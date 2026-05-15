"""End-to-end Agent SDK pipeline: Stage 3 (LLM) + Stage 4 (deterministic).

Mirrors the CrewAI flow at the level needed for the Story 2 verification
run. Story 3 added cost-budget wiring + per-run cost log. Stories 4-5
will add model tiering and the CrewAI removal.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import orjson

from src.agent_sdk.stage3_runner import (
    DEFAULT_GRAPHICS_MODEL,
    DEFAULT_WRITER_MODEL,
    run_stage3,
)
from src.agent_sdk.stage4_runner import run_stage4
from src.telemetry.roi_tracker import ROITracker, get_tracker

logger = logging.getLogger(__name__)

COST_LOG_PATH = Path("logs/agent_sdk_costs.jsonl")

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
    args = parser.parse_args()
    topic = (
        " ".join(args.topic)
        if args.topic
        else "the productivity paradox of AI coding assistants"
    )
    print(f"Running Agent SDK pipeline on: {topic}")
    print(f"  Models: writer={args.writer_model}, graphics={args.graphics_model}")
    print(
        f"  Budgets: writer ${args.writer_budget:.2f}, "
        f"graphics ${args.graphics_budget:.2f}",
    )

    start = time.perf_counter()
    result = asyncio.run(
        run_pipeline(
            topic,
            writer_budget_usd=args.writer_budget,
            graphics_budget_usd=args.graphics_budget,
            writer_model=args.writer_model,
            graphics_model=args.graphics_model,
        ),
    )
    total = time.perf_counter() - start

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pipeline_article.md").write_text(result.article)
    (out_dir / "pipeline_chart.json").write_bytes(
        orjson.dumps(result.chart_data, option=orjson.OPT_INDENT_2),
    )
    metrics = {
        k: v for k, v in asdict(result).items() if k not in ("article", "chart_data")
    }
    metrics["total_wall_seconds"] = total
    (out_dir / "pipeline_metrics.json").write_bytes(
        orjson.dumps(metrics, option=orjson.OPT_INDENT_2),
    )

    print(
        f"Pipeline complete: ${result.total_cost_usd:.4f} "
        f"(writer ${result.writer_cost_usd:.4f} via {result.writer_model}, "
        f"graphics ${result.graphics_cost_usd:.4f} via {result.graphics_model}), "
        f"{total:.1f}s total (S3 {result.stage3_seconds:.1f}s + "
        f"S4 {result.stage4_seconds:.2f}s), "
        f"score={result.editorial_score}%, "
        f"gates={result.gates_passed}/5, "
        f"validator={'PASS' if result.publication_validator_passed else 'FAIL'}, "
        f"ready={result.publication_ready}, "
        f"{result.article_chars} chars.",
    )
    if not result.publication_validator_passed:
        print("Validator issues:")
        for issue in result.publication_validator_issues:
            print(f"  - {issue.get('check', '?')}: {issue.get('message', '?')}")
    print("Artefacts: logs/spike/pipeline_{article.md,chart.json,metrics.json}")


if __name__ == "__main__":
    main()
