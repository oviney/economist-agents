"""Tests for src/quality/chart_metrics.py.

Covers ChartMetricsCollector (initialization, chart lifecycle tracking,
visual QA recording, regeneration tracking, failure patterns, summary,
report export, persistence) and the get_metrics_collector() singleton.

All file I/O uses pytest's tmp_path fixture so tests run in isolation.
The module-level _metrics_collector cache is reset between tests via an
autouse fixture to prevent cross-test state leakage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.quality.chart_metrics as chart_metrics
from src.quality.chart_metrics import ChartMetricsCollector, get_metrics_collector

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset module-level singleton cache around every test.

    Without this, get_metrics_collector() tests would leak the cached
    instance into other tests (and pick up state from prior runs).
    """
    chart_metrics._metrics_collector = None
    yield
    chart_metrics._metrics_collector = None


@pytest.fixture
def metrics_path(tmp_path: Path) -> Path:
    """Provide a temporary metrics file path inside a fresh tmp dir."""
    return tmp_path / "metrics" / "chart_metrics.json"


@pytest.fixture
def collector(metrics_path: Path) -> ChartMetricsCollector:
    """A fresh collector backed by a tmp_path-scoped metrics file."""
    return ChartMetricsCollector(metrics_file=str(metrics_path))


# ═══════════════════════════════════════════════════════════════════════════
# Initialization & metrics loading
# ═══════════════════════════════════════════════════════════════════════════


class TestInitialization:
    def test_initializes_default_metrics_when_file_absent(
        self,
        metrics_path: Path,
    ) -> None:
        collector = ChartMetricsCollector(metrics_file=str(metrics_path))

        assert collector.metrics["version"] == "1.0"
        assert collector.metrics["summary"]["total_charts_generated"] == 0
        assert collector.metrics["summary"]["total_visual_qa_runs"] == 0
        assert collector.metrics["failure_patterns"] == {}
        assert collector.metrics["sessions"] == []
        assert collector.current_session["charts"] == []
        assert "start_time" in collector.current_session

    def test_loads_existing_metrics_from_file(self, metrics_path: Path) -> None:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {
            "version": "1.0",
            "last_updated": "2025-01-01T00:00:00",
            "summary": {
                "total_charts_generated": 7,
                "total_visual_qa_runs": 5,
                "visual_qa_pass_count": 4,
                "visual_qa_fail_count": 1,
                "total_zone_violations": 2,
                "total_regenerations": 3,
                "total_generation_time_seconds": 12.5,
            },
            "failure_patterns": {"zone_violation": {}},
            "sessions": [{"timestamp": "2025-01-01T00:00:00"}],
        }
        metrics_path.write_text(json.dumps(existing))

        collector = ChartMetricsCollector(metrics_file=str(metrics_path))

        assert collector.metrics["summary"]["total_charts_generated"] == 7
        assert collector.metrics["sessions"] == [{"timestamp": "2025-01-01T00:00:00"}]

    def test_recovers_from_corrupted_metrics_file(self, metrics_path: Path) -> None:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text("{not valid json")

        collector = ChartMetricsCollector(metrics_file=str(metrics_path))

        # Recovered to default schema
        assert collector.metrics["version"] == "1.0"
        assert collector.metrics["summary"]["total_charts_generated"] == 0

    def test_treats_empty_metrics_file_as_default(self, metrics_path: Path) -> None:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text("")

        collector = ChartMetricsCollector(metrics_file=str(metrics_path))

        assert collector.metrics["summary"]["total_charts_generated"] == 0

    def test_default_metrics_file_path_resolves_to_repo_skills_dir(self) -> None:
        # Actually invoke ChartMetricsCollector() with no args and assert
        # the resolved path matches the documented repo layout: three levels
        # up from chart_metrics.py + skills/chart_metrics.json. __init__
        # only reads the file (no write on construction), so this is safe.
        collector = ChartMetricsCollector()

        module_file = Path(chart_metrics.__file__).resolve()
        expected = module_file.parent.parent.parent / "skills" / "chart_metrics.json"

        assert collector.metrics_file == expected
        assert collector.metrics_file.name == "chart_metrics.json"
        assert collector.metrics_file.parent.name == "skills"


# ═══════════════════════════════════════════════════════════════════════════
# Chart lifecycle: start_chart, record_generation, record_regeneration
# ═══════════════════════════════════════════════════════════════════════════


class TestChartLifecycle:
    def test_start_chart_appends_record_with_expected_fields(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart(
            chart_title="GDP Growth",
            chart_spec={"type": "line"},
        )

        assert record["title"] == "GDP Growth"
        assert record["chart_type"] == "line"
        assert record["generation_success"] is None
        assert record["visual_qa_run"] is False
        assert record["zone_violations"] == []
        assert record["regeneration_count"] == 0
        assert record["errors"] == []
        assert collector.current_session["charts"] == [record]

    def test_start_chart_defaults_chart_type_to_unknown_when_missing(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart(chart_title="No Type", chart_spec={})

        assert record["chart_type"] == "unknown"

    def test_record_generation_success_increments_totals_and_records_time(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_generation(record, success=True)

        assert record["generation_success"] is True
        assert record["generation_time_seconds"] is not None
        assert record["generation_time_seconds"] >= 0
        assert collector.metrics["summary"]["total_charts_generated"] == 1
        assert (
            collector.metrics["summary"]["total_generation_time_seconds"]
            == record["generation_time_seconds"]
        )
        # No error should have been appended on success
        assert record["errors"] == []

    def test_record_generation_failure_with_error_appends_error_entry(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_generation(record, success=False, error="bad spec")

        assert record["generation_success"] is False
        assert collector.metrics["summary"]["total_charts_generated"] == 0
        assert len(record["errors"]) == 1
        assert record["errors"][0]["type"] == "generation_error"
        assert record["errors"][0]["message"] == "bad spec"
        assert "timestamp" in record["errors"][0]

    def test_record_generation_failure_without_error_records_no_error_entry(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_generation(record, success=False)

        assert record["generation_success"] is False
        assert record["errors"] == []
        assert collector.metrics["summary"]["total_charts_generated"] == 0

    def test_record_regeneration_increments_counters_and_appends_error(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_regeneration(record, reason="color mismatch")
        collector.record_regeneration(record, reason="zone violation")

        assert record["regeneration_count"] == 2
        assert collector.metrics["summary"]["total_regenerations"] == 2
        assert [e["type"] for e in record["errors"]] == ["regeneration", "regeneration"]
        assert record["errors"][0]["reason"] == "color mismatch"
        assert record["errors"][1]["reason"] == "zone violation"


# ═══════════════════════════════════════════════════════════════════════════
# Visual QA: record_visual_qa, _track_failure_pattern
# ═══════════════════════════════════════════════════════════════════════════


class TestVisualQA:
    def test_record_visual_qa_pass_updates_pass_count(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_visual_qa(
            record,
            {
                "overall_pass": True,
                "gates": {"zone_integrity": {"pass": True}},
            },
        )

        assert record["visual_qa_run"] is True
        assert record["visual_qa_passed"] is True
        assert collector.metrics["summary"]["total_visual_qa_runs"] == 1
        assert collector.metrics["summary"]["visual_qa_pass_count"] == 1
        assert collector.metrics["summary"]["visual_qa_fail_count"] == 0
        assert collector.metrics["summary"]["total_zone_violations"] == 0
        assert collector.metrics["failure_patterns"] == {}

    def test_record_visual_qa_fail_with_zone_and_critical_issues(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_visual_qa(
            record,
            {
                "overall_pass": False,
                "gates": {
                    "zone_integrity": {
                        "pass": False,
                        "issues": ["title overlaps chart", "Title overlaps chart"],
                    },
                },
                "critical_issues": ["axis labels missing"],
            },
        )

        assert record["visual_qa_passed"] is False
        assert collector.metrics["summary"]["visual_qa_fail_count"] == 1
        assert collector.metrics["summary"]["visual_qa_pass_count"] == 0
        assert collector.metrics["summary"]["total_zone_violations"] == 2
        assert record["zone_violations"] == [
            "title overlaps chart",
            "Title overlaps chart",
        ]

        # Failure patterns: two identical (after normalization) zone violations
        # collapse into one pattern with count=2
        zone_patterns = collector.metrics["failure_patterns"]["zone_violation"]
        assert zone_patterns["title overlaps chart"]["count"] == 2

        # Critical issue tracked under its own bucket
        critical_patterns = collector.metrics["failure_patterns"]["critical_issue"]
        assert critical_patterns["axis labels missing"]["count"] == 1

    def test_record_visual_qa_fail_with_no_zone_violations(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        collector.record_visual_qa(
            record,
            {
                "overall_pass": False,
                "gates": {"zone_integrity": {"pass": True}},
                "critical_issues": [],
            },
        )

        assert collector.metrics["summary"]["visual_qa_fail_count"] == 1
        assert collector.metrics["summary"]["total_zone_violations"] == 0
        assert collector.metrics["failure_patterns"] == {}

    def test_record_visual_qa_missing_gates_treats_zone_as_passing(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("Test", {"type": "bar"})

        # No "gates" key at all — defaults inside the method should keep
        # zone_integrity as passing (no violations recorded).
        collector.record_visual_qa(record, {"overall_pass": True})

        assert collector.metrics["summary"]["visual_qa_pass_count"] == 1
        assert collector.metrics["summary"]["total_zone_violations"] == 0

    def test_track_failure_pattern_updates_last_seen_on_recurrence(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        collector._track_failure_pattern("zone_violation", "  Overlapping Title  ")
        first = collector.metrics["failure_patterns"]["zone_violation"][
            "overlapping title"
        ]["first_seen"]

        collector._track_failure_pattern("zone_violation", "OVERLAPPING title")

        entry = collector.metrics["failure_patterns"]["zone_violation"][
            "overlapping title"
        ]
        assert entry["count"] == 2
        assert entry["first_seen"] == first  # first_seen is preserved
        assert entry["last_seen"] >= first


# ═══════════════════════════════════════════════════════════════════════════
# Session lifecycle: end_session, save
# ═══════════════════════════════════════════════════════════════════════════


class TestSessionAndPersistence:
    def test_end_session_summarizes_and_persists(
        self,
        collector: ChartMetricsCollector,
        metrics_path: Path,
    ) -> None:
        # Successful chart with passing QA
        r1 = collector.start_chart("A", {"type": "bar"})
        collector.record_generation(r1, success=True)
        collector.record_visual_qa(
            r1,
            {"overall_pass": True, "gates": {"zone_integrity": {"pass": True}}},
        )

        # Failed chart, no QA
        r2 = collector.start_chart("B", {"type": "line"})
        collector.record_generation(r2, success=False, error="boom")

        collector.end_session()

        assert metrics_path.exists()
        on_disk = json.loads(metrics_path.read_text())
        assert len(on_disk["sessions"]) == 1
        session = on_disk["sessions"][0]
        assert session["charts_generated"] == 1
        assert session["visual_qa_runs"] == 1
        assert session["visual_qa_passed"] == 1
        assert len(session["charts"]) == 2
        assert session["duration_seconds"] >= 0
        assert "last_updated" in on_disk

    def test_end_session_with_no_charts_still_writes_session(
        self,
        collector: ChartMetricsCollector,
        metrics_path: Path,
    ) -> None:
        collector.end_session()

        on_disk = json.loads(metrics_path.read_text())
        assert len(on_disk["sessions"]) == 1
        assert on_disk["sessions"][0]["charts_generated"] == 0
        assert on_disk["sessions"][0]["visual_qa_runs"] == 0
        assert on_disk["sessions"][0]["charts"] == []

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c" / "metrics.json"
        collector = ChartMetricsCollector(metrics_file=str(nested))

        collector.save()

        assert nested.exists()
        loaded = json.loads(nested.read_text())
        assert loaded["version"] == "1.0"


# ═══════════════════════════════════════════════════════════════════════════
# Summary metrics: get_summary
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSummary:
    def test_summary_with_zero_activity_avoids_division_by_zero(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        summary = collector.get_summary()

        assert summary["avg_generation_time_seconds"] == 0.0
        assert summary["visual_qa_pass_rate"] == 0.0
        assert summary["avg_zone_violations_per_chart"] == 0.0

    def test_summary_computes_derived_metrics(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        # Seed the summary directly to keep this test deterministic
        collector.metrics["summary"].update(
            {
                "total_charts_generated": 4,
                "total_visual_qa_runs": 5,
                "visual_qa_pass_count": 3,
                "visual_qa_fail_count": 2,
                "total_zone_violations": 2,
                "total_generation_time_seconds": 8.0,
            },
        )

        summary = collector.get_summary()

        assert summary["avg_generation_time_seconds"] == pytest.approx(2.0)
        assert summary["visual_qa_pass_rate"] == pytest.approx(60.0)
        assert summary["avg_zone_violations_per_chart"] == pytest.approx(0.5)

    def test_summary_is_a_copy_not_a_live_reference(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        summary = collector.get_summary()
        summary["total_charts_generated"] = 999

        assert collector.metrics["summary"]["total_charts_generated"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Failure patterns: get_top_failure_patterns
# ═══════════════════════════════════════════════════════════════════════════


class TestTopFailurePatterns:
    def test_returns_empty_list_when_no_patterns(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        assert collector.get_top_failure_patterns() == []

    def test_returns_patterns_sorted_by_count_descending(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        for _ in range(3):
            collector._track_failure_pattern("zone_violation", "title overlap")
        collector._track_failure_pattern("zone_violation", "axis missing")
        for _ in range(5):
            collector._track_failure_pattern("critical_issue", "no data")

        patterns = collector.get_top_failure_patterns()

        assert [p["issue"] for p in patterns] == [
            "no data",
            "title overlap",
            "axis missing",
        ]
        assert [p["count"] for p in patterns] == [5, 3, 1]
        assert {p["type"] for p in patterns} == {"zone_violation", "critical_issue"}

    def test_respects_limit_argument(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        for i in range(15):
            for _ in range(i + 1):
                collector._track_failure_pattern("zone_violation", f"issue {i}")

        assert len(collector.get_top_failure_patterns(limit=5)) == 5
        # The top entries are the highest-count ones
        top = collector.get_top_failure_patterns(limit=3)
        assert [p["count"] for p in top] == [15, 14, 13]


# ═══════════════════════════════════════════════════════════════════════════
# Report export
# ═══════════════════════════════════════════════════════════════════════════


class TestExportReport:
    def test_report_includes_summary_headings_when_empty(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        report = collector.export_report()

        assert "CHART METRICS REPORT" in report
        assert "SUMMARY METRICS:" in report
        assert "Total Charts Generated: 0" in report
        assert "TOP FAILURE PATTERNS:" in report
        assert "No failure patterns recorded yet" in report

    def test_report_includes_failure_patterns_and_session_section(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        # Build some real state
        record = collector.start_chart("X", {"type": "line"})
        collector.record_generation(record, success=True)
        collector.record_visual_qa(
            record,
            {
                "overall_pass": False,
                "gates": {
                    "zone_integrity": {
                        "pass": False,
                        "issues": ["overlapping title"],
                    },
                },
                "critical_issues": ["missing axis"],
            },
        )
        collector.end_session()

        report = collector.export_report(include_sessions=True)

        assert "zone_violation" in report
        assert "overlapping title" in report
        assert "RECENT SESSIONS:" in report

    def test_report_omits_session_section_by_default(
        self,
        collector: ChartMetricsCollector,
    ) -> None:
        record = collector.start_chart("X", {"type": "line"})
        collector.record_generation(record, success=True)
        collector.end_session()

        report = collector.export_report()

        assert "RECENT SESSIONS:" not in report


# ═══════════════════════════════════════════════════════════════════════════
# Module-level singleton: get_metrics_collector
# ═══════════════════════════════════════════════════════════════════════════


class TestGetMetricsCollectorSingleton:
    def test_returns_same_instance_on_repeated_calls(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force ChartMetricsCollector to use a tmp path even when invoked
        # without args (which is how get_metrics_collector() calls it).
        original = ChartMetricsCollector.__init__

        def patched_init(self, metrics_file=None):  # type: ignore[no-redef]
            if metrics_file is None:
                metrics_file = str(tmp_path / "singleton.json")
            original(self, metrics_file)

        monkeypatch.setattr(ChartMetricsCollector, "__init__", patched_init)

        first = get_metrics_collector()
        second = get_metrics_collector()

        assert first is second
        assert isinstance(first, ChartMetricsCollector)

    def test_creates_collector_lazily(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Before any call, the cache is None (set by the autouse fixture)
        assert chart_metrics._metrics_collector is None

        original = ChartMetricsCollector.__init__

        def patched_init(self, metrics_file=None):  # type: ignore[no-redef]
            if metrics_file is None:
                metrics_file = str(tmp_path / "lazy.json")
            original(self, metrics_file)

        monkeypatch.setattr(ChartMetricsCollector, "__init__", patched_init)

        instance = get_metrics_collector()

        assert chart_metrics._metrics_collector is instance
