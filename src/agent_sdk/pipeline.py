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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import orjson

from src.agent_sdk._shared import (
    SearchProvidersEmptyError,
    SearchProvidersFailedError,
    _auto_embed_chart,
)
from src.agent_sdk.image_gate import ImageGateError, check_hero_image
from src.agent_sdk.stage3_runner import (
    DEFAULT_GRAPHICS_MODEL,
    DEFAULT_WRITER_MODEL,
    Stage3Result,
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
# 10 = Stage 3 complete, awaiting image-prompt handshake (#403 slice 3)
# 11 = --resume image-gate failure (missing/wrong-size/wrong-dims PNG) (#403 slice 4)
EXIT_HANDSHAKE_PENDING = 10
EXIT_IMAGE_GATE_FAILED = 11

# #403 slice 3: slug-keyed canonical artefacts. logs/spike/* stays as
# telemetry only (gitignored at the project level for the spike dir).
POSTS_DIR = Path("output/posts")
STATE_DIR = Path("output/state")
IMAGE_DROP_DIR = Path("output/posts/images")


@dataclass
class HandshakeArtefacts:
    """Paths emitted by Stage 3 when running in default (pause-for-image) mode."""

    slug: str
    article_path: Path
    chart_path: Path | None
    prompt_path: Path | None
    state_path: Path
    image_drop_path: Path  # where the human must drop the file


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
    writer_model: str
    graphics_model: str
    stage3_seconds: float
    stage4_seconds: float
    article_chars: int


async def run_pipeline(
    topic: str,
    writer_budget_usd: float | None = 0.30,
    graphics_budget_usd: float | None = 0.10,
    writer_model: str = DEFAULT_WRITER_MODEL,
    graphics_model: str = DEFAULT_GRAPHICS_MODEL,
) -> PipelineResult:
    """Generate one article through the Agent SDK pipeline."""
    stage3 = await run_stage3(
        topic,
        writer_budget_usd=writer_budget_usd,
        graphics_budget_usd=graphics_budget_usd,
        writer_model=writer_model,
        graphics_model=graphics_model,
    )
    stage4 = run_stage4(stage3.article, stage3.chart_data)

    result = PipelineResult(
        topic=topic,
        article=stage4.article,
        chart_data=stage3.chart_data,
        editorial_score=stage4.editorial_score,
        gates_passed=stage4.gates_passed,
        publication_ready=stage4.publication_ready,
        publication_validator_passed=stage4.publication_validator_passed,
        publication_validator_issues=stage4.publication_validator_issues,
        total_cost_usd=stage3.total_cost_usd,
        writer_cost_usd=stage3.writer_cost_usd,
        graphics_cost_usd=stage3.graphics_cost_usd,
        writer_model=stage3.writer_model,
        graphics_model=stage3.graphics_model,
        stage3_seconds=stage3.wall_seconds,
        stage4_seconds=stage4.wall_seconds,
        article_chars=len(stage4.article),
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


# ---------------------------------------------------------------------------
# #403 slice 3: handshake state persistence + article-mutation helpers
# ---------------------------------------------------------------------------


def _state_path(slug: str) -> Path:
    return STATE_DIR / f"{slug}.json"


def _persist_stage3_artefacts(stage3: Stage3Result) -> HandshakeArtefacts:
    """Write the slug-keyed canonical artefacts + state file after Stage 3.

    The state file is the contract that ``--resume <slug>`` reads to pick
    up where Stage 3 left off. chart_data is embedded directly because
    Stage 4 needs the parsed dict (not a re-read of the chart JSON).
    """
    slug = stage3.slug
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    article_path = POSTS_DIR / f"{slug}.md"
    article_path.write_text(stage3.article)

    state_path = _state_path(slug)
    state = {
        "schema_version": 1,
        "slug": slug,
        "topic": stage3.topic,
        "stage3_completed_at": datetime.now(UTC).isoformat(),
        "article_path": str(article_path),
        "chart_path": str(stage3.chart_path) if stage3.chart_path else None,
        "prompt_path": str(stage3.prompt_path) if stage3.prompt_path else None,
        "chart_data": stage3.chart_data,
        "metrics": {
            "writer_cost_usd": stage3.writer_cost_usd,
            "graphics_cost_usd": stage3.graphics_cost_usd,
            "writer_model": stage3.writer_model,
            "graphics_model": stage3.graphics_model,
            "wall_seconds": stage3.wall_seconds,
            "article_chars": stage3.article_chars,
            "stat_audit_removed": stage3.stat_audit_removed,
        },
    }
    state_path.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))

    return HandshakeArtefacts(
        slug=slug,
        article_path=article_path,
        chart_path=stage3.chart_path,
        prompt_path=stage3.prompt_path,
        state_path=state_path,
        image_drop_path=IMAGE_DROP_DIR / f"{slug}.png",
    )


def _load_state(slug: str) -> dict:
    """Read the Stage 3 state file for ``slug``.

    Raises ``FileNotFoundError`` with an operator-friendly message when
    no state exists (user ran ``--resume`` against a slug that was never
    generated)."""
    path = _state_path(slug)
    if not path.exists():
        raise FileNotFoundError(
            f"No Stage 3 state for slug {slug!r} at {path}. "
            f"Run `python -m src.agent_sdk.pipeline '<topic>'` first."
        )
    return orjson.loads(path.read_bytes())


_FRONTMATTER_IMAGE_LINE = re.compile(r"^image(?:_alt|_caption)?:[^\n]*\n", re.MULTILINE)


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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the Agent SDK pipeline.")
    parser.add_argument("topic", nargs="*", help="Article topic")
    parser.add_argument(
        "--writer-budget",
        type=float,
        default=0.30,
        help="Hard cap on writer cost in USD (default 0.30, sized for Sonnet)",
    )
    parser.add_argument(
        "--graphics-budget",
        type=float,
        default=0.10,
        help="Hard cap on graphics cost in USD (default 0.10)",
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
        "--resume",
        metavar="SLUG",
        help=(
            "Resume after the image handshake. Reads Stage 3 state from "
            "output/state/<slug>.json, runs Stage 4. Requires the human to "
            "have dropped the hero PNG at output/posts/images/<slug>.png "
            "first, unless --no-image is also set."
        ),
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help=(
            "With --resume: strip image: / image_alt: / image_caption: from "
            "the article frontmatter before Stage 4. Ships chart-only."
        ),
    )
    args = parser.parse_args()
    topic = (
        " ".join(args.topic)
        if args.topic
        else "the productivity paradox of AI coding assistants"
    )

    # --research-only path (Stage 0 only) — unchanged
    if args.research_only:
        _run_research_only(topic)
        return

    # --resume path (Stage 4 only) — #403 slice 3
    if args.resume:
        _run_resume(args.resume, no_image=args.no_image)
        return

    # Default path (Stage 3 only, then pause for image handshake) — #403 slice 3
    print(f"Running Agent SDK pipeline on: {topic}")
    print(f"  Models: writer={args.writer_model}, graphics={args.graphics_model}")
    print(
        f"  Budgets: writer ${args.writer_budget:.2f}, "
        f"graphics ${args.graphics_budget:.2f}",
    )
    _run_stage3_with_handshake(
        topic,
        writer_budget=args.writer_budget,
        graphics_budget=args.graphics_budget,
        writer_model=args.writer_model,
        graphics_model=args.graphics_model,
    )


def _run_research_only(topic: str) -> None:
    """Stage 0 only — print the assembled brief, no LLM calls."""
    from src.agent_sdk._shared import build_research_brief

    try:
        brief = build_research_brief(topic)
    except SearchProvidersFailedError as exc:
        print(
            "\nResearch aborted: providers failed.\n"
            f"  {exc}\n"
            "  Likely causes: provider outage, missing/invalid "
            "SERPER_API_KEY, or query rejected by provider (HTTP 4xx). "
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


def _run_stage3_with_handshake(
    topic: str,
    *,
    writer_budget: float | None,
    graphics_budget: float | None,
    writer_model: str,
    graphics_model: str,
) -> None:
    """Run Stage 3, persist artefacts, print the handshake message, exit 10.

    The pause-for-image step is the heart of Path A (#403): the pipeline
    does NOT auto-call a paid image API. Instead it produces a paste-ready
    prompt and waits for the human to drop the PNG. Resume via --resume.
    """
    start = time.perf_counter()
    try:
        stage3 = asyncio.run(
            run_stage3(
                topic,
                writer_budget_usd=writer_budget,
                graphics_budget_usd=graphics_budget,
                writer_model=writer_model,
                graphics_model=graphics_model,
            )
        )
    except SearchProvidersFailedError as exc:
        print(
            "\nPipeline aborted: research providers failed.\n"
            f"  {exc}\n"
            "  Likely causes: provider outage, missing/invalid SERPER_API_KEY, "
            "or query rejected by provider (HTTP 4xx). Retry in a few minutes "
            "or rephrase the topic as a noun-phrase rather than a question.",
            file=sys.stderr,
        )
        sys.exit(2)
    except SearchProvidersEmptyError as exc:
        print(
            "\nPipeline aborted: search providers ran but returned zero sources.\n"
            f"  {exc}\n"
            "  Likely cause: topic too narrow, too recent, or phrased in a way "
            "that matches nothing in arXiv/Google Scholar/Google Web. Try "
            "broadening it or rephrasing as a noun-phrase.",
            file=sys.stderr,
        )
        sys.exit(3)
    elapsed = time.perf_counter() - start

    artefacts = _persist_stage3_artefacts(stage3)
    _print_handshake_message(stage3, artefacts, elapsed)
    sys.exit(EXIT_HANDSHAKE_PENDING)


def _print_handshake_message(
    stage3: Stage3Result,
    artefacts: HandshakeArtefacts,
    wall_seconds: float,
) -> None:
    """Verbose, paste-ready operator instructions per spec Q2 lock-in."""
    print(
        f"\nStage 3 complete: ${stage3.total_cost_usd:.4f} "
        f"(writer ${stage3.writer_cost_usd:.4f} via {stage3.writer_model}, "
        f"graphics ${stage3.graphics_cost_usd:.4f} via {stage3.graphics_model}), "
        f"{wall_seconds:.1f}s, {stage3.article_chars} chars."
    )
    print(f"\nSlug: {artefacts.slug}")
    print("\nArtefacts:")
    print(f"  Article: {artefacts.article_path}")
    if artefacts.chart_path:
        print(f"  Chart:   {artefacts.chart_path}")
    if artefacts.prompt_path:
        print(f"  Prompt:  {artefacts.prompt_path}")
    print(f"  State:   {artefacts.state_path}")

    print("\n" + "=" * 70)
    if stage3.image_prompt:
        print("HANDOFF — paste this prompt into chat.openai.com (image tool):")
        print("=" * 70)
        print(stage3.image_prompt)
        print("=" * 70)
        print(f"\nDrop the generated PNG here: {artefacts.image_drop_path}")
        print(
            "\nThen resume with:\n"
            f"  python -m src.agent_sdk.pipeline --resume {artefacts.slug}\n"
            "\nOr ship chart-only (no hero image) with:\n"
            f"  python -m src.agent_sdk.pipeline --resume {artefacts.slug} --no-image"
        )
    else:
        print(
            "No image prompt was generated (writer omitted image_alt). "
            "Resume in chart-only mode with:\n"
            f"  python -m src.agent_sdk.pipeline --resume {artefacts.slug} --no-image"
        )
    print("=" * 70 + "\n")


def _run_resume(slug: str, *, no_image: bool) -> None:
    """Stage 4 only — load state, validate, optionally strip image fields."""
    try:
        state = _load_state(slug)
    except FileNotFoundError as exc:
        print(f"\n{exc}", file=sys.stderr)
        sys.exit(1)

    article_path = Path(state["article_path"])
    if not article_path.exists():
        print(
            f"\nState references article at {article_path} but the file is "
            "missing. Re-run Stage 3.",
            file=sys.stderr,
        )
        sys.exit(1)

    article = article_path.read_text()
    if no_image:
        # Stage 4 normally inserts the chart embed using the hero-image
        # slug. Preserve that derivation before chart-only mode removes
        # the hero metadata.
        article = _auto_embed_chart(article)
        article = _strip_image_frontmatter(article)
        # Persist the stripped version so Stage 4 + deploy see the same shape
        article_path.write_text(article)
        logger.info(
            "Stripped image: / image_alt: / image_caption: from %s", article_path
        )
    else:
        # #403 slice 4: deterministic gate before Stage 4 — the dropped hero
        # PNG must exist, be a real PNG, and match the expected aspect ratio.
        # Visual-quality grade is human-orchestrated post-resume.
        hero_path = IMAGE_DROP_DIR / f"{slug}.png"
        try:
            check_hero_image(hero_path)
        except ImageGateError as exc:
            print(f"\nImage gate failed: {exc}", file=sys.stderr)
            sys.exit(EXIT_IMAGE_GATE_FAILED)

    start = time.perf_counter()
    stage4 = run_stage4(article, state["chart_data"])
    elapsed = time.perf_counter() - start

    # Write back the polished article (Stage 4 may auto-fix British spelling etc.)
    article_path.write_text(stage4.article)

    s3_metrics = state.get("metrics", {})
    total_cost = s3_metrics.get("writer_cost_usd", 0.0) + s3_metrics.get(
        "graphics_cost_usd", 0.0
    )
    print(
        f"\nStage 4 complete: ${total_cost:.4f} pipeline cost, "
        f"{elapsed:.2f}s, score={stage4.editorial_score}%, "
        f"gates={stage4.gates_passed}/5, "
        f"validator={'PASS' if stage4.publication_validator_passed else 'FAIL'}, "
        f"ready={stage4.publication_ready}."
    )
    if not stage4.publication_validator_passed:
        print("Validator issues:")
        for issue in stage4.publication_validator_issues:
            print(f"  - {issue.get('check', '?')}: {issue.get('message', '?')}")
    print(f"Article: {article_path}")


if __name__ == "__main__":
    main()
