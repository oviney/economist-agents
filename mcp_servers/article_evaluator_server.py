#!/usr/bin/env python3
"""Article Evaluator MCP Server (Story 18.1).

Exposes ArticleEvaluator.evaluate() as an MCP tool so that any agent
(CrewAI, Claude Code, or future framework) can score articles without
importing Python modules directly.

Usage (stdio transport):
    python3 mcp_servers/article_evaluator_server.py
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path when run directly.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from scripts.article_evaluator import ArticleEvaluator  # noqa: E402

logger = logging.getLogger(__name__)

mcp = FastMCP("article-evaluator")

_evaluator = ArticleEvaluator()


@mcp.tool()
def evaluate_article(content: str) -> dict[str, Any]:
    """Evaluate an article across 5 quality dimensions.

    Scores the supplied article markdown deterministically on:
    - opening_quality   (1–10)
    - evidence_sourcing (1–10)
    - voice_consistency (1–10)
    - structure         (1–10)
    - visual_engagement (1–10)

    Args:
        content: Full article text, optionally with YAML frontmatter.

    Returns:
        Dictionary containing:
            scores      – per-dimension scores (dict[str, int])
            total_score – sum of all dimension scores (int)
            max_score   – maximum possible score, always 50 (int)
            percentage  – total_score / max_score * 100, rounded (int)
            details     – per-dimension textual feedback (dict[str, str])

        On invalid input an ``error`` key is added to the returned dict
        and all numeric fields are set to zero.  This function never raises.
    """
    if not isinstance(content, str):
        return {
            "error": "content must be a string",
            "scores": {},
            "total_score": 0,
            "max_score": 50,
            "percentage": 0,
            "details": {},
        }

    stripped = content.strip()
    if not stripped:
        return {
            "error": "content must not be empty",
            "scores": {},
            "total_score": 0,
            "max_score": 50,
            "percentage": 0,
            "details": {},
        }

    try:
        result = _evaluator.evaluate(stripped)
        return {
            "scores": result.scores,
            "total_score": result.total_score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "details": result.details,
        }
    except Exception as exc:
        logger.exception("evaluate_article failed: %s", exc)
        return {
            "error": str(exc),
            "scores": {},
            "total_score": 0,
            "max_score": 50,
            "percentage": 0,
            "details": {},
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
