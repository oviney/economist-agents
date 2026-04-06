#!/usr/bin/env python3
"""
Editor Agent - Reviews and edits article drafts

Extracted from economist_agent.py for better modularity.
Implements Sprint 8 Story 4 fixes:
- Fix #1: Regex-based gate counting (exactly 5 gates)
- Fix #2: Temperature=0 for deterministic evaluation
- Fix #3: Format validation for structured output
"""

import re
import sys
from pathlib import Path
from typing import Any

# Add scripts directory to path for llm_client import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from agent_loader import (  # noqa: E402
    load_content_agent as _load_content_agent,  # type: ignore
)
from llm_client import call_llm  # type: ignore  # noqa: E402

# Sprint 14 Integration: Style Memory RAG
try:
    from src.tools.style_memory_tool import StyleMemoryTool

    STYLE_MEMORY_AVAILABLE = True
except ImportError:
    STYLE_MEMORY_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# GATE COUNTING FIX #1: Regex patterns for exactly 5 gates
# Updated: Patterns match both [PASS] and - PASS formats for flexibility
# ═══════════════════════════════════════════════════════════════════════════

GATE_PATTERNS = [
    r"\*\*GATE 1: OPENING\*\*\s*[-:]\s*\[?(PASS|FAIL)\]?",
    r"\*\*GATE 2: EVIDENCE\*\*\s*[-:]\s*\[?(PASS|FAIL)\]?",
    r"\*\*GATE 3: VOICE\*\*\s*[-:]\s*\[?(PASS|FAIL)\]?",
    r"\*\*GATE 4: STRUCTURE\*\*\s*[-:]\s*\[?(PASS|FAIL)\]?",
    r"\*\*GATE 5: CHART INTEGRATION\*\*\s*[-:]\s*\[?(PASS|FAIL|N/A)\]?",
]

EXPECTED_GATES = 5


# ═══════════════════════════════════════════════════════════════════════════
# EDITOR AGENT PROMPT
# ═══════════════════════════════════════════════════════════════════════════
# EDITOR AGENT PROMPT
# ═══════════════════════════════════════════════════════════════════════════

_editor_config = _load_content_agent("editor")
EDITOR_AGENT_PROMPT = _editor_config.system_message


# ═══════════════════════════════════════════════════════════════════════════
# EDITOR AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class EditorAgent:
    """Editor agent for reviewing and editing article drafts.

    This agent focuses on:
    - Quality gate validation (5 gates: Opening, Evidence, Voice, Structure, Chart)
    - Fixing style violations
    - Ensuring publication-ready quality

    Implements Sprint 8 Story 4 fixes:
    - Fix #1: Regex-based gate counting (exactly 5 gates)
    - Fix #2: Temperature=0 for deterministic evaluation
    - Fix #3: Format validation for structured output

    Args:
        client: LLM client instance (from llm_client.create_llm_client())
        governance: Optional governance tracker for audit logging

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> agent = EditorAgent(client)
        >>> edited, gates_passed, gates_failed = agent.edit(draft)
    """

    def __init__(
        self,
        client: Any,
        governance: Any | None = None,
        style_memory_tool: Any | None = None,
    ):
        """Initialize the editor agent.

        Args:
            client: LLM client for editorial reviews
            governance: Optional governance tracker for logging
            style_memory_tool: Optional StyleMemoryTool for RAG-based style patterns
        """
        self.client = client
        self.governance = governance
        self.style_memory_tool = style_memory_tool

        # Sprint 14 Integration: Initialize Style Memory if available and not provided
        if style_memory_tool is None and STYLE_MEMORY_AVAILABLE:
            try:
                self.style_memory_tool = StyleMemoryTool()
                print("✅ Editor Agent: Style Memory RAG enabled")
            except Exception as e:
                print(f"⚠️  Style Memory RAG initialization failed: {e}")
                self.style_memory_tool = None

        self.metrics = {
            "gates_passed": 0,
            "gates_failed": 0,
            "edits_made": 0,
            "quality_issues": [],
        }

    def validate_draft(self, draft: str) -> None:
        """Validate draft before editing.

        Args:
            draft: Article draft to validate

        Raises:
            ValueError: If draft is invalid or too short
        """
        if not draft or not isinstance(draft, str):
            raise ValueError(
                f"Invalid draft. Expected non-empty string, got: {type(draft).__name__}"
            )

        if len(draft.strip()) < 100:
            raise ValueError("Draft too short. Need at least 100 characters.")

    def edit(self, draft: str, current_date: str) -> tuple[str, int, int]:
        """Review and edit article draft through quality gates.

        Args:
            draft: Article draft to review and edit
            current_date: Current date in YYYY-MM-DD format for article frontmatter

        Returns:
            Tuple of (edited_article, gates_passed, gates_failed)
            - edited_article: Edited article text with YAML frontmatter
            - gates_passed: Number of quality gates that passed (0-5)
            - gates_failed: Number of quality gates that failed (0-5)

        Raises:
            ValueError: If draft is invalid

        Example:
            >>> edited, passed, failed = agent.edit(draft)
            >>> print(f"Quality: {passed}/{passed + failed} gates passed")
        """
        # Input validation
        if not draft or not isinstance(draft, str):
            raise ValueError(
                f"[EDITOR_AGENT] Invalid draft. Expected non-empty string, "
                f"got: {type(draft).__name__}"
            )

        if len(draft.strip()) < 100:
            raise ValueError(
                "[EDITOR_AGENT] Draft too short. Need at least 100 characters."
            )

        print("📝 Editor Agent: Reviewing draft through quality gates...")

        # Sprint 14 Integration: Query Style Memory RAG for relevant patterns
        style_context = ""
        if self.style_memory_tool:
            try:
                # Query for voice/style patterns
                patterns = self.style_memory_tool.query(
                    "Economist voice and style guidelines", n_results=3
                )
                if patterns:
                    style_context = (
                        "\n\nRELEVANT STYLE PATTERNS (from Gold Standard articles):\n"
                    )
                    for i, pattern in enumerate(patterns, 1):
                        style_context += f"\n{i}. {pattern['text'][:200]}...\n   (Relevance: {pattern['score']:.2f})"
                    print(
                        f"   📖 Style Memory: Retrieved {len(patterns)} relevant patterns"
                    )
            except Exception as e:
                print(f"   ⚠️  Style Memory query failed: {e}")

        # FIX #2: Set temperature=0 for deterministic evaluation
        prompt_with_context = (
            EDITOR_AGENT_PROMPT.format(draft=draft, current_date=current_date)
            + style_context
        )
        response = call_llm(
            self.client,
            prompt_with_context,
            "Review and edit this article.",
            max_tokens=4000,
            temperature=0.0,  # Sprint 8 Story 4 Fix #2: Deterministic gate decisions
        )

        # FIX #3: Validate format before parsing
        if not self._validate_editor_format(response):
            print("   ⚠️  Editor output format invalid, using draft unchanged")
            return draft, 0, EXPECTED_GATES

        # FIX #1: Parse gate results using regex (exactly 5 gates)
        gates_passed, gates_failed = self._parse_gate_results(response)

        # Extract edited article
        edited_article = self._extract_edited_article(response)

        # Update metrics
        self.metrics["gates_passed"] = gates_passed
        self.metrics["gates_failed"] = gates_failed
        self.metrics["edits_made"] += 1
        if gates_failed > 0:
            self.metrics["quality_issues"].append(f"{gates_failed} gates failed")

        # Log to governance if available
        if self.governance:
            self.governance.log_agent_output(
                "editor_agent",
                {
                    "response": response,
                    "gates_passed": gates_passed,
                    "gates_failed": gates_failed,
                },
                metadata={"word_count": len(edited_article.split())},
            )

        print(f"   Quality gates: {gates_passed}/{EXPECTED_GATES} passed")

        return edited_article, gates_passed, gates_failed

    def _parse_gate_results(self, response: str) -> tuple[int, int]:
        """Parse gate results using regex to ensure exactly 5 gates counted.

        This is Sprint 8 Story 4 Fix #1: Regex-based gate counting.
        Prevents sub-criteria checkboxes from being counted as gates.

        Args:
            response: Editor LLM response text

        Returns:
            Tuple of (gates_passed, gates_failed)
        """
        gates_passed = 0
        gates_failed = 0

        for i, pattern in enumerate(GATE_PATTERNS, 1):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                if result == "PASS":
                    gates_passed += 1
                elif result == "FAIL":
                    gates_failed += 1
                elif result == "N/A":
                    # N/A counts as passing (no chart required)
                    gates_passed += 1
            else:
                # Gate not found in expected format
                print(f"   ⚠️  GATE {i} not found in expected format")

        return gates_passed, gates_failed

    def _validate_editor_format(self, response: str) -> bool:
        """Validate editor output contains required sections.

        This is Sprint 8 Story 4 Fix #3: Format validation.
        Fails fast if format deviates from expected structure.

        Args:
            response: Editor LLM response text

        Returns:
            True if format is valid, False otherwise
        """
        required_sections = [
            "## Quality Gate Results",
            "**OVERALL GATES PASSED**:",
            "**PUBLICATION DECISION**:",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in response:
                missing_sections.append(section)

        if missing_sections:
            print(f"   ⚠️  Missing sections: {', '.join(missing_sections)}")
            return False

        # Validate at least 3 of 5 gates present (allow some flexibility)
        gate_count = sum(
            1
            for pattern in GATE_PATTERNS
            if re.search(pattern, response, re.IGNORECASE)
        )
        if gate_count < 3:
            print(f"   ⚠️  Only {gate_count}/5 gates found in response")
            return False

        return True

    def _extract_edited_article(self, response: str) -> str:
        """Extract edited article from editor response.

        Args:
            response: Editor LLM response text

        Returns:
            Edited article text with YAML frontmatter
        """
        # Look for "## Edited Article" section
        if "## Edited Article" in response:
            parts = response.split("## Edited Article", 1)
            if len(parts) == 2:
                article = parts[1].strip()
                # Remove any trailing "---" separator
                if article.endswith("---"):
                    article = article[:-3].strip()
                return article

        # Fallback: Look for YAML frontmatter after gate results
        lines = response.split("\n")
        article_start = -1
        for i, line in enumerate(lines):
            if (
                line.strip() == "---"
                and i > 0
                and any(
                    gate_text in "\n".join(lines[:i])
                    for gate_text in ["**GATE", "Quality Gate Results"]
                )
            ):
                article_start = i
                break
        return "\n".join(lines[article_start:]).strip()

        # Last resort: return everything after PUBLICATION DECISION
        if "**PUBLICATION DECISION**:" in response:
            parts = response.split("**PUBLICATION DECISION**:", 1)
            if len(parts) == 2:
                # Skip decision text, find next ---
                remaining = parts[1]
                if "---" in remaining:
                    article_parts = remaining.split("---", 1)
                    if len(article_parts) == 2:
                        return ("---" + article_parts[1]).strip()

        print("   ⚠️  Could not extract edited article, returning original")
        return response


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION (for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════


def run_editor_agent(
    client: Any,
    draft: str,
    governance: Any | None = None,
    style_memory_tool: Any | None = None,
    current_date: str | None = None,
) -> tuple[str, int, int]:
    """Convenience function to run editor agent.

    Args:
        client: LLM client instance
        draft: Article draft to edit
        governance: Optional governance tracker
        style_memory_tool: Optional StyleMemoryTool for RAG patterns

    Returns:
        Tuple of (edited_article, gates_passed, gates_failed)

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> edited, passed, failed = run_editor_agent(client, draft)
    """
    # Default to today's date if not provided
    if current_date is None:
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")

    agent = EditorAgent(client, governance, style_memory_tool)
    return agent.edit(draft, current_date)
