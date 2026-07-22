#!/usr/bin/env python3
"""Tests for destructive change guard."""

from unittest.mock import patch

from scripts.destructive_change_guard import (
    CRITICAL_FILES,
    MAX_DELETION_PCT,
    get_intentional_rewrites,
)


class TestConfiguration:
    def test_critical_files_list_not_empty(self) -> None:
        assert len(CRITICAL_FILES) > 0

    def test_flow_py_is_critical(self) -> None:
        assert "src/economist_agents/flow.py" in CRITICAL_FILES

    def test_stage3_agent_sdk_runner_is_critical(self) -> None:
        assert "src/agent_sdk/stage3_runner.py" in CRITICAL_FILES

    def test_stage4_agent_sdk_runner_is_critical(self) -> None:
        assert "src/agent_sdk/stage4_runner.py" in CRITICAL_FILES

    def test_deleted_crewai_crews_are_not_critical(self) -> None:
        assert "src/crews/stage3_crew.py" not in CRITICAL_FILES
        assert "src/crews/stage4_crew.py" not in CRITICAL_FILES

    def test_max_deletion_is_50_pct(self) -> None:
        assert MAX_DELETION_PCT == 50

    def test_retired_ci_workflows_are_not_critical(self) -> None:
        # GitHub Actions was retired (content-pipeline.yml in B-009, ci.yml in
        # B-011); the guard protects core source, not CI config we intentionally
        # removed, so these must NOT be in the protected list.
        assert ".github/workflows/ci.yml" not in CRITICAL_FILES
        assert ".github/workflows/content-pipeline.yml" not in CRITICAL_FILES


class TestIntentionalRewriteBypass:
    def test_returns_empty_when_no_pr_context(self) -> None:
        with patch.dict(
            "os.environ",
            {"GITHUB_REF": "", "PR_NUMBER": "", "INTENTIONAL_REWRITE": ""},
            clear=False,
        ):
            assert get_intentional_rewrites() == set()

    def test_local_allowlist_via_env_var(self) -> None:
        # B-011: paywall-free local allowlist for `make ci-local` — comma/space
        # separated, works with no PR context and no gh.
        with patch.dict(
            "os.environ",
            {
                "GITHUB_REF": "",
                "PR_NUMBER": "",
                "INTENTIONAL_REWRITE": "src/a.py, scripts/b.py",
            },
            clear=False,
        ):
            assert get_intentional_rewrites() == {"src/a.py", "scripts/b.py"}

    def test_parses_marker_lines_from_pr_body(self) -> None:
        body = (
            "## Summary\nWhatever.\n\n"
            "Intentional rewrite: src/agent_sdk/stage3_runner.py\n"
            "Intentional rewrite: src/economist_agents/flow.py\n"
            "Some other text.\n"
        )
        with (
            patch.dict("os.environ", {"PR_NUMBER": "999"}, clear=False),
            patch("scripts.destructive_change_guard.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = body
            allowlist = get_intentional_rewrites()
        assert "src/agent_sdk/stage3_runner.py" in allowlist
        assert "src/economist_agents/flow.py" in allowlist

    def test_returns_empty_when_gh_call_fails(self) -> None:
        with (
            patch.dict("os.environ", {"PR_NUMBER": "999"}, clear=False),
            patch("scripts.destructive_change_guard.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            assert get_intentional_rewrites() == set()

    def test_extracts_pr_number_from_github_ref(self) -> None:
        body = "Intentional rewrite: src/agent_sdk/stage4_runner.py"
        env = {"GITHUB_REF": "refs/pull/315/merge"}
        with (
            patch.dict("os.environ", env, clear=False),
            patch("scripts.destructive_change_guard.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = body
            allowlist = get_intentional_rewrites()
        assert "src/agent_sdk/stage4_runner.py" in allowlist
