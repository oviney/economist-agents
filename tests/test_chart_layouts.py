"""Regression tests for known chart layout failures."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src.quality.visual_qa_zones import ZoneBoundaryValidator

FIXTURE_SCRIPTS = Path("tests/fixtures/bad_charts/scripts")
BG_COLOR = (241, 240, 233)
RED_BAR = (227, 49, 11)


def _write_chart_image(path: Path) -> None:
    """Create a minimal Economist-coloured PNG for validator pixel checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (800, 550), BG_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 800, 22), fill=RED_BAR)
    image.save(path)


def _copy_fixture_script(tmp_path: Path, name: str) -> Path:
    root = tmp_path / "bad_charts"
    scripts_dir = root / "scripts"
    images_dir = root / "images"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    source = FIXTURE_SCRIPTS / f"{name}.py"
    target = scripts_dir / source.name
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    image_path = images_dir / f"{name}.png"
    _write_chart_image(image_path)
    return image_path


@pytest.mark.parametrize(
    ("fixture_name", "expected_issue"),
    [
        ("title-red-bar-overlap", "RED BAR"),
        ("inline-label-on-line", "overlap data"),
        ("inline-label-x-axis-zone", "X-axis zone"),
        ("label-to-label-overlap", "Label-to-label overlap"),
        ("clipped-elements", "clipped"),
    ],
)
def test_known_bad_chart_layouts_are_detected(
    tmp_path: Path,
    fixture_name: str,
    expected_issue: str,
) -> None:
    """Every documented bad chart pattern must fail deterministic QA."""
    chart_path = _copy_fixture_script(tmp_path, fixture_name)

    is_valid, issues = ZoneBoundaryValidator().validate_chart(str(chart_path))

    assert not is_valid
    assert any(expected_issue in issue for issue in issues), issues


def test_multiline_annotations_with_offsets_are_not_flagged_as_missing(
    tmp_path: Path,
) -> None:
    """Project chart scripts use multi-line annotate calls and should parse cleanly."""
    root = tmp_path / "good_charts"
    scripts_dir = root / "scripts"
    images_dir = root / "images"
    scripts_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    (scripts_dir / "good-multiline.py").write_text(
        """
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.annotate(
    "High series",
    xy=(2024, 78),
    xytext=(-50, 15),
    textcoords="offset points",
)
ax.annotate(
    "End label",
    xy=(2025, 80),
    xytext=(10, 0),
    textcoords="offset points",
)
ax.annotate(
    "Low series",
    xy=(2021, 8),
    xytext=(0, 18),
    textcoords="offset points",
)
fig.text(0.08, 0.90, "Clean title")
""".strip(),
        encoding="utf-8",
    )
    image_path = images_dir / "good-multiline.png"
    _write_chart_image(image_path)

    _is_valid, issues = ZoneBoundaryValidator().validate_chart(str(image_path))

    assert not any("missing xytext offset" in issue for issue in issues), issues
    assert not any("overlap data line" in issue for issue in issues), issues
    assert not any("X-axis zone" in issue for issue in issues), issues
