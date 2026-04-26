"""End-to-end Agent SDK pipeline: Stage 3 (LLM) + Stage 4 (deterministic).

Mirrors the CrewAI flow at the level needed for the Story 2 verification
run. Story 3-5 will add cost-budget wiring, model tiering, and the
CrewAI removal.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import orjson

from src.agent_sdk.stage3_runner import run_stage3_spike
from src.agent_sdk.stage4_runner import run_stage4

logger = logging.getLogger(__name__)


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
    stage3_seconds: float
    stage4_seconds: float
    article_chars: int


async def run_pipeline(topic: str) -> PipelineResult:
    """Generate one article through the Agent SDK pipeline."""
    stage3 = await run_stage3_spike(topic)
    stage4 = run_stage4(stage3.article, stage3.chart_data)

    return PipelineResult(
        topic=topic,
        article=stage4.article,
        chart_data=stage3.chart_data,
        editorial_score=stage4.editorial_score,
        gates_passed=stage4.gates_passed,
        publication_ready=stage4.publication_ready,
        publication_validator_passed=stage4.publication_validator_passed,
        publication_validator_issues=stage4.publication_validator_issues,
        total_cost_usd=stage3.total_cost_usd,
        stage3_seconds=stage3.wall_seconds,
        stage4_seconds=stage4.wall_seconds,
        article_chars=len(stage4.article),
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    topic = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "the productivity paradox of AI coding assistants"
    )
    print(f"Running Agent SDK pipeline on: {topic}")

    start = time.perf_counter()
    result = asyncio.run(run_pipeline(topic))
    total = time.perf_counter() - start

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pipeline_article.md").write_text(result.article)
    (out_dir / "pipeline_chart.json").write_bytes(
        orjson.dumps(result.chart_data, option=orjson.OPT_INDENT_2)
    )
    metrics = {
        k: v for k, v in asdict(result).items() if k not in ("article", "chart_data")
    }
    metrics["total_wall_seconds"] = total
    (out_dir / "pipeline_metrics.json").write_bytes(
        orjson.dumps(metrics, option=orjson.OPT_INDENT_2)
    )

    print(
        f"Pipeline complete: ${result.total_cost_usd:.4f}, "
        f"{total:.1f}s total (S3 {result.stage3_seconds:.1f}s + "
        f"S4 {result.stage4_seconds:.2f}s), "
        f"score={result.editorial_score}%, "
        f"gates={result.gates_passed}/5, "
        f"validator={'PASS' if result.publication_validator_passed else 'FAIL'}, "
        f"ready={result.publication_ready}, "
        f"{result.article_chars} chars."
    )
    if not result.publication_validator_passed:
        print("Validator issues:")
        for issue in result.publication_validator_issues:
            print(f"  - {issue.get('check', '?')}: {issue.get('message', '?')}")
    print("Artefacts: logs/spike/pipeline_{article.md,chart.json,metrics.json}")


if __name__ == "__main__":
    main()
