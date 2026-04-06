"""Tests for scripts/ga4_etl — GA4 ETL pipeline.

All Google API calls are mocked; no network access required.
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.ga4_etl import (
    compute_scores,
    fetch_ga4_report,
    main,
    normalize,
    parse_rows,
    store_results,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_dimension_value(value: str) -> MagicMock:
    """Create a mock DimensionValue."""
    dv = MagicMock()
    dv.value = value
    return dv


def _make_metric_value(value: str) -> MagicMock:
    """Create a mock MetricValue."""
    mv = MagicMock()
    mv.value = value
    return mv


def _make_row(
    path: str,
    title: str,
    date: str,
    pageviews: int,
    engagement_rate: float,
    avg_duration: float,
    scrolled_users: int,
) -> MagicMock:
    """Build a mock GA4 row with the given values."""
    row = MagicMock()
    row.dimension_values = [
        _make_dimension_value(path),
        _make_dimension_value(title),
        _make_dimension_value(date),
    ]
    row.metric_values = [
        _make_metric_value(str(pageviews)),
        _make_metric_value(str(engagement_rate)),
        _make_metric_value(str(avg_duration)),
        _make_metric_value(str(scrolled_users)),
    ]
    return row


def _make_response(rows: list[MagicMock] | None = None) -> MagicMock:
    """Build a mock RunReportResponse."""
    resp = MagicMock()
    resp.rows = rows or []
    return resp


@pytest.fixture()
def sample_response() -> MagicMock:
    """A response with three realistic rows."""
    return _make_response(
        [
            _make_row(
                "/blog/ai-trends", "AI Trends", "20260401", 500, 0.72, 120.5, 300
            ),
            _make_row(
                "/blog/data-eng", "Data Engineering", "20260401", 200, 0.55, 80.0, 100
            ),
            _make_row("/blog/cloud", "Cloud Native", "20260401", 800, 0.90, 200.0, 700),
        ]
    )


@pytest.fixture()
def tmp_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Provide a temporary SQLite database path."""
    return tmp_path / "test_performance.db"


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


class TestNormalize:
    """Tests for the min-max normalize helper."""

    def test_standard_normalization(self) -> None:
        """Standard case: distinct values are spread to [0, 1]."""
        result = normalize([10.0, 20.0, 30.0])
        assert result == [0.0, 0.5, 1.0]

    def test_empty_list(self) -> None:
        """Empty input returns empty output."""
        assert normalize([]) == []

    def test_single_value(self) -> None:
        """Single value normalizes to 0.0 (zero span)."""
        assert normalize([42.0]) == [0.0]

    def test_all_identical(self) -> None:
        """All identical values yield zeros."""
        assert normalize([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]

    def test_two_values(self) -> None:
        """Two distinct values map to 0.0 and 1.0."""
        result = normalize([100.0, 200.0])
        assert result == [0.0, 1.0]

    def test_negative_values(self) -> None:
        """Negative values are handled correctly."""
        result = normalize([-10.0, 0.0, 10.0])
        assert result == [0.0, 0.5, 1.0]


# ---------------------------------------------------------------------------
# parse_rows()
# ---------------------------------------------------------------------------


class TestParseRows:
    """Tests for GA4 response parsing."""

    def test_parse_valid_response(self, sample_response: MagicMock) -> None:
        """Valid response is parsed into row dicts with correct keys."""
        rows = parse_rows(sample_response)
        assert len(rows) == 3
        first = rows[0]
        assert first["page_path"] == "/blog/ai-trends"
        assert first["page_title"] == "AI Trends"
        assert first["pageviews"] == 500
        assert first["engagement_rate"] == 0.72
        assert first["avg_engagement_time"] == 120.5
        # scroll_depth_rate = scrolledUsers / pageviews = 300 / 500
        assert first["scroll_depth_rate"] == pytest.approx(0.6)

    def test_parse_empty_response(self) -> None:
        """Empty response returns an empty list without errors."""
        resp = _make_response(rows=None)
        assert parse_rows(resp) == []

    def test_parse_empty_rows_list(self) -> None:
        """Response with empty rows list returns an empty list."""
        resp = _make_response(rows=[])
        assert parse_rows(resp) == []

    def test_zero_pageviews_scroll_depth(self) -> None:
        """Zero pageviews should not cause division by zero."""
        resp = _make_response(
            [_make_row("/empty", "Empty", "20260401", 0, 0.0, 0.0, 0)]
        )
        rows = parse_rows(resp)
        assert rows[0]["scroll_depth_rate"] == 0.0


# ---------------------------------------------------------------------------
# compute_scores()
# ---------------------------------------------------------------------------


class TestComputeScores:
    """Tests for composite engagement score computation."""

    def test_scores_are_computed(self, sample_response: MagicMock) -> None:
        """Each row gets a composite_score key."""
        rows = parse_rows(sample_response)
        scored = compute_scores(rows)
        assert all("composite_score" in r for r in scored)

    def test_score_range(self, sample_response: MagicMock) -> None:
        """Scores should be between 0 and 1 (GSC placeholders are 0)."""
        rows = parse_rows(sample_response)
        scored = compute_scores(rows)
        for row in scored:
            assert 0.0 <= row["composite_score"] <= 1.0

    def test_best_row_has_highest_score(self, sample_response: MagicMock) -> None:
        """The row with the best metrics should have the highest score."""
        rows = parse_rows(sample_response)
        scored = compute_scores(rows)
        # /blog/cloud has the highest pageviews, engagement, duration, scroll
        scores = {r["page_path"]: r["composite_score"] for r in scored}
        assert scores["/blog/cloud"] == max(scores.values())

    def test_empty_rows(self) -> None:
        """Empty input passes through cleanly."""
        assert compute_scores([]) == []

    def test_single_row_score_is_zero(self) -> None:
        """A single row normalizes everything to 0 (zero span)."""
        rows: list[dict[str, Any]] = [
            {
                "page_path": "/solo",
                "page_title": "Solo",
                "pageviews": 100,
                "engagement_rate": 0.5,
                "avg_engagement_time": 60.0,
                "scroll_depth_rate": 0.3,
            }
        ]
        scored = compute_scores(rows)
        assert scored[0]["composite_score"] == 0.0


# ---------------------------------------------------------------------------
# store_results()
# ---------------------------------------------------------------------------


class TestStoreResults:
    """Tests for SQLite storage."""

    def test_creates_table_and_inserts(
        self, sample_response: MagicMock, tmp_db: pathlib.Path
    ) -> None:
        """Rows are inserted and retrievable."""
        rows = compute_scores(parse_rows(sample_response))
        count = store_results(rows, db_path=tmp_db)
        assert count == 3

        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute("SELECT COUNT(*) FROM article_performance")
        assert cursor.fetchone()[0] == 3
        conn.close()

    def test_fetched_at_is_populated(
        self, sample_response: MagicMock, tmp_db: pathlib.Path
    ) -> None:
        """Each row has a non-empty fetched_at timestamp."""
        rows = compute_scores(parse_rows(sample_response))
        store_results(rows, db_path=tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute("SELECT fetched_at FROM article_performance")
        for (ts,) in cursor.fetchall():
            assert ts is not None
            assert len(ts) > 0
        conn.close()

    def test_empty_rows_inserts_nothing(self, tmp_db: pathlib.Path) -> None:
        """Storing an empty list creates the table but inserts 0 rows."""
        count = store_results([], db_path=tmp_db)
        assert count == 0

        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute("SELECT COUNT(*) FROM article_performance")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_schema_columns(
        self, sample_response: MagicMock, tmp_db: pathlib.Path
    ) -> None:
        """Verify all expected columns exist in the table."""
        rows = compute_scores(parse_rows(sample_response))
        store_results(rows, db_path=tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.execute("PRAGMA table_info(article_performance)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

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
        assert columns == expected


# ---------------------------------------------------------------------------
# fetch_ga4_report()
# ---------------------------------------------------------------------------


class TestFetchGa4Report:
    """Tests for the GA4 API call wrapper (mocked)."""

    def test_calls_run_report(self) -> None:
        """The client's run_report method is called with the correct property."""
        mock_client = MagicMock()
        mock_client.run_report.return_value = _make_response()

        fetch_ga4_report(mock_client, "123456", days=7)

        mock_client.run_report.assert_called_once()
        call_args = mock_client.run_report.call_args
        request = call_args[0][0] if call_args[0] else call_args[1].get("request")
        assert request.property == "properties/123456"


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


class TestMainCLI:
    """Integration tests for the CLI entry-point with all externals mocked."""

    @patch("scripts.ga4_etl.build_ga4_client")
    @patch("scripts.ga4_etl.store_results")
    @patch.dict("os.environ", {"GA4_PROPERTY_ID": "359949411"})
    def test_main_success(
        self,
        mock_store: MagicMock,
        mock_build_client: MagicMock,
        sample_response: MagicMock,
    ) -> None:
        """Successful end-to-end run stores rows."""
        mock_client = MagicMock()
        mock_client.run_report.return_value = sample_response
        mock_build_client.return_value = mock_client
        mock_store.return_value = 3

        main(["--days", "7"])

        mock_store.assert_called_once()
        stored_rows = mock_store.call_args[0][0]
        assert len(stored_rows) == 3
        assert all("composite_score" in r for r in stored_rows)

    @patch("scripts.ga4_etl.build_ga4_client")
    @patch("scripts.ga4_etl.store_results")
    @patch.dict("os.environ", {"GA4_PROPERTY_ID": "359949411"})
    def test_main_empty_response(
        self,
        mock_store: MagicMock,
        mock_build_client: MagicMock,
    ) -> None:
        """Empty GA4 response results in no store call."""
        mock_client = MagicMock()
        mock_client.run_report.return_value = _make_response()
        mock_build_client.return_value = mock_client

        main(["--days", "7"])

        mock_store.assert_not_called()

    @patch("scripts.ga4_etl.build_ga4_client")
    @patch.dict("os.environ", {"GA4_PROPERTY_ID": "359949411"})
    def test_main_dry_run(
        self,
        mock_build_client: MagicMock,
        sample_response: MagicMock,
    ) -> None:
        """Dry-run mode does not write to the database."""
        mock_client = MagicMock()
        mock_client.run_report.return_value = sample_response
        mock_build_client.return_value = mock_client

        # Should not raise, and should not create a DB file
        main(["--days", "7", "--dry-run"])

    @patch.dict("os.environ", {"GA4_PROPERTY_ID": ""}, clear=False)
    def test_main_missing_property_id(self) -> None:
        """Missing GA4_PROPERTY_ID raises SystemExit."""
        with pytest.raises(SystemExit):
            main(["--days", "7"])
