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

> **Opened 2026-07-29 from the article-two run.** **B-025** was withdrawn the same
> day (see below); **B-026** and **B-027** landed the same day (see Done). Ids are
> never reused, so all three numbers stay spent. **B-028** and **B-029** are open,
> both from the RCA on the skipped review stage.
>
> **Opened 2026-07-29 from the harness audit.** **B-030 … B-034** come from auditing
> this repo against SE Radio 730 (harness engineering). They generalise B-028 and
> B-029: a guide the default ignores, and a sensor that cannot fail. See the
> "Harness engineering" section below.

### B-028 · The unreviewed publish path must stop being the default

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

- [ ] `deploy_to_blog` with no `--mode` exits non-zero with a message naming both
      modes and pointing at the review workflow
- [ ] No code caller breaks — `git grep` finds **no** programmatic callers, only
      docs, so this is safe
- [ ] A test asserts the missing-mode failure, so a future tidy-up cannot restore
      a silent default

**Verify:** new test; `make ci-local`. **Files:** `scripts/deploy_to_blog.py`, one test.

#### Task 2 — document the workflow where it governs behaviour (S)

- [ ] `CLAUDE.md` gains the publish workflow as an operating instruction, not a
      changelog reference
- [ ] All five docs above corrected to show `--mode review` → `make publish`
- [ ] `docs/HANDOFF.md:48` fixed specifically — that is the line that was followed

**Dependencies:** Task 1. **Files:** 6 docs. **Scope:** S.

#### Task 3 — decide whether `--mode post` should exist at all (needs a spec + LGTM)

If review → promote is the sanctioned route, `--mode post` may have no remaining
role: `promote_review.py` already writes `_posts/` on the live branch. Retiring it
would make the unreviewed path *unreachable* rather than merely inconvenient,
which is the difference between a guardrail and a suggestion. But it is a
behavioural removal with a governance history (B-015a tuned `deploy()`'s staging
for PR scope), so it needs a spec and an owner decision — not a quiet deletion.

**Dependencies:** Tasks 1–2. **Scope:** S (spec) + S (removal), owner-gated.

### B-029 · The acceptance oracle renames its input, so it does not test the deploy path

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
- [ ] The oracle stages the article under the **filename the deploy path
      produces**, rather than composing its own
- [ ] Given a deploy path that emits an undated filename, the oracle **fails**
      (the BUG-069 reproduction — it currently passes)
- [ ] The existing pass on a correctly-dated article is unchanged
- [ ] The date the oracle injects into front matter stays fixed, so the run is
      deterministic — only the *filename* derivation changes

**Verify:** re-run against `output/posts/review-queue-throughput-tax.md`; confirm
it still passes, then confirm it fails against a deliberately undated copy.
**Files:** `scripts/acceptance_blog_frontmatter.sh`. **Scope:** S.

**Risk if left:** this is the gate the project trusts most, and it has now been
shown to give a false green on a publish-blocking defect. Every future article
inherits that.

---

## Harness engineering (B-030 … B-034) — opened 2026-07-29

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

### B-035 · Close the three harness decisions B-030…B-034 deliberately left open

**Opened 2026-07-30.** B-030…B-034 shipped with three questions routed to the owner
rather than guessed at. All three were then **measured** (2026-07-30) and each has one
recommended path. This item is the execution.

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

- [ ] Changed `scripts/X.py` maps to `tests/test_X.py`; only matching files run
- [ ] 60s cap; on timeout or no match, fall back to lint-only (never block on a timeout)
- [ ] Lint stays the always-on part — tests are additive, not a replacement
- [ ] A test asserts the fallback path does not block

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

- [ ] Baseline records the 12 files, with the error count each is grandfathered at
- [ ] A **new** error in a baselined file still blocks (baseline is per-file count, not a mute)
- [ ] Baseline shrinks only — a test fails if a file's grandfathered count grows
- [ ] `CLAUDE.md` keeps "Type hints mandatory"; the baseline is what makes it honest

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

- [ ] `sync_copilot_context.py` replaces rather than appends; file regenerated
      (**do this regardless of the rest — it is a bug fix, not a decision**)
- [ ] The 19 vendored upstream skill copies deleted; `using-agent-skills` kept for its
      32 lines of local routing contract
- [ ] `CLAUDE.md` Key Skills section points at the plugin, not at deleted paths
- [ ] mkdocs nav entries for the deleted skills removed
- [ ] All 17 domain skills untouched
- [ ] `make ci-local` green; `validate_skills.py` still passes on what remains

**Net: 8,031 → ~2,700 lines with zero instructions lost**, because everything deleted
duplicates something that loads from elsewhere.

**Open question that gates (b) only:** the public docs site currently republishes those 19
upstream skills. If republishing addyosmani's skills under `oviney`'s docs was deliberate,
that changes Task 3(a) — it does not change 3(b) or Tasks 1–2.

**Files:** `scripts/sync_copilot_context.py`, `.github/copilot-instructions.md`, 19
`skills/*/` directories, `CLAUDE.md`, `mkdocs.yml`. **Scope:** M, owner-gated on the docs
site question.

---

### B-015 · economist-agents PRs must satisfy oviney/blog's governance gates

### ~~B-025~~ · WITHDRAWN 2026-07-29 — the defect record was never at risk

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

**RESOLVED 2026-07-26 (B-019).** Measured with
`scripts/acceptance_blog_frontmatter.sh`: **both** blog scripts require `image:`,
and `validate-post-quality.sh` check 1 errors with "hero image not set". So the
answer is the first option — **always author a hero**; chart-only is simply not a
publishable mode. Tracked as a blocker in **B-016b**.

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
