"""Tests that `make ci-local` is reproducible (B-039).

ADR-0015 makes `make ci-local` the merge gate — there is no GitHub Actions and `main` is
unprotected — so the gate has to mean the same thing on every machine and in every shell.
It did not: every recipe resolved its tools from ambient ``PATH``, so the gate linted with
an unpinned ruff, could not run without an activated venv, and reported a *missing* mypy
identically to a mypy that ran and found errors.

These tests **execute** the Makefile in a throwaway directory against stub tools. A grep of
the Makefile's text would pass the moment someone wrote the right-looking line; running it
is the only thing that proves which binary actually wins.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
MAKEFILE = REPO_ROOT / "Makefile"

#: A PATH with no venv on it, so anything the gate finds it found ambiently.
BARE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"


def write_stub(path: Path, *, prints: str = "", exit_code: int = 0) -> None:
    """Write an executable shell stub that announces itself and exits as told."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!/bin/sh\n{f'echo {prints}' if prints else ''}\nexit {exit_code}\n"
    )
    path.chmod(0o755)


def run_make(target: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one make target in an isolated directory with no venv on PATH."""
    return subprocess.run(
        ["make", "--no-print-directory", target],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": BARE_PATH},
    )


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """A directory holding only the repo's Makefile."""
    shutil.copy(MAKEFILE, tmp_path / "Makefile")
    return tmp_path


class TestTheGateUsesThePinnedVenv:
    """`requirements-dev.txt` pins `ruff==0.14.10`; ambient ruff was 0.15.9 and formatted
    differently. The pin is meaningless if the gate does not run the pinned binary."""

    def test_a_venv_tool_wins_over_the_ambient_one(self, sandbox: Path) -> None:
        write_stub(sandbox / ".venv" / "bin" / "python")
        write_stub(sandbox / ".venv" / "bin" / "ruff", prints="THE-VENV-RUFF-RAN")

        result = run_make("lint", sandbox)

        assert result.returncode == 0, result.stderr
        assert "THE-VENV-RUFF-RAN" in result.stdout

    def test_the_test_target_also_uses_the_venv(self, sandbox: Path) -> None:
        write_stub(sandbox / ".venv" / "bin" / "python")
        write_stub(sandbox / ".venv" / "bin" / "pytest", prints="THE-VENV-PYTEST-RAN")

        result = run_make("test", sandbox)

        assert "THE-VENV-PYTEST-RAN" in result.stdout


class TestAMissingVenvFailsLoudly:
    """Falling through to ambient tools is how the gate silently changed meaning."""

    def test_ci_local_refuses_to_start_without_a_venv(self, sandbox: Path) -> None:
        result = run_make("ci-local", sandbox)

        assert result.returncode != 0
        assert "venv" in (result.stdout + result.stderr).lower()

    def test_it_fails_before_running_any_check_rather_than_part_way(
        self, sandbox: Path
    ) -> None:
        result = run_make("ci-local", sandbox)

        assert "── ruff format ──" not in result.stdout

    def test_the_message_says_how_to_fix_it(self, sandbox: Path) -> None:
        result = run_make("ci-local", sandbox)

        assert "make install" in result.stdout + result.stderr

    def test_install_creates_the_venv_rather_than_requiring_it(
        self, sandbox: Path
    ) -> None:
        # Chicken-and-egg: `make install` must not require the thing it installs into,
        # or require-venv's instruction would send you to a target that also refuses.
        # Dry-run, so this asserts what install *would* do without installing anything.
        result = subprocess.run(
            ["make", "--no-print-directory", "--dry-run", "install"],
            cwd=sandbox,
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": BARE_PATH},
        )

        assert result.returncode == 0, result.stderr
        assert "python3 -m venv .venv" in result.stdout
        assert "/.venv/bin/pip install" in result.stdout


class TestTheMypyAdvisoryCannotMaskAMissingTool:
    """B-031's complaint: a sensor that cannot tell "I ran and found problems" from
    "I never ran". `(mypy ... || echo advisory)` swallowed exit 127 exactly like exit 1."""

    @pytest.fixture
    def sandbox_with_python(self, sandbox: Path) -> Path:
        write_stub(sandbox / ".venv" / "bin" / "python")
        return sandbox

    def test_clean_mypy_passes(self, sandbox_with_python: Path) -> None:
        write_stub(sandbox_with_python / ".venv" / "bin" / "mypy", exit_code=0)

        result = run_make("mypy-advisory", sandbox_with_python)

        assert result.returncode == 0, result.stderr

    def test_type_errors_stay_advisory(self, sandbox_with_python: Path) -> None:
        write_stub(sandbox_with_python / ".venv" / "bin" / "mypy", exit_code=1)

        result = run_make("mypy-advisory", sandbox_with_python)

        assert result.returncode == 0, result.stderr
        assert "advisory" in result.stdout

    def test_a_mypy_that_could_not_run_fails_the_gate(
        self, sandbox_with_python: Path
    ) -> None:
        # 127 is "command not found"; 2 is a mypy usage/internal error. Neither is
        # "the codebase is known-red", which is the only thing the advisory excuses.
        write_stub(sandbox_with_python / ".venv" / "bin" / "mypy", exit_code=127)

        result = run_make("mypy-advisory", sandbox_with_python)

        assert result.returncode != 0
        assert "advisory" not in result.stdout.replace("mypy (advisory)", "")

    def test_a_mypy_crash_fails_the_gate_too(self, sandbox_with_python: Path) -> None:
        write_stub(sandbox_with_python / ".venv" / "bin" / "mypy", exit_code=2)

        result = run_make("mypy-advisory", sandbox_with_python)

        assert result.returncode != 0
