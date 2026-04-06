"""Tests for scripts/audit_composite_scores.py.

All database access is performed against temporary SQLite files; no live
``data/performance.db`` is required.
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any

import pytest

from scripts.audit_composite_scores import (
    _ACTIVE_WEIGHT_SUM,
    _ZERO_WEIGHT_SUM,
    build_report,
    compute_verdict,
    load_all_rows,
    recompute_score,
    render_verdict_section,
    run_sanity_checks,
    select_sample,
)
from scripts.ga4_etl import COMPOSITE_WEIGHTS

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_performance (
    page_path           TEXT,
    page_title          TEXT,
    pageviews           INTEGER,
    engagement_rate     REAL,
    avg_engagement_time REAL,
    scroll_depth_rate   REAL,
    composite_score     REAL,
    fetched_at          TEXT
);
"""

_SAMPLE_ROWS: list[dict[str, Any]] = [
    {
        "page_path": "/a",
        "page_title": "Article A",
        "pageviews": 1000,
        "engagement_rate": 0.9,
        "avg_engagement_time": 200.0,
        "scroll_depth_rate": 0.85,
        "composite_score": 0.7,
        "fetched_at": "2026-04-01T12:00:00+00:00",
    },
    {
        "page_path": "/b",
        "page_title": "Article B",
        "pageviews": 500,
        "engagement_rate": 0.6,
        "avg_engagement_time": 100.0,
        "scroll_depth_rate": 0.5,
        "composite_score": 0.4,
        "fetched_at": "2026-04-01T12:00:00+00:00",
    },
    {
        "page_path": "/c",
        "page_title": "Article C",
        "pageviews": 10,
        "engagement_rate": 0.3,
        "avg_engagement_time": 20.0,
        "scroll_depth_rate": 0.2,
        "composite_score": 0.05,
        "fetched_at": "2026-04-01T12:00:00+00:00",
    },
    {
        "page_path": "/d",
        "page_title": "Article D",
        "pageviews": 200,
        "engagement_rate": 0.4,
        "avg_engagement_time": 60.0,
        "scroll_depth_rate": 0.3,
        "composite_score": 0.2,
        "fetched_at": "2026-04-01T12:00:00+00:00",
    },
    {
        "page_path": "/e",
        "page_title": "Article E",
        "pageviews": 75,
        "engagement_rate": 0.2,
        "avg_engagement_time": 15.0,
        "scroll_depth_rate": 0.1,
        "composite_score": 0.01,
        "fetched_at": "2026-04-01T12:00:00+00:00",
    },
]


def _populate_db(db_path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    """Create and populate a test SQLite DB."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(CREATE_TABLE_SQL)
    for r in rows:
        conn.execute(
            """
            INSERT INTO article_performance
                (page_path, page_title, pageviews, engagement_rate,
                 avg_engagement_time, scroll_depth_rate, composite_score, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["page_path"],
                r["page_title"],
                r["pageviews"],
                r["engagement_rate"],
                r["avg_engagement_time"],
                r["scroll_depth_rate"],
                r["composite_score"],
                r["fetched_at"],
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture()
def tmp_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Provide a temporary SQLite DB populated with sample rows."""
    db = tmp_path / "performance.db"
    _populate_db(db, _SAMPLE_ROWS)
    return db


@pytest.fixture()
def empty_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Provide a temporary empty SQLite DB (table exists, no rows)."""
    db = tmp_path / "empty_performance.db"
    conn = sqlite3.connect(str(db))
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()
    return db


# ---------------------------------------------------------------------------
# load_all_rows()
# ---------------------------------------------------------------------------


class TestLoadAllRows:
    """Tests for loading rows from the database."""

    def test_loads_all_rows(self, tmp_db: pathlib.Path) -> None:
        """All rows from the latest snapshot are returned."""
        rows = load_all_rows(tmp_db)
        assert len(rows) == len(_SAMPLE_ROWS)

    def test_missing_db_raises(self, tmp_path: pathlib.Path) -> None:
        """FileNotFoundError is raised when the database does not exist."""
        with pytest.raises(FileNotFoundError):
            load_all_rows(tmp_path / "nonexistent.db")

    def test_empty_db_returns_empty_list(self, empty_db: pathlib.Path) -> None:
        """An empty table returns an empty list."""
        rows = load_all_rows(empty_db)
        assert rows == []

    def test_returns_latest_snapshot_only(self, tmp_path: pathlib.Path) -> None:
        """Only the most recent fetched_at row is returned per page_path."""
        db = tmp_path / "dup.db"
        old = {**_SAMPLE_ROWS[0], "composite_score": 0.1, "fetched_at": "2026-01-01T00:00:00+00:00"}
        new = {**_SAMPLE_ROWS[0], "composite_score": 0.7, "fetched_at": "2026-04-01T12:00:00+00:00"}
        _populate_db(db, [old, new])
        rows = load_all_rows(db)
        assert len(rows) == 1
        assert rows[0]["composite_score"] == pytest.approx(0.7)

    def test_row_keys_match_schema(self, tmp_db: pathlib.Path) -> None:
        """Every row dict has the expected keys."""
        expected = {
            "page_path",
            "page_title",
            "pageviews",
            "engagement_rate",
            "avg_engagement_time",
            "scroll_depth_rate",
            "composite_score",
            "fetched_at",
        }
        rows = load_all_rows(tmp_db)
        for row in rows:
            assert set(row.keys()) == expected


# ---------------------------------------------------------------------------
# select_sample()
# ---------------------------------------------------------------------------


class TestSelectSample:
    """Tests for the 5-URL sample selection."""

    def test_empty_input_returns_empty(self) -> None:
        """Empty input yields an empty sample."""
        assert select_sample([]) == {}

    def test_returns_expected_slots(self, tmp_db: pathlib.Path) -> None:
        """Expected slot keys are present for a rich enough dataset."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        # All sample rows in _SAMPLE_ROWS have pageviews > 5 and at least one > 50
        assert "top" in sample
        assert "most_traffic" in sample
        assert "median" in sample

    def test_top_has_highest_score(self, tmp_db: pathlib.Path) -> None:
        """The 'top' slot corresponds to the highest composite score."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        max_score = max(r["composite_score"] for r in rows)
        assert sample["top"]["composite_score"] == pytest.approx(max_score)

    def test_most_traffic_has_highest_pageviews(self, tmp_db: pathlib.Path) -> None:
        """The 'most_traffic' slot corresponds to the highest pageviews."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        max_pv = max(r["pageviews"] for r in rows)
        assert sample["most_traffic"]["pageviews"] == max_pv

    def test_viral_shallow_has_pageviews_above_50(self, tmp_db: pathlib.Path) -> None:
        """The 'viral_shallow' slot has pageviews > 50."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        if "viral_shallow" in sample:
            assert sample["viral_shallow"]["pageviews"] > 50

    def test_tail_has_pageviews_above_5(self, tmp_db: pathlib.Path) -> None:
        """The 'tail' slot has pageviews > 5."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        if "tail" in sample:
            assert sample["tail"]["pageviews"] > 5


# ---------------------------------------------------------------------------
# recompute_score()
# ---------------------------------------------------------------------------


class TestRecomputeScore:
    """Tests for per-URL score re-derivation."""

    def test_recomputed_keys_present(self, tmp_db: pathlib.Path) -> None:
        """All expected keys are returned."""
        rows = load_all_rows(tmp_db)
        math = recompute_score(rows[0], rows)
        for key in ("raw", "normalized", "contributions", "recomputed_score", "stored_score", "zero_terms"):
            assert key in math

    def test_contributions_sum_to_recomputed_score(self, tmp_db: pathlib.Path) -> None:
        """The sum of weighted contributions equals recomputed_score."""
        rows = load_all_rows(tmp_db)
        for row in rows:
            math = recompute_score(row, rows)
            total = sum(math["contributions"].values())
            assert total == pytest.approx(math["recomputed_score"], abs=1e-6)

    def test_normalized_values_in_0_1_range(self, tmp_db: pathlib.Path) -> None:
        """All normalised values are in [0, 1]."""
        rows = load_all_rows(tmp_db)
        for row in rows:
            math = recompute_score(row, rows)
            for term, nv in math["normalized"].items():
                assert 0.0 <= nv <= 1.0, f"{term} normalised to {nv}"

    def test_gsc_placeholders_in_zero_terms(self, tmp_db: pathlib.Path) -> None:
        """search_ctr and search_impressions appear in zero_terms when weighted."""
        rows = load_all_rows(tmp_db)
        math = recompute_score(rows[0], rows)
        # These are placeholders in the current formula
        for term in ("search_ctr", "search_impressions"):
            if COMPOSITE_WEIGHTS.get(term, 0.0) > 0.0:
                assert term in math["zero_terms"]

    def test_raw_values_match_db(self, tmp_db: pathlib.Path) -> None:
        """raw values returned are taken directly from the database row."""
        rows = load_all_rows(tmp_db)
        row = rows[0]
        math = recompute_score(row, rows)
        assert math["raw"]["pageviews"] == row["pageviews"]
        assert math["raw"]["engagement_rate"] == row["engagement_rate"]


# ---------------------------------------------------------------------------
# run_sanity_checks()
# ---------------------------------------------------------------------------


class TestRunSanityChecks:
    """Tests for the sanity check section."""

    def test_returns_list_of_strings(self, tmp_db: pathlib.Path) -> None:
        """Sanity checks return a non-empty list of markdown strings."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        math_map = {slot: recompute_score(row, rows) for slot, row in sample.items()}
        bullets = run_sanity_checks(rows, sample, math_map)
        assert isinstance(bullets, list)
        assert len(bullets) > 0
        for b in bullets:
            assert isinstance(b, str)

    def test_active_weight_fraction_mentioned(self, tmp_db: pathlib.Path) -> None:
        """The active weight fraction is referenced in the output."""
        rows = load_all_rows(tmp_db)
        sample = select_sample(rows)
        math_map = {slot: recompute_score(row, rows) for slot, row in sample.items()}
        bullets = run_sanity_checks(rows, sample, math_map)
        combined = "\n".join(bullets)
        assert "%" in combined


# ---------------------------------------------------------------------------
# compute_verdict()
# ---------------------------------------------------------------------------


class TestComputeVerdict:
    """Tests for the verdict logic."""

    def test_verdict_keys_are_valid(self, tmp_db: pathlib.Path) -> None:
        """Verdict key is one of the three expected values."""
        rows = load_all_rows(tmp_db)
        verdict_key, _, exit_code = compute_verdict(rows)
        assert verdict_key in ("proceed", "re-weight", "wait for GSC")
        assert exit_code in (0, 1)

    def test_proceed_exit_code_0(self) -> None:
        """Exit code 0 is returned for 'proceed' verdict (when no placeholders)."""
        # The actual verdict depends on _ZERO_WEIGHT_SUM from ga4_etl; we verify
        # the contract: exit code must be 0 or 1 and the three possible verdicts
        # have the right codes.
        verdict_key, _, exit_code = compute_verdict([])
        assert verdict_key in ("proceed", "re-weight", "wait for GSC")
        if verdict_key == "proceed":
            assert exit_code == 0
        else:
            assert exit_code == 1

    def test_zero_weight_sum_constant(self) -> None:
        """_ZERO_WEIGHT_SUM + _ACTIVE_WEIGHT_SUM equals total weights."""
        total = sum(COMPOSITE_WEIGHTS.values())
        assert pytest.approx(total) == _ZERO_WEIGHT_SUM + _ACTIVE_WEIGHT_SUM


# ---------------------------------------------------------------------------
# build_report()
# ---------------------------------------------------------------------------


class TestBuildReport:
    """Integration tests for the full report builder."""

    def test_report_is_string(self, tmp_db: pathlib.Path) -> None:
        """build_report returns a (str, int) tuple."""
        rows = load_all_rows(tmp_db)
        report, exit_code = build_report(rows, tmp_db)
        assert isinstance(report, str)
        assert exit_code in (0, 1)

    def test_report_contains_header(self, tmp_db: pathlib.Path) -> None:
        """Report starts with the expected H1 header."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "# Composite Score Audit" in report

    def test_report_contains_weight_summary(self, tmp_db: pathlib.Path) -> None:
        """Report includes the weight summary section."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "Weight Summary" in report
        assert "pageviews" in report
        assert "search_ctr" in report

    def test_report_contains_verdict(self, tmp_db: pathlib.Path) -> None:
        """Report includes a Verdict section."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "## Verdict" in report

    def test_report_contains_sanity_checks(self, tmp_db: pathlib.Path) -> None:
        """Report includes the sanity checks section."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "Sanity Checks" in report

    def test_empty_db_report(self, empty_db: pathlib.Path) -> None:
        """An empty database produces a valid report with a warning."""
        rows = load_all_rows(empty_db)
        report, exit_code = build_report(rows, empty_db)
        assert "database is empty" in report.lower() or "empty" in report.lower()
        assert exit_code == 1

    def test_determinism(self, tmp_db: pathlib.Path) -> None:
        """Running build_report twice produces identical reports (excluding timestamps)."""
        rows = load_all_rows(tmp_db)
        report1, _ = build_report(rows, tmp_db)
        report2, _ = build_report(rows, tmp_db)
        # Strip timestamp lines before comparing
        def strip_ts(text: str) -> str:
            return "\n".join(
                line for line in text.splitlines()
                if "Generated:" not in line
            )
        assert strip_ts(report1) == strip_ts(report2)

    def test_url_walkthroughs_present(self, tmp_db: pathlib.Path) -> None:
        """Report includes per-URL math walkthrough sections."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "Weighted contributions" in report
        assert "Raw values" in report

    def test_placeholder_flag_in_report(self, tmp_db: pathlib.Path) -> None:
        """GSC placeholder warning appears in the report."""
        rows = load_all_rows(tmp_db)
        report, _ = build_report(rows, tmp_db)
        assert "placeholder" in report.lower()


# ---------------------------------------------------------------------------
# render_verdict_section()
# ---------------------------------------------------------------------------


class TestRenderVerdictSection:
    """Tests for individual verdict section rendering."""

    @pytest.mark.parametrize("verdict_key", ["proceed", "re-weight", "wait for GSC"])
    def test_verdict_section_contains_key(self, verdict_key: str) -> None:
        """Each verdict key is reflected in the section text."""
        section = render_verdict_section(verdict_key, "Test narrative.", [])
        assert verdict_key.upper() in section or verdict_key in section

    def test_verdict_contains_gsc_activation_note(self) -> None:
        """The GSC activation sub-section is always present."""
        section = render_verdict_section("proceed", "Narrative.", [])
        assert "GSC" in section or "search" in section.lower()

    def test_verdict_contains_recommendation(self) -> None:
        """The Recommendation sub-section is always present."""
        section = render_verdict_section("re-weight", "Narrative.", [])
        assert "Recommendation" in section
