"""Tests for the Agent Performance Metrics Dashboard (Story 32 / #metrics).

Covers:
- DB schema creation (``init_db``)
- Record insertion (``record_run``)
- Metric calculations (``compute_summary``)
- CLI integration (``record_metrics.main``)
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest

from scripts.record_metrics import (
    compute_summary,
    fetch_all_runs,
    init_db,
    record_run,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Return a fresh temporary database path for each test.

    Args:
        tmp_path: pytest temporary directory.

    Returns:
        Path to a not-yet-created SQLite file inside *tmp_path*.
    """
    return tmp_path / "test_metrics.db"


# ---------------------------------------------------------------------------
# DB schema tests
# ---------------------------------------------------------------------------


class TestInitDb:
    """Verify that ``init_db`` creates the correct schema."""

    def test_creates_file(self, tmp_db: Path) -> None:
        """Database file is created when it does not yet exist."""
        assert not tmp_db.exists()
        conn = init_db(tmp_db)
        conn.close()
        assert tmp_db.exists()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Parent directories are created automatically."""
        nested = tmp_path / "a" / "b" / "metrics.db"
        conn = init_db(nested)
        conn.close()
        assert nested.exists()

    def test_table_exists(self, tmp_db: Path) -> None:
        """The *pipeline_runs* table is present after initialisation."""
        conn = init_db(tmp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_runs'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "pipeline_runs" in tables

    def test_correct_columns(self, tmp_db: Path) -> None:
        """The *pipeline_runs* table has all required columns."""
        expected_columns = {
            "run_id",
            "timestamp",
            "agent_name",
            "topic",
            "editorial_score",
            "gates_passed",
            "token_count",
            "cost_usd",
            "duration_s",
            "status",
        }
        conn = init_db(tmp_db)
        cursor = conn.execute("PRAGMA table_info(pipeline_runs)")
        actual_columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        assert expected_columns == actual_columns

    def test_idempotent(self, tmp_db: Path) -> None:
        """Calling *init_db* twice does not raise an error."""
        conn = init_db(tmp_db)
        conn.close()
        conn2 = init_db(tmp_db)
        conn2.close()

    def test_run_id_is_primary_key(self, tmp_db: Path) -> None:
        """run_id is the primary key of the table."""
        conn = init_db(tmp_db)
        cursor = conn.execute("PRAGMA table_info(pipeline_runs)")
        pk_cols = [row[1] for row in cursor.fetchall() if row[5] == 1]
        conn.close()
        assert pk_cols == ["run_id"]


# ---------------------------------------------------------------------------
# Record insertion tests
# ---------------------------------------------------------------------------


class TestRecordRun:
    """Verify that ``record_run`` correctly inserts rows."""

    def test_returns_run_id(self, tmp_db: Path) -> None:
        """record_run returns the run_id string."""
        run_id = record_run("researcher", "AI in Finance", db_path=tmp_db)
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    def test_custom_run_id_is_preserved(self, tmp_db: Path) -> None:
        """A caller-supplied run_id is stored verbatim."""
        custom_id = str(uuid.uuid4())
        returned_id = record_run(
            "editor", "Test Topic", run_id=custom_id, db_path=tmp_db
        )
        assert returned_id == custom_id
        rows = fetch_all_runs(tmp_db)
        assert rows[0]["run_id"] == custom_id

    def test_row_is_stored(self, tmp_db: Path) -> None:
        """One row appears in the table after a single record_run call."""
        record_run("writer", "Blockchain Myths", db_path=tmp_db)
        rows = fetch_all_runs(tmp_db)
        assert len(rows) == 1

    def test_all_fields_stored(self, tmp_db: Path) -> None:
        """All supplied field values are persisted correctly."""
        custom_id = str(uuid.uuid4())
        record_run(
            agent_name="editor",
            topic="Quantum Computing",
            editorial_score=87.5,
            gates_passed=4,
            token_count=15000,
            cost_usd=0.045,
            duration_s=62.3,
            status="published",
            run_id=custom_id,
            db_path=tmp_db,
        )
        rows = fetch_all_runs(tmp_db)
        row = rows[0]
        assert row["agent_name"] == "editor"
        assert row["topic"] == "Quantum Computing"
        assert row["editorial_score"] == pytest.approx(87.5)
        assert row["gates_passed"] == 4
        assert row["token_count"] == 15000
        assert row["cost_usd"] == pytest.approx(0.045)
        assert row["duration_s"] == pytest.approx(62.3)
        assert row["status"] == "published"

    def test_multiple_rows(self, tmp_db: Path) -> None:
        """Multiple calls result in multiple distinct rows."""
        for i in range(5):
            record_run("researcher", f"Topic {i}", db_path=tmp_db)
        rows = fetch_all_runs(tmp_db)
        assert len(rows) == 5

    def test_invalid_status_raises(self, tmp_db: Path) -> None:
        """An unrecognised status value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            record_run(
                "researcher", "Bad Status Topic", status="nonsense", db_path=tmp_db
            )

    def test_valid_statuses(self, tmp_db: Path) -> None:
        """All valid status values are accepted without error."""
        for status in ("published", "revision", "failed", "unknown"):
            record_run("agent", f"Topic for {status}", status=status, db_path=tmp_db)
        rows = fetch_all_runs(tmp_db)
        assert len(rows) == 4

    def test_duplicate_run_id_raises(self, tmp_db: Path) -> None:
        """Inserting a duplicate run_id raises an IntegrityError."""
        rid = str(uuid.uuid4())
        record_run("agent", "Topic", run_id=rid, db_path=tmp_db)
        with pytest.raises(sqlite3.IntegrityError):
            record_run("agent", "Another Topic", run_id=rid, db_path=tmp_db)

    def test_default_values(self, tmp_db: Path) -> None:
        """Minimal call uses sensible defaults."""
        record_run("agent", "Topic", db_path=tmp_db)
        row = fetch_all_runs(tmp_db)[0]
        assert row["editorial_score"] == pytest.approx(0.0)
        assert row["gates_passed"] == 0
        assert row["token_count"] == 0
        assert row["cost_usd"] == pytest.approx(0.0)
        assert row["duration_s"] == pytest.approx(0.0)
        assert row["status"] == "unknown"


# ---------------------------------------------------------------------------
# fetch_all_runs tests
# ---------------------------------------------------------------------------


class TestFetchAllRuns:
    """Verify that ``fetch_all_runs`` returns expected data."""

    def test_empty_db_returns_empty_list(self, tmp_db: Path) -> None:
        """An empty table produces an empty list."""
        rows = fetch_all_runs(tmp_db)
        assert rows == []

    def test_returns_dicts(self, tmp_db: Path) -> None:
        """Rows are returned as plain dicts."""
        record_run("agent", "Topic", db_path=tmp_db)
        rows = fetch_all_runs(tmp_db)
        assert isinstance(rows[0], dict)

    def test_newest_first_ordering(self, tmp_db: Path) -> None:
        """Rows are ordered newest timestamp first."""
        record_run("a", "old", timestamp="2025-01-01T00:00:00+00:00", db_path=tmp_db)
        record_run("a", "new", timestamp="2026-01-01T00:00:00+00:00", db_path=tmp_db)
        rows = fetch_all_runs(tmp_db)
        assert rows[0]["topic"] == "new"
        assert rows[1]["topic"] == "old"


# ---------------------------------------------------------------------------
# compute_summary tests
# ---------------------------------------------------------------------------


class TestComputeSummary:
    """Verify aggregate metric calculations from ``compute_summary``."""

    def test_empty_list_returns_zeros(self) -> None:
        """An empty run list yields all-zero summary."""
        s = compute_summary([])
        assert s["total_runs"] == 0
        assert s["success_rate_pct"] == 0.0
        assert s["avg_editorial_score"] == 0.0

    def test_total_runs(self) -> None:
        """total_runs equals the number of input rows."""
        runs = [
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.01,
                "duration_s": 10,
            },
            {
                "status": "failed",
                "editorial_score": 40,
                "cost_usd": 0.02,
                "duration_s": 20,
            },
        ]
        s = compute_summary(runs)
        assert s["total_runs"] == 2

    def test_status_counts(self) -> None:
        """Published / revision / failed counts are correct."""
        runs = [
            {
                "status": "published",
                "editorial_score": 90,
                "cost_usd": 0.01,
                "duration_s": 5,
            },
            {
                "status": "published",
                "editorial_score": 85,
                "cost_usd": 0.02,
                "duration_s": 6,
            },
            {
                "status": "revision",
                "editorial_score": 60,
                "cost_usd": 0.01,
                "duration_s": 8,
            },
            {
                "status": "failed",
                "editorial_score": 20,
                "cost_usd": 0.005,
                "duration_s": 3,
            },
        ]
        s = compute_summary(runs)
        assert s["published_count"] == 2
        assert s["revision_count"] == 1
        assert s["failed_count"] == 1

    def test_success_rate_calculation(self) -> None:
        """success_rate_pct = published / total × 100."""
        runs = [
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.01,
                "duration_s": 10,
            },
            {
                "status": "failed",
                "editorial_score": 30,
                "cost_usd": 0.01,
                "duration_s": 5,
            },
            {
                "status": "failed",
                "editorial_score": 20,
                "cost_usd": 0.01,
                "duration_s": 4,
            },
            {
                "status": "failed",
                "editorial_score": 15,
                "cost_usd": 0.01,
                "duration_s": 3,
            },
        ]
        s = compute_summary(runs)
        assert s["success_rate_pct"] == pytest.approx(25.0)

    def test_avg_editorial_score(self) -> None:
        """avg_editorial_score is the arithmetic mean."""
        runs = [
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.01,
                "duration_s": 10,
            },
            {
                "status": "published",
                "editorial_score": 60,
                "cost_usd": 0.01,
                "duration_s": 10,
            },
        ]
        s = compute_summary(runs)
        assert s["avg_editorial_score"] == pytest.approx(70.0)

    def test_total_cost(self) -> None:
        """total_cost_usd sums all cost_usd values."""
        runs = [
            {
                "status": "published",
                "editorial_score": 70,
                "cost_usd": 0.10,
                "duration_s": 10,
            },
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.20,
                "duration_s": 15,
            },
        ]
        s = compute_summary(runs)
        assert s["total_cost_usd"] == pytest.approx(0.30)

    def test_avg_cost(self) -> None:
        """avg_cost_usd is total / count."""
        runs = [
            {
                "status": "published",
                "editorial_score": 70,
                "cost_usd": 0.10,
                "duration_s": 10,
            },
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.20,
                "duration_s": 15,
            },
        ]
        s = compute_summary(runs)
        assert s["avg_cost_usd"] == pytest.approx(0.15)

    def test_avg_duration(self) -> None:
        """avg_duration_s is the arithmetic mean of duration_s."""
        runs = [
            {
                "status": "published",
                "editorial_score": 70,
                "cost_usd": 0.01,
                "duration_s": 10,
            },
            {
                "status": "published",
                "editorial_score": 80,
                "cost_usd": 0.01,
                "duration_s": 30,
            },
        ]
        s = compute_summary(runs)
        assert s["avg_duration_s"] == pytest.approx(20.0)

    def test_all_published_100_percent_success(self) -> None:
        """If every run is published, success rate is 100%."""
        runs = [
            {
                "status": "published",
                "editorial_score": 90,
                "cost_usd": 0.01,
                "duration_s": 10,
            }
            for _ in range(3)
        ]
        s = compute_summary(runs)
        assert s["success_rate_pct"] == pytest.approx(100.0)
        assert s["failed_count"] == 0
        assert s["revision_count"] == 0


# ---------------------------------------------------------------------------
# End-to-end: record → fetch → summarise
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Integration: record → fetch → compute matches expectations."""

    def test_round_trip(self, tmp_db: Path) -> None:
        """Data recorded survives fetch and summary unchanged."""
        record_run(
            "researcher",
            "Alpha",
            editorial_score=85,
            gates_passed=5,
            token_count=10000,
            cost_usd=0.03,
            duration_s=50,
            status="published",
            db_path=tmp_db,
        )
        record_run(
            "writer",
            "Beta",
            editorial_score=55,
            gates_passed=2,
            token_count=8000,
            cost_usd=0.024,
            duration_s=40,
            status="revision",
            db_path=tmp_db,
        )
        record_run(
            "editor",
            "Gamma",
            editorial_score=20,
            gates_passed=1,
            token_count=5000,
            cost_usd=0.015,
            duration_s=30,
            status="failed",
            db_path=tmp_db,
        )

        rows = fetch_all_runs(tmp_db)
        assert len(rows) == 3

        summary = compute_summary(rows)
        assert summary["total_runs"] == 3
        assert summary["published_count"] == 1
        assert summary["revision_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["success_rate_pct"] == pytest.approx(100 / 3, rel=0.01)
        assert summary["avg_editorial_score"] == pytest.approx(
            (85 + 55 + 20) / 3, abs=0.01
        )
        assert summary["total_cost_usd"] == pytest.approx(0.03 + 0.024 + 0.015)
