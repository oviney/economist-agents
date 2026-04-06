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

According to DORA's 2026 State of DevOps report, 73% of organisations now use test automation, yet 60% report rising maintenance costs — a paradox that demands scrutiny.

## The Maintenance Trap

Test automation frameworks promise efficiency but deliver complexity. Google's 2025 engineering blog analysis shows maintenance consumes 40% of QA budgets in large enterprises. The scripts that once saved time now demand constant updates as interfaces evolve.

## The Skills Gap

Hiring automation engineers costs 25% more than traditional QA roles, per a 2026 IEEE survey of 1,200 software teams. The talent shortage compounds the cost problem, forcing organisations to choose between expensive specialists and undertrained generalists.

## The Alternative

Infrastructure-first teams report 3x faster delivery with 5x fewer production incidents, according to a 2025 arXiv paper on continuous testing practices. They invest in deterministic environments rather than brittle scripts.

![Test Automation Costs](/assets/charts/test-costs.png)

As the chart illustrates, maintenance costs have grown steadily since 2020 while productivity gains plateau.

The organisations that thrive will be those that treat test infrastructure as a strategic investment, not an automation checkbox. Those that chase vendor promises without measuring real returns will find themselves paying more for diminishing gains.

## References

1. DORA, ["State of DevOps 2026"](https://dora.dev), *DORA Research*, 2026
2. Google, ["Engineering Productivity at Scale"](https://example.com), *Google Engineering Blog*, 2025
3. IEEE, ["Software Engineering Workforce Survey"](https://example.com), *IEEE*, 2026
4. arXiv, ["Continuous Testing in CI/CD Pipelines"](https://arxiv.org), *arXiv*, 2025
5. Gartner, ["Magic Quadrant for Test Automation"](https://example.com), *Gartner*, 2025
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

    def test_abstract_noun_opening_scores_low(self, evaluator: ArticleEvaluator) -> None:
        article = "---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\nThe arrival of AI tools has changed testing.\n\nMore content here."
        result = evaluator.evaluate(article)
        assert result.scores["opening_quality"] <= 3

    def test_emergence_opening_scores_low(self, evaluator: ArticleEvaluator) -> None:
        article = "---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\nThe emergence of cloud computing demands scrutiny.\n\nMore content here."
        result = evaluator.evaluate(article)
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

    def test_hedging_phrases_penalised(self, evaluator: ArticleEvaluator) -> None:
        article = "---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\nQuality matters. It is worth noting that teams struggle. It should be noted that costs rise. One might argue otherwise.\n"
        result = evaluator.evaluate(article)
        assert result.scores["voice_consistency"] <= 7  # 3 hedging phrases = -3


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

    def test_excessive_headings_penalised(self, evaluator: ArticleEvaluator) -> None:
        headings = "\n\n".join(f"## Section {i}\n\nParagraph {i}." for i in range(1, 8))
        body = f"Opening sentence with data: 42% of teams fail.\n\n{headings}\n\n## References\n\n1. Source A\n2. Source B\n3. Source C\n4. Source D\n5. Source E\n"
        article = f"---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\n{body}" + " ".join(["word"] * 600)
        result_many = evaluator.evaluate(article)
        # 7 headings (>5) → -2 penalty vs same article with 4 headings
        few_headings = "\n\n".join(f"## Section {i}\n\nParagraph {i}." for i in range(1, 4))
        article_few = f"---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\nOpening sentence with data: 42% of teams fail.\n\n{few_headings}\n\n## References\n\n1. Source A\n2. Source B\n3. Source C\n4. Source D\n5. Source E\n" + " ".join(["word"] * 600)
        result_few = evaluator.evaluate(article_few)
        assert result_many.scores["structure"] < result_few.scores["structure"]

    def test_list_formatting_penalised(self, evaluator: ArticleEvaluator) -> None:
        list_body = "Opening with 42% data.\n\n## Section One\n\nHere are the steps:\n\n- Step one\n- Step two\n- Step three\n- Step four\n\n## Section Two\n\nMore content.\n\n## References\n\n1. Ref A\n2. Ref B\n3. Ref C\n"
        article = f"---\nlayout: post\ntitle: Test\ndate: 2026-04-05\ncategories: []\nimage: x.png\n---\n\n{list_body}" + " ".join(["word"] * 600)
        result = evaluator.evaluate(article)
        # 4 list items in prose → -2 penalty
        assert result.scores["structure"] <= 8


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
