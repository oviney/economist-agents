---
name: visual-qa
description: Use when validating Economist-style charts for publication. Defines the 5-gate rubric, approved palette, and common failure patterns. Referenced by visual-qa-agent and any pipeline that auto-rejects charts.
---

# Visual QA

## Overview

The visual quality rubric for all charts published through the economist-agents pipeline. Defines what "publication-ready" means for an Economist-style chart: red bar, beige background, inline labels, horizontal-only gridlines, and five layout gates that each must pass before publication.

Consumed by `visual-qa-agent` (via Claude vision) and by `src/crews/stage4_crew.py` (deterministic chart-embed validation). A chart that fails any gate is rejected and the graphics agent is re-queued.

## When to Use

- Reviewing a generated chart image before publication
- Configuring a new graphics agent or chart generation script
- Writing tests for chart output validation
- Defining acceptance criteria for visual design stories

### When NOT to Use

- For article prose quality — that's `economist-writing`
- For data accuracy or source verification — that's `research-sourcing`
- For chart *data structure* (Python dict) — that's the Stage 3 crew spec

## Core Process

### The 5 Gates

Every chart must pass all five gates. A single gate failure rejects the chart.

| Gate | Name | Key checks |
|------|------|-----------|
| 1 | Layout Integrity | Red bar fully visible, title below red bar (≥10px), no text or element overlap, no clipping, source line present |
| 2 | Typography | Title bold + readable, subtitle smaller + gray, axis labels legible, end-of-line data labels visible and non-overlapping |
| 3 | Economist Style | Red bar (#e3120b), warm beige/cream background (not white/gray), horizontal gridlines only (no vertical), no border/frame, approved colour palette |
| 4 | Data Integrity | All data points visible, values reasonable, end-of-line percentage labels present, y-axis starts at zero unless explicitly justified |
| 5 | Export Quality | Sharp (not blurry or pixelated), aspect ratio correct, no rendering artefacts |

### Approved Palette

- **Red bar:** `#e3120b` (or perceptually similar red — not orange, not magenta)
- **Line/bar colours:** navy, burgundy, teal, gold (in that priority order for series 1–4)
- **Background:** warm beige / cream (e.g. `#f5f5e8`) — NOT white, NOT gray
- **Grid:** light gray, horizontal only

### Known Failure Patterns

1. **Title/Red Bar Overlap** — Title text collides with red bar. Increase top padding.
2. **Inline Label/Line Overlap** — Series labels sitting on data lines. Shift label vertically.
3. **Clipped Elements** — Red bar, source line, or labels cut off by figure bounds. Increase figure margins.
4. **Vertical Gridlines** — Economist style uses horizontal gridlines only. Remove vertical.
5. **Legend Box** — Economist uses inline labels, not legend boxes. Remove legend.

### Validation Output

The visual-qa-agent returns a structured JSON result per the gate schema documented in its `## Output Format` section. Each gate entry has `pass: true/false` and `issues: [...]`. `overall_pass` is `true` only when all five gates pass.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "White background looks cleaner" | Economist charts use warm beige; white is out-of-brand and makes them look like generic analytics dashboards |
| "Vertical gridlines help readers track values" | The Economist style deliberately omits them — they add visual noise |
| "A legend is clearer than inline labels at this scale" | Inline labels are brand-mandatory; if the chart is too crowded for inline labels, the chart has too many series |
| "Gate 4 is subjective — just pass it" | Y-axis at zero is an editorial standard that prevents misleading charts; only override with explicit editorial sign-off |

## Red Flags

- A chart is regenerated three times without passing Gate 3 — the colour palette configuration is probably wrong, not just a transient issue
- `overall_pass: true` when any `gate.pass` is `false` — the gate aggregation is broken
- Gate 1 passes but the source line is missing — the layout check is not inspecting the bottom margin
- The approved colour list keeps growing — colour sprawl undermines brand consistency; cap at 6 colours maximum

## Verification

- `visual-qa-agent` runs all five gates on every chart image and emits the JSON result with `overall_pass`
- Stage 4 crew (`src/crews/stage4_crew.py`) gate: chart must be embedded in article before publication validator runs
- Manual spot-check: `python scripts/generate_chart.py --preview` renders a sample chart; verify beige background, red bar, and no legend box
