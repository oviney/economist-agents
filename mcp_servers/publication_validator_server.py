#!/usr/bin/env python3
"""
Publication Validator MCP Server

Exposes the PublicationValidator quality gate as an MCP tool so that any
agent in the content pipeline can validate articles before publication.

Transport: stdio (default FastMCP behaviour)
"""

import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure the repo root is on sys.path so the scripts package is importable
# when the server is launched directly (mirrors run.sh behaviour).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.publication_validator import PublicationValidator  # noqa: E402

logger = logging.getLogger(__name__)

mcp = FastMCP("publication-validator")


@mcp.tool()
def validate_for_publication(
    content: str,
    expected_date: str | None = None,
) -> dict:
    """Validate an article against publication quality gates.

    Wraps ``PublicationValidator.validate()`` and returns a structured
    result suitable for consumption by downstream agents.

    Args:
        content: Full article text including YAML front matter.
        expected_date: Expected publication date in ``YYYY-MM-DD`` format.
            Defaults to today's date when omitted.

    Returns:
        A dictionary with the following keys:

        * ``is_valid`` (bool): ``True`` when no CRITICAL issues were found.
        * ``issues`` (list[dict]): Zero or more issue dictionaries, each
          containing at minimum ``check``, ``severity``, and ``message``
          keys as produced by :class:`~scripts.publication_validator.PublicationValidator`.
    """
    logger.info(
        "validate_for_publication called: expected_date=%s, content_length=%d",
        expected_date,
        len(content),
    )

    validator = PublicationValidator(expected_date=expected_date)
    try:
        is_valid, issues = validator.validate(content)
    except Exception as exc:
        logger.exception("validate_for_publication failed: %s", exc)
        return {
            "is_valid": False,
            "issues": [
                {
                    "check": "validator_error",
                    "severity": "CRITICAL",
                    "message": str(exc),
                }
            ],
        }

    logger.info(
        "Validation complete: is_valid=%s, issue_count=%d", is_valid, len(issues)
    )

    return {"is_valid": is_valid, "issues": issues}


if __name__ == "__main__":
    mcp.run(transport="stdio")
