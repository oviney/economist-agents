#!/usr/bin/env python3
"""Tests for Article Evaluator MCP Server (Story 18.1).

Validates that the MCP tool evaluate_article():
- Returns {score: float, feedback: list[str], pass: bool} for valid markdown
- Accepts an optional title parameter
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
        assert "score" in result
        assert "feedback" in result
        assert "pass" in result

    def test_no_error_key_on_success(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert "error" not in result

    def test_score_is_float(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert isinstance(result["score"], float)

    def test_score_in_valid_range(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert 0.0 <= result["score"] <= 100.0

    def test_feedback_is_list(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert isinstance(result["feedback"], list)

    def test_feedback_items_are_strings(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        for item in result["feedback"]:
            assert isinstance(item, str)

    def test_pass_is_bool(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert isinstance(result["pass"], bool)

    def test_good_article_passes(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert result["pass"] is True

    def test_good_article_scores_above_60(self) -> None:
        result = evaluate_article(GOOD_ARTICLE)
        assert result["score"] >= 60.0

    def test_bad_article_scores_below_50(self) -> None:
        result = evaluate_article(BAD_ARTICLE)
        assert result["score"] < 50.0

    def test_bad_article_does_not_pass(self) -> None:
        result = evaluate_article(BAD_ARTICLE)
        assert result["pass"] is False

    def test_feedback_has_five_dimensions(self) -> None:
        """Without a title argument, feedback should have one entry per dimension."""
        result = evaluate_article(GOOD_ARTICLE)
        assert len(result["feedback"]) == 5

    def test_pass_consistent_with_score(self) -> None:
        """pass must equal score >= 60.0."""
        result = evaluate_article(GOOD_ARTICLE)
        assert result["pass"] == (result["score"] >= 60.0)


# ═══════════════════════════════════════════════════════════════════════════
# Title parameter
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluateArticleWithTitle:
    """Tests for the optional title parameter."""

    def test_title_included_in_feedback(self) -> None:
        result = evaluate_article(GOOD_ARTICLE, title="My Custom Title")
        assert any("Title: My Custom Title" in item for item in result["feedback"])

    def test_title_is_first_feedback_item(self) -> None:
        result = evaluate_article(GOOD_ARTICLE, title="My Custom Title")
        assert len(result["feedback"]) > 0
        assert result["feedback"][0] == "Title: My Custom Title"

    def test_empty_title_not_added_to_feedback(self) -> None:
        result_no_title = evaluate_article(GOOD_ARTICLE)
        result_empty_title = evaluate_article(GOOD_ARTICLE, title="")
        assert len(result_no_title["feedback"]) == len(result_empty_title["feedback"])

    def test_whitespace_only_title_not_added(self) -> None:
        result = evaluate_article(GOOD_ARTICLE, title="   ")
        assert not any("Title:" in item for item in result["feedback"])
        assert len(result["feedback"]) == 5

    def test_title_does_not_affect_score(self) -> None:
        result_no_title = evaluate_article(GOOD_ARTICLE)
        result_with_title = evaluate_article(GOOD_ARTICLE, title="Some Title")
        assert result_no_title["score"] == result_with_title["score"]

    def test_feedback_with_title_has_six_items(self) -> None:
        result = evaluate_article(GOOD_ARTICLE, title="A Title")
        assert len(result["feedback"]) == 6


# ═══════════════════════════════════════════════════════════════════════════
# Error handling: malformed / edge-case input
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluateArticleErrorHandling:
    """Tests for evaluate_article() graceful error handling."""

    def test_empty_string_returns_error(self) -> None:
        result = evaluate_article("")
        assert "error" in result
        assert result["score"] == 0.0
        assert result["feedback"] == []
        assert result["pass"] is False

    def test_whitespace_only_returns_error(self) -> None:
        result = evaluate_article("   \n\t  ")
        assert "error" in result

    def test_non_string_returns_error(self) -> None:
        result = evaluate_article(None)  # type: ignore[arg-type]
        assert "error" in result
        assert result["score"] == 0.0
        assert result["pass"] is False

    def test_integer_input_returns_error(self) -> None:
        result = evaluate_article(42)  # type: ignore[arg-type]
        assert "error" in result

    def test_error_result_has_all_keys(self) -> None:
        result = evaluate_article("")
        for key in ("error", "score", "feedback", "pass"):
            assert key in result, f"Missing key: {key}"

    def test_minimal_valid_content(self) -> None:
        """Single word content should not crash — returns low scores."""
        result = evaluate_article("Hello world.")
        assert "error" not in result
        assert isinstance(result["score"], float)

    def test_no_frontmatter_content(self) -> None:
        """Bare markdown without YAML frontmatter is valid input."""
        article = (
            "## Overview\n\nOrganisations are investing in quality.\n\n## Summary\n\nResults vary."
        )
        result = evaluate_article(article)
        assert "error" not in result
        assert isinstance(result["feedback"], list)

    def test_malformed_frontmatter_does_not_crash(self) -> None:
        """Bad YAML frontmatter should degrade gracefully, not crash."""
        article = "---\ntitle: [unclosed\n---\n\nBody text here."
        result = evaluate_article(article)
        assert isinstance(result, dict)
        assert "score" in result


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

    def test_pass_threshold_is_60(self) -> None:
        from mcp_servers.article_evaluator_server import _PASS_THRESHOLD

        assert _PASS_THRESHOLD == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
