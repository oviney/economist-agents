# Complexity review — Fable 5.1, 2026-09-10

Fresh-context adversarial review run against the prompt in
`2026-09-10-complexity-review-prompt.md`. The reviewer had repo read access and was told to
verify the baseline before relying on it.

**It refuted two claims in `docs/repo-state-2026-09-10.md`.** Both corrections were
independently re-verified before being recorded here; see §0.

---

## 0. Corrections to the baseline

| Claim in the state doc | Reality | Status |
|---|---|---|
| 35,505 lines of production Python | The walk covered only `src/` and `scripts/`. `agents/` (2,483) and `mcp_servers/` (1,568) are production Python too. Non-archived total is **~39,800** | **Undercount by ~11%** |
| "**ZERO orphans** — all 48 unreachable modules are named in a config, Makefile or doc" | Conflated *config* with *doc*. Adding every genuinely wired entry point — 4 hooks, 5 registered MCP servers, 5 pre-commit scripts — still leaves **47 modules / 17,554 lines** unreachable, and **none** of them is named by `Makefile`, `.pre-commit-config.yaml`, `.claude/settings.json` or `.mcp.json`. Only a doc mention tethers them | **Refuted. They are orphans with documentation** |
| 30 published posts | 29. `temp_blog_repo/_posts/2026-08-30-a-post.md` is an untracked **test fixture** (`title: t`) | Corrected |
| 281 markdown files | 283 under `docs/` alone; 376 repo-wide | Undercount |
| 20 ADRs | 19 + `TEMPLATE.md`, 3 superseded | Minor |
| 55% unreachable | Reviewer's own walk: 58% (64 modules / 21,529 lines). Holds | Confirmed, slightly low |

Supporting evidence for the orphan refutation: **no output file from any analysis script**
(`topic_scout_reproducibility_*`, `composite_score_audit_*`, `quality_dashboard.json`,
`team_skills*`) exists anywhere in the tree — only their `__pycache__`. 28 of the 35 largest
were last touched by the 2026-04-30 mass reformat and have **zero commits** since the current
architecture landed.

## 1. Smallest set that still produces and publishes an article

**Eleven modules, 5,977 lines** — 15% of production Python:

`pipeline.py` 599 · `_shared.py` 1,097 · `stage3_runner.py` 874 · `stage4_runner.py` 138 ·
`research/claude_web.py` 149 · `tools/research_tools.py` 166 · `review_packet.py` 251 ·
`image_prompt_synth.py` 107 · `publication_validator.py` 1,497 · the deploy script 874 ·
`promote_review.py` 225

With `make art` (`finalise_art` 137 + `chart_renderer` 224) and two validator dependencies:
**7,246 lines total.**

Notable things shown to be inert:
- **Style memory** (`style_memory_tool.py`, 394): `stage3_runner.py:72-96` fetches style
  context from a Chroma collection with **count 0**. It has never contributed a sentence.
- **Hero SVG gate** (381): only the constant `HERO_IMAGES_DIR` is imported. `check_hero_svg`,
  `report_edge_contact`, `render_to_png` have no caller — B-016b was reversed by B-042.
- **Editorial score**: `stage4_runner` computes it; `pipeline.py` exits 1 only on
  `publication_validator_passed`. The score is decoration in the review packet.
- `_shared.refine_image_metadata` (1006-1097) and `parse_research_for_verification` (979): no
  callers.

## 2. Ten largest unreachable modules — verdicts

| Module | Lines | Verdict | Reason from the code |
|---|---|---|---|
| `economist_agent.py` | 1,239 | **DELETE** | "v3 orchestrator"; sole importer of `agents/*.py` and four `src/quality` modules. ADR-0016 declared one pipeline path. 94 doc mentions, zero invocations |
| `skills_gap_analyzer.py` | 1,060 | **DELETE** | Maps agent defects to "Junior/Mid/Senior for data-driven hiring". There is one human and no hiring |
| `topic_scout_reproducibility.py` | 923 | **DELETE** | ADR-0007:12-24 already records the experiment's outcome. No output file exists |
| `defect_tracker.py` | 813 | **DELETE + amend CLAUDE.md** | CLAUDE.md mandates logging here; last entry is BUG-072 (Aug 2). BUG-074/078/079/081 all went to BACKLOG instead. The module is the un-followed rule |
| `validate_closed_loop.py` | 737 | **DELETE** | Lines 9-10 validate `skill_synthesizer.py` and `blog_qa_agent.py`. **Neither file exists** |
| `audit_composite_scores.py` | 715 | **DELETE** | Reads `data/performance.db`, which must not exist (BUG-081). Result already in ADR-0007:17 |
| `ab_topic_scout_comparison.py` | 631 | **DELETE** | One-shot experiment; verdict in ADR-0007:12 |
| `quality_metrics.py` | 625 | **DELETE** | Writes `logs/quality_dashboard.json`. No such file exists. Never run |
| `quality_dashboard.py` | 604 | **DELETE** | Reads two JSONs last changed **2026-04-16**; "sprint progress" for a regime retired 2026-07-14 |
| `context_manager.py` | 566 | **DELETE** | "Shared Context Manager for CrewAI Agents… Sprint 7 Story 2". CrewAI retired. Zero importers |

Also: `editorial_judge.py` (562) has no caller **yet sits in `destructive_change_guard.py:29`
`CRITICAL_FILES`** — a guard protecting an unreachable file.

**REDUCE, not delete:** `html_to_brief.py` (553) — B-038 is an owner-stated workflow but
BACKLOG:451 says "still unexercised". Keep until used once.

## 3. Measured but never acted on

- **ROI tracker**: logs `input_tokens=0, output_tokens=0` on a subscription with no per-call
  charge. Its only reader is `economist_agent.py:691` — itself unreachable. `execution_roi.json`
  was last written *by the test suite* (a 90µs "execution").
- **`data/skills_state/`**: four JSONs have **zero readers in code**; three more are read only
  by unreachable modules. All last changed 2026-04-16.
- **`logs/article_evals.json`** (278KB, written every Stage 4 run): no threshold consumes it.
- **`logs/sensor_history.jsonl`**: written by the post-edit hook; **no reader**.
- **The `src/quality` 90% coverage gate** — the strictest rule in the repo — applies to a
  package imported only by two unreachable modules. Meanwhile **`.coveragerc:74` omits
  `publication_validator.py`**, the one gate that decides publication, and 35 of 47 omit
  entries name files that no longer exist.

## 4. Test proportionality

2,791 tests. By what the tested module reaches: core produce/publish path 15,990 lines (of
which **8,278 is the Stage 1/2 cluster** — `test_topic_scout.py` alone is 1,776 lines, the
largest test file, for a function called once); wired tooling 12,756; **second system 15,636**;
and **3,713 lines testing the CrewAI `agents/` package, which has no importable target on the
live path**.

Tests protecting something a blog reader would notice: **~5,200 lines, 11% of the suite.**

**Worse than disproportion — the suite mutates real state.** `test_deploy_to_blog.py:153` uses
`Path("temp_blog_repo")`. The blog clone now sits on a test-created branch
(`content/2026-07-28-a-post-20260830-201155`) with an untracked fixture in `_posts/`.
`logs/execution_roi.json`, `logs/article_evals.json` and `output/quarantine/` are rewritten at
test time. **If the owner ever commits from that clone, a test fixture ships to the blog.**

## 5. Governance — load-bearing vs self-sustaining

**Load-bearing** (machine-read; these change what happens): `CLAUDE.md` + `BACKLOG.md`
headings (read by the session hook every start), `.claude/settings.json` hooks,
`docs/sensors/register.yaml` + `check_sensor_proofs`, `docs/mypy-baseline.md` +
`mypy_baseline`, `.pre-commit-config.yaml`, the five docs CLAUDE.md links, 8 of 18 skills, and
`docs/HANDOFF.md` (810 lines, 31 commits since July — the cross-session memory of an operator
whose sessions clear).

**Self-sustaining** (records that something happened): 131 root-level docs, **106 last touched
2026-01 and 38 with zero inbound references** (`SCRUM_MASTER_PROTOCOL.md` 875,
`AUTONOMOUS_ORCHESTRATION_STRATEGY.md` 1,117, `SPRINT_7_PARALLEL_EXECUTION_LOG.md` 1,223…);
`docs/CHANGELOG.md` 4,258 lines with one commit since July; `docs/archive/` 60 files; 10 of 18
skills referenced by nothing that loads them.

**BACKLOG.md's 2,317 lines: Todo 633, "Harness engineering" 1,072, Done 585 — 46% of the
backlog is the second system's own backlog.** Of 172 commits since July 1, **117 are
docs-only (68%)**.

## 6. Ranked cuts

| # | Cluster | Code | Tests | Risk |
|---|---|---|---|---|
| 1 | `economist_agent` + `agents/*` + 6 `src/quality` modules + `quality_dashboard` + `record_metrics` | 6,899 | 7,988 | Low — edit Makefile 90% line, guard, `.coveragerc` |
| 2 | Closed-loop: `skills_gap_analyzer`, `validate_closed_loop`, `skills_manager`, `skill_eval`, `feedback_loop`, `quality_metrics` | 3,830 | 2,702 | Low |
| 3 | CrewAI-era one-offs: `context_manager`, `caching`, `data_sanitization`, `validation`, `agent_trace_logger`, `spend_report`, `github_issue_claim`, `citation_verifier`, `generate_chart`, `blog_quality_audit`, `architecture_audit`, `editorial_judge` | 3,934 | 2,811 | Low |
| 4 | One-shot experiments: `ab_topic_scout_comparison`, `topic_scout_reproducibility`, `audit_composite_scores` | 2,269 | 1,944 | Low |
| 5 | `defect_tracker` + the CLAUDE.md flowchart line | 813 | 1,077 | Low; needs a CLAUDE.md edit |
| 6 | Unregistered MCP servers: `image_generator_server` (violates constraint #4 by design), `blog_deployer_server` | 584 | 879 | Low |
| 7 | Dead functions: hero SVG gate, ROI tracker, `_shared` orphans, `DEFAULT_GRAPHICS_MODEL` | ~950 | ~1,020 | Low |
| 8 | Stale docs: 38 zero-inbound root docs, CHANGELOG, `docs/archive/`, 10 unreferenced skills | ~20,000 md | — | **Medium** — `check_docs_references` will go red on dangling links; a sweep, not a delete |
| 9 | **OWNER-GATED:** `flow.py` Stage 1/2 + feeders (`editorial_board`, `topic_scout`, `llm_client`, `agent_loader`, `ga4_etl`, `gsc_etl`, `content_intelligence`…) | 5,707 | 9,794 | **Medium** |

**Items 1–7: ~19,200 lines of code (49%) and ~18,400 lines of tests (38%) removed at low risk,
with no change to what any blog reader sees.** What remains is ~20,000 lines, of which ~7,250
produce and publish.

**Item 9 is a true fork.** Keep case: BUG-046 was fixed on 2026-07-31 specifically to keep
Stage 1/2 keyless, so it was invested in five weeks ago, and README:27 / CLAUDE.md:185 call it
the orchestrator. Against: no article since July went through it, its dedup index is empty,
and its performance context needs a Google key that constraint #1 forbids.

**Explicitly KEEP** — the gate layer: `check_sensor_proofs`, the hooks, `destructive_change_guard`,
`mypy_baseline`, `check_docs_references`, `publication_validator`, the deploy `--mode`
requirement and hero refusal. *"These are the reviewer a solo operator with no CI and
unprotected `main` does not have. B-028, BUG-065 and B-039 each document a real defect that
reached production or masked a failure before the corresponding gate existed."*

## 7. Fix regardless of any cut

1. The test suite writes into `temp_blog_repo/`, `logs/`, `output/quarantine/`.
2. `pipeline.py:139` defaults `research_mode="deterministic"` while CLAUDE.md says `claude_web`
   is the default in practice and BUG-050 says deterministic frequently aborts; `pipeline.py:345`
   still advertises "(default, Serper)" — Serper was removed by #438.
3. `.coveragerc` omits `publication_validator.py`; 35 of 47 omit entries are stale.
4. `destructive_change_guard` protects three files off the critical path.
