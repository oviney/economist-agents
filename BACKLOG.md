# Backlog

> **Source of record for planning items.** PRs + code review live on GitHub (`gh` CLI).
> Item ids are `B-NNN` and are never reused. The `(was #N)` tag records the GitHub
> issue an item was migrated from (those issues are closed, not deleted).
>
> See `docs/specs/local-backlog-migration.md` for why this file exists.

## In Progress

_(none)_

## Todo

### B-003 · P3 · Broken adr-lint pre-commit hook + ADR governance drift (was #428)

Blocks new ADRs. `type:refactor`.

The `adr-lint` pre-commit hook (`.pre-commit-config.yaml:64`) runs
`.venv/bin/python scripts/lint_adrs.py`, but that script was archived to
`scripts/archived/lint_adrs.py` (ADR-0010 scripts→src migration), so the hook
fails with `can't open file '.../scripts/lint_adrs.py'` on **any** change under
`docs/adr/`. New ADRs cannot be committed through the gate.

Running the archived copy from the repo root also surfaces **pre-existing
non-compliance** the broken hook had been masking:
- `docs/adr/0010-scripts-to-src-migration.md`: status `Implemented` is not in the
  allowed set (`Accepted/Deprecated/Proposed/Rejected/Superseded`).
- `docs/adr/0010-...` is not referenced in `mkdocs.yml`.

(The archived script's `repo_root` default is `Path(__file__).parent.parent`,
which resolves to `scripts/` from `scripts/archived/` — so it must run with
`--repo-root` or be restored to `scripts/`.)

**Fix**
1. Restore `scripts/lint_adrs.py` (or repoint the hook + fix the `repo_root`
   default for the archived location).
2. Bring ADR-0010 into compliance (status → `Accepted`; add to `mkdocs.yml`).
3. Land **ADR-0011 (Deep Research)** — documents the #390 decision; rationale
   currently lives in `docs/specs/390-deep-research.md`. Draft below (was inlined
   from closed issue #428 so it survives locally):

   > **ADR-0011: Opt-In Recursive Deep Research**
   > **Status:** Accepted · **Date:** 2026-06-13 · **Decision Maker:** Ouray Viney (Engineering Lead)
   >
   > **Context:** The research phase (`build_research_brief`) is a one-shot,
   > deterministic, no-LLM search burst. #390 adds a recursive
   > planner→search→extract→synthesise loop (Deep Research pattern) that produces
   > report-grade briefs at 5–10× cost ($1.50–3.00 vs ~$0.30), 30–60s vs ~5s, and
   > introduces LLM calls into a path kept deterministic to prevent source hallucination.
   >
   > **Decision:** Add Deep Research as **opt-in**, not a replacement. `research_mode`
   > (`deterministic` default | `deep`, `RESEARCH_MODE` env override) on
   > `run_stage3`/`run_pipeline`. New `src/agent_sdk/research/` package reusing the
   > existing providers. Bounded by a hard iteration cap (2) and `research_budget_usd`
   > ($2.50). Model tiering: planner/synthesizer Sonnet, extractor Haiku. Brief keeps
   > the same string contract (writer + stat audit unchanged); research spend recorded
   > in the cost log.
   >
   > **Consequences:** + Report-grade briefs on demand without sacrificing the cheap
   > default; bounded, observable cost. − Non-deterministic and expensive when opted
   > in; v1 extracts from snippets only (full-page fetch deferred). Follow-ups:
   > production trigger for `deep`, cross-article cache, full-page fetch.
   >
   > **References:** Issue #390; spec `docs/specs/390-deep-research.md`; companion #389.

### B-002 · P3 · Remove asyncio.run stub in test_flow_agent_sdk.py (was #425)

Residual coroutine warnings. `type:refactor`.

Surfaced by the PR #424 review. `tests/test_flow_agent_sdk.py` (the
`TestGenerateContent` cases) patch `flow.asyncio.run` to a no-op stub, which
leaves `run_pipeline()` coroutines un-awaited and emits
`RuntimeWarning: coroutine ... was never awaited` — the defect class commit
236cd48 set out to resolve.

`tests/test_flow_image_mode.py` was already migrated (PR #424) to patch
`run_pipeline`/`refine_image_metadata` as `AsyncMock` and let the real
`asyncio.run` drive them — no warnings.

**Fix** Migrate the remaining `TestGenerateContent` tests to the same `AsyncMock`
pattern so the un-awaited-coroutine warnings stop masking a potential future real leak.

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

_(append completed items here with an ISO completion date, e.g. `YYYY-MM-DD`)_
