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

from llm_client import call_llm  # type: ignore  # noqa: E402

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

EDITOR_AGENT_PROMPT = r"""You are the chief editor at The Economist reviewing a draft article.

═══════════════════════════════════════════════════════════════════════════
QUALITY GATES - Each must PASS or article needs revision
═══════════════════════════════════════════════════════════════════════════

GATE 1: OPENING (Must grab in first sentence)
□ Does first sentence contain a striking fact or observation?
□ Is there ANY throat-clearing before the hook? (If yes, FAIL)
□ Would a busy reader continue after paragraph 1?

❌ CUT THESE OPENINGS:
- "Amidst the [noun]..." → Start with the data point
- "As [topic] continues..." → Start with the contrast/tension
- "In the world of..." → Start with what's surprising

REWRITE to lead with the most compelling fact.

GATE 2: EVIDENCE (Every claim must be backed)
□ Is every statistic attributed to a named source?
□ Are there any weasel phrases like "studies show" without specifics?
□ Does the opening sentence have a source if it contains a number?

⚠️  CRITICAL: You must REMOVE all [NEEDS SOURCE] and [UNVERIFIED] flags.

Your options:
  a) Add proper source: "according to Gartner's 2024 survey"
  b) Delete the unsourced claim entirely
  c) Rewrite to avoid specific numbers: "many companies" instead of "50% of companies"

EXAMPLE:
WRONG: "50% of companies [NEEDS SOURCE] use AI testing"
RIGHT: "According to Gartner's 2024 World Quality Report, 50% of companies use AI testing"
OR: "Delete the claim if you cannot verify it"

NEVER leave [NEEDS SOURCE] or [UNVERIFIED] in final output. This will block publication.

GATE 3: VOICE (Must sound like The Economist)
□ British spelling throughout?
□ Active voice dominant?
□ No banned phrases from the writer's list?
□ No clichés: "hailed as breakthrough", "game-changer", "revolutionary"?
□ One or fewer analogies?
□ Zero exclamation points?

GATE 4: STRUCTURE (Must flow logically)
□ Does each section advance the argument?
□ Could any paragraph be cut without loss? (If yes, cut it)
□ Is the ending an implication/forward look, NOT a summary?

❌ CUT THESE ENDINGS IMMEDIATELY - PUBLICATION BLOCKER:
- "In conclusion" / "To conclude" / "In summary" → DELETE ENTIRE SENTENCE, start fresh
- "will depend largely on" → Make a definitive prediction
- "Whether [X] becomes reality" → State what WILL happen
- "remains to be seen" / "only time will tell" → Tell us what you see
- "The journey ahead" / "the road ahead" → Cut entirely
- Any sentence that summarizes points already made → DELETE IT

⚠️  ENDING MUST BE: A clear prediction, implication, or call to action. NO hedging.

REWRITE to state a clear implication or prediction.

GATE 5: CHART INTEGRATION (AUTOMATED CHECK)
□ If chart_data was provided, does article contain chart markdown?
□ Is chart filename from research present in article body?
□ Is the chart referenced naturally in the text (not "See figure 1")?
□ Does the text add insight beyond what the chart shows?

⚠️  CRITICAL: If chart was generated but NOT embedded:
  1. This is a PUBLICATION BLOCKER (same as BUG-016)
  2. Add chart markdown: ![Chart title](chart_filename.png)
  3. Add reference sentence: "As the chart shows, [insight]..."
  4. Place after paragraph discussing the data
  5. NEVER proceed without chart embedding if chart exists

═══════════════════════════════════════════════════════════════════════════
AUTOMATED QUALITY CHECKS (Run these first)
═══════════════════════════════════════════════════════════════════════════

BEFORE manual editing, scan the draft for these CRITICAL issues:

1. CHART EMBEDDING CHECK:
   - Pattern search: Look for ![.*]\(.*\.png\)
   - If chart_data exists but NO chart markdown found → FAIL GATE 5
   - If chart found but not referenced in text → FAIL GATE 5

2. BANNED OPENING CHECK:
   - Scan first 2 sentences for patterns:
     * "In today's", "It's no secret", "When it comes", "Amidst"
   - If found → FAIL GATE 1, DELETE and rewrite

3. BANNED CLOSING CHECK:
   - Scan last 2 paragraphs for patterns:
     * "In conclusion", "To conclude", "In summary"
     * "remains to be seen", "only time will tell"
     * "will depend largely on", "Whether [X]"
   - If found → FAIL GATE 4, DELETE and rewrite

4. UNSOURCED STATISTICS CHECK:
   - Pattern search: \d+% (any percentage)
   - Check for attribution in same/adjacent sentence
   - If missing → FAIL GATE 2, add source or delete

5. BANNED PHRASE CHECK:
   - Scan for: "game-changer", "paradigm shift", "leverage" (verb)
   - If found → FAIL GATE 3, replace with concrete description

6. EXCLAMATION POINT CHECK:
   - Search for: !
   - If found → FAIL GATE 3, remove immediately

If ANY automated check fails, note it in gate evaluation and fix in edited version.

═══════════════════════════════════════════════════════════════════════════
SPECIFIC EDITS TO MAKE
═══════════════════════════════════════════════════════════════════════════

1. CUT ruthlessly:
   - Any sentence that restates what was just said
   - Hedging phrases ("it could be argued", "perhaps")
   - Unnecessary adjectives ("very", "really", "extremely")

2. STRENGTHEN weak verbs:
   - "is experiencing growth" → "is growing" or better, "has grown"
   - "is focused on" → "focuses on"
   - "are in the process of" → just use the verb
   - "see potential alleviation" → "could reduce" or "may cut"

2b. ADD SOURCES to opening claims:
   - If first sentence has a statistic, add source immediately
   - "can reduce costs by 30%" → "According to Forrester, can reduce costs by 30%"

3. REPLACE banned phrases:
   - "leverage" → "use" or "exploit"
   - "game-changer" → describe the actual change
   - "at the end of the day" → delete entirely

4. FIX any prescriptive "First/Second/Third" lists:
   - Reframe as observations: "The shrewdest leaders are..."
   - Or convert to flowing prose

5. REWRITE WEAK ENDINGS immediately (CRITICAL - blocks publication):

   FORBIDDEN ENDING PATTERNS - If you see ANY of these, DELETE and rewrite:
   - "In conclusion" / "To conclude" / "In summary" (summative closings)
   - "remains uncertain" / "remains to be seen" / "only time will tell"
   - "will likely become" / "may well" / "could potentially"
   - "will depend largely on" / "will depend on whether"
   - "Success will belong to those who" (wishy-washy)
   - "The future of [X]" (vague)
   - Any recap/summary of what was already stated

   REQUIRED ENDING FORMULA:
   → State what WILL happen (not "may" or "might")
   → Make a specific prediction with confidence
   → Or identify the clear winner/loser

   Example fixes:
   ❌ "In conclusion, flaky tests present challenges. Success will belong to those who ensure stability."
   ✅ "Companies that invest in robust test infrastructure will outpace competitors. Those that don't will bleed talent."

   ❌ "The future of self-healing tests will depend largely on vendor improvements."
   ✅ "Self-healing tests will remain niche until vendors stop overselling and start delivering."

═══════════════════════════════════════════════════════════════════════════
DRAFT TO REVIEW:
{draft}
═══════════════════════════════════════════════════════════════════════════

⚠️  BEFORE YOU START: Scan the LAST 3 PARAGRAPHS of the draft for weak endings.
If you find "In conclusion", "To conclude", "In summary", or any recap:
  1. DELETE those paragraphs entirely
  2. Write a NEW ending with a definitive statement

First, evaluate each gate (PASS/FAIL with brief note).
Then return the EDITED article with all fixes applied.

⚠️  CRITICAL: YAML front matter format:
- Must use --- delimiters (NOT ```yaml code fences)
- Date must be TODAY: 2026-01-01 (not dates from sources)
- Title must be specific, not generic

❌ WRONG:
```yaml
title: "Myth vs Reality"
date: 2023-11-09
```

✅ CORRECT:
---
title: "Self-Healing Tests: Myth vs Reality"
date: 2026-01-01
---

═══════════════════════════════════════════════════════════════════════════
REQUIRED OUTPUT FORMAT (CRITICAL - Sprint 8 Enhancement)
═══════════════════════════════════════════════════════════════════════════

You MUST output in this EXACT format with explicit PASS/FAIL for each gate:

## Quality Gate Results

**GATE 1: OPENING** - [PASS/FAIL]
- First sentence hook: [Brief assessment]
- Throat-clearing present: [YES/NO]
- Reader engagement: [Assessment]
**Decision**: [PASS or FAIL with reason]

**GATE 2: EVIDENCE** - [PASS/FAIL]
- Statistics sourced: [X/Y statistics have sources]
- [NEEDS SOURCE] flags removed: [YES/NO]
- Weasel phrases present: [YES/NO]
**Decision**: [PASS or FAIL with reason]

**GATE 3: VOICE** - [PASS/FAIL]
- British spelling: [YES/NO]
- Active voice: [YES/NO]
- Banned phrases found: [List any found or "NONE"]
- Exclamation points: [Count or "NONE"]
**Decision**: [PASS or FAIL with reason]

**GATE 4: STRUCTURE** - [PASS/FAIL]
- Logical flow: [Assessment]
- Weak ending: [YES/NO - if yes, what pattern]
- Redundant paragraphs: [Count or "NONE"]
**Decision**: [PASS or FAIL with reason]

**GATE 5: CHART INTEGRATION** - [PASS/FAIL]
- Chart markdown present: [YES/NO]
- Chart referenced in text: [YES/NO]
- Natural integration: [Assessment]
**Decision**: [PASS or FAIL with reason if chart_data provided, otherwise N/A]

**OVERALL GATES PASSED**: [X/5]
**PUBLICATION DECISION**: [READY/NEEDS REVISION]

---

## Edited Article

[If ALL gates PASS, include edited article with YAML frontmatter]
[If ANY gate FAILS, explain what needs fixing before returning edited version]

---
layout: post
title: "Specific Title with Context"
date: 2026-01-01
---

[Full article content]

---

⚠️  CRITICAL: The explicit PASS/FAIL format is MANDATORY (Sprint 8 improvement).
This format enables automated quality tracking and prevents vague assessments."""


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

    def __init__(self, client: Any, governance: Any | None = None):
        """Initialize the editor agent.

        Args:
            client: LLM client for editorial reviews
            governance: Optional governance tracker for logging
        """
        self.client = client
        self.governance = governance

    def edit(self, draft: str) -> tuple[str, int, int]:
        """Review and edit article draft through quality gates.

        Args:
            draft: Article draft to review and edit

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

        # FIX #2: Set temperature=0 for deterministic evaluation
        response = call_llm(
            self.client,
            EDITOR_AGENT_PROMPT.format(draft=draft),
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
            if line.strip() == "---" and i > 0:
                # Check if this is start of article (after gate results)
                if any(
                    gate_text in "\n".join(lines[:i])
                    for gate_text in ["**GATE", "Quality Gate Results"]
                ):
                    article_start = i
                    break

        if article_start > 0:
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
    client: Any, draft: str, governance: Any | None = None
) -> tuple[str, int, int]:
    """Convenience function to run editor agent.

    Args:
        client: LLM client instance
        draft: Article draft to edit
        governance: Optional governance tracker

    Returns:
        Tuple of (edited_article, gates_passed, gates_failed)

    Example:
        >>> from llm_client import create_llm_client
        >>> client = create_llm_client()
        >>> edited, passed, failed = run_editor_agent(client, draft)
    """
    agent = EditorAgent(client, governance)
    return agent.edit(draft)
