#!/usr/bin/env python3
"""
Writer Agent Module

Extracts writer agent functionality from economist_agent.py
for improved modularity and testability.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any

try:
    import orjson  # noqa: F401

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

import json as json_stdlib  # Always have standard json for formatting

# Add scripts directory to path for imports
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from agent_loader import (  # noqa: E402
    load_content_agent as _load_content_agent,  # type: ignore
)
from agent_reviewer import review_agent_output  # type: ignore  # noqa: E402
from governance import GovernanceTracker  # type: ignore  # noqa: E402
from llm_client import call_llm  # type: ignore  # noqa: E402

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# WRITER AGENT PROMPT
# ═══════════════════════════════════════════════════════════════════════════

_writer_config = _load_content_agent("writer")
WRITER_AGENT_PROMPT = _writer_config.system_message


# ═══════════════════════════════════════════════════════════════════════════
# WRITER AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class WriterAgent:
    """Writer agent for drafting Economist-style articles.

    This agent focuses on:
    - Writing engaging, data-driven articles
    - Following Economist style guidelines
    - Embedding charts naturally
    - Self-validation before returning drafts

    Args:
        client: LLM client instance (from llm_client.create_llm_client())
        governance: Optional governance tracker for audit logging

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> agent = WriterAgent(client)
        >>> draft, metadata = agent.write(
        ...     topic="AI Testing Trends",
        ...     research_brief={...},
        ...     current_date="2026-01-02"
        ... )
    """

    def __init__(self, client: Any, governance: GovernanceTracker | None = None):
        """Initialize the writer agent.

        Args:
            client: LLM client for generating articles
            governance: Optional governance tracker for logging
        """
        self.client = client
        self.governance = governance

    @staticmethod
    def _ensure_frontmatter(draft: str) -> str:
        """Programmatically fix known YAML frontmatter issues.

        Repairs missing opening ``---`` delimiter and strips code-fence
        wrappers so downstream validators always receive well-formed
        frontmatter.  This is a deterministic safety net — the LLM
        prompt already requests correct formatting, but LLMs are not
        guaranteed to comply.

        Args:
            draft: Raw article text from LLM.

        Returns:
            Article text with corrected frontmatter delimiters.
        """
        text = draft.strip()

        # Strip ```yaml / ```yml code-fence wrapper
        if text.startswith("```yaml") or text.startswith("```yml"):
            # Remove opening fence line
            text = re.sub(r"^```ya?ml\s*\n", "", text, count=1)
            # Remove trailing ``` that closed the fence (if present)
            text = re.sub(r"\n```\s*$", "", text, count=1)
            # The content now likely starts with YAML fields — fall through
            # to the missing-opener check below.

        # If the article already starts with ---, nothing to do
        if text.startswith("---"):
            return text

        # Heuristic: looks like YAML fields without the opening ---
        yaml_field_pattern = re.compile(
            r"^(layout|title|date|author|categories|description|image)\s*:",
            re.MULTILINE,
        )
        if yaml_field_pattern.match(text):
            logger.warning("Frontmatter missing opening '---' — prepending delimiter")
            text = "---\n" + text

        return text

    def write(
        self,
        topic: str,
        research_brief: dict[str, Any],
        current_date: str,
        chart_filename: str | None = None,
        featured_image: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Write an Economist-style article based on research brief.

        Args:
            topic: Article topic
            research_brief: Research data from research agent
            current_date: Date to use in YAML frontmatter (YYYY-MM-DD)
            chart_filename: Optional chart filename to embed
            featured_image: Optional featured image path

        Returns:
            Tuple of (article_text, metadata_dict)
            - article_text: Complete markdown with YAML frontmatter
            - metadata_dict: Validation results
                * is_valid: Whether draft passed validation
                * regenerated: Whether draft was regenerated
                * critical_issues: Count of critical issues found

        Raises:
            ValueError: If inputs are invalid

        Example:
            >>> draft, metadata = agent.write(
            ...     topic="Self-Healing Tests",
            ...     research_brief={"headline_stat": {...}, ...},
            ...     current_date="2026-01-02",
            ...     chart_filename="/assets/charts/testing.png"
            ... )
            >>> print(f"Valid: {metadata['is_valid']}")
            >>> print(f"Word count: {len(draft.split())}")
        """
        # Input validation
        if not topic or not isinstance(topic, str):
            raise ValueError(
                "[WRITER_AGENT] Invalid topic. Expected non-empty string, "
                f"got: {type(topic).__name__}"
            )

        if not isinstance(research_brief, dict):
            raise ValueError(
                "[WRITER_AGENT] Invalid research_brief. Expected dict, "
                f"got: {type(research_brief).__name__}"
            )

        if not research_brief:
            raise ValueError(
                "[WRITER_AGENT] Empty research_brief. Cannot write without research data."
            )

        print(f"✍️  Writer Agent: Drafting article on '{topic[:50]}...'")

        # Build system prompt by replacing placeholders
        system_prompt = WRITER_AGENT_PROMPT.replace("{current_date}", current_date)

        # Add chart information if available
        if chart_filename and research_brief.get("chart_data"):
            chart_title = research_brief["chart_data"].get("title", "Chart")
            chart_info = f"""

═══════════════════════════════════════════════════════════════════════════
⚠️  CHART EMBEDDING REQUIRED ⚠️
═══════════════════════════════════════════════════════════════════════════

A chart has been generated for this article. You MUST include it using this EXACT markdown:

![{chart_title}]({chart_filename})

Place this markdown in the article body after discussing the relevant data.
Add a sentence referencing it: "As the chart shows, [observation]..."

Failure to include the chart will result in article rejection.
═══════════════════════════════════════════════════════════════════════════
"""
            system_prompt = system_prompt.replace(
                "{research_brief}",
                json_stdlib.dumps(research_brief, indent=2) + chart_info,
            )
        else:
            system_prompt = system_prompt.replace(
                "{research_brief}", json_stdlib.dumps(research_brief, indent=2)
            )

        # Add references information from research data
        references_info = self._format_references_guidance(research_brief)
        if references_info:
            system_prompt += references_info

        # Add featured image to front matter if available
        if featured_image:
            featured_image_note = f"""

⚠️  FEATURED IMAGE AVAILABLE ⚠️
Add this line to the YAML front matter:
image: {featured_image}

Example:
---
layout: post
title: "Article Title In Title Case"
date: {current_date}
author: "Ouray Viney"
categories: ["quality-engineering"]
description: "Brief SEO summary ≤160 chars"
image: {featured_image}
---
"""
            system_prompt += featured_image_note

        # Generate initial draft
        draft = call_llm(
            self.client,
            system_prompt,
            f"⚠️  REMEMBER: Use date: {current_date} in YAML front matter.\n\nWrite an Economist-style article on: {topic}",
            max_tokens=3000,
        )
        # Deterministic fix for BUG-028: ensure opening --- is present
        draft = self._ensure_frontmatter(draft)
        word_count = len(draft.split())
        print(f"   ✓ Draft complete ({word_count} words)")

        # SELF-VALIDATION: Review draft before returning
        print("   🔍 Self-validating draft...")
        is_valid, issues = review_agent_output(
            "writer_agent", draft, context={"chart_filename": chart_filename}
        )

        critical_issues = []
        regenerated = False  # Track whether regeneration occurred
        # If validation fails and issues are critical, attempt one regeneration
        if not is_valid:
            critical_issues = [i for i in issues if "CRITICAL" in i or "BANNED" in i]
            if critical_issues:
                print(
                    f"   ⚠️  {len(critical_issues)} critical issues found, regenerating..."
                )

                # Create fix instructions — targeted guidance for word count failures
                word_count_issues = [
                    i for i in critical_issues if "too short" in i.lower()
                ]
                current_words = 0
                if word_count_issues:
                    import re as _re

                    m = _re.search(r"(\d+) words", word_count_issues[0])
                    current_words = int(m.group(1)) if m else 0

                fix_lines = ["CRITICAL FIXES REQUIRED:"]
                for issue in critical_issues[:5]:
                    if "too short" in issue.lower() and current_words:
                        needed = max(900 - current_words, 150)
                        fix_lines.append(
                            f"- WORD COUNT: Article is only {current_words} words. "
                            f"You MUST add at least {needed} more words. "
                            "Expand by: (1) adding a concrete real-world example or case study, "
                            "(2) deepening the economic analysis with specific figures, "
                            "or (3) adding a new ## section exploring implications. "
                            "Do NOT pad with filler — add substantive content."
                        )
                    else:
                        fix_lines.append(f"- {issue}")
                fix_lines.append(
                    "\nReturn the COMPLETE corrected article with ALL fixes applied."
                )
                fix_instructions = "\n".join(fix_lines)

                # Regenerate with fix instructions, passing original draft for context
                draft = call_llm(
                    self.client,
                    system_prompt + "\n\n" + fix_instructions,
                    f"Fix the issues in this draft and return the complete corrected article:\n\n{draft}",
                    max_tokens=4000,
                )
                # Deterministic fix for BUG-028 on regenerated output
                draft = self._ensure_frontmatter(draft)
                regenerated = True  # Mark that regeneration occurred

                # Re-validate
                is_valid, issues = review_agent_output(
                    "writer_agent", draft, context={"chart_filename": chart_filename}
                )

                if not is_valid:
                    print(
                        f"   ⚠️  Draft still has {len(issues)} issues after regeneration"
                    )
                else:
                    print("   ✅ Regenerated draft passed validation")
            else:
                print(f"   ⚠️  Draft has {len(issues)} warnings (non-critical)")
        else:
            print("   ✅ Draft passed self-validation")

        # Log to governance if available
        if self.governance:
            self.governance.log_agent_output(
                "writer_agent",
                {"draft": draft, "word_count": len(draft.split())},
                metadata={
                    "topic": topic,
                    "length": len(draft),
                    "is_valid": is_valid,
                    "regenerated": regenerated,
                },
            )

        # Return draft with validation metadata
        return draft, {
            "is_valid": is_valid,
            "regenerated": regenerated,
            "critical_issues": len(critical_issues) if not is_valid else 0,
        }

    def _format_references_guidance(self, research_brief: dict[str, Any]) -> str:
        """Format references guidance from research data sources.

        Extracts sources from research brief and formats them as
        reference examples for the Writer Agent to follow.

        Args:
            research_brief: Research data with data_points containing sources

        Returns:
            Formatted guidance string or empty string if no sources
        """
        sources = []

        # Extract sources from data_points
        for dp in research_brief.get("data_points", []):
            if dp.get("source") and dp.get("verified", False):
                source_entry = {
                    "source": dp["source"],
                    "year": dp.get("year", "2024"),
                    "url": dp.get("url", ""),
                }
                # Avoid duplicates
                if source_entry not in sources:
                    sources.append(source_entry)

        # Extract source from headline_stat
        if research_brief.get("headline_stat"):
            hs = research_brief["headline_stat"]
            if hs.get("source") and hs.get("verified", False):
                source_entry = {
                    "source": hs["source"],
                    "year": hs.get("year", "2024"),
                    "url": "",
                }
                if source_entry not in sources:
                    sources.insert(0, source_entry)  # Headline source first

        if not sources:
            return ""

        # Format references guidance
        guidance = [
            "\n",
            "═══════════════════════════════════════════════════════════════════════════",
            "⚠️  REFERENCES SOURCES AVAILABLE ⚠️",
            "═══════════════════════════════════════════════════════════════════════════",
            "",
            "The Research Agent has verified these sources. Include them in your References section:",
            "",
        ]

        for i, src in enumerate(sources[:5], 1):  # Max 5 sources
            source_name = src["source"]
            year = src["year"]
            url = src.get("url", "")

            if url:
                guidance.append(
                    f"{i}. {source_name}, [source title/report name], *Publication*, {year}"
                )
                guidance.append(f"   URL: {url}")
            else:
                guidance.append(
                    f"{i}. {source_name}, [report/study name], *Publication*, {year}"
                )

        guidance.extend(
            [
                "",
                "Format these as proper references in your '## References' section.",
                "Use descriptive link text, not generic 'click here'.",
                "═══════════════════════════════════════════════════════════════════════════",
            ]
        )

        return "\n".join(guidance)


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


def run_writer_agent(
    client: Any,
    topic: str,
    research_brief: dict[str, Any],
    current_date: str,
    chart_filename: str | None = None,
    featured_image: str | None = None,
    governance: GovernanceTracker | None = None,
) -> tuple[str, dict[str, Any]]:
    """Run the writer agent (backward compatibility wrapper).

    This function maintains 100% backward compatibility with the original
    economist_agent.py implementation.

    Args:
        client: LLM client instance
        topic: Article topic
        research_brief: Research data dictionary
        current_date: Date for YAML frontmatter
        chart_filename: Optional chart filename to embed
        featured_image: Optional featured image path
        governance: Optional governance tracker

    Returns:
        Tuple of (article_text, metadata_dict)

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> draft, metadata = run_writer_agent(
        ...     client,
        ...     "AI Testing",
        ...     {"headline_stat": {...}},
        ...     "2026-01-02"
        ... )
    """
    agent = WriterAgent(client, governance)
    return agent.write(
        topic=topic,
        research_brief=research_brief,
        current_date=current_date,
        chart_filename=chart_filename,
        featured_image=featured_image,
    )
