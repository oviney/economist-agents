# Implementation Plan: Chart Layout Regression Tests

## Overview

Extend the deterministic chart validator so CI catches the five chart-layout
regressions listed in `.github/BACKLOG.md`. Work proceeds in small RED/GREEN
slices and reuses the existing `ZoneBoundaryValidator` boundary.

## Architecture Decisions

- Parse `fig.text()` and `ax.annotate()` calls with `ast` instead of regular
  expressions so multiline calls and nested tuples are handled correctly.
- Keep fixture scripts minimal and pair them with generated synthetic PNGs.
- Correct pixel coordinates so the visual red bar is checked at the top of the
  raster image.
- Rely on the existing CI `pytest tests/` command for automatic discovery.

## Task List

### Phase 1: Regression Contract

- [ ] Add five bad-layout fixture scripts and fixture-backed tests.
  - Acceptance: every documented failure requires its own specific issue.
  - Verify: run the new suite and record RED failures before implementation.
  - Files: `tests/test_chart_layouts.py`, `tests/fixtures/bad_charts/scripts/*`

### Checkpoint: RED

- [ ] Confirm the new suite fails against the current validator for the missing
      behaviors.

### Phase 2: Deterministic Detection

- [ ] Replace regex-only figure-text parsing with AST helpers.
  - Acceptance: title/red-bar intrusion and clipped figure text are detected.
  - Verify: run the relevant parameterized regression cases.
  - Files: `src/quality/visual_qa_zones.py`

- [ ] Add AST-backed annotation validation.
  - Acceptance: on-line labels, low labels, and likely label collisions are
    detected while valid multiline annotations pass.
  - Verify: run the annotation regression cases and multiline positive case.
  - Files: `src/quality/visual_qa_zones.py`

- [ ] Correct raster red-bar coordinates and direct unit fixtures.
  - Acceptance: a top red bar passes and a missing or misplaced red bar fails.
  - Verify: run `tests/test_visual_qa_zones.py`.
  - Files: `src/quality/visual_qa_zones.py`, `tests/test_visual_qa_zones.py`

### Checkpoint: GREEN

- [ ] Run the new suite and existing direct validator tests.
- [ ] Run related chart tests with `MPLBACKEND=Agg`.

### Phase 3: Ship

- [ ] Mark the backlog item complete with files and verification evidence.
- [ ] Run Ruff, formatting, diff hygiene, and repository quality gates.
- [ ] Review the final diff for correctness, architecture, security, and
      performance.
- [ ] Commit, push, and open a PR for human review.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Static checks overclaim runtime precision | Medium | Use issue text such as "likely" and scope the spec to literal script arguments. |
| Existing pixel fixture encodes bottom-row behavior | Medium | Add top-row fixture assertions and update direct tests in the same slice. |
| AST parser misses dynamic expressions | Low | Skip non-literal values rather than producing false positives. |

## Open Questions

None.
