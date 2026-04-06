#!/usr/bin/env python3
"""Orchestrator MCP Server.

Exposes the orchestrator agent's PR triage and dispatch decision logic
as MCP tools so that any agent (Claude Code, CrewAI, or a GitHub Actions
workflow) can call them over stdio without importing Python modules directly.

Tools:
    check_pr_ready:       Is this PR done enough to promote?
    triage_duplicates:    Which of two duplicate PRs should we keep?
    check_dispatch_safe:  Should we dispatch this issue now?
    check_stalled:        Is this agent stalled or just slow?

Usage (stdio transport):
    python3 mcp_servers/orchestrator_server.py
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure project root is importable when run directly.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from scripts.orchestrator_agent import (  # noqa: E402
    check_dispatch_safe,
    check_pr_ready,
    check_stalled,
    triage_duplicates,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("orchestrator")


@mcp.tool()
def check_pr_ready_tool(pr_url: str) -> dict[str, Any]:
    """Check whether a pull request is ready to be promoted.

    Fetches the PR diff and evaluates: substantive code changes,
    absence of TODO/FIXME markers, non-trivial description with issue
    reference, and presence of test files.

    Args:
        pr_url: Full GitHub pull-request URL,
            e.g. https://github.com/owner/repo/pull/123

    Returns:
        Dictionary with keys:
            promote (bool): Whether the PR is ready to promote.
            reason  (str):  Human-readable explanation.
            details (dict): Granular sub-checks.

        On error an ``error`` key is present and promote is False.
    """
    try:
        return check_pr_ready(pr_url)
    except Exception as exc:
        logger.exception("check_pr_ready_tool failed: %s", exc)
        return {"error": str(exc), "promote": False, "reason": "Failed to check PR readiness", "details": {}}


@mcp.tool()
def triage_duplicates_tool(pr_a_url: str, pr_b_url: str) -> dict[str, Any]:
    """Recommend which of two duplicate PRs to keep.

    Scores each PR on files changed, test coverage, description
    completeness, and commit count.  The higher-scoring PR is kept.

    Args:
        pr_a_url: Full GitHub URL for the first PR candidate.
        pr_b_url: Full GitHub URL for the second PR candidate.

    Returns:
        Dictionary with keys:
            keep   (str):  "pr-a" or "pr-b" — the PR to retain.
            close  (str):  "pr-a" or "pr-b" — the PR to close.
            reason (str):  Human-readable explanation.
            scores (dict): Numeric scores for each PR.
            details(dict): Sub-scores for each PR.

        On error an ``error`` key is present.
    """
    try:
        return triage_duplicates(pr_a_url, pr_b_url)
    except Exception as exc:
        logger.exception("triage_duplicates_tool failed: %s", exc)
        return {"error": str(exc), "keep": None, "close": None, "reason": "Failed to triage duplicate PRs"}


@mcp.tool()
def check_dispatch_safe_tool(issue_url: str) -> dict[str, Any]:
    """Determine whether a backlog issue is safe to dispatch to an agent.

    Checks blocking labels, active agent PR capacity (max 6), and
    explicit dependency mentions in the issue body.

    Args:
        issue_url: Full GitHub issue URL,
            e.g. https://github.com/owner/repo/issues/42

    Returns:
        Dictionary with keys:
            dispatch (bool): Whether it is safe to dispatch.
            reason   (str):  Human-readable explanation.
            details  (dict): Granular sub-checks.

        On error an ``error`` key is present and dispatch is False.
    """
    try:
        return check_dispatch_safe(issue_url)
    except Exception as exc:
        logger.exception("check_dispatch_safe_tool failed: %s", exc)
        return {"error": str(exc), "dispatch": False, "reason": "Failed to check dispatch safety", "details": {}}


@mcp.tool()
def check_stalled_tool(pr_url: str, idle_minutes: int) -> dict[str, Any]:
    """Determine whether an agent PR is stalled or just working on a slow task.

    Infers task complexity from PR labels and file count, then compares
    elapsed idle time against complexity-appropriate thresholds:
    low (30 min), medium (60 min), high (90 min).

    Args:
        pr_url: Full GitHub pull-request URL.
        idle_minutes: Minutes the PR has been idle (no new commits/comments).

    Returns:
        Dictionary with keys:
            stalled (bool): Whether the PR is considered stalled.
            reason  (str):  Human-readable explanation.
            details (dict): Complexity, thresholds, file count.

        On error an ``error`` key is present and stalled is False.
    """
    try:
        return check_stalled(pr_url, idle_minutes)
    except Exception as exc:
        logger.exception("check_stalled_tool failed: %s", exc)
        return {"error": str(exc), "stalled": False, "reason": "Failed to check stall status", "details": {}}


if __name__ == "__main__":
    mcp.run(transport="stdio")
