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

from crewai.tools import tool

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


def _github_project_add_issue_impl(
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
    # Enhanced input validation with type checking
    if not isinstance(project_number, int):
        raise TypeError(
            f"project_number must be an integer, got {type(project_number).__name__}"
        )

    if project_number < 1:
        return "Error: Invalid project number. Must be a positive integer."

    if not isinstance(issue_url, str):
        raise TypeError(f"issue_url must be a string, got {type(issue_url).__name__}")

    if not _validate_github_issue_url(issue_url):
        return "Error: Invalid GitHub issue URL format. Must be https://github.com/owner/repo/issues/number"

    if not isinstance(owner, str):
        raise TypeError(f"owner must be a string, got {type(owner).__name__}")

    if not owner.strip():
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


class CallableTool:
    """Wrapper to make CrewAI tools callable like functions"""

    def __init__(self, tool, original_func):
        self.tool = tool
        self._original_func = original_func
        # Expose all tool attributes
        for attr in ["name", "__doc__", "description"]:
            if hasattr(tool, attr):
                setattr(self, attr, getattr(tool, attr))

        # Make inspect.getsource work by exposing the original function's attributes
        for attr in ["__module__", "__qualname__", "__annotations__"]:
            if hasattr(original_func, attr):
                setattr(self, attr, getattr(original_func, attr))

    def __call__(self, *args, **kwargs):
        # Use the tool's run method
        return self.tool.run(*args, **kwargs)

    def __getattr__(self, name):
        # For inspect operations, try the original function first
        if hasattr(self._original_func, name):
            return getattr(self._original_func, name)
        # Delegate any other attributes to the underlying tool
        return getattr(self.tool, name)

    # Make this object appear like the original function to inspect
    @property
    def __wrapped__(self):
        return self._original_func

    # Override inspect-related attributes to point to original function
    @property
    def __code__(self):
        return self._original_func.__code__

    @property
    def __globals__(self):
        return self._original_func.__globals__


# Create the decorated tool and make it callable
_tool_instance = tool("github_project_add_issue")(_github_project_add_issue_impl)
_tool_instance.__doc__ = _github_project_add_issue_impl.__doc__
github_project_add_issue = CallableTool(_tool_instance, _github_project_add_issue_impl)

# Export the raw function for direct calling if needed
github_project_add_issue_raw = _github_project_add_issue_impl

# Export as class name for backward compatibility
GitHubProjectTool = github_project_add_issue


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
