"""
Custom CrewAI tools for the economist-agents system.

This package contains custom tool implementations that extend CrewAI's
capabilities with project-specific functionality.
"""

from scripts.tools.github_project_tool import (
    GitHubProjectTool,
    github_project_add_issue,
)

__all__ = ["github_project_add_issue", "GitHubProjectTool"]
