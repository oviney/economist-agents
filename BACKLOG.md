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

### B-012 · Opt-in `deep-brief` research mode (spec'd — prototype validated)

Wire the `deep-research` harness as an **opt-in** research path for flagship
posts; `claude_web` stays the everyday default. **Prototype (2026-07-22) settled
it:** dramatically better sourcing — 19 claims each surviving a 3-0 verification
vote, and it *refuted the walked-back Accenture Copilot numbers* a single-pass
researcher would ship — but one topic cost ~102 agents / ~2M tokens / ~15 min and
**hit the session limit**. So: opt-in, not default. Spec:
`docs/specs/B-012-deep-brief-research-mode.md`. Prototype output (a real verified
brief) lives at `docs/research/ai-productivity-brief.md`.

### B-014 · Chart redesign — fix graphics-stage correctness bug + dataviz styling (spec'd)

The graphics stage produces charts that **misrepresent the data** — the
flaky-tests chart mixed five percentages with a raw 150,000 count on one axis
(headline 84% vanished; count mislabeled "150000 %"). Fix the graphics-agent spec
(one axis / one measure / correct units / form-follows-job) + bring
dataviz-validated colorblind-safe palettes + mark specs into `chart_renderer.py`
(matplotlib PNG kept; **not** an SVG/interactive switch). Prototype before/after
proved the defect and the fix; palettes already validated. Spec:
`docs/specs/B-014-chart-redesign.md`.

### B-013 · Live unlisted draft review on GitHub Pages (candidate — gated on leak test)

Review generated drafts as the *rendered* post at an obscure, `noindex`, live
`/review/<slug>-<token>/` URL (real theme, reviewable from a phone) instead of a
GitHub PR diff; promote to `_posts/` via `make publish`. One-pager:
`docs/ideas/live-draft-review.md`. **Gate:** 10-minute leak test — deploy one
draft and confirm the minimal-mistakes theme surfaces it in *none* of
homepage/archives/feed/sitemap. Not yet spec'd.

### B-009 · Retire paid-AI GitHub Actions (Track A)

Executes [ADR-0014](docs/adr/0014-retire-paid-github-actions-generation.md).
Spec: `docs/specs/B-009-retire-paid-github-actions.md` (see the **T1 re-spec
banner** — this item was split after the fail-fast run). Four workflows inject
paid-AI secrets, contradicting CLAUDE.md #5 and ADR-0013; the weekly
`content-pipeline.yml` cron has failed 8 runs straight (no live article since
2026-04-27). This item **removes the paid + broken + misleading machinery**. It
does *not* claim a working keyless command — that is B-010.

Scope:
- Delete `.github/workflows/content-pipeline.yml` (scheduled paid generation),
  `.github/workflows/regenerate-image.yml` (DALL-E — violates CLAUDE.md #1/#4),
  and `.github/workflows/remediation-sync.yml` (its cron triggers the deleted
  content pipeline — would fail post-merge).
- Strip `OPENAI_API_KEY` from `.github/workflows/ci.yml` (tests mock APIs, so
  inert — **verify a green CI run**, don't assume).
- `.github/workflows/blog-quality-audit.yml`: strip the vestigial
  `OPENAI_API_KEY` **and remove its cron** (keep `workflow_dispatch`); its
  weekly scan re-spams the blog via a `state=open`-only dedup bug.
- Correct the false/stale run docs: CLAUDE.md's `OPENAI_API_KEY | DALL-E 3` env
  row; README's Serper line, env table, and Usage block. Point README/CLAUDE.md
  at the runbook. **Do not** assert `flow.py` is the keyless command (it isn't —
  BUG-046). Where a canonical keyless command is needed, mark it "in repair
  (B-010)" rather than document a command that produces no article.

Acceptance:
- `grep -rE "ANTHROPIC_API_KEY|OPENAI_API_KEY|SERPER_API_KEY" .github/workflows/`
  → empty; no remaining workflow references a deleted one.
- Remaining GitHub Actions (tests/lint/docs) pass with no paid secrets present.
- No run doc advertises Serper, a required `ANTHROPIC_API_KEY`, or DALL-E; none
  claims `flow.py` as a working keyless command.

Out of scope: fixing keyless generation (→ B-010); any unattended/scheduled
replacement (see ADR-0014 "Revisit if").

### B-010 · Fix keyless generation so a local run produces an article + blog PR (Track B)

> **✅ ACCEPTANCE GATE MET (2026-07-21).** A keyless run
> (`pipeline.py … --research-mode claude_web` → `deploy_to_blog`) produced a
> publish-valid article and opened **oviney/blog PR #1156** — the first article
> since 2026-04-27. Fixes BUG-047/048/049/050/051 (all now `fixed` in the
> tracker). BUG-046 resolved-by-workaround (two-step skips paid discovery);
> making `EconomistContentFlow` discovery keyless remains a future enhancement.

Split out of B-009 by the T1 fail-fast run (2026-07-21). The keyless generator
*runs* on the subscription but cannot yet produce a publishable article
end-to-end. Delivers the working keyless generate+publish command that ADR-0014
promises. Fixes three logged defects:

- **BUG-046** — `EconomistContentFlow` topic discovery is not keyless
  (`flow.py:176 → create_llm_client` needs a paid key). Either move discovery to
  the subscription Agent SDK, or bless a `pipeline.py <topic>` + `deploy_to_blog`
  two-step as the canonical keyless path.
- **BUG-047** — the keyless writer exhausts its cumulative budget across retries
  and emits no article. **First step: the budget-vs-loop diagnostic** (rerun
  with a generous `--writer-budget`); if it still fails, fix the writer
  well-formed/recovery path (cf. the closed PR #441 `_extract_article`, BUG-044).
- **BUG-048** — async-generator cleanup bug (`aclose(): asynchronous generator
  is already running`) masks `BudgetExceededError` in `_collect_text`.

Acceptance (the gate that moved here from B-009):
- One documented keyless command produces a publish-valid article + chart **and**
  opens a PR on `oviney/blog`, verified by a real end-to-end run on the
  subscription (env: `.venv` provisioned, `BLOG_REPO_*`, `claude` CLI auth).
- `docs/keyless-pipeline-runbook.md` names that command as canonical, plus a
  **Setup/Prerequisites** section (venv, `get-pip.py` since `ensurepip` is
  stripped on this Debian python, `pip install -r requirements.txt`) — gaps T1
  surfaced.

Depends on: B-009 (clears the paid/false machinery first).

### B-011 · Retire GitHub Actions CI; local `make quality` + pre-commit is the verification path

> **✅ DONE (2026-07-22).** `make ci-local` reproduces every gate ci.yml
> enforced (ruff, mypy-advisory, tests+coverage 70% / src/quality 90%, bandit,
> destructive guard) — verified green (2217 passed, 79.5% cov, src/quality 97%).
> ci.yml / quality-tests.yml / sync-copilot.yml deleted; docs.yml +
> copilot-setup-steps.yml kept. Python pinned to 3.12; ADR-0015 recorded;
> ADR-0004 superseded. Fixed a full-suite hang (hermetic-env conftest fixture).
> Follow-up (optional): wire coverage/guard/bandit into pre-commit as
> non-optional (make ci-local is the enforced gate today).

Scoped in `docs/specs/B-011-retire-ci-local-verification.md`. Extends ADR-0014
from generation to verification: make local tooling the source of truth, zero
dependency on GitHub Actions (the repo is public so Actions is free, but the goal
is independence). `main` is unprotected, so no CI is required to merge today.

The real work is **parity, not deletion** — `make quality`/pre-commit are weaker
than `ci.yml` (single Python vs 3.11+3.12 matrix; 40% coverage on `scripts` vs
70% on `src`+`scripts` + `src/quality` 90%; no destructive-change guard; no
bandit). Port those gates local first, *then* delete `ci.yml` +
`quality-tests.yml` (+ `sync-copilot.yml`, the merge-noise bot). Open questions:
fate of `docs.yml`/`copilot-setup-steps.yml`, whether to keep multi-version
testing, and whether to record an ADR-0015. Not yet approved to build.

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
built-in `WebSearch`/`WebFetch` tools (no Serper; ADR-0013). Vision refinement
rerouted off the `anthropic` client onto `query()` (also clears the ADR-0002
concern in `_shared.py`). New `--image-mode chart_only` CLI path runs end-to-end
(no hero image, no handshake) and writes `output/posts/<slug>.md`; the deprecated
`economist_agent.py` now fails loud with a pointer to the keyless command.
Surfaced + fixed two pre-existing chart-embed bugs found by the real validator:
**BUG-039** (`apply_editorial_fixes` mangled `![...]` image syntax when stripping
`!`) and **BUG-040** (`run_pipeline` chart_only stripped the image slug before
`_auto_embed_chart` could fire). Spec: `docs/specs/B-006-keyless-subscription-pipeline.md`;
plan: `tasks/plan.md`; runbook: `docs/keyless-pipeline-runbook.md`. Deterministic
+ tested (keyless, mocked SDK); behavioural proof is a live subscription run
(Checkpoint B).

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
