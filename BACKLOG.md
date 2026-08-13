# Backlog

> **Source of record for planning items.** PRs + code review live on GitHub (`gh` CLI).
> Item ids are `B-NNN` and are never reused. The `(was #N)` tag records the GitHub
> issue an item was migrated from (those issues are closed, not deleted).
>
> See `docs/specs/local-backlog-migration.md` for why this file exists.

## Sprint Goal (2026-08-12)

**What is left is owner judgement plus one open PR.** B-040 needs a spot-check of the
calibration negatives (the sheet for it is built — PR #480); B-012 needs a live
deep-research acceptance run; B-045 is built and awaiting merge (PR #479). The
2026-06-14 goal (B-003 → B-002 → B-001) landed, and everything opened since has shipped.

- **Ordering:** B-045 first — it is a security fix and merge-ready. Then B-040, which
  unblocks ADR-0018 Decision 3 (promoting `blog-post-review` from advisory to blocking).
  B-012 blocks nothing and is the most expensive; it can wait.
- **Cadence:** spec → **human LGTM** → build/TDD → PR → merge. Stop for LGTM after each
  slice's spec.
- **Session discipline:** one slice per session. On merge, mark Done here, then `/clear`
  before the next slice. This file is the durable handoff — a fresh session resumes from it.
- **"Deployed to production" = merged to `main`** via reviewed PR (no separate runtime deploy).

## In Progress

### B-040 · Calibrate the editorial review gate so it can be promoted

**Opened 2026-08-01.** Spec: `docs/specs/review-gate-calibration.md` — **LGTM'd 2026-08-05**,
with both open questions answered in the affirmative (agent drafts negatives + owner
spot-checks a sample; `unverified` is a third outcome with its own `n`). Task breakdown below.

ADR-0018 Decision 3 keeps `blog-post-review` advisory and says "promote to blocking once a
false-positive rate is known." **Nothing has ever produced that number.** The gate has run
exactly once, by hand, on one article — and that run contained a near-false-positive (a
summarised Graphite fetch would have reported a false G2 failure on a correct figure). So the
only instrument that catches fidelity defects the deterministic evaluator provably cannot
(88% PASS vs 51 BLOCK on the same article) is frozen by a missing measurement.

Reviewed against Anthropic's [Demystifying evals for AI
agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), the eval
surface is lopsided in one specific way: **code-based graders are strong** (`article_evaluator`
at 841 records, `publication_validator`, `_shared.py`, `skill_eval`), and the one model-based
grader **has no ground truth to be checked against**. `logs/article_evals.json` is production
monitoring, not an eval set. The guide's instruction — *"20-50 simple tasks drawn from real
failures"* — is satisfiable today at **finding** granularity: ADR-0018 enumerates 10 labelled
fidelity defects plus the 1 labelled near-false-positive.

- [x] ~25 cases, ≥40% negatives, each traceable to a real article or a real finding
      *(23 cases at 52% negatives, 2026-08-05 — pending the owner spot-check. Known gap:
      **G3 has no positive case** and one must not be invented, so G3's false-negative rate
      is unmeasurable in v1.)*
- [ ] Report false-positive and false-negative rates **separately, with `n`** — never averaged
- [ ] Keyless judge via the Agent SDK; case selection and arithmetic deterministic
- [ ] Sufficient for the owner to answer ADR-0018 Decision 3

**Build after n≈5 real reviews**, which accrue free from the B-013 review stage the owner
already performs — the only added cost is recording, per gate, whether he agreed. The harness
design depends on what those runs show: a gate that blocks everything needs threshold tuning,
one that passes everything needs anchor revision (ADR-0018's own warning: "scores clustering
above 85 would mean the rubric is broken rather than the pipeline"). Different tools.

**Scope:** M. **Files:** `scripts/calibrate_review_gate.py`, `docs/evals/review-gate/`,
`tests/test_calibrate_review_gate.py`.

#### Plan — 2026-08-05, post-LGTM

**Phase 1 · the case set — unblocked now.** The set is 8 cases, **2 negatives (25%)**, against
a criterion of ≥20 cases and ≥40% negatives. All 8 carry
`source: testing-shortcuts-migration-deadline`; the README claims two sources but
`review-queue-throughput-tax` has contributed **zero**.

**Phase 1 DONE 2026-08-05 — PR #473, open, gated on the owner spot-check.** The set is
**23 cases / 12 negatives (52%) / 4 source articles**; `make ci-local` green at 2,768 passed,
9 skipped. Resume instructions and the four cases to spot-check are in `docs/HANDOFF.md`.

- [x] **Task 1 — convert the ADR-0018 findings into cases (S).** The 10 labelled fidelity
      defects plus the **near-false-positive** (the summarised Graphite fetch that would have
      reported a false G2 failure on Graphite's own published figure). The spec calls that one
      case worth more than all ten positives, because false positives are what block
      promotion — and it is the case the set does not have. Correct the README's provenance
      claim in the same change. **Files:** `docs/evals/review-gate/cases/*.yaml`, README.
- [x] **Task 2 — mine ~15 negatives from the 26 published articles (M).** *(12 mined, from 3
      articles; the criterion was the 40% ratio, which 12 clears at 52%.)* Source of truth is
      the `oviney/blog` clone at `/Users/ouray.viney/code/economist-blog-v5/_posts` (26 posts,
      current to 2026-08-02). Every case carries `source:` provenance. **Owner spot-checks a
      sample** — per the answered open question, this is the control on the agent drafting
      cases for a judge of its own model family, so it is not optional.

**Checkpoint (owner):** ≥20 cases, ≥40% negatives, spot-check passed. Phase 2 opens here.

**Phase 2 · the runner — TDD, judge stubbed in tests, no model calls in the suite.**

- [ ] **Task 3 — case loader + schema validation + balance report (S).** A file missing
      `expected` or `why` is rejected loudly, never skipped. Balance reported every run.
- [ ] **Task 4 — agreement arithmetic (S).** False-positive, false-negative and `unverified`
      as **three separate counts with three denominators**; `n` beside every rate; a rate from
      <20 cases labelled provisional in the output itself. Degenerate cases (all-pass,
      all-fail, empty) covered.
- [ ] **Task 5 — keyless judge via the Agent SDK + `--gate` / `--report` (M).** Runs the gate
      **as accepted 2026-07-31** — v1 does not touch `rubric.md` or `REVIEW_PROMPT.md`.
- [ ] **Task 6 — report to `logs/review_gate_calibration.json`, append-only (S).** Decide
      *against* wiring into `make ci-local`: the runner makes model calls, and `ci-local` must
      stay keyless and offline.

**Sequencing note, flagged rather than acted on.** The spec gates the build on "n≈5 real
reviews"; the repo has 2. That gate is worth re-examining at the Phase 2 checkpoint, because
the runner grades **cases**, not review runs — the 5 reviews inform how to *interpret* the
result (threshold tuning vs anchor revision), not the harness design. Owner's call at the
checkpoint; Phase 1 does not depend on it either way.

**Shipped 2026-08-01 alongside the spec, because waiting corrupts the baseline:**

- [x] **G5 added to the machine-readable verdict block.** ADR-0018 Decision 2 says G5 was
      amended "into the machine-readable verdict block". It reached `SKILL.md:165` but **not**
      `REVIEW_PROMPT.md:85` — the file actually pasted into a review session — nor the rubric
      card. Every review until now silently dropped the result of the gate that exists
      *because* a reversed DORA statistic passed the other four.
- [x] **Runbook cost/duration figures replaced with the recorded range** (see B-041).

**Phase 2 is the owner's, and the cost of it is now removed — PR #480, 2026-08-12.**
`scripts/render_calibration_review_sheet.py` collapses the 23 case files into
`docs/evals/review-gate/SPOT-CHECK.md`: passage, labelled verdict and stated reasoning
side by side, negatives first, with an agree/disagree control per case. It does **not**
perform the check — an agent adjudicating negatives it drafted, for a judge of its own
model family, is the loop the control exists to break. Its header counts are computed
from the loaded cases rather than restated, so the sheet independently reproduces
23 / 12 negatives (52%) / 4 sources instead of trusting Phase 1's numbers.

**Still open:** the owner reads the sheet; disagreements are findings, not failures.
Then the false-positive and false-negative rates can be reported separately with `n`,
which is what ADR-0018 Decision 3 is blocked on.

### B-045 · `deploy_article` could publish any readable file — **PR #479, 2026-08-12**

`deploy_article` (`mcp_servers/blog_deployer_server.py`) took an agent-supplied
`article_path`, wrapped it in `Path()` and checked only `.exists()`. Nothing constrained
it to `output/`, and the function copies the named file into a **public** blog PR using
`GITHUB_TOKEN`. This pipeline ingests untrusted web research and owner HTML artifacts, so
injected text steering an agent could name any readable file — OWASP LLM01 → LLM06.

**Not theoretical.** The symlink reproduction test failed with `assert True is False`
before the fix: a symlink planted inside `output/` pointing at a file outside it deployed
successfully.

`_resolve_article_path` resolves first — collapsing `..`, following symlinks — then refuses
anything not under the deployable root, *before* the existence check so an out-of-root path
cannot be used to probe which files exist. The root is **not a tool argument**: an agent that
can widen its own sandbox does not have one.

**Provenance, and the half worth recording as closed.** Found triaging PR #475, unsolicited
scanner outreach from Trustabl.ai. Its payload was a GitHub Actions workflow — which reverses
**B-011** (Actions CI retired; `make ci-local` is the verification source of truth) and adds a
third-party service against Operating Constraint #2 — so **#475 itself is declined**. One of
its two findings was real and is fixed here.

**Its other finding is a measured false positive: do not re-raise it.** "Session permission
mode bypasses approvals" is true of the flag and false of the configuration. All five
`permission_mode="bypassPermissions"` sites pair it with an explicit allowlist, all with
`mcp_servers={}`:

| Site | `allowed_tools` |
|---|---|
| `src/agent_sdk/research/_llm.py:55` | `[]` |
| `scripts/llm_client.py:198` | `[]` |
| `src/agent_sdk/_shared.py:1062` | `["Read"]` |
| `src/agent_sdk/research/claude_web.py:109` | `["WebSearch", "WebFetch"]` |
| `src/agent_sdk/stage3_runner.py:536` | caller-supplied, defaults `[]` |

Bypassing approval for an empty tool set grants nothing. Recorded here so the next scanner —
or the next session — settles it by reading this table rather than re-deriving it.

**Known hotspot, deliberately not fixed here.** `deploy_article` was already at 13/13/61
against the complexity sensor's 10/12/50 before this change; folding the existence check into
the resolver keeps it at 13/13/61, net zero. No override recorded — the debt is pre-existing
and unclaimed, and it is a genuine target if B-032 wants one.

## Todo

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

### B-044 · Finish the B-042 acceptance — 2026-08-02

**The article is published:** <https://www.viney.ca/2026/08/02/migration-deadline-testing-trap/>

The B-042 hand-off has now run end to end, live, for the first time: pipeline → packet →
owner's hero → `make art` → `--mode review` → owner approval → `make publish`. **Four defects
were found doing it** — BUG-070, BUG-071, BUG-072 and the range-endpoint proposal — none of
which 2,747 passing tests could see. All fixed with regression tests.

**One editorial correction the review stage caught, which is the whole argument for having
one.** The draft rested its subtitle and a section title on the IBM Systems Sciences
Institute's 1:15:60-100 defect-cost ratio, propped up by the sentence "they have since been
corroborated by every serious study that followed" — which is the *reverse* of the truth.
The Institute was a staff training programme, not a research body; the figure traces to
Pressman (1987) citing "[IBM81]" course notes with no data behind it. The published version
says so, and argues the case is stronger without it. **Neither the validator nor the
evaluator can catch a claim like that** — only a human reading the rendered page.

The remaining owner round-trip, unchanged: **re-sourcing an HTML artifact via Claude.ai is
still unexercised**, since this run used `claude_web`. That is the only part of B-038's
path the acceptance did not cover.

<details><summary>Original item, as opened</summary>

**Opened 2026-08-02** from the first live run of the hand-off. Full record:
`docs/reviews/b042-live-acceptance-2026-08-02.md`.

The flow now works end to end in code — **BUG-070** and **BUG-071** were found live and are
fixed, with regression tests. What remains is not code:

1. **Draw the hero** at `output/posts/images/migration-deadline-testing-trap-hero.svg`. The
   brief is in the review packet and the `.image_prompt.md` sidecar. Then `make art
   SLUG=migration-deadline-testing-trap`, deploy `--mode review`, read the live page,
   `make publish`. Steps 4 and 5 have **never run live** and will not until the hero exists.
2. **Re-source the artifact**, if the B-038 HTML→brief path is to be accepted too. This run
   used `claude_web` instead, because the Claude.ai conversation that produced
   `sre-quality-governance-guide.html` could not be identified from `recents` — the artifact
   dates to **Jul 21 13:04** and nothing in the list obviously matches it. Pasting into a
   guessed thread was not worth the risk.

**Read the article before publishing.** Three editorial items are flagged in the record — the
contested IBM 60-to-1 ratio carrying an uncited "corroborated by every serious study"
sentence, a reference list that is mostly secondary sources, and 8 quantified claims without
inline attribution.

**The two chart-proposal items are DONE** (PR #468, 2026-08-02). A range bound is no longer
proposed at all — "15–20%" offering a row reading `20 %` states an endpoint as a
measurement, which is B-042's complaint arriving through a different door — and the
provenance quote snaps to word boundaries. The live spec went 19 rows → 17; the two dropped
are exactly those endpoints. Both packet branches now name what was left out, so nothing is
excluded silently.

**A fourth defect, BUG-072**, found the same way: `make art` crashed with
`UnicodeDecodeError` on a real PNG hero, because `_hero_description` read every hero as
text to harvest an SVG `<desc>`. The suite's PNG heroes are `write_text("stub")` — text
files wearing a `.png` name. Fixed, PR #470.

**Small, unfixed:** `deploy_review` mints a fresh `<slug>-<token>` on every run and never
retires the previous draft, so redeploying a review leaves the superseded copy live at its
own URL. Removed by hand on 2026-08-02. Worth a cleanup step before the review path gets
used often.

**Nothing else here is code.** The item is blocked on the owner reading the review page.

</details>

> **Opened 2026-07-29 from the article-two run.** **B-025** was withdrawn the same
> day (see below); **B-026** and **B-027** landed the same day (see Done). Ids are
> never reused, so all three numbers stay spent. **B-028** and **B-029** are open,
> both from the RCA on the skipped review stage.
>
> **Opened 2026-07-29 from the harness audit.** **B-030 … B-034** come from auditing
> this repo against SE Radio 730 (harness engineering). They generalise B-028 and
> B-029: a guide the default ignores, and a sensor that cannot fail. See the
> "Harness engineering" section below.

### B-039 · The merge gate runs whatever toolchain the machine happens to have — 2026-08-01

**Opened 2026-08-01**, found by `make ci-local` failing on a file the session never touched.

ADR-0015 makes `make ci-local` *the* merge gate — there is no GitHub Actions, and `main` is
unprotected. So the gate has to mean the same thing on every machine and in every shell. It
does not. Every recipe resolves its tools from ambient `PATH`, not from the venv this repo
pins, and line 51 (`.venv/bin/python scripts/mypy_baseline.py`) shows someone already hit
this and patched the one line instead of the class.

Three symptoms, all measured on 2026-08-01, not inferred:

| Symptom | Measured |
|---|---|
| **The gate lints with an unpinned ruff.** `requirements-dev.txt` pins `ruff==0.14.10` *exactly*; the gate ran homebrew's **0.15.9** and demanded a reformat of `tests/test_mypy_baseline.py`, which no one had edited. | `ruff --version` → 0.15.9 ambient vs 0.14.10 in `.venv` |
| **The gate cannot run in a clean shell at all.** Line 49 calls bare `python`, which does not exist on macOS outside an activated venv. | `make ci-local` → `/bin/sh: python: command not found`, Error 127 |
| **The advisory mypy step reports a missing tool as a pass.** `(mypy scripts/ \|\| echo "advisory")` swallows exit 127 exactly like exit 1, so "mypy found 187 errors" and "mypy was never installed" print the same line. `mypy` and `bandit` are both absent from ambient `PATH` here. | `sh -c '(mypy scripts/ \|\| echo advisory)'` → `mypy: command not found` then the advisory text, exit 0 |

The third is the serious one, and it is **B-031's complaint exactly**: a sensor that cannot
distinguish "I ran and found problems" from "I never ran". The first is B-037's sibling — that
item found four declarations of the Python version disagreeing with the interpreter actually
running the suite; this is the same drift one level down, in the *tool* versions.

**Fix:** put `.venv/bin` first on `PATH` for the whole Makefile, guard every tool-running
target behind a `require-venv` check that fails loudly rather than falling through to ambient
binaries, and split the mypy advisory into its own target that distinguishes exit >1 (did not
run — fail the gate) from exit 1 (type errors — advisory, as intended).

- [x] `make ci-local` resolves ruff, mypy, pytest, bandit and coverage from `.venv/bin`
- [x] A missing venv fails with an instruction, instead of silently using ambient tools
- [x] The mypy advisory step fails the gate when mypy did not run
- [x] Regression tests that *execute* the Makefile against stub tools, not greps of its text

**Scope:** S. **Files:** `Makefile`, `tests/test_ci_gate_is_reproducible.py`.

**DONE 2026-08-01. The obvious fix did not work, and only a running test caught it.**

`export PATH := $(CURDIR)/.venv/bin:$(PATH)` is the one-line fix everyone reaches for, it
reads correctly, and `make showpath` confirms the exported value. It still left `ruff check .`
running the ambient ruff. **GNU make 3.81 — what macOS ships — direct-execs any recipe line
containing no shell metacharacters, and resolves the binary against make's own startup PATH
rather than the exported one.** So `mypy ...; status=$$?` used the venv (it has a `;`, so a
shell runs it) while `ruff check .` did not. The fix is to name `$(VENV_BIN)/<tool>`
explicitly in every recipe; the `export PATH` stays, but only for what *child* processes
look up.

A grep-the-Makefile test would have passed the moment the plausible-looking line was
written. The test that executes `make lint` against a stub `ruff` failed, which is the whole
argument for behavioural sensors — and the **fourth** instance of the pattern in
`skills/defect-prevention/SKILL.md`: asserting from a plausible reading instead of measuring.

Verified from a bare shell (`env -i PATH=/usr/bin:/bin:/opt/homebrew/bin make ci-local`,
no activated venv, no PATH prefix): green, 2,680 tests. Before this change that invocation
died at step 3 with `python: command not found`.

Mutation-checked, so the new sensor is not decorative: the old
`(mypy … || echo "advisory")` form exits **0** against a `mypy` stub that exits 127; the new
form exits non-zero. `make install` now creates the venv if it is absent, so require-venv's
instruction points at a target that actually works from nothing.

### B-041 · The hero draw's worst case is 3× the longest run ever recorded, and nothing attributes it — 2026-08-01

**Opened 2026-08-01**, found by the owner asking whether "~35 minutes" was ludicrous. It was
— but not in the direction either of us assumed.

`logs/agent_sdk_costs.jsonl` has recorded `wall_seconds` and per-stage cost **since
2026-04-26**, and no recorded run exceeds **15.4 minutes**; four of the five are under 5. The
"~$1 and ~35 minutes" in `docs/HANDOFF.md` and the runbook was folklore contradicted by the
repo's own data. **The instrument existed and went unread** while its contradiction was
repeated in two documents — and this session quoted it back to the owner and defended it
before checking. That is the `defect-prevention` surface-reading class again, in a session
that had just added an entry to it.

The real finding is underneath. A run started 2026-08-01 blew past every recorded figure, and
the log says why:

```
WARNING src.agent_sdk.hero_author: Hero attempt 1/2 timed out after 600s
```

`hero_author.py`: `_DRAW_TIMEOUT_S = 600`, `_MAX_STRUCTURAL_ATTEMPTS = 2`,
`_MAX_CRITIQUE_RETRIES = 1` → **2 redraws × 2 attempts × 600s = 40 minutes of hero drawing
alone**, before critique (2 × 180s). A *successful* draw is measured at 454s. So the pipeline
has two utterly different durations — ~4 minutes when the hero lands first try, up to ~46
when it does not — and the ledger cannot distinguish them, because the hero sits inside
`stage3_seconds` with no sub-timing.

The constants are not arbitrary; the comments record that 240s and $0.40 were "each
independently fatal". The problem is not the ceiling, it is that **a 10× duration swing is
invisible in the only place anyone would look for it.**

- [x] Record hero draw seconds, attempt count and timeout count as their own ledger fields
- [x] Decide whether a timed-out first attempt should retry at all
- [x] Bound the aggregate, not just each call
- [x] ~~State the honest range in the runbook once several runs carry `hero_*` fields~~ —
      **overtaken by B-042.** No run will ever carry them again.

**CLOSED 2026-08-01 as MOOTED by B-042.** The owner now draws every hero by hand, so
`hero_author.py` is deleted and the pipeline contains no draw to time. The 10× duration swing
this item existed to make visible cannot recur, and the `hero_*` ledger fields were removed
with it rather than left recording a permanent zero — which would have been this item's own
complaint (a reading that looks authoritative and measures nothing).

**The lesson outlives the item, and is worth keeping:** the ledger recorded only runs where
the hero landed, so it could not see the timeout path at all. A log that is written on
success and not on failure is not a partial instrument, it is a misleading one. See ADR-0019.

**Scope:** S. **Files:** ~~`src/agent_sdk/hero_author.py`~~ (deleted),
`src/agent_sdk/stage3_runner.py`, `src/agent_sdk/pipeline.py`.

**FIXED 2026-08-01, and the run that prompted it settled the design question.**

The run finished while this item was being written, and it is the whole argument:

| | |
|---|---|
| Wall clock | **31.8 min** — twice the previous record |
| Cost | $1.01, of which $0.18 graphics |
| Hero attempt 1 | timed out at 600s |
| Hero attempt 2 | **also timed out at 600s**, carrying the "return a simpler drawing with fewer, larger shapes" instruction |
| Hero produced | **none** |

So **20 of the 31.8 minutes bought nothing**, and the article is unpublishable — the blog
requires a resolvable `image:`. It also retires the open question: the shrink-the-ask retry
does not work. One timeout is a diagnosis, not a transient.

That reframed the fix. An aggregate budget of 1200s would have changed this run by **zero
seconds** (2 × 600 = 1200 exactly). The ceiling has to make the second full-price attempt
*impossible*, not merely capped:

- `_HERO_TOTAL_BUDGET_S = 900` — one measured successful draw (454s) plus its critique (180s)
  plus slack, and equal to the longest *complete* pipeline run ever recorded.
- `_MIN_USEFUL_DRAW_S = 450` — no observed successful draw has finished faster than 454s.

Those two numbers separate the retry cases by arithmetic rather than by a special case, which
is why the fix is small. A **rejected** attempt returns in seconds and leaves the budget
almost intact, so it retries exactly as before. A **timed-out** attempt has consumed 600s by
definition, leaving 300s — under the floor — so it stops. Cheap signal, retry; expensive
silence, stop.

Worst case: **46 min → 15 min.** This run's failure mode: **20 min → 10 min.**

**And the folklore was not baseless after all.** The earlier correction — "no recorded run
exceeds 15.4 minutes" — was true of the ledger, and the ledger was the wrong instrument: it
had only ever recorded runs where the hero landed. "~35 minutes" was a real memory of the
timeout path that nothing had ever written down. Both halves were right, which is exactly the
case for the `hero_*` fields: the ledger now distinguishes the two populations it was
silently averaging.

**Found in passing, and it may explain the thin ledger.** A value orjson cannot serialise
does not fail the write loudly — `pipeline.py` catches it and logs "cost log write failed
(non-fatal)", so the entire row disappears. Five rows across four months of runs is suspicious
on its own. `_numeric()` now coerces at the boundary; whether earlier rows were lost this way
is unverified and worth a look before anyone trends this data.

### B-042 · The mandatory-chart gate manufactures the fabrication it should prevent — 2026-08-01

**Opened 2026-08-01**, found by the owner asking "if we don't need a chart, why build one?"
He is right, and the repo currently disagrees with him — in a way that produced two of the
eight calibration cases logged the same day.

`publication_validator.py:1031` makes a chart **mandatory at CRITICAL severity**:

```python
if not chart_refs:
    "check": "missing_chart",
    "severity": "CRITICAL",
    "message": "Article missing required chart — every article must include at least one data chart"
```

So when the research carries no quantitative data, the pipeline is *required* to produce a
chart regardless. On the 2026-08-01 run it did exactly that: a brief containing one number
yielded a chart carrying four invented percentages (62/46/28/12%), presented with an axis and
a measured-sounding subtitle. **That was compliance, not a rogue writer.**

The next check compounds it. `orphaned_chart` (HIGH) fires unless the prose contains "chart",
"figure", "shows" or "illustrates" near the embed — pushing the writer to add a sentence
describing the chart, with nothing verifying the description is true. That is how "As the
chart below illustrates, undetected defects do not flow linearly into rework" came to be
written about a static four-bar comparison, reproducing ADR-0018's chart finding exactly.

**Two gates, combined, manufactured two defects.** A rule meant to enforce evidence produced
fabricated evidence, and the deterministic evaluator then scored the result 76 and passed it.

- [x] Decide the editorial policy — **the owner owns every image, charts included** (stated
      2026-08-01). Not "mandatory when the research supports one" but "his call, always"
- [x] Make the requirement conditional — **superseded by deletion.** `missing_chart` is gone.
      The setpoint was not mistuned, it was held by the wrong party: whether an article
      warrants a chart is judged against the research, which the validator never sees
- [x] `orphaned_chart` must not be satisfiable by a describing sentence — **deleted.** It
      could never fire at all (`missing_chart` returns early unless a `/assets/charts/….png`
      ref exists, so the content always contained "chart"), and a *working* one would have
      pushed the writer to describe the chart, which is what wrote case `g2`
- [x] Regression case: a brief with no quantitative data produces an article with no chart
      that passes — `tests/test_publication_validator.py::TestChartIsNotTheValidatorsDecision`

**DONE 2026-08-01.** Spec: `docs/specs/mandatory-chart-setpoint.md`. Decision: **ADR-0019** —
a setpoint is a decision about who decides. The pipeline no longer draws a hero or generates
chart data; it *extracts* candidate figures from the brief with provenance and hands off a
review packet (`output/posts/<slug>.review.md`). Art presence is gated at deploy (ADR-0017),
which is now the only thing enforcing it. Operating Constraint #4 amended — this reverses
B-016b. **B-041 is mooted** and closed with it.

**Scope:** M. **Files:** `scripts/publication_validator.py`, `src/agent_sdk/_shared.py`
(`_auto_embed_chart`), `src/agent_sdk/stage3_runner.py`.

### B-043 · No sensor ships without a proof it can fail — 2026-08-01

**Opened 2026-08-01. DONE 2026-08-01.** Spec: `docs/specs/sensor-proof-of-teeth.md`.
**Absorbs B-040** as its inferential-sensor arm.

**Shipped:** `scripts/check_sensor_proofs.py` runs as a `make ci-local` step,
`docs/sensors/register.yaml` holds 20 entries (**19 proved, 0 unproved, 1 report-only**), and
`tests/test_check_sensor_proofs.py` carries the checker's own proof of teeth. Two sensors that
had **zero** tests now have 26 between them.

The 2026-07-29 SE Radio 730 assessment graded this repo *guide-maximal, sensor-disconnected*;
B-030 … B-035 fixed the wiring. **The next failure mode is that nothing validates the sensors
themselves**, and 2026-08-01 produced four independent proofs in one day:

| Finding | Kind of sensor failure |
|---|---|
| **B-039** | A **fifth** inert sensor — `(mypy \|\| echo advisory)` returned exit 0 against a stub exiting 127 — found *after* B-031 fixed four |
| **B-040** | A sensor that **never runs**, with no ground truth |
| **B-041** | A **biased** sensor: the ledger recorded only runs where the hero succeeded, hiding a 10x duration swing |
| **B-042** | A sensor whose **setpoint manufactured the defect** it exists to prevent |

**B-031 fixed four named sensors; it did not fix the class.** That is the argument for a
standing check rather than another audit.

The technique already exists — used three times on 2026-08-01, at a terminal, unrecorded.
Mutate something, check whether the sensor notices. The third instance is the one that matters:
`export PATH := .venv/bin:$(PATH)` looked right, `make showpath` confirmed it, and running
`make lint` against a stub `ruff` showed the ambient ruff still won. **A grep of the Makefile
would have passed on a fix that fixed nothing.**

Measured baseline: 13 sensor scripts; `lint_adrs.py` and `check_bare_name_imports.py` have
**zero tests**; the rest have unit tests (does the code work) not efficacy tests (does it fire).

**The design constraint that decides everything: the fix must be a sensor, not a guide.**
Writing the rule into a `SKILL.md` reproduces exactly what this repo was graded down for —
constraint #1 ("NO new API keys. Ever.") had zero computational backing until B-030, and B-028
was a review stage that existed as prose while the tool default bypassed it. A rule nothing
enforces gets skipped.

- [x] `scripts/check_sensor_proofs.py` in `make ci-local`, failing on an unregistered sensor
- [x] `docs/sensors/register.yaml` covering all of them, `proof: none` allowed as a recorded
      baseline — **not needed in the end**, every discovered sensor got a real proof
- [x] `lint_adrs` and `check_bare_name_imports` proved first — the two real gaps
- [x] The three hand-run mutation proofs exist as tests, not shell history
- [x] The checker has its own proof of teeth

**Scope:** M. **Files:** `scripts/check_sensor_proofs.py`, `docs/sensors/register.yaml`,
`tests/test_check_sensor_proofs.py`.

**Discovery reads the wiring, not filenames.** The checker parses the `Makefile`,
`.pre-commit-config.yaml`, `.claude/settings.json` and the publish entrypoints, and demands a
register entry for every in-repo script they invoke. A `scripts/*_guard.py` glob would have been
gameable by renaming and blind to anything added under another name — and the whole complaint
about B-031 is that fixing four sensors *by name* left a fifth to be found.

**Verified in situ, because a fixture passing is not the claim.** Adding a recipe invoking a new
script to the real `Makefile` made the real gate exit 1 naming it; reverting restored green. This
is B-039's third lesson applied to its own successor — `export PATH :=` looked right, `make
showpath` confirmed it, and only running a recipe against a stub binary showed it did nothing.

**The limit is stated, not papered over.** The checker verifies a proof *exists and runs*; it
cannot verify a proof is *genuine* — `assert True` under an honest-sounding test name would pass.
Mutation-testing the mutation tests is where the value curve goes flat, so the `mutation:` field
exists instead, to make genuineness a one-glance review-time check.

**Open question ANSWERED — what counts as a sensor.** The proposal was right in substance and
wrong in one word: "non-zero exit" is the wrong test, because **every harness hook exits 0 by
design** and refuses via JSON. Measured, `guard_constraints` denies a tool call and `session_gate`
blocks a turn, while `post_edit_sensor` and `session_context` return only `additionalContext`.
Adopted: *a sensor is anything a gate site invokes that can **refuse** — deny a tool call, block a
turn, or exit non-zero.* Both named cases resolve as proposed and both were checked, not assumed:
`publication_validator` is **in** (imported by both publish entrypoints, its verdict stops a
publish); `article_evaluator` is **out** (zero gate-site references anywhere — it scored the
fabricated article 76 while the validator passed it, which is precisely a score and not a gate).
Note it *is* on `destructive_change_guard`'s `CRITICAL_FILES`: being protected from being gutted
is not the same as being a sensor. Full reasoning in the spec's open-questions section.

### B-028 · The unreviewed publish path must stop being the default — 2026-07-31

**RCA finding, 2026-07-29.** Article two was deployed with
`deploy_to_blog --mode post` — a PR straight into `_posts/` — skipping the B-013
live review stage entirely. Article one had used it (`generate → --mode review →
live unlisted /review/<slug>-<token>/ → owner approval → make publish`). The PR
(`oviney/blog#1169`) was closed and the article re-deployed through review.

**Root cause: the review stage exists only in a completed-backlog entry, and the
tool's default mode bypasses it.** `deploy_to_blog.py:681` sets
`default="post"`, so running the documented command produces an unreviewed
publish with no error and no warning.

**The documentation problem is systemic, not one stale line.** Five docs describe
`deploy_to_blog` without the review step, and `CLAUDE.md` — the governing doc —
never mentions `--mode review`, `_review`, `make publish`, or the unlisted URL at
all (grepped: zero hits):

| File | What it says |
|---|---|
| `docs/HANDOFF.md:48` | "Then `deploy_to_blog` opens the PR." |
| `CONTRIBUTING.md:96` | `python -m scripts.deploy_to_blog --article output/posts/<slug>.md` |
| `README.md:39` | "a human deploys via `scripts/deploy_to_blog.py`" |
| `.github/copilot-instructions.md:29` | "deploy with `scripts/deploy_to_blog.py`" |
| `docs/README.md:114` | "Deploy an approved article to the blog repo" |

**Corroborating evidence that `--mode post` is the unused path:** BUG-069 (the
missing date prefix, which makes a post unpublishable) existed *only* there.
`promote_review.py:117` builds `f"{deploy_date}-{slug}.md"` — correct by
construction — so the reviewed path never had it. A defect that severe surviving
in `--mode post` is evidence real publishing does not go through it.

#### Task 1 — remove the accidental default (XS, do first)

`--mode` becomes **required**. Neither value is a safe default: `post` skips
review, and making `review` the default would write to the blog's live branch on
a bare invocation, which is worse. Forcing an explicit choice removes the
accident without picking a wrong default.

- [x] `deploy_to_blog` with no `--mode` exits non-zero with a message naming both
      modes and pointing at the review workflow
- [x] No code caller breaks — `git grep` finds **no** programmatic callers, only
      docs, so this is safe
- [x] A test asserts the missing-mode failure, so a future tidy-up cannot restore
      a silent default

**Verify:** new test; `make ci-local`. **Files:** `scripts/deploy_to_blog.py`, one test.

#### Task 2 — document the workflow where it governs behaviour (S)

- [x] `CLAUDE.md` gains the publish workflow as an operating instruction, not a
      changelog reference
- [x] All five docs above corrected to show `--mode review` → `make publish`
- [x] `docs/HANDOFF.md:48` fixed specifically — that is the line that was followed

**Dependencies:** Task 1. **Files:** 6 docs. **Scope:** S.

**Tasks 1 and 2 DONE 2026-07-31.** `--mode` is required; `_build_parser` was split out of
`_parse_args` so a test asserts on the *configuration* (`required is True` **and**
`default is None`), because argparse silently accepts a default alongside `required=True` —
and a quietly restored default is the regression worth guarding. One existing test relied on
the default and now passes `--mode post` explicitly; B-028's prediction of no programmatic
callers held.

`CLAUDE.md` had **zero** mentions of `--mode review`, `_review`, `make publish` or the
unlisted URL. It now carries the workflow as an operating instruction. Also corrected:
`README.md`, `CONTRIBUTING.md`, `docs/README.md`, `docs/HANDOFF.md` (the line that was
followed), `.github/copilot-instructions.md` — whose cited line 29 had drifted since the RCA,
so the workflow went into its hand-authored Developer Workflow section instead.

#### ~~Task 3~~ — WON'T DO, decided 2026-07-31

**The accident is already prevented three times over**, so removal buys a fourth lock on a
bolted door:

1. `--mode` is required — a bare invocation fails (Task 1).
2. B-030's `PreToolUse` hook **denies** `deploy_to_blog` without `--mode review`.
3. Six documents now describe the review route, `CLAUDE.md` included (Task 2).

What removal *costs* is an escape hatch — republishing, repairing a live post, anything
where review is not the point. And it is a behavioural removal with governance history
(B-015a tuned `deploy()`'s staging for PR scope), so it is not a cheap deletion either.

Recorded rather than deleted: the original reasoning below is sound, and if a fourth
unreviewed publish ever happens *despite* all three gates, this is the item to reopen.

<details><summary>Original Task 3 rationale (kept for the record)</summary>

If review → promote is the sanctioned route, `--mode post` may have no remaining
role: `promote_review.py` already writes `_posts/` on the live branch. Retiring it
would make the unreviewed path *unreachable* rather than merely inconvenient,
which is the difference between a guardrail and a suggestion. But it is a
behavioural removal with a governance history (B-015a tuned `deploy()`'s staging
for PR scope), so it needs a spec and an owner decision — not a quiet deletion.

**Dependencies:** Tasks 1–2. **Scope:** S (spec) + S (removal), owner-gated.

</details>

### B-029 · The acceptance oracle renames its input, so it does not test the deploy path — 2026-07-31

**Found while fixing BUG-069, 2026-07-29.** `scripts/acceptance_blog_frontmatter.sh`
is documented as *the* oracle — "a green local suite says nothing about what the
blog accepts, and only the blog's own scripts are the oracle" — and `HANDOFF.md`
names it as the source of truth. It passed on article two with 0 errors while the
deploy path was producing an **unpublishable filename**.

The reason is line 120: `STAGED="$BLOG/_posts/2026-01-01-${SLUG}.md"`. The oracle
constructs its own dated filename instead of using the one `deploy_to_blog`
produces, which was `_posts/<slug>.md` — undated. **The oracle validated a name
that would never exist.** An oracle that renames its input is not testing the
deploy path; it is testing a hypothetical one.

`scripts/validate-posts.sh` cannot catch it either — it globs `_posts/*.md`
itself rather than asking Jekyll, so an undated file validates happily. The only
gate that would notice is the blog's own `build` (html-proofer/Jekyll), which runs
on a PR and was never reached because #1169 was closed.

**Acceptance criteria:**
- [x] The oracle stages the article under the **filename the deploy path
      produces**, rather than composing its own
- [x] Given a deploy path that emits an undated filename, the oracle **fails**
      (the BUG-069 reproduction — it currently passes)
- [x] The existing pass on a correctly-dated article is unchanged
- [x] The date the oracle injects into front matter stays fixed, so the run is
      deterministic — only the *filename* derivation changes

**Verify:** re-run against `output/posts/review-queue-throughput-tax.md`; confirm
it still passes, then confirm it fails against a deliberately undated copy.
**Files:** `scripts/acceptance_blog_frontmatter.sh`. **Scope:** S.

**Risk if left:** this is the gate the project trusts most, and it has now been
shown to give a false green on a publish-blocking defect. Every future article
inherits that.

**DONE 2026-07-31.** The oracle now derives the staged filename from
`deploy_to_blog._dated_post_name` — the deploy path's own function — instead of composing
`2026-01-01-${SLUG}.md`.

Deriving correctly was **not sufficient**, which is the part worth recording. B-029 already
noted that `validate-posts.sh` globs `_posts/*.md` itself rather than asking Jekyll, so an
undated file validates happily there; the oracle therefore cannot delegate the check. A new
`is_publishable_post_name` predicate lives next to `_dated_post_name`, and the oracle asserts
on it and exits 1 with a named reason. The injected front-matter date stays pinned at
`2026-01-01`, so only the *filename* derivation changed and the run is still deterministic.

The BUG-069 reproduction runs as a test rather than being asserted statically: with
`_dated_post_name` stubbed back to its no-op behaviour, the guard exits non-zero. It is the
same defect *class* as B-031 — a check that could not fail the thing it existed to check.

---

### Harness engineering (B-030 … B-034) — opened 2026-07-29, shipped 2026-07-31

> **Source:** an audit of this repo against *SE Radio 730 — Birgitta Boeckeler on
> Harness Engineering for AI Agents*. Full findings in
> `docs/reviews/harness-engineering-assessment-2026-07-29.md`; spec in
> `docs/specs/harness-engineering.md`.
>
> **The finding in one line.** This repo is **guide-maximal and
> sensor-disconnected**: 8,031 lines of `SKILL.md` plus a strong sensor inventory
> (ruff, mypy, pytest, bandit, four custom guards) with **zero hooks** wiring them
> together — so every sensor fires at the owner's gate rather than the agent's, and
> the owner performs triage an agent could have done mid-session.
>
> Boeckeler's framework splits harness work into **guides** (feed-forward: markdown,
> codemods) and **sensors** (feedback: static analysis, tests — "that starts another
> little loop where the agent tries to self-correct and then asks the sensor again").
> Her warnings land squarely on **B-028** (*"a guide the default ignores"*) and
> **B-029** (*"if my pipeline is always green… I would get suspicious"*) — those two
> items are this episode's central failures, already self-diagnosed. B-030…B-034
> generalise the fix.
>
> **Implementation order: B-034 → B-031 → B-032 → B-030 → B-033.** B-030 is the
> highest-leverage item but not the first: 034 and 031 shrink the surface, 032
> supplies the sensor 030 calls, and 033's value depends on 030's session recording.
>
> **Status 2026-07-29: all five BUILT on `fix/article-two-run-defects`, `make ci-local`
> green** (2515 passed, 9 skipped, coverage 80.38%, `src/quality` 97%, bandit clean).
> They stay in Todo until merged — per this file's convention, "done" means merged to
> `main` via reviewed PR, and the owner is the merge gate (ADR-0015). Three decisions
> are flagged for the owner in the spec's Open Questions: whether the `Stop` gate should
> also run tests, whether mypy's per-commit enforcement is the right trade, and which
> unmeasured guides to cut.

### B-030 · Sensors must fire in the agent's loop, not only at the owner's gate

**The gap.** There is no project `.claude/settings.json` at all;
`.claude/settings.local.json` holds 122 permission entries and **no `hooks` key**. The
only hooks anywhere are two user-level `terminal-notifier` calls. Every computational
sensor is bound to `pre-commit`, `pre-push`, or `make ci-local`. An agent can therefore
write 200 lines of Python and end its turn with the tree red and no signal having reached
it; the owner discovers this later, with the agent's context already stale.

**The fix — five hook wirings** in a committed `.claude/settings.json`:

| Event | Matcher | Behaviour |
|---|---|---|
| `PostToolUse` | `Edit\|Write` | On `*.py`: format + autofix the touched file, then feed anything remaining (plus complexity findings from B-032) back as `additionalContext`. |
| `PreToolUse` | `Bash` | **Deny** forbidden-key introduction and `deploy_to_blog` without `--mode review`. |
| `PreToolUse` | `Write\|Edit` | Same deny set on the file-write path. |
| `Stop` | — | Red tracked-Python tree → `decision: "block"` **once per session**, violations as the reason. |
| `SessionStart` | — | Inject the five non-negotiable constraints, branch, and open `B-` items. |

**Why the `PreToolUse` denies matter more than they look.** `CLAUDE.md` constraint #1 —
**"NO new API keys. Ever."** — is the most emphatic sentence in the repo and has *zero*
computational backing (grepped: neither `destructive_change_guard.py` nor
`pre_commit_arch_check.py` mentions `OPENAI_API_KEY`). B-028 is the same shape: the review
stage is prose, and the tool's default ignores it. **A policy expressed as a guide is
skippable; expressed as a deny it is not.** This item does not touch
`deploy_to_blog.py`'s default — that stays B-028's call — it makes the policy hold from
the harness side either way.

**Acceptance criteria:**
- [x] `.claude/settings.json` is committed; `jq -e` resolves every hook command
- [x] Each hook returns a valid payload and exit 0 for its documented stdin
- [x] A forbidden-key `Bash` command is denied; `git status` is not
- [x] `deploy_to_blog --mode post` is denied; `--mode review` is not
- [x] `session_gate` blocks on first call, **does not block** on the second with the same
      `session_id` (an unbounded blocking `Stop` hook is a session trap — this is the
      guardrail, not a nicety)
- [x] Malformed stdin → exit 0, empty payload, for **every** hook (a broken sensor must
      degrade to no sensor, never to a blocked developer)
- [x] `logs/sensor_history.jsonl` gains a snapshot line per edit; gitignored

**Side benefit — revives dead code.** `scripts/agent_trace_logger.py` is a complete,
schema-versioned, secret-redacting trace logger whose **only importer is its own test**.
It becomes the snapshot writer, closing the observability gap Boeckeler describes ("how
did the number of analysis violations evolve?").

**Files:** `.claude/settings.json`, `scripts/hooks/*`, `.gitignore`,
`tests/test_harness_hooks.py`. **Scope:** M.

### B-031 · Four sensors cannot currently fail

**The gap.** A green run proves nothing, because four gates are structurally incapable of
going red:

| Sensor | Why it is inert |
|---|---|
| mypy | `stages: [manual]`, `strict = False`, `check_untyped_defs = False`, **and** `ci-local` wraps it in `\|\| echo "advisory"` — while `CLAUDE.md` says "Type hints mandatory" |
| coverage (pre-push) | `stages: [manual]` → never runs; and `make test` says 40 while `ci-local` says 70 |
| badge validation | `entry: bash -c '... \|\| true'` — cannot fail, by construction, on a hook whose stated purpose is preventing BUG-023 |
| `validate-skills` | registered **twice** under the same `id`, second copy has `always_run: false` duplicated as a YAML key |

**The fix.** mypy becomes a real per-commit hook on the files being committed (repo-wide
mypy stays advisory — 611 known errors is a separate project, and the `ci-local` comment
now says so instead of implying debt-free). One coverage number, in one place. `|| true`
deleted. Duplicate registration deleted.

**Acceptance criteria:**
- [x] No pre-commit hook entry contains `|| true` — asserted by test
- [x] No hook `id` appears twice — asserted by test
- [x] `make test` and `make ci-local` declare the **same** `--cov-fail-under`
- [x] `pre-commit run --all-files` fails when a checked condition actually fails

**Cross-reference, not scope.** **B-029** is the same class of defect — an oracle that
renames its input and so cannot fail — but it lives in the blog deploy path and B-029 owns
its fix. Both items are instances of one rule: *a sensor that cannot fire is worse than no
sensor, because it manufactures confidence.*

**Files:** `.pre-commit-config.yaml`, `Makefile`, `tests/test_harness_config.py`.
**Scope:** S.

### B-032 · Nothing regulates complexity — the characteristic AI-code failure mode

**The gap.** `ruff.toml` selects `E, W, F, I, UP, B, C4, SIM`. No `C901`, no `PLR`, no
`max-complexity` (grepped: zero hits). Measured during the audit:

```
41  C901     complex-structure     worst: generate_economist_post (33 > 10),
                                   validate (28), review_writer_output (24)
28  PLR0912  too-many-branches
21  PLR0913  too-many-arguments
18  PLR0915  too-many-statements
```

Boeckeler names over-long functions and cyclomatic complexity as *the* typical failure
modes of AI-written code, "even with the big models." In a repo where an agent writes most
of the code, this dimension is unregulated.

**The fix — her ESLint technique, ported.** `scripts/complexity_sensor.py` wraps ruff and
rewrites the output into a *judgment call* rather than a bare number: this is usually a
smell, consider splitting it, and **if the complexity is genuinely warranted you may keep
it by recording an override in `docs/harness-overrides.md` with a one-line justification —
not a bare `noqa`.** The recorded overrides become the owner's review queue, which is the
whole point: it is the tuning nobody does by hand.

Enforcement is scoped to **touched files** via B-030's `PostToolUse` hook — where new
complexity is actually born — so the 41-violation legacy baseline is *recorded* rather
than retroactively enforced, and `ci-local` still passes on day one.

**Acceptance criteria:**
- [x] An over-complex function yields the judgment-call text and a non-zero exit
- [x] A clean file yields no output and exit 0
- [x] `--changed` scopes to `git diff --name-only`, skipping non-Python paths
- [x] `make ci-local` still passes (legacy backlog recorded, not enforced retroactively)
- [x] `docs/harness-overrides.md` exists with the register format and the day-one baseline

**Files:** `scripts/complexity_sensor.py`, `ruff.toml`, `docs/harness-overrides.md`,
`tests/test_complexity_sensor.py`. **Scope:** S.

### B-033 · The guide layer has never been measured, so it can only grow

**The gap.** 8,031 lines across 38 `SKILL.md`, plus a 210-line `CLAUDE.md`, a **2,601-line**
`.github/copilot-instructions.md`, a `GEMINI.md`, and a root `copilot-instructions.md`.
Nothing measures whether any of it changes an outcome. Product evals exist
(`logs/article_evals.json`); **harness** evals do not.

> "I just don't see the future as being like 50 markdown files in our code base… and then
> in every markdown file we have very, very important, do the following, never do the
> following. I mean, that can't be it. Can we still call ourselves engineers if that's how
> we're doing stuff?"

Her sharper point: many skills are *model-authored*, so the model may already know their
content — in which case the file is pure context cost.

**The fix.** `scripts/skill_eval.py`: `--list` for cheap triage (line count + mtime, so
big-old-unreferenced surfaces first); `--skill <name>` runs the skill's `eval.yaml`
scenarios with and without the skill in context and reports the delta against the existing
deterministic scorer. A skill with no `eval.yaml` reports **`UNMEASURED`** rather than
passing silently. Deterministic and `--dry-run` by default, so it is free to run and
cannot fail on auth.

**Acceptance criteria:**
- [x] `--list` reports all 38 skills, largest first
- [x] A skill with `eval.yaml` produces a with/without delta
- [x] A skill without one reports `UNMEASURED`; `--strict` exits non-zero
- [x] No LLM call on the default path

**Non-goal: deletion.** This item produces evidence. Cutting any skill — including the
2,601-line copilot file — is the owner's call.

**Files:** `scripts/skill_eval.py`, `tests/test_skill_eval.py`. **Scope:** M.

### B-034 · The harness offers the agent tools its own guides forbid

**The gap.** `.mcp.json` still ships two servers whose declared `env` is prohibited:

| Server | Requires | Forbidden by |
|---|---|---|
| `image-generator` | `OPENAI_API_KEY` | constraints #1/#2/#4; ADR-0014 retired the DALL-E path |
| `web-researcher` | `SERPER_API_KEY` | constraints #1/#2/#3; removed by #438 |

`.claude/settings.local.json` sets `enableAllProjectMcpServers: true`, so both load every
session and the agent is shown *"Generates Economist-style editorial illustrations using
DALL-E 3. Requires the OPENAI_API_KEY"* directly beside the guide forbidding it.

> "It also cannot be just like throwing 100 tools at the agent and like 50 sensors that
> kind of overload it."

**The fix.** Delete the `image-generator` entry; name the keyless servers explicitly instead
of auto-approving all; and assert the absence in a test so a future re-add fails locally
rather than silently contradicting `CLAUDE.md`.

**One correction found while implementing.** `web_researcher_server.py` is **already
keyless** — #438 stripped the Serper leg, and the module now exposes only `search_arxiv`
and `fetch_page`, both permitted by constraint #3. Deleting the server (as first planned)
would have removed a legitimate keyless research tool. Only the stale `env` block and the
misleading description came out; the server stays.

**Acceptance criteria:**
- [x] `.mcp.json` contains exactly the six keyless servers
- [x] No `OPENAI_API_KEY` / `SERPER_API_KEY` / `GEMINI_API_KEY` anywhere in `.mcp.json`
- [x] No MCP server declares an `env` block — a stricter, more durable invariant than
      name-matching, since any `env` requirement is a key requirement in disguise
- [x] A test fails if any is reintroduced (`test_harness_config.py`)
- [x] `enableAllProjectMcpServers` replaced by an explicit `enabledMcpjsonServers` list

**Scope call:** `mcp_servers/image_generator_server.py` and its passing test are left in
place. The finding was that the harness *offers* a forbidden tool; deleting the entry closes
that. Moving the module would churn a green suite for no harness benefit, and ADR-0014
already retired the workflow.

**Files:** `.mcp.json`, `.claude/settings.local.json`, `tests/test_harness_config.py`.
**Scope:** XS — smallest diff in the set, and it deletes a live contradiction.

### B-035 · Close the three harness decisions B-030…B-034 deliberately left open — 2026-07-31

**Opened 2026-07-30. DONE 2026-07-31.** B-030…B-034 shipped with three questions routed to
the owner rather than guessed at. All three were then **measured** (2026-07-30) and each had
one recommended path. This item was the execution.

**Outcome.** All three landed, in the order 3(b) → 2 → 1 → 3(a). Spec:
`docs/specs/b035-harness-decisions.md`.

| Task | Result |
|---|---|
| **3(b)** | Three defects, not one. The append bug; an unbounded `split` that would silently discard content; and both JSON extractors reading `skills/` when the state files live in `data/skills_state/`. The third was found while checking the regeneration was lossless — it would have **dropped** two of three pattern families. `.github/copilot-instructions.md`: 2,601 → 819 lines, 20 sections → 1, 58 → **84** patterns, zero lost. |
| **2** | `scripts/mypy_baseline.py` + `docs/mypy-baseline.md`. Baseline is 11 files / 30 errors, not the measured 12: `sync_copilot_context.py` was **fixed** rather than grandfathered (four annotations). A test fails if any count grows *or* if an improved file keeps its allowance, so the baseline can only shrink. `CLAUDE.md` keeps "Type hints mandatory" — a test asserts it. |
| **1** | Stop gate now runs `tests/test_X.py` for each changed `X.py`, 60s cap, lint-only fallback. Found in build: the gate's own test file matches its mapping rule, so it spawned a pytest that re-entered the gate. Added a reentrancy guard bounding recursion at depth one. |
| **3(a)** | Owner approved "delete + index page" 2026-07-31. 20 dirs deleted, `using-agent-skills` kept. Guide layer **8,031 → 2,243 lines**, better than the ~2,700 estimate. `docs/workflow-lifecycle.md` is the replacement index. |

**Open question, answered.** The docs site's republishing of the upstream skills was *not*
deliberate. The decisive evidence: those copies were never what got loaded — every skill
invocation resolves to the `agent-skills` plugin directory and prints it. They were unread
and free to drift.

#### Task 1 — the `Stop` gate should run scoped tests, not just lint (S)

| Measurement | Value |
|---|---|
| Full suite | ~100s |
| One matching test file | **3.4s** (6.2s wall) |
| `scripts/` modules with a matching `tests/test_<name>.py` | **40 of 48 (83%)** |

The objection was cost, and the measurement removes it: don't run the suite, run the
*matching* files. Lint regulates maintainability only; a red test is the correctness
signal, which the podcast calls the most important and least solved feedback loop. The
one-block-per-session bound already caps the downside.

- [x] Changed `scripts/X.py` maps to `tests/test_X.py`; only matching files run
- [x] 60s cap; on timeout or no match, fall back to lint-only (never block on a timeout)
- [x] Lint stays the always-on part — tests are additive, not a replacement
- [x] A test asserts the fallback path does not block

**Files:** `scripts/hooks/session_gate.py`, `tests/test_harness_hooks.py`. **Scope:** S.

#### Task 2 — mypy needs a baseline, not a weaker guide (S)

| Measurement | Value |
|---|---|
| `scripts/*.py` mypy-clean under `--follow-imports=silent` | 36 of 48 |
| Would block a commit **merely by being touched** | **12 (25%)** |

As shipped, one commit in four touching `scripts/` is blocked by errors it did not
introduce — including `publication_validator.py`, `editorial_board.py` and, pointedly,
`destructive_change_guard.py`. That is the noise-overload failure mode that gets a gate
reverted to `manual`, which is how mypy went inert in the first place.

**Do not delete "Type hints mandatory" from `CLAUDE.md`.** Record the 12 known-dirty files
as a baseline and block only on errors outside it. B-032 already built this exact
mechanism for complexity (`docs/harness-overrides.md`); mypy should reuse it rather than
invent a second answer to the same question. One mechanism, two sensors — and with a
baseline the guide becomes *true* for all new code instead of aspirational.

- [x] Baseline records the 12 files, with the error count each is grandfathered at
- [x] A **new** error in a baselined file still blocks (baseline is per-file count, not a mute)
- [x] Baseline shrinks only — a test fails if a file's grandfathered count grows
- [x] `CLAUDE.md` keeps "Type hints mandatory"; the baseline is what makes it honest

**Files:** `.pre-commit-config.yaml`, `docs/harness-overrides.md` (or a sibling),
`tests/test_harness_config.py`. **Scope:** S.

#### Task 3 — cut ~5,300 of 8,031 guide lines without losing one instruction (M)

The reference-count hypothesis from the audit was **wrong** — every skill is referenced ≥3
times via the mkdocs nav, so it discriminates nothing. Two stronger signals replaced it.

**(a) The local skills are duplicates of a repo that loads from elsewhere.**

| Finding | Lines |
|---|---|
| Byte-identical to upstream `addyosmani/agent-skills` | 15 skills, **4,488** |
| Diverged by 2–4 lines only (trivial) | 4 skills, ~1,120 |
| Genuinely diverged — `using-agent-skills`, the Skill Routing Contract | 32 of 174 lines |
| Local-only domain skills (economist-writing, python-quality, …) | 17 skills — **keep all** |

Decisive: **every skill invoked during the 2026-07-29 session loaded from
`/Users/ouray.viney/code/agent-skills/skills/`, not from `economist-agents/skills/`** (each
invocation prints its base directory). The repo's own skills are not in the invocable skill
list at all — `CLAUDE.md` reaches them as file paths. Those 4,488 lines are not a guide the
agent reads; they are a stale copy of one it reads from somewhere else.

**(b) `.github/copilot-instructions.md` is not a 2,601-line guide — it is a generator bug.**
`scripts/sync_copilot_context.py` **appends** its "Learned Anti-Patterns" section instead of
replacing it. There are now **20 of them** (16 distinct, most 85 lines); 2,267 of 2,601
lines sit below the first heading.

- [x] `sync_copilot_context.py` replaces rather than appends; file regenerated
      (**do this regardless of the rest — it is a bug fix, not a decision**)
- [x] The 19 vendored upstream skill copies deleted; `using-agent-skills` kept for its
      32 lines of local routing contract
- [x] `CLAUDE.md` Key Skills section points at the plugin, not at deleted paths
- [x] mkdocs nav entries for the deleted skills removed
- [x] All 17 domain skills untouched
- [x] `make ci-local` green; `validate_skills.py` still passes on what remains

**Net: 8,031 → ~2,700 lines with zero instructions lost**, because everything deleted
duplicates something that loads from elsewhere.

**Open question that gates (b) only:** the public docs site currently republishes those 19
upstream skills. If republishing addyosmani's skills under `oviney`'s docs was deliberate,
that changes Task 3(a) — it does not change 3(b) or Tasks 1–2.

**Files:** `scripts/sync_copilot_context.py`, `.github/copilot-instructions.md`, 19
`skills/*/` directories, `CLAUDE.md`, `mkdocs.yml`. **Scope:** M, owner-gated on the docs
site question.

---

### B-038 · Ingest Claude HTML artifacts as research briefs — 2026-07-31

**Opened 2026-07-31. Built 2026-07-31 — LGTM'd, implemented, all boxes ticked.** Spec:
`docs/specs/html-research-ingestion.md`.

The owner researches by holding a back-and-forth conversation with Claude and finalising it
as an **HTML artifact**, and does this often. The pipeline cannot consume HTML: `--brief`
expects markdown at `docs/research/<slug>.md`. The only route today is manual transcription.

**The measurement that shaped the design.** `load_brief_file` does exactly two things — read
the file and strip `## Refuted…` sections — and `stage3_runner.py:249` then hands the result
to the writer **verbatim**. So there is no schema: the only hard requirements are *markdown*
and *`## Refuted` is honoured*. The `ai-productivity-brief.md` layout is a convention the
deep-research harness happens to emit, not an interface.

That turns the build from **claim extraction into faithful conversion**, which is the correct
answer for artifacts whose shape varies with the conversation. A claim-extractor would have
to guess the shape of every conversation and would silently drop what it did not recognise.

**No LLM in the middle.** ADR-0018 measured what that costs: fidelity defects — a statistic
quoted with its offsetting clause deleted, a conclusion imported into a paper that does not
report it — survived four gates and cost a BLOCK at 51/100 on an article the deterministic
evaluator passed at 88%. A paraphrase step sits exactly where that damage originates. The
brief's job is transport; the judging already happened in the conversation.

- [x] `scripts/html_to_brief.py`: HTML → `docs/research/<slug>.md`, deterministic (bs4,
      already installed — no new dependency, no key, no network)
- [x] Quotes, tables and URLs preserved verbatim; nothing silently dropped
- [x] Always emits an empty `## Refuted / unverified` section — content moved there is
      excluded *by construction*, which is the highest-value thing the tool can do
- [x] Round-trip asserted against the real `load_brief_file`, not a mirrored regex
- [x] Usable on a real artifact without re-typing any content

**Scope:** M. **Files:** `scripts/html_to_brief.py`, `tests/test_html_to_brief.py`,
`tests/fixtures/html_briefs/*.html`.

**What the build added beyond the spec, and why.** Two things, both forced by the owner's
real artifact rather than imagined:

1. **Inline `<svg>` diagrams are labelled, not flattened.** Claude draws diagrams as inline
   SVG, and the owner's artifact carries an 18-label causal-loop diagram. Flattened into a
   paragraph its labels read as a sentence — *"Schedule Pressure Feature Velocity + – DELAY
   B1 R1"* — which is precisely the ADR-0018 fidelity hazard: the writer would treat a
   diagram key as a claim. Every label is kept, prefixed with *"Diagram (inline SVG in the
   source) — labels only:"*. Nothing invented, nothing dropped, no longer mistakable for prose.
2. **The no-drop promise is a runtime sensor, not just a test.** `find_dropped_words()`
   compares the source's content tree against the emitted markdown on every run and warns.
   Mutation-checked: adding `table` to `CHROME_TAGS` makes it report 48 lost words, so the
   invariant has teeth rather than being decorative.

**Samples are gitignored.** `docs/research/samples/*.html` holds the owner's own research
conversations and this repo is public, so they stay local. The sample-backed test converts
whatever is there and skips with an explicit reason when the directory is empty — a fresh
clone is green *and* honest about not having seen a real artifact.

**Known limit, deliberately not fixed.** Semantic styling carried only by CSS class
(`div.card-header`, `div.subtitle`) converts to a plain paragraph, losing its heading role
but not its text. Inferring headings from class names would be guessing at whatever CSS a
given conversation emitted; promoting one is a one-character edit in the brief.

### B-036 · Badge validation has no implementation — decide whether to restore it — 2026-07-31

**Opened 2026-07-31**, found by B-031 doing its job.

The `badge-validation` pre-commit hook ran `python3 scripts/validate_badges.py` to prevent
stale README badges (BUG-023). That script was archived to `scripts/archived/` in `3cbe96d`
(#327/#343). The hook was **inert twice over**: its entry was `bash -c '... || true'`, which
swallowed both the stale-badge failures it existed to catch *and* the `No such file or
directory` error proving it had no implementation.

B-031 removed the `|| true`. The next push then failed — which is the sensor working
correctly, and is how the missing script came to light at all.

**The hook is removed, not resurrected.** Pointing it at the archived copy would not restore
the gate: that script resolves its paths relative to `scripts/` (so it looks for
`scripts/README.md` and `scripts/data/skills_state/…`), several inputs it wants no longer
exist, and it exits 0 while printing failures — a third way it could not gate.

`tests/test_harness_config.py::TestHooksPointAtRealScripts` now fails if **any** local hook
references a script that does not exist, which generalises the defect class.

**DONE 2026-07-31.** Owner chose to restore it. **The badges were in fact stale**, which
settled the question — the validator was rebuilt, not merely re-pointed.

Three live defects, all caught by the new validator on its first run against the real README:

| Badge | Defect |
|---|---|
| `CI` | referenced `.github/workflows/ci.yml` — **deleted** when ADR-0015 retired GitHub Actions CI |
| `Quality Tests` | referenced `.github/workflows/quality-tests.yml` — **also deleted** |
| `Python` | advertised **3.13** while `.python-version` pins **3.12** |

So the front page claimed CI this project deliberately does not have, for months, while the
gate that existed to prevent exactly that could not run.

`scripts/validate_badges.py` is narrow on purpose — it checks the two things that actually
rot, and it resolves every path from the repo root rather than from `scripts/`, which is the
bug that made the archived copy look for `scripts/README.md`.

- [x] Decide: restore badge validation (the badges were stale, so the answer was clear)
- [x] A validator that resolves paths from the repo root and exits non-zero on failure
- [x] A test proving it *can* fail — `TestTheRealReadme` runs it against the real README, and
      `TestExitCodes` asserts a stale badge exits 1
- [x] `scripts/archived/validate_badges.py` deleted — it was a trap
- [x] Hook re-wired with `.venv/bin/python`, not `python3`: the old entry used system python,
      which here is 3.14 and carries none of the project's dependencies. A third way it
      could not have worked.
- [x] README badges corrected: `Docs` (a workflow that exists), a static `local-first`
      verification badge, `Python 3.12`, MIT. A note records why there is no CI badge.

**Scope:** S. **Follow-up:** see B-037 — the pin and the interpreter disagree.

### B-037 · `.python-version` pins 3.12 but the venv runs 3.13.14 — 2026-07-31

**Opened 2026-07-31**, found while fixing B-036's Python badge.

Correcting the badge required deciding which version is authoritative, and the two disagree:

| Source | Version |
|---|---|
| `.python-version` | **3.12** |
| `.venv/bin/python` (what `make ci-local` actually runs) | **3.13.14** |
| `CONTRIBUTING.md` | "Python 3.12 (pinned in `.python-version`; single version per ADR-0015)" |

ADR-0015 says Python is pinned to **one** version via `.python-version`, and ADR-0004
constrains the version. The badge now follows the declared pin, which is the only defensible
choice for a *declaration* — but the tests are green on an interpreter the pin forbids, so
the declaration is not what is being verified.

This is not urgent — 2,595 tests pass on 3.13 — but it means "pinned to one version" is
currently untrue, and nothing detects that.

**DONE 2026-07-31. Owner chose 3.13.**

The drift was worse than this item recorded. Surveying every declaration turned up **four**
different versions, not two:

| Source | Claimed | Now |
|---|---|---|
| `.python-version` | 3.12 | **3.13** |
| `CONTRIBUTING.md` | 3.12 | 3.13 |
| `ruff.toml` `target-version` | **py311** | py313 |
| `mypy.ini` `python_version` | **3.11** | 3.13 |
| `README.md`, `GEMINI.md`, ADR-0004 | 3.13 | unchanged — already right |
| the interpreter running the suite | 3.13.14 | unchanged — already right |

So 3.13 was not a coin-flip: the documentation majority and reality already agreed on it,
and `.python-version`, `CONTRIBUTING.md`, `ruff.toml` and `mypy.ini` were the four outliers.
The two *tool* pins were the real find — nothing in B-037 knew about them, and linting
against py311 while running 3.13 silently forgoes three releases of modernisation checks.

`tests/test_python_version_consistency.py` now checks every declaration **against the pin
rather than against a literal**, so the next bump is a one-line change to `.python-version`
and the tests keep working. A test hardcoding 3.13 would only relocate the drift.

- [x] Decide which is authoritative: bumped `.python-version` to 3.13
- [x] Align `CONTRIBUTING.md`
- [x] A test asserting the running interpreter matches `.python-version` — plus `ruff.toml`,
      `mypy.ini`, `CONTRIBUTING.md` and the README badge, since all four had drifted too

**No cascade from the tool bumps:** `ruff check .` is clean at py313, and the mypy baseline
is unchanged at 30 errors across 11 files under `python_version = 3.13`.

**Scope:** XS to decide, S to enforce. **Owner-gated** on which version is wanted.

### B-023 · Decide the fate of `llm_client.py`'s Anthropic auth path — 2026-07-31

Surfaced 2026-07-28 while reconciling `backup/integration-test-20260728`, a
Mac-only branch that was never pushed. Almost everything on it had already
landed on `main` by other routes (the paid-search-API removal, BUG-047's
code-fence recovery, the arXiv `papers_analyzed` fix). Two things had not:

1. **The model bump — TAKEN.** Cherry-picked as `3988dad`; `llm_client.py` was
   still defaulting to the deprecated `claude-sonnet-4-20250514`.
2. **The auth work — NOT TAKEN, needs a decision.** The branch taught
   `_create_anthropic_client` to honour an `ant` OAuth profile /
   `ANTHROPIC_AUTH_TOKEN` instead of requiring `ANTHROPIC_API_KEY`
   (`tests/test_anthropic_auth_resolution.py`,
   `docs/specs/anthropic-auth-token-resolution.md` — both absent from `main`).

**The decision:** `create_llm_client` is the **legacy paid path** — Stage 1
topic discovery needs `ANTHROPIC_API_KEY` (BUG-046), and **B-010 exists to
retire it**. So the auth work either (a) makes a keyless-ish route work on a
path we intend to delete, or (b) is genuinely useful if that path survives.
There is also a constraint question: Operating Constraint #1 forbids new API
keys, and an `ANTHROPIC_AUTH_TOKEN` is still a credential — arguably in the
spirit of #3 (the Claude subscription) rather than against it, but that is a
call for the owner, not an inference.

**Answer B-010's scope first**, then either port the branch's auth commit
(`73e73c0`) or delete `backup/integration-test-20260728`. Do not delete the
branch before this is answered — it is the only copy.

**DECIDED 2026-07-31: do not port. The question is dissolved, not answered.**

The branch's work teaches `_create_anthropic_client` to accept an `ANTHROPIC_AUTH_TOKEN` or
an `ant` OAuth profile *instead of* `ANTHROPIC_API_KEY`. Both branches of the original
question — "is a token a new key (#1) or the subscription (#3)?" — assume the path needs a
credential at all.

It does not. **BUG-046 was fixed by making `create_llm_client` default to a keyless Agent
SDK provider** (see BUG-046 in Done), so Stage 1 topic discovery and Stage 2 editorial
review now run on the subscription with **no token of any kind**. Porting auth work to
authenticate a path that no longer authenticates would be strictly worse than doing nothing.

`backup/integration-test-20260728` can now be deleted — the only thing on it that had not
landed elsewhere was this auth commit, and it is moot.

**DELETED 2026-07-31**, on the owner's instruction, after verification:

| Check | Result |
|---|---|
| Present on `origin`? | **No** — local-only, so it really was the only copy |
| Tip SHA | **`6104a4c`** (`Merge branch 'chore/stage3-strip-code-fence' into local/integration-test`) |
| Auth commit | **`73e73c0`** — the one unlanded change, made moot by BUG-046 |
| Source files present on the branch but absent from `main` | 18, **all deliberate removals**: `agent_registry.py` (ADR-0012), `orchestrator_agent.py` / `po_agent.py` / `sm_agent.py` (CrewAI-era, cleaned up in #327/#343), `src/backlog/migrate_backlog_to_github.py` (local-backlog migration), `src/agent_sdk/image_gate.py` (ADR-0014) |

Nothing on it was unlanded work. **Recoverable from `6104a4c`** via
`git branch <name> 6104a4c` until the objects are garbage-collected (~90 days by default) —
which is why the SHA is recorded here rather than only in the reflog.

**Correction: "it is the only copy" was never true.** Checked after deleting —
`git branch --contains 73e73c0` still returns **`chore/anthropic-auth-token-resolution`**.
The backup branch was a *merge* of six `chore/*` branches, and every one of them still
exists locally:

```
chore/anthropic-auth-token-resolution   ece6f7e   <- carries the auth commit 73e73c0
chore/stage3-strip-code-fence           6cd181c
chore/fix-chart-embed-chart-only        38f9b9b
chore/harden-free-research              8dbd612
chore/remove-mcp-serper-path            b1e08fa
chore/remove-paid-research-apis         c99fda2
```

So the caution that shaped this item for three days was based on an unverified claim, and
one `git branch --contains` would have dissolved it. That is the same pattern B-027 exists
to remedy and that ~~B-025~~ was recorded for: **asserting from a surface reading instead of
measuring.** Third instance. Recorded here rather than quietly fixed, because the pattern is
the finding.

### ~~B-025~~ · WITHDRAWN — the defect record was never at risk — 2026-07-29

Opened on the claim that `.gitignore`'s `data/*` left
`data/skills_state/defect_tracker.json` untracked, so BUG-066/067/068 existed only
on one laptop. **The claim was false and the item is void.**

`git ls-files` shows the tracker has been tracked all along, and tracked files are
unaffected by `.gitignore`. `git cat-file -p HEAD:…` confirms all three defects are
committed in `8e34ef5`, all `resolved`.

The mistake: `git add` printed *"The following paths are ignored… data/skills_state"*
— a hint about the **directory** pattern — and that was read as the add having
failed. It had not; the already-tracked file was staged regardless and went into
the commit. A hint was mistaken for an error, and a whole backlog item was built
on it before anyone checked `git ls-files`.

Recorded rather than deleted because it is the second instance in one session of
asserting a defect from a surface reading instead of measuring — the first being
the hero "clipping" that a four-line pixel check disproved. That pattern is the
actual finding here, and **B-027** is its concrete remedy.

### B-027 · Hero framing is measured — but it cannot be adjudicated — 2026-07-29

**Scoped as a clipping detector; shipped as a measurement, because the detector is
not achievable.** That negative result is the finding worth keeping.

The trigger: a hero was reported as having a clipped top card. It did not. The
claim came from glancing at a thumbnail, and a four-line border-pixel check
disproved it — at the cost of a $0.49 redraw that fixed nothing. The nine
structural rules check viewBox, aspect ratio, element counts and text bans; none
measured framing. Real clipping *has* happened (B-020: a clipped queue stack, a
chart line off the right edge), so the gap was real.

`report_edge_contact()` measures the rendered PNG rather than the SVG — a true SVG
bounding box needs transform composition and path-data parsing, which is hard and
prone to false failures on valid geometry.

**Two design corrections, both found by testing rather than reasoning:**

1. *Coverage thresholds do not work.* The first implementation flagged a full-bleed
   floor band, because a band spanning the full width necessarily puts a partial
   run on **both** vertical edges. Full-bleed is now excluded structurally: a
   border pixel counts only when the perpendicular line through it is not uniform.
2. *Intent is invisible.* Run against the real heroes, the check fires on both —
   and correctly so. The shipped hero has a desk rect from `x=0` stopping at
   `x=680`: it bleeds off one side deliberately, and that is **geometrically
   identical** to a shape accidentally clipped. No pixel test can separate them.

So it reports what is true ("content meets the left edge across 10% of it without
crossing the frame") and leaves the verdict to a human. It is **not** folded into
`defects`, so it never drives a redraw or the exit code — letting unadjudicated
observations spend money is the mistake that started this item.
`TestEdgeContactIsAMeasurementNotAVerdict` pins the limitation so nobody later
suppresses the "false positives"; they are not false, they are unjudged.

9 tests in `tests/test_hero_edge_contact.py`, including the full-bleed control that
the first implementation failed. Wired into `hero_author._author` at INFO.

### B-026 · B-024 criterion 3 now holds for every research mode — 2026-07-29

B-024 shipped the research-failure policy for `claude_web` and `deterministic` but
left `deep` unguarded, which meant its own criterion 3 ("on any
`--research-mode`") was not true. `build_deep_research_brief` has its own
duplicated `_RESEARCH_BRIEF_GUARDRAILS` and its own
`_format_brief(topic, findings)`, so `_acquire_research_brief` returned whatever it
produced with no emptiness check — the exact hole BUG-067 was. The deferral was
honest (B-012 leaves `deep` unexercised, so a guard there would be untested code)
and a unit test removed the objection.

**Writing the guard found a case the `claude_web` predicate would have missed.** A
deep brief whose *every* subquestion answers `- No evidence found.` carries no
evidence at all, yet is not string-equal to a freshly formatted empty brief — so
the equality check that suffices for `claude_web` returns "has findings" for it.
`deep_research.brief_has_findings` therefore checks both: string-equality with the
empty brief, **and** whether any bullet is something other than the no-evidence
line. `_NO_EVIDENCE_LINE` is now a named constant so the formatter and the
predicate cannot drift apart.

Also collapsed the duplicated downgrade block into `_fallback_to_deterministic()`,
so the policy and its warning live in one place for every mode that can come back
empty. 8 tests in `tests/test_research_failure_fallback.py`; `make ci-local` green.

### B-022 · The DALL-E branch is gone from `EconomistContentFlow` — 2026-07-28

`image_mode="hero"` called `generate_featured_image`, warned that
`OPENAI_API_KEY` was unset, and fell back to `blog-default.svg` — which the
deploy path rejects as `default_image_fallback`. Its graceful degradation
degraded into an unpublishable article. Constraints #1–#4 forbid it; ADR-0014 had
already retired DALL-E. B-021 had stopped it changing what the pipeline produces,
leaving `image_mode` with one live value and one dead one, so the argument went
too. `test_flow_image_mode.py` → `test_flow_image_contract.py`: no mode left to
test, but the contract that branch existed to satisfy still needs pinning —
including the control proving `blog-default.svg` is rejected, which is why this
was a removal and not a repair.

### Close-out defects — 2026-07-28

- **BUG-064 · graphics retries could spend 3× the cap.** `_GRAPHICS_MAX_ATTEMPTS`
  handed every attempt the FULL `graphics_budget_usd` instead of the remaining
  balance. The mirror image of BUG-061 — silent *overspend* rather than
  under-funding — which is why it never aborted a run and sat unnoticed until
  BUG-061 sent me reading the neighbouring loop.
- **BUG-065 · production escape: the hero-prompt comment reached the blog.** The
  `<!-- HERO IMAGE … -->` block published live and sat in the page source. Gated
  at the **deploy boundary**, not in `publication_validator`: the comment is
  injected *after* Stage 4 by design, so the validator cannot see it, and it is
  legitimate in the local artifact — illegitimate only on the blog. Guards both
  `deploy()` and `deploy_review()` (a review deploy is a live URL too) and fires
  before any clone. Rejects rather than strips: stripping would hide that no hero
  was drawn. Removed from the live post in `oviney/blog#1168`.

### B-021 · The next run cannot abort, hang, or default to a dead mode — 2026-07-28

B-020 proved the pipeline works but deferred three defects it exposed, all of
which cost a real ~$1 / ~35-min run to hit. Spec:
`docs/specs/B-021-run-safety-cleanups.md`.

- **BUG-061 (writer budget) — FIXED.** `_WRITER_MAX_ATTEMPTS=3` with a $0.60
  cumulative default and a measured ~$0.42 per attempt funded exactly ONE
  attempt, so a malformed first draft — a *handled* condition — aborted the run
  with the SDK's generic budget error. The cumulative cap stays (it is the only
  runaway guard); the default is now **derived** from
  `_WRITER_ATTEMPT_COST_USD × _WRITER_MAX_ATTEMPTS` so the two cannot drift, and
  an unfundable retry is refused before dispatch with the arithmetic and the flag
  name in the message.
- **BUG-059 (no wall clock) — FIXED, wider than logged.** Every SDK collector now
  runs under `asyncio.timeout` and raises a typed `ModelCallTimeoutError` naming
  the call. The bug named `_collect_text`, but `research/_llm.py` and
  `research/claude_web.py` had the identical unbounded `async for` — and research
  is the longest, costliest leg, so it is where a stall is likeliest. Bounds are
  measured, not guessed: 900s per Stage 3 call, 300s per research orchestration
  call, 900s for the web-research leg. `hero_author` already bounded itself.
- **BUG-060 + `--image-mode` — RESOLVED BY DELETION** (owner call, 2026-07-28).
  `hero` was the DEFAULT and was dead: it ran the retired handshake, told the
  operator to paste a prompt into chat.openai.com, and exited 10 without reaching
  Stage 4. `chart_only` was the only working mode and, since B-016b, ships a
  Claude-drawn hero — so its name lied too. Removed `--image-mode`, `--resume`,
  `--no-image`, `image_gate.py`, the handshake/resume/state machinery, and exit
  codes 10/11 (**retired, not reused**). One path remains. Hand-supplied art now
  means overwriting `output/posts/images/<slug>-hero.svg` and re-running.

**Also found, logged not fixed:** **BUG-064** — `_graphics_with_retry` hands every
attempt the FULL `graphics_budget_usd` instead of the remaining balance, so 3
attempts can spend 3× the stated cap (the mirror image of BUG-061). **B-022** —
the flow's DALL-E branch, now provably dead.

Suite 2377 green, `make ci-local` green.

### B-020 · Full end-to-end acceptance PASSED — 2026-07-27

**A fully generated article cleared the blog's own validators with 0 errors** —
front matter, chart, and a Claude-drawn hero, nothing hand-touched. This is
B-016b's success criterion 1 and the last gate before article two.

```
validate-posts:        PASSED — all posts valid
validate-post-quality: ✅ code-review-queue-throughput-tax.md   Errors: 0
ACCEPTANCE PASSED — generated front matter clears the blog's gate.
```

Reproduce with `scripts/acceptance_blog_frontmatter.sh <blog-clone> <article.md>`.

**It took five runs, and each one exposed a different real defect that no test
could have caught.** That is the headline finding, worth more than any single fix:

| Run | Died at | Defect |
|---|---|---|
| 1 | writer budget | **BUG-061** — retries share one budget, so a malformed first attempt starves the retry meant to recover from it |
| 2 | hero step | `asyncio.run()` inside a running loop; all 20 hero tests called it synchronously |
| 3 | chart render | **BUG-063** — graphics had no retry while the writer has three |
| 4 | acceptance gate | `chart_only` stripped `image_alt`/`image_caption` and injected a "generate an image" comment, both premised on there being no hero |
| 5 | acceptance gate | `image_alt` rejected as prompt text |

Also caught in passing: **BUG-062 (CRITICAL)** — wiring the hero into Stage 3 made
`make ci-local` issue real LLM calls, because `hero_author` holds its own
`_collect_text` reference. The gate went from timing out at 900s to 119s once
`netguard` blocked the SDK chokepoint.

**The nicest fix:** `image_alt` now comes from the hero SVG's own `<desc>`. The
writer's alt is a drawing *brief* ("An Economist-style editorial illustration
of…") which the blog rejects as prompt text; the `<desc>` describes what was
actually drawn, so it is both more accurate and clean of prompt vocabulary.

**Measured cost of one article:** ~$0.97–$1.35 and ~35 minutes, including the
hero (~20 min, ~$0.66) and the graphics retries — which fired on **2 of 3
attempts** in the passing run.

**Hero quality, looked at (Constraint #4):** usable, not excellent. The editorial
idea lands — a small figure dwarfed by a towering queue, burndown flatlining below
— but the top card is clipped, the chart line runs off the right edge, and the
figure is crude. The vision critique reported all three correctly, which is the
design working: gate passes, critique reports, human decides.


### B-016b · Stage 3 draws the hero SVG automatically — 2026-07-27

Spec: `docs/specs/B-016b-automatic-hero-svg.md` (owner LGTM). **Verified end to
end: Claude drew a usable hero from the article's own `image_alt` brief with no
human input.** The blocker is cleared — the pipeline can now produce an article
with a resolvable `image:`, which both blog validators require.

Shipped: `hero_svg.py` (9-rule structural gate + headless-Chrome render),
`hero_author.py` (draw loop + vision critique), Stage 3 integration, and the CLI
exit policy from the spec's three-row failure table.

**What actually determines quality: a worked example, not rules.** With the
rulebook alone the output passed all nine structural rules and was still clipart —
dot-eyed cartoon figure, a "shadow" reading as a beige wedge, no editorial idea.
Adding a condensed extract of the shipped hero to the system prompt (full-bleed
background, few large forms, silhouettes not faces, separation strokes on overlaps)
moved it to usable in one change with nothing else different.

**Three spec assumptions were wrong, each independently fatal.** Measured by
instrumenting the SDK message stream: a draw is ~440s of thinking, then one
~3,700-char TextBlock at 454s, costing $0.4534.
- `max_turns=1` → thinking consumes turns, so it died with "Reached maximum number
  of turns (1)" before any text arrived. Now 4.
- 240s timeout → below the 454s floor; some draws exceed 600s. Now 600s.
- $0.40 budget → below the actual $0.4534. Now $0.75.

**The critique is a good reporter and an unreliable judge.** It correctly caught a
queue stack clipped at the top and right edges, and a figure's stool legs clipped at
the bottom — but it also called deliberate negative space a defect, and it never
converged (real defects on every attempt across three runs). So retries went from
the spec's 2 to 1, and it stays a reporter, never a gate.

**Cost per article: ~20 min, ~$0.66** for the hero, on top of writer + graphics.
That is the honest figure to weigh against hand-authoring one.

Also found and filed **BUG-059**: `_collect_text` bounds cost but not wall clock, so
any Stage 3 call — writer and graphics included — can stall the pipeline with no
diagnostic. The hero's own calls are bounded here as a local mitigation.

Still open: **multiple figures per post**, deliberately out of scope (see spec).


### B-015 · economist-agents PRs must satisfy oviney/blog's governance gates — 2026-07-26

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

**RESOLVED 2026-07-26 (B-019).** Measured with
`scripts/acceptance_blog_frontmatter.sh`: **both** blog scripts require `image:`,
and `validate-post-quality.sh` check 1 errors with "hero image not set". So the
answer is the first option — **always author a hero**; chart-only is simply not a
publishable mode. Tracked as a blocker in **B-016b**.

### B-019 · Generated front matter now clears the blog's gate — 2026-07-26

Spec: `docs/specs/B-019-frontmatter-contract-alignment.md`. Closed the four
generator-side gaps that made every future article fail the blog's
`validate-editorial` job, and built the acceptance oracle that proves it.

- **Slug ≤50 chars** through `canonical_slug()` — the single B-008 seam, so the
  filename, chart PNG, chart embed, and prompt sidecar all move together. Drops
  stop-words, strips possessives, trims **whole trailing words** (never mid-word,
  which is the failure `URL_SLUG_POLICY.md` exists to prevent). The real 76-char
  flaky-tests title now yields 46. A writer-proposed `slug:` is honoured when it
  matches the blog's shape; the derivation is the guarantee.
- **`categories`** rewritten to the blog's exact form — inline, double-quoted,
  values validated against the blog's four, off-list dropped, block-style YAML
  converted. Tags now derive *after* canonicalisation so an off-list value cannot
  leak into them.
- **`subtitle`** backfilled from the description (≤40 words) when the writer omits
  it, and requested distinctly in the Stage-3 prompt.
- **Placeholder `image:`** stripped — the prompt used to ask for a literal
  `/assets/images/SLUG.png`, which can never resolve. The prompt no longer asks
  for an image path at all.
- **Guardrail:** the pipeline now prints `slug: <value> (N chars, <source>)` at
  generation time. The URL is permanent — no `jekyll-redirect-from` — so it should
  be reviewable in one line, not inferred from an output path.
- **`scripts/acceptance_blog_frontmatter.sh`** — runs a pipeline-finalized article
  through the blog's two real validators in a real clone. **This is the oracle**;
  `make ci-local` was green through all four of the original gate failures.

Verified: acceptance **0 errors** against the blog's own scripts; `make ci-local`
green; 38 new tests.

**Found while verifying:** `image:` is mandatory on the blog, so there is no
publishable chart-only article. B-016b promoted to blocker; B-015's open item
resolved. See `docs/blog-integration-constraints.md`.


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
**BUG-046 fully resolved 2026-07-31** (was resolved-by-workaround below).
`create_llm_client` now defaults to a keyless `agent_sdk` provider running on the
Claude subscription, so `EconomistContentFlow` Stage 1 (topic discovery) and
Stage 2 (editorial review) need no key. Operating Constraint #3 now holds *by
construction*: the keyless provider wins even when `ANTHROPIC_API_KEY` is set, so
a stray key cannot silently start billing. Legacy paid providers survive only as
an explicit `LLM_PROVIDER=anthropic|openai` opt-out, and naming one without its
key is an error rather than a silent fallback. 9 new tests in
`tests/test_llm_client_keyless.py`; `tests/test_llm_client.py` updated, since it
encoded the old auto-detect-from-key behaviour. This also dissolves **B-023** —
there is nothing left to authenticate.

Original entry: BUG-047/048/049/050/051. BUG-046 resolved-by-workaround: the two-step
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

