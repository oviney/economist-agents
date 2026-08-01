# Hand-off — 2026-07-31

Written for a fresh session after `/clear`. `BACKLOG.md` stays the source of record; this
file is the "where were we" note a new session reads first, then overwrites when it goes
stale. The 2026-07-30 hand-off (B-030…B-034 close-out) is superseded; its durable warnings
are carried forward below.

**Read next, in this order:** this file → `docs/keyless-pipeline-runbook.md` if you are
generating an article → `BACKLOG.md` (B-015, B-012 are the only open items) →
`docs/specs/b035-harness-decisions.md` only if you need the reasoning behind the harness
gates.

**Session of 2026-07-31 is closed out.** B-028, B-029, B-035, B-036, B-037, BUG-046, B-023
and **B-038** all landed; ADR-0018 accepted; the working tree is clean and both PRs are
`MERGEABLE`. Nothing is half-finished.

## B-038, HTML research ingestion — BUILT 2026-07-31

**`scripts/html_to_brief.py` exists and works.** Spec `docs/specs/html-research-ingestion.md`
was LGTM'd and implemented the same day; `tests/test_html_to_brief.py` is 46 tests, 94%
coverage on the module. Nothing about it is pending.

```bash
python scripts/html_to_brief.py ~/Downloads/conversation.html --slug ai-code-review
# → docs/research/ai-code-review.md   (refuses to overwrite without --force)

IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" --brief docs/research/ai-code-review.md
```

~$1 and ~35 minutes for the run. Then **deploy to review, never straight to `_posts/`** — see
the publishing section below. `--mode` is required (B-028).

**Why it is a converter and not a claim-extractor**, so a fresh session does not re-derive it:
`load_brief_file` does exactly two things — read the file, strip `## Refuted…` — and
`stage3_runner.py:249` hands the result to the writer **verbatim**. **There is no schema.**
The `ai-productivity-brief.md` layout is a convention the deep-research harness emits, not an
interface. So the brief's job is *transport*, and there is deliberately **no LLM in the
middle**: ADR-0018 measured that fidelity defects survived four gates and produced a 51/100
BLOCK on an article the deterministic evaluator passed at 88%.

### The three things worth knowing before you touch it

1. **The `## Refuted / unverified` section is the point.** Every brief ends with it, empty.
   Move a paragraph under that heading and the loader deletes it before the writer ever sees
   it — exclusion by construction, not by the writer's discretion. The tool does **not** try
   to infer what is hedged; that is judgment, and judgment already happened in the
   conversation.
2. **Never-silently-drop is enforced at runtime, not only in tests.** `find_dropped_words()`
   diffs the source's content tree against the emitted markdown on every run and warns.
   Mutation-checked (adding `table` to `CHROME_TAGS` makes it report 48 lost words), so it is
   a sensor that can actually fail — B-031's whole complaint.
3. **Inline `<svg>` diagrams are labelled, not flattened.** Claude draws diagrams as SVG; the
   owner's first real artifact carried an 18-label causal-loop diagram. Flattened it reads as
   prose — *"Schedule Pressure Feature Velocity + – DELAY B1 R1"* — which is the ADR-0018
   hazard exactly: a diagram key mistaken for a claim. Labels are kept and prefixed
   *"Diagram (inline SVG in the source) — labels only:"*.

### Samples are local-only, on purpose

`docs/research/samples/*.html` is **gitignored** (decided 2026-07-31): this repo is public and
the artifacts are the owner's own research conversations. `tests/test_html_to_brief.py`
converts whatever is present and **skips with an explicit reason** when the directory is
empty, so a fresh clone is green *and* honest about never having seen a real artifact. Three
synthetic fixtures (`tests/fixtures/html_briefs/`) cover headings-and-prose, blockquote-heavy
and table-bearing shapes, and the repo's own Claude artifact
(`docs/reviews/review-queue-throughput-tax-42d2fbb4.html`, zero `<a href>`) is a committed
real-HTML regression test.

**Proven against a real owner artifact on 2026-07-31** — an SRE quality-governance CLD guide.
Every word survived; nothing needed re-typing. Two honest limits found on it and left
unfixed, both one-edit-away in the brief: semantic styling carried only by CSS class
(`div.card-header`) becomes a plain paragraph, and an artifact with no `<a href>` produces a
brief with no citations, which the writer path and `citation_verifier` will notice downstream.

## B-039 — the merge gate now runs the pinned toolchain

**Fixed 2026-08-01.** `make ci-local` resolved its tools from ambient `PATH`, so the gate did
not mean the same thing twice: it linted with homebrew's ruff 0.15.9 while
`requirements-dev.txt` pins `ruff==0.14.10` exactly, it could not run at all in a shell
without an activated venv (bare `python`), and its advisory mypy step printed the same
reassuring line for "found 187 errors" and "mypy is not installed".

Every recipe now names `$(VENV_BIN)/<tool>` explicitly, `require-venv` fails with an
instruction instead of falling through to ambient binaries, `make install` creates the venv
if it is missing, and `mypy-advisory` is its own target that fails the gate on exit >1.

**The trap, worth knowing before you touch the Makefile:** `export PATH := …/.venv/bin:$(PATH)`
does *not* do the job on its own, however right it looks. GNU make 3.81 (what macOS ships)
direct-execs recipe lines with no shell metacharacters and resolves them against its own
startup PATH — so `ruff check .` kept using ambient ruff while `mypy …; status=$$?` used the
venv. `tests/test_ci_gate_is_reproducible.py` executes `make` against stub binaries for
exactly this reason; a grep of the Makefile would have passed on the broken fix. Recorded as
the fourth instance in `skills/defect-prevention/SKILL.md`.

Verified from a bare shell — `env -i PATH=/usr/bin:/bin:/opt/homebrew/bin make ci-local` —
green at 2,680 tests, where that same invocation previously died at step 3.

## State in one paragraph

**Both stacked streams merged to `main` on 2026-08-01 and their branches are deleted.**
PR #459 (article-two defects: B-028 Tasks 1–2, B-029, the editorial-review-gate artifacts)
and PR #460 (harness engineering: B-030 … B-035, plus B-038) are in. Merge commits, not
rebases — #459 carried a merge of `main`, which GitHub refuses to rebase. `make ci-local` is
green on `main` at 2,680 tests. No open PRs. Nothing is loose on disk.

## Branches and PRs

**Local branches were cleaned up 2026-07-31: 46 → 13.** 33 were deleted, each verified
merged first — either an ancestor of `origin/main`, or its PR appears in
`gh pr list --state merged`. Squash-merged branches are not ancestors of `main`, so
`--merged` alone would have missed 23 of them; the PR cross-reference is what made them
safe.

The 10 survivors are **deliberately kept** — none is merged and each needs a judgement call:

| Branch | Last commit | Why it is still here |
|---|---|---|
| `chore/anthropic-auth-token-resolution` | 2026-06-28 | **carries `73e73c0`**, the B-023 auth commit. Keep until you are sure you never want it |
| `chore/stage3-strip-code-fence` | 2026-06-28 | unmerged sibling of the same series |
| `backup/pr406-before-main-refresh` | 2026-05-27 | a second backup branch — same provenance question as the one just deleted |
| `feat/309-agent-sdk-stage3-spike` | 2026-05-27 | the Agent SDK spike; 96 commits ahead |
| `copilot/add-{publication-validator,style-memory,web-researcher}-mcp-server` | 2026-04-05 | three MCP server branches |
| `fix-150`, `fix-151`, `fix-153` | 2026-04-05 | MCP import fixes, same vintage |

Everything from April is almost certainly dead, but "almost certainly" is what got B-023
wrong — so they are listed rather than guessed at.

| Branch | PR | Base | Contains |
|---|---|---|---|
| `fix/article-two-run-defects` | **#459** | `main` | BUG-066/067/068, B-024, B-026, B-027, BUG-069, **B-028 Tasks 1–2, B-029, ADR-0018**, and a merge of `main` |
| `harness/close-the-sensor-loop` | **#460** | `fix/article-two-run-defects` | B-030 … B-035 |

**#460 is deliberately stacked on #459**, not on `main` — the harness section in
`BACKLOG.md` is inserted after the B-028/B-029 entries #459 introduces, and those two items
are the concrete examples the whole audit is built on. **Review and merge #459 first.**

## The working tree is clean — the editorial stream has landed

**Resolved 2026-07-31.** The four editorial-review-gate artifacts that had been sitting
uncommitted across several sessions are now committed on `fix/article-two-run-defects`
(`cbf33f5`). Nothing of value is loose on disk any more.

**The ADR was renumbered `0016` → `0018`.** `main` landed ADR-0016 (One Pipeline Path) and
ADR-0017 (Gate Publishable Content at Deploy) while the draft sat on disk, so the number it
was written against was taken. `docs/README.md` documents a single global MADR sequence, and
`lint_adrs.py` now validates 18. Its status stays **Proposed** — committing it
version-controls the argument, it does not decide it.

**Two traps that stream set, both hit before it landed.** They no longer apply, but the
*pattern* recurs whenever untracked files coexist with a tracked file they are referenced
from:

1. A `git reset --hard` destroyed the `mkdocs.yml` nav change once. When one file must carry
   hunks for two streams, write a "mine-only" copy, `git add` it, then restore the combined
   file to the working tree — the staged diff then holds only your hunk.
2. **`adr-lint` fails while an ADR is untracked — on both `git commit` and `git push`.** The
   hook framework stashes unstaged changes, removing the ADR's *nav line* from `mkdocs.yml`,
   but the ADR *file* is untracked and survives the stash, so it looks unreferenced. Move
   the file aside for the operation and back afterwards. It bit twice.

## What landed: B-030 … B-034 (harness engineering)

Audited this repo against **SE Radio 730 — Birgitta Boeckeler on Harness Engineering for AI
Agents**. Findings in `docs/reviews/harness-engineering-assessment-2026-07-29.md`; spec in
`docs/specs/harness-engineering.md`.

**The finding:** the repo was **guide-maximal and sensor-disconnected** — 8,031 lines of
`SKILL.md` plus a strong sensor inventory (ruff, mypy, pytest, bandit, four custom guards)
with **zero hooks** wiring them together. Every sensor fired at the owner's gate.

| Item | What shipped |
|---|---|
| **B-034** | `image-generator` MCP entry removed; explicit server list replaces `enableAllProjectMcpServers`; a test blocks any `env` requirement returning. |
| **B-031** | Four always-green sensors made able to fail: mypy off `stages:[manual]`, `\|\| true` deleted from badge validation, duplicate `validate-skills` removed, one coverage threshold instead of 40-and-70. |
| **B-032** | `scripts/complexity_sensor.py` — C901/PLR wrapper emitting a *judgment call* plus a recorded-override path (`docs/harness-overrides.md`), scoped to touched files. |
| **B-030** | Five hooks in a committed `.claude/settings.json` + `scripts/hooks/*`. |
| **B-033** | `scripts/skill_eval.py` — keyless with/without eval. |

## What landed: B-035 (this session)

The three questions B-030…B-034 routed to the owner, all measured then executed in the order
3(b) → 2 → 1 → 3(a). Spec: `docs/specs/b035-harness-decisions.md`.

### Task 3(b) — `sync_copilot_context.py`: three defects, not one

The known bug was append-instead-of-replace. Two more were in the same function:

1. **Append, not replace.** The insertion point was `content.split(MARKER)[0]`, a prefix
   that still held every earlier section. 20 copies had accumulated; 2,267 of 2,601 lines
   sat below the first generated heading.
2. **Unbounded split.** Reassembly used only `parts[0]` and `parts[1]`, so a doubled marker
   would have silently discarded the rest. Latent — never fired.
3. **Wrong source directory.** Both JSON extractors read `skills/`, but the state files live
   in `data/skills_state/`. Both returned empty and warned. **Found while verifying the
   regeneration was lossless** — without this fix, regenerating would have *dropped* the
   Defect Prevention and Content Quality sections the committed file still carried.

Result: **2,601 → 819 lines, 20 sections → 1, 58 → 84 patterns, zero lost** (pattern IDs
diffed before/after; lines 1–334 byte-identical).

### Task 2 — mypy baseline

`scripts/mypy_baseline.py` + `docs/mypy-baseline.md`. Pre-existing debt is grandfathered per
file; a **new** error still blocks, because the baseline is a count, not a mute. The
baseline can only shrink: `tests/test_mypy_baseline.py` fails if a count grows *or* if an
improved file keeps its old allowance, so raising a number to unblock a commit fails the
suite instead. `CLAUDE.md` keeps "Type hints mandatory" — a test asserts it.

Baseline is **11 files / 30 errors**, not the measured 12: `sync_copilot_context.py` was
fixed rather than grandfathered while landing 3(b). Four annotations were cheaper than an
entry.

### Task 1 — Stop gate runs scoped tests

`scripts/hooks/session_gate.py` now maps each changed `X.py` to `tests/test_X.py` and runs
only those. 60s cap. Every non-red outcome — no match, timeout, pytest missing — degrades to
lint-only. Lint stays always-on; the one-block-per-session bound covers the test path too.

**A defect found in the build, worth remembering:** the gate's own test file matches its
mapping rule, so `handle()` spawned a pytest that re-entered the gate. The suite hung. Fixed
with an env-flag reentrancy guard (`HARNESS_SESSION_GATE_ACTIVE`) that bounds recursion at
depth one, plus two regression tests.

### Task 3(a) — the vendored skills are gone

Owner approved "delete + index page" on 2026-07-31. The question — *was republishing the
upstream skills deliberate?* — resolved to **no**, on decisive evidence: those copies were
never what got loaded. Every skill invocation resolves to
`/Users/ouray.viney/code/agent-skills/skills/` and prints its base directory.

20 directories deleted; `using-agent-skills` kept for its 32 lines of local Skill Routing
Contract; all 17 domain skills untouched. **Guide layer 8,031 → 2,243 lines with zero
instructions lost.** `docs/workflow-lifecycle.md` is the replacement index and links
upstream.

### The hooks, and how to work with them

`.claude/settings.json` is **committed** (`.gitignore` carries `!.claude/settings.json`).
All five hooks route through `scripts/hooks/run_hook.sh`.

| Event | Behaviour you will notice |
|---|---|
| `PostToolUse` (Edit/Write) | Formats and autofixes your `.py` file, then feeds remaining lint + complexity back into context. **Silent when clean.** |
| `PreToolUse` (Bash) | **Denies** paid-key introduction and `deploy_to_blog` without `--mode review`. |
| `PreToolUse` (Write/Edit) | Same deny set for config-file writes. Markdown is exempt. |
| `Stop` | Blocks a red tree **once per session** — now lint **and** scoped tests. |
| `SessionStart` | Injects the five constraints, the branch, and open `B-` items. |

**Three gotchas that will bite you:**

1. **The deny guard blocks literal key assignments inside shell heredocs.** Write long text
   to a file and use `--body-file` rather than inlining it in a shell command.
2. **Every hook exits 0, always.** If a sensor seems not to have fired, it degraded silently
   by design. Check `logs/sensor_history.jsonl` (gitignored) rather than expecting an error.
3. **`ruff format` runs in pre-commit and will reformat staged files**, failing that commit
   attempt. Re-`git add` and re-run — the second attempt passes.

### Verification as of this hand-off

`make ci-local` green on **both** branches after the merge:

| Branch | Result |
|---|---|
| `fix/article-two-run-defects` | 2,446 passed, 9 skipped, coverage 80.46% |
| `harness/close-the-sensor-loop` | **2,594 passed, 9 skipped, coverage 81.26%** |

Threshold is 70; `src/quality` is above 90; bandit, the destructive-change guard and the
mypy baseline gate are all clean. 78 new tests this session: `test_sync_copilot_context.py`
(13), `test_mypy_baseline.py` (26), `test_harness_hooks.py` (+18),
`test_deploy_mode_required.py` (6), `test_acceptance_oracle_filename.py` (15).

Note: `make ci-local`'s repo-wide mypy step stays **advisory** and prints errors from
`scripts/archived/`. That is expected — the blocking gate is `mypy_baseline.py`, which is
scoped to `scripts/*.py` and does not descend into `archived/`.

## Publishing — read this before deploying anything

`--mode` is now **required** on `deploy_to_blog` (B-028). The sanctioned route:

```bash
python -m scripts.deploy_to_blog --article output/posts/<slug>.md --mode review
# read the printed https://<host>/review/<slug>-<token>/ page, then:
make publish SLUG=<slug>
```

This hand-off previously said "Then `deploy_to_blog` opens the PR" — and that is the line
that was followed when article two published unreviewed. `CLAUDE.md` now carries the
workflow as an operating instruction.

## Still open

**Two items, neither of them code in this repo.**

- **B-015** — every article PR needs an admin bypass to merge: `🔒 Security Audit` and
  `🖼️ Visual Regression` fail blog-side for pre-existing reasons (npm CVEs; stale visual
  baselines), both are required checks, and GitHub forbids self-approval. **The fix is in
  `oviney/blog`, not here** — bump its deps and refresh its visual baselines.
- **B-012** — deep-research mode is built; only a live acceptance run remains (~2M tokens).
  Parked as an owner cost decision, not a defect.

Also owner-actionable, but trivial: **`backup/integration-test-20260728` can now be
deleted.** B-023 dissolved, so the auth commit it held is moot and nothing else on it is
unlanded. Left undeleted deliberately — the "only copy" caution was well placed.

### Closed 2026-07-31

- **B-028 Tasks 1–2** — `--mode` is required; a bare invocation fails naming both choices.
  `CLAUDE.md` had **zero** mentions of the review workflow and now documents it, along with
  five other docs.
- **B-029** — the oracle now stages the filename `deploy_to_blog._dated_post_name` produces
  instead of composing `2026-01-01-<slug>.md`. Deriving correctly was **not sufficient**:
  the blog's `validate-posts.sh` globs `_posts/*.md` itself rather than asking Jekyll, so an
  undated file validates happily there. A new `is_publishable_post_name` predicate is
  asserted by the oracle directly.
- **BUG-046 / B-010** — the flow is **keyless end to end**. `create_llm_client` now defaults
  to an `agent_sdk` provider running on the subscription, so `EconomistContentFlow` Stage 1
  and Stage 2 need no key. Constraint #3 holds *by construction*: the keyless provider wins
  even when `ANTHROPIC_API_KEY` is set, so a stray key cannot silently start billing. Paid
  providers survive only as an explicit `LLM_PROVIDER=anthropic|openai` opt-out, and naming
  one without its key errors rather than falling back.
- **B-023** — **dissolved**, not answered. The question was whether porting
  `ANTHROPIC_AUTH_TOKEN` support counts as a new key (#1) or the subscription (#3). Both
  readings assumed the path needs a credential; it no longer does. `backup/integration-test-20260728`
  now holds nothing unlanded and **you can delete it** — left to you, since the "only copy"
  caution was well placed.
- **B-028 Task 3** — **WON'T DO.** The accident is prevented three times over (`--mode`
  required, B-030's hook denies it, six docs). Removal buys a fourth lock on a bolted door
  and costs the escape hatch for republishing. Reopen only if a fourth unreviewed publish
  happens *despite* all three.
- **ADR-0018** — **Accepted.** The 37-point spread (88% PASS vs 51.0 BLOCK on one article)
  decided it. Advisory-first per its own decision 3, so it informs the human who already
  approves at the B-013 stage rather than acquiring a veto.
- **B-037** — **one** Python version now, 3.13, verified rather than asserted. The drift was
  worse than the item recorded: four declarations disagreed, and the two nobody knew about
  were `ruff.toml` (**py311**) and `mypy.ini` (**3.11**) — so the repo was linting against
  py311 while running 3.13, silently forgoing three releases of modernisation checks.
  `tests/test_python_version_consistency.py` checks every declaration *against the pin*, so
  the next bump is a one-line change to `.python-version`. No cascade: ruff clean at py313,
  mypy baseline unchanged at 30.
- **B-036** — badge validation rebuilt. The badges really were stale: `CI` and
  `Quality Tests` pointed at workflows ADR-0015 deleted, and the Python badge disagreed with
  the pin. The front page claimed CI this project deliberately does not have, for months,
  while the gate meant to catch that could not run. `scripts/validate_badges.py` is new,
  resolves paths from the repo root, and exits non-zero; the archived copy is deleted.

### Review queue the owner now owns

- **`docs/mypy-baseline.md`** — 11 files, 30 errors. Every line is debt with a name on it.
- **`docs/harness-overrides.md`** — 2 accepted complexity findings, both in
  `sync_copilot_context.py` and both pre-existing; recorded rather than refactored because
  they were out of scope for a bug fix.

## Things that will bite a fresh session

Carried forward — all still true:

- **A green `make ci-local` says nothing about what the blog accepts.** Four consecutive
  defects were green locally and rejected by the blog. Measured contract in
  `docs/blog-integration-constraints.md`. **See B-029 — the oracle itself is unsound.**
- **The blog repo is `oviney/blog`.** `deploy_to_blog.py`'s usage docstring says
  `viney-blog`; that is the example, not the repo.
- **`image:` is required and there are no redirects.** A published slug is permanent.
- **System python has no pip** — work in `.venv`. `make ci-local` needs `.venv/bin` on
  `PATH` or `ruff` is not found.
- **Exit codes 10 and 11 are retired, not reused.**
- **`_check_placeholders` cannot catch the hero-prompt comment, and that is correct.** Do
  not "helpfully" add a pattern there; it would be dead code.

## Conventions a fresh session must not rediscover

- **`make ci-local` is the merge gate.** `main` is unprotected; you are the gate (ADR-0015).
- **`BACKLOG.md` is the source of record**; PRs live on GitHub via `gh`. No new issues.
- **Five non-negotiable constraints** in `CLAUDE.md` — the `SessionStart` hook injects them.
- **Lifecycle discipline:** `Skill agent-skills:using-agent-skills` first, then the phase
  skill it points at. **Skills load from the `agent-skills` plugin.** As of B-035 Task 3(a)
  this is no longer a trap — the shadowing local copies are deleted, and
  `docs/workflow-lifecycle.md` says so explicitly.
