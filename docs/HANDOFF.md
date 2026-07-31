# Hand-off — 2026-07-31

Written for a fresh session after `/clear`. `BACKLOG.md` stays the source of record; this
file is the "where were we" note a new session reads first, then overwrites when it goes
stale. The 2026-07-30 hand-off (B-030…B-034 close-out) is superseded; its durable warnings
are carried forward below.

**Read next, in this order:** this file → `BACKLOG.md` (B-028, B-029, B-015) →
`docs/specs/b035-harness-decisions.md` if you need the reasoning behind the harness gates.

## State in one paragraph

Two work streams are open, stacked. The **article-two defect stream** sits on
`fix/article-two-run-defects` (PR #459 → `main`) with B-028 and B-029 still to fix. The
**harness engineering stream** sits on `harness/close-the-sensor-loop` (PR #460 → #459),
where B-030 … B-034 **and now B-035** are built, tested and green. Nothing is broken.
`make ci-local` passes on the harness branch. The harness stream is **complete** — #460 is
ready for review once #459 merges.

## Branches and PRs

| Branch | PR | Base | Contains |
|---|---|---|---|
| `fix/article-two-run-defects` | **#459** | `main` | BUG-066/067/068, B-024, B-026, B-027, BUG-069, and the B-028/B-029 RCA notes |
| `harness/close-the-sensor-loop` | **#460** | `fix/article-two-run-defects` | B-030 … B-035 |

**#460 is deliberately stacked on #459**, not on `main` — the harness section in
`BACKLOG.md` is inserted after the B-028/B-029 entries #459 introduces, and those two items
are the concrete examples the whole audit is built on. **Review and merge #459 first.**

## Uncommitted work on disk — do not lose this

These files are on the working tree and belong to the **editorial-review-gate** stream, not
to either PR. They survive a `/clear` but are in no commit:

| Path | What it is |
|---|---|
| `docs/adr/0016-editorial-review-gate.md` | ADR (Proposed) — the deterministic evaluator cannot tell "cited" from "cited correctly" |
| `skills/blog-post-review/` | The rubric skill ADR-0016 adopts as a distinct review stage |
| `mkdocs.yml` (2 unstaged lines) | Nav entries for both of the above |
| `docs/reviews/review-queue-throughput-tax-42d2fbb4.html` | The reviewed draft that motivated ADR-0016 |

They belong on `fix/article-two-run-defects` or a branch of their own — **not** on
`harness/close-the-sensor-loop`.

**Two traps this stream sets, both hit during the B-035 session:**

1. **A `git reset --hard` on the harness branch destroyed the `mkdocs.yml` change once**
   (recovered from a pre-commit stash). B-035 needed to edit the *same file*; the safe
   method was to write a "mine-only" copy, `git add` it, then restore the combined file to
   the working tree — so the staged diff held only the B-035 hunk and the two editorial
   lines stayed unstaged.
2. **`adr-lint` fails while ADR-0016 is untracked — on both `git commit` and `git push`.**
   The hook framework stashes unstaged changes, which removes the ADR-0016 *nav line* from
   `mkdocs.yml`, but the ADR *file* is untracked and survives the stash — so it looks
   unreferenced and the hook errors. Move `docs/adr/0016-editorial-review-gate.md` aside for
   the operation and move it straight back. Expect to do this **twice** per push (once for
   the commit, once for the push); it bit both times this session.

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

`make ci-local` green on `harness/close-the-sensor-loop`: **2,572 passed, 9 skipped,
coverage 81%** (threshold 70), `src/quality` above 90%, bandit clean, destructive-change
guard clean, mypy baseline gate clean. 57 new tests this session across
`tests/test_sync_copilot_context.py` (13), `tests/test_mypy_baseline.py` (26) and
`tests/test_harness_hooks.py` (+18).

Note: `make ci-local`'s repo-wide mypy step stays **advisory** and prints errors from
`scripts/archived/`. That is expected — the blocking gate is `mypy_baseline.py`, which is
scoped to `scripts/*.py` and does not descend into `archived/`.

## Still open

- **B-028** — `deploy_to_blog.py:681` sets `default="post"`, so the documented command
  publishes unreviewed. *(B-030's `PreToolUse` guard already enforces the policy from the
  harness side, but the tool's own default is still wrong.)*
- **B-029** — `acceptance_blog_frontmatter.sh:120` builds its own filename instead of using
  the deploy path's, so the oracle passed on an unpublishable name.
- **ADR-0016** — Proposed, uncommitted. Needs an owner decision.
- **B-015** — every article PR needs an admin bypass to merge: `🔒 Security Audit` and
  `🖼️ Visual Regression` fail blog-side for pre-existing reasons.
- **B-012** — deep-research mode is built; only a live acceptance run remains (~2M tokens).
  Parked as an owner cost decision, not a defect.

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
