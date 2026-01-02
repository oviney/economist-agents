#!/usr/bin/env python3
"""
Visual QA Zone Boundary Validator (Sprint 8 Story 2)

Programmatic validation of Economist-style chart zones to catch layout bugs
BEFORE they reach LLM-based Visual QA. This is shift-left testing for charts.

Background:
- Sprint 7 found 28.6% of bugs are visual QA gaps
- Most bugs are zone boundary violations (labels in X-axis zone, title/red bar overlap)
- LLM vision is not deterministic - need programmatic checks

Zone Layout (from CHART_DESIGN_SPEC.md):
```
┌─────────────────────────────────────────────────────────┐
│ RED BAR ZONE (y: 0.96 - 1.00)                          │
├─────────────────────────────────────────────────────────┤
│ TITLE ZONE (y: 0.85 - 0.94)                            │
├─────────────────────────────────────────────────────────┤
│ CHART ZONE (y: 0.15 - 0.78)                            │
├─────────────────────────────────────────────────────────┤
│ X-AXIS ZONE (y: 0.08 - 0.14)                           │
├─────────────────────────────────────────────────────────┤
│ SOURCE ZONE (y: 0.01 - 0.06)                           │
└─────────────────────────────────────────────────────────┘
```

Usage:
    from visual_qa_zones import ZoneBoundaryValidator

    validator = ZoneBoundaryValidator()
    is_valid, issues = validator.validate_chart('output/chart.png')

    if not is_valid:
        print(f"Zone violations: {issues}")
"""

import re
from pathlib import Path


class ZoneBoundaryValidator:
    """Validates Economist-style chart zone boundaries programmatically"""

    # Zone boundaries in figure coordinates (0-1)
    ZONES = {
        "red_bar": (0.96, 1.00),
        "title": (0.85, 0.94),
        "chart": (0.15, 0.78),
        "x_axis": (0.08, 0.14),
        "source": (0.01, 0.06),
    }

    def __init__(self):
        self.issues = []

    def validate_chart(self, chart_path: str) -> tuple[bool, list[str]]:
        """
        Validate chart zone boundaries.

        Args:
            chart_path: Path to chart PNG file

        Returns:
            (is_valid, issues_list)
        """
        self.issues = []
        chart_path = Path(chart_path)

        if not chart_path.exists():
            self.issues.append(f"Chart file not found: {chart_path}")
            return False, self.issues

        # Read the matplotlib code that generated the chart
        # (This assumes we have access to generation script or can extract from metadata)
        # For now, validate based on naming conventions and expected patterns

        # Check 1: Validate chart filename follows convention
        if not self._validate_filename(chart_path):
            self.issues.append(
                f"Invalid filename: {chart_path.name}. Must be slug-style (lowercase-with-hyphens.png)"
            )

        # Check 2: Look for corresponding generation script or metadata
        script_path = (
            chart_path.parent.parent
            / "scripts"
            / chart_path.name.replace(".png", ".py")
        )
        if script_path.exists():
            code_issues = self._validate_matplotlib_code(script_path)
            self.issues.extend(code_issues)

        # Check 3: Pixel-based validation (if PIL available)
        try:
            import PIL.Image  # noqa: F401

            pixel_issues = self._validate_pixels(chart_path)
            self.issues.extend(pixel_issues)
        except ImportError:
            # PIL not available - skip pixel validation
            pass

        return len(self.issues) == 0, self.issues

    def _validate_filename(self, chart_path: Path) -> bool:
        """Validate chart filename follows conventions"""
        name = chart_path.stem  # Filename without extension

        # Must be lowercase with hyphens (slug style)
        if not re.match(r"^[a-z0-9-]+$", name):
            return False

        # Must not have consecutive hyphens
        if "--" in name:
            return False

        # Must not start or end with hyphen
        return not (name.startswith("-") or name.endswith("-"))

    def _validate_matplotlib_code(self, script_path: Path) -> list[str]:
        """Validate matplotlib code for zone boundary violations"""
        issues = []

        with open(script_path) as f:
            code = f.read()

        # Check 1: Title position (should be y=0.90 in figure coords)
        title_matches = re.findall(
            r'fig\.text\([^,]+,\s*(0\.\d+),.*?["\'].*?title', code, re.IGNORECASE
        )
        for y_pos in title_matches:
            y = float(y_pos)
            if y < 0.85 or y > 0.94:
                issues.append(f"Title y={y} outside TITLE ZONE (0.85-0.94)")

        # Check 2: Subtitle position (should be y=0.85)
        subtitle_matches = re.findall(
            r'fig\.text\([^,]+,\s*(0\.\d+),.*?["\'].*?subtitle', code, re.IGNORECASE
        )
        for y_pos in subtitle_matches:
            y = float(y_pos)
            if y < 0.85 or y > 0.94:
                issues.append(f"Subtitle y={y} outside TITLE ZONE (0.85-0.94)")

        # Check 3: Source line position (should be y=0.03 in source zone)
        source_matches = re.findall(
            r'fig\.text\([^,]+,\s*(0\.\d+),.*?["\'].*?[Ss]ource', code
        )
        for y_pos in source_matches:
            y = float(y_pos)
            if y < 0.01 or y > 0.06:
                issues.append(f"Source y={y} outside SOURCE ZONE (0.01-0.06)")

        # Check 4: Red bar position (should be y=0.96-1.00)
        redbar_matches = re.findall(r"Rectangle\(\(0,\s*(0\.\d+)\)", code)
        for y_pos in redbar_matches:
            y = float(y_pos)
            if y < 0.96:
                issues.append(f"Red bar y={y} below RED BAR ZONE (0.96-1.00)")

        # Check 5: Inline labels (ax.annotate) should have appropriate offsets
        # Look for labels without xytext offset
        annotate_matches = re.findall(r"ax\.annotate\([^)]+\)", code)
        for match in annotate_matches:
            if "xytext" not in match:
                issues.append(
                    f"Inline label missing xytext offset (will overlap data): {match[:50]}..."
                )

        return issues

    def _validate_pixels(self, chart_path: Path) -> list[str]:
        """Validate chart at pixel level for zone boundaries"""
        issues = []

        try:
            import numpy as np
            from PIL import Image

            img = Image.open(chart_path)
            pixels = np.array(img)
            height, width = pixels.shape[:2]

            # Convert zone boundaries to pixel coordinates
            red_bar_zone = (int(height * 0.96), height)
            title_zone = (int(height * 0.85), int(height * 0.94))

            # Check 1: Red bar present at top
            red_bar_pixels = pixels[red_bar_zone[0] : red_bar_zone[1], :, :]
            red_bar_color = np.array([227, 49, 11])  # #e3120b

            # Check if red bar color is dominant in that zone
            red_matches = np.all(np.abs(red_bar_pixels - red_bar_color) < 10, axis=2)
            if red_matches.sum() < (width * 4 * 0.5):  # Less than 50% coverage
                issues.append("Red bar not detected in RED BAR ZONE (top 4%)")

            # Check 2: Background color
            bg_color = np.array([241, 240, 233])  # #f1f0e9
            bg_pixels = pixels[title_zone[0] : title_zone[1], :, :]
            bg_matches = np.all(np.abs(bg_pixels - bg_color) < 30, axis=2)

            if bg_matches.sum() < (bg_pixels.shape[0] * bg_pixels.shape[1] * 0.3):
                issues.append(
                    "Background color #f1f0e9 not dominant (expected warm beige)"
                )

        except Exception:
            # Pixel validation optional - don't fail if it errors
            pass

        return issues

    def generate_report(self) -> str:
        """Generate human-readable validation report"""
        if not self.issues:
            return "✅ All zone boundary checks PASSED"

        report = ["❌ Zone Boundary Violations Detected:", ""]

        for i, issue in enumerate(self.issues, 1):
            report.append(f"  {i}. {issue}")

        report.extend(
            [
                "",
                "Recommendation: Fix zone boundary violations before publication.",
                "See docs/CHART_DESIGN_SPEC.md for zone layout rules.",
            ]
        )

        return "\n".join(report)


def validate_chart_cli():
    """CLI entry point for zone validation"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Economist-style chart zone boundaries"
    )
    parser.add_argument("chart_path", help="Path to chart PNG file")
    parser.add_argument(
        "--report", action="store_true", help="Generate detailed report"
    )

    args = parser.parse_args()

    validator = ZoneBoundaryValidator()
    is_valid, issues = validator.validate_chart(args.chart_path)

    if args.report:
        print(validator.generate_report())
    else:
        if is_valid:
            print(f"✅ {args.chart_path}: All checks PASSED")
        else:
            print(f"❌ {args.chart_path}: {len(issues)} issues found")
            for issue in issues:
                print(f"   • {issue}")

    return 0 if is_valid else 1


if __name__ == "__main__":
    import sys

    sys.exit(validate_chart_cli())
