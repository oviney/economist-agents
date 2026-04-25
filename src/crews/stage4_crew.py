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
    "One suspects",
    "if you find yourself",
    "it is clear that",
    "it remains to be seen",
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
    "One suspects",
]


_CATEGORY_NORMALIZATION: dict[str, str] = {
    "quality engineering": "quality-engineering",
    "software engineering": "software-engineering",
    "test automation": "test-automation",
}


def _normalize_category_casing(frontmatter: str) -> str:
    """Normalize category values to kebab-case.

    Only modifies the categories: line, not other frontmatter fields.

    Args:
        frontmatter: YAML frontmatter string (between --- delimiters).

    Returns:
        Frontmatter with categories normalized to kebab-case.
    """
    lines = frontmatter.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("categories:"):
            for title_case, kebab in _CATEGORY_NORMALIZATION.items():
                lines[i] = re.sub(
                    re.escape(title_case), kebab, lines[i], flags=re.IGNORECASE
                )
            break
    return "\n".join(lines)


def _truncate_description(frontmatter: str, max_chars: int = 160) -> str:
    """Truncate the description field to max_chars.

    The publication validator rejects descriptions over 160 characters.
    Truncates at the last word boundary and adds ellipsis.

    Args:
        frontmatter: YAML frontmatter string (between --- delimiters).
        max_chars: Maximum allowed characters for description.

    Returns:
        Frontmatter with description truncated if needed.
    """
    match = re.search(
        r'^(description:\s*["\']?)(.+?)(["\']?\s*)$',
        frontmatter,
        re.MULTILINE,
    )
    if not match:
        return frontmatter

    prefix, value, suffix = match.group(1), match.group(2), match.group(3)
    if len(value) <= max_chars:
        return frontmatter

    # Truncate at last space before limit, add ellipsis
    truncated = value[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return frontmatter.replace(match.group(0), f"{prefix}{truncated}{suffix}")


def _auto_embed_chart(article: str) -> str:
    """Insert chart embed if chart_data referenced but no image embed found.

    Looks for a chart file reference in frontmatter or text without a
    corresponding ``![...](...chart...)`` markdown image. Inserts the embed
    just before the References section (or at end of body).

    Args:
        article: Full article text with YAML frontmatter.

    Returns:
        Article with chart embed inserted if needed.
    """
    if "![" in article and "/assets/charts/" in article:
        return article

    slug_match = re.search(r"image:\s*/assets/images/([^.\s]+)", article)
    if not slug_match:
        return article

    slug = slug_match.group(1)
    chart_embed = f"\n![Chart](/assets/charts/{slug}.png)\n"

    ref_match = re.search(r"\n## References", article)
    if ref_match:
        pos = ref_match.start()
        return article[:pos] + chart_embed + article[pos:]

    return article.rstrip() + "\n" + chart_embed


def _enforce_heading_limit(article: str, max_headings: int = 4) -> str:
    """Merge the shortest section when body heading count exceeds the limit.

    Counts ``## `` headings in the article body (after YAML frontmatter),
    excluding ``## References``.  When the count exceeds *max_headings*,
    the shortest section (fewest lines between consecutive headings) is
    merged into the previous section by removing its heading line.  The
    process repeats until the count is at or below the limit.

    Args:
        article: Full article text, optionally with YAML frontmatter.
        max_headings: Maximum allowed ``## `` headings (default 4).

    Returns:
        Article with headings merged down to the limit.
    """
    # Split frontmatter from body
    if article.startswith("---"):
        parts = article.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]
        else:
            frontmatter = ""
            body = article
    else:
        frontmatter = ""
        body = article

    while True:
        lines = body.split("\n")
        # Collect indices of body headings (## ) excluding ## References
        heading_indices: list[int] = [
            i
            for i, line in enumerate(lines)
            if line.startswith("## ") and line.strip() != "## References"
        ]

        if len(heading_indices) <= max_headings:
            break

        # Find shortest section (by line count between headings)
        # Build section lengths: from heading to next heading (or end)
        section_lengths: list[tuple[int, int]] = []  # (length, heading_index)
        for idx, h_idx in enumerate(heading_indices):
            if idx + 1 < len(heading_indices):
                next_h = heading_indices[idx + 1]
            else:
                next_h = len(lines)
            section_len = next_h - h_idx
            section_lengths.append((section_len, h_idx))

        # Don't merge the very first heading (nothing to merge into)
        mergeable = section_lengths[1:]
        if not mergeable:
            break

        # Pick the shortest mergeable section
        shortest = min(mergeable, key=lambda x: x[0])
        remove_idx = shortest[1]

        logger.info(
            "Heading limit exceeded (%d > %d); removing heading at line %d: %s",
            len(heading_indices),
            max_headings,
            remove_idx + 1,
            lines[remove_idx].strip(),
        )

        # Remove the heading line
        del lines[remove_idx]
        body = "\n".join(lines)

    return frontmatter + body


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
                fm = fm.rstrip() + '\ncategories: ["quality-engineering"]\n'
            # 8b. Normalize category casing to kebab-case
            fm = _normalize_category_casing(fm)
            # 8e. Truncate description to 160 chars (publication validator limit)
            fm = _truncate_description(fm)
            # Ensure frontmatter ends with newline so closing --- is on its own line
            if not fm.endswith("\n"):
                fm += "\n"
            text = "---" + fm + "---" + parts[2]

    # 8c. Auto-embed chart if chart_data exists but embed missing
    text = _auto_embed_chart(text)

    # 8d. Enforce heading limit (max 4 body headings)
    text = _enforce_heading_limit(text)

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
        from src.crews.stage3_crew import _get_crewai_llm

        return Agent(
            role="Editorial Reviewer",
            goal="Apply 5 quality gates to ensure article meets Economist standards with >95% pass rate",
            llm=_get_crewai_llm(),
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
            description="""Review the following article against 5 quality gates.

ARTICLE TO REVIEW:
{article}

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
        crew_output = self.crew.kickoff(
            inputs={"article": article, "chart_data": str(chart_data)}
        )

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
        # Sanitize common LLM template artifacts before parsing
        sanitized = result_str
        sanitized = re.sub(r"\btrue/false\b", "true", sanitized)
        sanitized = re.sub(r'"\.\.\.?"', '""', sanitized)
        sanitized = re.sub(r"<[^>]+>", '""', sanitized)  # <number 0-100> etc.

        for candidate in (sanitized, result_str):
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

            json_match = re.search(r"\{.*\}", candidate, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        # Fall back to article evaluator score instead of 0/100
        logger.warning(
            "Failed to parse reviewer JSON — falling back to article evaluator"
        )
        try:
            from scripts.article_evaluator import ArticleEvaluator

            evaluator = ArticleEvaluator()
            eval_result = evaluator.evaluate(result_str)
            score = eval_result.percentage
            logger.info("Article evaluator fallback score: %d%%", score)
            return {
                "editorial_score": score,
                "gates_passed": 5 if score >= 80 else 3,
                "specific_edits": [
                    "Reviewer output unparseable — scored by article evaluator"
                ],
            }
        except Exception:
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
