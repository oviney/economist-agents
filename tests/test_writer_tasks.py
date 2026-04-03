#!/usr/bin/env python3
"""Tests for writer_tasks module — article structure validation and chart extraction."""

import pytest

from agents.writer_tasks import (
    extract_chart_references,
    validate_article_structure,
)

# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def valid_article() -> str:
    """Minimal valid article with all required elements."""
    body = " ".join(["word"] * 850)
    return (
        '---\nlayout: post\ntitle: "Test Article Title Here"\n'
        'date: 2026-04-03\nauthor: "The Economist"\n'
        'categories: ["quality-engineering"]\n---\n\n'
        f"## Section One\n\n{body}\n\n## Section Two\n\nMore content.\n"
    )


@pytest.fixture
def short_article() -> str:
    """Article under the 800-word minimum."""
    body = " ".join(["word"] * 100)
    return f'---\nlayout: post\ntitle: "Short"\ndate: 2026-04-03\n---\n\n{body}\n'


@pytest.fixture
def no_frontmatter_article() -> str:
    """Article with no YAML frontmatter at all."""
    body = " ".join(["word"] * 850)
    return f"# Just a Heading\n\n{body}\n"


@pytest.fixture
def banned_phrase_article() -> str:
    """Article containing banned phrases."""
    body = " ".join(["word"] * 850)
    return (
        '---\nlayout: post\ntitle: "Valid Title Here Today"\n'
        "date: 2026-04-03\n---\n\n"
        f"In conclusion, this is a game-changer. {body}\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# validate_article_structure TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateArticleStructure:
    """Tests for validate_article_structure()."""

    def test_valid_article_no_issues(self, valid_article: str) -> None:
        result = validate_article_structure(valid_article)
        assert result["has_frontmatter"] is True
        assert result["has_title"] is True
        assert result["has_date"] is True
        assert result["has_layout"] is True
        assert result["word_count"] >= 800
        assert result["section_count"] >= 1

    def test_missing_frontmatter(self, no_frontmatter_article: str) -> None:
        result = validate_article_structure(no_frontmatter_article)
        assert result["has_frontmatter"] is False
        assert "Missing YAML frontmatter" in result["issues"]

    def test_short_article_flagged(self, short_article: str) -> None:
        result = validate_article_structure(short_article)
        assert any("too short" in i for i in result["issues"])

    def test_banned_phrases_detected(self, banned_phrase_article: str) -> None:
        result = validate_article_structure(banned_phrase_article)
        assert any("game-changer" in i for i in result["issues"])
        assert any("in conclusion" in i.lower() for i in result["issues"])

    def test_missing_title_field(self) -> None:
        article = "---\nlayout: post\ndate: 2026-04-03\n---\n\n" + " ".join(
            ["word"] * 850
        )
        result = validate_article_structure(article)
        assert result["has_title"] is False
        assert any("Missing title" in i for i in result["issues"])

    def test_missing_date_field(self) -> None:
        article = '---\nlayout: post\ntitle: "Test"\n---\n\n' + " ".join(["word"] * 850)
        result = validate_article_structure(article)
        assert result["has_date"] is False

    def test_missing_layout_field(self) -> None:
        article = '---\ntitle: "Test"\ndate: 2026-04-03\n---\n\n' + " ".join(
            ["word"] * 850
        )
        result = validate_article_structure(article)
        assert result["has_layout"] is False

    def test_long_article_flagged(self) -> None:
        body = " ".join(["word"] * 1300)
        article = '---\nlayout: post\ntitle: "X"\ndate: 2026-04-03\n---\n\n' + body
        result = validate_article_structure(article)
        assert any("too long" in i for i in result["issues"])

    def test_section_count(self) -> None:
        body = " ".join(["word"] * 850)
        article = (
            '---\nlayout: post\ntitle: "X"\ndate: 2026-04-03\n---\n\n'
            f"## A\n\n{body}\n\n## B\n\nMore.\n\n## C\n\nEnd.\n"
        )
        result = validate_article_structure(article)
        assert result["section_count"] == 3


# ═══════════════════════════════════════════════════════════════════════════
# extract_chart_references TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractChartReferences:
    """Tests for extract_chart_references()."""

    def test_no_charts(self) -> None:
        result = extract_chart_references("Just plain text, no images here.")
        assert result["chart_images"] == []
        assert result["chart_mentions"] == 0
        assert result["has_natural_reference"] is False

    def test_single_chart(self) -> None:
        article = "Some text\n\n![Chart Title](/assets/charts/test.png)\n\nMore text"
        result = extract_chart_references(article)
        assert len(result["chart_images"]) == 1
        assert result["chart_images"][0] == "/assets/charts/test.png"

    def test_multiple_charts(self) -> None:
        article = "![A](/a.png)\n\nText\n\n![B](/b.png)\n"
        result = extract_chart_references(article)
        assert len(result["chart_images"]) == 2

    def test_natural_reference_detected(self) -> None:
        article = (
            "As the chart shows, testing adoption is rising.\n\n![Chart](/test.png)"
        )
        result = extract_chart_references(article)
        assert result["has_natural_reference"] is True

    def test_chart_mentions_counted(self) -> None:
        article = "The chart below shows the data. See figure 1 and graph 2."
        result = extract_chart_references(article)
        assert result["chart_mentions"] == 3  # chart + figure + graph


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
