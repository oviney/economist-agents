"""Stage 4 on the Anthropic Agent SDK — deterministic gates only.

Replaces ``src/crews/stage4_crew.py`` for the Phase 2 migration
(ADR-0006, epic #308, story #310). The CrewAI Stage 4 LLM Reviewer is
deliberately omitted here — it adds no value (50% JSON parse failure
on Claude per the 2026-04-21 sprint memo) and the deterministic
``ArticleEvaluator`` already produces a usable score with no LLM call.

This module is the cheapest possible Stage 4: apply the same
deterministic editorial fixes the existing pipeline uses, then score
the result with ``ArticleEvaluator``.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson

from scripts.article_evaluator import ArticleEvaluator
from scripts.publication_validator import PublicationValidator
from src.agent_sdk._shared import apply_editorial_fixes as _apply_editorial_fixes

logger = logging.getLogger(__name__)


@dataclass
class Stage4Result:
    """Output of the Agent SDK Stage 4 run."""

    article: str
    editorial_score: int
    gates_passed: int
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    score_details: dict[str, int]
    wall_seconds: float


def run_stage4(
    article: str,
    chart_data: dict[str, Any] | None = None,
    publish_threshold: int = 70,
) -> Stage4Result:
    """Polish the article and score it deterministically.

    Args:
        article: Raw article text from Stage 3 (with YAML frontmatter).
        chart_data: Chart spec dict from Stage 3 (used only by callers
            that need to render the chart; this stage does not generate
            images).
        publish_threshold: Minimum percentage to mark publication-ready.
            Default 70 matches ``PUBLISH_THRESHOLD`` in the live pipeline.

    Returns:
        Stage4Result containing polished article, score, gates passed,
        and a publication-ready flag.
    """
    del chart_data
    start = time.perf_counter()

    polished = _apply_editorial_fixes(
        article,
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )

    evaluator = ArticleEvaluator()
    eval_result = evaluator.evaluate(polished)
    score = eval_result.percentage
    gates_passed = sum(1 for v in eval_result.scores.values() if v >= 7)

    validator = PublicationValidator()
    validator_passed, validator_issues = validator.validate(polished)

    elapsed = time.perf_counter() - start
    return Stage4Result(
        article=polished,
        editorial_score=score,
        gates_passed=gates_passed,
        publication_ready=score >= publish_threshold and validator_passed,
        publication_validator_passed=validator_passed,
        publication_validator_issues=validator_issues,
        score_details=dict(eval_result.scores),
        wall_seconds=elapsed,
    )


def main() -> None:
    """CLI entrypoint — read an article from a file and run Stage 4."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    if len(sys.argv) < 2:
        print("Usage: python -m src.agent_sdk.stage4_runner <article.md>")
        sys.exit(1)

    article_path = Path(sys.argv[1])
    article = article_path.read_text()
    result = run_stage4(article)

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stage4_polished.md").write_text(result.article)
    (out_dir / "stage4_metrics.json").write_bytes(
        orjson.dumps(
            {
                "editorial_score": result.editorial_score,
                "gates_passed": result.gates_passed,
                "publication_ready": result.publication_ready,
                "publication_validator_passed": result.publication_validator_passed,
                "publication_validator_issues": result.publication_validator_issues,
                "score_details": result.score_details,
                "wall_seconds": result.wall_seconds,
                "article_chars": len(result.article),
            },
            option=orjson.OPT_INDENT_2,
        )
    )
    print(
        f"Stage 4 complete: score={result.editorial_score}%, "
        f"gates={result.gates_passed}/5, "
        f"validator={'PASS' if result.publication_validator_passed else 'FAIL'}, "
        f"publication_ready={result.publication_ready}, "
        f"{result.wall_seconds:.2f}s."
    )


if __name__ == "__main__":
    main()
