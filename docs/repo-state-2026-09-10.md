# State of the repo — 2026-09-10

> **CORRECTED 2026-09-10** after an adversarial review (Fable 5.1) refuted two figures below.
> Both corrections were re-verified independently. See
> `docs/reviews/2026-09-10-fable-complexity-review.md` §0.
>
> 1. **The production line count was an 11% undercount.** The walk covered only `src/` and
>    `scripts/`; `agents/` (2,483 lines) and `mcp_servers/` (1,568) are production Python too.
>    Non-archived total is **~39,800**, not 35,505.
> 2. **"Zero orphans" was wrong**, and wrong in the direction that flattered the repo. It
>    conflated *named in a config* with *named in a doc*. Adding every genuinely wired entry
>    point still leaves **47 modules / 17,554 lines** that no `Makefile`, `.pre-commit-config.yaml`,
>    `.claude/settings.json` or `.mcp.json` references. They are orphans with documentation, and
>    a large deletion **is** available — roughly 19,200 lines of code at low risk.
>
> The rest of the document stands as measured. It is left uncorrected in place so the error is
> visible: the first walk stopped at two directories and the classifier accepted a doc mention
> as a live caller.

A handoff snapshot for a fresh session. Every number here was measured on 2026-09-10 by
running something, not by reading a previous document. Commands are given so each figure can
be re-taken rather than trusted.

**Bottom line:** the merge gate is green, the pipeline works, and the repository is roughly
**two-thirds tooling about the pipeline rather than pipeline**. Nothing is dead; that is the
problem worth looking at.

---

## 1. What this repo actually produces

A multi-agent pipeline that writes Economist-style articles and publishes them to
`oviney/blog`. The blog clone lives at `temp_blog_repo/` (gitignored).

| Measure | Value |
|---|---|
| Published posts on the blog | **30** (`temp_blog_repo/_posts/`) |
| Posted 2026-07 or later — the keyless-pipeline era | **6** |
| Distinct drafts in `output/posts/` | 5, of which 3 are variants of one topic, plus `test.md` |

Publication history by month: 2023-12 ×1, 2025-12 ×1, 2026-01 ×6, 2026-04 ×16, 2026-07 ×1,
2026-08 ×5. The 2026-04 cluster predates the current architecture.

```bash
ls temp_blog_repo/_posts/ | sed 's/^\([0-9]*-[0-9]*\).*/\1/' | sort | uniq -c
```

## 2. Code inventory

```bash
for d in src scripts tests; do find $d -name '*.py' -not -path '*/archived/*' \
  -exec cat {} + | wc -l; done
```

| Area | Files | Lines |
|---|---|---|
| `src/` | 37 | 11,155 |
| `scripts/` | 61 | 24,350 |
| **Production subtotal** | **98** | **35,505** |
| `tests/` | 164 | 48,554 |
| `scripts/archived/` | 38 | 11,805 |
| **Total Python** | **300** | **95,864** |

Test-to-production ratio: **1.37 : 1**.

Largest single modules: `publication_validator.py` (1,497), `economist_agent.py` (1,239),
`_shared.py` (1,097), `skills_gap_analyzer.py` (1,060), `topic_scout_reproducibility.py` (923).

## 3. The finding that matters: reachability

Static import-graph walk from the 12 real entry points — the pipeline
(`src/agent_sdk/pipeline.py`), the flow, the deploy/art/publish scripts, and every check
`make ci-local` runs:

| | Modules | Lines | Share |
|---|---|---|---|
| Reachable from an entry point | 43 | 15,662 | 45% |
| **Not reachable from any entry point** | **48** | **18,891** | **55%** |

**But none of it is dead.** Classifying those 48 by whether anything references them:

| Category | Lines |
|---|---|
| Named in a config, Makefile, or doc — standalone tools with a caller | 16,929 |
| No config reference, but has tests | 1,962 |
| **No reference and no tests — genuinely orphaned** | **0** |

That zero is the important number. There is no dead-code cleanup available here. The 18,891
lines are a **second system**: quality metrics, defect tracking, architecture auditing, skills
gap analysis, A/B scout comparison, GA4/GSC ETL, dashboards, closed-loop validation, sensor
proofs. Each is documented, most are tested, and every one was built deliberately.

The question a reviewer should ask is therefore not "what is dead?" but **"what does this
second system buy, per article, at six articles?"**

Representative members (lines, all unreachable from the pipeline):
`economist_agent.py` 1,239 · `skills_gap_analyzer.py` 1,060 ·
`topic_scout_reproducibility.py` 923 · `defect_tracker.py` 813 · `validate_closed_loop.py` 737 ·
`audit_composite_scores.py` 715 · `ab_topic_scout_comparison.py` 631 · `quality_metrics.py` 625 ·
`quality_dashboard.py` 604 · `architecture_audit.py` 512 (the only one with no tests).

## 4. Governance surface

| Artifact | Count |
|---|---|
| ADRs (`docs/adr/`) | 20 |
| Specs (`docs/specs/`) | 33 |
| Domain skills (`skills/*/SKILL.md`) | 18 |
| All `docs/**/*.md` | 281 |
| `BACKLOG.md` | 2,317 lines |
| `CLAUDE.md` | 323 lines |
| MCP servers configured | 6 |

`BACKLOG.md` is the source of record and is now longer than any source file by a factor of 1.5.

## 5. Verification

`make ci-local` is the only gate — no GitHub Actions, `main` unprotected (ADR-0015).

```
2791 passed, 9 skipped, 83.74% coverage — green as of 2026-09-10
```

Gate steps: ruff format/check → bare-name imports → docs-truth → mypy advisory → mypy
baseline → pytest + coverage (70% overall, 90% on `src/quality`) → bandit → destructive-change
guard → sensor proofs.

Python is pinned to **3.12** (`.python-version`). It was 3.13 until 2026-09-03; that number was
inherited from CrewAI's wheel ceiling and survived CrewAI's removal by nine months. See B-047
for the 3.14 attempt.

## 6. Open work

Genuinely open, in the order the evidence supports:

- **B-046** — the session-start hook lists completed items and ignores `BUG-` ids entirely, so
  4 of its 12 slots are finished work and the newest bugs are invisible. XS. Everything else is
  chosen off a list that is currently wrong.
- **BUG-081** — `_connect()` guards on `.exists()`, so a zero-byte `data/performance.db` passes
  the guard and breaks 21 tests. Reproducible today: `touch data/performance.db` → 21 failed.
- **BUG-079** — B-029's oracle test asserts against a re-typed copy of the guard, not the shell
  script.
- **B-047** — Python 3.14 works on dependencies; blocked on BUG-081 and a `chromadb` 0.x→1.x
  bump.
- **B-028** — the unreviewed publish path (`--mode post`) still exists. Oldest open decision.
- **B-030 … B-035** — the harness-engineering set, including **B-032, "nothing regulates
  complexity"**, which this document is evidence for.
- **BUG-075/076/077** (LOW) — playwright MCP fails on Node version; github plugin credential
  malformed; `quality_dashboard.py` not runnable as a script.

## 7. Things a newcomer will trip over

1. **The constraint guard matches on command text.** A Bash command that merely *mentions*
   `deploy_to_blog` without `--mode review` is denied, even when it is not invoking it — a
   static-analysis script naming it in a list gets blocked. Write such scripts to a file.
2. **`ensurepip` is unavailable** — `python3.12 -m venv` fails. `.venv` already exists; to make
   another, use `uv`.
3. **`data/performance.db` is untracked and must not exist.** A zero-byte one breaks 21 tests
   and the error names sqlite, not the cause (BUG-081).
4. **`output/posts/` holds three variants of one article**, which makes the pipeline look more
   productive than it is.
