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

_(none — sprint backlog cleared 2026-06-14: B-003 → B-002 → B-001 all merged)_

## Done

### B-005 · Writer word-count contract (single source of truth + structured prompt) — 2026-07-14

Follow-up from B-004. Short drafts (< 700 words) were the one remaining
un-fixable-by-finalize quarantine cause. Consolidated the drifted word-count
thresholds into `WORD_COUNT_MIN/TARGET/MAX` constants in `publication_validator.py`
(the docstring had claimed 800 while the code enforced 700), routed
`_check_word_count` + the new pure `word_count_shortfall`/`_body_word_count`
helpers through the single source of truth, and rewrote the `stage3_runner` writer
prompt into a structured per-section budget (~850 across 3-4 sections, aligned to
the heading cap) that imports the constants so it can never drift below the floor.
700 floor unchanged (consolidation, not re-tuning). Shipped in **PR #443**
(squash-merged to `main` as `ed0453f`, alongside B-004). Behavioural proof (real
drafts clear the target) is an explicit live-run step — not verifiable in an
API-key-less CI. Spec: `docs/specs/B-005-writer-word-count-contract.md`.

### B-004 · Deterministic frontmatter finalize so mechanical defects never quarantine — 2026-07-14

Defect **BUG-038**. The pipeline quarantined an otherwise-publishable article
(`generation.log`) for a single mechanically-fixable `DATE_MISMATCH`, after LLM
regeneration destroyed the frontmatter. Hardened
`src/agent_sdk/_shared.py:apply_editorial_fixes` to guarantee a complete, valid
frontmatter block when a finalize `current_date` is supplied (reconstruct a missing
block with the H1 as title, stamp today's date, fill categories/description and an
EMPTY chart-only `image:` — a default hero is itself a CRITICAL), and wired that
finalizer into the deprecated `scripts/economist_agent.py` before validation.
Word-count left to B-005. Shipped in **PR #443** (squash-merged to `main` as
`ed0453f`). A Copilot review caught a real image-fallback regression, fixed
pre-merge. Spec: `docs/specs/B-004-frontmatter-finalize.md`.

### B-001 · Wired Stage 4 author safety net to BLOG_AUTHOR — 2026-06-14

Slice 3 (final) of the sprint. PR #435 (squash-merged to `main`). The Stage 4
frontmatter safety net (`src/agent_sdk/_shared.py`) hard-coded the author as the
literal `"Ouray Viney"`; it now interpolates `BLOG_AUTHOR`
(`scripts/publication_validator.py`) via a lazy import, making the constant the
single source of truth across the Stage 3 prompt, Stage 4 safety net, and the
validator's author contract. Editing `_shared.py` was blocked by a pre-existing
ADR-002 violation (`import anthropic` in the vision helper); cleared by adding
`create_async_anthropic_client()` to the exception-listed `scripts/llm_client.py`
factory and routing `refine_image_metadata` through it (no behaviour change — the
factory's lazy `from anthropic import AsyncAnthropic` keeps existing
`patch("anthropic.AsyncAnthropic")` tests valid). Added a load-bearing regression
that monkeypatches `BLOG_AUTHOR` at its source and asserts the new value flows
into the frontmatter (fails if reverted to a literal). Full suite: 2410 passed.
Spec: `docs/specs/B-001-blog-author-safety-net.md`.

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
