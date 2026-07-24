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

### B-016 · Claude-generated visuals: hero image + all post figures (BUG-053)

Owner wants Claude's own visualization to produce the **hero image** and **all
charts/images** a post needs — today the pipeline only draws one data chart
(matplotlib) and emits a hero-image *prompt* for a human. **BLOCKED ON AN OWNER
DECISION:** this reverses CLAUDE.md constraint #4 (NON-NEGOTIABLE — no pipeline
hero-image generation, "not even procedural/PIL"), which exists to honour #1 (no
keyed image services). Keyless-compatible interpretations to choose among:
(i) extend keyless code-drawn charts to multiple figures per post; (ii) a
Claude-authored **SVG/code hero illustration** (keyless, but currently banned by
#4); (iii) true raster AI hero art (needs a keyed/paid image model → blocked by
#1/#2). Owner amends #4 + picks scope, then spec it. See BUG-053.

### B-017 · Economist-writing enforcement misses AI-slop tells (BUG-054)

The generated flaky-tests article passes every deterministic economist-writing
gate (named companies, ≤4 headings, colon-twist title, no lists) yet still reads
like AI slop. Stage-4 only strips a fixed hedging/closing set; it does not catch:
em-dash rhythm, the repeated "not X but Y" scaffold, meta-commentary on its own
argument ("The argument here is…", "The numbers…make this case almost without
assistance"), unfalsifiable superlatives ("No other category…"), and purple/mixed
metaphors (dripping-tap→flooding-basement→plumber; "the engineer's nervous
system"). Spec a fix: extend the banlist/heuristics and/or add an
economist-writing judge pass, with regression fixtures from the cited tells. See
BUG-054 for the full evidence list.

### B-015 · economist-agents PRs must satisfy oviney/blog's governance gates

Discovered 2026-07-23 opening the B-013 blog PR (#1157). The **target blog repo
is itself agent-governed** with its own skills framework, scoped `agent:*`
labels, protected files, and a required-check branch-protection gate — and
economist-agents is an external agent from its point of view. Full findings:
`docs/blog-integration-constraints.md`. Impact beyond B-013: our everyday
`deploy_to_blog` article PRs must pass the blog's `build`, `Security Audit`,
`check-agent-scope`, Content Validation, Visual Regression, and Playwright gates,
and clear its 1-review requirement (author can't self-approve). Decide + document
the canonical way our PRs pass `check-agent-scope` — likely label them
`agent:editorial-chief` and keep article PRs `_posts/`-only (nothing else) — and
whether the deploy step should carry that label. Not yet spec'd; capture-only.

### B-012 · Opt-in `deep-brief` research mode (BUILT — live acceptance run pending)

> **✅ CODE DONE.** `--brief <file>` wired end-to-end (`pipeline.load_brief_file`
> strips refuted claims → `run_pipeline`/`run_stage3` `brief_override` skips the
> research step); documented opt-in/heavy in the runbook; `claude_web` stays
> default. Tested (`tests/test_deep_brief.py`) + `make ci-local` green. The one
> remaining acceptance criterion — a real deep-research → article run — is a
> token-heavy owner-run step (deep-research ~2M tokens), left opt-in by design.



Wire the `deep-research` harness as an **opt-in** research path for flagship
posts; `claude_web` stays the everyday default. **Prototype (2026-07-22) settled
it:** dramatically better sourcing — 19 claims each surviving a 3-0 verification
vote, and it *refuted the walked-back Accenture Copilot numbers* a single-pass
researcher would ship — but one topic cost ~102 agents / ~2M tokens / ~15 min and
**hit the session limit**. So: opt-in, not default. Spec:
`docs/specs/B-012-deep-brief-research-mode.md`. Prototype output (a real verified
brief) lives at `docs/research/ai-productivity-brief.md`.

### B-013 · Live unlisted draft review on GitHub Pages (candidate — gated on leak test)

Review generated drafts as the *rendered* post at an obscure, `noindex`, live
`/review/<slug>-<token>/` URL (real theme, reviewable from a phone) instead of a
GitHub PR diff; promote to `_posts/` via `make publish`. One-pager:
`docs/ideas/live-draft-review.md`. **Gate:** 10-minute leak test — deploy one
draft and confirm the minimal-mistakes theme surfaces it in *none* of
homepage/archives/feed/sitemap. Spec: `docs/specs/B-013-live-draft-review.md`.

**Local half BUILT (2026-07-23), `make ci-local` green:** `deploy_to_blog
--mode review` (writes `_review/<slug>-<token>.md`, `layout: review`, commits to
the live branch, no PR, prints the obscure URL) + `scripts/promote_review.py` /
`make publish SLUG=<slug>` (blocking validator gate). Tests:
`test_deploy_review_mode.py`, `test_promote_review.py`; `post` path untouched.

**Blog side — MOSTLY DONE, one fix PR pending merge:**
- **PR #1157 MERGED** (2026-07-24) — `review` collection + `noindex`/`sitemap:false`
  defaults + `_layouts/review.html` + `robots.txt` disallow now on blog `main`.
- **Leak test RUN (2026-07-24), 6/7 pass** — deployed one unlisted draft
  (`…-1530b611`). Draft is absent from homepage, /blog/, feed.xml, sitemap.xml,
  and search.json, and robots.txt disallows /review/ ⇒ **the hide works.** The one
  failure: the draft rendered **bare** (no `<head>`, no theme, no `noindex` meta).
- **Root cause:** this blog **disabled `remote_theme`** and uses local layouts —
  there is **no `single` layout**. `review.html` extended `single`, so it didn't
  chain to `default.html` (where `noindex` lives). Real posts use `layout: post`.
- **Fix: PR #1159 OPEN → https://github.com/oviney/blog/pull/1159** — one word,
  `review.html` now `layout: post`. `review.html` is NOT a protected file, so it
  should clear `check-agent-scope`.

**NEXT (resume here):**
1. **Merge blog PR #1159** (owner web-UI: "Merge without waiting for requirements
   (bypass rules)" → "Bypass rules and merge (squash)" → Confirm — same flow used
   for #1157; `gh pr merge` is classifier-blocked for the agent).
2. After Pages rebuilds, re-run the leak-test verify on the SAME draft URL
   (`…-1530b611`) — expect the `noindex` meta present ⇒ **7/7**.
3. Then `make publish SLUG=<slug>` on an approved draft, and move B-013 to Done.
   (A bare-rendered test draft `…-1530b611` is currently live/unlisted; it
   re-renders correctly once #1159 merges, or delete `_review/…-1530b611.md`.)

Note: canonical blog URL is **www.viney.ca**; live branch **main**; `.env`
`BLOG_REPO_TOKEN` failed push auth (`gh auth token` works — refresh the PAT).
Blog governance findings that bit us here → `docs/blog-integration-constraints.md`
+ BACKLOG **B-015**.

## Done

### B-008 · Single canonical slug across article file, chart PNG, and image-prompt sidecar — 2026-07-23

Adds `canonical_slug(article, fallback)` in `_shared.py` — one title-based slug
(topic fallback) that `_auto_embed_chart`, `_slug_for_chart` (stage3), and
`_slug_from_article` (pipeline) all delegate to. Turned out to be more than
cosmetic: in `chart_only` mode the hero `image:` frontmatter is stripped, so the
old `image:`-derived slug could embed the chart at a slug that didn't match the
rendered PNG on disk. Now the article file, chart PNG, `![Chart]` embed, and the
`<slug>.image_prompt.md` sidecar always share one slug. Regression test
(`tests/test_canonical_slug.py`) asserts they agree for a `chart_only` article.
PR #456; `make ci-local` green (2224 passed, cov 79.49% / `src/quality` 97%).

### B-014 · Chart redesign — graphics-stage correctness fix + dataviz styling — 2026-07-22

The graphics stage produced charts that **misrepresented the data** (the
flaky-tests chart mixed five percentages with a raw 150,000 count on one axis;
headline 84% vanished, count mislabeled "150000 %"). Baked one-axis/one-measure/
correct-units rules into the graphics-agent prompt (`_shared.py`) and added a
mixed-unit guard to `chart_renderer.py` (`_MAX_VALUE_SPAN = 1000`, rejects specs
whose max/min-nonzero ratio exceeds 1000× — Prove-It regression). Swapped in a
dataviz-validated colorblind-safe navy (`#0f5f92`). Matplotlib PNG kept — **not**
an SVG/interactive switch. PR #454. Spec: `docs/specs/B-014-chart-redesign.md`.

### B-011 · Retire GitHub Actions CI; local `make ci-local` is the verification source of truth — 2026-07-22

`make ci-local` reproduces every gate ci.yml enforced (ruff, mypy-advisory,
tests + coverage 70% / `src/quality` 90%, bandit, destructive guard) — verified
green. ci.yml / quality-tests.yml / sync-copilot.yml deleted; docs.yml +
copilot-setup-steps.yml kept. Python pinned to 3.12; ADR-0015 recorded, ADR-0004
superseded. Fixed a full-suite hang (hermetic-env conftest fixture that clears
`BLOG_REPO_*`/`*_API_KEY` so tests never do a real blog clone). `main` is
unprotected — the operator running `make ci-local` is the merge gate. PR #452.
Spec: `docs/specs/B-011-retire-ci-local-verification.md`.

### B-010 · Keyless generation produces an article + blog PR again (Track B) — 2026-07-21

A keyless run (`pipeline.py … --research-mode claude_web` → `deploy_to_blog`)
produced a publish-valid article and opened **oviney/blog PR #1156** — the first
live article since 2026-04-27 (pipeline had been dark ~3 months). Fixes
BUG-047/048/049/050/051. BUG-046 resolved-by-workaround: the two-step
`pipeline.py <topic>` + `deploy_to_blog` is the blessed keyless path (skips the
paid `EconomistContentFlow` discovery); making discovery itself keyless remains a
future enhancement. Runbook updated with the canonical command + Setup/Prereqs.
PR #451.

### B-009 · Retire paid-AI GitHub Actions (Track A) — 2026-07-21

Executes ADR-0014. Deleted `content-pipeline.yml` (scheduled paid generation),
`regenerate-image.yml` (DALL-E — violates CLAUDE.md #1/#4), and
`remediation-sync.yml`; stripped `OPENAI_API_KEY` from `ci.yml`; stripped the key
+ removed the cron from `blog-quality-audit.yml` (kept `workflow_dispatch`).
Corrected the false/stale run docs (README/CLAUDE.md Serper + DALL-E claims). No
workflow injects a paid-AI secret and none references a deleted workflow. PR #450.
Spec: `docs/specs/B-009-retire-paid-github-actions.md`.

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
