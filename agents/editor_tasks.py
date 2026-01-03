#!/usr/bin/env python3
"""
Editor Agent Tasks for CrewAI Integration

Defines task configurations and utilities for the Editor Agent
when working within CrewAI framework.
"""

from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# QUALITY GATE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

BANNED_OPENINGS = [
    "In today's",
    "It's no secret",
    "When it comes",
    "Amidst",
    "In the world of",
]

BANNED_CLOSINGS = [
    "In conclusion",
    "To conclude",
    "In summary",
    "remains to be seen",
    "only time will tell",
    "will depend largely on",
    "Whether",
    "The journey ahead",
    "the road ahead",
]

BANNED_PHRASES = [
    "game-changer",
    "paradigm shift",
    "leverage",  # as verb
    "at the end of the day",
]


# ═══════════════════════════════════════════════════════════════════════════
# TASK CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════


def create_editor_task_config(
    draft: str,
    topic: str,
    expected_gates: int = 5,
) -> dict[str, Any]:
    """Create task configuration for editing article draft.

    Args:
        draft: Article draft to edit
        topic: Article topic for context
        expected_gates: Number of quality gates to validate (default: 5)

    Returns:
        Task configuration dict for CrewAI
    """
    return {
        "description": f"""Review and edit this Economist-style article on '{topic}'.

Apply 5 quality gates:
1. OPENING - Must grab attention immediately
2. EVIDENCE - All claims sourced
3. VOICE - British spelling, active voice, no clichés
4. STRUCTURE - Logical flow, strong ending
5. CHART INTEGRATION - Charts embedded and referenced

Draft to edit:
{draft}

Output MUST include Quality Gate Results with explicit PASS/FAIL for each gate.""",
        "expected_output": f"""Quality Gate Results with {expected_gates} gates evaluated,
followed by edited article with YAML frontmatter.""",
        "agent": "editor",
        "context": {
            "draft": draft,
            "topic": topic,
            "word_count": len(draft.split()),
        },
    }


def create_critique_task_config(
    article: str,
    topic: str,
) -> dict[str, Any]:
    """Create task configuration for hostile review of final article.

    Args:
        article: Final edited article
        topic: Article topic for context

    Returns:
        Task configuration dict for CrewAI
    """
    return {
        "description": f"""Perform hostile review of this Economist article on '{topic}'.

Look for:
1. Unsourced claims
2. Clichés that slipped through
3. Logic gaps
4. Voice breaks (doesn't sound like The Economist)
5. Missing contrarian angle

Article to review:
{article}

Be harsh. Find problems, not praise.""",
        "expected_output": "List of issues found with specific text, problem description, and suggested fixes. Or confirmation that article is genuinely good.",
        "agent": "critic",
        "context": {
            "article": article,
            "topic": topic,
            "word_count": len(article.split()),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY VALIDATION UTILITIES
# ═══════════════════════════════════════════════════════════════════════════


def validate_opening(draft: str) -> dict[str, Any]:
    """Validate article opening against quality standards.

    Args:
        draft: Article draft to validate

    Returns:
        Validation result with issues found
    """
    lines = draft.split("\n")
    first_two_lines = "\n".join(lines[:2]).lower()

    issues = []
    for phrase in BANNED_OPENINGS:
        if phrase.lower() in first_two_lines:
            issues.append(f"Banned opening phrase: '{phrase}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_closing(draft: str) -> dict[str, Any]:
    """Validate article ending against quality standards.

    Args:
        draft: Article draft to validate

    Returns:
        Validation result with issues found
    """
    lines = [line for line in draft.split("\n") if line.strip()]
    last_paragraphs = "\n".join(lines[-6:]).lower()  # Last ~2 paragraphs

    issues = []
    for phrase in BANNED_CLOSINGS:
        if phrase.lower() in last_paragraphs:
            issues.append(f"Banned closing phrase: '{phrase}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_voice(draft: str) -> dict[str, Any]:
    """Validate article voice against Economist style.

    Args:
        draft: Article draft to validate

    Returns:
        Validation result with issues found
    """
    draft_lower = draft.lower()
    issues = []

    # Check banned phrases
    for phrase in BANNED_PHRASES:
        if phrase.lower() in draft_lower:
            issues.append(f"Banned phrase: '{phrase}'")

    # Check for exclamation points (but exclude markdown image syntax ![...])
    # Remove markdown images first
    import re

    draft_no_images = re.sub(r"!\[.*?\]\(.*?\)", "", draft)
    exclamation_count = draft_no_images.count("!")
    if exclamation_count > 0:
        issues.append(f"{exclamation_count} exclamation point(s) found")

    # Check for American spelling (common patterns)
    american_patterns = [
        ("organization", "organisation"),
        ("favor", "favour"),
        ("color", "colour"),
        ("optimize", "optimise"),
        ("analyze", "analyse"),
    ]

    for american, british in american_patterns:
        if american in draft_lower:
            issues.append(f"American spelling: '{american}' → use '{british}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_chart_integration(draft: str, has_chart: bool = False) -> dict[str, Any]:
    """Validate chart embedding in article.

    Args:
        draft: Article draft to validate
        has_chart: Whether chart was generated for this article

    Returns:
        Validation result with issues found
    """
    issues = []

    # Check for chart markdown
    has_chart_markdown = "![" in draft and ".png" in draft

    if has_chart and not has_chart_markdown:
        issues.append("Chart generated but not embedded in article")

    if has_chart_markdown:
        # Check for natural reference
        chart_indicators = [
            "as the chart shows",
            "the chart reveals",
            "data shows",
            "illustrated above",
        ]

        has_reference = any(
            indicator in draft.lower() for indicator in chart_indicators
        )

        if not has_reference:
            issues.append("Chart embedded but not referenced naturally in text")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "has_chart_markdown": has_chart_markdown,
    }


def parse_quality_gates(response: str) -> dict[str, Any]:
    """Parse quality gate results from editor response.

    Args:
        response: Editor agent response text

    Returns:
        Parsed gate results with counts and details
    """
    # Count PASS/FAIL occurrences
    gates_passed = response.upper().count("PASS")
    gates_failed = response.upper().count("FAIL")

    # Extract individual gate results
    gate_results = {}
    for i in range(1, 6):
        gate_name = f"GATE {i}"
        if gate_name in response.upper():
            # Find the decision line
            gate_section = response[response.upper().find(gate_name) :]
            decision_start = gate_section.find("**Decision**:")
            if decision_start != -1:
                decision_line = gate_section[decision_start : decision_start + 200]
                is_pass = "PASS" in decision_line.upper()
                gate_results[f"gate_{i}"] = "PASS" if is_pass else "FAIL"

    # Check for edited article section
    has_edited_article = "## Edited Article" in response

    return {
        "gates_passed": gates_passed,
        "gates_failed": gates_failed,
        "total_gates": gates_passed + gates_failed,
        "gate_results": gate_results,
        "has_edited_article": has_edited_article,
        "publication_ready": gates_failed == 0 and has_edited_article,
    }


def extract_edited_article(response: str) -> str | None:
    """Extract edited article from editor response.

    Args:
        response: Editor agent response text

    Returns:
        Edited article text or None if not found
    """
    if "## Edited Article" not in response:
        return None

    # Split and get everything after the marker
    parts = response.split("## Edited Article")
    if len(parts) < 2:
        return None

    edited = parts[1].strip()

    # Remove any trailing markdown formatting
    if edited.startswith("```"):
        edited = edited[3:].strip()
    if edited.endswith("```"):
        edited = edited[:-3].strip()

    return edited


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════


def validate_all_gates(
    draft: str,
    has_chart: bool = False,
) -> dict[str, Any]:
    """Run all quality gate validations on draft.

    Args:
        draft: Article draft to validate
        has_chart: Whether chart was generated

    Returns:
        Combined validation results
    """
    results = {
        "opening": validate_opening(draft),
        "closing": validate_closing(draft),
        "voice": validate_voice(draft),
        "chart_integration": validate_chart_integration(draft, has_chart),
    }

    # Count total issues
    total_issues = sum(len(result["issues"]) for result in results.values())

    # Overall validation
    all_valid = all(result["valid"] for result in results.values())

    return {
        "valid": all_valid,
        "total_issues": total_issues,
        "results": results,
    }
