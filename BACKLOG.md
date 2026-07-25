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

> **Priority note (2026-07-25).** B-020 → B-023 outrank B-019. B-019 describes
> failures that are caught *loudly, at a gate, before publication* — which is the
> cheap and safe kind. B-020–B-023 describe a failure that passed **every**
> deterministic gate and reached readers: the first published article carried six
> factual errors and two fabricated citations (BUG-058 → BUG-062, corrected in
> `oviney/blog` b1eb5fd). The backlog had been ordered by what breaks the build
> rather than by what breaks the reader. Fix that ordering first.
>
> Root cause shared by B-020/B-021: **the research brief stores values stripped of
> provenance**, and Stage 3 re-associates them late. Author bleed, unit loss,
> number-to-claim mismatch and stance inversion are four symptoms of that one
> architectural choice.
>
> Evidence corpus: `data/review_corpus/2026-07-24-green-light-red-ledger/`.

### B-020 · Citation-integrity gate — resolve every reference and match its metadata

**Highest-priority pipeline item.** Fixes BUG-058. For each entry in the
References section: fetch the URL, extract the real title and author list, and
assert they match what the article emitted. Fail the article if they do not.

- Deterministic, keyless, no LLM — satisfies constraints #1–#3.
- Would have caught both fabrications mechanically: a title that does not exist
  at the cited URL, and an author lifted from a different reference.
- Regression fixtures already exist in `data/review_corpus/`: reference 1
  (`Parry, J. et al.` → Leinen et al.) and reference 5 (invented title).
- Note the existing evidence check *counts* references; it has never *resolved*
  one. Counting is not verification.

### B-021 · Claim provenance — every statistic carries its source sentence and unit

Fixes BUG-059. A number in the research brief must carry (a) a pointer to the
exact source sentence it came from and (b) an explicit unit. Stage 4 asserts the
pointer resolves and that the unit survives into the prose.

- Catches the `0.02 cents → $0.02` class (unit dropped in transit).
- Catches the `45% of projects → 45% of root causes` class (number re-scoped to a
  claim it does not support).
- **The existing stat audit is not a substitute and never was.** It asserts
  `stat ∈ research_brief`. It has never asserted that the brief entry is true,
  correctly scoped, or correctly united — so it passed a fabricated headline
  statistic while working exactly as specified. This is a spec defect to correct,
  not a bug to patch.

### B-022 · Source-stance check — does the source support the sentence citing it?

Fixes BUG-060. For each citation, classify whether the source's own conclusion
**supports**, **contradicts**, or **does not bear on** the sentence that cites it.
Flag contradictions before publication.

- Keyless via `query()` on the subscription (constraint #3).
- The published article argued auto-retry is "an anaesthetic" while citing a paper
  whose authors concluded the opposite and shifted toward automatic reruns. No
  deterministic gate can catch this; it needs a stage that reads conclusions
  rather than mining numbers.
- Depends on B-020 (a resolved citation is a precondition for reading its stance).

### B-023 · Chart data provenance — no derived series without a declared source

Fixes BUG-061. A chart series must point at a source figure. A series computed
from another series must be explicitly declared as derived and justified.

- The published chart plotted "genuine defects" shares of 16% and 79%, both
  produced by subtracting the flaky share from 100. Neither appears in any source,
  and the 16% collided with an unrelated real Google figure, making an invented
  number look corroborated.
- Also covers **BUG-062** (hero-prompt comment leaking into the published body):
  strip the `<!-- HERO IMAGE` placeholder whenever `image:` resolves to a real
  asset, with a regression test asserting none survives finalisation.
- Constraint #4 already says *always look at the rendered result*. That is what
  found this defect; the prose review missed it. Make it a gate, not a habit.

### B-019 · Align generated front matter with the blog's post contract (NEXT ARTICLE WILL FAIL WITHOUT THIS)

**Highest-priority pipeline item.** Publishing the first real article failed the
blog's `validate-editorial` job **four times**, each on a rule our own validator
does not have. Full measured contract:
`docs/blog-integration-constraints.md` → "The post front-matter contract".
Only `tags` was fixed generator-side (BUG-057). Still unemitted:

1. **`subtitle`** — required front matter (≤60 words hard, ≤40 soft). Not emitted
   at all. Needs a Stage-3/Stage-4 source (derive from the description, or have the
   writer produce it as a distinct field).
2. **Quoted category items** — the blog's parser splits on `", "`, so our unquoted
   `[Quality Engineering, Test Automation]` reads as ONE invalid category. One-line
   fix in the frontmatter emitter, but needs a test asserting the quoted form.
3. **Slug ≤ 60 chars** — ours derive from the full title; the flaky-tests slug was
   **76**. **This is the careful one:** it collides with **B-008**'s
   single-canonical-slug invariant, where one slug feeds the article filename, the
   chart PNG, the chart embed, and the `.image_prompt.md` sidecar. A naive truncation
   desynchronises them and reintroduces the class of bug B-008 closed. Needs a spec:
   shorten at a word boundary, keep one derivation, and cover every consumer.
4. Advisory but worth doing: `image_caption` ≤ ~40 chars (renders as
   `figcaption.image-credit`).

**No redirects exist** (no `jekyll-redirect-from`; `_config.yml` is protected), so a
too-long slug cannot be fixed after publish without 404ing the live URL — the
flaky-tests post had to be renamed. Get it right pre-publish.

**Verify against the blog's own scripts, never by reading them:**
`bash scripts/validate-posts.sh` and
`bash scripts/validate-post-quality.sh --all` (exit 2 = warnings only = pass).

### B-016b · Generate the hero SVG automatically in Stage 3 (follow-on)

**B-016a shipped the mechanism** (see Done) but the hero SVG for the flaky-tests
article was **hand-authored by Claude in-session**, not produced by the pipeline.
To make this repeatable, Stage 3 needs a graphics step that asks Claude to author
`output/posts/images/<slug>-hero.svg` from the existing `compose_prompt` brief,
plus a deterministic gate (well-formed XML, `viewBox`, `<title>`/`<desc>`
present, no `<text>` glyphs, no external `href`, size ceiling) and a
render-and-look check. Also unresolved: **multiple figures per post** — the
owner's ask included "any charts or images the post requires", and today the
pipeline still draws exactly one chart. Not yet spec'd.

### B-015 · economist-agents PRs must satisfy oviney/blog's governance gates

**`check-agent-scope` RESOLVED 2026-07-24** (see B-015a in Done). **Gate matrix
now measured** on blog PR #1159 (run 30135701462/30135701497):

| Check | Result | Note |
|---|---|---|
| `build` | **pass** | only after the BUG-055 empty-`image:` fix (B-018) |
| `check-agent-scope` | **pass** | unlabelled ⇒ Rule 4 skipped (B-015a) |
| `📝 Content Validation` | **pass** | |
| `validate-editorial` | **pass** | |
| Playwright shards 1–3 | **pass** | |
| `🎯 Accessibility, Visual & Lighthouse` | **pass** | |
| `📊 Quality Report` | **pass** | |
| `🔒 Security Audit` | **fail** | **pre-existing, blog-side**: npm CVEs in the blog's deps (`body-parser` high). Not content-related |
| `🖼️ Visual Regression` | **fail** | **pre-existing, blog-side**: stale committed baselines on `about`/`blog-index`/`homepage` (expected 3274px, got 3501px). Same 3 pages failed on #1157 |

**So every check we can influence passes.** The two failures are blog-repo
maintenance debt, and both are *required* checks — meaning **every**
economist-agents PR needs an owner bypass until the blog bumps its npm deps and
refreshes its visual baselines. Worth two issues in `oviney/blog` (not here).
Also unavoidable regardless: the **1-review requirement** — the token user is the
owner and GitHub forbids self-approval. Full findings:
`docs/blog-integration-constraints.md`.

**MEASURED ON A REAL ARTICLE 2026-07-25 — and it failed.** Publishing the
flaky-tests post tripped `validate-editorial`: the blog's
`scripts/validate-posts.sh` requires a **`tags`** field (≥2, inline
`[foo, bar]`, **all lowercase-hyphen**) and the pipeline had never emitted one, so
*every* article would have failed. Fixed generator-side (`_derive_tags`, BUG-057)
and verified by running the blog's own script → `PASSED`. Lesson: the gate matrix
above was measured on a *layout* PR; only a real article exercises the gates that
govern articles.

**Open item from the same script:** `validate-posts.sh` also requires **`image:`**,
so a **chart-only** article — which omits `image:` per BUG-055 — would fail this
gate. Currently **masked** because B-016 always draws a hero. Decide the intended
behaviour: always author a hero (then chart-only never happens), or give
chart-only posts a default illustration. Not yet spec'd.

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

## Done

### 🎉 FIRST ARTICLE PUBLISHED END-TO-END — 2026-07-25

**https://www.viney.ca/2026/07/24/green-light-red-ledger-flaky-tests-are-engineering-s-costliest-invisible-tax/**

The keyless pipeline's first article to travel the whole path: generate → review
as a live unlisted draft (B-013) → owner approval → `make publish` → live post,
with a **Claude-authored SVG hero** (B-016a) and a **corrected chart** (BUG-056).
The B-017 slop detectors printed as **advisory notes** in the publish report and
correctly did not block. Owner accepted the prose as-is.

Three defects had to be fixed *because* of this run, each invisible to
`make ci-local`: **BUG-055** (empty `image:` broke the blog build), **BUG-056**
(chart with 5 invisible bars and a `150000 %` label), **BUG-057** (`tags:` never
emitted → failed the blog's `validate-editorial`). Standing lesson recorded in
CLAUDE.md #4 and B-015: **a green local gate says nothing about what the blog
accepts, and only a real article exercises the gates that govern articles.**

### B-016a · Claude-authored hero illustrations ship end-to-end; constraint #4 amended — 2026-07-25

Owner amended **constraint #4** (was NON-NEGOTIABLE, recorded in CLAUDE.md rather
than changed silently). New line: **visuals are drawn as CODE, never generated as
pixels.** Allowed — Claude hand-authors the hero as **SVG** + charts via
`chart_renderer.py`, both keyless on the subscription (#1–#3 unchanged).
Forbidden — any raster/pixel model (DALL-E, Imagen, Midjourney, SD) and
procedural/PIL. Claude has **no keyless raster model**, so photographic art still
cannot be done keyless; the hero-prompt sidecar is retained as the brief Claude
draws from and as the manual-supply escape hatch.

**Hero shipping had never been wired** — `deploy()` copied only
`output/posts/images/<slug>.png` (an SVG hero was silently skipped → broken
`<img>`), and `deploy_review()` copied **no hero at all**, so a review draft could
never show the illustration it exists to review. Now frontmatter-driven:
`_hero_asset_ref()` + `_copy_hero_asset()`, wired into both paths,
`assets/images` staged. The **webp asymmetry is load-bearing**: the blog's
`responsive-image.html` does `replace: '.png','.webp'` and emits a
`<source srcset>` html-proofer demands, so a PNG hero needs the sibling and an SVG
hero takes the plain `<img>` branch and needs none — SVG is both the keyless path
and the lower-friction one. Tests: `tests/test_deploy_hero_asset.py` (8).

**Verified live** on draft `…-f40e8d27`: `hero.svg` serves 200 `image/svg+xml`,
renders in-theme with its figcaption, leak test still 10/10.

**Also fixed the article's chart, which was unshippable.** Five of six bars were
**invisible** (percentages 84/21/2.5/1.3/1.1 sharing one axis with a raw 150,000
count) and that count was labelled **"150000 %"** — a stale artifact from *before*
B-014's mixed-unit guard. Confirmed the guard now rejects that exact spec, then
rebuilt the chart on one coherent measure (share of failing builds caused by flaky
tests vs genuine defects: Google 84/16, Jira Frontend 21/79) — which is what the
prose actually promises the chart shows.

**Standing rule added to CLAUDE.md #4: look at the rendered result before
shipping.** Five iterations were needed, and a screenshot caught a z-order bug
where the drain painted over the coin pile — invisible in source.

Follow-on (pipeline automation + multi-figure posts) → **B-016b**.

### B-013 · Live unlisted draft review on GitHub Pages — 2026-07-25 · **LEAK TEST 10/10**

Review a generated draft as the *rendered* post at an obscure, `noindex`, live
`/review/<slug>-<token>/` URL (real theme, readable on a phone) instead of a
GitHub PR diff; promote to `_posts/` with `make publish SLUG=<slug>`.
Spec: `docs/specs/B-013-live-draft-review.md`; one-pager
`docs/ideas/live-draft-review.md`; blog-side runbook
`docs/specs/B-013-blog-side.md`.

**Local half:** `deploy_to_blog --mode review` (writes
`_review/<slug>-<token>.md`, rewrites `layout: review` + chart paths, commits
straight to the live branch, opens **no PR**, prints the obscure URL) +
`scripts/promote_review.py` / `make publish` (blocking validator gate). The
default `post` path is untouched — a separate function guarantees it. Tests:
`test_deploy_review_mode.py`, `test_promote_review.py`.

**Blog side (PRs #1157 + #1159, both merged):** `review` collection with
`output: true`, `permalink: /review/:name/`, and defaults `noindex: true` /
`sitemap: false`; `_layouts/review.html`; `robots.txt` disallows `/review/`.

**ACCEPTANCE — leak test 10/10 on draft `…-a7014d4d`** (`www.viney.ca`,
re-runnable via `scripts/leak_test_review_draft.sh <slug-with-token>`):
reachable at its obscure URL, renders through the real theme, carries
`<meta name="robots" content="noindex, nofollow">`, no src-less `<img>`, and is
**absent from `/`, `/blog/`, `feed.xml`, `sitemap.xml`, and `search.json`** with
`robots.txt` disallowing the path.

**Two bugs had to be fixed to get there, and the first was masking the second:**
1. **BUG-051** — `review.html` extended `single`, a layout that does not exist
   (this blog has `remote_theme` **commented out** and uses local layouts:
   `default`/`page`/`post`). The draft rendered **bare** — no `<head>`, no theme,
   and critically no `noindex`. Fixed in #1159: extend `post`, which chains to
   `default.html` where the `noindex` meta lives. That was the 6/7 failure.
2. **BUG-055** — with the layout fixed, the draft finally rendered the hero
   guard, exposing `image: ""` → html-proofer → blog `build` FAIL. See B-018.
   The bare render had been hiding it by emitting no `<img>` at all.

**Operational notes:** canonical host is **www.viney.ca** (apex redirects — the
`--host` default was BUG-052); live branch is **main**; `.env`'s
`BLOG_REPO_TOKEN` fails push auth, `gh auth token` works (**refresh that PAT**).
Blog governance constraints → `docs/blog-integration-constraints.md` + **B-015**.

**Draft `…-a7014d4d` is live and unlisted** — review it, then
`make publish SLUG=green-light-red-ledger-flaky-tests-are-engineering-s-costliest-invisible-tax`
to promote, or delete `_review/…-a7014d4d.md` to discard. Note it still carries
the **B-017 prose tells** (that article is BUG-054's evidence) and has **no hero
image** (constraint #4 — human-supplied).

### B-018 · `image: ""` broke the blog's required `build` check (BUG-055) — 2026-07-24

**Found by reading CI on the open B-013 PR rather than trusting the local gate.**
Stage 4 stamped `image: ""` into every article. Our validator reads empty and
absent identically ("no hero", chart-only) so it passed `make ci-local` — but
**Jekyll does not**: in Liquid only `nil`/`false` are falsy, so `""` satisfies the
blog's `{% if page.image %}` hero guard, `responsive-image.html` emits an `<img>`
with no usable `src`, and html-proofer fails the blog's **required `build`
check** with "image has no src or srcset attribute". Evidence: blog PR #1159
`build` FAIL, html-proofer at
`_site/review/…-1530b611/index.html:166`. (#1157's build passed only because
`review.html` then extended a nonexistent layout and rendered bare, emitting no
`<img>` at all — the bare-render bug was masking this one.)
**Impact was NOT limited to review drafts:** every generated article PR would
have failed the same required check.

**Root cause was two in-repo contracts disagreeing.** `frontmatter_schema.py`
`REQUIRED_FIELDS` (Story #117) required `image`, which is *why* Stage 4 stamped an
empty value — but #403 slice 2 had since made the hero **optional** ("Path A:
chart-only"), and `publication_validator._check_image_contract` treats an absent
`image:` as valid. Fix reconciles them: `image` is no longer a required field,
Stage 4 omits the key instead of stamping it, and any empty `image:` line the
writer emits is stripped (`_EMPTY_IMAGE_LINE` in `_shared.py`). Hero images stay
human-supplied (constraint #4) — no image generation added.
Regressions: `TestEmptyImageFrontmatterNeverEmitted`
(`tests/test_stage4_editorial_fixes.py`) and
`test_image_key_omitted_entirely_not_stamped_empty`
(`tests/test_frontmatter_finalize.py`, rewritten — it previously *asserted* the
buggy empty-stamp behaviour). See BUG-055.

**Still to do before B-013 can close:** the stale test draft
`_review/…-1530b611.md` already on blog `main` still carries `image: ""`, so blog
PR #1159's `build` will keep failing until that file is deleted. Delete it (it is
a throwaway bare-render test artifact), then merge #1159, then redeploy a fresh
draft — which now omits the key — and re-run the leak test for 7/7.

### B-015a · Article PRs are governance-safe by construction; agent-label plan reversed — 2026-07-24

Read `oviney/blog`'s `scripts/check-pr-scope.sh` instead of inferring from its
docs, and the answer **reversed B-015's stated plan.** Rule 4 (agent scope) is
**opt-in by label**: an unlabelled PR is treated as a *human PR* and skips the
check entirely. Adding `agent:editorial-chief` would therefore only **add**
restrictions (it activates the forbidden-zone pattern including `^scripts/`,
`^tests/`, `^_layouts/`). **Decision: keep `deploy_to_blog` PRs unlabelled** —
less work and less risk than labelling. Rules 1–3 (protected files, >15 files,
governance surfaces) apply regardless and our article PRs pass all three.
To make that hold **by construction rather than by luck**, `deploy()` now stages
`git add _posts assets` instead of `git add .` (an unscoped add sweeps in
anything else dirty in the clone, which could trip Rule 1/2);
`deploy_review()` already did this. Regression: `TestGovernanceSafeStaging`
(2 tests) in `tests/test_deploy_to_blog.py`. Findings table:
`docs/blog-integration-constraints.md`. The **other** required checks (build,
Security Audit, Content Validation, Visual Regression, Playwright) remain
unverified on a real article PR — still open under B-015.

### B-017 · Flag the AI-slop tells that pass every deterministic gate (BUG-054) — 2026-07-24

The flaky-tests article passed every economist-writing gate yet still read like
AI slop. Four countable detectors now run inside Stage 4 on
`publication_validator.py` (which already surfaces its issues to the reviewer):
`em_dash_density`, `antithesis_scaffold` (the "not X but Y" pile-up),
`meta_commentary`, `unfalsifiable_superlative`. Two design rules: they **flag,
never rewrite** (deleting one arm of a "not X but Y" mid-paragraph is worse slop
— rewriting stays human-in-the-loop, like the hero image), and they emit
**HIGH/MEDIUM, never CRITICAL** (inform the reviewer; don't quarantine a
publishable draft). Body-only — frontmatter, References, and fenced code blocks
exempt. **Verified on the real BUG-054 article:** all four fire (em-dash
1.15/para HIGH, antithesis ×3, 4 meta-commentary hits, 1 superlative) and its
only CRITICAL is a pre-existing `date_mismatch`. Scope is honest: 4 of 5 cited
tells are countable; the **purple/mixed-metaphor tell is semantic and was not
faked** — it stays human-review's job, with an opt-in keyless judge parked in the
spec (the CrewAI Stage-4 LLM reviewer was removed for 50% parse failure; not
reintroduced into the default path). 14 tests
(`tests/test_publication_validator_ai_slop.py`) incl. a clean control that must
stay unflagged. Spec: `docs/specs/B-017-ai-slop-enforcement.md`.
**Thresholds are first guesses** (em-dash 0.8/para HIGH, antithesis ≥4 HIGH /
≥2 MEDIUM) — tune on the next few real articles.

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
