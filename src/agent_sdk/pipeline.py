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
    _auto_embed_chart,
    canonical_slug,
    describe_slug,
)
from src.agent_sdk.hero_svg import HERO_IMAGES_DIR
from src.agent_sdk.stage3_runner import (
    DEFAULT_GRAPHICS_MODEL,
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
# human-image handshake in B-021: Stage 3 draws its own hero, so nothing pauses
# and there is no dropped PNG to gate. Do not reuse the numbers — old scripts
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
    chart_data: dict
    editorial_score: int
    gates_passed: int
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    total_cost_usd: float
    writer_cost_usd: float
    graphics_cost_usd: float
    research_cost_usd: float
    writer_model: str
    graphics_model: str
    stage3_seconds: float
    stage4_seconds: float
    article_chars: int
    hero_critique: str = ""
    hero_error: str = ""


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


def _prepare_for_stage4(article: str, *, hero_drawn: bool) -> str:
    """Embed the chart and, when there is no hero, strip the hero metadata.

    This behaviour used to be gated behind ``image_mode="chart_only"``, which was
    built on the premise that the article ships WITHOUT a hero — so it stripped
    ``image_alt``/``image_caption`` along with ``image:``. B-016b made that
    premise false, and the blog requires both fields, so a drawn hero produced an
    article rejected for "missing image_alt" (B-020 run 4). Strip only when there
    really is no hero.
    """
    # Embed the chart while the hero-image slug is still present (the chart path
    # is derived from it), THEN strip — stripping first would leave
    # _auto_embed_chart with no slug and fail the required-chart check (BUG-040).
    article = _auto_embed_chart(article)
    if hero_drawn:
        return article
    return _strip_image_frontmatter(article)


def _maybe_inject_hero_prompt(
    article: str, *, image_prompt: str, hero_drawn: bool
) -> str:
    """Surface the hero-image prompt for a reviewer — only if no hero was drawn.

    Injecting it alongside a hero that already exists tells the reviewer to
    hand-make art the pipeline just produced.
    """
    if image_prompt and not hero_drawn:
        return _inject_hero_prompt_comment(article, image_prompt)
    return article


async def run_pipeline(
    topic: str,
    writer_budget_usd: float | None = DEFAULT_WRITER_BUDGET_USD,
    graphics_budget_usd: float | None = 0.10,
    writer_model: str = DEFAULT_WRITER_MODEL,
    graphics_model: str = DEFAULT_GRAPHICS_MODEL,
    research_mode: Literal["deterministic", "deep", "claude_web"] = "deterministic",
    brief_override: str | None = None,
) -> PipelineResult:
    """Generate one article through the Agent SDK pipeline — Stage 3 then Stage 4.

    There is one path (B-021). Stage 3 draws the hero SVG itself (B-016b), so the
    article ships with its hero and chart. If no hero was drawn, the hero
    frontmatter is stripped so the draft validates on its chart alone and the
    hero-image *prompt* is surfaced inline for a reviewer to supply art by hand
    (CLAUDE.md Operating Constraint #4).
    """
    stage3 = await run_stage3(
        topic,
        writer_budget_usd=writer_budget_usd,
        graphics_budget_usd=graphics_budget_usd,
        writer_model=writer_model,
        graphics_model=graphics_model,
        research_mode=research_mode,
        brief_override=brief_override,
    )
    hero_drawn = bool(getattr(stage3, "hero_path", None))
    article_for_stage4 = _prepare_for_stage4(stage3.article, hero_drawn=hero_drawn)
    stage4 = run_stage4(article_for_stage4, stage3.chart_data)

    # Surface the hero-image prompt inline when no hero was drawn, so a reviewer
    # can supply art at PR-review time (CLAUDE.md Operating Constraint #4).
    # Injected AFTER Stage 4 so validation is unchanged.
    final_article = _maybe_inject_hero_prompt(
        stage4.article,
        image_prompt=getattr(stage3, "image_prompt", ""),
        hero_drawn=hero_drawn,
    )

    # The blog requires a resolvable `image:` (B-019), so link the hero asset if
    # one has been drawn for this slug. No asset -> the key stays absent and the
    # blog will reject the article; drawing it automatically is B-016b.
    final_article = _link_hero_asset(
        final_article, canonical_slug(final_article, topic)
    )

    result = PipelineResult(
        topic=topic,
        article=final_article,
        chart_data=stage3.chart_data,
        editorial_score=stage4.editorial_score,
        gates_passed=stage4.gates_passed,
        publication_ready=stage4.publication_ready,
        publication_validator_passed=stage4.publication_validator_passed,
        publication_validator_issues=stage4.publication_validator_issues,
        total_cost_usd=stage3.total_cost_usd,
        writer_cost_usd=stage3.writer_cost_usd,
        graphics_cost_usd=stage3.graphics_cost_usd,
        research_cost_usd=stage3.research_cost_usd,
        writer_model=stage3.writer_model,
        graphics_model=stage3.graphics_model,
        stage3_seconds=stage3.wall_seconds,
        stage4_seconds=stage4.wall_seconds,
        article_chars=len(final_article),
        # getattr: test doubles stand in for Stage3Result, same reason as
        # image_prompt above.
        hero_critique=getattr(stage3, "hero_critique", ""),
        hero_error=getattr(stage3, "hero_error", ""),
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
    table so the recorded cost matches the actual API charge. The writer
    and graphics calls are logged as separate ``log_llm_call`` entries so
    per-model attribution is preserved in ``logs/execution_roi.json``.
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
    tracker.log_llm_call(
        execution_id=execution_id,
        agent=ROI_PIPELINE_AGENT,
        model=result.graphics_model,
        input_tokens=0,
        output_tokens=0,
        cost_usd=result.graphics_cost_usd,
        metadata={"stage": "graphics", "topic": result.topic},
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
        "graphics_cost_usd": result.graphics_cost_usd,
        "research_cost_usd": result.research_cost_usd,
        "writer_model": result.writer_model,
        "graphics_model": result.graphics_model,
        "stage3_seconds": result.stage3_seconds,
        "stage4_seconds": result.stage4_seconds,
        "wall_seconds": total_wall_seconds,
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
        "--graphics-budget",
        type=float,
        default=0.40,
        help=(
            "Hard cap on graphics cost in USD (default 0.40). Higher than the "
            "library default because the subscription CLI uses multiple turns "
            "for the chart JSON (see BUG-042)."
        ),
    )
    parser.add_argument(
        "--writer-model",
        default=DEFAULT_WRITER_MODEL,
        help=f"Writer model id (default {DEFAULT_WRITER_MODEL})",
    )
    parser.add_argument(
        "--graphics-model",
        default=DEFAULT_GRAPHICS_MODEL,
        help=f"Graphics model id (default {DEFAULT_GRAPHICS_MODEL})",
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

    # The only path (B-021): Stage 3 draws the hero and Stage 4 validates, end to
    # end, keyless (pair with --research-mode claude_web for zero keys).
    _run_end_to_end(
        topic,
        writer_budget=args.writer_budget,
        graphics_budget=args.graphics_budget,
        writer_model=args.writer_model,
        graphics_model=args.graphics_model,
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
    """The hero's ``<desc>``, cleaned for use as YAML-safe alt text."""
    try:
        match = _HERO_DESC.search(path.read_text())
    except OSError:
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
    graphics_budget: float | None,
    writer_model: str,
    graphics_model: str,
    research_mode: str,
    brief_override: str | None = None,
) -> None:
    """Run the pipeline end to end and write the finished article.

    With ``--research-mode claude_web`` this is fully keyless — Stage 3
    writer/graphics, the hero drawing, and research all run on the Claude
    subscription via the Agent SDK; no ANTHROPIC/OPENAI/SERPER key is used.
    """
    print(f"Running Agent SDK pipeline on: {topic}")
    print(f"  Research mode: {research_mode}; models: writer={writer_model}")
    try:
        result = asyncio.run(
            run_pipeline(
                topic,
                writer_budget_usd=writer_budget,
                graphics_budget_usd=graphics_budget,
                writer_model=writer_model,
                graphics_model=graphics_model,
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

    # B-016b failure policy. The hero is a separate axis from the validator: the
    # blog requires a resolvable image:, and an unresolved composition critique
    # must not ship on a permanent public page just because a warning was logged.
    hero_failed = bool(result.hero_critique or result.hero_error)
    if result.hero_error:
        print(f"❌ No hero drawn: {result.hero_error}", file=sys.stderr)
        print(
            "   The blog requires a resolvable image: — it will reject this "
            "article until a hero exists.",
            file=sys.stderr,
        )
    if result.hero_critique:
        print(
            "❌ Hero composition still defective after redraws "
            "(the SVG is on disk — look at it, then redraw or accept):",
            file=sys.stderr,
        )
        for line in result.hero_critique.splitlines():
            print(f"  {line}", file=sys.stderr)

    if result.publication_validator_passed and not hero_failed:
        print("✅ Publication validator PASSED — article is publish-ready.")
        sys.exit(0)
    if not result.publication_validator_passed:
        print("❌ Publication validator found issues:", file=sys.stderr)
        for issue in result.publication_validator_issues:
            print(
                f"  [{issue.get('severity')}] {issue.get('check')}: "
                f"{issue.get('message')}",
                file=sys.stderr,
            )
    sys.exit(1)


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
