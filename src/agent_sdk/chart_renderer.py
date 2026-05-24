"""Render Economist-style charts from Stage 3 chart specs.

The Stage 3 graphics LLM produces a JSON spec describing a chart;
this module turns that spec into a PNG. Deterministic, matplotlib-only —
no LLM call, no API key, no per-run cost.

Public surface
--------------
ChartRenderError
    Raised when the spec is malformed or matplotlib fails.

render_chart(spec: dict, output_path: Path) -> Path
    Render a horizontal-bar chart to *output_path*. Returns the
    written path. Auto-creates parent directories.

Spec contract
-------------
::

    {
        "title": str,                 # required, non-empty
        "subtitle": str,              # optional
        "data": [                     # required, non-empty list
            {
                "metric": str,        # required per item
                "value": float|int,   # required per item, numeric
                "unit": str,          # optional (rendered in label)
                "color": str,         # optional: "navy" | "red" | hex
            }, ...
        ],
        "source": str,                # optional, shown bottom-left
    }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Lazy matplotlib import — matplotlib pulls in numpy + tk and adds ~1s to
# every module import. Push that cost to render-time so tests that don't
# render don't pay it.

# Economist palette (matches scripts/generate_chart.py).
_NAVY = "#17648d"
_RED = "#e3120b"
_BURGUNDY = "#843844"
_BG_COLOR = "#f1f0e9"
_GRAY_TEXT = "#666666"
_GRID_COLOR = "#cccccc"

_NAMED_COLORS: dict[str, str] = {
    "navy": _NAVY,
    "red": _RED,
    "burgundy": _BURGUNDY,
    "gray": _GRAY_TEXT,
    "grey": _GRAY_TEXT,
}


class ChartRenderError(ValueError):
    """Spec is malformed, or matplotlib failed to render."""


def _resolve_color(name: str | None) -> str:
    """Map spec color name to a hex value; passthrough if already hex."""
    if not name:
        return _NAVY
    if name.startswith("#"):
        return name
    return _NAMED_COLORS.get(name.lower(), _NAVY)


def _validate_spec(spec: Any) -> None:
    """Reject any spec that would crash matplotlib partway through render."""
    if not isinstance(spec, dict):
        raise ChartRenderError(f"spec must be a dict, got {type(spec).__name__}")
    title = spec.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ChartRenderError("spec.title is required and must be a non-empty string")
    data = spec.get("data")
    if not isinstance(data, list) or not data:
        raise ChartRenderError("spec.data is required and must be a non-empty list")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ChartRenderError(f"spec.data[{i}] must be a dict")
        if not isinstance(item.get("metric"), str) or not item["metric"].strip():
            raise ChartRenderError(f"spec.data[{i}].metric is required")
        value = item.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ChartRenderError(
                f"spec.data[{i}].value must be numeric, got {type(value).__name__}"
            )


def render_chart(spec: dict, output_path: Path) -> Path:
    """Render *spec* to a PNG at *output_path*.

    Args:
        spec: Chart spec matching the contract documented at module top.
        output_path: Destination PNG path. Parent directories are created
            if missing.

    Returns:
        The resolved output path.

    Raises:
        ChartRenderError: spec is malformed or matplotlib raises.
    """
    _validate_spec(spec)

    import matplotlib

    matplotlib.use("Agg")  # headless backend
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = spec["title"]
    subtitle = spec.get("subtitle", "")
    source = spec.get("source", "")
    data = spec["data"]

    metrics = [item["metric"] for item in data]
    values = [float(item["value"]) for item in data]
    colors = [_resolve_color(item.get("color")) for item in data]
    unit = data[0].get("unit", "")  # use first item's unit for axis label

    # 1200×800 PNG — figsize 12×8 inches at 100 dpi gives exactly that.
    fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
    try:
        fig.patch.set_facecolor(_BG_COLOR)
        ax.set_facecolor(_BG_COLOR)

        # Economist top-of-chart red rule (signature visual).
        fig.add_artist(
            plt.Rectangle(
                (0.06, 0.93), 0.04, 0.012, color=_RED, transform=fig.transFigure
            )
        )

        y_pos = list(range(len(metrics)))
        ax.barh(y_pos, values, color=colors, height=0.6, edgecolor=_BG_COLOR)

        # Inline value labels at end of each bar.
        max_val = max(values) if values else 0
        label_offset = max_val * 0.01 if max_val else 0.1
        for y, v in zip(y_pos, values, strict=True):
            label = f"{v:g}{(' ' + unit) if unit else ''}"
            ax.text(
                v + label_offset,
                y,
                label,
                va="center",
                ha="left",
                fontsize=10,
                color=_GRAY_TEXT,
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(metrics, fontsize=11, color="black")
        ax.invert_yaxis()  # first metric on top — newspaper convention

        # X axis: minimal — just a baseline grid for reference.
        ax.tick_params(axis="x", colors=_GRAY_TEXT, labelsize=9)
        ax.grid(axis="x", color=_GRID_COLOR, linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)

        # Strip the chart-area frame; keep only the bottom rule.
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(_GRID_COLOR)

        # Title + subtitle stacked above the chart, aligned with the red rule.
        fig.text(0.06, 0.88, title, fontsize=18, fontweight="bold", color="black")
        if subtitle:
            fig.text(0.06, 0.84, subtitle, fontsize=11, color=_GRAY_TEXT)

        # Source line at bottom-left, also aligned with the red rule.
        if source:
            fig.text(0.06, 0.03, f"Source: {source}", fontsize=9, color=_GRAY_TEXT)

        plt.subplots_adjust(left=0.22, right=0.95, top=0.78, bottom=0.10)
        fig.savefig(output_path, dpi=100, facecolor=_BG_COLOR)
    except Exception as exc:
        raise ChartRenderError(f"matplotlib render failed: {exc}") from exc
    finally:
        plt.close(fig)

    return output_path
