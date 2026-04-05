#!/usr/bin/env python3
"""
Stage 4 Crew - Editorial Review and Deterministic Polish

Uses an LLM reviewer agent for quality gate evaluation, then applies
deterministic post-processing fixes.  The Final Editor LLM agent was
removed because it hallucinated unrelated articles instead of making
targeted edits — a well-known failure mode when LLMs are asked to
"rewrite" rather than evaluate.

Architecture:
    Stage 3 Output → Reviewer Agent (LLM, 5-gate eval)
                   → Deterministic Polish (regex/string ops)
                   → Polished Article
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from crewai import Agent, Crew, Task

logger = logging.getLogger(__name__)

# British spelling replacements (American → British)
_BRITISH_SPELLING: dict[str, str] = {
    "organization": "organisation",
    "Organization": "Organisation",
    "optimize": "optimise",
    "Optimize": "Optimise",
    "optimization": "optimisation",
    "analyze": "analyse",
    "Analyze": "Analyse",
    "analyzing": "analysing",
    "utilize": "utilise",
    "utilizing": "utilising",
    "recognize": "recognise",
    "customize": "customise",
    "prioritize": "prioritise",
    "standardize": "standardise",
    "modernize": "modernise",
    "behavior": "behaviour",
    "favor": "favour",
    "favorable": "favourable",
    "color": "colour",
    "labor": "labour",
    "center": "center",  # Keep as-is for tech terms
}

# Banned phrases to strip
_BANNED_PHRASES: list[str] = [
    "game-changer",
    "game changer",
    "paradigm shift",
    "at the end of the day",
]

# Hedging phrases that undermine the authoritative Economist voice (SKILL.md Rule 4)
_HEDGING_PHRASES: list[str] = [
    "it would be misguided",
    "one might",
    "it is worth noting",
    "it should be noted",
    "it is important to",
    "it is not a minor footnote",
    "further complicating matters",
    "invites closer scrutiny",
    "in practical terms",
]

# Verbose padding — throat-clearing and redundant attribution (SKILL.md Rule 6)
_VERBOSE_PADDING: list[str] = [
    "it goes without saying",
    "needless to say",
    "as mentioned earlier",
    "as noted above",
    "as stated above",
]

# Banned phrase patterns (case-insensitive) — only match "leverage" as verb
_BANNED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bleverage\b(?=\s+(?:the|our|their|its|this|that|these|those))",
            re.IGNORECASE,
        ),
        "use",
    ),
]

# Banned openings (first paragraph)
_BANNED_OPENINGS: list[str] = [
    "In today's world",
    "In today's fast-paced",
    "It's no secret",
    "When it comes to",
    "Amidst",
    "The arrival of",
    "The emergence of",
    "The rise of",
]

# Banned closings (last 500 chars)
_BANNED_CLOSINGS: list[str] = [
    "In conclusion",
    "To conclude",
    "In summary",
    "remains to be seen",
    "only time will tell",
    "The journey ahead",
    "will rest on",
    "depends on",
    "the key is",
    "to summarise",
]


def _apply_editorial_fixes(article: str, current_date: str | None = None) -> str:
    """Apply deterministic editorial fixes to an article.

    Performs the mechanical edits that the Editorial Reviewer might flag:
    British spelling, banned phrase removal, exclamation point removal,
    and date correction.  Does NOT rewrite content — only surgical fixes.

    Args:
        article: Full article text with YAML frontmatter.
        current_date: Expected publication date (YYYY-MM-DD).

    Returns:
        Article with deterministic fixes applied.
    """
    text = article

    # 1. British spelling
    for american, british in _BRITISH_SPELLING.items():
        text = text.replace(american, british)

    # 2. Remove banned phrases (exact match, case-insensitive)
    for phrase in _BANNED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)

    # 3. Remove banned patterns (regex)
    for pattern, replacement in _BANNED_PATTERNS:
        text = pattern.sub(replacement, text)

    # 4. Remove exclamation points (not inside code blocks)
    lines = text.split("\n")
    in_code_block = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block:
            lines[i] = line.replace("!", ".")
    text = "\n".join(lines)

    # 5. Fix double periods from exclamation replacement
    text = text.replace("..", ".")

    # 6. Fix date in YAML frontmatter if needed
    if current_date and text.startswith("---"):
        text = re.sub(
            r"^(---\n.*?date:\s*)\S+(.*?\n---)",
            rf"\g<1>{current_date}\g<2>",
            text,
            count=1,
            flags=re.DOTALL,
        )

    # 7. Strip verification placeholders that should never reach publication
    text = re.sub(r"\s*\[NEEDS SOURCE\]", "", text)
    text = re.sub(r"\s*\[UNVERIFIED\]", "", text)
    text = re.sub(r"\s*\[REPLACE[-_]?ME\]", "", text, flags=re.IGNORECASE)

    # 8. Enforce required frontmatter fields (layout, categories)
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            if "layout:" not in fm:
                fm = "\nlayout: post" + fm
            if "categories:" not in fm:
                fm = fm.rstrip() + '\ncategories: ["Quality Engineering"]\n'
            text = "---" + fm + "---" + parts[2]

    # 9. Clean up double spaces from phrase/placeholder removal
    text = re.sub(r"  +", " ", text)

    # 10. Strip hedging phrases (undermine authoritative voice)
    for phrase in _HEDGING_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)

    # 11. Strip verbose padding (throat-clearing and redundant attribution)
    for phrase in _VERBOSE_PADDING:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)

    # 12. Final cleanup of double spaces introduced by steps 10-11
    text = re.sub(r"  +", " ", text)

    return text


class Stage4Crew:
    """Stage 4: Editorial review (LLM) + deterministic polish.

    The reviewer agent evaluates the article against 5 quality gates
    and returns a structured JSON assessment.  Deterministic post-
    processing then applies mechanical fixes (spelling, banned phrases,
    date correction).  No LLM is used for the editing step.
    """

    def __init__(self) -> None:
        """Initialise Stage 4 with reviewer agent only."""
        self.reviewer_agent = self._create_reviewer_agent()
        self.review_task = self._create_review_task()

        self.crew = Crew(
            agents=[self.reviewer_agent],
            tasks=[self.review_task],
            verbose=True,
        )

    def _create_reviewer_agent(self) -> Agent:
        """Reviewer Agent — applies 5 quality gates."""
        return Agent(
            role="Editorial Reviewer",
            goal="Apply 5 quality gates to ensure article meets Economist standards with >95% pass rate",
            backstory="""You are a senior editorial reviewer at The Economist with 15 years experience.

You enforce the publication's strict quality standards through 5 quality gates:
1. **OPENING**: First sentence must hook with striking fact/data. No throat-clearing ("In today's world...")
2. **EVIDENCE**: Every statistic must have named source. No "studies show" without citation.
3. **VOICE**: British spelling (organisation, analyse). Active voice. No banned phrases (game-changer, leverage as verb).
4. **STRUCTURE**: Logical flow, ruthless cutting of redundancy. Ending must predict/imply, never summarize.
5. **CHART INTEGRATION**: If chart exists, must be embedded in markdown and referenced naturally.

Your pass rate must exceed 95% (4.75/5 gates minimum).

BANNED OPENINGS: "In today's world", "It's no secret", "When it comes to", "Amidst", "The arrival/emergence/rise of"
BANNED CLOSINGS: "In conclusion", "To conclude", "remains to be seen", "only time will tell", "will rest on", "depends on", "to summarise"
BANNED PHRASES: "game-changer", "paradigm shift", "leverage" (as verb), "at the end of the day"
BANNED HEDGING: "it would be misguided", "one might", "it is worth noting", "it should be noted", "it is important to", "further complicating matters", "invites closer scrutiny", "in practical terms"
BANNED STRUCTURE: numbered/bulleted lists in prose body; more than 5 headings

You are ruthlessly precise. Vague feedback is unacceptable.

CRITICAL: You are EVALUATING the article. Do NOT rewrite it. Return ONLY the JSON assessment.""",
            verbose=True,
            allow_delegation=False,
        )

    def _create_review_task(self) -> Task:
        """Create review task for quality gate assessment."""
        return Task(
            description="""Review article from Stage 3 against 5 quality gates.

INPUT: Article with YAML frontmatter and chart_data

QUALITY GATES TO CHECK:
1. OPENING - First sentence hooks? No throat-clearing?
2. EVIDENCE - All statistics sourced? No [NEEDS SOURCE] flags?
3. VOICE - British spelling? No banned phrases? Active voice?
4. STRUCTURE - Logical flow? Strong ending (no "in conclusion")?
5. CHART INTEGRATION - Chart embedded if chart_data exists? Referenced naturally?

OUTPUT FORMAT (JSON only — no other text):
{
    "gates_passed": <number 0-5>,
    "gate_1_opening": {"pass": true/false, "issue": "..."},
    "gate_2_evidence": {"pass": true/false, "issue": "..."},
    "gate_3_voice": {"pass": true/false, "issue": "..."},
    "gate_4_structure": {"pass": true/false, "issue": "..."},
    "gate_5_chart": {"pass": true/false, "issue": "..."},
    "editorial_score": <number 0-100>,
    "specific_edits": ["Edit 1", "Edit 2", ...]
}

CRITICAL: Return ONLY valid JSON. Do NOT include the article text in your response.""",
            expected_output="JSON object with gate results and specific edit recommendations",
            agent=self.reviewer_agent,
        )

    def kickoff(self, stage3_input: dict[str, Any]) -> dict[str, Any]:
        """Execute Stage 4 review and deterministic polish.

        Args:
            stage3_input: dict with 'article' (str) and optional 'chart_data'.

        Returns:
            dict with 'article', 'editorial_score', 'gates_passed',
            'publication_ready', 'reviewer_feedback', 'specific_edits'.
        """
        if not isinstance(stage3_input, dict):
            raise ValueError("stage3_input must be a dictionary")
        if "article" not in stage3_input:
            raise ValueError("stage3_input must contain 'article' key")

        article = stage3_input["article"]
        chart_data = stage3_input.get("chart_data", {})

        # --- LLM step: reviewer evaluates the article ---
        self.review_task.context = {"article": article, "chart_data": chart_data}
        crew_output = self.crew.kickoff()

        result_str = (
            str(crew_output.raw) if hasattr(crew_output, "raw") else str(crew_output)
        )

        review_result = self._parse_review_json(result_str)

        # --- Deterministic step: apply mechanical fixes ---
        current_date = datetime.now().strftime("%Y-%m-%d")
        polished_article = _apply_editorial_fixes(article, current_date)

        editorial_score = review_result.get("editorial_score", 0)
        gates_passed = review_result.get("gates_passed", 0)

        return {
            "article": polished_article,
            "editorial_score": editorial_score,
            "gates_passed": gates_passed,
            "publication_ready": editorial_score >= 95,
            "reviewer_feedback": review_result.get("specific_edits", []),
            "specific_edits": review_result.get("specific_edits", []),
        }

    @staticmethod
    def _parse_review_json(result_str: str) -> dict[str, Any]:
        """Extract JSON from reviewer output, with fallbacks."""
        try:
            return json.loads(result_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting JSON from surrounding text
        json_match = re.search(r"\{.*\}", result_str, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse reviewer JSON output")
        return {
            "editorial_score": 0,
            "gates_passed": 0,
            "specific_edits": ["Failed to parse reviewer output"],
        }


if __name__ == "__main__":
    print("Stage4Crew initialized")
    crew = Stage4Crew()
    print(f"Agents: {len(crew.crew.agents)}")
    print(f"Tasks: {len(crew.crew.tasks)}")
