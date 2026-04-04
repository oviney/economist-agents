#!/usr/bin/env python3
"""Tests for Article Evaluator (Story #116).

Validates the 5-dimension scoring framework for generated articles.
"""

import time

import pytest

from scripts.article_evaluator import ArticleEvaluator

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

GOOD_ARTICLE = """---
layout: post
title: "The Hidden Cost of Test Automation"
date: 2026-04-04
author: "The Economist"
categories: ["Quality Engineering", "Test Automation"]
image: /assets/images/test-automation.png
---

According to Gartner's 2024 survey, 73% of organisations now use test automation, yet 60% report rising maintenance costs — a paradox that demands scrutiny.

## The Maintenance Trap

Test automation frameworks promise efficiency but deliver complexity. Forrester's 2024 analysis shows maintenance consumes 40% of QA budgets in large enterprises. The scripts that once saved time now demand constant updates as interfaces evolve.

## The Skills Gap

Hiring automation engineers costs 25% more than traditional QA roles, per Deloitte's 2024 technology workforce report. The talent shortage compounds the cost problem, forcing organisations to choose between expensive specialists and undertrained generalists.

## The Alternative

Infrastructure-first teams report 3x faster delivery with 5x fewer production incidents, according to the IEEE Software Engineering Standards 2024 report. They invest in deterministic environments rather than brittle scripts.

![Test Automation Costs](/assets/charts/test-costs.png)

As the chart illustrates, maintenance costs have grown steadily since 2020 while productivity gains plateau.

The organisations that thrive will be those that treat test infrastructure as a strategic investment, not an automation checkbox. Those that chase vendor promises without measuring real returns will find themselves paying more for diminishing gains.

## References

1. Gartner, ["World Quality Report 2024"](https://example.com), *Gartner Research*, 2024
2. Forrester, ["Test Automation ROI Study"](https://example.com), *Forrester*, 2024
3. Deloitte, ["Technology Workforce Report"](https://example.com), *Deloitte*, 2024
4. IEEE, ["Software Engineering Standards"](https://example.com), *IEEE*, 2024
5. Capgemini, ["Digital Engineering Report"](https://example.com), *Capgemini*, 2024
""" + " ".join(["word"] * 500)


BAD_ARTICLE = """---
title: "Test"
date: April 4
---

In today's world, testing is a game-changer. It's no secret that paradigm shifts
happen. Studies show this is important. [NEEDS SOURCE]

Short article with no headings, no references, no image.
"""


@pytest.fixture
def evaluator() -> ArticleEvaluator:
    return ArticleEvaluator()


# ═══════════════════════════════════════════════════════════════════════════
# Dimension 1: Opening Quality
# ═══════════════════════════════════════════════════════════════════════════


class TestOpeningQuality:
    def test_strong_data_hook_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["opening_quality"] >= 7

    def test_banned_opening_scores_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["opening_quality"] <= 3


# ═══════════════════════════════════════════════════════════════════════════
# Dimension 2: Evidence Sourcing
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceSourcing:
    def test_sourced_article_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["evidence_sourcing"] >= 7

    def test_unsourced_article_scores_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["evidence_sourcing"] <= 3


# ═══════════════════════════════════════════════════════════════════════════
# Dimension 3: Voice Consistency
# ═══════════════════════════════════════════════════════════════════════════


class TestVoiceConsistency:
    def test_british_spelling_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["voice_consistency"] >= 7

    def test_banned_phrases_score_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["voice_consistency"] <= 7  # 2 banned phrases = -4


# ═══════════════════════════════════════════════════════════════════════════
# Dimension 4: Structure
# ═══════════════════════════════════════════════════════════════════════════


class TestStructure:
    def test_well_structured_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["structure"] >= 7

    def test_poor_structure_scores_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["structure"] <= 3


# ═══════════════════════════════════════════════════════════════════════════
# Dimension 5: Visual Engagement
# ═══════════════════════════════════════════════════════════════════════════


class TestVisualEngagement:
    def test_image_and_chart_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["visual_engagement"] >= 7

    def test_no_visuals_scores_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["visual_engagement"] <= 5  # Base 4, no image/chart


# ═══════════════════════════════════════════════════════════════════════════
# Overall scoring
# ═══════════════════════════════════════════════════════════════════════════


class TestOverallScoring:
    def test_total_score_is_sum(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.total_score == sum(result.scores.values())

    def test_max_score_is_50(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.max_score == 50

    def test_percentage_calculated(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        expected_pct = round(result.total_score / 50 * 100)
        assert result.percentage == expected_pct

    def test_good_article_above_70_pct(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.percentage >= 70

    def test_bad_article_below_50_pct(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.percentage < 50

    def test_details_populated(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert len(result.details) == 5
        assert all(isinstance(v, str) for v in result.details.values())


# ═══════════════════════════════════════════════════════════════════════════
# Performance
# ═══════════════════════════════════════════════════════════════════════════


class TestPerformance:
    def test_evaluation_under_5_seconds(self, evaluator: ArticleEvaluator) -> None:
        start = time.perf_counter()
        evaluator.evaluate(GOOD_ARTICLE)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Evaluation took {elapsed:.1f}s (max 5s)"


# ═══════════════════════════════════════════════════════════════════════════
# Persistence
# ═══════════════════════════════════════════════════════════════════════════


class TestPersistence:
    def test_to_dict_serializable(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        d = result.to_dict()
        assert "scores" in d
        assert "total_score" in d
        assert "percentage" in d
        assert "details" in d
        assert "timestamp" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
