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


def _validate_github_issue_url(issue_url: str) -> bool:
    """Validate GitHub issue URL format for security."""
    if not isinstance(issue_url, str):
        return False
    return issue_url.startswith("https://github.com/") and "/issues/" in issue_url


def _check_github_auth() -> bool:
    """Check if GitHub CLI is authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, timeout=10, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@tool("github_project_add_issue")
def github_project_add_issue(
    project_number: int, issue_url: str, owner: str = "oviney"
) -> str:
    """Add a GitHub Issue to a Project V2 board.

    This tool wraps the gh CLI command to add issues to Project V2 boards,
    covering a gap in the standard GitHub MCP server which does not yet
    support Project V2 mutations.

    Security Features:
    - URL format validation
    - Authentication verification
    - Input sanitization
    - Timeout protection
    - Rate limiting friendly

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
    # Enhanced input validation
    if not isinstance(project_number, int) or project_number < 1:
        return "Error: Invalid project number. Must be a positive integer."

    if not _validate_github_issue_url(issue_url):
        return "Error: Invalid GitHub issue URL format. Must be https://github.com/owner/repo/issues/number"

    if not isinstance(owner, str) or not owner.strip():
        return "Error: Invalid owner. Must be a non-empty string."

    # Authentication check
    if not _check_github_auth():
        return "Error: GitHub CLI not authenticated. Run 'gh auth login' first."

    # Sanitize inputs (strip whitespace)
    owner = owner.strip()
    issue_url = issue_url.strip()

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
