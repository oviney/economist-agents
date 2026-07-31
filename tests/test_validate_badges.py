"""Tests for the README badge validator (B-036).

BUG-023 was stale badges. The hook that existed to prevent it ran
`scripts/validate_badges.py`, which had been archived to `scripts/archived/` —
and its entry was `bash -c '... || true'`, so it swallowed both the stale-badge
failures *and* the "no such file" error proving it had no implementation. It was
inert twice over, and the badges went stale anyway: two of them pointed at
GitHub Actions workflows that ADR-0015 retired.

This validator is scoped to the two things that actually rot:

1. A workflow badge must reference a workflow file that exists.
2. The Python badge must match `.python-version`.

The archived version also resolved its paths relative to `scripts/`, so it went
looking for `scripts/README.md`. Everything here resolves from the repo root,
and `check_badges` takes an explicit root so the tests can prove it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = REPO_ROOT / "scripts" / "validate_badges.py"
_spec = importlib.util.spec_from_file_location("validate_badges", _SCRIPT)
assert _spec is not None and _spec.loader is not None
validate_badges = importlib.util.module_from_spec(_spec)
sys.modules["validate_badges"] = validate_badges
_spec.loader.exec_module(validate_badges)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A miniature repo: README, .python-version, and a workflows dir."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".python-version").write_text("3.12\n")
    return tmp_path


def _readme(repo: Path, body: str) -> None:
    (repo / "README.md").write_text(body)


class TestWorkflowBadges:
    """A badge for a workflow that does not exist is a lie on the front page."""

    def test_badge_for_an_existing_workflow_passes(self, repo: Path) -> None:
        (repo / ".github" / "workflows" / "docs.yml").write_text("name: docs\n")
        _readme(
            repo,
            "[![Docs](https://github.com/o/e/actions/workflows/docs.yml/badge.svg)](x)\n",
        )

        assert validate_badges.check_badges(repo) == []

    def test_badge_for_a_missing_workflow_fails(self, repo: Path) -> None:
        """The live defect: ci.yml was retired by ADR-0015, the badge stayed."""
        _readme(
            repo,
            "[![CI](https://github.com/o/e/actions/workflows/ci.yml/badge.svg)](x)\n",
        )

        problems = validate_badges.check_badges(repo)

        assert len(problems) == 1
        assert "ci.yml" in problems[0]

    def test_every_missing_workflow_is_reported(self, repo: Path) -> None:
        """Report all of them, not just the first — both badges were stale."""
        _readme(
            repo,
            "[![CI](https://github.com/o/e/actions/workflows/ci.yml/badge.svg)](x)\n"
            "[![QT](https://github.com/o/e/actions/workflows/quality-tests.yml/badge.svg)](x)\n",
        )

        problems = validate_badges.check_badges(repo)

        assert len(problems) == 2

    def test_a_readme_with_no_badges_passes(self, repo: Path) -> None:
        _readme(repo, "# Title\n\nProse only.\n")

        assert validate_badges.check_badges(repo) == []


class TestPythonBadge:
    """The badge must agree with the pin, not with whatever was true once."""

    def test_matching_version_passes(self, repo: Path) -> None:
        _readme(repo, "![Python](https://img.shields.io/badge/Python-3.12-blue)\n")

        assert validate_badges.check_badges(repo) == []

    def test_mismatched_version_fails(self, repo: Path) -> None:
        """The live defect: badge said 3.13, .python-version said 3.12."""
        _readme(repo, "![Python](https://img.shields.io/badge/Python-3.13-blue)\n")

        problems = validate_badges.check_badges(repo)

        assert len(problems) == 1
        assert "3.13" in problems[0]
        assert "3.12" in problems[0]

    def test_missing_python_version_file_is_not_a_crash(self, repo: Path) -> None:
        """Degrade to skipping the check, never to a traceback."""
        (repo / ".python-version").unlink()
        _readme(repo, "![Python](https://img.shields.io/badge/Python-3.13-blue)\n")

        assert validate_badges.check_badges(repo) == []


class TestPathsResolveFromRepoRoot:
    """The archived validator looked for `scripts/README.md`. This one must not."""

    def test_missing_readme_is_reported_not_crashed(self, repo: Path) -> None:
        problems = validate_badges.check_badges(repo)

        assert len(problems) == 1
        assert "README.md" in problems[0]

    def test_module_default_root_is_the_repo_not_scripts(self) -> None:
        assert validate_badges.REPO_ROOT == REPO_ROOT
        assert (validate_badges.REPO_ROOT / "README.md").is_file()


class TestExitCodes:
    """B-031's rule: a gate that cannot fail is not a gate."""

    def test_clean_repo_exits_zero(self, repo: Path) -> None:
        _readme(repo, "![Python](https://img.shields.io/badge/Python-3.12-blue)\n")

        assert validate_badges.main([str(repo)]) == 0

    def test_stale_badge_exits_non_zero(self, repo: Path) -> None:
        _readme(
            repo,
            "[![CI](https://github.com/o/e/actions/workflows/ci.yml/badge.svg)](x)\n",
        )

        assert validate_badges.main([str(repo)]) == 1


class TestTheRealReadme:
    """The repo's own badges must be honest. This is the point of the exercise."""

    def test_this_repos_badges_are_current(self) -> None:
        problems = validate_badges.check_badges(REPO_ROOT)

        assert not problems, "README badges are stale: " + "; ".join(problems)
