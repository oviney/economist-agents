# Spec — B-035: close the three harness decisions B-030…B-034 left open

**Status:** In progress · **Opened:** 2026-07-30 · **Branch:** `harness/close-the-sensor-loop`

B-030…B-034 shipped with three questions routed to the owner rather than guessed at. All
three were measured on 2026-07-30 (evidence in `BACKLOG.md` under B-035). This spec turns
the three recommendations into implementable, testable slices.

Execution order — **3(b) → 2 → 1 → 3(a)**. 3(b) is a bug fix and is independent of
everything else; 3(a) was owner-gated and was approved on 2026-07-31 (see Task 3(a)).

---

## Task 3(b) — `sync_copilot_context.py` must replace, not append

### Problem

`PatternExtractor.update_copilot_instructions` (`scripts/sync_copilot_context.py:292`)
inserts a freshly formatted `## Learned Anti-Patterns` section before
`## Additional Resources` **without removing the section it inserted last time**. The
insertion point is computed as `content.split("## Additional Resources")[0]`, and that
prefix still contains every previously generated section.

Measured state of `.github/copilot-instructions.md`:

| Fact | Value |
|---|---|
| `## Learned Anti-Patterns` headings | **20** (lines 335…2505) |
| Total lines | 2,601 |
| Lines below the first generated heading | **2,267** |
| Hand-authored instruction lines | 334 (lines 1–334) + `## Additional Resources` (2594+) |

So 87% of the file Copilot loads is the same section repeated twenty times.

### Second defect in the same function

`content.split("## Additional Resources")` is unbounded, and the reassembly uses only
`parts[0]` and `parts[1]`. If the marker ever appeared twice, everything from the third
part onward would be **silently discarded**. It appears once today, so this has not fired —
but it is a data-loss bug in the same six lines and is fixed here rather than left armed.

### Required behaviour

1. Every existing `## Learned Anti-Patterns` section is removed before the new one is
   written. A "section" runs from its `## ` heading to the next `## ` heading at the same
   level, or to end-of-file.
2. Exactly one such section exists after a sync, regardless of how many existed before.
3. Running the sync N times in a row produces byte-identical output to running it once
   (idempotence), holding the generated date constant.
4. Hand-authored content above the first generated section and the `## Additional
   Resources` section below it are preserved verbatim.
5. Splitting on the insertion marker is bounded (`maxsplit=1`) so no content can be dropped.
6. `--dry-run` still writes nothing.

### Acceptance criteria

- [ ] A test builds a file with 3 pre-existing generated sections and asserts exactly 1 remains
- [ ] A test asserts sync-twice == sync-once (idempotent)
- [ ] A test asserts hand-authored prose above and `## Additional Resources` below survive
- [ ] A test asserts a doubled `## Additional Resources` marker loses no content
- [ ] A test asserts `--dry-run` leaves the file unmodified
- [ ] `.github/copilot-instructions.md` regenerated: 20 sections → 1

### Non-goals

Not rewriting the extractors, the formatter, or the section's content. The section's
*shape* is correct; only its accumulation is wrong.

---

## Task 2 — mypy needs a per-file baseline, not a weaker guide

### Problem

B-031 took mypy off `stages: [manual]`, making it able to fail for the first time. The
measurement then showed the cost: **12 of 48 `scripts/*.py` files (25%) would block a commit
merely by being touched**, on errors the commit did not introduce — including
`publication_validator.py`, `editorial_board.py` and `destructive_change_guard.py`.

That is the noise-overload failure mode that gets a gate reverted to `manual`, which is
exactly how mypy went inert originally.

### Decision

**Do not weaken `CLAUDE.md`.** "Type hints mandatory" stays. Record the known-dirty files
with the error count each is grandfathered at, and block only on errors beyond that count.
B-032 already built this mechanism for complexity (`docs/harness-overrides.md`); mypy reuses
it rather than inventing a second answer to the same question.

A baseline makes the guide *true for all new code* instead of aspirational.

### Required behaviour

1. A baseline file records each known-dirty file and its grandfathered error count.
2. A **new** error in a baselined file still blocks — the baseline is a per-file count, not
   a mute.
3. A file absent from the baseline blocks on its first error.
4. The baseline may only shrink. A test fails if any file's recorded count grows, or if a
   file that is now clean is still listed.

### Acceptance criteria

- [ ] Baseline records the 12 files with per-file counts
- [ ] New error in a baselined file blocks (count exceeded)
- [ ] Baseline-shrinks-only test present and passing
- [ ] `CLAUDE.md` keeps "Type hints mandatory"

---

## Task 1 — the `Stop` gate should run scoped tests, not just lint

### Problem

The `Stop` hook regulates maintainability (lint) but not correctness (tests). The podcast's
point — and the reason this was left open — is that a red test is the correctness signal,
and the objection to running it was cost. The measurement removes the objection:

| Measurement | Value |
|---|---|
| Full suite | ~100s |
| One matching test file | **3.4s** (6.2s wall) |
| `scripts/` modules with a matching `tests/test_<name>.py` | **40 of 48 (83%)** |

### Required behaviour

1. A changed `scripts/X.py` maps to `tests/test_X.py`; only matching files run.
2. A 60s cap. On timeout, or when nothing matches, fall back to lint-only — **never block on
   a timeout**.
3. Lint stays the always-on part. Tests are additive, not a replacement.
4. The existing one-block-per-session bound still caps the downside.

### Acceptance criteria

- [ ] Changed `scripts/X.py` → `tests/test_X.py` mapping, matching files only
- [ ] 60s cap; timeout and no-match both fall back to lint-only
- [ ] Lint remains always-on
- [ ] A test asserts the fallback path does not block

---

## Task 3(a) — delete the vendored upstream skill copies

**Owner-gated; approved 2026-07-31** with the "delete + index page" option.

### Evidence

Re-measured on this branch against `/Users/ouray.viney/code/agent-skills/skills/`:

| Category | Count |
|---|---|
| Byte-identical to upstream | **15** |
| Diverged by 2–4 lines (cosmetic) | **5** (`browser-testing-with-devtools`, `idea-refine`, `incremental-implementation`, `spec-driven-development`, `test-driven-development`) |
| Genuinely diverged — the local Skill Routing Contract | **1** (`using-agent-skills`, 32 lines) |
| Local-only domain skills | **17** — keep all |

Decisive: every skill invoked during the 2026-07-29 and 2026-07-31 sessions loaded from
`/Users/ouray.viney/code/agent-skills/skills/`, not from `economist-agents/skills/` — each
invocation prints its base directory. These are not a guide the agent reads; they are a
stale copy of one it reads from elsewhere, and nothing compares the two, so they can only
drift.

### Required behaviour

1. The 20 vendored copies are deleted. `using-agent-skills` is **kept** for its 32 lines of
   local routing contract.
2. All 17 domain skills are untouched.
3. The mkdocs nav's workflow-skills section is replaced by a single lifecycle index page
   that names the phases and links to upstream `addyosmani/agent-skills`.
4. `CLAUDE.md`'s Key Skills section points at the plugin, not at deleted paths.
5. `validate_skills.py` still passes on what remains.

### Acceptance criteria

- [ ] 20 vendored dirs deleted; `using-agent-skills` and all 17 domain skills remain
- [ ] Lifecycle index page exists and is in the nav; no nav entry points at a deleted path
- [ ] `CLAUDE.md` Key Skills references the plugin
- [ ] `make ci-local` green; `validate_skills.py` passes

---

## Verification for all four slices

`make ci-local` (ruff, mypy, pytest + coverage 70% / `src/quality` 90%, bandit,
destructive-change guard) must be green before push. ADR-0015: `main` is unprotected and
there is no GitHub Actions CI — this is the merge gate.
