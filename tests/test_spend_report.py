"""Tests for scripts/spend_report.py.

RED phase: written before implementation exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.spend_report import (
    aggregate,
    filter_since,
    load_log,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RUNS = [
    {
        "timestamp": "2026-05-01T10:00:00+00:00",
        "topic": "AI coding agents",
        "total_cost_usd": 0.12,
        "writer_cost_usd": 0.10,
        "graphics_cost_usd": 0.02,
        "writer_model": "claude-sonnet-4-6",
        "graphics_model": "claude-sonnet-4-6",
        "publication_validator_passed": True,
        "publication_ready": True,
        "editorial_score": 82,
        "article_chars": 4800,
    },
    {
        "timestamp": "2026-05-01T14:00:00+00:00",
        "topic": "AI coding agents",
        "total_cost_usd": 0.31,
        "writer_cost_usd": 0.28,
        "graphics_cost_usd": 0.03,
        "writer_model": "claude-sonnet-4-6",
        "graphics_model": "claude-sonnet-4-6",
        "publication_validator_passed": False,
        "publication_ready": False,
        "editorial_score": 55,
        "article_chars": 3200,
    },
    {
        "timestamp": "2026-05-02T09:00:00+00:00",
        "topic": "test coverage myths",
        "total_cost_usd": 0.09,
        "writer_cost_usd": 0.07,
        "graphics_cost_usd": 0.02,
        "writer_model": "claude-sonnet-4-6",
        "graphics_model": "claude-sonnet-4-6",
        "publication_validator_passed": True,
        "publication_ready": True,
        "editorial_score": 91,
        "article_chars": 5100,
    },
]


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    path = tmp_path / "costs.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in SAMPLE_RUNS) + "\n")
    return path


# ---------------------------------------------------------------------------
# T1a: load_log parses JSONL into a list of dicts
# ---------------------------------------------------------------------------


def test_load_log_returns_all_entries(log_file: Path) -> None:
    runs = load_log(log_file)
    assert len(runs) == 3
    assert runs[0]["topic"] == "AI coding agents"


def test_load_log_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_log(tmp_path / "nonexistent.jsonl")


# ---------------------------------------------------------------------------
# T1b: filter_since narrows by date
# ---------------------------------------------------------------------------


def test_filter_since_excludes_earlier_entries(log_file: Path) -> None:
    runs = load_log(log_file)
    filtered = filter_since(runs, "2026-05-02")
    assert len(filtered) == 1
    assert filtered[0]["topic"] == "test coverage myths"


def test_filter_since_none_returns_all(log_file: Path) -> None:
    runs = load_log(log_file)
    assert filter_since(runs, None) == runs


# ---------------------------------------------------------------------------
# T1c: aggregate produces correct global + per-topic stats
# ---------------------------------------------------------------------------


def test_aggregate_global_totals(log_file: Path) -> None:
    runs = load_log(log_file)
    report = aggregate(runs)
    assert report.total_runs == 3
    assert report.total_cost_usd == pytest.approx(0.52, abs=1e-6)
    assert report.avg_cost_usd == pytest.approx(0.52 / 3, abs=1e-6)


def test_aggregate_success_rate(log_file: Path) -> None:
    runs = load_log(log_file)
    report = aggregate(runs)
    # 2 out of 3 passed
    assert report.success_rate == pytest.approx(2 / 3, abs=1e-6)


def test_aggregate_top_topics_ordered_by_cost(log_file: Path) -> None:
    runs = load_log(log_file)
    report = aggregate(runs)
    # "AI coding agents" has two runs totalling $0.43; "test coverage myths" $0.09
    assert report.top_topics[0].topic == "AI coding agents"
    assert report.top_topics[0].total_cost_usd == pytest.approx(0.43, abs=1e-6)
    assert report.top_topics[0].run_count == 2
    assert report.top_topics[1].topic == "test coverage myths"


# ---------------------------------------------------------------------------
# T1d: SpendReport.to_json round-trips cleanly
# ---------------------------------------------------------------------------


def test_to_json_is_valid_json(log_file: Path) -> None:
    runs = load_log(log_file)
    report = aggregate(runs)
    payload = report.to_json()
    parsed = json.loads(payload)
    assert parsed["total_runs"] == 3
    assert "top_topics" in parsed


def test_to_table_contains_key_fields(log_file: Path) -> None:
    runs = load_log(log_file)
    report = aggregate(runs)
    table = report.to_table()
    assert "AI coding agents" in table
    assert "$0." in table
