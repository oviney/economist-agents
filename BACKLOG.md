# Backlog

> **Source of record for planning items.** PRs + code review live on GitHub (`gh` CLI).
> Item ids are `B-NNN` and are never reused. The `(was #N)` tag records the GitHub
> issue an item was migrated from (those issues are closed, not deleted).
>
> See `docs/specs/local-backlog-migration.md` for why this file exists.

## Sprint Goal (2026-06-14)

**Clear the backlog: land B-003 → B-002 → B-001 to `main`, one self-contained slice
per session, clearing context between each to prevent session bloat.**

- **Ordering (dependency-driven):** `B-003` (unblocks ADR gate) → `B-002` (test-only,
  independent) → `B-001` (largest; requires routing `import anthropic` out of
  `_shared.py` via `AgentRegistry` to clear the ADR-002 gate before wiring `BLOG_AUTHOR`).
- **Cadence:** spec → **human LGTM** → build/TDD → PR → merge. Stop for LGTM after each
  slice's spec.
- **Session discipline:** one slice per session. On merge, mark Done here, then `/clear`
  before the next slice. This file is the durable handoff — a fresh session resumes from it.
- **"Deployed to production" = merged to `main`** via reviewed PR (no separate runtime deploy).

## In Progress

_(none)_

## Todo

### B-001 · P3 · Wire Stage 4 author safety net to BLOG_AUTHOR constant (was #420)

`type:refactor`.

Follow-up from PR #416 (issue #401). `BLOG_AUTHOR`
(`scripts/publication_validator.py`) is wired into the Stage 3 writer prompt and
the validator's author contract. The Stage 4 frontmatter safety net at
`src/agent_sdk/_shared.py:632` still emits the author as a literal
(`author: "Ouray Viney"`), so it can drift if `BLOG_AUTHOR` changes.

**Why deferred** `_shared.py` carries a pre-existing ADR-002 violation
(`import anthropic` in the vision-refinement helper, ~line 734) that the
arch-review gate blocks on any edit to that file.

**Fix (once unblocked)**
1. Resolve the ADR-002 `anthropic` import (route via AgentRegistry).
2. Import `BLOG_AUTHOR` and interpolate at line 632.
3. The behavioural test in `tests/test_author_contract.py` becomes load-bearing
   against the constant.

## Done

### B-002 · Removed asyncio.run stub in test_flow_agent_sdk.py — 2026-06-14

Slice 2 of the sprint. PR #433 (squash-merged to `main`). Migrated all 9
`asyncio.run`-patching tests across `TestGenerateContent`, `TestRequestRevision`,
and `TestKickoffResultFile` to the `AsyncMock` pattern from `test_flow_image_mode.py`
(PR #424), so the real `asyncio.run` drives the mocked coroutines — clearing the
`RuntimeWarning: coroutine ... was never awaited` class. Whole-file scope (not just
`TestGenerateContent`) so the warning class is fully gone:
`pytest tests/test_flow_agent_sdk.py -W error::RuntimeWarning` → 41 passed, 0 warnings.
The one `asyncio.run`-introspection test was rewritten to assert the `await` directly.
Test-only; `flow.py` untouched. Spec: `docs/specs/B-002-asyncio-run-stub-removal.md`.

### B-003 · Repaired adr-lint gate + ADR governance drift — 2026-06-14

Slice 1 of the sprint. PR #431 (squash-merged to `main`). Restored
`scripts/lint_adrs.py` (was archived, breaking the hook on all `docs/adr/`
changes); ADR-0010 status `Implemented` → `Accepted`; landed ADR-0011 (Opt-In
Recursive Deep Research); added both to `mkdocs.yml` nav. Gate verified on `main`
(11 ADRs validated). Spec: `docs/specs/B-003-adr-lint-governance.md`.
