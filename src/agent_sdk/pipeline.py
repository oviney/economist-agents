"""End-to-end Agent SDK pipeline: Stage 3 (LLM) + Stage 4 (deterministic).

Mirrors the CrewAI flow at the level needed for the Story 2 verification
run. Story 3 added cost-budget wiring + per-run cost log. Stories 4-5
will add model tiering and the CrewAI removal.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import orjson

from src.agent_sdk._shared import (
    SearchProvidersEmptyError,
    SearchProvidersFailedError,
    canonical_slug,
    describe_slug,
)
from src.agent_sdk.hero_svg import HERO_IMAGES_DIR
from src.agent_sdk.review_packet import notify, write_packet
from src.agent_sdk.stage3_runner import (
    DEFAULT_WRITER_BUDGET_USD,
    DEFAULT_WRITER_MODEL,
    run_stage3,
)
from src.agent_sdk.stage4_runner import run_stage4
from src.telemetry.roi_tracker import ROITracker, get_tracker

logger = logging.getLogger(__name__)

COST_LOG_PATH = Path("logs/agent_sdk_costs.jsonl")

# Distinct exit codes so callers (CI, scripts, the operator) can branch
# on outcome without parsing stderr.
# 0  = full pipeline complete (Stage 3 + Stage 4 ran)
# 1  = operator error (unknown slug, missing article)
# 2  = SearchProvidersFailedError (transient/environmental)
# 3  = SearchProvidersEmptyError (topic too narrow)
#
# 10 (handshake pending) and 11 (image-gate failure) were retired with the
# human-image handshake in B-021, because nothing pauses mid-run and there is no
# dropped PNG to gate. The reason B-021 gave — "Stage 3 draws its own hero" — no
# longer holds: B-042 removed the hero author, and the owner makes every image.
# The exit codes stay retired either way. Do not reuse the numbers — old scripts
# and notes still mention them.

# Slug-keyed canonical artefacts. logs/spike/* stays as telemetry only
# (gitignored at the project level for the spike dir).
POSTS_DIR = Path("output/posts")
STATE_DIR = Path("output/state")


# Logical agent name used when recording pipeline runs in the ROI tracker.
ROI_PIPELINE_AGENT = "pipeline"


@dataclass
class PipelineResult:
    """Captured metrics for an end-to-end run."""

    topic: str
    article: str
    #: B-042: figures extracted from the brief for the owner to frame, or None
    #: when the brief carries no numeric claim.
    chart_proposal: dict | None
    editorial_score: int
    gates_passed: int
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    total_cost_usd: float
    writer_cost_usd: float
    research_cost_usd: float
    writer_model: str
    stage3_seconds: float
    stage4_seconds: float
    article_chars: int
    #: B-042: what the review packet needs to tell the owner what to make.
    slug: str = ""
    image_prompt: str = ""
    chart_spec_path: Path | None = None


def _numeric(source: object, name: str) -> float:
    """Read a numeric metric off a Stage 3 result, tolerating test doubles.

    ``getattr`` on a ``MagicMock`` returns another ``MagicMock`` rather than the
    default, and these values reach the JSON cost ledger — where an unserialisable
    value does not fail loudly, it makes the whole row vanish into a "cost log
    write failed (non-fatal)" warning. Anything that is not a real number becomes
    zero.
    """
    value = getattr(source, name, 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def load_brief_file(path: str | Path) -> str:
    """Load an opt-in deep-research brief for the writer, EXCLUDING refuted claims.

    B-012: a deep-research brief (``docs/research/<slug>.md``) carries a
    ``## Refuted / unverified`` section listing claims the adversarial check
    killed. Those must never reach the writer, so this drops that section (from
    its heading to the next top-level ``##`` heading or EOF); the verified claims
    and sources pass through unchanged.
    """
    text = Path(path).read_text()
    text = re.sub(r"(?ms)^##\s+Refuted\b.*?(?=^##\s|\Z)", "", text)
    return text.strip() + "\n"


def _prepare_for_stage4(article: str) -> str:
    """Strip the hero metadata the writer emitted.

    B-042: no art exists at this point in the run and none will — the owner
    authors every image. So ``image:``/``image_alt``/``image_caption`` are
    always stripped, and the article validates as art-pending (Phase A). The
    chart is no longer embedded here either: there is no chart until the owner
    renders one, and embedding a path to a PNG nobody has drawn is what made
    ``missing_chart`` satisfiable by a broken link.
    """
    return _strip_image_frontmatter(article)


async def run_pipeline(
    topic: str,
    writer_budget_usd: float | None = DEFAULT_WRITER_BUDGET_USD,
    writer_model: str = DEFAULT_WRITER_MODEL,
    research_mode: Literal["deterministic", "deep", "claude_web"] = "deterministic",
    brief_override: str | None = None,
) -> PipelineResult:
    """Generate one article through the Agent SDK pipeline — Stage 3 then Stage 4.

    There is one path (B-021), and it still exits 0 with a complete, fully-gated
    article — nothing pauses mid-run, so ADR-0016 holds. What changed in B-042 is
    what "complete" means: the pipeline produces everything a *machine* can
    produce and hands the art off. No hero is drawn and no chart is generated;
    the run ends with a review packet naming what the owner must make.
    """
    stage3 = await run_stage3(
        topic,
        writer_budget_usd=writer_budget_usd,
        writer_model=writer_model,
        research_mode=research_mode,
        brief_override=brief_override,
    )
    article_for_stage4 = _prepare_for_stage4(stage3.article)
    stage4 = run_stage4(article_for_stage4)

    # Surface the hero brief inline so it travels with the article the owner
    # reads. Injected AFTER Stage 4 so validation is unchanged, and refused at
    # the deploy boundary if it is still there (BUG-065, ADR-0017).
    image_prompt = getattr(stage3, "image_prompt", "")
    final_article = (
        _inject_hero_prompt_comment(stage4.article, image_prompt)
        if image_prompt
        else stage4.article
    )

    result = PipelineResult(
        topic=topic,
        article=final_article,
        chart_proposal=getattr(stage3, "chart_proposal", None),
        editorial_score=stage4.editorial_score,
        gates_passed=stage4.gates_passed,
        publication_ready=stage4.publication_ready,
        publication_validator_passed=stage4.publication_validator_passed,
        publication_validator_issues=stage4.publication_validator_issues,
        total_cost_usd=stage3.total_cost_usd,
        writer_cost_usd=stage3.writer_cost_usd,
        research_cost_usd=stage3.research_cost_usd,
        writer_model=stage3.writer_model,
        stage3_seconds=stage3.wall_seconds,
        stage4_seconds=stage4.wall_seconds,
        article_chars=len(final_article),
        slug=getattr(stage3, "slug", "") or canonical_slug(final_article, topic),
        image_prompt=image_prompt,
        chart_spec_path=getattr(stage3, "chart_spec_path", None),
    )
    wall_seconds = result.stage3_seconds + result.stage4_seconds
    try:
        await asyncio.to_thread(_append_cost_log, result, wall_seconds)
    except Exception as exc:
        logger.warning("Cost log write failed (non-fatal): %s", exc)
    try:
        await asyncio.to_thread(_record_roi, result)
    except Exception as exc:
        logger.warning("ROI telemetry write failed (non-fatal): %s", exc)
    return result


def _record_roi(result: PipelineResult) -> None:
    """Record this pipeline run in the ROI telemetry log.

    Uses the SDK-reported ``total_cost_usd`` rather than the local pricing
    table so the recorded cost matches the actual API charge.

    B-042 removed the graphics entry: there is no graphics call. A stage that
    can only ever log $0.00 is the kind of always-zero reading B-041 objected
    to, so it is gone rather than left recording nothing.
    """
    tracker: ROITracker = get_tracker()
    execution_id = tracker.start_execution(ROI_PIPELINE_AGENT)
    tracker.log_llm_call(
        execution_id=execution_id,
        agent=ROI_PIPELINE_AGENT,
        model=result.writer_model,
        input_tokens=0,
        output_tokens=0,
        cost_usd=result.writer_cost_usd,
        metadata={"stage": "writer", "topic": result.topic},
    )
    tracker.end_execution(execution_id)


_FRONTMATTER_IMAGE_LINE = re.compile(r"^image(?:_alt|_caption)?:[^\n]*\n", re.MULTILINE)


def _inject_hero_prompt_comment(article: str, image_prompt: str) -> str:
    """Insert the hero-image prompt as a review-visible HTML comment at the top
    of the body (CLAUDE.md Operating Constraint #4).

    Chart-only posts ship without a hero; the reviewer generates the image from
    this prompt at PR-review time and replaces the comment with the image. The
    comment is invisible in the rendered post but shows in the PR diff and the
    raw markdown, right where the hero belongs.
    """
    # Neutralise any "-->" in the prompt so it cannot terminate the HTML comment
    # early and leak prompt text into the rendered post.
    safe_prompt = image_prompt.strip().replace("-->", "--​>")
    block = (
        "<!-- HERO IMAGE — generate an image from the prompt below, then replace "
        "this whole comment with it (see output/posts/<slug>.image_prompt.md):\n\n"
        f"{safe_prompt}\n-->\n\n"
    )
    if not article.startswith("---"):
        return block + article
    parts = article.split("---", 2)
    if len(parts) < 3:
        return block + article
    body = parts[2].lstrip("\n")
    return f"---{parts[1]}---\n\n{block}{body}"


def _strip_image_frontmatter(article: str) -> str:
    """Remove image:, image_alt:, image_caption: lines from frontmatter.

    For ``--no-image`` mode: the article shipped chart-only. Stripping
    these three fields satisfies the publication validator's "image:
    optional, file must exist when present" contract (slice 2) without
    leaving dangling alt/caption fields that reference an absent image.
    Only the frontmatter (between the first two ``---`` lines) is
    touched; body image syntax (chart embed) is left alone.
    """
    if not article.startswith("---"):
        return article
    parts = article.split("---", 2)
    if len(parts) < 3:
        return article
    fm = _FRONTMATTER_IMAGE_LINE.sub("", parts[1])
    return f"---{fm}---{parts[2]}"


# ---------------------------------------------------------------------------
# Existing cost-log + ROI helpers
# ---------------------------------------------------------------------------


def _append_cost_log(result: PipelineResult, total_wall_seconds: float) -> None:
    """Append a single JSON line summarising this run for spend tracking."""
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "topic": result.topic,
        "total_cost_usd": result.total_cost_usd,
        "writer_cost_usd": result.writer_cost_usd,
        "research_cost_usd": result.research_cost_usd,
        "writer_model": result.writer_model,
        "stage3_seconds": result.stage3_seconds,
        "stage4_seconds": result.stage4_seconds,
        "wall_seconds": total_wall_seconds,
        # B-042: the hero fields B-041 added are gone with the hero draw. They
        # measured a stage that no longer runs, and the duration swing they
        # existed to attribute cannot recur — nothing in a run now blocks on a
        # model drawing a picture.
        "chart_figures_proposed": (
            len(result.chart_proposal["data"]) if result.chart_proposal else 0
        ),
        "editorial_score": result.editorial_score,
        "gates_passed": result.gates_passed,
        "publication_validator_passed": result.publication_validator_passed,
        "article_chars": result.article_chars,
    }
    with COST_LOG_PATH.open("ab") as fh:
        fh.write(orjson.dumps(entry) + b"\n")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the Agent SDK pipeline.")
    parser.add_argument("topic", nargs="*", help="Article topic")
    parser.add_argument(
        "--writer-budget",
        type=float,
        default=DEFAULT_WRITER_BUDGET_USD,
        help=(
            f"Hard cap on TOTAL writer cost in USD across all attempts (default "
            f"{DEFAULT_WRITER_BUDGET_USD:.2f}). This is a runaway guard, not "
            "billing — the subscription path is not metered per token. The "
            "default is one measured Sonnet attempt x the retry limit, so a "
            "malformed first draft can still be regenerated (BUG-061)."
        ),
    )
    parser.add_argument(
        "--writer-model",
        default=DEFAULT_WRITER_MODEL,
        help=f"Writer model id (default {DEFAULT_WRITER_MODEL})",
    )
    parser.add_argument(
        "--research-only",
        action="store_true",
        help=(
            "Run only Stage 0 (web search + brief assembly), print the brief, "
            "exit. No LLM calls. Useful for iterating on topic phrasing."
        ),
    )
    parser.add_argument(
        "--research-mode",
        choices=("deterministic", "deep", "claude_web"),
        default="deterministic",
        help=(
            "Research path: 'deterministic' (default, Serper) | 'deep' (recursive, "
            "Serper) | 'claude_web' (keyless — Claude's own WebSearch/WebFetch on "
            "the subscription, no SERPER_API_KEY). See ADR-0013."
        ),
    )
    parser.add_argument(
        "--brief",
        default=None,
        metavar="PATH",
        help=(
            "Opt-in (B-012): use a pre-built deep-research brief file "
            "(docs/research/<slug>.md) as the writer's research instead of "
            "running --research-mode. Refuted claims are stripped. For flagship "
            "posts — the deep-research harness is heavy; claude_web is the default."
        ),
    )
    args = parser.parse_args(argv)
    topic = (
        " ".join(args.topic)
        if args.topic
        else "the productivity paradox of AI coding assistants"
    )

    # --research-only path (Stage 0 only) — unchanged
    if args.research_only:
        _run_research_only(topic)
        return

    # The only path (B-021): Stage 3 writes, Stage 4 validates, end to end,
    # keyless (pair with --research-mode claude_web for zero keys). B-042: the
    # run ends with a review packet, not with finished art.
    _run_end_to_end(
        topic,
        writer_budget=args.writer_budget,
        writer_model=args.writer_model,
        research_mode=args.research_mode,
        brief_override=load_brief_file(args.brief) if args.brief else None,
    )


def _slug_from_article(article: str, fallback: str) -> str:
    """Filename slug for the article — the single canonical slug (B-008), shared
    with the chart PNG, chart embed, and image-prompt sidecar."""
    return canonical_slug(article, fallback)


#: Constraint #4 prefers SVG: the blog's ``responsive-image.html`` rewrites
#: ``.png`` to ``.webp``, so a PNG hero needs a ``.webp`` sibling while an SVG
#: takes the plain ``<img>`` branch. Order = preference.
_HERO_SUFFIXES = (".svg", ".png")

_IMAGE_LINE = re.compile(r"^image:.*$\n?", re.MULTILINE)


def _link_hero_asset(
    article: str, slug: str, *, images_dir: Path = HERO_IMAGES_DIR
) -> str:
    """Point ``image:`` at the article's hero asset, if one has been drawn.

    The blog **requires** ``image:`` — measured 2026-07-26 with
    ``scripts/acceptance_blog_frontmatter.sh``, both ``validate-posts.sh`` and
    ``validate-post-quality.sh`` error with "hero image not set", and the path
    must resolve to a real file. So there is **no publishable chart-only
    article** (this closes the B-015 open question).

    This function only *links* an asset that already exists at
    ``<images_dir>/<slug>-hero.{svg,png}``. Generating it is B-016b. When no
    asset exists the key is left absent rather than pointed at a missing file:
    absent is a clean gate failure, a broken path breaks the Jekyll build
    (BUG-055).
    """
    if not article.startswith("---"):
        return article
    for suffix in _HERO_SUFFIXES:
        if (images_dir / f"{slug}-hero{suffix}").is_file():
            break
    else:
        return article

    parts = article.split("---", 2)
    if len(parts) < 3:
        return article
    fm = _IMAGE_LINE.sub("", parts[1]).rstrip()
    fm += f"\nimage: /assets/images/{slug}-hero{suffix}\n"

    # The hero's own <desc> is real alt text: it describes what was DRAWN. The
    # writer's image_alt is a drawing brief ("An Economist-style editorial
    # illustration of...") and the blog rejects that as prompt text rather than
    # accessible alt text (B-020 run 5).
    desc = _hero_description(images_dir / f"{slug}-hero{suffix}")
    if desc:
        fm = _IMAGE_ALT_LINE.sub("", fm).rstrip()
        fm += f'\nimage_alt: "{desc}"\n'
    return "---" + fm + "---" + parts[2]


_HERO_DESC = re.compile(r"<desc[^>]*>(.*?)</desc>", re.DOTALL | re.IGNORECASE)
_IMAGE_ALT_LINE = re.compile(r"^image_alt:.*$\n?", re.MULTILINE)


def _hero_description(path: Path) -> str:
    """The hero's ``<desc>``, cleaned for use as YAML-safe alt text.

    Only an SVG has one. BUG-072: this read *any* hero as text, so a real PNG —
    a first-class hero format, listed in ``_HERO_SUFFIXES`` and given a ``.webp``
    sibling at deploy — raised ``UnicodeDecodeError`` and took ``make art`` down
    with it. The suite missed it because its PNG heroes are written with
    ``write_text("stub")``, which is a text file wearing a ``.png`` name.

    A PNG hero therefore has no alt text to harvest, and the caller leaves
    ``image_alt`` for a human. That is correct rather than a gap: alt text
    describes what was drawn, and nothing on disk can tell us that about a
    raster.
    """
    if path.suffix.lower() != ".svg":
        return ""
    try:
        match = _HERO_DESC.search(path.read_text())
    except (OSError, UnicodeDecodeError):
        return ""
    if not match:
        return ""
    # Collapse whitespace and drop double quotes so the value cannot break the
    # front matter it is written into.
    return " ".join(match.group(1).split()).replace('"', "").strip()


def _run_end_to_end(
    topic: str,
    *,
    writer_budget: float | None,
    writer_model: str,
    research_mode: str,
    brief_override: str | None = None,
) -> None:
    """Run the pipeline end to end, write the article, and hand off the art.

    With ``--research-mode claude_web`` this is fully keyless — the writer and
    research both run on the Claude subscription via the Agent SDK; no
    ANTHROPIC/OPENAI/SERPER key is used.
    """
    print(f"Running Agent SDK pipeline on: {topic}")
    print(f"  Research mode: {research_mode}; models: writer={writer_model}")
    try:
        result = asyncio.run(
            run_pipeline(
                topic,
                writer_budget_usd=writer_budget,
                writer_model=writer_model,
                research_mode=research_mode,
                brief_override=brief_override,
            )
        )
    except SearchProvidersFailedError as exc:
        print(
            "\nPipeline aborted: research providers failed.\n"
            f"  {exc}\n"
            "  Likely cause: an arXiv / Semantic Scholar outage or rate-limit. "
            "Retry in a few minutes "
            "or rephrase the topic as a noun-phrase rather than a question.",
            file=sys.stderr,
        )
        sys.exit(2)
    except SearchProvidersEmptyError as exc:
        print(
            "\nPipeline aborted: search providers ran but returned zero sources.\n"
            f"  {exc}\n"
            "  Likely cause: topic too narrow, too recent, or phrased in a way "
            "that matches nothing in arXiv / Semantic Scholar. Try "
            "broadening it or rephrasing as a noun-phrase.",
            file=sys.stderr,
        )
        sys.exit(3)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug_from_article(result.article, topic)
    article_path = POSTS_DIR / f"{slug}.md"
    article_path.write_text(result.article)

    print(
        f"\nStage 3+4 complete: ${result.total_cost_usd:.4f}, "
        f"{result.article_chars} chars → {article_path}"
    )
    # The slug becomes a permanent URL — oviney/blog has no jekyll-redirect-from
    # and _config.yml is a protected file, so renaming a published post 404s the
    # original. Surface it explicitly for review rather than burying it in the
    # output path (B-019).
    print(f"  {describe_slug(result.article, topic)}")

    # B-042: the run ends by handing off, not by finishing. Writing the packet
    # must not be able to lose a good article, so a failure here is reported and
    # the exit code still reflects the gates.
    packet_path: Path | None = None
    try:
        packet_path = write_packet(result, article_path)
    except OSError as exc:
        print(f"⚠️  Review packet could not be written: {exc}", file=sys.stderr)

    if not result.publication_validator_passed:
        print("❌ Publication validator found issues:", file=sys.stderr)
        for issue in result.publication_validator_issues:
            print(
                f"  [{issue.get('severity')}] {issue.get('check')}: "
                f"{issue.get('message')}",
                file=sys.stderr,
            )
        sys.exit(1)

    chart_line = (
        f"{len(result.chart_proposal['data'])} chart figure(s) proposed"
        if result.chart_proposal
        else "no chart proposed (no numeric claim in the brief)"
    )
    print("\n✅ Every gate passed. The prose is ready; the art is yours.")
    print(f"  Hero: draw it at output/posts/images/{result.slug}-hero.svg")
    print(f"  Chart: {chart_line}")
    if packet_path:
        print(f"\n📋 Review packet — read this next: {packet_path}")
    notify(
        "Article ready for your review",
        f"{result.slug} — passed every gate. Hero and chart are yours.",
    )
    sys.exit(0)


def _run_research_only(topic: str) -> None:
    """Stage 0 only — print the assembled brief, no LLM calls."""
    from src.agent_sdk._shared import build_research_brief

    try:
        brief = build_research_brief(topic)
    except SearchProvidersFailedError as exc:
        print(
            "\nResearch aborted: providers failed.\n"
            f"  {exc}\n"
            "  Likely cause: an arXiv / Semantic Scholar outage or rate-limit. "
            "Retry in a few minutes or rephrase the topic.",
            file=sys.stderr,
        )
        sys.exit(2)
    except SearchProvidersEmptyError as exc:
        print(
            "\nResearch aborted: providers ran but returned zero sources.\n"
            f"  {exc}\n"
            "  Likely cause: topic too narrow, too recent, or phrased in "
            "a way that matches nothing. Try broadening or rephrasing.",
            file=sys.stderr,
        )
        sys.exit(3)
    print("\n--- Research brief ---\n")
    print(brief)


if __name__ == "__main__":
    main()
