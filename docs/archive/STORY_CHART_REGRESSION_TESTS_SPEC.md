# Spec: Chart Layout Regression Tests

## Objective

Add deterministic regression coverage for the five documented Economist-style
chart layout failures in `.github/BACKLOG.md`:

1. title/red-bar overlap;
2. inline label directly on a data line;
3. inline label intruding into the X-axis zone;
4. label-to-label overlap; and
5. clipped figure text at chart edges.

The checks run before LLM-based visual QA. They must stay offline, fast, and
deterministic so CI can reject known bad chart scripts without image-model
calls.

## Tech Stack

- Python 3.11+
- Pytest
- `ast` from the Python standard library
- Pillow and NumPy for existing pixel-level checks
- `src.quality.visual_qa_zones.ZoneBoundaryValidator`

## Commands

- Baseline: `MPLBACKEND=Agg .venv/bin/python -m pytest tests/test_visual_qa_zones.py -q`
- RED/GREEN suite: `MPLBACKEND=Agg .venv/bin/python -m pytest tests/test_chart_layouts.py tests/test_visual_qa_zones.py -q`
- Related chart suite: `MPLBACKEND=Agg .venv/bin/python -m pytest tests/test_chart_layouts.py tests/test_visual_qa_zones.py tests/test_generate_chart.py -q`
- Lint: `.venv/bin/ruff check src/quality/visual_qa_zones.py tests/test_chart_layouts.py tests/test_visual_qa_zones.py tests/fixtures/bad_charts/scripts`
- Format: `.venv/bin/ruff format --check src/quality/visual_qa_zones.py tests/test_chart_layouts.py tests/test_visual_qa_zones.py tests/fixtures/bad_charts/scripts`

## Project Structure

- `src/quality/visual_qa_zones.py`: deterministic chart script and pixel checks
- `tests/test_chart_layouts.py`: fixture-backed regression suite
- `tests/fixtures/bad_charts/scripts/`: minimal scripts for known failures
- `tests/test_visual_qa_zones.py`: direct validator unit tests
- `.github/BACKLOG.md`: backlog status and verification evidence

## Code Style

Use small AST extraction helpers and explicit issue messages:

```python
if abs(offset_x) <= 2 and abs(offset_y) <= 2:
    issues.append(
        f"Inline label '{label}' has near-zero xytext offset; "
        "it will overlap data line",
    )
```

## Testing Strategy

Create synthetic top-red-bar PNGs and pair them with small fixture scripts.
`ZoneBoundaryValidator.validate_chart()` locates the matching script and
reports a specific issue for each documented layout failure. Keep existing
filename, CLI, and optional pixel-validation tests passing. Add a positive
multiline-annotation case because production chart scripts use multiline
`ax.annotate()` calls.

## Boundaries

- Always: keep checks offline and deterministic; parse Python with `ast`; run
  RED before implementation and GREEN after each slice.
- Ask first: add dependencies, change the chart generation API, or alter CI
  workflow configuration.
- Never: require network credentials or image-model calls; weaken existing
  filename, CLI, or pixel checks.

## Success Criteria

- Each of the five known bad layouts has a fixture-backed failing regression.
- Each fixture produces a specific detector issue, not an incidental failure.
- Multiline annotations with valid offsets do not produce false positives.
- Pixel checks validate that the red bar occupies the top 4% of the image.
- Existing direct validator and related chart tests pass.
- Ruff, formatting, and repository quality gates pass.

## Open Questions

None. This slice intentionally analyzes literal Matplotlib script arguments.
Dynamic runtime layout analysis remains outside the backlog item.
