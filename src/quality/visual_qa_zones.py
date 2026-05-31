#!/usr/bin/env python3
"""Visual QA Zone Boundary Validator (Sprint 8 Story 2)

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
    from src.quality.visual_qa_zones import ZoneBoundaryValidator

    validator = ZoneBoundaryValidator()
    is_valid, issues = validator.validate_chart('output/chart.png')

    if not is_valid:
        print(f"Zone violations: {issues}")
"""

import ast
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
        """Validate chart zone boundaries.

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
                f"Invalid filename: {chart_path.name}. Must be slug-style (lowercase-with-hyphens.png)",
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

        # Check 1-3: Figure text zones
        issues.extend(self._validate_figure_text_layout(code))

        # Check 4: Red bar position (should be y=0.96-1.00)
        redbar_matches = re.findall(r"Rectangle\(\(0,\s*(0\.\d+)\)", code)
        for y_pos in redbar_matches:
            y = float(y_pos)
            if y < 0.96:
                issues.append(f"Red bar y={y} below RED BAR ZONE (0.96-1.00)")

        # Check 5: Inline labels should avoid data, axis, and each other.
        issues.extend(self._validate_annotation_layout(code))
        return issues

    def _validate_figure_text_layout(self, code: str) -> list[str]:
        """Validate title, subtitle, source, and canvas bounds for figure text."""
        issues: list[str] = []
        for text_call in self._iter_figure_text_calls(code):
            x = text_call["x"]
            y = text_call["y"]
            label = str(text_call["label"])
            label_lower = label.lower()

            if not isinstance(x, float) or not isinstance(y, float):
                continue

            if 0.96 <= y <= 1.0:
                issues.append(
                    f"Figure text '{label}' y={y:g} intrudes into "
                    "RED BAR ZONE (0.96-1.00)",
                )

            if (
                "title" in label_lower
                and "subtitle" not in label_lower
                and (y < 0.85 or y > 0.94)
            ):
                issues.append(f"Title y={y:g} outside TITLE ZONE (0.85-0.94)")

            if "subtitle" in label_lower and (y < 0.85 or y > 0.94):
                issues.append(f"Subtitle y={y:g} outside TITLE ZONE (0.85-0.94)")

            if "source" in label_lower and (y < 0.01 or y > 0.06):
                issues.append(f"Source y={y:g} outside SOURCE ZONE (0.01-0.06)")

            if x < 0.0 or x > 0.98 or y < 0.0 or y > 1.0:
                issues.append(
                    f"Figure text at ({x:g}, {y:g}) may be clipped at chart edge",
                )
        return issues

    def _validate_annotation_layout(self, code: str) -> list[str]:
        """Validate inline label offsets and label-to-label spacing."""
        issues: list[str] = []
        annotations: list[dict[str, float | str]] = []

        for annotation in self._iter_annotation_calls(code):
            label = str(annotation["label"])
            xy = annotation["xy"]
            xytext = annotation["xytext"]

            if xytext is None:
                if not annotation["has_xytext"]:
                    source = str(annotation["source"])
                    issues.append(
                        "Inline label missing xytext offset "
                        f"(will overlap data): {source[:50]}...",
                    )
                continue

            offset_x, offset_y = xytext
            if abs(offset_x) <= 2 and abs(offset_y) <= 2:
                issues.append(
                    f"Inline label '{label}' has near-zero xytext offset; "
                    "it will overlap data line",
                )

            if xy is not None:
                anchor_x, anchor_y = xy
                annotations.append(
                    {
                        "label": label,
                        "anchor_x": anchor_x,
                        "anchor_y": anchor_y,
                        "offset_x": offset_x,
                        "offset_y": offset_y,
                    },
                )
                if anchor_y <= 15 and offset_y < 0:
                    issues.append(
                        f"Inline label '{label}' uses negative offset near low data "
                        "and may intrude into X-axis zone",
                    )

        issues.extend(self._detect_label_collisions(annotations))
        return issues

    def _iter_annotation_calls(self, code: str) -> list[dict[str, object]]:
        """Return literal details from ``ax.annotate`` calls in chart code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        annotations: list[dict[str, object]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "annotate":
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "ax":
                continue

            xy_node = self._find_keyword_node(node, "xy")
            xytext_node = self._find_keyword_node(node, "xytext")
            annotations.append(
                {
                    "label": self._extract_string_arg(node, 0),
                    "xy": self._extract_numeric_tuple(xy_node),
                    "xytext": self._extract_numeric_tuple(xytext_node),
                    "has_xytext": xytext_node is not None,
                    "source": ast.get_source_segment(code, node) or "ax.annotate(...)",
                },
            )
        return annotations

    def _iter_figure_text_calls(self, code: str) -> list[dict[str, object]]:
        """Return literal details from ``fig.text`` calls in chart code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        text_calls: list[dict[str, object]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "text":
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "fig":
                continue

            text_calls.append(
                {
                    "x": self._extract_numeric_arg(node, 0),
                    "y": self._extract_numeric_arg(node, 1),
                    "label": self._extract_string_arg(node, 2),
                },
            )
        return text_calls

    def _find_keyword_node(self, call: ast.Call, name: str) -> ast.AST | None:
        """Find a keyword argument node in a Matplotlib call."""
        for keyword in call.keywords:
            if keyword.arg == name:
                return keyword.value
        return None

    def _extract_string_arg(self, call: ast.Call, index: int) -> str:
        """Extract a string-like positional argument from a parsed call."""
        if len(call.args) <= index:
            return "<unknown>"
        arg = call.args[index]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.JoinedStr):
            return "<dynamic>"
        return "<unknown>"

    def _extract_numeric_arg(self, call: ast.Call, index: int) -> float | None:
        """Extract a numeric positional argument from a parsed call."""
        if len(call.args) <= index:
            return None
        return self._extract_numeric_value(call.args[index])

    def _extract_numeric_tuple(
        self,
        node: ast.AST | None,
    ) -> tuple[float, float] | None:
        """Extract a literal numeric two-item tuple from parsed Python."""
        if not isinstance(node, ast.Tuple) or len(node.elts) != 2:
            return None

        values: list[float] = []
        for item in node.elts:
            value = self._extract_numeric_value(item)
            if value is None:
                return None
            values.append(value)
        return (values[0], values[1])

    def _extract_numeric_value(self, node: ast.AST) -> float | None:
        """Extract a literal numeric value from parsed Python."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, int | float)
        ):
            return -float(node.operand.value)
        return None

    def _detect_label_collisions(
        self,
        annotations: list[dict[str, float | str]],
    ) -> list[str]:
        """Detect labels anchored too close together with similar offsets."""
        issues: list[str] = []
        for index, first in enumerate(annotations):
            for second in annotations[index + 1 :]:
                same_x = abs(float(first["anchor_x"]) - float(second["anchor_x"])) < 0.5
                close_anchor_y = (
                    abs(float(first["anchor_y"]) - float(second["anchor_y"])) < 5
                )
                similar_offset = (
                    abs(float(first["offset_y"]) - float(second["offset_y"])) < 8
                )
                if same_x and close_anchor_y and similar_offset:
                    issues.append(
                        "Label-to-label overlap likely between "
                        f"'{first['label']}' and '{second['label']}'",
                    )
        return issues

    def _validate_pixels(self, chart_path: Path) -> list[str]:
        """Validate chart at pixel level for zone boundaries"""
        issues = []

        try:
            import numpy as np
            from PIL import Image

            with Image.open(chart_path) as img:
                pixels = np.array(img.convert("RGB"))
            height, width = pixels.shape[:2]

            # Raster rows count down from the top, unlike figure coordinates.
            red_bar_height = max(1, int(height * 0.04))
            red_bar_zone = (0, red_bar_height)
            title_zone = (int(height * 0.06), int(height * 0.15))

            # Check 1: Red bar present at top
            red_bar_pixels = pixels[red_bar_zone[0] : red_bar_zone[1], :, :]
            red_bar_color = np.array([227, 49, 11])  # #e3120b

            # Check if red bar color is dominant in that zone
            red_matches = np.all(np.abs(red_bar_pixels - red_bar_color) < 10, axis=2)
            if red_matches.sum() < (red_bar_pixels.shape[0] * width * 0.5):
                issues.append("Red bar not detected in RED BAR ZONE (top 4%)")

            # Check 2: Background color
            bg_color = np.array([241, 240, 233])  # #f1f0e9
            bg_pixels = pixels[title_zone[0] : title_zone[1], :, :]
            bg_matches = np.all(np.abs(bg_pixels - bg_color) < 30, axis=2)

            if bg_matches.sum() < (bg_pixels.shape[0] * bg_pixels.shape[1] * 0.3):
                issues.append(
                    "Background color #f1f0e9 not dominant (expected warm beige)",
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
            ],
        )

        return "\n".join(report)


def validate_chart_cli():
    """CLI entry point for zone validation"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Economist-style chart zone boundaries",
    )
    parser.add_argument("chart_path", help="Path to chart PNG file")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )

    args = parser.parse_args()

    validator = ZoneBoundaryValidator()
    is_valid, issues = validator.validate_chart(args.chart_path)

    if args.report:
        print(validator.generate_report())
    elif is_valid:
        print(f"✅ {args.chart_path}: All checks PASSED")
    else:
        print(f"❌ {args.chart_path}: {len(issues)} issues found")
        for issue in issues:
            print(f"   • {issue}")

    return 0 if is_valid else 1


if __name__ == "__main__":
    import sys

    sys.exit(validate_chart_cli())
