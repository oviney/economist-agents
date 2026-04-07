#!/usr/bin/env python3
"""Article Evaluator MCP Server (Story 18.1).

Exposes ArticleEvaluator.evaluate() as an MCP tool so that any agent
(CrewAI, Claude Code, or future framework) can score articles without
importing Python modules directly.

Usage (stdio transport — default):
    python3 mcp_servers/article_evaluator_server.py

Usage (HTTP transport):
    MCP_TRANSPORT=http python3 mcp_servers/article_evaluator_server.py
"""

import logging
import os
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

# Passing score threshold (percentage).
_PASS_THRESHOLD: float = 60.0


@mcp.tool()
def evaluate_article(content: str, title: str = "") -> dict[str, Any]:
    """Evaluate an article and return a quality score.

    Scores the supplied article markdown deterministically on 5 quality
    dimensions and returns a simplified pass/fail verdict suitable for
    pipeline gate decisions.

    Args:
        content: Full article text, optionally with YAML frontmatter.
        title: Optional article title.  Included in feedback when provided
               and frontmatter is absent; does not affect numeric scoring.

    Returns:
        Dictionary containing:
            score    – quality percentage as a float (0.0 – 100.0)
            feedback – per-dimension feedback messages (list[str])
            pass     – True when score >= 60.0 (bool)

        On invalid input an ``error`` key is added to the returned dict
        and all numeric fields are reset to zero.  This function never raises.
    """
    if not isinstance(content, str):
        return {
            "error": "content must be a string",
            "score": 0.0,
            "feedback": [],
            "pass": False,
        }

    stripped = content.strip()
    if not stripped:
        return {
            "error": "content must not be empty",
            "score": 0.0,
            "feedback": [],
            "pass": False,
        }

    try:
        result = _evaluator.evaluate(stripped)
        score = float(result.percentage)

        feedback: list[str] = list(result.details.values())
        clean_title = title.strip()
        if clean_title:
            feedback.insert(0, f"Title: {clean_title}")

        return {
            "score": score,
            "feedback": feedback,
            "pass": score >= _PASS_THRESHOLD,
        }
    except Exception as exc:
        logger.exception("evaluate_article failed: %s", exc)
        return {
            "error": str(exc),
            "score": 0.0,
            "feedback": [],
            "pass": False,
        }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
