"""Tests for src/agent_sdk/chart_renderer.py (#403 slice 1)."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from src.agent_sdk.chart_renderer import ChartRenderError, render_chart


def _valid_spec() -> dict:
    """Mirrors the shape Stage 3's graphics LLM produces (see
    logs/spike/pipeline_chart.json from the 2026-05-18 run)."""
    return {
        "title": "The Shrinking Squad",
        "subtitle": "Typical product team composition, full-time human roles per squad",
        "data": [
            {"metric": "Product Manager", "value": 1, "unit": "role", "color": "navy"},
            {"metric": "Designer", "value": 1, "unit": "role", "color": "navy"},
            {"metric": "Tech Lead", "value": 1, "unit": "role", "color": "navy"},
            {"metric": "Junior PM", "value": 0, "unit": "role", "color": "red"},
        ],
        "source": "Department of Product, 2025",
    }


def _mixed_scale_spec() -> dict:
    """The exact flaky-tests failure (B-014): five percentages plus a raw
    150,000 count on one linear axis — the count (mislabelled '%') swallowed the
    scale and the headline 84% collapsed to an invisible sliver."""
    return {
        "title": "The Invisible Payroll Tax",
        "subtitle": "Cost of flaky tests, selected industrial studies",
        "data": [
            {"metric": "Google CI signal skewed", "value": 84, "unit": "%"},
            {"metric": "Jira frontend build failures", "value": 21, "unit": "%"},
            {"metric": "Total productive dev time", "value": 2.5, "unit": "%"},
            {"metric": "Dev time repairing", "value": 1.3, "unit": "%"},
            {"metric": "Dev time investigating", "value": 1.1, "unit": "%"},
            {"metric": "Atlassian dev-hours/yr", "value": 150000, "unit": "%"},
        ],
    }


def test_values_spanning_many_orders_of_magnitude_are_rejected() -> None:
    """B-014 Prove-It: a spec whose values span too many orders of magnitude for
    one linear axis must be rejected before render — not silently produce a chart
    where the small values are invisible."""
    with pytest.raises(ChartRenderError, match="orders of magnitude|one .*axis|coherent"):
        render_chart(_mixed_scale_spec(), Path("/tmp/should-not-be-written.png"))


def test_normal_scale_spec_still_renders(tmp_path: Path) -> None:
    """Guard rail: a spec whose values are within a sane range is unaffected."""
    out = tmp_path / "ok.png"
    render_chart(_valid_spec(), out)  # values 0..1 — well within span
    assert out.exists()


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Read width, height from a PNG header without depending on Pillow.

    PNG byte layout (per RFC 2083):
      bytes 0-7   = signature
      bytes 8-15  = IHDR chunk length + type
      bytes 16-23 = width (big-endian uint32), height (big-endian uint32)
    """
    with path.open("rb") as f:
        header = f.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
    width, height = struct.unpack(">II", header[16:24])
    return width, height


# ── valid render path ────────────────────────────────────────────────


def test_valid_spec_writes_png_to_output_path(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    result = render_chart(_valid_spec(), out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_rendered_png_has_expected_1200x800_dimensions(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    render_chart(_valid_spec(), out)
    w, h = _png_dimensions(out)
    # Spec contract: 1200×800 (figsize 12×8 in @ 100 dpi).
    assert (w, h) == (1200, 800), f"expected 1200×800, got {w}×{h}"


def test_output_dir_auto_created(tmp_path: Path) -> None:
    out = tmp_path / "deeply" / "nested" / "charts" / "x.png"
    render_chart(_valid_spec(), out)
    assert out.exists()


def test_subtitle_and_source_are_optional(tmp_path: Path) -> None:
    spec = _valid_spec()
    del spec["subtitle"]
    del spec["source"]
    out = tmp_path / "chart.png"
    render_chart(spec, out)
    assert out.exists()


def test_unit_omitted_when_missing(tmp_path: Path) -> None:
    spec = _valid_spec()
    for item in spec["data"]:
        item.pop("unit", None)
    out = tmp_path / "chart.png"
    render_chart(spec, out)  # must not crash on missing unit
    assert out.exists()


def test_unknown_color_name_falls_back_to_navy(tmp_path: Path) -> None:
    spec = _valid_spec()
    spec["data"][0]["color"] = "chartreuse"  # not in the named palette
    out = tmp_path / "chart.png"
    render_chart(spec, out)
    assert out.exists()


def test_hex_color_passthrough(tmp_path: Path) -> None:
    spec = _valid_spec()
    spec["data"][0]["color"] = "#0066cc"
    out = tmp_path / "chart.png"
    render_chart(spec, out)
    assert out.exists()


# ── malformed spec rejection ─────────────────────────────────────────


def test_non_dict_spec_raises(tmp_path: Path) -> None:
    with pytest.raises(ChartRenderError, match="must be a dict"):
        render_chart("not a dict", tmp_path / "x.png")  # type: ignore[arg-type]


def test_missing_title_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    del spec["title"]
    with pytest.raises(ChartRenderError, match="title"):
        render_chart(spec, tmp_path / "x.png")


def test_empty_title_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    spec["title"] = "   "
    with pytest.raises(ChartRenderError, match="title"):
        render_chart(spec, tmp_path / "x.png")


def test_missing_data_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    del spec["data"]
    with pytest.raises(ChartRenderError, match="data"):
        render_chart(spec, tmp_path / "x.png")


def test_empty_data_list_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    spec["data"] = []
    with pytest.raises(ChartRenderError, match="non-empty list"):
        render_chart(spec, tmp_path / "x.png")


def test_non_numeric_value_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    spec["data"][0]["value"] = "lots"
    with pytest.raises(ChartRenderError, match="numeric"):
        render_chart(spec, tmp_path / "x.png")


def test_boolean_value_raises(tmp_path: Path) -> None:
    # bool is a subclass of int in Python — easy to misclassify as numeric.
    spec = _valid_spec()
    spec["data"][0]["value"] = True
    with pytest.raises(ChartRenderError, match="numeric"):
        render_chart(spec, tmp_path / "x.png")


def test_missing_metric_in_data_item_raises(tmp_path: Path) -> None:
    spec = _valid_spec()
    del spec["data"][1]["metric"]
    with pytest.raises(ChartRenderError, match="metric"):
        render_chart(spec, tmp_path / "x.png")
