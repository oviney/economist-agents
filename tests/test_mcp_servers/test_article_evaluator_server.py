#!/usr/bin/env python3
"""Tests for Article Evaluator MCP Server (Story 18.1).

Validates that the MCP tool evaluate_article():
- Returns correct 5-dimension scores for valid markdown
- Returns structured error dicts (not exceptions) for bad input
- Covers >80% of mcp_servers/article_evaluator_server.py
"""

import pytest

from mcp_servers.article_evaluator_server import evaluate_article

# ═══════════════════════════════════════════════════════════════════════════
# Shared fixtures / constants
# ═══════════════════════════════════════════════════════════════════════════

GOOD_ARTICLE = """---
layout: post
title: "The Hidden Cost of Test Automation"
date: 2026-04-04
author: "The Economist"
categories: ["Quality Engineering"]
image: /assets/images/test-automation.png
---

According to Gartner's 2024 survey, 73% of organisations now use test automation, yet 60% report rising maintenance costs.

## The Maintenance Trap

Forrester's 2024 analysis shows maintenance consumes 40% of QA budgets in large enterprises.

## The Skills Gap

Hiring automation engineers costs 25% more than traditional QA roles, per Deloitte's 2024 report.

## The Alternative

Infrastructure-first teams report 3x faster delivery, according to IEEE Software Engineering Standards 2024.

![Test Automation Costs](/assets/charts/test-costs.png)

As the chart illustrates, maintenance costs have grown steadily since 2020.

## References

1. Gartner, "World Quality Report 2024", 2024
2. Forrester, "Test Automation ROI Study", 2024
3. Deloitte, "Technology Workforce Report", 2024
4. IEEE, "Software Engineering Standards", 2024
5. Capgemini, "Digital Engineering Report", 2024
""" + " ".join(["word"] * 500)

BAD_ARTICLE = """---
title: "Test"
---

In today's world, testing is a game-changer. Studies show this is important. [NEEDS SOURCE]

Short article with no headings, no references, no image.
"""


# ═══════════════════════════════════════════════════════════════════════════
# Happy-path: valid article input
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluateArticleValidInput:
    """Tests for evaluate_article() with valid markdown content."""

    def test_returns_dict(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert isinstance(result, dict)

    def test_has_required_keys(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert "scores" in result
        assert "total_score" in result
        assert "max_score" in result
        assert "percentage" in result
        assert "details" in result

    def test_no_error_key_on_success(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert "error" not in result

    def test_five_dimension_scores(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        expected_dims = {
            "opening_quality",
            "evidence_sourcing",
            "voice_consistency",
            "structure",
            "visual_engagement",
        }
        assert set(result["scores"].keys()) == expected_dims

    def test_scores_are_integers_in_range(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        for dim, score in result["scores"].items():
            assert isinstance(score, int), f"{dim} score is not int"
            assert 1 <= score <= 10, f"{dim} score {score} out of range [1,10]"

    def test_max_score_is_50(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert result["max_score"] == 50

    def test_total_score_matches_sum(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert result["total_score"] == sum(result["scores"].values())

    def test_percentage_is_correct(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        expected = round(result["total_score"] / 50 * 100)
        assert result["percentage"] == expected

    def test_details_has_five_dimensions(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert len(result["details"]) == 5

    def test_details_are_strings(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        for dim, text in result["details"].items():
            assert isinstance(text, str), f"{dim} detail is not str"

    def test_good_article_scores_above_60_percent(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert result["percentage"] >= 60

    def test_bad_article_scores_below_50_percent(self) -> None:
        result = evaluate_article(BAD_ARTICLE)
        assert result["percentage"] < 50

    def test_bad_article_returns_five_dimensions(self) -> None:
        result = evaluate_article(BAD_ARTICLE)
        assert len(result["scores"]) == 5


# ═══════════════════════════════════════════════════════════════════════════
# Error handling: malformed / edge-case input
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluateArticleErrorHandling:
    """Tests for evaluate_article() graceful error handling."""

    def test_empty_string_returns_error(self) -> None:
        result = evaluate_article("")
        assert "error" in result
        assert result["scores"] == {}
        assert result["total_score"] == 0
        assert result["max_score"] == 50
        assert result["percentage"] == 0

    def test_whitespace_only_returns_error(self) -> None:
        result = evaluate_article("   \n\t  ")
        assert "error" in result

    def test_non_string_returns_error(self) -> None:
        result = evaluate_article(None)  # type: ignore[arg-type]
        assert "error" in result
        assert result["scores"] == {}
        assert result["percentage"] == 0

    def test_integer_input_returns_error(self) -> None:
        result = evaluate_article(42)  # type: ignore[arg-type]
        assert "error" in result

    def test_error_result_has_all_keys(self) -> None:
        result = evaluate_article("")
        for key in ("error", "scores", "total_score", "max_score", "percentage", "details"):
            assert key in result, f"Missing key: {key}"

    def test_minimal_valid_content(self) -> None:
        """Single word content should not crash — returns low scores."""
        result = evaluate_article("Hello world.")
        assert "error" not in result
        assert result["total_score"] >= 0

    def test_no_frontmatter_content(self) -> None:
        """Bare markdown without YAML frontmatter is valid input."""
        article = (
            "## Overview\n\nOrganisations are investing in quality.\n\n## Summary\n\nResults vary."
        )
        result = evaluate_article(article)
        assert "error" not in result
        assert len(result["scores"]) == 5

    def test_malformed_frontmatter_does_not_crash(self) -> None:
        """Bad YAML frontmatter should degrade gracefully, not crash."""
        article = "---\ntitle: [unclosed\n---\n\nBody text here."
        result = evaluate_article(article)
        # Should return scores (possibly low), not an error
        assert isinstance(result, dict)
        assert "scores" in result


# ═══════════════════════════════════════════════════════════════════════════
# Tool metadata
# ═══════════════════════════════════════════════════════════════════════════


class TestToolMetadata:
    """Checks that the FastMCP tool is properly decorated and importable."""

    def test_evaluate_article_is_callable(self) -> None:
        assert callable(evaluate_article)

    def test_evaluate_article_has_docstring(self) -> None:
        assert evaluate_article.__doc__ is not None
        assert len(evaluate_article.__doc__) > 10

    def test_mcp_server_importable(self) -> None:
        from mcp_servers import article_evaluator_server  # noqa: F401

        assert article_evaluator_server.mcp is not None

    def test_evaluator_singleton_exists(self) -> None:
        from mcp_servers.article_evaluator_server import _evaluator

        assert _evaluator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
