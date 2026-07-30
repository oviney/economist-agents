"""Tests for the B-032 complexity sensor.

The sensor exists because `ruff.toml` regulated no complexity dimension, which is the
characteristic failure mode of AI-written code (SE Radio 730). Its job is not to report a
number — ruff already does that — but to turn the number into a *judgment call* with a
recorded-override escape hatch, per Boeckeler's ESLint-message technique.

These tests assert the sensor's contract, not its internals: given source text, what does
it emit and what does it exit with.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.complexity_sensor import (
    JUDGMENT_CALL_MARKER,
    ComplexityFinding,
    format_report,
    load_overrides,
    scan_paths,
)

# A function whose cyclomatic complexity is comfortably over 10.
OVER_COMPLEX_SOURCE = '''"""Fixture module."""


def tangled(value: int) -> str:
    """Branch enough times to exceed max-complexity."""
    result = ""
    if value > 1:
        result += "a"
    if value > 2:
        result += "b"
    if value > 3:
        result += "c"
    if value > 4:
        result += "d"
    if value > 5:
        result += "e"
    if value > 6:
        result += "f"
    if value > 7:
        result += "g"
    if value > 8:
        result += "h"
    if value > 9:
        result += "i"
    if value > 10:
        result += "j"
    if value > 11:
        result += "k"
    if value > 12:
        result += "l"
    return result
'''

CLEAN_SOURCE = '''"""Fixture module."""


def tidy(value: int) -> str:
    """Do one thing."""
    return "big" if value > 10 else "small"
'''


@pytest.fixture
def over_complex_file(tmp_path: Path) -> Path:
    """Write a module containing one over-complex function."""
    path = tmp_path / "tangled_module.py"
    path.write_text(OVER_COMPLEX_SOURCE, encoding="utf-8")
    return path


@pytest.fixture
def clean_file(tmp_path: Path) -> Path:
    """Write a module with no complexity findings."""
    path = tmp_path / "tidy_module.py"
    path.write_text(CLEAN_SOURCE, encoding="utf-8")
    return path


class TestScanPaths:
    """`scan_paths` turns ruff's JSON output into findings."""

    def test_flags_an_over_complex_function(self, over_complex_file: Path) -> None:
        findings = scan_paths([over_complex_file])

        assert findings, "an over-complex function must produce at least one finding"
        assert any(f.function == "tangled" for f in findings)
        assert any(f.code == "C901" for f in findings)

    def test_clean_file_produces_no_findings(self, clean_file: Path) -> None:
        assert scan_paths([clean_file]) == []

    def test_skips_non_python_paths(self, tmp_path: Path) -> None:
        not_python = tmp_path / "notes.md"
        not_python.write_text("# not code\n", encoding="utf-8")

        assert scan_paths([not_python]) == []

    def test_missing_path_is_ignored_rather_than_raising(self, tmp_path: Path) -> None:
        """A deleted file must not crash the sensor — hooks call this on git diffs."""
        assert scan_paths([tmp_path / "gone.py"]) == []


class TestFormatReport:
    """The report is the whole point: a judgment call, not a number."""

    def test_report_states_the_judgment_call_and_the_override_path(self) -> None:
        finding = ComplexityFinding(
            path="scripts/foo.py",
            line=12,
            function="bar",
            code="C901",
            message="`bar` is too complex (18 > 10)",
        )

        report = format_report([finding])

        assert "scripts/foo.py" in report
        assert "bar" in report
        assert JUDGMENT_CALL_MARKER in report
        # The override register must be named, or the escape hatch is folklore.
        assert "docs/harness-overrides.md" in report
        # A bare noqa is explicitly not the escape hatch.
        assert "noqa" in report

    def test_empty_findings_produce_an_empty_report(self) -> None:
        assert format_report([]) == ""


class TestOverrides:
    """A recorded override must actually suppress its finding, or it is theatre."""

    def test_recorded_override_suppresses_the_matching_finding(
        self,
        tmp_path: Path,
    ) -> None:
        register = tmp_path / "harness-overrides.md"
        register.write_text(
            "# Overrides\n\n"
            "- `scripts/foo.py::bar` — dispatch table, splitting it would obscure it\n",
            encoding="utf-8",
        )

        overrides = load_overrides(register)

        assert "scripts/foo.py::bar" in overrides

    def test_absent_register_yields_no_overrides(self, tmp_path: Path) -> None:
        assert load_overrides(tmp_path / "nope.md") == set()

    def test_override_filters_the_finding_out_of_the_report(
        self,
        tmp_path: Path,
    ) -> None:
        register = tmp_path / "harness-overrides.md"
        register.write_text(
            "- `scripts/foo.py::bar` — generated parser, keep as-is\n",
            encoding="utf-8",
        )
        finding = ComplexityFinding(
            path="scripts/foo.py",
            line=12,
            function="bar",
            code="C901",
            message="`bar` is too complex (18 > 10)",
        )

        report = format_report([finding], overrides=load_overrides(register))

        assert report == ""


class TestThresholdSource:
    """The threshold lives in ruff.toml, so there is exactly one number."""

    def test_ruff_toml_declares_max_complexity(self) -> None:
        ruff_config = Path(__file__).resolve().parents[1] / "ruff.toml"
        text = ruff_config.read_text(encoding="utf-8")

        assert "[lint.mccabe]" in text
        assert "max-complexity" in text
