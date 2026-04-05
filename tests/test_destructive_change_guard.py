#!/usr/bin/env python3
"""Tests for destructive change guard."""

from scripts.destructive_change_guard import CRITICAL_FILES, MAX_DELETION_PCT


class TestConfiguration:
    def test_critical_files_list_not_empty(self) -> None:
        assert len(CRITICAL_FILES) > 0

    def test_flow_py_is_critical(self) -> None:
        assert "src/economist_agents/flow.py" in CRITICAL_FILES

    def test_stage3_is_critical(self) -> None:
        assert "src/crews/stage3_crew.py" in CRITICAL_FILES

    def test_stage4_is_critical(self) -> None:
        assert "src/crews/stage4_crew.py" in CRITICAL_FILES

    def test_max_deletion_is_50_pct(self) -> None:
        assert MAX_DELETION_PCT == 50

    def test_ci_workflow_is_critical(self) -> None:
        assert ".github/workflows/ci.yml" in CRITICAL_FILES
