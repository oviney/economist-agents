#!/usr/bin/env python3
"""Tests for Stage3Crew post-write stat audit.

Validates that fabricated statistics are tagged [UNVERIFIED] when they
don't appear in the research brief, and that verified stats pass through
cleanly.
"""

import pytest

from src.crews.stage3_crew import _audit_article_stats, _extract_stats


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
    """_audit_article_stats() tags fabricated stats."""

    def test_fabricated_stat_tagged_unverified(self) -> None:
        research = "Teams report a 23% improvement in deployment speed."
        article = (
            "---\ntitle: Test\n---\n"
            "The study found a 41% increase in bugs after AI adoption."
        )
        result = _audit_article_stats(article, research)
        assert "[UNVERIFIED]" in result
        assert "41%" in result

    def test_verified_stat_passes_cleanly(self) -> None:
        research = "Carnegie Mellon found a 41% increase in bugs."
        article = (
            "---\ntitle: Test\n---\n"
            "Researchers documented a 41% increase in production bugs."
        )
        result = _audit_article_stats(article, research)
        assert "[UNVERIFIED]" not in result

    def test_multiple_stats_mixed(self) -> None:
        research = "Adoption reached 68% according to the survey."
        article = (
            "---\ntitle: Test\n---\n"
            "Adoption reached 68% globally. "
            "Meanwhile, bugs increased by 156% in the first year."
        )
        result = _audit_article_stats(article, research)
        # 68% is in research — should not be tagged
        assert "68%" in result
        assert "68% [UNVERIFIED]" not in result
        # 156% is NOT in research — should be tagged
        assert "156% [UNVERIFIED]" in result

    def test_no_stats_in_article_returns_unchanged(self) -> None:
        research = "Some research data here with 50% stats."
        article = "---\ntitle: Test\n---\nThis article has no numbers."
        result = _audit_article_stats(article, research)
        assert result == article

    def test_frontmatter_stats_not_audited(self) -> None:
        """Stats in frontmatter (like dates) should not be tagged."""
        research = "No matching stats here."
        article = (
            "---\ntitle: Test\ndate: 2026-04-17\n---\n"
            "The body has no numeric claims."
        )
        result = _audit_article_stats(article, research)
        assert "[UNVERIFIED]" not in result

    def test_already_tagged_not_double_tagged(self) -> None:
        research = "No matching stats."
        article = (
            "---\ntitle: Test\n---\n"
            "The rate was 75% [UNVERIFIED] according to sources."
        )
        result = _audit_article_stats(article, research)
        assert result.count("[UNVERIFIED]") == 1


class TestParseResearchForVerification:
    """Stage3Crew._parse_research_for_verification() extracts URL+stat pairs."""

    def test_extracts_markdown_links_with_stats(self) -> None:
        from src.crews.stage3_crew import Stage3Crew

        research = (
            "According to [Carnegie Mellon Study](https://example.com/study), "
            "bugs increased by 41% after AI adoption."
        )
        result = Stage3Crew._parse_research_for_verification(research)
        assert len(result["data_points"]) >= 1
        assert result["data_points"][0]["url"] == "https://example.com/study"

    def test_no_links_returns_empty(self) -> None:
        from src.crews.stage3_crew import Stage3Crew

        research = "Some research text with 50% stats but no URLs."
        result = Stage3Crew._parse_research_for_verification(research)
        assert result["data_points"] == []
