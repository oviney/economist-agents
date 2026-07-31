"""Tests for the mypy per-file baseline (B-035 Task 2).

B-031 took mypy off ``stages: [manual]``, making it able to fail for the first
time. The measurement then showed the cost: 12 of 48 ``scripts/*.py`` files
would block a commit **merely by being touched**, on errors the commit did not
introduce. That is the noise-overload failure mode that gets a gate reverted to
``manual`` — which is how mypy went inert in the first place.

The answer is not a weaker guide. ``CLAUDE.md`` keeps "Type hints mandatory";
the baseline is what makes that claim *true for all new code* instead of
aspirational. B-032 built this same mechanism for complexity
(``docs/harness-overrides.md``); this reuses the shape rather than inventing a
second answer to the same question.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = REPO_ROOT / "scripts" / "mypy_baseline.py"
_spec = importlib.util.spec_from_file_location("mypy_baseline", _SCRIPT)
assert _spec is not None and _spec.loader is not None
mypy_baseline = importlib.util.module_from_spec(_spec)
sys.modules["mypy_baseline"] = mypy_baseline
_spec.loader.exec_module(mypy_baseline)

BASELINE_DOC = REPO_ROOT / "docs" / "mypy-baseline.md"


class TestParseBaseline:
    """The baseline is markdown so it is reviewable, and parsed so it is enforced."""

    def test_parses_path_and_count(self) -> None:
        parsed = mypy_baseline.parse_baseline(
            "## Baseline\n\n- `scripts/foo.py` — 8\n- `scripts/bar.py` — 2\n",
        )

        assert parsed == {"scripts/foo.py": 8, "scripts/bar.py": 2}

    def test_ignores_prose_and_headings(self) -> None:
        parsed = mypy_baseline.parse_baseline(
            "# Title\n\nSome prose about why.\n\n- `scripts/foo.py` — 1\n\nMore prose.\n",
        )

        assert parsed == {"scripts/foo.py": 1}

    def test_accepts_ascii_hyphen_as_separator(self) -> None:
        """An em dash is the house style, but a typed hyphen must not silently drop."""
        assert mypy_baseline.parse_baseline("- `scripts/foo.py` - 3\n") == {
            "scripts/foo.py": 3,
        }

    def test_empty_document_is_empty_baseline(self) -> None:
        assert mypy_baseline.parse_baseline("# Nothing here\n") == {}

    def test_fenced_example_is_not_parsed_as_an_entry(self) -> None:
        """The register documents its own format; that example is not data."""
        parsed = mypy_baseline.parse_baseline(
            "## Format\n\n```markdown\n- `scripts/foo.py` — 8\n```\n\n"
            "## Baseline\n\n- `scripts/real.py` — 2\n",
        )

        assert parsed == {"scripts/real.py": 2}


class TestCountErrors:
    """Per-file error counts come from mypy's own output."""

    def test_counts_errors_per_file(self) -> None:
        output = (
            "scripts/foo.py:1: error: Need type annotation  [var-annotated]\n"
            "scripts/foo.py:9: error: Incompatible return  [return-value]\n"
            "scripts/bar.py:3: error: Missing return  [return]\n"
        )

        assert mypy_baseline.count_errors(output) == {
            "scripts/foo.py": 2,
            "scripts/bar.py": 1,
        }

    def test_notes_are_not_errors(self) -> None:
        output = (
            "scripts/foo.py:1: note: see documentation\n"
            "mypy.ini: note: unused section(s)\n"
            "scripts/foo.py:2: error: real problem  [misc]\n"
        )

        assert mypy_baseline.count_errors(output) == {"scripts/foo.py": 1}

    def test_clean_output_counts_nothing(self) -> None:
        assert mypy_baseline.count_errors("Success: no issues found\n") == {}


class TestCheck:
    """The gate itself: what blocks and what is grandfathered."""

    def test_file_at_its_baseline_passes(self) -> None:
        assert mypy_baseline.check({"scripts/foo.py": 8}, {"scripts/foo.py": 8}) == []

    def test_file_below_its_baseline_passes(self) -> None:
        """Paying errors down must never block the commit that pays them."""
        assert mypy_baseline.check({"scripts/foo.py": 3}, {"scripts/foo.py": 8}) == []

    def test_new_error_in_baselined_file_blocks(self) -> None:
        """The baseline is a per-file count, not a mute."""
        violations = mypy_baseline.check({"scripts/foo.py": 9}, {"scripts/foo.py": 8})

        assert len(violations) == 1
        assert "scripts/foo.py" in violations[0]
        assert "9" in violations[0] and "8" in violations[0]

    def test_unbaselined_file_blocks_on_first_error(self) -> None:
        violations = mypy_baseline.check({"scripts/new.py": 1}, {})

        assert len(violations) == 1
        assert "scripts/new.py" in violations[0]

    def test_clean_repo_passes(self) -> None:
        assert mypy_baseline.check({}, {"scripts/foo.py": 8}) == []


class TestBaselineShrinksOnly:
    """The baseline must track reality downward, never drift upward.

    This is the test that keeps the mechanism honest. Without it a baseline is
    just a mute with extra steps: someone bumps a number when a commit is
    blocked, and the gate is decoration again.
    """

    @pytest.fixture(scope="class")
    def actual_counts(self) -> dict[str, int]:
        """Measure every scripts/*.py file the way the pre-commit hook does."""
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "mypy",
                "--config-file=mypy.ini",
                "--follow-imports=silent",
                "--no-error-summary",
                *sorted(str(p) for p in (REPO_ROOT / "scripts").glob("*.py")),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return mypy_baseline.count_errors(result.stdout)

    @pytest.fixture(scope="class")
    def baseline(self) -> dict[str, int]:
        return mypy_baseline.parse_baseline(BASELINE_DOC.read_text(encoding="utf-8"))

    def test_baseline_document_exists(self) -> None:
        assert BASELINE_DOC.exists(), f"{BASELINE_DOC} is the register; it must exist"

    def test_no_file_exceeds_its_grandfathered_count(
        self,
        actual_counts: dict[str, int],
        baseline: dict[str, int],
    ) -> None:
        """A new error anywhere is a blocked commit, baselined file or not."""
        grew = {
            path: (count, baseline.get(path, 0))
            for path, count in actual_counts.items()
            if count > baseline.get(path, 0)
        }

        assert not grew, (
            "mypy errors grew beyond the baseline: "
            + "; ".join(f"{p}: {now} > {was}" for p, (now, was) in sorted(grew.items()))
            + ". Fix the new errors — do not raise the baseline."
        )

    def test_baseline_has_no_stale_entries(
        self,
        actual_counts: dict[str, int],
        baseline: dict[str, int],
    ) -> None:
        """A file that is now clean, or cleaner, must not keep its old allowance."""
        stale = {
            path: (actual_counts.get(path, 0), count)
            for path, count in baseline.items()
            if actual_counts.get(path, 0) < count
        }

        assert not stale, (
            "these files improved but the baseline still grants the old allowance: "
            + "; ".join(
                f"{p}: {now} < {was}" for p, (now, was) in sorted(stale.items())
            )
            + ". Lower the numbers in docs/mypy-baseline.md (remove the entry at 0)."
        )

    def test_baseline_lists_only_real_paths(self, baseline: dict[str, int]) -> None:
        missing = [p for p in baseline if not (REPO_ROOT / p).exists()]

        assert not missing, f"baseline names files that do not exist: {missing}"


class TestMain:
    """The entry point pre-commit actually calls."""

    def test_no_paths_is_a_no_op(self) -> None:
        """pre-commit can invoke the hook with no matching files."""
        assert mypy_baseline.main([]) == 0

    def test_clean_file_exits_zero(self) -> None:
        assert mypy_baseline.main(["scripts/mypy_baseline.py"]) == 0

    def test_baselined_file_exits_zero(self) -> None:
        """Grandfathered debt must not block a commit that merely touches it."""
        assert mypy_baseline.main(["scripts/publication_validator.py"]) == 0

    def test_new_error_exits_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A file with more errors than allowed blocks, and says by how many."""
        monkeypatch.setattr(
            mypy_baseline,
            "run_mypy",
            lambda paths: (
                "scripts/agent_loader.py:1: error: boom  [misc]\n"
                "scripts/agent_loader.py:2: error: boom  [misc]\n"
                "scripts/agent_loader.py:3: error: boom  [misc]\n"
            ),
        )

        assert mypy_baseline.main(["scripts/agent_loader.py"]) == 1

    def test_all_flag_checks_every_script(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seen: list[list[str]] = []
        monkeypatch.setattr(
            mypy_baseline,
            "run_mypy",
            lambda paths: seen.append(paths) or "",
        )

        assert mypy_baseline.main(["--all"]) == 0
        assert len(seen) == 1
        assert "scripts/mypy_baseline.py" in seen[0]
        assert len(seen[0]) > 40


class TestHookIsWired:
    """A baseline nobody runs is worse than no baseline (the B-031 lesson)."""

    @pytest.fixture(scope="class")
    def hooks(self) -> list[dict]:
        import yaml

        config = yaml.safe_load(
            (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"),
        )
        return [hook for repo in config["repos"] for hook in repo["hooks"]]

    def test_baseline_hook_exists(self, hooks: list[dict]) -> None:
        assert any(h["id"] == "mypy-baseline" for h in hooks)

    def test_baseline_hook_is_not_manual(self, hooks: list[dict]) -> None:
        """`stages: [manual]` is exactly how mypy went inert before B-031."""
        hook = next(h for h in hooks if h["id"] == "mypy-baseline")

        assert "manual" not in hook.get("stages", [])

    def test_no_raw_mypy_hook_bypasses_the_baseline(self, hooks: list[dict]) -> None:
        """Two mypy gates would mean the un-baselined one still blocks everything."""
        assert not [h for h in hooks if h["id"] == "mypy"]


class TestGuideStaysStrict:
    """Task 2's explicit non-goal: the baseline must not weaken the guide."""

    def test_claude_md_still_mandates_type_hints(self) -> None:
        text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        assert "Type hints mandatory" in text
