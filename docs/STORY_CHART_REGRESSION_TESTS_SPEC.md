# Spec: Chart Regression Tests

## Objective
Add automated regression coverage for five known Economist-style chart layout failures: title/red bar overlap, inline label directly on a data line, inline label intruding into the X-axis zone, label-to-label overlap, and clipped elements at the edge. The tests should exercise the deterministic Visual QA zone validator rather than requiring an LLM vision call.

## Tech Stack
- Python 3.13
- Pytest
- `scripts.visual_qa_zones.ZoneBoundaryValidator`
- Lightweight fixture scripts under `tests/fixtures/bad_charts/scripts/`

## Commands
- Red/green targeted test: `.venv/bin/pytest tests/test_chart_layouts.py -q`
- Related validator test: `.venv/bin/pytest tests/test_chart_layouts.py tests/test_quality_system.py -q`
- Lint touched Python: `.venv/bin/ruff check scripts/visual_qa_zones.py tests/test_chart_layouts.py`

## Project Structure
- `tests/test_chart_layouts.py` - regression tests for known bad chart layouts
- `tests/fixtures/bad_charts/scripts/` - minimal bad chart generation snippets
- `scripts/visual_qa_zones.py` - deterministic detection logic

## Code Style
Tests should assert named layout failures are detected by behavior, not by private helper implementation:

```python
is_valid, issues = ZoneBoundaryValidator().validate_chart(".../title-red-bar-overlap.png")
assert not is_valid
assert any("Title" in issue and "RED BAR" in issue for issue in issues)
```

## Testing Strategy
Use generated temporary PNG files with matching fixture scripts. `ZoneBoundaryValidator.validate_chart()` locates the corresponding script and runs code-level checks while keeping pixel checks deterministic.

## Boundaries
- Always: keep tests offline and deterministic; avoid LLM calls.
- Ask first: adding image-comparison dependencies or changing chart generation API.
- Never: weaken existing visual QA checks, remove existing quality-system pseudo-regression tests, or require network/API credentials.

## Success Criteria
- Each of the five known bugs has a fixture-backed regression test.
- `ZoneBoundaryValidator` reports a specific issue for each known bad fixture.
- Targeted tests and lint pass.
