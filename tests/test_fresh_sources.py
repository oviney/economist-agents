#!/usr/bin/env python3
"""
Tests for source freshness and analyst-diversity checks in ArticleEvaluator.

Story #137: Upgrade research agent with fresh source requirements.
Tests the new source freshness scoring in the evidence_sourcing dimension.

Usage::

    pytest tests/test_fresh_sources.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.article_evaluator import (
    _ANALYST_VENDORS,
    _FRESH_YEARS,
    _STALE_CUTOFF_YEAR,
    ArticleEvaluator,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CURRENT_YEAR = datetime.now().year
_PREV_YEAR = _CURRENT_YEAR - 1


def _make_article(
    references: str = "",
    body_extra: str = "",
    title: str = "AI Testing: The Hidden Cost",
    date: str | None = None,
) -> str:
    """Build a minimal valid article with the given references section.

    Args:
        references: Content of the ## References section (numbered list).
        body_extra: Additional body text (e.g., inline citations with years).
        title: Article title for frontmatter.
        date: Article date; defaults to today.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Body with a data-driven opening (avoids opening quality deductions)
    opening = (
        f"According to a {_CURRENT_YEAR} study, 73% of organisations now use test automation, "
        "yet 60% report rising maintenance costs."
    )
    heading = "## The Maintenance Trap\n\n"
    body = f"{opening}\n\n{heading}{body_extra}\n\n"
    refs_section = f"## References\n\n{references}\n" if references else ""

    # Pad to meet minimum word count requirements in other dimensions
    padding = " ".join(["word"] * 200)

    return (
        f"---\n"
        f"layout: post\n"
        f'title: "{title}"\n'
        f"date: {date}\n"
        f"author: Test\n"
        f'categories: ["Quality Engineering"]\n'
        f"image: /assets/images/test.png\n"
        f"---\n\n"
        f"{body}{padding}\n\n{refs_section}"
    )


@pytest.fixture
def evaluator() -> ArticleEvaluator:
    """Return an ArticleEvaluator instance."""
    return ArticleEvaluator()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: constant sanity-checks
# ─────────────────────────────────────────────────────────────────────────────


class TestFreshnessConstants:
    """Verify the freshness constants are coherent with the current year."""

    def test_fresh_years_contain_current_and_previous(self) -> None:
        """_FRESH_YEARS must contain the current year and the previous year."""
        assert str(_CURRENT_YEAR) in _FRESH_YEARS
        assert str(_PREV_YEAR) in _FRESH_YEARS

    def test_stale_cutoff_is_two_years_ago(self) -> None:
        """_STALE_CUTOFF_YEAR should be exactly 2 years before current year."""
        assert _STALE_CUTOFF_YEAR == _CURRENT_YEAR - 2

    def test_analyst_vendors_list_is_non_empty(self) -> None:
        """_ANALYST_VENDORS must include the known stale-source offenders."""
        for vendor in ("gartner", "forrester", "capgemini"):
            assert vendor in _ANALYST_VENDORS


# ─────────────────────────────────────────────────────────────────────────────
# Tests: evidence_sourcing score — freshness dimension
# ─────────────────────────────────────────────────────────────────────────────


class TestEvidenceFreshness:
    """Test the freshness checks added to _score_evidence."""

    def test_article_with_fresh_sources_scores_well(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """An article with multiple current-year references should not lose freshness points."""
        references = (
            f'1. DORA, ["State of DevOps {_CURRENT_YEAR}"](https://dora.dev), DORA, {_CURRENT_YEAR}\n'
            f'2. Google, ["Testing at Scale"](https://eng.google), Google Engineering, {_CURRENT_YEAR}\n'
            f'3. arXiv, ["Neural test generation"](https://arxiv.org/), arXiv, {_PREV_YEAR}\n'
        )
        body_extra = (
            f"DORA {_CURRENT_YEAR} survey. Google Engineering {_CURRENT_YEAR} report."
        )
        article = _make_article(references=references, body_extra=body_extra)
        result = evaluator.evaluate(article)
        # Fresh sources should not deduct freshness points
        detail = result.details.get("evidence_sourcing", "")
        assert "fresh citations" in detail
        # Score should not have freshness penalty (no deduction for fresh)
        score = result.scores["evidence_sourcing"]
        assert score >= 5  # Should be healthy

    def test_article_with_no_recent_sources_is_penalised(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """An article citing only stale 2023 sources should score lower."""
        stale_article = _make_article(
            references=(
                '1. Gartner, ["Magic Quadrant 2023"](https://gartner.com), Gartner, 2023\n'
                '2. Forrester, ["Test ROI 2023"](https://forrester.com), Forrester, 2023\n'
                '3. Capgemini, ["WQR 2022"](https://cap.com), Capgemini, 2022\n'
            ),
            body_extra="Gartner 2023 said 73%. Forrester 2023 analysis. Capgemini 2022 survey.",
        )
        fresh_article = _make_article(
            references=(
                f'1. DORA, ["Report {_CURRENT_YEAR}"](https://dora.dev), DORA, {_CURRENT_YEAR}\n'
                f'2. Google, ["Blog post"](https://eng.google), Google, {_CURRENT_YEAR}\n'
                f'3. arXiv, ["Paper"](https://arxiv.org), arXiv, {_PREV_YEAR}\n'
            ),
            body_extra=f"DORA {_CURRENT_YEAR} data. Google {_CURRENT_YEAR} findings.",
        )
        stale_result = evaluator.evaluate(stale_article)
        fresh_result = evaluator.evaluate(fresh_article)

        stale_score = stale_result.scores["evidence_sourcing"]
        fresh_score = fresh_result.scores["evidence_sourcing"]
        assert fresh_score > stale_score, (
            f"Fresh article ({fresh_score}) should outscore stale article ({stale_score})"
        )

    def test_detail_includes_freshness_info(self, evaluator: ArticleEvaluator) -> None:
        """_detail_evidence must report fresh citation count in detail string."""
        article = _make_article(
            references=f'1. DORA, ["State {_CURRENT_YEAR}"](https://dora.dev), {_CURRENT_YEAR}\n',
            body_extra=f"DORA {_CURRENT_YEAR} survey data.",
        )
        result = evaluator.evaluate(article)
        detail = result.details["evidence_sourcing"]
        assert "fresh citations" in detail
        assert "analyst vendors cited" in detail


# ─────────────────────────────────────────────────────────────────────────────
# Tests: evidence_sourcing score — analyst diversity dimension
# ─────────────────────────────────────────────────────────────────────────────


class TestAnalystDiversity:
    """Test penalisation when more than 1 analyst vendor is cited."""

    def test_single_analyst_vendor_not_penalised(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """Citing exactly one analyst vendor should not trigger the diversity penalty."""
        article = _make_article(
            references=(
                f'1. Gartner, ["Magic Quadrant {_CURRENT_YEAR}"](https://gartner.com), Gartner, {_CURRENT_YEAR}\n'
                f'2. DORA, ["State of DevOps {_CURRENT_YEAR}"](https://dora.dev), {_CURRENT_YEAR}\n'
                f'3. arXiv, ["Paper"](https://arxiv.org), arXiv, {_PREV_YEAR}\n'
            ),
            body_extra=f"Gartner {_CURRENT_YEAR} data. DORA survey.",
        )
        result = evaluator.evaluate(article)
        detail = result.details["evidence_sourcing"]
        assert "analyst vendors cited: 1" in detail

    def test_multiple_analyst_vendors_are_penalised(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """Citing 3 different analyst vendors should reduce the evidence score."""
        single_vendor_article = _make_article(
            references=(
                f'1. Gartner, ["Report {_CURRENT_YEAR}"](https://gartner.com), {_CURRENT_YEAR}\n'
                f'2. DORA, ["State of DevOps {_CURRENT_YEAR}"](https://dora.dev), {_CURRENT_YEAR}\n'
                f'3. arXiv, ["Paper"](https://arxiv.org), {_PREV_YEAR}\n'
            ),
            body_extra=f"Gartner data. DORA report {_CURRENT_YEAR}.",
        )
        multi_vendor_article = _make_article(
            references=(
                f'1. Gartner, ["Magic Quadrant {_CURRENT_YEAR}"](https://g.com), {_CURRENT_YEAR}\n'
                '2. Forrester, ["Wave Report 2023"](https://f.com), 2023\n'
                '3. Capgemini, ["WQR 2023"](https://c.com), 2023\n'
            ),
            body_extra="Gartner data. Forrester analysis. Capgemini survey.",
        )
        single_result = evaluator.evaluate(single_vendor_article)
        multi_result = evaluator.evaluate(multi_vendor_article)

        single_score = single_result.scores["evidence_sourcing"]
        multi_score = multi_result.scores["evidence_sourcing"]
        assert single_score >= multi_score, (
            f"Single-vendor ({single_score}) should score >= multi-vendor ({multi_score})"
        )

    def test_detail_shows_analyst_vendor_count(
        self, evaluator: ArticleEvaluator
    ) -> None:
        """Detail string should include the number of analyst vendors cited."""
        article = _make_article(
            body_extra="Gartner report. Forrester analysis. Capgemini data.",
        )
        result = evaluator.evaluate(article)
        detail = result.details["evidence_sourcing"]
        assert "analyst vendors cited" in detail
        # We cited gartner, forrester, capgemini → 3
        assert "analyst vendors cited: 3" in detail


# ─────────────────────────────────────────────────────────────────────────────
# Tests: RESEARCH_AGENT_PROMPT freshness requirements
# ─────────────────────────────────────────────────────────────────────────────


class TestResearchAgentPrompt:
    """Verify the research agent prompt contains the required freshness language."""

    def test_prompt_references_skill_file(self) -> None:
        """RESEARCH_AGENT_PROMPT must reference the sourcing skill file."""
        from agents.research_agent import RESEARCH_AGENT_PROMPT

        assert "skills/research-sourcing/SKILL.md" in RESEARCH_AGENT_PROMPT

    def test_prompt_requires_fresh_sources(self) -> None:
        """RESEARCH_AGENT_PROMPT must include year freshness requirements."""
        from agents.research_agent import RESEARCH_AGENT_PROMPT

        # Should require references from current or previous year
        assert "2025-2026" in RESEARCH_AGENT_PROMPT or "2026" in RESEARCH_AGENT_PROMPT

    def test_prompt_limits_analyst_reports(self) -> None:
        """RESEARCH_AGENT_PROMPT must limit analyst reports to max 1."""
        from agents.research_agent import RESEARCH_AGENT_PROMPT

        assert (
            "MAX 1" in RESEARCH_AGENT_PROMPT or "max 1" in RESEARCH_AGENT_PROMPT.lower()
        )

    def test_prompt_includes_source_diversity_types(self) -> None:
        """RESEARCH_AGENT_PROMPT must mention source diversity types."""
        from agents.research_agent import RESEARCH_AGENT_PROMPT

        assert "arXiv" in RESEARCH_AGENT_PROMPT
        assert (
            "case study" in RESEARCH_AGENT_PROMPT.lower()
            or "case_study" in RESEARCH_AGENT_PROMPT
        )

    def test_prompt_includes_source_freshness_summary_field(self) -> None:
        """RESEARCH_AGENT_PROMPT output structure must request freshness summary."""
        from agents.research_agent import RESEARCH_AGENT_PROMPT

        assert "source_freshness_summary" in RESEARCH_AGENT_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# Tests: Stage3Crew research backstory
# ─────────────────────────────────────────────────────────────────────────────


class TestStage3CrewBackstory:
    """Verify the Stage3Crew research agent backstory references sourcing skill."""

    def test_backstory_references_skill_file(self) -> None:
        """Stage3Crew research backstory should mention the sourcing skill file."""
        with open("src/crews/stage3_crew.py") as f:
            content = f.read()
        assert "skills/research-sourcing/SKILL.md" in content

    def test_backstory_mentions_analyst_limit(self) -> None:
        """Stage3Crew research backstory should mention the 1 analyst report limit."""
        with open("src/crews/stage3_crew.py") as f:
            content = f.read()
        assert "max 1" in content.lower() or "MAX 1" in content

    def test_backstory_mentions_source_freshness(self) -> None:
        """Stage3Crew research backstory should mention 2025 or 2026 as required years."""
        with open("src/crews/stage3_crew.py") as f:
            content = f.read()
        assert "2025" in content or "2026" in content
