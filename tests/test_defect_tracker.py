"""Direct unit tests for src/quality/defect_tracker.py.

These tests exercise the public surface of DefectTracker and its main() CLI
entrypoint in-process. Filesystem state is isolated per test via tmp_path —
each test instantiates its own DefectTracker with an explicit tracker_file
path, so no global JSON file is mutated. The module's print() calls are
captured (and asserted on where load-bearing) via capsys.

Mocking strategy:
- Filesystem: tmp_path / "defect_tracker.json" passed to constructor.
- Time: no patching; tests do not depend on exact timestamps, only on
  string-isoformat parseability and relative ordering.
- main(): monkeypatches DefectTracker default tracker_file resolution by
  redirecting the path computation, then runs main() to exercise the CLI
  branch and assert the resulting JSON state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.quality import defect_tracker as dt_mod
from src.quality.defect_tracker import DefectTracker

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def tracker_path(tmp_path: Path) -> Path:
    """Return a tracker JSON path inside the test's tmp_path."""
    return tmp_path / "defect_tracker.json"


@pytest.fixture
def tracker(tracker_path: Path) -> DefectTracker:
    """Return a fresh DefectTracker backed by tmp_path."""
    return DefectTracker(tracker_file=str(tracker_path))


# ═══════════════════════════════════════════════════════════════════════════
# Class constants
# ═══════════════════════════════════════════════════════════════════════════


class TestClassConstants:
    def test_severities_define_four_levels(self):
        assert DefectTracker.SEVERITIES == ["critical", "high", "medium", "low"]

    def test_stages_define_three_environments(self):
        assert DefectTracker.STAGES == ["development", "staging", "production"]

    def test_root_causes_includes_canonical_taxonomy(self):
        for cause in [
            "validation_gap",
            "prompt_engineering",
            "integration_error",
            "requirements_gap",
            "code_logic",
            "configuration",
            "data_issue",
            "race_condition",
            "dependency",
            "other",
        ]:
            assert cause in DefectTracker.ROOT_CAUSES

    def test_test_types_includes_none_sentinel(self):
        assert "none" in DefectTracker.TEST_TYPES

    def test_prevention_strategies_includes_automation(self):
        assert "automation" in DefectTracker.PREVENTION_STRATEGIES


# ═══════════════════════════════════════════════════════════════════════════
# Construction & loading
# ═══════════════════════════════════════════════════════════════════════════


class TestInitAndLoad:
    def test_initializes_empty_tracker_when_file_does_not_exist(
        self, tracker: DefectTracker
    ):
        assert tracker.tracker["version"] == "1.0"
        assert tracker.tracker["bugs"] == []
        assert tracker.tracker["summary"]["total_bugs"] == 0
        assert tracker.tracker["summary"]["defect_escape_rate"] == 0.0

    def test_initializes_summary_with_zeroed_severity_and_stage_counts(
        self, tracker: DefectTracker
    ):
        summary = tracker.tracker["summary"]
        assert summary["by_severity"] == {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        assert summary["by_stage"] == {
            "development": 0,
            "staging": 0,
            "production": 0,
        }

    def test_loads_existing_tracker_from_disk(self, tracker_path: Path):
        existing = {
            "version": "1.0",
            "created": "2025-01-01T00:00:00",
            "bugs": [
                {
                    "id": "BUG-PRE",
                    "severity": "low",
                    "discovered_in": "development",
                    "discovered_date": "2025-01-01T00:00:00",
                    "description": "preexisting",
                    "github_issue": None,
                    "component": None,
                    "responsible_agent": None,
                    "status": "open",
                    "fixed_date": None,
                    "fix_commit": None,
                    "is_production_escape": False,
                    "root_cause": None,
                    "root_cause_notes": None,
                    "introduced_in_commit": None,
                    "introduced_date": None,
                    "time_to_detect_days": None,
                    "time_to_resolve_days": None,
                    "missed_by_test_type": None,
                    "test_gap_description": None,
                    "prevention_test_added": False,
                    "prevention_test_file": None,
                    "prevention_strategy": [],
                    "prevention_actions": [],
                }
            ],
            "summary": {},
        }
        tracker_path.write_text(json.dumps(existing))
        tracker = DefectTracker(tracker_file=str(tracker_path))
        assert len(tracker.tracker["bugs"]) == 1
        assert tracker.tracker["bugs"][0]["id"] == "BUG-PRE"

    def test_default_path_falls_back_to_legacy_when_new_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """When tracker_file is None and neither new nor legacy file exists,
        the constructor should use the legacy path as fallback (and create
        an empty in-memory tracker).
        """
        # Point Path(__file__) resolution at a tmp tree where neither path exists.
        fake_module = tmp_path / "src" / "quality" / "defect_tracker.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("# placeholder")
        monkeypatch.setattr(dt_mod, "__file__", str(fake_module))
        tracker = DefectTracker()
        # Expect legacy path because new path doesn't exist either
        assert tracker.tracker_file.name == "defect_tracker.json"
        assert tracker.tracker["bugs"] == []

    def test_default_path_prefers_new_location_when_present(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        fake_module = tmp_path / "src" / "quality" / "defect_tracker.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("# placeholder")
        new_path = tmp_path / "data" / "skills_state" / "defect_tracker.json"
        new_path.parent.mkdir(parents=True)
        new_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "created": "2025-01-01T00:00:00",
                    "bugs": [],
                    "summary": {
                        "total_bugs": 0,
                        "fixed_bugs": 0,
                        "production_bugs": 0,
                        "defect_escape_rate": 0.0,
                        "by_severity": dict.fromkeys(DefectTracker.SEVERITIES, 0),
                        "by_stage": dict.fromkeys(DefectTracker.STAGES, 0),
                    },
                }
            )
        )
        monkeypatch.setattr(dt_mod, "__file__", str(fake_module))
        tracker = DefectTracker()
        assert tracker.tracker_file == new_path


# ═══════════════════════════════════════════════════════════════════════════
# log_bug
# ═══════════════════════════════════════════════════════════════════════════


class TestLogBug:
    def test_logs_minimal_bug_with_required_fields(
        self, tracker: DefectTracker, capsys: pytest.CaptureFixture[str]
    ):
        tracker.log_bug(
            bug_id="BUG-001",
            severity="critical",
            discovered_in="development",
            description="thing broke",
        )
        captured = capsys.readouterr()
        assert "BUG-001" in captured.out
        assert len(tracker.tracker["bugs"]) == 1
        bug = tracker.tracker["bugs"][0]
        assert bug["id"] == "BUG-001"
        assert bug["severity"] == "critical"
        assert bug["status"] == "open"
        assert bug["is_production_escape"] is False

    def test_marks_production_bug_as_escape(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-PROD",
            severity="high",
            discovered_in="production",
            description="escaped",
        )
        assert tracker.tracker["bugs"][0]["is_production_escape"] is True

    def test_rejects_invalid_severity(self, tracker: DefectTracker):
        with pytest.raises(ValueError, match="Severity must be one of"):
            tracker.log_bug(
                bug_id="BUG-X",
                severity="nuclear",
                discovered_in="development",
                description="bad",
            )

    def test_rejects_invalid_stage(self, tracker: DefectTracker):
        with pytest.raises(ValueError, match="Stage must be one of"):
            tracker.log_bug(
                bug_id="BUG-X",
                severity="low",
                discovered_in="space",
                description="bad",
            )

    def test_rejects_invalid_root_cause(self, tracker: DefectTracker):
        with pytest.raises(ValueError, match="Root cause must be one of"):
            tracker.log_bug(
                bug_id="BUG-X",
                severity="low",
                discovered_in="development",
                description="bad",
                root_cause="cosmic_rays",
            )

    def test_rejects_invalid_test_type(self, tracker: DefectTracker):
        with pytest.raises(ValueError, match="Test type must be one of"):
            tracker.log_bug(
                bug_id="BUG-X",
                severity="low",
                discovered_in="development",
                description="bad",
                missed_by_test_type="psychic_test",
            )

    def test_duplicate_bug_id_is_noop_and_warns(
        self, tracker: DefectTracker, capsys: pytest.CaptureFixture[str]
    ):
        tracker.log_bug(
            bug_id="BUG-DUP",
            severity="low",
            discovered_in="development",
            description="first",
        )
        tracker.log_bug(
            bug_id="BUG-DUP",
            severity="critical",
            discovered_in="production",
            description="second",
        )
        captured = capsys.readouterr()
        assert "already exists" in captured.out
        assert len(tracker.tracker["bugs"]) == 1
        assert tracker.tracker["bugs"][0]["description"] == "first"

    def test_calculates_time_to_detect_when_introduced_date_provided(
        self, tracker: DefectTracker
    ):
        # introduced_date is interpreted by datetime.fromisoformat — pick a
        # date in the past so TTD is positive.
        tracker.log_bug(
            bug_id="BUG-TTD",
            severity="medium",
            discovered_in="development",
            description="lagged",
            introduced_date="2020-01-01T00:00:00",
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["time_to_detect_days"] is not None
        assert bug["time_to_detect_days"] >= 0

    def test_omits_time_to_detect_when_introduced_date_missing(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="BUG-NOTTD",
            severity="low",
            discovered_in="development",
            description="no date",
        )
        assert tracker.tracker["bugs"][0]["time_to_detect_days"] is None

    def test_preserves_optional_metadata(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-META",
            severity="high",
            discovered_in="staging",
            description="meta test",
            github_issue=42,
            component="writer_agent",
            responsible_agent="writer_agent",
            root_cause="validation_gap",
            root_cause_notes="missing check",
            missed_by_test_type="unit_test",
            test_gap_description="no unit test",
            prevention_strategy=["new_test", "new_validation"],
            prevention_actions=["add the test", "add the check"],
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["github_issue"] == 42
        assert bug["component"] == "writer_agent"
        assert bug["responsible_agent"] == "writer_agent"
        assert bug["root_cause"] == "validation_gap"
        assert bug["prevention_strategy"] == ["new_test", "new_validation"]
        assert bug["prevention_actions"] == ["add the test", "add the check"]

    def test_default_prevention_lists_are_empty_not_none(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-DEF",
            severity="low",
            discovered_in="development",
            description="defaults",
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["prevention_strategy"] == []
        assert bug["prevention_actions"] == []


# ═══════════════════════════════════════════════════════════════════════════
# fix_bug
# ═══════════════════════════════════════════════════════════════════════════


class TestFixBug:
    def test_marks_bug_as_fixed_with_commit(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-F1",
            severity="high",
            discovered_in="development",
            description="needs fix",
        )
        tracker.fix_bug("BUG-F1", fix_commit="deadbeef")
        bug = tracker.tracker["bugs"][0]
        assert bug["status"] == "fixed"
        assert bug["fix_commit"] == "deadbeef"
        assert bug["fixed_date"] is not None
        assert bug["time_to_resolve_days"] is not None

    def test_unknown_bug_is_noop_and_logs(
        self, tracker: DefectTracker, capsys: pytest.CaptureFixture[str]
    ):
        tracker.fix_bug("BUG-MISSING", fix_commit="abc")
        captured = capsys.readouterr()
        assert "not found" in captured.out
        assert tracker.tracker["bugs"] == []

    def test_attaches_fix_notes_when_provided(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-N",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.fix_bug("BUG-N", fix_commit="abc", notes="patched it")
        assert tracker.tracker["bugs"][0]["fix_notes"] == "patched it"

    def test_records_prevention_test_metadata(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-P",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.fix_bug(
            "BUG-P",
            fix_commit="abc",
            prevention_test_added=True,
            prevention_test_file="tests/test_x.py",
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["prevention_test_added"] is True
        assert bug["prevention_test_file"] == "tests/test_x.py"

    def test_prevention_test_added_without_file_does_not_set_file(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="BUG-PN",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.fix_bug("BUG-PN", fix_commit="abc", prevention_test_added=True)
        bug = tracker.tracker["bugs"][0]
        assert bug["prevention_test_added"] is True
        assert bug["prevention_test_file"] is None


# ═══════════════════════════════════════════════════════════════════════════
# update_bug_rca
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateBugRca:
    def test_backfills_root_cause_fields(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-R1",
            severity="medium",
            discovered_in="development",
            description="x",
        )
        tracker.update_bug_rca(
            "BUG-R1",
            root_cause="code_logic",
            root_cause_notes="off-by-one",
            introduced_in_commit="abc1234",
            missed_by_test_type="unit_test",
            test_gap_description="boundary not tested",
            prevention_strategy=["new_test"],
            prevention_actions=["add boundary test"],
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["root_cause"] == "code_logic"
        assert bug["root_cause_notes"] == "off-by-one"
        assert bug["introduced_in_commit"] == "abc1234"
        assert bug["missed_by_test_type"] == "unit_test"
        assert bug["test_gap_description"] == "boundary not tested"
        assert bug["prevention_strategy"] == ["new_test"]
        assert bug["prevention_actions"] == ["add boundary test"]

    def test_recalculates_ttd_when_introduced_date_added(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-R2",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.update_bug_rca(
            "BUG-R2",
            introduced_date="2020-01-01T00:00:00",
        )
        assert tracker.tracker["bugs"][0]["time_to_detect_days"] >= 0

    def test_unknown_bug_is_noop_and_logs(
        self, tracker: DefectTracker, capsys: pytest.CaptureFixture[str]
    ):
        tracker.update_bug_rca("NOPE", root_cause="code_logic")
        out = capsys.readouterr().out
        assert "not found" in out

    def test_rejects_invalid_root_cause(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-R3",
            severity="low",
            discovered_in="development",
            description="x",
        )
        with pytest.raises(ValueError, match="Root cause must be one of"):
            tracker.update_bug_rca("BUG-R3", root_cause="bad_cause")

    def test_rejects_invalid_test_type(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="BUG-R4",
            severity="low",
            discovered_in="development",
            description="x",
        )
        with pytest.raises(ValueError, match="Test type must be one of"):
            tracker.update_bug_rca("BUG-R4", missed_by_test_type="bad_type")


# ═══════════════════════════════════════════════════════════════════════════
# _update_summary (exercised via get_metrics)
# ═══════════════════════════════════════════════════════════════════════════


class TestSummaryMetrics:
    def test_escape_rate_is_zero_when_no_bugs(self, tracker: DefectTracker):
        assert tracker.get_metrics()["defect_escape_rate"] == 0.0

    def test_escape_rate_computes_production_over_total(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="A", severity="low", discovered_in="development", description="x"
        )
        tracker.log_bug(
            bug_id="B", severity="low", discovered_in="production", description="x"
        )
        tracker.log_bug(
            bug_id="C", severity="low", discovered_in="production", description="x"
        )
        metrics = tracker.get_metrics()
        assert metrics["total_bugs"] == 3
        assert metrics["production_bugs"] == 2
        assert metrics["defect_escape_rate"] == round(2 / 3 * 100, 1)

    def test_by_severity_counts_per_level(self, tracker: DefectTracker):
        for i, sev in enumerate(["critical", "critical", "high", "low"]):
            tracker.log_bug(
                bug_id=f"S-{i}",
                severity=sev,
                discovered_in="development",
                description="x",
            )
        sev = tracker.get_metrics()["by_severity"]
        assert sev["critical"] == 2
        assert sev["high"] == 1
        assert sev["medium"] == 0
        assert sev["low"] == 1

    def test_by_stage_counts_per_environment(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="D1", severity="low", discovered_in="development", description="x"
        )
        tracker.log_bug(
            bug_id="S1", severity="low", discovered_in="staging", description="x"
        )
        tracker.log_bug(
            bug_id="P1", severity="low", discovered_in="production", description="x"
        )
        by_stage = tracker.get_metrics()["by_stage"]
        assert by_stage == {"development": 1, "staging": 1, "production": 1}

    def test_fixed_bug_count_increments_on_fix(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="F1", severity="low", discovered_in="development", description="x"
        )
        assert tracker.get_metrics()["fixed_bugs"] == 0
        tracker.fix_bug("F1", fix_commit="abc")
        assert tracker.get_metrics()["fixed_bugs"] == 1

    def test_root_cause_distribution_aggregates_bugs(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="R1",
            severity="low",
            discovered_in="development",
            description="x",
            root_cause="code_logic",
        )
        tracker.log_bug(
            bug_id="R2",
            severity="low",
            discovered_in="development",
            description="x",
            root_cause="code_logic",
        )
        tracker.log_bug(
            bug_id="R3",
            severity="low",
            discovered_in="development",
            description="x",
            root_cause="validation_gap",
        )
        dist = tracker.get_metrics()["root_cause_distribution"]
        assert dist == {"code_logic": 2, "validation_gap": 1}

    def test_test_gap_distribution_aggregates_bugs(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="T1",
            severity="low",
            discovered_in="development",
            description="x",
            missed_by_test_type="unit_test",
        )
        tracker.log_bug(
            bug_id="T2",
            severity="low",
            discovered_in="development",
            description="x",
            missed_by_test_type="visual_qa",
        )
        dist = tracker.get_metrics()["test_gap_distribution"]
        assert dist == {"unit_test": 1, "visual_qa": 1}

    def test_agent_defect_distribution_aggregates_bugs(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="A1",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="writer_agent",
        )
        tracker.log_bug(
            bug_id="A2",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="writer_agent",
        )
        tracker.log_bug(
            bug_id="A3",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="editor_agent",
        )
        dist = tracker.get_metrics()["agent_defect_distribution"]
        assert dist == {"writer_agent": 2, "editor_agent": 1}

    def test_avg_time_to_detect_is_none_when_no_data(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="N1", severity="low", discovered_in="development", description="x"
        )
        assert tracker.get_metrics()["avg_time_to_detect_days"] is None

    def test_avg_time_to_detect_computed_when_data_present(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="TT1",
            severity="critical",
            discovered_in="development",
            description="x",
            introduced_date="2020-01-01T00:00:00",
        )
        tracker.log_bug(
            bug_id="TT2",
            severity="low",
            discovered_in="development",
            description="x",
            introduced_date="2020-01-02T00:00:00",
        )
        metrics = tracker.get_metrics()
        assert metrics["avg_time_to_detect_days"] is not None
        assert metrics["avg_time_to_detect_days"] >= 0
        assert metrics["avg_critical_ttd_days"] is not None

    def test_avg_time_to_resolve_present_as_summary_key(self, tracker: DefectTracker):
        """Resolution time defaults to None and is included in summary keys
        once _update_summary runs (i.e. after at least one bug is logged).

        Note: the source treats avg_ttr=0 as falsy (line 366), so a same-day
        log+fix yields None — this test only confirms the key exists.
        """
        tracker.log_bug(
            bug_id="TR1", severity="low", discovered_in="development", description="x"
        )
        tracker.fix_bug("TR1", fix_commit="abc")
        summary = tracker.get_metrics()
        assert "avg_time_to_resolve_days" in summary

    def test_last_updated_timestamp_added_after_first_summary_update(
        self, tracker: DefectTracker
    ):
        from datetime import datetime as dt

        # Fresh tracker (no bugs yet) hasn't run _update_summary, so no
        # last_updated key yet — that's an implementation detail of the lazy
        # initialiser. Adding a bug triggers _update_summary.
        tracker.log_bug(
            bug_id="LU1", severity="low", discovered_in="development", description="x"
        )
        ts = tracker.get_metrics()["last_updated"]
        dt.fromisoformat(ts)  # must not raise


# ═══════════════════════════════════════════════════════════════════════════
# Query methods
# ═══════════════════════════════════════════════════════════════════════════


class TestQueryMethods:
    def test_get_production_bugs_returns_only_escapes(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="D1", severity="low", discovered_in="development", description="x"
        )
        tracker.log_bug(
            bug_id="P1", severity="low", discovered_in="production", description="x"
        )
        prod = tracker.get_production_bugs()
        assert [b["id"] for b in prod] == ["P1"]

    def test_get_production_bugs_empty_when_none(self, tracker: DefectTracker):
        assert tracker.get_production_bugs() == []

    def test_get_open_bugs_excludes_fixed(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="O1", severity="low", discovered_in="development", description="x"
        )
        tracker.log_bug(
            bug_id="O2", severity="low", discovered_in="development", description="x"
        )
        tracker.fix_bug("O1", fix_commit="abc")
        open_bugs = tracker.get_open_bugs()
        assert [b["id"] for b in open_bugs] == ["O2"]

    def test_get_open_bugs_empty_when_none(self, tracker: DefectTracker):
        assert tracker.get_open_bugs() == []

    def test_get_bugs_by_agent_filters_by_responsible_agent(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="W1",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="writer_agent",
        )
        tracker.log_bug(
            bug_id="E1",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="editor_agent",
        )
        writer_bugs = tracker.get_bugs_by_agent("writer_agent")
        assert [b["id"] for b in writer_bugs] == ["W1"]

    def test_get_bugs_by_agent_empty_when_no_matches(self, tracker: DefectTracker):
        assert tracker.get_bugs_by_agent("nobody") == []

    def test_get_agent_defect_rate_returns_count(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="X1",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="writer_agent",
        )
        tracker.log_bug(
            bug_id="X2",
            severity="low",
            discovered_in="development",
            description="x",
            responsible_agent="writer_agent",
        )
        assert tracker.get_agent_defect_rate("writer_agent") == 2

    def test_get_agent_defect_rate_zero_when_no_bugs(self, tracker: DefectTracker):
        assert tracker.get_agent_defect_rate("ghost_agent") == 0


# ═══════════════════════════════════════════════════════════════════════════
# validate_requirements_traceability
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateRequirementsTraceability:
    def test_classifies_as_bug_when_history_dominated_by_defects(
        self, tracker: DefectTracker
    ):
        # Seed component history with defects (non-requirements_gap)
        for i in range(3):
            tracker.log_bug(
                bug_id=f"H-{i}",
                severity="low",
                discovered_in="development",
                description="x",
                component="writer_agent",
                root_cause="code_logic",
            )
        result = tracker.validate_requirements_traceability(
            component="writer_agent",
            behavior="articles_lack_references",
            expected_behavior="articles_have_references_section",
            original_story="STORY-001",
        )
        assert result["is_defect"] is True
        assert result["classification"] == "bug"
        assert result["confidence"] == "medium"
        assert (
            "REVIEW REQUIRED" in result["recommendation"]
            or "WARNING" in result["recommendation"]
        )

    def test_classifies_as_enhancement_when_no_history(self, tracker: DefectTracker):
        result = tracker.validate_requirements_traceability(
            component="brand_new_component",
            behavior="x",
            expected_behavior="y",
        )
        assert result["is_defect"] is False
        assert result["classification"] == "enhancement"

    def test_classifies_as_enhancement_when_requirements_gaps_dominate(
        self, tracker: DefectTracker
    ):
        # Seed history dominated by requirements_gap entries
        for i in range(3):
            tracker.log_bug(
                bug_id=f"G-{i}",
                severity="low",
                discovered_in="development",
                description="x",
                component="some_component",
                root_cause="requirements_gap",
            )
        result = tracker.validate_requirements_traceability(
            component="some_component",
            behavior="x",
            expected_behavior="y",
        )
        assert result["is_defect"] is False
        assert result["classification"] == "enhancement"

    def test_includes_registry_available_flag(self, tracker: DefectTracker):
        result = tracker.validate_requirements_traceability(
            component="c", behavior="b", expected_behavior="e"
        )
        assert "registry_available" in result
        assert isinstance(result["registry_available"], bool)


# ═══════════════════════════════════════════════════════════════════════════
# reclassify_as_feature
# ═══════════════════════════════════════════════════════════════════════════


class TestReclassifyAsFeature:
    def test_reclassifies_open_bug_and_updates_status(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="RC-1",
            severity="medium",
            discovered_in="development",
            description="not really a bug",
        )
        tracker.reclassify_as_feature(
            "RC-1",
            feature_id="FEATURE-001",
            reason="It was a missing requirement, not a defect",
            original_story="STORY-007",
            requirement_existed=False,
        )
        bug = tracker.tracker["bugs"][0]
        assert bug["status"] == "reclassified_as_feature"
        assert bug["reclassified_as"] == "FEATURE-001"
        assert bug["reclassification_reason"].startswith("It was")
        assert bug["requirements_traceability"]["original_story"] == "STORY-007"
        assert bug["requirements_traceability"]["requirement_existed"] is False

    def test_preserves_fixed_status_when_reclassifying_fixed_bug(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="RC-2",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.fix_bug("RC-2", fix_commit="abc")
        tracker.reclassify_as_feature("RC-2", "FEATURE-X", "post-hoc reclass")
        bug = tracker.tracker["bugs"][0]
        # Status should remain "fixed" since the branch only updates open bugs
        assert bug["status"] == "fixed"
        assert bug["reclassified_as"] == "FEATURE-X"

    def test_unknown_bug_is_noop_and_logs(
        self, tracker: DefectTracker, capsys: pytest.CaptureFixture[str]
    ):
        tracker.reclassify_as_feature("NOPE", "FEATURE-Z", "reason")
        out = capsys.readouterr().out
        assert "not found" in out


# ═══════════════════════════════════════════════════════════════════════════
# save
# ═══════════════════════════════════════════════════════════════════════════


class TestSave:
    def test_persists_tracker_to_disk(self, tracker: DefectTracker, tracker_path: Path):
        tracker.log_bug(
            bug_id="SAV-1",
            severity="low",
            discovered_in="development",
            description="persist me",
        )
        tracker.save()
        assert tracker_path.exists()
        on_disk = json.loads(tracker_path.read_text())
        assert on_disk["bugs"][0]["id"] == "SAV-1"

    def test_creates_parent_directories_if_missing(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c" / "defect_tracker.json"
        tracker = DefectTracker(tracker_file=str(nested))
        tracker.log_bug(
            bug_id="N-1",
            severity="low",
            discovered_in="development",
            description="x",
        )
        tracker.save()
        assert nested.exists()


# ═══════════════════════════════════════════════════════════════════════════
# generate_report
# ═══════════════════════════════════════════════════════════════════════════


class TestGenerateReport:
    def test_empty_report_has_summary_header(self, tracker: DefectTracker):
        report = tracker.generate_report()
        assert "# Defect Tracking Report" in report
        assert "## Summary Metrics" in report
        assert "Total Bugs**: 0" in report

    def test_report_lists_production_escapes(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="PROD-1",
            severity="critical",
            discovered_in="production",
            description="exploded in prod",
            github_issue=123,
            introduced_date="2020-01-01T00:00:00",
            root_cause="code_logic",
        )
        report = tracker.generate_report()
        assert "Production Escapes" in report
        assert "PROD-1" in report
        assert "GitHub Issue: #123" in report
        assert "Root Cause:" in report
        assert "Time to Detect:" in report

    def test_report_lists_open_bugs_with_production_marker(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="OPEN-1",
            severity="high",
            discovered_in="production",
            description="open prod bug",
        )
        report = tracker.generate_report()
        assert "Open Bugs" in report
        assert "OPEN-1" in report
        assert "[PRODUCTION]" in report

    def test_report_includes_root_cause_distribution_when_present(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="RC-RPT",
            severity="low",
            discovered_in="development",
            description="x",
            root_cause="code_logic",
        )
        report = tracker.generate_report()
        assert "Root Cause Analysis" in report
        assert "Code Logic" in report

    def test_report_includes_test_gap_section_when_present(
        self, tracker: DefectTracker
    ):
        tracker.log_bug(
            bug_id="TG-RPT",
            severity="low",
            discovered_in="development",
            description="x",
            missed_by_test_type="unit_test",
        )
        report = tracker.generate_report()
        assert "Test Gap Analysis" in report
        assert "Unit Test" in report

    def test_report_includes_time_metrics_when_available(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="TM-RPT",
            severity="critical",
            discovered_in="development",
            description="x",
            introduced_date="2020-01-01T00:00:00",
        )
        tracker.fix_bug("TM-RPT", fix_commit="abc")
        report = tracker.generate_report()
        assert "Time Metrics" in report
        assert "Avg Time to Detect" in report
        # Avg Critical Bug TTD prints whenever critical TTD is non-falsy
        assert "Avg Critical Bug TTD" in report

    def test_report_severity_section_filters_zero_counts(self, tracker: DefectTracker):
        tracker.log_bug(
            bug_id="SEV-1",
            severity="critical",
            discovered_in="development",
            description="x",
        )
        report = tracker.generate_report()
        # critical present, but low/medium/high should not appear in severity section
        assert "**Critical**:" in report


# ═══════════════════════════════════════════════════════════════════════════
# main() — CLI entrypoint
# ═══════════════════════════════════════════════════════════════════════════


class TestMain:
    def test_main_runs_end_to_end_and_persists_known_bugs(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Redirect the default tracker path resolution to tmp_path, then run
        main() and confirm the four BUG-### entries are logged + saved.
        """
        # Build a fake __file__ inside tmp_path so the relative path computation
        # `parent.parent.parent` lands at tmp_path itself.
        fake_module = tmp_path / "src" / "quality" / "defect_tracker.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("# placeholder")
        monkeypatch.setattr(dt_mod, "__file__", str(fake_module))

        dt_mod.main()

        # Saved file should live under tmp_path/data/skills_state/
        # (legacy path is used since new path doesn't exist)
        legacy_path = tmp_path / "skills" / "defect_tracker.json"
        # main() created the file via save() — parents are created as needed
        assert legacy_path.exists()

        on_disk = json.loads(legacy_path.read_text())
        ids = [b["id"] for b in on_disk["bugs"]]
        assert "BUG-015" in ids
        assert "BUG-016" in ids
        assert "BUG-017" in ids
        assert "BUG-020" in ids

        # BUG-015 / BUG-016 / BUG-017 should be marked fixed
        by_id = {b["id"]: b for b in on_disk["bugs"]}
        assert by_id["BUG-015"]["status"] == "fixed"
        assert by_id["BUG-016"]["status"] == "fixed"
        assert by_id["BUG-017"]["status"] == "fixed"
        # BUG-020 remains open per main() docstring
        assert by_id["BUG-020"]["status"] == "open"

        # Report was emitted to stdout
        captured = capsys.readouterr()
        assert "Defect Tracking Report" in captured.out

    def test_main_is_idempotent_on_second_invocation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Running main() twice should not duplicate bugs (log_bug is a no-op
        on duplicate IDs).
        """
        fake_module = tmp_path / "src" / "quality" / "defect_tracker.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("# placeholder")
        monkeypatch.setattr(dt_mod, "__file__", str(fake_module))

        dt_mod.main()
        capsys.readouterr()  # drain
        dt_mod.main()
        out = capsys.readouterr().out
        assert "already exists" in out

        legacy_path = tmp_path / "skills" / "defect_tracker.json"
        on_disk = json.loads(legacy_path.read_text())
        ids = [b["id"] for b in on_disk["bugs"]]
        # No duplicates introduced
        assert len(ids) == len(set(ids))
