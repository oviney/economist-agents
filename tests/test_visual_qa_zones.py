#!/usr/bin/env python3
"""Tests for ``src.quality.visual_qa_zones`` — Zone Boundary Validator.

Covers public surface:
* ``ZoneBoundaryValidator.validate_chart``
* ``ZoneBoundaryValidator._validate_filename`` (used via ``validate_chart``)
* ``ZoneBoundaryValidator._validate_matplotlib_code``
* ``ZoneBoundaryValidator._validate_pixels``
* ``ZoneBoundaryValidator.generate_report``
* ``validate_chart_cli`` (CLI entry point)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.quality.visual_qa_zones import ZoneBoundaryValidator, validate_chart_cli

# ── Helpers ───────────────────────────────────────────────────────────────────

RED_BAR_RGB = (227, 49, 11)  # #e3120b
BG_RGB = (241, 240, 233)  # #f1f0e9


def _make_compliant_chart(path: Path, width: int = 100, height: int = 100) -> Path:
    """Create a synthetic PNG that satisfies the pixel-level zone checks.

    Fills the top 4% with the red bar colour and the title zone with the
    expected beige background.
    """
    img = Image.new("RGB", (width, height), BG_RGB)
    pixels = np.array(img)

    # Pixel rows are top-down, so the red bar occupies the first 4%.
    red_bar_end = max(1, int(height * 0.04))
    pixels[:red_bar_end, :, :] = RED_BAR_RGB

    # Raster rows 0.06..0.15 correspond to the figure-coordinate title zone.
    Image.fromarray(pixels).save(path)
    return path


def _make_blank_chart(path: Path, width: int = 100, height: int = 100) -> Path:
    """Create a solid black PNG — fails both pixel checks.

    Black (0,0,0) is far enough from both the red bar (#e3120b) and the beige
    background (#f1f0e9) to exceed the validator's 10/30 tolerance windows.
    """
    Image.new("RGB", (width, height), (0, 0, 0)).save(path)
    return path


def _make_bottom_bar_chart(path: Path, width: int = 100, height: int = 100) -> Path:
    """Create a chart with the red bar incorrectly placed at the bottom."""
    img = Image.new("RGB", (width, height), BG_RGB)
    pixels = np.array(img)
    red_bar_start = int(height * 0.96)
    pixels[red_bar_start:, :, :] = RED_BAR_RGB
    Image.fromarray(pixels).save(path)
    return path


# ── ZoneBoundaryValidator.validate_chart ──────────────────────────────────────


class TestValidateChartFileExistence:
    def test_missing_file_returns_invalid_with_error_message(
        self, tmp_path: Path
    ) -> None:
        validator = ZoneBoundaryValidator()
        missing = tmp_path / "does-not-exist.png"

        is_valid, issues = validator.validate_chart(str(missing))

        assert is_valid is False
        assert any("Chart file not found" in i for i in issues)

    def test_validate_chart_resets_issues_between_calls(self, tmp_path: Path) -> None:
        """A second call must not accumulate issues from the first."""
        validator = ZoneBoundaryValidator()
        missing = tmp_path / "nope.png"
        validator.validate_chart(str(missing))  # populates issues

        compliant = _make_compliant_chart(tmp_path / "compliant-chart.png")
        is_valid, issues = validator.validate_chart(str(compliant))

        assert is_valid is True
        assert issues == []


class TestValidateChartFilename:
    def test_valid_slug_filename_passes(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        chart = _make_compliant_chart(tmp_path / "good-chart-name.png")

        is_valid, issues = validator.validate_chart(str(chart))

        assert is_valid is True
        assert issues == []

    @pytest.mark.parametrize(
        "filename",
        [
            "BadName.png",  # uppercase
            "bad_name.png",  # underscore
            "bad--name.png",  # consecutive hyphens
            "-bad.png",  # leading hyphen
            "bad-.png",  # trailing hyphen
            "bad name.png",  # space
        ],
    )
    def test_invalid_filename_flagged(self, tmp_path: Path, filename: str) -> None:
        validator = ZoneBoundaryValidator()
        chart = _make_compliant_chart(tmp_path / filename)

        is_valid, issues = validator.validate_chart(str(chart))

        assert is_valid is False
        assert any("Invalid filename" in i for i in issues)


# ── ZoneBoundaryValidator._validate_matplotlib_code ───────────────────────────


def _setup_script_alongside_chart(tmp_path: Path, code: str) -> Path:
    """Return chart path with a sibling ``scripts/<stem>.py`` containing ``code``.

    Mirrors the layout the validator looks for:
        <tmp>/output/chart.png
        <tmp>/scripts/chart.py
    """
    output_dir = tmp_path / "output"
    scripts_dir = tmp_path / "scripts"
    output_dir.mkdir()
    scripts_dir.mkdir()

    chart_path = _make_compliant_chart(output_dir / "demo-chart.png")
    (scripts_dir / "demo-chart.py").write_text(code)
    return chart_path


class TestValidateMatplotlibCode:
    def test_compliant_matplotlib_code_produces_no_code_issues(
        self, tmp_path: Path
    ) -> None:
        validator = ZoneBoundaryValidator()
        code = (
            'fig.text(0.5, 0.90, "Big Title", ha="center")\n'
            'fig.text(0.5, 0.87, "Subtitle here", ha="center")\n'
            'fig.text(0.5, 0.03, "Source: BLS", ha="center")\n'
            "ax.add_patch(Rectangle((0, 0.97), 1, 0.03))\n"
            # NB: the validator's annotate regex stops at the first ')', so the
            # ``xytext`` keyword must appear *before* any parenthesised expression
            # (such as ``xy=(1, 2)``) to be detected.
            'ax.annotate("label", xytext=(5, 5), textcoords="offset points")\n'
        )
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        is_valid, issues = validator.validate_chart(str(chart_path))

        # Filename is valid AND code has no violations AND pixels are compliant.
        assert is_valid is True
        assert issues == []

    def test_title_outside_zone_is_flagged(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        code = 'fig.text(0.5, 0.50, "Big Title here")\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("Title y=0.5 outside TITLE ZONE" in i for i in issues)

    def test_subtitle_outside_zone_is_flagged(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        code = 'fig.text(0.5, 0.20, "A subtitle text")\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("Subtitle y=0.2 outside TITLE ZONE" in i for i in issues)
        assert not any("Title y=0.2 outside TITLE ZONE" in i for i in issues)

    def test_source_outside_zone_is_flagged(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        code = 'fig.text(0.5, 0.50, "Source: World Bank")\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("Source y=0.5 outside SOURCE ZONE" in i for i in issues)

    def test_red_bar_below_zone_is_flagged(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        code = "ax.add_patch(Rectangle((0, 0.50), 1, 0.03))\n"
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("Red bar y=0.5 below RED BAR ZONE" in i for i in issues)

    def test_inline_annotate_without_xytext_is_flagged(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        code = 'ax.annotate("label", xy=(1, 2))\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("Inline label missing xytext offset" in i for i in issues)

    def test_positional_xy_anchor_triggers_xaxis_intrusion(
        self, tmp_path: Path
    ) -> None:
        """Matplotlib accepts the anchor positionally: annotate(text, xy, ...).

        Regression for #413: the parser previously read only the ``xy`` keyword,
        so a positional anchor recorded ``xy=None`` and silently skipped the
        X-axis intrusion check. The positional form must behave like the keyword
        form below.
        """
        validator = ZoneBoundaryValidator()
        code = 'ax.annotate("label", (5, 10), xytext=(0, -5))\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("may intrude into X-axis zone" in i for i in issues)

    def test_keyword_xy_anchor_triggers_xaxis_intrusion(self, tmp_path: Path) -> None:
        """Parity baseline: keyword ``xy`` must fire the same check as positional."""
        validator = ZoneBoundaryValidator()
        code = 'ax.annotate("label", xy=(5, 10), xytext=(0, -5))\n'
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("may intrude into X-axis zone" in i for i in issues)

    def test_positional_xy_anchor_triggers_label_collision(
        self, tmp_path: Path
    ) -> None:
        """Positional anchors must also feed label-collision detection (#413)."""
        validator = ZoneBoundaryValidator()
        code = (
            'ax.annotate("a", (5, 50), xytext=(0, 5))\n'
            'ax.annotate("b", (5, 50), xytext=(0, 5))\n'
        )
        chart_path = _setup_script_alongside_chart(tmp_path, code)

        _, issues = validator.validate_chart(str(chart_path))

        assert any("collide" in i.lower() or "overlap" in i.lower() for i in issues)

    def test_no_script_means_no_code_issues(self, tmp_path: Path) -> None:
        """When no sibling script exists the code-validation step is skipped."""
        validator = ZoneBoundaryValidator()
        # No scripts/ sibling — only the chart.
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        chart_path = _make_compliant_chart(output_dir / "lonely-chart.png")

        is_valid, issues = validator.validate_chart(str(chart_path))

        assert is_valid is True
        assert issues == []


# ── ZoneBoundaryValidator._validate_pixels ────────────────────────────────────


class TestValidatePixels:
    def test_compliant_chart_passes_pixel_checks(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        chart = _make_compliant_chart(tmp_path / "pixel-good.png")

        is_valid, issues = validator.validate_chart(str(chart))

        assert is_valid is True
        assert issues == []

    def test_blank_chart_flags_missing_red_bar_and_background(
        self, tmp_path: Path
    ) -> None:
        validator = ZoneBoundaryValidator()
        chart = _make_blank_chart(tmp_path / "pixel-blank.png")

        is_valid, issues = validator.validate_chart(str(chart))

        assert is_valid is False
        joined = "\n".join(issues)
        assert "Red bar not detected" in joined
        assert "Background color #f1f0e9 not dominant" in joined

    def test_bottom_red_bar_is_rejected(self, tmp_path: Path) -> None:
        validator = ZoneBoundaryValidator()
        chart = _make_bottom_bar_chart(tmp_path / "pixel-bottom-bar.png")

        is_valid, issues = validator.validate_chart(str(chart))

        assert is_valid is False
        assert any("Red bar not detected" in issue for issue in issues)

    def test_pixel_validation_swallows_unexpected_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If PIL/numpy blow up mid-validation, no exception should propagate."""
        validator = ZoneBoundaryValidator()
        chart = _make_compliant_chart(tmp_path / "pixel-safe.png")

        # Force ``Image.open`` to raise once we're inside ``_validate_pixels``.
        from src.quality import visual_qa_zones as mod

        original_open = Image.open

        def _boom(*_a, **_kw):
            raise RuntimeError("simulated PIL failure")

        # Patch the symbol resolved inside ``_validate_pixels`` (``from PIL import Image``).
        # Easiest path: monkeypatch ``PIL.Image.open`` globally for this test.
        monkeypatch.setattr("PIL.Image.open", _boom)

        try:
            is_valid, issues = validator.validate_chart(str(chart))
        finally:
            monkeypatch.setattr("PIL.Image.open", original_open)

        # Pixel issues are swallowed; filename + missing-script paths still ran cleanly,
        # so the chart is reported valid with no issues.
        assert is_valid is True
        assert issues == []
        # Ensure we actually exercised the module under test.
        assert mod.ZoneBoundaryValidator is ZoneBoundaryValidator


# ── ZoneBoundaryValidator.generate_report ─────────────────────────────────────


class TestGenerateReport:
    def test_report_when_no_issues(self) -> None:
        validator = ZoneBoundaryValidator()
        # No validate_chart call → issues is empty by construction.
        report = validator.generate_report()

        assert "All zone boundary checks PASSED" in report

    def test_report_lists_each_issue_with_numbering(self) -> None:
        validator = ZoneBoundaryValidator()
        validator.issues = ["alpha problem", "beta problem"]

        report = validator.generate_report()

        assert "Zone Boundary Violations Detected" in report
        assert "1. alpha problem" in report
        assert "2. beta problem" in report
        assert "docs/CHART_DESIGN_SPEC.md" in report


# ── validate_chart_cli ────────────────────────────────────────────────────────


class TestValidateChartCli:
    def test_cli_returns_zero_for_compliant_chart(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        chart = _make_compliant_chart(tmp_path / "cli-good-chart.png")
        monkeypatch.setattr("sys.argv", ["visual_qa_zones", str(chart)])

        exit_code = validate_chart_cli()

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "All checks PASSED" in out

    def test_cli_returns_one_for_invalid_chart(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        chart = _make_compliant_chart(tmp_path / "BadName.png")  # invalid filename
        monkeypatch.setattr("sys.argv", ["visual_qa_zones", str(chart)])

        exit_code = validate_chart_cli()

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "issues found" in out
        assert "Invalid filename" in out

    def test_cli_report_flag_emits_detailed_report(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        chart = _make_compliant_chart(tmp_path / "BadName.png")
        monkeypatch.setattr("sys.argv", ["visual_qa_zones", str(chart), "--report"])

        exit_code = validate_chart_cli()

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "Zone Boundary Violations Detected" in out
        assert "Recommendation" in out

    def test_cli_missing_file_returns_one(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        missing = tmp_path / "ghost.png"
        monkeypatch.setattr("sys.argv", ["visual_qa_zones", str(missing)])

        exit_code = validate_chart_cli()

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "Chart file not found" in out
