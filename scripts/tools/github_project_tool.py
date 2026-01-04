#!/usr/bin/env python3
"""GitHub Project V2 Tooling.

This module provides tools for adding GitHub issues to Project V2 boards.
The standard GitHub MCP server does not yet support Project V2 mutations,
so this tool wraps the gh CLI to provide that capability.

Usage:
    from scripts.tools.github_project_tool import github_project_add_issue

    result = github_project_add_issue(
        project_number=1,
        issue_url="https://github.com/oviney/economist-agents/issues/42",
        owner="oviney"
    )
"""

import logging
import subprocess

from crewai_tools import tool

logger = logging.getLogger(__name__)


@tool("github_project_add_issue")
def github_project_add_issue(
    project_number: int, issue_url: str, owner: str = "oviney"
) -> str:
    """Add a GitHub Issue to a Project V2 board.

    This tool wraps the gh CLI command to add issues to Project V2 boards,
    covering a gap in the standard GitHub MCP server which does not yet
    support Project V2 mutations.

    Args:
        project_number: The integer number of the project board.
        issue_url: Full URL of the issue (e.g., https://github.com/org/repo/issues/1).
        owner: The organization or user owner of the project (default: oviney).

    Returns:
        Success message or error description.

    Examples:
        >>> result = github_project_add_issue(
        ...     project_number=1,
        ...     issue_url="https://github.com/oviney/economist-agents/issues/42"
        ... )
        >>> print(result)
        'Success: Added https://github.com/oviney/economist-agents/issues/42 to Project 1'
    """
    command = [
        "gh",
        "project",
        "item-add",
        str(project_number),
        "--owner",
        owner,
        "--url",
        issue_url,
    ]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=30
        )

        if result.returncode != 0:
            error_msg = f"Failed to add item to project: {result.stderr.strip()}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        logger.info(f"Successfully added {issue_url} to Project {project_number}")
        return f"Success: Added {issue_url} to Project {project_number}"

    except FileNotFoundError:
        msg = "GitHub CLI (gh) not found. Please install it."
        logger.error(msg)
        return f"Error: {msg}"
    except subprocess.TimeoutExpired:
        msg = "Command timed out after 30 seconds"
        logger.error(msg)
        return f"Error: {msg}"
    except Exception as e:
        msg = f"Unexpected error: {type(e).__name__}: {e}"
        logger.error(msg)
        return f"Error: {msg}"


if __name__ == "__main__":
    # Example usage for testing
    print("GitHub Project Tool - Test Mode")
    print("Tool name: github_project_add_issue")
    print(
        "\nTo test, uncomment and run with a real issue:\n"
        "# result = github_project_add_issue(\n"
        "#     project_number=1,\n"
        '#     issue_url="https://github.com/oviney/economist-agents/issues/1"\n'
        "# )\n"
        "# print(result)"
    )
