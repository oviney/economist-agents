"""Tests for scripts/ab_topic_scout_comparison.py.

All external I/O (LLM calls, performance DB) is mocked so that the test
suite is hermetic and does not require a live API key or populated DB.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup so we can import from scripts/
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import topic_scout  # noqa: E402

from ab_topic_scout_comparison import (  # noqa: E402
    _EMPTY_CONTEXT,
    _topic_title_set,
    jaccard_similarity,
    qualitative_notes,
    render_report,
    run_ab_pair,
    save_report,
    score_deltas,
    verdict,
)
from content_intelligence import ArticlePerformance  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_topics_a() -> list[dict]:
    """Run A topics — include a keyword overlap with a top performer."""
    return [
        {
            "topic": "Why AI Test Generation Overpromises on Maintenance Reduction",
            "hook": "Automation tools cut flaky tests by only 10%, not the 40% vendors claim",
            "thesis": "AI testing hype exceeds real-world ROI",
            "contrarian_angle": "Vendors cherry-pick benchmarks",
            "timeliness_trigger": "Gartner report released Q1 2026",
            "scores": {
                "timeliness": 5,
                "data_availability": 4,
                "contrarian_potential": 5,
                "audience_fit": 5,
                "economist_fit": 4,
            },
            "total_score": 23,
            "talking_points": "ROI, maintenance, vendor claims",
        },
        {
            "topic": "The Hidden Cost of Flaky Tests",
            "hook": "Teams lose 20% velocity to test instability",
            "thesis": "Flaky tests cost more than anyone admits",
            "contrarian_angle": "Problem worse than acknowledged",
            "timeliness_trigger": "Recent platform outages",
            "scores": {
                "timeliness": 4,
                "data_availability": 4,
                "contrarian_potential": 3,
                "audience_fit": 5,
                "economist_fit": 4,
            },
            "total_score": 20,
            "talking_points": "Cost, trust, mitigation",
        },
    ]


@pytest.fixture
def sample_topics_b() -> list[dict]:
    """Run B topics — completely different titles (Jaccard should be 0)."""
    return [
        {
            "topic": "Platform Engineering and the Death of the QA Silo",
            "hook": "50% of engineering orgs have disbanded dedicated QA teams",
            "thesis": "QA is becoming infrastructure",
            "contrarian_angle": "Centralisation creates hidden quality debt",
            "timeliness_trigger": "GitHub Universe announcements",
            "scores": {
                "timeliness": 3,
                "data_availability": 3,
                "contrarian_potential": 4,
                "audience_fit": 4,
                "economist_fit": 5,
            },
            "total_score": 19,
            "talking_points": "Platform, infra, QA roles",
        },
        {
            "topic": "Shift-Left is Dead, Long Live Shift-Right",
            "hook": "Production monitoring beats pre-release testing ROI",
            "thesis": "The testing pendulum is swinging back",
            "contrarian_angle": "Shift-left was a vendor narrative",
            "timeliness_trigger": "SRE adoption surge in 2026",
            "scores": {
                "timeliness": 4,
                "data_availability": 3,
                "contrarian_potential": 5,
                "audience_fit": 4,
                "economist_fit": 4,
            },
            "total_score": 20,
            "talking_points": "Monitoring, SRE, shift-right",
        },
    ]


@pytest.fixture
def top_performers() -> list[ArticlePerformance]:
    """Synthetic top performers for qualitative notes tests."""
    return [
        ArticlePerformance(
            page_path="/2025/01/01/ai-testing-roi/",
            page_title="The Real ROI of AI Testing Tools",
            total_pageviews=1200,
            avg_engagement_rate=0.72,
            avg_engagement_time=180.0,
            avg_scroll_depth=0.65,
            avg_composite_score=0.71,
        ),
        ArticlePerformance(
            page_path="/2025/03/15/flaky-tests/",
            page_title="Flaky Tests Are Draining Your Team",
            total_pageviews=900,
            avg_engagement_rate=0.68,
            avg_engagement_time=160.0,
            avg_scroll_depth=0.60,
            avg_composite_score=0.65,
        ),
    ]


@pytest.fixture
def bottom_performers() -> list[ArticlePerformance]:
    """Synthetic bottom performers for qualitative notes tests."""
    return [
        ArticlePerformance(
            page_path="/2024/06/01/shift-left-basics/",
            page_title="Introduction to Shift-Left Testing",
            total_pageviews=500,
            avg_engagement_rate=0.30,
            avg_engagement_time=45.0,
            avg_scroll_depth=0.25,
            avg_composite_score=0.22,
        ),
    ]


# ---------------------------------------------------------------------------
# Unit tests: _topic_title_set
# ---------------------------------------------------------------------------


class TestTopicTitleSet:
    def test_returns_lowercase_stripped_set(self, sample_topics_a: list[dict]) -> None:
        result = _topic_title_set(sample_topics_a)
        assert isinstance(result, set)
        for title in result:
            assert title == title.lower()
            assert title == title.strip()

    def test_empty_list_returns_empty_set(self) -> None:
        assert _topic_title_set([]) == set()

    def test_topics_missing_title_skipped(self) -> None:
        topics = [{"hook": "something"}, {"topic": " My Topic "}]
        result = _topic_title_set(topics)
        assert result == {"my topic"}


# ---------------------------------------------------------------------------
# Unit tests: jaccard_similarity
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_identical_sets_return_one(self) -> None:
        s = {"a", "b", "c"}
        assert jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets_return_zero(self) -> None:
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self) -> None:
        result = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert result == 0.5  # |∩|=2, |∪|=4

    def test_both_empty_returns_zero(self) -> None:
        assert jaccard_similarity(set(), set()) == 0.0

    def test_one_empty_returns_zero(self) -> None:
        assert jaccard_similarity({"a"}, set()) == 0.0


# ---------------------------------------------------------------------------
# Unit tests: score_deltas
# ---------------------------------------------------------------------------


class TestScoreDeltas:
    def test_returns_all_dimensions(
        self,
        sample_topics_a: list[dict],
        sample_topics_b: list[dict],
    ) -> None:
        result = score_deltas(sample_topics_a, sample_topics_b)
        expected_dims = {
            "timeliness",
            "data_availability",
            "contrarian_potential",
            "audience_fit",
            "economist_fit",
        }
        assert set(result.keys()) == expected_dims

    def test_each_entry_has_avg_and_max(
        self,
        sample_topics_a: list[dict],
        sample_topics_b: list[dict],
    ) -> None:
        result = score_deltas(sample_topics_a, sample_topics_b)
        for dim, stats in result.items():
            assert "avg_delta" in stats, f"Missing avg_delta for {dim}"
            assert "max_delta" in stats, f"Missing max_delta for {dim}"

    def test_identical_topics_yield_zero_deltas(
        self, sample_topics_a: list[dict]
    ) -> None:
        result = score_deltas(sample_topics_a, sample_topics_a)
        for stats in result.values():
            assert stats["avg_delta"] == 0.0
            assert stats["max_delta"] == 0.0

    def test_empty_lists_yield_zero_deltas(self) -> None:
        result = score_deltas([], [])
        for stats in result.values():
            assert stats["avg_delta"] == 0.0


# ---------------------------------------------------------------------------
# Unit tests: qualitative_notes
# ---------------------------------------------------------------------------


class TestQualitativeNotes:
    def test_detects_top_performer_keyword(
        self,
        sample_topics_a: list[dict],
        top_performers: list[ArticlePerformance],
    ) -> None:
        notes = qualitative_notes(sample_topics_a, top_performers, [])
        # "flaky" appears in both Run A topic 2 and top performer "Flaky Tests…"
        assert any("✅" in n for n in notes)

    def test_detects_bottom_performer_keyword(
        self,
        bottom_performers: list[ArticlePerformance],
    ) -> None:
        topics = [
            {
                "topic": "Why Shift-Left Testing Is Misunderstood",
                "hook": "Shift-left promises more than it delivers",
                "thesis": "Shift-left is a vendor narrative",
                "contrarian_angle": "Production monitoring beats pre-release testing",
                "timeliness_trigger": "Recent SRE surge",
                "scores": {},
                "total_score": 18,
            }
        ]
        notes = qualitative_notes(topics, [], bottom_performers)
        assert any("⚠️" in n for n in notes)

    def test_no_match_returns_info_note(
        self,
        top_performers: list[ArticlePerformance],
        bottom_performers: list[ArticlePerformance],
    ) -> None:
        topics = [
            {
                "topic": "Quantum Computing and Software Delivery",
                "hook": "Qubit speeds will transform CI/CD",
                "thesis": "Quantum will reshape pipelines",
                "contrarian_angle": "Most teams are not ready",
                "timeliness_trigger": "IBM quantum roadmap",
                "scores": {},
                "total_score": 15,
            }
        ]
        notes = qualitative_notes(topics, top_performers, bottom_performers)
        assert any("ℹ️" in n for n in notes)

    def test_empty_inputs_return_info_note(self) -> None:
        notes = qualitative_notes([], [], [])
        assert any("ℹ️" in n for n in notes)


# ---------------------------------------------------------------------------
# Unit tests: verdict
# ---------------------------------------------------------------------------


class TestVerdict:
    def test_real_when_jaccard_low_and_top_ref(self) -> None:
        notes = ['✅ Run A topic **"X"** references top-performer **"Y"** (keywords: testing)']
        is_real, text = verdict(0.2, notes)
        assert is_real is True
        assert "VERDICT: Feedback loop is causally real" in text

    def test_not_real_when_jaccard_high(self) -> None:
        notes = ['✅ Run A topic **"X"** references top-performer **"Y"** (keywords: testing)']
        is_real, text = verdict(0.7, notes)
        assert is_real is False
        assert "NOT confirmed" in text

    def test_not_real_when_no_top_ref(self) -> None:
        notes = ["ℹ️  No Run A topic explicitly matched keywords from the top/bottom performers."]
        is_real, text = verdict(0.1, notes)
        assert is_real is False
        assert "NOT confirmed" in text

    def test_boundary_jaccard_0_59_is_real(self) -> None:
        notes = ['✅ Run A topic **"X"** references top-performer **"Y"** (keywords: test)']
        is_real, _ = verdict(0.59, notes)
        assert is_real is True

    def test_boundary_jaccard_0_6_not_real(self) -> None:
        notes = ['✅ Run A topic **"X"** references top-performer **"Y"** (keywords: test)']
        is_real, _ = verdict(0.6, notes)
        assert is_real is False


# ---------------------------------------------------------------------------
# Unit tests: render_report
# ---------------------------------------------------------------------------


class TestRenderReport:
    def _make_pair(
        self,
        topics_a: list[dict],
        topics_b: list[dict],
        top_performers: list[ArticlePerformance],
        bottom_performers: list[ArticlePerformance],
        jac: float = 0.0,
    ) -> dict:
        notes = qualitative_notes(topics_a, top_performers, bottom_performers)
        verdict_is_real, verdict_text = verdict(jac, notes)
        return {
            "topics_a": topics_a,
            "topics_b": topics_b,
            "jaccard": jac,
            "deltas": score_deltas(topics_a, topics_b),
            "notes": notes,
            "verdict_is_real": verdict_is_real,
            "verdict_text": verdict_text,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
        }

    def test_report_contains_required_sections(
        self,
        sample_topics_a: list[dict],
        sample_topics_b: list[dict],
        top_performers: list[ArticlePerformance],
        bottom_performers: list[ArticlePerformance],
    ) -> None:
        pair = self._make_pair(
            sample_topics_a, sample_topics_b, top_performers, bottom_performers
        )
        report = render_report([pair], "2026-04-06 12:00:00")
        assert "# A/B Topic Scout Comparison Report" in report
        assert "## Summary Statistics" in report
        assert "## Per-Dimension Score Deltas" in report
        assert "## Topic Comparison" in report
        assert "## Qualitative Notes" in report
        assert "## Verdict" in report

    def test_jaccard_appears_in_report(
        self,
        sample_topics_a: list[dict],
        sample_topics_b: list[dict],
        top_performers: list[ArticlePerformance],
        bottom_performers: list[ArticlePerformance],
    ) -> None:
        pair = self._make_pair(
            sample_topics_a,
            sample_topics_b,
            top_performers,
            bottom_performers,
            jac=0.25,
        )
        report = render_report([pair], "2026-04-06 12:00:00")
        assert "0.250" in report

    def test_multiple_pairs_show_aggregate(
        self,
        sample_topics_a: list[dict],
        sample_topics_b: list[dict],
        top_performers: list[ArticlePerformance],
        bottom_performers: list[ArticlePerformance],
    ) -> None:
        pair = self._make_pair(
            sample_topics_a, sample_topics_b, top_performers, bottom_performers
        )
        report = render_report([pair, pair], "2026-04-06 12:00:00")
        assert "Aggregate Verdict" in report
        assert "Pairs run: 2" in report


# ---------------------------------------------------------------------------
# Unit tests: save_report
# ---------------------------------------------------------------------------


class TestSaveReport:
    def test_creates_file_in_output_dir(self, tmp_path: Path) -> None:
        report = "# Test Report\n\nSome content."
        saved = save_report(report, tmp_path)
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == report

    def test_filename_contains_timestamp_prefix(self, tmp_path: Path) -> None:
        saved = save_report("# R", tmp_path)
        assert saved.name.startswith("ab_topic_scout_comparison_")
        assert saved.suffix == ".md"

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        saved = save_report("# R", nested)
        assert nested.exists()
        assert saved.exists()


# ---------------------------------------------------------------------------
# Integration-style test: run_ab_pair (fully mocked)
# ---------------------------------------------------------------------------


class TestRunAbPair:
    """Verify run_ab_pair calls scout_topics twice with the correct patching."""

    def test_run_a_uses_real_context_run_b_uses_empty(self) -> None:
        """Run B's scout call should receive the empty fallback context."""
        real_context_seen: list[str] = []
        patched_context_seen: list[str] = []

        sample_topics = [
            {
                "topic": "AI Testing ROI",
                "hook": "AI tools overperform on benchmarks",
                "thesis": "ROI claims are exaggerated",
                "contrarian_angle": "Maintenance costs hidden",
                "timeliness_trigger": "New Gartner report",
                "scores": {
                    "timeliness": 4,
                    "data_availability": 4,
                    "contrarian_potential": 4,
                    "audience_fit": 4,
                    "economist_fit": 4,
                },
                "total_score": 20,
                "talking_points": "ROI, maintenance",
            }
        ]

        call_count = 0

        def fake_scout_topics(client, focus_area=None):
            nonlocal call_count
            call_count += 1
            # Capture whether the real or patched context was used
            ctx = topic_scout.get_performance_context()
            if "No performance data available" in ctx:
                patched_context_seen.append(ctx)
            else:
                real_context_seen.append(ctx)
            return sample_topics

        mock_client = MagicMock()

        with (
            patch("ab_topic_scout_comparison.topic_scout.scout_topics", side_effect=fake_scout_topics),
            patch("ab_topic_scout_comparison.content_intelligence.get_top_performers", return_value=[]),
            patch("ab_topic_scout_comparison.content_intelligence.get_bottom_performers", return_value=[]),
        ):
            result = run_ab_pair(mock_client, pair_index=1)

        assert call_count == 2, "scout_topics should be called exactly twice"
        assert "topics_a" in result
        assert "topics_b" in result
        assert "jaccard" in result
        assert "deltas" in result
        assert "notes" in result
        assert "verdict_is_real" in result

    def test_result_schema_complete(self) -> None:
        """run_ab_pair result contains all expected keys."""
        sample_topics = [
            {
                "topic": "Test Topic",
                "hook": "hook",
                "thesis": "thesis",
                "contrarian_angle": "angle",
                "timeliness_trigger": "now",
                "scores": {
                    "timeliness": 3,
                    "data_availability": 3,
                    "contrarian_potential": 3,
                    "audience_fit": 3,
                    "economist_fit": 3,
                },
                "total_score": 15,
                "talking_points": "tp",
            }
        ]
        mock_client = MagicMock()

        with (
            patch("ab_topic_scout_comparison.topic_scout.scout_topics", return_value=sample_topics),
            patch("ab_topic_scout_comparison.content_intelligence.get_top_performers", return_value=[]),
            patch("ab_topic_scout_comparison.content_intelligence.get_bottom_performers", return_value=[]),
        ):
            result = run_ab_pair(mock_client, pair_index=1)

        required_keys = {
            "topics_a",
            "topics_b",
            "jaccard",
            "deltas",
            "notes",
            "verdict_is_real",
            "verdict_text",
            "top_performers",
            "bottom_performers",
        }
        assert required_keys.issubset(result.keys())
