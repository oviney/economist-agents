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


def make_test_article(refs: str) -> str:
    """Helper: build a minimal well-formed article with a given references block."""
    return (
        "---\n"
        "layout: post\n"
        'title: "Test Article"\n'
        "date: 2026-04-05\n"
        "categories: []\n"
        "image: x.png\n"
        "---\n\n"
        "According to a 2026 study by NIST, 73% of teams now use AI testing.\n\n"
        "## The Challenge\n\n"
        "Engineers at Google report a 40% reduction in flaky tests after adopting deterministic environments.\n\n"
        "## The Solution\n\n"
        "Infrastructure-first teams see 3x faster delivery according to the IEEE Software Engineering Standards 2025.\n\n"
        "## The Outcome\n\n"
        "Spotify's SRE team documented a 50% drop in incident response time after adopting chaos engineering.\n\n"
        + " ".join(["word"] * 300)
        + "\n\n## References\n\n"
        + refs
    )


class TestEvidenceSourcing:
    def test_sourced_article_scores_high(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(GOOD_ARTICLE)
        assert result.scores["evidence_sourcing"] >= 7

    def test_unsourced_article_scores_low(self, evaluator: ArticleEvaluator) -> None:
        result = evaluator.evaluate(BAD_ARTICLE)
        assert result.scores["evidence_sourcing"] <= 3

    def test_fresh_sources_score_higher_than_stale(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """Articles with 3+ references from current/previous year score higher."""
        fresh_refs = (
            "1. NIST, [\"NIST Report 2026\"](https://example.com), *NIST*, 2026\n"
            "2. Google, [\"Engineering Blog Post\"](https://example.com), *Google*, 2025\n"
            "3. IEEE, [\"Software Engineering Standards\"](https://example.com), *IEEE*, 2025\n"
            "4. Spotify, [\"SRE Case Study\"](https://example.com), *Spotify*, 2026\n"
            "5. arXiv, [\"Recent AI Testing Paper\"](https://example.com), *arXiv*, 2026\n"
        )
        stale_refs = (
            "1. Gartner, [\"World Quality Report 2022\"](https://example.com), *Gartner*, 2022\n"
            "2. Forrester, [\"Test Automation Study 2022\"](https://example.com), *Forrester*, 2022\n"
            "3. McKinsey, [\"Digital Report 2021\"](https://example.com), *McKinsey*, 2021\n"
            "4. IDC, [\"Market Analysis 2022\"](https://example.com), *IDC*, 2022\n"
            "5. BCG, [\"Tech Trends 2021\"](https://example.com), *BCG*, 2021\n"
        )
        fresh_result = evaluator.evaluate(make_test_article(fresh_refs))
        stale_result = evaluator.evaluate(make_test_article(stale_refs))
        assert fresh_result.scores["evidence_sourcing"] > stale_result.scores["evidence_sourcing"]

    def test_stale_sources_penalised(self, evaluator: ArticleEvaluator) -> None:
        """An article whose 5 references are all >2 years old loses 2 points."""
        stale_refs = (
            "1. Gartner, [\"World Quality Report 2022\"](https://example.com), *Gartner*, 2022\n"
            "2. Forrester, [\"Test Automation Study 2022\"](https://example.com), *Forrester*, 2022\n"
            "3. NIST, [\"NIST Framework 2023\"](https://example.com), *NIST*, 2023\n"
            "4. IEEE, [\"Standards 2023\"](https://example.com), *IEEE*, 2023\n"
            "5. Capgemini, [\"Quality Report 2022\"](https://example.com), *Capgemini*, 2022\n"
        )
        result = evaluator.evaluate(make_test_article(stale_refs))
        # 10 base - 2 (freshness penalty: 0 of 5 refs from current/prev year) = 8 max
        assert result.scores["evidence_sourcing"] <= 8  # freshness penalty applied

    def test_analyst_report_cap_enforced(self, evaluator: ArticleEvaluator) -> None:
        """Articles citing >1 analyst firm (Gartner, Forrester, etc.) are penalised."""
        single_analyst_refs = (
            "1. Gartner, [\"Report 2025\"](https://example.com), *Gartner*, 2025\n"
            "2. NIST, [\"Framework 2026\"](https://example.com), *NIST*, 2026\n"
            "3. Google, [\"Engineering Blog 2026\"](https://example.com), *Google*, 2026\n"
            "4. IEEE, [\"Standards 2025\"](https://example.com), *IEEE*, 2025\n"
            "5. arXiv, [\"AI Testing 2026\"](https://example.com), *arXiv*, 2026\n"
        )
        multi_analyst_refs = (
            "1. Gartner, [\"Report 2025\"](https://example.com), *Gartner*, 2025\n"
            "2. Forrester, [\"Study 2025\"](https://example.com), *Forrester*, 2025\n"
            "3. McKinsey, [\"Report 2026\"](https://example.com), *McKinsey*, 2026\n"
            "4. IEEE, [\"Standards 2025\"](https://example.com), *IEEE*, 2025\n"
            "5. BCG, [\"Trends 2025\"](https://example.com), *BCG*, 2025\n"
        )
        single = evaluator.evaluate(make_test_article(single_analyst_refs))
        multi = evaluator.evaluate(make_test_article(multi_analyst_refs))
        assert single.scores["evidence_sourcing"] > multi.scores["evidence_sourcing"]

    def test_detail_includes_freshness_and_analyst_info(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """Detail string reports fresh reference count and analyst report count."""
        result = evaluator.evaluate(GOOD_ARTICLE)
        detail = result.details["evidence_sourcing"]
        assert "fresh" in detail
        assert "analyst" in detail


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
