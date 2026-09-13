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

from scripts.publication_validator import PublicationValidator
from src.agent_sdk._shared import apply_editorial_fixes as _apply_editorial_fixes

logger = logging.getLogger(__name__)


@dataclass
class Stage4Result:
    """Output of the Agent SDK Stage 4 run."""

    article: str
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    wall_seconds: float


def run_stage4(
    article: str,
    chart_data: dict[str, Any] | None = None,
) -> Stage4Result:
    """Polish the article deterministically, then run the publication validator.

    B-048 D4: there is no editorial score. The validator's CRITICAL findings are
    the invariants a reader would be harmed by (no unsourced number, links that
    resolve, no placeholder or reviewer comment, a frontmatter Jekyll can build);
    everything else it reports is advisory and goes to the review packet for the
    owner, who reads every draft anyway.

    Args:
        article: Raw article text from Stage 3 (with YAML frontmatter).
        chart_data: Accepted for call-site compatibility; unused (the pipeline
            draws nothing, B-042).
    """
    del chart_data
    start = time.perf_counter()
    polished = _apply_editorial_fixes(
        article,
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )
    validator = PublicationValidator()
    validator_passed, validator_issues = validator.validate(polished)
    elapsed = time.perf_counter() - start
    return Stage4Result(
        article=polished,
        publication_ready=validator_passed,
        publication_validator_passed=validator_passed,
        publication_validator_issues=validator_issues,
        wall_seconds=elapsed,
    )


def main() -> None:
    """CLI entrypoint — read an article from a file and run Stage 4."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
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
                "publication_ready": result.publication_ready,
                "publication_validator_passed": result.publication_validator_passed,
                "publication_validator_issues": result.publication_validator_issues,
                "wall_seconds": result.wall_seconds,
                "article_chars": len(result.article),
            },
            option=orjson.OPT_INDENT_2,
        ),
    )
    print(
        f"Stage 4 complete: validator={'PASS' if result.publication_validator_passed else 'FAIL'}, "
        f"publication_ready={result.publication_ready}, "
        f"{result.wall_seconds:.2f}s.",
    )


if __name__ == "__main__":
    main()
