"""Tests for src/quality/agent_metrics.py.

Covers AgentMetrics: initialization, per-agent tracking (research, writer,
editor, graphics), trend calculation, summary aggregation, persistence,
history queries, and human-readable report export.

All file I/O uses pytest's tmp_path fixture so tests run in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.quality.agent_metrics import AgentMetrics

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def metrics_path(tmp_path: Path) -> Path:
    """Provide a temporary metrics file path inside a fresh tmp dir."""
    return tmp_path / "data" / "skills_state" / "agent_metrics.json"


@pytest.fixture
def metrics(metrics_path: Path) -> AgentMetrics:
    """A fresh AgentMetrics instance backed by a tmp_path-scoped file."""
    return AgentMetrics(metrics_file=str(metrics_path))


# ═══════════════════════════════════════════════════════════════════════════
# Initialization & metrics loading
# ═══════════════════════════════════════════════════════════════════════════


class TestInitialization:
    def test_initializes_default_structure_when_file_absent(
        self,
        metrics_path: Path,
    ) -> None:
        m = AgentMetrics(metrics_file=str(metrics_path))

        assert m.metrics["version"] == "1.0"
        assert m.metrics["runs"] == []
        assert m.metrics["summary"]["total_runs"] == 0
        # All four agent slots exist but are empty
        for agent in [
            "research_agent",
            "writer_agent",
            "editor_agent",
            "graphics_agent",
        ]:
            assert m.metrics["summary"]["agents"][agent] == {}

    def test_loads_existing_metrics_file(self, metrics_path: Path) -> None:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {
            "version": "1.0",
            "created": "2026-01-01T00:00:00",
            "runs": [{"timestamp": "2026-01-02T00:00:00", "agents": {}}],
            "summary": {
                "total_runs": 1,
                "agents": {
                    "research_agent": {"total_runs": 1},
                    "writer_agent": {},
                    "editor_agent": {},
                    "graphics_agent": {},
                },
            },
        }
        metrics_path.write_text(json.dumps(existing))

        m = AgentMetrics(metrics_file=str(metrics_path))

        assert m.metrics["runs"] == existing["runs"]
        assert m.metrics["summary"]["total_runs"] == 1

    def test_default_metrics_file_resolves_under_repo_root(self) -> None:
        """When no path is passed, file resolves to data/skills_state/agent_metrics.json."""
        m = AgentMetrics()
        assert m.metrics_file.name == "agent_metrics.json"
        assert m.metrics_file.parent.name == "skills_state"

    def test_current_run_initialized_with_timestamp_and_empty_agents(
        self,
        metrics: AgentMetrics,
    ) -> None:
        assert "timestamp" in metrics.current_run
        assert metrics.current_run["agents"] == {}


# ═══════════════════════════════════════════════════════════════════════════
# track_research_agent
# ═══════════════════════════════════════════════════════════════════════════


class TestTrackResearchAgent:
    def test_happy_path_high_verification_passes(self, metrics: AgentMetrics) -> None:
        metrics.track_research_agent(
            data_points=10,
            verified=9,
            unverified=1,
            sources=["src1", "src2"],
            token_usage=1000,
        )

        r = metrics.current_run["agents"]["research_agent"]
        assert r["verification_rate"] == 90.0
        assert r["quality_score"] == 90.0
        assert r["sources"] == ["src1", "src2"]
        assert r["actual"] == "Pass"
        assert r["cost_per_quality_unit"] == round(1000 / 90.0, 2)

    def test_zero_data_points_avoids_division_by_zero(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_research_agent(data_points=0, verified=0, unverified=0)

        r = metrics.current_run["agents"]["research_agent"]
        assert r["verification_rate"] == 0
        assert r["quality_score"] == 0
        assert r["cost_per_quality_unit"] == 0
        assert r["actual"] == "Needs improvement"

    def test_validation_failure_halves_quality_score(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_research_agent(
            data_points=10,
            verified=10,
            unverified=0,
            validation_passed=False,
        )

        r = metrics.current_run["agents"]["research_agent"]
        assert r["verification_rate"] == 100.0
        assert r["quality_score"] == 50.0

    def test_sources_default_to_empty_list(self, metrics: AgentMetrics) -> None:
        metrics.track_research_agent(data_points=5, verified=4, unverified=1)
        assert metrics.current_run["agents"]["research_agent"]["sources"] == []


# ═══════════════════════════════════════════════════════════════════════════
# track_writer_agent
# ═══════════════════════════════════════════════════════════════════════════


class TestTrackWriterAgent:
    def test_clean_draft_scores_100(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=1200,
            banned_phrases=0,
            validation_passed=True,
            regenerations=0,
            chart_embedded=True,
            token_usage=500,
        )

        w = metrics.current_run["agents"]["writer_agent"]
        assert w["quality_score"] == 100
        assert w["token_usage"] == 500  # regenerations=0 → multiplier 1
        assert w["actual"] == "Pass"

    def test_banned_phrases_deduct_ten_each(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=3,
            validation_passed=True,
            regenerations=0,
        )
        # 100 - 3*10 = 70
        assert metrics.current_run["agents"]["writer_agent"]["quality_score"] == 70
        assert (
            metrics.current_run["agents"]["writer_agent"]["actual"]
            == "Needs improvement"
        )

    def test_missing_chart_deducts_twenty(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=True,
            regenerations=0,
            chart_embedded=False,
        )
        assert metrics.current_run["agents"]["writer_agent"]["quality_score"] == 80

    def test_validation_failure_deducts_thirty(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=False,
            regenerations=0,
        )
        assert metrics.current_run["agents"]["writer_agent"]["quality_score"] == 70

    def test_quality_score_floors_at_zero(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=20,  # -200, far below zero
            validation_passed=False,
            regenerations=0,
            chart_embedded=False,
        )
        w = metrics.current_run["agents"]["writer_agent"]
        assert w["quality_score"] == 0
        assert w["cost_per_quality_unit"] == float("inf")

    def test_regenerations_multiply_token_cost(self, metrics: AgentMetrics) -> None:
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=True,
            regenerations=2,
            token_usage=100,
        )
        # total_tokens = 100 * (2+1) = 300
        assert metrics.current_run["agents"]["writer_agent"]["token_usage"] == 300


# ═══════════════════════════════════════════════════════════════════════════
# track_editor_agent
# ═══════════════════════════════════════════════════════════════════════════


class TestTrackEditorAgent:
    def test_all_gates_passed(self, metrics: AgentMetrics) -> None:
        metrics.track_editor_agent(
            gates_passed=5,
            gates_failed=0,
            edits_made=10,
            token_usage=200,
        )
        e = metrics.current_run["agents"]["editor_agent"]
        assert e["gate_pass_rate"] == 100.0
        assert e["quality_score"] == 100.0
        assert e["actual"] == "Pass"

    def test_zero_gates_avoids_division_by_zero(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_editor_agent(
            gates_passed=0,
            gates_failed=0,
            edits_made=0,
        )
        e = metrics.current_run["agents"]["editor_agent"]
        assert e["gate_pass_rate"] == 0
        assert e["quality_score"] == 0
        assert e["cost_per_quality_unit"] == 0

    def test_quality_issues_deduct_five_each_and_floor_at_zero(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_editor_agent(
            gates_passed=3,
            gates_failed=2,
            edits_made=5,
            quality_issues=["issue1"] * 20,  # 20*5 = 100 deduction
        )
        e = metrics.current_run["agents"]["editor_agent"]
        # gate_pass_rate = 60.0, then 60 - 100 = -40 → floored to 0
        assert e["quality_score"] == 0
        assert e["actual"] == "Failed 2 gates"

    def test_quality_issues_default_to_empty_list(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_editor_agent(gates_passed=5, gates_failed=0, edits_made=5)
        assert metrics.current_run["agents"]["editor_agent"]["quality_issues"] == []


# ═══════════════════════════════════════════════════════════════════════════
# track_graphics_agent
# ═══════════════════════════════════════════════════════════════════════════


class TestTrackGraphicsAgent:
    def test_clean_qa_run(self, metrics: AgentMetrics) -> None:
        metrics.track_graphics_agent(
            charts_generated=2,
            visual_qa_passed=2,
            zone_violations=0,
            regenerations=0,
            token_usage=300,
        )
        g = metrics.current_run["agents"]["graphics_agent"]
        assert g["visual_qa_pass_rate"] == 100.0
        assert g["quality_score"] == 100.0
        assert g["actual"] == "Pass"
        assert g["token_usage"] == 300

    def test_zero_charts_avoids_division_by_zero(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_graphics_agent(
            charts_generated=0,
            visual_qa_passed=0,
            zone_violations=0,
            regenerations=0,
        )
        g = metrics.current_run["agents"]["graphics_agent"]
        assert g["visual_qa_pass_rate"] == 0
        assert g["quality_score"] == 0
        # Graphics agent uses float("inf") sentinel when quality_score==0
        assert g["cost_per_quality_unit"] == float("inf")

    def test_zone_violations_deduct_fifteen_each(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_graphics_agent(
            charts_generated=2,
            visual_qa_passed=2,
            zone_violations=2,
            regenerations=0,
        )
        # qa_pass_rate=100, then 100 - 2*15 = 70
        g = metrics.current_run["agents"]["graphics_agent"]
        assert g["quality_score"] == 70
        assert g["actual"] == "2 violations"

    def test_score_floors_at_zero_and_cost_is_inf(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_graphics_agent(
            charts_generated=1,
            visual_qa_passed=0,
            zone_violations=10,  # -150
            regenerations=1,
            token_usage=50,
        )
        g = metrics.current_run["agents"]["graphics_agent"]
        assert g["quality_score"] == 0
        assert g["cost_per_quality_unit"] == float("inf")
        # regenerations=1 → multiplier 2
        assert g["token_usage"] == 100


# ═══════════════════════════════════════════════════════════════════════════
# finalize_run + save + persistence
# ═══════════════════════════════════════════════════════════════════════════


class TestFinalizeRunAndSave:
    def test_finalize_run_computes_success_rate(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.track_research_agent(data_points=10, verified=9, unverified=1)
        metrics.track_writer_agent(
            word_count=900,
            banned_phrases=5,  # makes it Needs improvement
            validation_passed=True,
            regenerations=0,
        )
        metrics.finalize_run()

        summary = metrics.current_run["summary"]
        assert summary["agents_tracked"] == 2
        assert summary["agents_successful"] == 1
        assert summary["success_rate"] == 50.0

    def test_finalize_run_with_no_agents_returns_zero(
        self,
        metrics: AgentMetrics,
    ) -> None:
        metrics.finalize_run()
        assert metrics.current_run["summary"]["success_rate"] == 0

    def test_save_persists_to_disk_and_creates_parent_dirs(
        self,
        metrics: AgentMetrics,
        metrics_path: Path,
    ) -> None:
        metrics.track_research_agent(data_points=10, verified=9, unverified=1)
        metrics.save()

        assert metrics_path.exists()
        loaded = json.loads(metrics_path.read_text())
        assert loaded["summary"]["total_runs"] == 1
        assert "research_agent" in loaded["runs"][0]["agents"]

    def test_save_appends_subsequent_runs(
        self,
        metrics_path: Path,
    ) -> None:
        m1 = AgentMetrics(metrics_file=str(metrics_path))
        m1.track_research_agent(data_points=10, verified=8, unverified=2)
        m1.save()

        m2 = AgentMetrics(metrics_file=str(metrics_path))
        m2.track_research_agent(data_points=10, verified=10, unverified=0)
        m2.save()

        loaded = json.loads(metrics_path.read_text())
        assert loaded["summary"]["total_runs"] == 2
        assert len(loaded["runs"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# _update_agent_summaries (exercised via save())
# ═══════════════════════════════════════════════════════════════════════════


class TestAgentSummaries:
    def test_research_summary_aggregates_verification_rate(
        self,
        metrics_path: Path,
    ) -> None:
        for verified in (6, 8, 10):
            m = AgentMetrics(metrics_file=str(metrics_path))
            m.track_research_agent(
                data_points=10,
                verified=verified,
                unverified=10 - verified,
            )
            m.save()

        loaded = json.loads(metrics_path.read_text())
        research = loaded["summary"]["agents"]["research_agent"]
        assert research["total_runs"] == 3
        assert research["avg_verification_rate"] == round((60 + 80 + 100) / 3, 1)
        # 60→100 trend = improving
        assert "improving" in research["trend"]

    def test_writer_summary_tracks_clean_drafts_and_rework_rate(
        self,
        metrics_path: Path,
    ) -> None:
        # Run 1: clean draft, no regens
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=True,
            regenerations=0,
        )
        m.save()

        # Run 2: dirty draft with regens
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_writer_agent(
            word_count=900,
            banned_phrases=2,
            validation_passed=False,
            regenerations=2,
        )
        m.save()

        loaded = json.loads(metrics_path.read_text())
        writer = loaded["summary"]["agents"]["writer_agent"]
        assert writer["total_runs"] == 2
        assert writer["clean_draft_rate"] == 50.0
        assert writer["avg_regenerations"] == 1.0
        assert writer["rework_rate"] == 50.0
        assert writer["validation_pass_rate"] == 50.0

    def test_editor_summary_computes_avg_gate_pass_rate_and_trend(
        self,
        metrics_path: Path,
    ) -> None:
        for passed in (3, 5):
            m = AgentMetrics(metrics_file=str(metrics_path))
            m.track_editor_agent(
                gates_passed=passed,
                gates_failed=5 - passed,
                edits_made=1,
            )
            m.save()

        loaded = json.loads(metrics_path.read_text())
        editor = loaded["summary"]["agents"]["editor_agent"]
        assert editor["total_runs"] == 2
        assert editor["avg_gate_pass_rate"] == round((60 + 100) / 2, 1)
        # Only 2 data points: first half mean=60, second half=100, diff=40 → improving
        assert "improving" in editor["trend"]

    def test_graphics_summary_aggregates_violations(
        self,
        metrics_path: Path,
    ) -> None:
        for v in (0, 1, 2):
            m = AgentMetrics(metrics_file=str(metrics_path))
            m.track_graphics_agent(
                charts_generated=1,
                visual_qa_passed=1,
                zone_violations=v,
                regenerations=0,
            )
            m.save()

        loaded = json.loads(metrics_path.read_text())
        graphics = loaded["summary"]["agents"]["graphics_agent"]
        assert graphics["total_runs"] == 3
        assert graphics["avg_qa_pass_rate"] == 100.0
        assert graphics["avg_violations"] == round((0 + 1 + 2) / 3, 1)


# ═══════════════════════════════════════════════════════════════════════════
# _calculate_trend
# ═══════════════════════════════════════════════════════════════════════════


class TestCalculateTrend:
    def test_stable_when_fewer_than_two_values(self, metrics: AgentMetrics) -> None:
        assert metrics._calculate_trend([]) == "stable"
        assert metrics._calculate_trend([42.0]) == "stable"

    def test_improving_when_second_half_higher(self, metrics: AgentMetrics) -> None:
        result = metrics._calculate_trend([10.0, 20.0, 80.0, 90.0])
        assert "improving" in result

    def test_declining_when_second_half_lower(self, metrics: AgentMetrics) -> None:
        result = metrics._calculate_trend([90.0, 80.0, 20.0, 10.0])
        assert "declining" in result

    def test_stable_when_diff_within_threshold(self, metrics: AgentMetrics) -> None:
        # mean(50,52) vs mean(53,55) → diff = 3, below ±5 threshold
        result = metrics._calculate_trend([50.0, 52.0, 53.0, 55.0])
        assert "stable" in result


# ═══════════════════════════════════════════════════════════════════════════
# get_latest_run and get_agent_history
# ═══════════════════════════════════════════════════════════════════════════


class TestQueries:
    def test_get_latest_run_returns_none_when_empty(
        self,
        metrics: AgentMetrics,
    ) -> None:
        assert metrics.get_latest_run() is None

    def test_get_latest_run_returns_most_recent(
        self,
        metrics_path: Path,
    ) -> None:
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_research_agent(data_points=10, verified=5, unverified=5)
        m.save()

        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_research_agent(data_points=10, verified=10, unverified=0)
        m.save()

        latest = m.get_latest_run()
        assert latest is not None
        assert latest["agents"]["research_agent"]["verified"] == 10

    def test_get_agent_history_returns_recent_runs_reverse_chronological(
        self,
        metrics_path: Path,
    ) -> None:
        for verified in (5, 7, 9):
            m = AgentMetrics(metrics_file=str(metrics_path))
            m.track_research_agent(
                data_points=10,
                verified=verified,
                unverified=10 - verified,
            )
            m.save()

        history = m.get_agent_history("research_agent", last_n=2)
        assert len(history) == 2
        # Reverse chronological: most recent first
        assert history[0]["verified"] == 9
        assert history[1]["verified"] == 7
        # timestamp injected from run record
        assert "timestamp" in history[0]

    def test_get_agent_history_skips_runs_missing_agent(
        self,
        metrics_path: Path,
    ) -> None:
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_research_agent(data_points=10, verified=9, unverified=1)
        m.save()

        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=True,
            regenerations=0,
        )
        m.save()

        history = m.get_agent_history("research_agent", last_n=10)
        assert len(history) == 1
        assert history[0]["verified"] == 9

    def test_get_agent_history_empty_when_agent_never_tracked(
        self,
        metrics: AgentMetrics,
    ) -> None:
        assert metrics.get_agent_history("research_agent") == []


# ═══════════════════════════════════════════════════════════════════════════
# export_summary_report
# ═══════════════════════════════════════════════════════════════════════════


class TestExportSummaryReport:
    def test_empty_report_contains_header_and_zero_runs(
        self,
        metrics: AgentMetrics,
    ) -> None:
        report = metrics.export_summary_report()
        assert "AGENT PERFORMANCE SUMMARY" in report
        assert "Total Runs: 0" in report

    def test_report_includes_each_agent_section(
        self,
        metrics_path: Path,
    ) -> None:
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_research_agent(data_points=10, verified=9, unverified=1)
        m.track_writer_agent(
            word_count=900,
            banned_phrases=0,
            validation_passed=True,
            regenerations=0,
        )
        m.track_editor_agent(gates_passed=5, gates_failed=0, edits_made=5)
        m.track_graphics_agent(
            charts_generated=1,
            visual_qa_passed=1,
            zone_violations=0,
            regenerations=0,
        )
        m.save()

        report = m.export_summary_report()
        assert "Research Agent" in report
        assert "Writer Agent" in report
        assert "Editor Agent" in report
        assert "Graphics Agent" in report
        assert "Quality Score" in report
        assert "Average Verification Rate" in report
        assert "Clean Draft Rate" in report
        assert "Average Gate Pass Rate" in report
        assert "Average Visual QA Pass Rate" in report

    def test_report_skips_agents_with_empty_summary(
        self,
        metrics_path: Path,
    ) -> None:
        m = AgentMetrics(metrics_file=str(metrics_path))
        m.track_research_agent(data_points=10, verified=9, unverified=1)
        m.save()

        report = m.export_summary_report()
        assert "Research Agent" in report
        # Writer/editor/graphics never tracked → their summaries remain empty {}
        assert "Writer Agent" not in report
        assert "Editor Agent" not in report
        assert "Graphics Agent" not in report
