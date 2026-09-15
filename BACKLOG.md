# Backlog

Source of record for open work. `B-NNN` are items, `BUG-NNN` are defects; both live here and
nowhere else (no GitHub issues). Done items are git history: the pre-redesign backlog is
archived verbatim at `docs/archive/BACKLOG-2026-09-13.md`, and every close-out since lives in
the commit that made it. The session-start hook lists the `### B-NNN ·` headings under Todo.

## In Progress

### B-049 · Interview-driven writing (position B) — **SPEC APPROVED 2026-09-15 (owner LGTM); S0 next**

**Spec:** `docs/specs/interview-driven-writing.md`. Target repo is `oviney/blog-gate-mcp`; this
repo is retired in its last slice (D8, owner-gated). Grounded in
`docs/research/2026-09-15-content-systems-synthesis.md` and the owner's 2026-09-15 decision:
Claude interviews, then arranges the draft from the owner's own transcript sentences; every
opinion traces to a turn he said, gate-checked. Supersedes B-048's open items: slice 5's live
acceptance becomes S4 here, D7 stays blog-side, D10 is moot.

### B-048 · Redesign: the owner's voice is the input, not the gate — **SLICES 0–6, 9 LANDED 2026-09-13; three things open**

**Spec:** `docs/specs/redesign-owner-voice-first.md`. Written at the owner's request
("tell me what's wrong with my thinking, what I'm missing, then redesign the whole thing").

**The finding one level above the 2026-09-10 complexity review:** the product is defined as
a *style* ("Economist-style") and that style forbids the only input the blog owns — the
owner's twenty years of experience. 20 of 29 published posts contain zero first-person
words; none cites an owner experience. The owner's judgment enters only at the end, as an
approve/reject of 1,000 finished words. Quality is operationalised as regex compliance (25
validator checks, a 5-dimension scorer) and no reader signal is captured. Since July: 173
commits, 5 articles.

**Ten decisions (D1–D10), each with reasoning, trade-off and reversibility, in the spec.**
The spine: the pipeline starts from an owner brief (thesis, experiences, disagreements)
instead of a topic string; Stage 1/2 and the second system are deleted; gates split into
blocking (reader-protecting) and advisory (style); the owner's own post-publish verdict
closes the quality loop, keyless.

**Owner-gated before slice 2:** D3 (delete Stage 1/2), D6 (retire sensors incl. docs-truth),
D7 (hero optional), D8 (archive all but three living docs). Recommendation on all four: yes.

**Absorbs:** see the Done section below for every item B-048 closed.

**Progress:**
- Slice 0 — DONE 2026-09-13. Tag `pre-redesign-2026-09` at 3798fdd. BUG-082 closed (guard + 13
  culprits fixed). Baseline before: 2791 passed / 9 skipped / 83.74%.

- Slice 1 — DONE 2026-09-13. Cut items 1–7 of the 09-10 review: 105 files, −38,700 lines
  (43 production modules incl. `agents/*.py`, `src/quality`, `src/telemetry`, `src/utils`; 47
  test files incl. the CrewAI-skipped integration test). `hero_svg`'s one live constant moved
  into `pipeline.py`; the ROI tracker call left with its module. Makefile 90% line, guard
  list, `.coveragerc` (BUG-084 closed), mypy baseline and five instruction docs edited; the
  836-line CrewAI-era `.github/copilot-instructions.md` archived rather than patched.
  Production Python 39,800 → 20,881; tests 48,554 → 29,204; suite 154 s → 82 s.
  Gate: 1675 passed / 5 skipped / 87.88% (from 2791 / 9 / 83.71%).

- Slice 2 — DONE 2026-09-13 (D3). Stage 1/2 and feeders: `flow.py`, editorial board, topic
  scout + trend grounding, `llm_client`, `agent_loader` + the `agents/` YAML library, GA4/GSC
  ETL, content intelligence, the ChromaDB topic deduplicator and its backfill, the Copilot
  sync script, the featured-image agent, the OpenAI token logger; 21 test files. The
  architecture-compliance test lost its allow-list: with `llm_client` gone the rule is
  absolute (no `anthropic`/`openai` import anywhere in production code). Pre-commit hook,
  sensor register and guard list edited; README / Copilot / CLAUDE.md architecture prose
  rewritten to the one path. Gate: 1278 passed / 1 skipped / 88.53% in 76 s.

- Slice 3 — DONE 2026-09-13 (D8). 249 files moved into `docs/archive/` unedited (131 root
  docs, 12 doc subtrees, 33 closed specs, the old BACKLOG, root CONTRIBUTING/GEMINI/Copilot
  files, `.github/` write-ups, `references/`, `tasks/`, the spike outputs, fourteen skills);
  the mkdocs deploy workflow and the workflow calling a deleted audit script deleted;
  `mkdocs.yml` cut to the ADR nav the ADR linter needs. `CLAUDE.md` rewritten at 110 lines,
  `BACKLOG.md` at 119 (open items only). Markdown outside the archive: 376 → 51.
  Gate: 1277 passed / 1 skipped / 88.51% in 69 s.

- Slice 4 — DONE 2026-09-13 (D6). Retired: the sensor register and proofs, the complexity
  and post-edit sensors, the mypy baseline, the destructive-change guard, the ADR / skill /
  badge linters, the arch-review hook, the bare-name-import check, `mkdocs.yml`; ten test
  files and the sensor halves of two more. `ci-local` is now ruff + docs-truth + mypy (hard,
  over `src/ scripts/ mcp_servers/`, archived excluded, the 18 live errors fixed) + pytest
  with coverage + bandit. Kept: the `PreToolUse` constraint guard, session context, the stop
  gate (which inlined the one helper it borrowed), and `check_docs_references.py` as a plain
  check. Gate: 1046 passed / 1 skipped / 87.68% in 94 s.

- Slice 5 — DONE 2026-09-13 (D1, D2, BUG-083). `src/agent_sdk/brief.py` parses
  `briefs/<slug>.md` (template at `briefs/TEMPLATE.md`; the take is the one hard
  requirement, empty optional sections are reported); `--brief` is the owner's take and the
  topic defaults to its title; `--research-brief` is the old verbatim research input;
  `claude_web` research takes a focus (evidence for the thesis, the best counter-evidence,
  named cases); the writer prompt leads with the AUTHOR'S BRIEF and the system prompt is a
  practitioner's editor with first person expected; the packet's new §0 says what the run
  started from. Default research mode is `claude_web` everywhere, with a test that the CLI,
  both signatures and CLAUDE.md agree. The test netguard now blocks the research modules'
  own SDK references too — the first gate after the default changed stalled on a real
  `claude` subprocess. Gate: 1071 passed / 1 skipped / 87.86% in 61 s.
  **Live acceptance still open:** a real article from a real owner brief to a review URL
  needs the owner to write `briefs/<slug>.md` first; nothing else can supply the take.

- Slice 6 — DONE 2026-09-13 (D4, D5). No editorial score: the 5-dimension evaluator, its
  MCP server and `logs/article_evals.json` are gone; Stage 4 is polish + validator. The
  validator's CRITICAL findings block, everything else is advisory in the packet (word count
  and weak endings demoted; heading structure kept blocking because a literal `##` in a
  paragraph is reader-visible). ChromaDB is out — style memory (collection count 0 for its
  whole life), the topic archive and their two MCP servers — so B-047 is unblocked. The
  owner's `## Verdict` in each brief now steers the next draft: `recent_verdicts()` feeds
  the last five into the writer prompt. Gate: 904 passed / 2 skipped / 87.38% in 37 s.
- Slice 9 — DONE 2026-09-13. ADR-0020 records the decision; README rewritten at 80 lines;
  CLAUDE.md and the spec point at both. Markdown outside `docs/archive/`: 51.
- Review pass — DONE 2026-09-13. A fresh-context reviewer on slices 5–6 found three real
  defects, all fixed with regression tests: the brief parser ended a section at a `#` inside
  a code block or at a `###` subsection (a take silently truncated); a copied template's
  `<placeholder>` verdict would have been injected as an editorial note; and the "never
  invent experiences" rule vanished exactly when the brief had no experiences. Also fixed:
  placeholder-only sections count as empty, operator errors exit 1 not the transient code 2,
  non-UTF-8 briefs cannot crash Stage 3, the packet protocol declares the brief fields, three
  vacuous test assertions, and stale prose that still promised a rejection or a scorer.

**Open, in the order to take them:**
1. **Slice 5 live acceptance — needs the owner.** Write `briefs/<slug>.md` from
   `briefs/TEMPLATE.md` and run `python -m src.agent_sdk.pipeline --brief briefs/<slug>.md`
   to a review URL. Nothing else can supply the take.
2. **D7 (hero optional) — BLOCKED by evidence, not implemented.** The spec said it was one
   condition in the deploy step. It is not: `oviney/blog/scripts/validate-post-quality.sh:110`
   errors "hero image not set" and the blog's `test-build.yml` runs it. The change is on the
   blog side and is the owner's to make; the deploy refusal here stays until then.
3. **D10 / slice 8 (stage-per-file rewrite) — not attempted.** Its gate is three real runs
   to a review URL. A rewrite of the one path that works, proven only by the unit suite, is
   the regression the spec's own mitigation forbids. B-012 (deep research: keep or delete) is
   decided there.


## Todo

### BUG-083 · The pipeline's default research mode contradicts the documentation

`pipeline.py` defaults `research_mode` to `deterministic`; CLAUDE.md names `claude_web` as the
default in practice, and `deterministic` frequently aborts (BUG-050). The CLI help still
advertises Serper, removed by #438. XS. **Lands in B-048 slice 5** with the input inversion,
plus a test that the default equals what CLAUDE.md names.

### B-028 · The unreviewed publish path — Task 3 is owner-gated

Tasks 1–2 done (2026-07-31): `--mode` is required, the hook denies anything but `review`.
**Task 3, open:** should `--mode post` exist at all? B-048 slice 7 touches the deploy step;
the recommendation there will be to delete the mode. Full record in the archived backlog.

### B-012 · Opt-in deep research — acceptance never run

Code done (`--brief`, `deep` mode via `src/agent_sdk/research/deep_research.py`); the one
open criterion is a real deep-research → article run (~2M tokens, owner-run). B-048 D10 keeps
`claude_web` only. **Decision due at slice 8:** run the acceptance once, or delete the deep
path with the rewrite. Recommendation: delete unless a flagship post wants it first.

### B-047 · Python 3.14 — blocked on chromadb

Dependencies otherwise fine (2026-09-03). ChromaDB goes with the style memory in B-048
slice 6; retry the bump immediately after.

### BUG-079 · B-029's oracle test proves a copy of the guard, not the guard (LOW)

`tests/` asserts against a re-typed copy of the deploy-mode guard rather than the shell
script it protects. Fix when slice 4 reshapes the hooks.

### BUG-075 · playwright MCP fails on Node v18 (needs ≥20) — LOW, environment
### BUG-076 · github plugin credential malformed — LOW, environment

Both machine setup, not repo defects. Fix or remove the servers from `.mcp.json`.

## Done

Closed by B-048 on 2026-09-13, with the slice that closed them. Details are in the archived
backlog and the slice commits.

- **BUG-082** (slice 0) — the suite mutated the real blog clone; guard + 13 culprits fixed.
- **BUG-084** (slice 1) — `.coveragerc` omitted the validator; now measured at 89%.
- **BUG-081** (slice 1) — `data/performance.db` had one reader and 21 tests; all deleted.
- **BUG-077** (slice 1) — `quality_dashboard.py` deleted.
- **B-023** (slice 2) — `llm_client.py` deleted; the auth-path question is moot.
- **B-038** (D1) — the HTML-artifact import survives as the brief input path; the item is
  the redesign's D1, not a separate feature.
- **B-040** (D4) — the editorial scorer is deleted rather than calibrated.
- **B-041** — moot since B-042 removed the hero draw the item was timing.
- **B-046** — fixed by construction: this file lists only open items.
- **B-030, B-031, B-032, B-033, B-034, B-035, B-043** (D6) — the harness-engineering set is
  superseded: the sensors programme is retired in slice 4, and B-048 itself is the answer to
  B-032 ("nothing regulates complexity").
- **B-015** — a branch-reconciliation record with nothing open; B-015a shipped 2026-07-24.
- **B-025, BUG-073** — withdrawn before B-048.
