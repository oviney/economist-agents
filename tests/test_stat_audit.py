#!/usr/bin/env python3
"""Tests for Stage3Crew post-write stat audit.

Validates that fabricated statistics are tagged [UNVERIFIED] when they
don't appear in the research brief, and that verified stats pass through
cleanly.
"""

from src.agent_sdk._shared import (
    _extract_stats,
    parse_research_for_verification,
)
from src.agent_sdk._shared import (
    audit_article_stats as _audit_article_stats,
)


class TestExtractStats:
    """_extract_stats() regex extraction."""

    def test_extracts_percentages(self) -> None:
        text = "Teams report a 41% increase in bugs after adoption."
        stats = _extract_stats(text)
        assert len(stats) >= 1
        assert any("41%" in s for s in stats)

    def test_extracts_dollar_amounts(self) -> None:
        text = "The market reached $4.5 billion in 2025."
        stats = _extract_stats(text)
        assert len(stats) >= 1
        assert any("4.5" in s and "billion" in s.lower() for s in stats)

    def test_extracts_multipliers(self) -> None:
        text = "Complexity increased 2.1 times compared to manual code."
        stats = _extract_stats(text)
        assert len(stats) >= 1
        assert any("2.1" in s for s in stats)

    def test_empty_text_returns_empty(self) -> None:
        assert _extract_stats("") == []

    def test_no_stats_returns_empty(self) -> None:
        assert _extract_stats("This article has no numbers at all.") == []


class TestAuditArticleStats:
    """_audit_article_stats() removes sentences with fabricated stats."""

    def test_fabricated_stat_sentence_removed(self) -> None:
        research = "Teams report a 23% improvement in deployment speed."
        article = (
            "---\ntitle: Test\n---\n"
            "The study found a 41% increase in bugs after AI adoption. "
            "This is a clean sentence."
        )
        result = _audit_article_stats(article, research)
        assert "41%" not in result
        assert "clean sentence" in result

    def test_verified_stat_passes_cleanly(self) -> None:
        research = "Carnegie Mellon found a 41% increase in bugs."
        article = (
            "---\ntitle: Test\n---\n"
            "Researchers documented a 41% increase in production bugs."
        )
        result = _audit_article_stats(article, research)
        assert "41%" in result

    def test_multiple_stats_mixed(self) -> None:
        research = "Adoption reached 68% according to the survey."
        article = (
            "---\ntitle: Test\n---\n"
            "Adoption reached 68% globally. "
            "Meanwhile, bugs increased by 156% in the first year."
        )
        result = _audit_article_stats(article, research)
        # 68% is in research — sentence kept
        assert "68%" in result
        # 156% is NOT in research — sentence removed
        assert "156%" not in result

    def test_no_stats_in_article_returns_unchanged(self) -> None:
        research = "Some research data here with 50% stats."
        article = "---\ntitle: Test\n---\nThis article has no numbers."
        result = _audit_article_stats(article, research)
        assert "no numbers" in result

    def test_frontmatter_preserved(self) -> None:
        research = "No matching stats here."
        article = (
            "---\ntitle: Test\ndate: 2026-04-17\n---\nThe body has no numeric claims."
        )
        result = _audit_article_stats(article, research)
        assert "title: Test" in result
        assert "date: 2026-04-17" in result

    def test_references_section_preserved(self) -> None:
        research = "Adoption reached 50% globally."
        article = (
            "---\ntitle: Test\n---\n"
            "Adoption reached 50% globally.\n\n"
            "## References\n\n"
            "1. Study with 99% accuracy claim"
        )
        result = _audit_article_stats(article, research)
        assert "## References" in result
        assert "99%" in result  # References not audited


class TestParseResearchForVerification:
    """Stage3Crew._parse_research_for_verification() extracts URL+stat pairs."""

    def test_extracts_markdown_links_with_stats(self) -> None:
        research = (
            "According to [Carnegie Mellon Study](https://example.com/study), "
            "bugs increased by 41% after AI adoption."
        )
        result = parse_research_for_verification(research)
        assert len(result["data_points"]) >= 1
        assert result["data_points"][0]["url"] == "https://example.com/study"

    def test_no_links_returns_empty(self) -> None:
        research = "Some research text with 50% stats but no URLs."
        result = parse_research_for_verification(research)
        assert result["data_points"] == []
