"""Tests for scripts/content_intelligence.py.

Uses a temp SQLite database populated with synthetic fixtures so that
all tests are hermetic — no dependency on the live performance.db or
GA4 API.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

# Add scripts/ to path so we can import content_intelligence directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from content_intelligence import (  # noqa: E402
    ArticlePerformance,
    TrafficSummary,
    _is_article,
    get_bottom_performers,
    get_performance_context,
    get_top_performers,
    get_traffic_summary,
)


@pytest.fixture
def synthetic_db(tmp_path: Path) -> Path:
    """Create a synthetic performance.db with known data shape."""
    db_path = tmp_path / "performance.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE article_performance (
            page_path           TEXT,
            page_title          TEXT,
            pageviews           INTEGER,
            engagement_rate     REAL,
            avg_engagement_time REAL,
            scroll_depth_rate   REAL,
            composite_score     REAL,
            fetched_at          TEXT
        )
        """
    )

    # Three real articles, two non-article index pages, and one article
    # with multiple date rows to test aggregation.
    rows = [
        # High-performing article, single day
        (
            "/2026/01/01/great-article/",
            "Great Article",
            500,
            0.85,
            240.0,
            0.9,
            0.900,
            "2026-04-06",
        ),
        # Low-performing article, high pageviews (the viral-but-shallow case)
        (
            "/2026/01/15/viral-dud/",
            "Viral Dud",
            10000,
            0.15,
            45.0,
            0.2,
            0.100,
            "2026-04-06",
        ),
        # Medium article with two date rows — tests aggregation
        (
            "/2025/12/20/split-rows/",
            "Split Rows",
            100,
            0.60,
            120.0,
            0.5,
            0.500,
            "2026-04-05",
        ),
        (
            "/2025/12/20/split-rows/",
            "Split Rows",
            50,
            0.70,
            150.0,
            0.6,
            0.600,
            "2026-04-06",
        ),
        # Below min_pageviews threshold — should be excluded from top
        (
            "/2026/02/01/tiny/",
            "Tiny Article",
            2,
            0.99,
            300.0,
            0.95,
            0.999,
            "2026-04-06",
        ),
        # Non-article index pages — should be filtered out
        ("/", "Home", 5000, 0.5, 60.0, 0.3, 0.400, "2026-04-06"),
        ("/blog/", "Blog Archive", 200, 0.3, 30.0, 0.2, 0.200, "2026-04-06"),
        (
            "/software-engineering/",
            "Software Engineering",
            300,
            0.4,
            45.0,
            0.25,
            0.250,
            "2026-04-06",
        ),
    ]
    conn.executemany(
        "INSERT INTO article_performance VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def empty_db(tmp_path: Path) -> Path:
    """Create an empty performance.db (schema only, no rows)."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE article_performance (
            page_path           TEXT,
            page_title          TEXT,
            pageviews           INTEGER,
            engagement_rate     REAL,
            avg_engagement_time REAL,
            scroll_depth_rate   REAL,
            composite_score     REAL,
            fetched_at          TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


class TestIsArticle:
    """Unit tests for the _is_article heuristic."""

    def test_index_pages_are_not_articles(self) -> None:
        assert not _is_article("/")
        assert not _is_article("/blog/")
        assert not _is_article("/about/")
        assert not _is_article("/software-engineering/")

    def test_dated_paths_are_articles(self) -> None:
        assert _is_article("/2026/01/01/some-title/")
        assert _is_article("/2025/12/31/testing-times/")

    def test_undated_custom_pages_are_not_articles(self) -> None:
        assert not _is_article("/random-page/")
        assert not _is_article("/tags/")


class TestGetTopPerformers:
    """Tests for get_top_performers."""

    def test_returns_top_by_composite_score(self, synthetic_db: Path) -> None:
        top = get_top_performers(limit=5, db_path=synthetic_db)
        assert len(top) >= 2
        assert top[0].avg_composite_score >= top[-1].avg_composite_score

    def test_filters_non_articles(self, synthetic_db: Path) -> None:
        top = get_top_performers(limit=10, db_path=synthetic_db)
        for article in top:
            assert article.page_path not in {"/", "/blog/", "/software-engineering/"}

    def test_respects_min_pageviews(self, synthetic_db: Path) -> None:
        """Tiny article (2 pageviews) should be excluded even though it has the highest score."""
        top = get_top_performers(limit=10, min_pageviews=5, db_path=synthetic_db)
        paths = [a.page_path for a in top]
        assert "/2026/02/01/tiny/" not in paths

    def test_aggregates_by_page_path(self, synthetic_db: Path) -> None:
        """Article with two date rows should appear once with summed pageviews."""
        top = get_top_performers(limit=10, db_path=synthetic_db)
        split_rows = [a for a in top if a.page_path == "/2025/12/20/split-rows/"]
        assert len(split_rows) == 1
        assert split_rows[0].total_pageviews == 150  # 100 + 50

    def test_returns_empty_for_missing_db(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.db"
        assert get_top_performers(db_path=missing) == []

    def test_limit_is_respected(self, synthetic_db: Path) -> None:
        top = get_top_performers(limit=1, db_path=synthetic_db)
        assert len(top) == 1

    def test_returns_ArticlePerformance_instances(self, synthetic_db: Path) -> None:
        top = get_top_performers(limit=1, db_path=synthetic_db)
        assert isinstance(top[0], ArticlePerformance)


class TestGetBottomPerformers:
    """Tests for get_bottom_performers."""

    def test_returns_ascending_by_score(self, synthetic_db: Path) -> None:
        bottom = get_bottom_performers(limit=5, min_pageviews=5, db_path=synthetic_db)
        assert len(bottom) >= 2
        assert bottom[0].avg_composite_score <= bottom[-1].avg_composite_score

    def test_captures_viral_but_shallow(self, synthetic_db: Path) -> None:
        """The viral dud (10k views, 0.1 score) should be at the top of the bottom list."""
        bottom = get_bottom_performers(limit=5, min_pageviews=5, db_path=synthetic_db)
        assert bottom[0].page_path == "/2026/01/15/viral-dud/"
        assert bottom[0].total_pageviews == 10000

    def test_higher_min_pageviews_default(self, synthetic_db: Path) -> None:
        """Default min_pageviews=20 should exclude low-traffic articles."""
        bottom = get_bottom_performers(db_path=synthetic_db)
        for a in bottom:
            assert a.total_pageviews >= 20

    def test_returns_empty_for_missing_db(self, tmp_path: Path) -> None:
        assert get_bottom_performers(db_path=tmp_path / "nope.db") == []


class TestGetTrafficSummary:
    """Tests for get_traffic_summary."""

    def test_summary_counts_distinct_paths(self, synthetic_db: Path) -> None:
        summary = get_traffic_summary(db_path=synthetic_db)
        assert summary is not None
        # 7 distinct paths in fixture (split-rows counted once)
        assert summary.article_count == 7

    def test_summary_sums_pageviews(self, synthetic_db: Path) -> None:
        summary = get_traffic_summary(db_path=synthetic_db)
        assert summary is not None
        # 500 + 10000 + 100 + 50 + 2 + 5000 + 200 + 300 = 16152
        assert summary.total_pageviews == 16152

    def test_returns_none_for_missing_db(self, tmp_path: Path) -> None:
        assert get_traffic_summary(db_path=tmp_path / "nope.db") is None

    def test_returns_none_for_empty_db(self, empty_db: Path) -> None:
        assert get_traffic_summary(db_path=empty_db) is None

    def test_returns_TrafficSummary_instance(self, synthetic_db: Path) -> None:
        summary = get_traffic_summary(db_path=synthetic_db)
        assert isinstance(summary, TrafficSummary)


class TestGetPerformanceContext:
    """Tests for the primary prompt-injection function."""

    def test_contains_top_and_bottom_sections(self, synthetic_db: Path) -> None:
        context = get_performance_context(db_path=synthetic_db)
        assert "Top performers" in context
        assert "Underperformers" in context
        assert "## Performance Context" in context

    def test_contains_summary_line(self, synthetic_db: Path) -> None:
        context = get_performance_context(db_path=synthetic_db)
        assert "16,152" in context  # comma-formatted total_pageviews

    def test_graceful_fallback_for_missing_db(self, tmp_path: Path) -> None:
        context = get_performance_context(db_path=tmp_path / "nope.db")
        assert "No performance data" in context
        assert "## Performance Context" in context

    def test_graceful_fallback_for_empty_db(self, empty_db: Path) -> None:
        context = get_performance_context(db_path=empty_db)
        assert "No performance data" in context

    def test_has_actionable_instructions(self, synthetic_db: Path) -> None:
        context = get_performance_context(db_path=synthetic_db)
        assert "topic selection" in context.lower()

    def test_titles_truncated_in_tables(self, synthetic_db: Path) -> None:
        context = get_performance_context(db_path=synthetic_db)
        # No single line should be absurdly long
        for line in context.split("\n"):
            assert len(line) < 300
