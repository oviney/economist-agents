"""Writer agent utilities — article structure validation and chart extraction.

The CrewAI-specific task-config builders that originally lived here
(``create_writer_task_config``, ``create_article_refinement_task_config``)
were removed when CrewAI was retired in favour of the Anthropic Agent SDK
(ADR-0006 Phase 2). The two pure-Python utilities below survived because
they're used by the writer-agent test suite and are framework-agnostic.
"""

from typing import Any


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
        "has_description": False,
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

                if "description:" in frontmatter:
                    results["has_description"] = True
                else:
                    results["issues"].append("Missing description in frontmatter")
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
            f"Article too short: {results['word_count']} words (target: 800-1200)",
        )
    elif results["word_count"] > 1200:
        results["issues"].append(
            f"Article too long: {results['word_count']} words (target: 800-1200)",
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
