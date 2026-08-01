#!/usr/bin/env python3
"""Tests for destructive change guard.

`TestItCatchesARealGutting` is this sensor's **proof of teeth** (B-043). Until it
was written, every test in this file checked configuration (is this file on the
critical list?) or the bypass path — nothing gutted a file and asserted the guard
noticed. That is the difference the B-043 baseline measured across the repo:
unit tests answer *does the code work*, efficacy tests answer *does it fire on a
real defect*, and only the second kind would have caught the four inert sensors
found on 2026-08-01.

The proof runs against a real git repository in `tmp_path` rather than mocked
diff stats, deliberately. B-039's third finding was a fix that looked right and
did nothing — `export PATH :=` in the Makefile, confirmed by `make showpath`,
still ran the ambient binary. Mocking `get_diff_stats` would test the arithmetic
while assuming the git plumbing underneath it works, which is the same shape of
assumption. This truncates a real file in a real repo and runs the real guard.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.destructive_change_guard import (
    CRITICAL_FILES,
    MAX_DELETION_PCT,
    check_destructive_changes,
    get_intentional_rewrites,
    main,
)

#: A file on CRITICAL_FILES, so the guard is supposed to protect it.
PROTECTED = "scripts/publication_validator.py"

#: One that is not, so it is the control.
UNPROTECTED = "scripts/spend_report.py"


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


def _git(repo: Path, *args: str) -> None:
    """Run one git command in a fixture repo, raising on failure."""
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo on `main` holding a 100-line copy of each candidate file.

    The guard resolves everything through git in the process's working directory,
    so the fixture chdirs rather than patching. It also clears the PR-context
    environment: an allowlisted file is waved through, and a proof that passes
    because the defect was allowlisted proves nothing.
    """
    for name in (PROTECTED, UNPROTECTED):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(f"line {n}\n" for n in range(100)))

    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "baseline")

    for var in ("GITHUB_REF", "PR_NUMBER", "INTENTIONAL_REWRITE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestItCatchesARealGutting:
    """The mutation the spec names: truncate a file listed as critical to a stub,
    run the guard, assert it blocks."""

    def test_gutting_a_critical_file_is_caught(self, repo: Path) -> None:
        (repo / PROTECTED).write_text("# gutted\n")

        violations = check_destructive_changes()

        assert violations, "a critical file cut from 100 lines to 1 must be blocked"
        assert PROTECTED in violations[0]

    def test_the_violation_reports_the_scale_of_the_loss(self, repo: Path) -> None:
        """A blocked commit has to say what tripped it or it just gets retried."""
        (repo / PROTECTED).write_text("# gutted\n")

        assert "99%" in check_destructive_changes()[0]

    def test_it_exits_non_zero(self, repo: Path) -> None:
        """`make ci-local` reads the exit code, not the return value."""
        (repo / PROTECTED).write_text("# gutted\n")

        with pytest.raises(SystemExit) as exit_info:
            main()

        assert exit_info.value.code == 1


class TestItDoesNotFireOnOrdinaryWork:
    """The other half of the mutation. A guard that blocks everything is
    disabled within a day — the noise-overload failure mode that gets a sensor
    reverted to `stages: [manual]`, which is exactly what B-031 found mypy on."""

    def test_a_targeted_edit_passes(self, repo: Path) -> None:
        lines = (repo / PROTECTED).read_text().splitlines(keepends=True)
        (repo / PROTECTED).write_text("".join(lines[:90]))

        assert check_destructive_changes() == []

    def test_an_untouched_tree_passes(self, repo: Path) -> None:
        assert check_destructive_changes() == []

    def test_it_exits_zero_on_a_clean_tree(self, repo: Path) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main()

        assert exit_info.value.code == 0

    def test_gutting_a_file_that_is_not_critical_passes(self, repo: Path) -> None:
        """The list is the scope. Widening it silently would make the guard a
        general "large diff" alarm, which is a different and much noisier tool."""
        (repo / UNPROTECTED).write_text("# gutted\n")

        assert check_destructive_changes() == []


class TestTheBypassStillWorks:
    """An intentional rewrite is allowed — but only when it is recorded, which is
    the `docs/harness-overrides.md` convention in another form."""

    def test_an_allowlisted_file_is_waved_through(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (repo / PROTECTED).write_text("# gutted\n")
        monkeypatch.setenv("INTENTIONAL_REWRITE", PROTECTED)

        assert check_destructive_changes() == []

    def test_allowlisting_a_different_file_does_not_help(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A blanket bypass would be the `|| true` B-031 deleted."""
        (repo / PROTECTED).write_text("# gutted\n")
        monkeypatch.setenv("INTENTIONAL_REWRITE", UNPROTECTED)

        assert check_destructive_changes()
