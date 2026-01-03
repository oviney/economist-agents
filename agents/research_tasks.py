#!/usr/bin/env python3
"""
Research Agent Tasks

CrewAI-compatible task definitions for the Research Agent.
These tasks can be used with CrewAI's Task class or standalone.
"""

from typing import Any

from agents.research_agent import ResearchAgent


def create_research_task_config(
    topic: str, talking_points: str = "", expected_output: str = None
) -> dict[str, Any]:
    """Create a CrewAI-compatible task configuration for research.

    Args:
        topic: Article topic to research
        talking_points: Optional focus areas
        expected_output: Description of expected output format

    Returns:
        Dictionary with task configuration suitable for CrewAI Task class

    Example:
        >>> from crewai import Task, Agent
        >>> config = create_research_task_config(
        ...     "AI Testing Trends",
        ...     "adoption rates, ROI"
        ... )
        >>> task = Task(**config, agent=research_agent)
    """
    if expected_output is None:
        expected_output = """A comprehensive research brief with:
- headline_stat: Most compelling statistic with source
- data_points: List of verified data points (each with source, year, URL)
- trend_narrative: 2-3 sentences on the bigger picture
- chart_data: Visualization-ready data (if available)
- contrarian_angle: Counterintuitive findings
- unverified_claims: Claims that couldn't be sourced (flagged)"""

    description = f"""Research the topic "{topic}" for an Economist-style article.

Focus areas: {talking_points if talking_points else "General coverage"}

Critical requirements:
1. Every statistic MUST have a named source (organization, report, date)
2. Mark unverifiable claims as [UNVERIFIED]
3. Prefer primary sources (surveys, reports) over secondary sources
4. Flag numbers that appear in multiple sources with different values

The research should identify:
- Compelling statistics and trends
- Chart opportunities with quantitative data
- Contrarian or counterintuitive angles
- Source attribution for all claims"""

    return {
        "description": description,
        "expected_output": expected_output,
        "context": {
            "topic": topic,
            "talking_points": talking_points,
        },
    }


def execute_research_task(
    client: Any, topic: str, talking_points: str = "", governance: Any | None = None
) -> dict[str, Any]:
    """Execute research task directly (non-CrewAI mode).

    This function provides a simple interface for running research
    without CrewAI orchestration.

    Args:
        client: LLM client instance
        topic: Article topic to research
        talking_points: Optional focus areas
        governance: Optional governance tracker

    Returns:
        Research data dictionary

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> research = execute_research_task(client, "AI Testing")
    """
    agent = ResearchAgent(client, governance)
    return agent.research(topic, talking_points)


# ═══════════════════════════════════════════════════════════════════════════
# CREWAI TOOL DEFINITIONS (Future Enhancement)
# ═══════════════════════════════════════════════════════════════════════════

# Note: These tools can be implemented when CrewAI integration is complete
# in Sprint 7 Story 3. For now, they serve as placeholders showing the
# intended structure.


def research_tool_config() -> dict[str, Any]:
    """Configuration for research agent as a CrewAI tool.

    Returns:
        Tool configuration dictionary for CrewAI

    Note:
        This is a placeholder for future CrewAI integration.
        Actual implementation will follow Sprint 7 Story 3 patterns.
    """
    return {
        "name": "research_economist_article",
        "description": "Research and gather verified data for an Economist-style article. "
        "Returns data points with sources, chart opportunities, and contrarian angles.",
        "parameters": {
            "topic": {
                "type": "string",
                "description": "Article topic to research",
                "required": True,
            },
            "talking_points": {
                "type": "string",
                "description": "Optional focus areas (e.g., 'adoption rates, ROI')",
                "required": False,
            },
        },
    }
