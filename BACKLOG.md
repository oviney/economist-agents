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

### B-008 · Single canonical slug across article file, chart PNG, and image-prompt sidecar

Low-impact cleanup flagged in the B-006/B-007 code review. The finished article
file is named via `_slug_from_article` (from `title:`) while the chart PNG and
the `output/posts/<slug>.image_prompt.md` sidecar are named via `_slug_for_chart`
(from the `image:` field / topic). In `chart_only` runs these can diverge, so
`foo.md` may sit beside `bar.image_prompt.md`. No functional break (both files
exist; the prompt is also embedded inline), but a single shared slug derivation
would remove the confusion. Also aligns with the validator's title-based
canonical slug.

## Done

### B-006 · Keyless subscription pipeline (claude_web research + chart-embed fixes) — 2026-07-14

Makes the production pipeline generate a validator-passing article with **no paid
API keys** — writer, graphics, research, and vision all run on the Claude
subscription via the Agent SDK (`claude_agent_sdk.query()`). New opt-in
`research_mode="claude_web"` has Claude do its own live web research through the
built-in `WebSearch`/`WebFetch` tools (no Serper; ADR-0012). Vision refinement
rerouted off the `anthropic` client onto `query()` (also clears the ADR-0002
concern in `_shared.py`). New `--image-mode chart_only` CLI path runs end-to-end
(no hero image, no handshake) and writes `output/posts/<slug>.md`; the deprecated
`economist_agent.py` now fails loud with a pointer to the keyless command.
Surfaced + fixed two pre-existing chart-embed bugs found by the real validator:
**BUG-038** (`apply_editorial_fixes` mangled `![...]` image syntax when stripping
`!`) and **BUG-039** (`run_pipeline` chart_only stripped the image slug before
`_auto_embed_chart` could fire). Spec: `docs/specs/B-006-keyless-subscription-pipeline.md`;
plan: `tasks/plan.md`; runbook: `docs/keyless-pipeline-runbook.md`. Deterministic
+ tested (keyless, mocked SDK); behavioural proof is a live subscription run
(Checkpoint B).

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
