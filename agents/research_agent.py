#!/usr/bin/env python3
"""
Research Agent Module

Extracts research agent functionality from economist_agent.py
for improved modularity and testability.
"""

import sys
from pathlib import Path
from typing import Any

try:
    import orjson as json
except ImportError:
    import json

# Add scripts directory to path for imports
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from agent_reviewer import review_agent_output  # type: ignore
from governance import GovernanceTracker  # type: ignore
from llm_client import call_llm  # type: ignore

# ═══════════════════════════════════════════════════════════════════════════
# RESEARCH AGENT PROMPT
# ═══════════════════════════════════════════════════════════════════════════

RESEARCH_AGENT_PROMPT = """You are a Research Analyst preparing a briefing pack for an Economist-style article.

YOUR TASK:
Given a topic, produce a comprehensive research brief with VERIFIED data.

CRITICAL RULES:
1. Every statistic MUST have a named source (organization, report, date)
2. If you cannot verify a claim, mark it as [UNVERIFIED]
3. Prefer primary sources (surveys, reports) over secondary (blog posts, articles)
4. Flag any numbers that appear in multiple sources with different values

OUTPUT STRUCTURE:
{
  "headline_stat": {
    "value": "The single most compelling statistic",
    "source": "Exact source name",
    "year": "2024",
    "verified": true
  },
  "data_points": [
    {
      "stat": "Specific number or percentage",
      "source": "Organization/Report name",
      "year": "2024",
      "url": "Source URL if available",
      "verified": true
    }
  ],
  "trend_narrative": "2-3 sentences on the bigger picture with source references",
  "chart_data": {
    "title": "Economist-style chart title (noun phrase, not sentence)",
    "subtitle": "What the chart shows, units",
    "type": "line|bar|scatter",
    "x_label": "Years|Categories|etc",
    "y_label": "Units (%, $bn, etc)",
    "data": [{"label": "2020", "series1": 45, "series2": 12}],
    "source_line": "Sources: Name1; Name2"
  },
  "contrarian_angle": "What surprising or counterintuitive finding challenges conventional wisdom?",
  "unverified_claims": ["Any claims we couldn't source - DO NOT USE THESE"]
}

Be rigorous. Unsourced claims damage credibility."""


# ═══════════════════════════════════════════════════════════════════════════
# RESEARCH AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class ResearchAgent:
    """Research agent for gathering and validating article research data.

    This agent focuses on:
    - Gathering verified data with sources
    - Identifying chart opportunities
    - Flagging unverified claims
    - Self-validation before returning results

    Args:
        client: LLM client instance (from llm_client.create_llm_client())
        governance: Optional governance tracker for audit logging

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> agent = ResearchAgent(client)
        >>> research = agent.research("AI Testing Trends", "adoption rates, ROI")
    """

    def __init__(
        self, client: Any, governance: GovernanceTracker | None = None
    ) -> None:
        """Initialize research agent with LLM client.

        Args:
            client: LLM client instance
            governance: Optional governance tracker for logging
        """
        self.client = client
        self.governance = governance

    def research(self, topic: str, talking_points: str = "") -> dict[str, Any]:
        """Gather verified research data for an article topic.

        Args:
            topic: Article topic to research
            talking_points: Optional focus areas (e.g., "adoption rates, ROI")

        Returns:
            Dictionary containing:
                - headline_stat: Most compelling statistic
                - data_points: List of verified data points with sources
                - trend_narrative: Context and big picture
                - chart_data: Data suitable for visualization (if available)
                - contrarian_angle: Counterintuitive findings
                - unverified_claims: Claims that couldn't be sourced

        Raises:
            ValueError: If topic is invalid or too short

        Example:
            >>> research = agent.research(
            ...     "Self-Healing Tests",
            ...     "adoption rates, maintenance costs"
            ... )
            >>> print(f"Found {len(research['data_points'])} data points")
        """
        # Input validation
        if not topic or not isinstance(topic, str):
            raise ValueError(
                "[RESEARCH_AGENT] Invalid topic. Expected non-empty string, "
                f"got: {type(topic).__name__}"
            )

        if len(topic.strip()) < 5:
            raise ValueError(
                f"[RESEARCH_AGENT] Topic too short: '{topic}'. "
                "Must be at least 5 characters."
            )

        print(f"📊 Research Agent: Gathering verified data for '{topic[:50]}...'")

        # Build user prompt
        user_prompt = self._build_user_prompt(topic, talking_points)

        # Call LLM
        response_text = self._call_llm(user_prompt)

        # Parse response
        research_data = self._parse_response(response_text)

        # Log metrics
        self._log_metrics(research_data, topic)

        # Self-validate
        self._self_validate(research_data)

        # Log to governance if enabled
        if self.governance:
            self._log_to_governance(research_data, topic)

        return research_data

    def _build_user_prompt(self, topic: str, talking_points: str) -> str:
        """Build user prompt for LLM call."""
        return f"""Research this topic for an Economist-style article:

TOPIC: {topic}
FOCUS AREAS: {talking_points if talking_points else "General coverage"}

Find specific, VERIFIABLE data with exact sources. Flag anything you cannot verify."""

    def _call_llm(self, user_prompt: str) -> str:
        """Call LLM with research prompt.

        Note: This method uses the existing call_llm function from llm_client.
        It's abstracted here to allow for easier mocking in tests.
        """

        return call_llm(
            self.client, RESEARCH_AGENT_PROMPT, user_prompt, max_tokens=2500
        )

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON response from LLM.

        Handles cases where LLM wraps JSON in markdown or text.
        """
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                research_data = json.loads(response_text[start:end])
            else:
                research_data = {"raw_research": response_text, "chart_data": None}
        except json.JSONDecodeError:
            research_data = {"raw_research": response_text, "chart_data": None}

        return research_data

    def _log_metrics(self, research_data: dict[str, Any], topic: str) -> None:
        """Log research metrics to console."""
        verified = sum(
            1
            for dp in research_data.get("data_points", [])
            if dp.get("verified", False)
        )
        total = len(research_data.get("data_points", []))
        print(f"   ✓ Found {total} data points ({verified} verified)")

        if research_data.get("unverified_claims"):
            print(
                f"   ⚠ {len(research_data['unverified_claims'])} unverified claims flagged"
            )

    def _self_validate(self, research_data: dict[str, Any]) -> None:
        """Run self-validation on research output."""
        print("   🔍 Self-validating research...")
        is_valid, issues = review_agent_output("research_agent", research_data)

        if not is_valid:
            print(f"   ⚠️  Research has {len(issues)} quality issues")
            # Don't regenerate research - flag for human review
            # Research is expensive and regeneration may not help
            for issue in issues[:3]:  # Show first 3 issues
                print(f"     • {issue}")
        else:
            print("   ✅ Research passed self-validation")

    def _log_to_governance(self, research_data: dict[str, Any], topic: str) -> None:
        """Log research output to governance system."""
        if not self.governance:
            return

        verified = sum(
            1
            for dp in research_data.get("data_points", [])
            if dp.get("verified", False)
        )
        total = len(research_data.get("data_points", []))

        # Get validation results
        is_valid, issues = review_agent_output("research_agent", research_data)

        self.governance.log_agent_output(
            "research_agent",
            research_data,
            metadata={
                "topic": topic,
                "data_points": total,
                "verified": verified,
                "unverified": len(research_data.get("unverified_claims", [])),
                "validation_passed": is_valid,
                "validation_issues": len(issues),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def run_research_agent(
    client: Any,
    topic: str,
    talking_points: str = "",
    governance: GovernanceTracker | None = None,
) -> dict[str, Any]:
    """Run research agent (backward compatibility wrapper).

    This function maintains 100% backward compatibility with the original
    run_research_agent() function from economist_agent.py.

    Args:
        client: LLM client instance
        topic: Article topic to research
        talking_points: Optional focus areas
        governance: Optional governance tracker

    Returns:
        Research data dictionary

    Raises:
        ValueError: If topic is invalid

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> research = run_research_agent(client, "AI Testing")
    """
    agent = ResearchAgent(client, governance)
    return agent.research(topic, talking_points)
