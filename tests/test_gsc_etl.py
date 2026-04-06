"""Tests for scripts/gsc_etl.py — Google Search Console ETL (Issue #163).

All Google API calls are mocked. Tests cover:
- Successful data fetch and SQLite storage
- Empty response handling (new GSC property)
- Content gap identification logic
- SQLite table creation and row persistence
"""

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.gsc_etl import (
    aggregate_by_page,
    fetch_search_analytics,
    identify_content_gaps,
    init_db,
    parse_rows,
    run_etl,
    store_results,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


def _sample_gsc_rows() -> list[dict[str, Any]]:
    """Return realistic GSC API response rows."""
    return [
        {
            "keys": ["python tutorial", "https://www.viney.ca/python"],
            "impressions": 5000,
            "clicks": 50,
            "ctr": 0.01,
            "position": 8.2,
        },
        {
            "keys": ["economist analysis", "https://www.viney.ca/economics"],
            "impressions": 3000,
            "clicks": 300,
            "ctr": 0.10,
            "position": 3.1,
        },
        {
            "keys": ["data engineering", "https://www.viney.ca/data"],
            "impressions": 100,
            "clicks": 5,
            "ctr": 0.05,
            "position": 15.0,
        },
        {
            "keys": ["gsc api guide", "https://www.viney.ca/gsc"],
            "impressions": 8000,
            "clicks": 100,
            "ctr": 0.0125,
            "position": 6.5,
        },
    ]


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a temporary database path."""
    return tmp_path / "test_performance.db"


@pytest.fixture()
def sample_keyword_rows() -> list[dict[str, Any]]:
    """Parsed keyword rows (output of parse_rows)."""
    return parse_rows(_sample_gsc_rows())


# ═══════════════════════════════════════════════════════════════════════════
# Database initialisation
# ═══════════════════════════════════════════════════════════════════════════


class TestInitDb:
    """Tests for init_db."""

    def test_creates_tables(self, tmp_db: Path) -> None:
        """Tables are created when the database does not exist yet."""
        conn = init_db(tmp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "keyword_data" in tables
        assert "search_performance" in tables

    def test_idempotent(self, tmp_db: Path) -> None:
        """Calling init_db twice does not raise."""
        conn1 = init_db(tmp_db)
        conn1.close()
        conn2 = init_db(tmp_db)
        conn2.close()


# ═══════════════════════════════════════════════════════════════════════════
# Parsing
# ═══════════════════════════════════════════════════════════════════════════


class TestParseRows:
    """Tests for parse_rows."""

    def test_parses_keys(self) -> None:
        """Query and page_url are extracted from the keys list."""
        rows = parse_rows(_sample_gsc_rows())
        assert rows[0]["query"] == "python tutorial"
        assert rows[0]["page_url"] == "https://www.viney.ca/python"

    def test_numeric_fields(self) -> None:
        """Impressions, clicks, ctr, position are correct types."""
        rows = parse_rows(_sample_gsc_rows())
        assert isinstance(rows[0]["impressions"], int)
        assert isinstance(rows[0]["ctr"], float)

    def test_empty_input(self) -> None:
        """Empty list returns empty list."""
        assert parse_rows([]) == []


# ═══════════════════════════════════════════════════════════════════════════
# Content gap identification
# ═══════════════════════════════════════════════════════════════════════════


class TestContentGaps:
    """Tests for identify_content_gaps."""

    def test_flags_high_impression_low_ctr(
        self, sample_keyword_rows: list[dict[str, Any]]
    ) -> None:
        """Rows with impressions > median AND ctr < 0.03 are flagged."""
        result = identify_content_gaps(sample_keyword_rows)
        gaps = [r for r in result if r["is_content_gap"]]
        # "python tutorial" (5000 imp, 0.01 ctr) and "gsc api guide"
        # (8000 imp, 0.0125 ctr) should be gaps.
        gap_queries = {r["query"] for r in gaps}
        assert "python tutorial" in gap_queries
        assert "gsc api guide" in gap_queries

    def test_no_flag_high_ctr(self, sample_keyword_rows: list[dict[str, Any]]) -> None:
        """Rows with high CTR are not flagged even with high impressions."""
        result = identify_content_gaps(sample_keyword_rows)
        econ_row = next(r for r in result if r["query"] == "economist analysis")
        assert econ_row["is_content_gap"] is False

    def test_no_flag_low_impressions(
        self, sample_keyword_rows: list[dict[str, Any]]
    ) -> None:
        """Rows below median impressions are not flagged."""
        result = identify_content_gaps(sample_keyword_rows)
        data_row = next(r for r in result if r["query"] == "data engineering")
        assert data_row["is_content_gap"] is False

    def test_empty_list(self) -> None:
        """Empty input returns empty output without error."""
        assert identify_content_gaps([]) == []


# ═══════════════════════════════════════════════════════════════════════════
# Page aggregation
# ═══════════════════════════════════════════════════════════════════════════


class TestAggregateByPage:
    """Tests for aggregate_by_page."""

    def test_aggregation_counts(
        self, sample_keyword_rows: list[dict[str, Any]]
    ) -> None:
        """Each unique page_url produces one aggregate row."""
        pages = aggregate_by_page(sample_keyword_rows)
        assert len(pages) == 4  # 4 unique URLs in sample data

    def test_totals(self) -> None:
        """Impressions and clicks are summed for the same page."""
        rows = [
            {
                "query": "a",
                "page_url": "https://x.com/p1",
                "impressions": 10,
                "clicks": 2,
                "ctr": 0.2,
                "position": 5.0,
            },
            {
                "query": "b",
                "page_url": "https://x.com/p1",
                "impressions": 20,
                "clicks": 3,
                "ctr": 0.15,
                "position": 7.0,
            },
        ]
        pages = aggregate_by_page(rows)
        assert len(pages) == 1
        assert pages[0]["total_impressions"] == 30
        assert pages[0]["total_clicks"] == 5


# ═══════════════════════════════════════════════════════════════════════════
# SQLite storage
# ═══════════════════════════════════════════════════════════════════════════


class TestStoreResults:
    """Tests for store_results."""

    def test_inserts_rows(self, tmp_db: Path) -> None:
        """Page and keyword rows are persisted to the database."""
        conn = init_db(tmp_db)
        page_rows = [
            {
                "page_url": "https://www.viney.ca/p1",
                "total_impressions": 100,
                "total_clicks": 10,
                "avg_ctr": 0.1,
                "avg_position": 5.0,
            }
        ]
        keyword_rows = [
            {
                "query": "test query",
                "page_url": "https://www.viney.ca/p1",
                "impressions": 100,
                "clicks": 10,
                "ctr": 0.1,
                "position": 5.0,
                "is_content_gap": False,
            }
        ]
        store_results(conn, page_rows, keyword_rows, "2026-04-05T00:00:00+00:00")

        perf_rows = conn.execute("SELECT * FROM search_performance").fetchall()
        kw_rows = conn.execute("SELECT * FROM keyword_data").fetchall()
        conn.close()

        assert len(perf_rows) == 1
        assert len(kw_rows) == 1
        assert perf_rows[0][0] == "https://www.viney.ca/p1"
        assert kw_rows[0][0] == "test query"


# ═══════════════════════════════════════════════════════════════════════════
# Fetch (mocked API)
# ═══════════════════════════════════════════════════════════════════════════


class TestFetchSearchAnalytics:
    """Tests for fetch_search_analytics with mocked GSC API."""

    def test_successful_fetch(self) -> None:
        """Rows are returned from the mocked API response."""
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.return_value = {
            "rows": _sample_gsc_rows(),
        }
        rows = fetch_search_analytics(mock_service, "https://www.viney.ca/", 30)
        assert len(rows) == 4

    def test_empty_response(self) -> None:
        """Empty response returns an empty list (new property scenario)."""
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.return_value = {}
        rows = fetch_search_analytics(mock_service, "https://www.viney.ca/", 30)
        assert rows == []

    def test_no_rows_key(self) -> None:
        """Response with explicit empty rows list."""
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.return_value = {"rows": []}
        rows = fetch_search_analytics(mock_service, "https://www.viney.ca/", 30)
        assert rows == []


# ═══════════════════════════════════════════════════════════════════════════
# Full ETL pipeline (mocked)
# ═══════════════════════════════════════════════════════════════════════════


class TestRunEtl:
    """Integration tests for run_etl with mocked API."""

    @patch("scripts.gsc_etl.build_gsc_service")
    def test_full_pipeline(self, mock_build: MagicMock, tmp_db: Path) -> None:
        """End-to-end: data flows from API through transforms into SQLite."""
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.return_value = {
            "rows": _sample_gsc_rows(),
        }
        mock_build.return_value = mock_service

        summary = run_etl(
            credentials_path="/fake/creds.json",
            site_url="https://www.viney.ca/",
            days=30,
            db_path=tmp_db,
        )

        assert summary["total_queries"] == 4
        assert summary["total_pages"] == 4
        assert summary["content_gaps"] >= 1

        # Verify SQLite
        conn = sqlite3.connect(str(tmp_db))
        perf = conn.execute("SELECT COUNT(*) FROM search_performance").fetchone()[0]
        kw = conn.execute("SELECT COUNT(*) FROM keyword_data").fetchone()[0]
        conn.close()
        assert perf == 4
        assert kw == 4

    @patch("scripts.gsc_etl.build_gsc_service")
    def test_empty_pipeline(self, mock_build: MagicMock, tmp_db: Path) -> None:
        """Empty API response results in zero counts and no DB writes."""
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.return_value = {}
        mock_build.return_value = mock_service

        summary = run_etl(
            credentials_path="/fake/creds.json",
            site_url="https://www.viney.ca/",
            days=30,
            db_path=tmp_db,
        )

        assert summary == {"total_queries": 0, "total_pages": 0, "content_gaps": 0}
