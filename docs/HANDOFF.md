# Hand-off — 2026-07-30

Written for a fresh session after `/clear`. `BACKLOG.md` stays the source of record; this
file is the "where were we" note a new session reads first, then overwrites when it goes
stale. The 2026-07-28 hand-off (B-021/B-022 close-out) is superseded; its durable warnings
are carried forward below.

**Read next, in this order:** this file → `BACKLOG.md` (B-028 … B-035) →
`docs/specs/harness-engineering.md` if resuming the harness work.

## State in one paragraph

Two work streams are open, stacked. The **article-two defect stream** sits on
`fix/article-two-run-defects` (PR #459 → `main`) with B-028 and B-029 still to fix. The
**harness engineering stream** sits on `harness/close-the-sensor-loop` (PR #460 → #459),
where B-030 … B-034 are **built, tested and green** and B-035 is specced but not started.
Nothing is broken. `make ci-local` passes on the harness branch.

## Branches and PRs

| Branch | PR | Base | Contains |
|---|---|---|---|
| `fix/article-two-run-defects` | **#459** | `main` | BUG-066/067/068, B-024, B-026, B-027, BUG-069, and the B-028/B-029 RCA notes |
| `harness/close-the-sensor-loop` | **#460** | `fix/article-two-run-defects` | B-030 … B-034 (+ the B-035 spec) |

**#460 is deliberately stacked on #459**, not on `main` — the harness section in
`BACKLOG.md` is inserted after the B-028/B-029 entries #459 introduces, and those two items
are the concrete examples the whole audit is built on. Against `main` the diff was 39 files;
against #459 it is 24. **Review and merge #459 first.**

## Uncommitted work on disk — do not lose this

These files are on the working tree and belong to the **editorial-review-gate** stream, not
to either PR. They survive a `/clear` but are in no commit:

| Path | What it is |
|---|---|
| `docs/adr/0016-editorial-review-gate.md` | ADR (Proposed) — the deterministic evaluator cannot tell "cited" from "cited correctly" |
| `skills/blog-post-review/` | The rubric skill ADR-0016 adopts as a distinct review stage |
| `mkdocs.yml` (modified) | Nav entries for both of the above |
| `docs/reviews/review-queue-throughput-tax-42d2fbb4.html` | The reviewed draft that motivated ADR-0016 |

They belong on `fix/article-two-run-defects` or a branch of their own — **not** on
`harness/close-the-sensor-loop`. A `git reset --hard` on the harness branch destroyed the
`mkdocs.yml` change once already (recovered from a pre-commit stash). Treat that as the
known hazard here.

## What landed: B-030 … B-034 (harness engineering)

Audited this repo against **SE Radio 730 — Birgitta Boeckeler on Harness Engineering for AI
Agents**. Findings in `docs/reviews/harness-engineering-assessment-2026-07-29.md`; spec in
`docs/specs/harness-engineering.md`.

**The finding:** the repo was **guide-maximal and sensor-disconnected** — 8,031 lines of
`SKILL.md` plus a strong sensor inventory (ruff, mypy, pytest, bandit, four custom guards)
with **zero hooks** wiring them together. Every sensor fired at the owner's gate. The human
was the loop.

| Item | What shipped |
|---|---|
| **B-034** | `image-generator` MCP entry removed; explicit server list replaces `enableAllProjectMcpServers`; a test blocks any `env` requirement returning. *Correction: `web_researcher_server.py` is already keyless (#438), so only its stale `env` block came out — the server stays.* |
| **B-031** | Four always-green sensors made able to fail: mypy off `stages:[manual]`, `\|\| true` deleted from badge validation, duplicate `validate-skills` removed, one coverage threshold instead of 40-and-70. |
| **B-032** | `scripts/complexity_sensor.py` — C901/PLR wrapper emitting a *judgment call* plus a recorded-override path (`docs/harness-overrides.md`), scoped to touched files so the 41-violation legacy baseline is not a wall. |
| **B-030** | Five hooks in a committed `.claude/settings.json` + `scripts/hooks/*`. Revives `scripts/agent_trace_logger.py` (previously imported only by its own test) as the sensor-history writer. |
| **B-033** | `scripts/skill_eval.py` — keyless with/without eval. First result: **37 of 38 skills UNMEASURED**. |

### The hooks, and how to work with them

`.claude/settings.json` is now **committed** (`.gitignore` carries `!.claude/settings.json`).
All five hooks route through `scripts/hooks/run_hook.sh`, which resolves the repo root from
its own location and falls back to system `python3`.

| Event | Behaviour you will notice |
|---|---|
| `PostToolUse` (Edit/Write) | Formats and autofixes your `.py` file, then feeds remaining lint + complexity back into context. **Silent when clean.** |
| `PreToolUse` (Bash) | **Denies** paid-key introduction and `deploy_to_blog` without `--mode review`. |
| `PreToolUse` (Write/Edit) | Same deny set for config-file writes. Markdown is exempt. |
| `Stop` | Blocks a red tree **once per session**, then never again. |
| `SessionStart` | Injects the five constraints, the branch, and open `B-` items. |

**Two gotchas that will bite you:**

1. **The deny guard blocks literal key assignments inside shell heredocs.** It blocked the
   first attempt to open PR #460, because the body quoted one while *describing* the guard.
   Left unfixed on purpose (documented in `guard_constraints.py`'s docstring) — write long
   text to a file and use `--body-file` rather than inlining it in a shell command.
2. **Every hook exits 0, always.** If a sensor seems not to have fired, it degraded silently
   by design. Check `logs/sensor_history.jsonl` (gitignored) rather than expecting an error.

### Verification as of this hand-off

`make ci-local` green on `harness/close-the-sensor-loop`: **2515 passed, 9 skipped, coverage
80.38%** (threshold 70), `src/quality` 97%, bandit clean, destructive-change guard clean.
91 new tests across `tests/test_harness_hooks.py`, `test_complexity_sensor.py`,
`test_skill_eval.py`, `test_harness_config.py`.

## What is next: B-035 (specced, not started)

The three questions B-030…B-034 routed to the owner have been **measured**, and each has one
recommended path. Full evidence and acceptance criteria are in `BACKLOG.md` under B-035;
short form:

| Task | Recommendation | Key measurement |
|---|---|---|
| 1 · `Stop` gate scope | **Add scoped tests.** Map `scripts/X.py` → `tests/test_X.py`, 60s cap, lint-only fallback | one test file = **3.4s** vs ~100s for the suite; **83%** of modules have a matching test |
| 2 · mypy policy | **Keep it blocking, add a per-file baseline.** Do *not* weaken `CLAUDE.md` | **12 of 48** `scripts/` files would block a commit merely by being touched (25% friction) |
| 3 · guide reduction | **Fix the generator bug, then delete 19 vendored skill copies.** Keep all 17 domain skills | **15 skills / 4,488 lines byte-identical to upstream**; `.github/copilot-instructions.md` has **20** appended "Learned Anti-Patterns" sections |

**One open question, gating Task 3(a) only:** the public docs site republishes those 19
upstream skills. If that was deliberate, 3(a) changes. It does not affect 3(b) or Tasks 1–2.

**Task 3(b) — the `sync_copilot_context.py` append-instead-of-replace bug — is a bug fix,
not a decision. Do it regardless of the answer.**

## Still open from the article-two stream

- **B-028** — `deploy_to_blog.py:681` sets `default="post"`, so the documented command
  publishes unreviewed. Task 1 makes `--mode` required. *(B-030's `PreToolUse` guard already
  enforces the policy from the harness side, but the tool's own default is still wrong.)*
- **B-029** — `acceptance_blog_frontmatter.sh:120` builds its own filename instead of using
  the deploy path's, so the oracle passed on an unpublishable name. Same defect *class* as
  B-031, different layer.
- **ADR-0016** — Proposed, uncommitted. Needs an owner decision.
- **B-015** — every article PR needs an admin bypass to merge: `🔒 Security Audit` and
  `🖼️ Visual Regression` fail blog-side for pre-existing reasons (npm CVEs; stale visual
  baselines), both are required checks, and GitHub forbids self-approval.

## Things that will bite a fresh session

Carried forward from the 2026-07-28 hand-off — all still true:

- **A green `make ci-local` says nothing about what the blog accepts.** Four consecutive
  defects were green locally and rejected by the blog. The oracle is running the blog's own
  scripts against a clone: `scripts/validate-posts.sh`, `scripts/validate-post-quality.sh`.
  Measured contract in `docs/blog-integration-constraints.md`. **See B-029 — the oracle
  itself is currently unsound.**
- **The blog repo is `oviney/blog`.** `deploy_to_blog.py`'s usage docstring says
  `viney-blog`; that is the example, not the repo.
- **`image:` is required and there are no redirects.** A published slug is permanent.
- **System python has no pip** — work in `.venv`. `make ci-local` needs `.venv/bin` on
  `PATH` or `ruff` is not found.
- **Exit codes 10 and 11 are retired, not reused.** Old notes still mention them.
- **`_check_placeholders` cannot catch the hero-prompt comment, and that is correct** — the
  comment does not exist when the validator runs. The deploy gate is the fix. Do not
  "helpfully" add a pattern there; it would be dead code.

## Not done, on purpose

- **B-012** — deep-research mode is built; only a live acceptance run remains (~2M tokens).
  Parked as an owner cost decision, not a defect.
- **B-033 does not delete anything.** It produces evidence; cutting guides is B-035 Task 3
  and is the owner's call.

## Conventions a fresh session must not rediscover

- **`make ci-local` is the merge gate.** `main` is unprotected; you are the gate (ADR-0015).
- **`BACKLOG.md` is the source of record**; PRs live on GitHub via `gh`. No new issues.
- **Five non-negotiable constraints** in `CLAUDE.md` — the `SessionStart` hook now injects
  them, so a new session sees them without reading the file.
- **Lifecycle discipline:** `Skill agent-skills:using-agent-skills` first, then the phase
  skill it points at. Skills load from the `agent-skills` plugin, **not** from this repo's
  `skills/` directory — that is the B-035 Task 3 finding.
