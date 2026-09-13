# Spec: B-014 · Chart redesign — fix the graphics-stage correctness bug + dataviz styling

> Backlog: **B-014** (`type:bug`+`feature`). Prototype: the before/after
> established both the defect and the fix. Triage: `docs/ideas/tooling-adoption.md`.

## Objective

The graphics stage produces **charts that misrepresent the data** — the
flaky-tests chart plotted five percentages (84%, 21%, …) and one raw count
(150,000) on **one linear axis**, so the count swallowed the scale and the
article's headline finding (84%) collapsed to an invisible sliver; the count was
also mislabeled "150000 %". This is a correctness bug, not just ugliness. Fix the
**spec the graphics agent generates** (root cause) and bring **validated,
colorblind-safe styling** into the matplotlib renderer.

## Assumptions

1. **Root cause is the spec, not the renderer.** No renderer can rescue a
   mixed-unit spec. The highest-leverage fix is the graphics-agent *prompt*:
   one axis, one coherent measure tied to the thesis, correct units,
   form-follows-job. (These are the `dataviz` "choosing a form / one axis" rules.)
2. **Keep matplotlib PNG output.** The blog embeds static PNGs; switching to
   SVG/interactive charts is out of scope (over-engineering for a static blog).
3. The `dataviz` palette validator (`scripts/validate_palette.js`) is the source
   of truth for colors — validated pairs already exist: light `#b8352c`/`#2f6f9f`,
   dark `#cc5546`/`#3f8fcf`.

## Scope

**In:**
- **Graphics-agent prompt** (`GRAPHICS_AGENT_PROMPT` in `_shared.py`): forbid
  mixing units on one chart; require one coherent measure that advances the
  article's thesis; require correct unit labels; prefer a single clear form over
  cramming.
- **Spec guard** in `chart_renderer.py`'s validation: reject a spec whose `data`
  mixes incommensurable units (e.g. a `%` item beside a raw-count item) — fail
  loudly so a bad spec never renders a misleading chart.
- **Validated styling** in `chart_renderer.py`: use the dataviz-validated palette
  (colorblind-safe), the mark specs (rounded data-ends, recessive grid, direct
  labels, 2px gaps), and correct unit rendering.
- Update the chart-embed reference so prose still references the (now single,
  clear) chart.

**Out:**
- SVG / interactive / HTML charts (static PNG stays).
- A full charting-library swap.
- Re-generating already-published charts (applies going forward).

## Commands

```bash
# Render a spec to a PNG (existing entry):
python -c "from src.agent_sdk.chart_renderer import render_chart; ..."
# Validate a candidate palette (dataviz skill, run as an ESM package):
node scripts/validate_palette.js "#b8352c,#2f6f9f" --mode light --surface "#f7f5f1"
pytest tests/test_chart_renderer.py tests/test_chart_embed_regressions.py -q
```

## Code Style

```python
# chart_renderer._validate_spec — reject mixed units (BUG: 84% next to 150000)
units = {item.get("unit", "").strip() for item in data}
pctish = {"%", "percent", "pct"}
if units & pctish and any(u not in pctish for u in units if u):
    raise ChartRenderError(
        "spec.data mixes percentages with non-percentage units on one axis — "
        "pick one coherent measure (see dataviz: one axis, one measure)"
    )
```

## Testing Strategy

- **TDD (Prove-It):** a regression test feeding the *exact* broken spec
  (percentages + a 150000 count) asserts `ChartRenderError` — RED on today's
  code, GREEN after the guard.
- Renderer tests assert the validated palette hexes and correct unit labels.
- Manual: regenerate the flaky-tests chart; confirm it's the single clear
  proportion, not the mixed-unit mess.

## Boundaries

- **Always:** validate any new palette with `validate_palette.js` before use;
  keep PNG output.
- **Ask first:** removing the chart entirely from an article; changing the
  chart's position/embed contract.
- **Never:** ship a chart that mixes units on one axis; hand-pick colors without
  running the validator; switch to SVG/interactive under this item.

## Success Criteria

1. The graphics-agent prompt forbids mixed units and requires a thesis-aligned
   single measure + correct unit labels.
2. `chart_renderer` rejects a mixed-unit spec (regression test proves it).
3. Charts render with the dataviz-validated, colorblind-safe palette + mark specs.
4. A regenerated flaky-tests chart is a single clear proportion, correctly
   labeled. `make ci-local` green.

## Open Questions

- Whether the graphics agent should emit a `form` hint (bar / proportion / stat)
  so the renderer can pick the mark — or keep it bar-only for now. (Lean: keep
  bar-only for MVP; add proportion as a fast-follow.)
