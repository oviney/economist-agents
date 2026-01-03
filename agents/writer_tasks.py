#!/usr/bin/env python3
"""
Writer Agent Tasks

CrewAI-compatible task definitions for the Writer Agent.
These tasks can be used with CrewAI's Task class or standalone.
"""

from typing import Any


def create_writer_task_config(
    topic: str,
    research_brief: dict[str, Any],
    current_date: str,
    chart_filename: str | None = None,
    featured_image: str | None = None,
    expected_output: str | None = None,
) -> dict[str, Any]:
    """Create a CrewAI-compatible task configuration for writing.

    Args:
        topic: Article topic to write about
        research_brief: Research data from research agent
        current_date: Date for YAML frontmatter (YYYY-MM-DD)
        chart_filename: Optional chart filename to embed
        featured_image: Optional featured image path
        expected_output: Description of expected output format

    Returns:
        Dictionary with task configuration suitable for CrewAI Task class

    Example:
        >>> from crewai import Task, Agent
        >>> config = create_writer_task_config(
        ...     topic="AI Testing Trends",
        ...     research_brief={...},
        ...     current_date="2026-01-02"
        ... )
        >>> task = Task(**config, agent=writer_agent)
    """
    if expected_output is None:
        expected_output = """An Economist-style article with:
- YAML frontmatter (layout, title, date, author)
- Compelling opening with striking data point
- 3-4 body sections with clear headers
- Chart embedded naturally (if chart_filename provided)
- Strong closing with prediction or implication
- 800-1200 words
- British spelling throughout
- No banned phrases or clichés"""

    description = f"""Write an Economist-style article on "{topic}".

Current date: {current_date}
Chart available: {"Yes - MUST embed" if chart_filename else "No"}
Featured image: {"Yes" if featured_image else "No"}

Critical requirements:
- Lead with most striking data point from research
- Use British spelling (organisation, favour, analyse)
- No banned openings ("In today's world", "It's no secret")
- No banned closings ("In conclusion", "remains to be seen")
- Active voice and concrete language
- Chart must be embedded with natural reference (if provided)
- Strong, definitive closing (prediction or implication)

Style guidelines:
- 2-4 word punny title
- No exclamation points
- No listicle structure
- One analogy maximum
- Section headers: noun phrases, not questions"""

    return {
        "description": description,
        "expected_output": expected_output,
        "context": {
            "topic": topic,
            "research_brief": research_brief,
            "current_date": current_date,
            "chart_filename": chart_filename,
            "featured_image": featured_image,
        },
    }


def create_article_refinement_task_config(
    draft: str, validation_issues: list[str], expected_output: str | None = None
) -> dict[str, Any]:
    """Create a task configuration for refining an article draft.

    Args:
        draft: Initial article draft
        validation_issues: List of validation issues to fix
        expected_output: Description of expected output

    Returns:
        Dictionary with task configuration for refinement

    Example:
        >>> config = create_article_refinement_task_config(
        ...     draft="...",
        ...     validation_issues=["Missing chart embed", "Banned phrase: game-changer"]
        ... )
        >>> task = Task(**config, agent=writer_agent)
    """
    if expected_output is None:
        expected_output = """A refined article that:
- Fixes all validation issues
- Maintains original content quality
- Passes all style checks
- Is ready for publication"""

    issues_text = "\n".join([f"- {issue}" for issue in validation_issues])

    description = f"""Refine this article draft to fix validation issues:

VALIDATION ISSUES TO FIX:
{issues_text}

ORIGINAL DRAFT:
{draft[:500]}...

Requirements:
- Fix all listed issues
- Maintain Economist style
- Keep article structure intact
- Preserve key data points and arguments"""

    return {
        "description": description,
        "expected_output": expected_output,
        "context": {
            "draft": draft,
            "validation_issues": validation_issues,
        },
    }


def validate_article_structure(article: str) -> dict[str, Any]:
    """Validate article structure and content.

    Args:
        article: Complete article text with YAML frontmatter

    Returns:
        Dictionary with validation results:
        - has_frontmatter: bool
        - has_title: bool
        - has_date: bool
        - has_layout: bool
        - word_count: int
        - section_count: int
        - issues: list[str]

    Example:
        >>> results = validate_article_structure(article)
        >>> if results['issues']:
        ...     print(f"Found {len(results['issues'])} issues")
    """
    results = {
        "has_frontmatter": False,
        "has_title": False,
        "has_date": False,
        "has_layout": False,
        "word_count": 0,
        "section_count": 0,
        "issues": [],
    }

    # Check frontmatter
    if article.startswith("---"):
        results["has_frontmatter"] = True

        # Extract frontmatter
        try:
            end_marker = article.find("---", 3)
            if end_marker > 0:
                frontmatter = article[3:end_marker]

                if "title:" in frontmatter:
                    results["has_title"] = True
                else:
                    results["issues"].append("Missing title in frontmatter")

                if "date:" in frontmatter:
                    results["has_date"] = True
                else:
                    results["issues"].append("Missing date in frontmatter")

                if "layout:" in frontmatter:
                    results["has_layout"] = True
                else:
                    results["issues"].append("Missing layout in frontmatter")
        except Exception as e:
            results["issues"].append(f"Error parsing frontmatter: {e}")
    else:
        results["issues"].append("Missing YAML frontmatter")

    # Count words and sections
    words = article.split()
    results["word_count"] = len(words)

    # Count section headers (##)
    results["section_count"] = article.count("\n## ")

    # Check word count
    if results["word_count"] < 800:
        results["issues"].append(
            f"Article too short: {results['word_count']} words (target: 800-1200)"
        )
    elif results["word_count"] > 1200:
        results["issues"].append(
            f"Article too long: {results['word_count']} words (target: 800-1200)"
        )

    # Check for banned phrases
    banned_phrases = [
        "game-changer",
        "paradigm shift",
        "leverage" if " leverage " in article.lower() else None,
        "in conclusion",
        "in today's world",
        "it's no secret",
    ]

    for phrase in banned_phrases:
        if phrase and phrase.lower() in article.lower():
            results["issues"].append(f"Contains banned phrase: {phrase}")

    return results


def extract_chart_references(article: str) -> dict[str, Any]:
    """Extract chart references from article.

    Args:
        article: Article text

    Returns:
        Dictionary with:
        - chart_images: list[str] - Chart markdown references found
        - chart_mentions: int - Count of "chart" mentions in text
        - has_natural_reference: bool - Whether chart is referenced naturally

    Example:
        >>> refs = extract_chart_references(article)
        >>> if refs['chart_images'] and refs['chart_mentions'] == 0:
        ...     print("Chart embedded but not referenced in text!")
    """
    import re

    # Find chart images (markdown format)
    chart_pattern = r"!\[([^\]]+)\]\(([^)]+\.png)\)"
    chart_images = re.findall(chart_pattern, article)

    # Count chart mentions
    chart_mentions = article.lower().count("chart")
    chart_mentions += article.lower().count("figure")
    chart_mentions += article.lower().count("graph")

    # Check for natural references (e.g., "As the chart shows")
    natural_patterns = [
        r"as the chart shows",
        r"the chart reveals",
        r"according to the chart",
        r"the data shows",
    ]

    has_natural_reference = any(
        re.search(pattern, article.lower()) for pattern in natural_patterns
    )

    return {
        "chart_images": [img[1] for img in chart_images],  # Extract filenames
        "chart_mentions": chart_mentions,
        "has_natural_reference": has_natural_reference,
    }
