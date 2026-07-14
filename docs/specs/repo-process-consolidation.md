# Spec: Repo Process Consolidation — Retire the Autonomous-Scrum Regime

**Status:** DRAFT — awaiting human LGTM (spec-driven-development gate)
**Author:** economist-agents maintainer session, 2026-07-14
**Lifecycle:** `spec` (this doc) → human LGTM → `plan` (task breakdown) → `build`/`test` → `review` → `ship`
**Supersedes context:** builds on `docs/specs/local-backlog-migration.md` (2026-06-13)

---

## 1. Objective

The repository runs **two overlapping process regimes at once**. Decide, precisely,
which one is authoritative and dismantle the other so the repo has a single,
coherent way of working.

- **Regime A — the agent-skills lifecycle (LIVE, authoritative).**
  `skills/*/SKILL.md` (spec → plan → build → test → review → ship, every phase a
  human-in-the-loop `Skill` invocation) + `BACKLOG.md` as the local-first planning
  source of record + `CLAUDE.md`'s Lifecycle Discipline and Skill Routing Contract.
  Last substantively updated **2026-06-14**.

- **Regime B — a bespoke "autonomous Scrum" machine (ABANDONED IN PLACE).**
  `SPRINT.md` (88 KB), PO/SM/orchestrator agent scripts, `sprint-discipline.yml` /
  `sprint-sync.yml` workflows, ~10 sprint/agent state JSONs, 10 `.github/agents/*.agent.md`
  personas + `AGENTS.md`, and the `sprint-management` / `scrum-master` skills. Most of
  it **froze ~2026-05-16** and has had no live writer since.

**The core contradiction:** the June `local-backlog-migration` explicitly *retired the
"log all work via GitHub issues / SPRINT.md" model* that Regime B implements — but nobody
dismantled Regime B. It was simply left running. `sprint-sync.yml` still pushes work back
to GitHub issues; `sprint-discipline.yml` still fails PRs that don't map to `SPRINT.md`;
the sprint issue templates still exist. This spec finishes the migration.

### Does the agent-skills lifecycle "replace all the repo process"?

**No — but it replaces all of Regime B.** The user's thesis is substantially (≈80%) correct.
Precisely:

- The agent-skills lifecycle **replaces** every *process-orchestration* artifact in Regime B
  (sprint ceremonies, autonomous PO/SM agents, sprint sync, sprint discipline gates).
- It does **not** replace, and this spec keeps: the **domain/craft skills**, the **content
  pipeline** (`src/`, pipeline `scripts/`), **`defect_tracker.json`** + the defect-prevention
  flowchart, **standard CI** (`ci.yml`, `quality-tests.yml`), **ADR governance**, and
  **`BACKLOG.md`** itself.

Agent-skills are a *workflow discipline*, not a *product runtime*. Anything that is product
(the pipeline) or durable governance (ADRs, defect log, backlog) stays.

---

## 2.0 Correction — post-approval coupling audit (2026-07-14)

A dependency audit during `planning-and-task-breakdown` found the first-pass §2.3 over-classified
several items as RETIRE that are load-bearing for the KEEP test suite. Corrections:

- **`scripts/skills_manager.py`, `scripts/skills_gap_analyzer.py` → KEEP.** Imported by
  `src/quality/validate_closed_loop.py` (`from scripts.skills_manager import SkillsManager`) and
  integrated by `src/quality/chart_metrics.py`; exercised by `test_closed_loop_validation.py`,
  `test_validate_closed_loop.py`, `test_quality_system.py`. Not Regime B.
- **`.github/agents/*.agent.md` (10) + `AGENTS.md` + `scripts/agent_registry.py` → DEFERRED (needs ADR).**
  `test_llm_providers.py` builds `AgentRegistry` over the real `.github/agents/` dir and asserts
  `list_agents() > 0` and `match="scrum-master"`; `test_agent_registry_enhancement.py` and
  `test_architect_agent.py` also depend on it. This is ADR-002 architecture, not cruft — retiring it
  is a design change requiring a superseding ADR.
- **The autonomous agent scripts (`sm/po/orchestrator_agent`, `continuous_burndown`, `sprint_validator`)
  → DEFERRED.** They share `escalations/task_queue/sprint_tracker.json` writers with `src/backlog/*`
  and have live tests; safe removal needs the full suite runnable (blocked here — see below).
- **`SPRINT.md` → DEFERRED.** Read by KEEP code: `src/backlog/validate_documentation_accuracy.py` and
  `scripts/defect_prevention_rules.py` (soft-dep of `publication_validator`), plus
  `test_github_integration.py`/`test_continuous_burndown.py`. Delete it *with* those in Wave 2.
- **`.deployment_state` → KEEP (LIVE).** Read by `scripts/rollback_production.sh` (blue/green rollback).
- **`.github/BACKLOG.md` → DEFERRED.** Referenced by `src/backlog/migrate_backlog_to_github.py`.
- **Root `SPEC.md` → DEFERRED.** Referenced by `src/quality/visual_qa_zones.py`.
- **`remediation-sync.yml` → KEEP.** It is a *content*-remediation workflow (posts/pipeline), not sprint.

**Verification is CI-gated:** the full suite cannot run here (`pip install -r requirements.txt` fails
building the `sgmllib3k`/feedparser wheel). Wave-1 slices below are config/doc/artifact-only with **no
pytest import**, verifiable by grep + CI. See `tasks/plan.md` for the wave breakdown.

## 2. Decision map — KEEP / CONSOLIDATE / RETIRE

### 2.1 KEEP (live, no lifecycle overlap)

| Area | Artifacts |
|---|---|
| Lifecycle spine | `using-agent-skills`, `spec-driven-development`, `planning-and-task-breakdown`, `incremental-implementation`, `test-driven-development`, `code-review-and-quality`, `shipping-and-launch`, `idea-refine`, `context-engineering` |
| Domain/craft skills | `economist-writing`, `editorial-illustration`, `research-sourcing`, `article-evaluation`, `visual-qa`, `defect-prevention`, `observability`, `agent-traceability`, `python-quality`, `testing`, `architecture-patterns`, `mcp-development`, `frontend-ui-engineering`, `browser-testing-with-devtools`, `performance-optimization`, `security-and-hardening`, `source-driven-development` |
| Planning source of record | `BACKLOG.md` |
| Governance (durable) | `docs/specs/*`, `docs/worker-brief-contract.md`, `CLAUDE.md`, ADR set + `adr-governance` skill, `defect_tracker.json` |
| Content pipeline | `src/`, pipeline `scripts/` (`economist_agent.py`, `editorial_board.py`, `topic_scout.py`, `generate_chart.py`, `featured_image_agent.py`, `publication_validator.py`, `citation_verifier.py`, search/ETL adapters), `agents/skills_configs/*.yaml` |
| Standard CI | `ci.yml`, `quality-tests.yml` (after Regime-B references are excised), `content-pipeline.yml`, `docs.yml`, `regenerate-image.yml`, `blog-quality-audit.yml` |

### 2.2 CONSOLIDATE (overlap, not deletion)

| Overlap | Action |
|---|---|
| Coding standards restated ~5× (`CLAUDE.md`, `GEMINI.md`, root + `.github/copilot-instructions.md`, `CONTRIBUTING.md`) + `python-quality` skill | Make `CLAUDE.md` + skills the single source. Shrink `GEMINI.md`, both Copilot files, and CONTRIBUTING's coding-standards/TDD prose to **thin pointers**. |
| Two ADR skills: `documentation-and-adrs` vs `adr-governance` | Merge into one; keep `adr-governance`, fold the doc-writing guidance in. |
| Three CI skills: `ci-cd-and-automation` vs `devops` vs `quality-gates` | Collapse to one CI/automation skill; strip `devops`'s GitHub-Projects (Regime-B) content. |
| `testing` vs `test-driven-development` | Keep both; add a one-line boundary note (`testing` = domain patterns; TDD = lifecycle phase). |
| `code-simplification` vs `code-review-and-quality` | Minor; add cross-reference, no merge. |

### 2.3 RETIRE (Regime B — the autonomous-Scrum machine)

**Skills**
- `skills/sprint-management/`, `skills/scrum-master/` — sprint ceremony + SPRINT.md↔Issues sync; directly contradict `local-backlog-migration`.

**Executable code + their tests** (⚠ CI-wired — see §6; ⚠ superseded by §2.0)
- `scripts/po_agent.py`, `scripts/sm_agent.py`, `scripts/orchestrator_agent.py`,
  `scripts/sprint_validator.py`, `scripts/continuous_burndown.py`
- Tests: `tests/test_po_agent.py`, `tests/test_sm_agent.py`, `tests/test_orchestrator_agent.py`,
  `tests/test_continuous_burndown.py`
  (⚠ **verify** `test_orchestrator_agent.py` targets the Regime-B PR-triage orchestrator, not
  `deep_research_orchestrator`; `test_deep_research_orchestrator.py` is research-pipeline — KEEP.)
- **Not here:** `scripts/skills_manager.py`, `scripts/skills_gap_analyzer.py` (+ their tests) were
  moved to **KEEP** by the §2.0 correction — they back `src/quality/validate_closed_loop.py`.

**Workflows**
- `.github/workflows/sprint-discipline.yml`, `sprint-sync.yml`,
  `nightly-eval.yml`, `sync-copilot.yml` (+ `scripts/sync_copilot_context.py`,
  `sync_copilot_pre_commit.sh`) — regenerates the very Copilot files §2.2 shrinks.
  (`remediation-sync.yml` is **KEEP** per §2.0 — it is content remediation, not sprint.)

**Personas / registry**
- `.github/agents/*.agent.md` (10 files), `AGENTS.md`, `skills/agent-delegation` references to them.
  (Note: `CLAUDE.md`'s Skill Routing Contract already ranks these "never agent-skills".)

**Machine state** (`data/skills_state/`)
- `sprint_tracker.json`, `sprint_history.json`, `backlog.json` (the `STORY-NNN` machine backlog),
  `task_queue.json`, `escalations.json`, `agent_status.json`, `po_agent_test_metrics.json`,
  `sm_agent_test_metrics.json`, `test_backlog_story3.json`.
  KEEP: `defect_tracker.json`. Decide case-by-case: `agent_metrics.json`, `chart_metrics.json`,
  `quality_history.json`, `feature_registry.json`, `ci_health_patterns.json` (only if a KEEP script writes them).

**Sprint issue surface**
- `.github/ISSUE_TEMPLATE/sprint_story.yml`, `sprint_retrospective.md`;
  `.github/BACKLOG.md` (duplicate of root `BACKLOG.md`), `.github/MIGRATE_BACKLOG_QUICKSTART.md`,
  `.github/GITHUB_PROJECT_SETUP.md`.

**Stale snapshot artifacts (delete)**
- Root: `SPRINT.md`, `SPRINT_10_STORY_7_DONE.txt`, `SPRINT_15_BUSINESS_VALUE_REPORT.md`,
  `SPRINT_15_DEMO.md`, `EXECUTIVE_SUMMARY_SPRINT_15.md`, `sprint_badge.json`, `tests_badge.json`,
  `quality_score.json`, `.deployment_state`, and the stale root `SPEC.md` (a May scripts-cleanup
  spec — replaced by this file living under `docs/specs/`).
- Root shell wrappers: `run_full_workflow.sh` (SM-agent orchestration wrapper), `test_governance.sh`
  (smoke-tests `sprint_validator`) — retire with their targets.

---

## 3. Scope

**In scope:** everything in §2.2 (CONSOLIDATE) and §2.3 (RETIRE), executed as dependency-ordered
slices after LGTM.

**Out of scope:**
- Any change to `src/` product code or the content-pipeline scripts.
- `defect_tracker.json` and the defect-prevention flowchart (stays).
- `BACKLOG.md` content (stays as source of record).
- The 4 `agents/skills_configs/*.yaml` content-crew configs (not process personas — keep).
- ADR *history* — ADRs are append-only; supersede, never delete.

---

## 4. Assumptions (decisions taken as default — flip any at LGTM)

The interactive decision prompt failed to reach the user this session, so these are taken as
**explicit defaults** per Core Operating Behavior #1. Each is a fork the reviewer can redirect:

1. **Regime-B code → full retire** (scripts + tests + workflows + personas + state), not
   "leave dormant". Rationale: dormant unmaintained code that contradicts the live model is a
   future foot-gun; it still runs in CI and still fails PRs.
2. **Stale artifacts → hard delete** (git history preserves them), not moved to `/archived`.
3. **Instruction sprawl → collapse to pointers**, single-sourced on `CLAUDE.md` + skills.
4. **This session delivers the spec only** and stops for LGTM. No file is deleted or edited
   until the reviewer approves this doc.

---

## 5. Commands (verification)

```bash
# Baseline before any change — record the numbers to preserve
pytest tests/ -q                                   # capture pass count
ruff check --no-fix && ruff format --check .

# Prove Regime-B code has no KEEP importers before deletion
grep -rnE 'po_agent|sm_agent|orchestrator_agent|sprint_validator|continuous_burndown' \
  src/ scripts/ mcp_servers/ | grep -v '^scripts/\(po_agent\|sm_agent\|orchestrator_agent\|sprint_validator\|continuous_burndown\)'

# Find every CI reference to a retired script (must reach zero)
grep -rnE 'sprint_validator|po_agent|sm_agent|orchestrator_agent|continuous_burndown|sync_copilot' .github/workflows/

# Find every doc pointer to a deleted file (fix or drop the link)
grep -rnE 'SPRINT\.md|AGENTS\.md|sprint-discipline|sprint-sync' --include='*.md' .

# After each slice
pytest tests/ -q                                   # count only drops by the deleted Regime-B tests
```

## 6. Testing strategy — keeping CI green is the primary risk

Regime-B scripts are **not dead code to the test runner**: `test_po_agent.py`, `test_sm_agent.py`,
`test_orchestrator_agent.py`, `test_continuous_burndown.py`, `test_skills_gap_analyzer.py` exist and
`quality-tests.yml` references the sprint tooling. Deleting a script without its test/CI wiring
turns CI red. Therefore:

1. **Delete script + its test + its CI reference in the same slice** — never partially.
2. After each slice, `pytest tests/ -q` must pass; the pass count is expected to **drop by exactly
   the number of retired Regime-B tests** and by nothing else. Any *other* regression means a hidden
   dependency — stop and investigate.
3. The crewai-import guard and `test_architecture_compliance.py` `ALLOWED_FILES` list must be updated
   when scripts are removed (precedent: ADR-0010 / #344).
4. Pure doc/skill deletions (SPRINT_15 reports, sprint skills) carry no test; verify only that no
   `mkdocs.yml` nav entry or markdown link dangles (`docs.yml` build stays green).
5. Config/instruction consolidation is verified procedurally: `.mcp.json`/YAML still parse; the
   coding standards survive in exactly one place; pointers resolve.

## 7. Project structure (files touched, by slice — informational; real breakdown in `plan`)

```
RETIRE-skills/     skills/sprint-management/ skills/scrum-master/            (+ merge 2 ADR, 3 CI skills)
RETIRE-code/       scripts/{po_agent,sm_agent,orchestrator_agent,sprint_validator,
                   continuous_burndown,skills_gap_analyzer,skills_manager}.py + matching tests/
RETIRE-ci/         .github/workflows/{sprint-discipline,sprint-sync,remediation-sync,
                   nightly-eval,sync-copilot}.yml + scripts/sync_copilot_context.py
RETIRE-personas/   .github/agents/*.agent.md  AGENTS.md
RETIRE-state/      data/skills_state/{sprint_tracker,sprint_history,backlog,task_queue,
                   escalations,agent_status,po_agent_test_metrics,sm_agent_test_metrics,
                   test_backlog_story3}.json
RETIRE-issues/     .github/ISSUE_TEMPLATE/{sprint_story.yml,sprint_retrospective.md}
                   .github/{BACKLOG.md,MIGRATE_BACKLOG_QUICKSTART.md,GITHUB_PROJECT_SETUP.md}
DELETE-artifacts/  SPRINT.md SPRINT_10_STORY_7_DONE.txt SPRINT_15_*.md EXECUTIVE_SUMMARY_SPRINT_15.md
                   {sprint,tests}_badge.json quality_score.json .deployment_state SPEC.md
                   run_full_workflow.sh test_governance.sh
CONSOLIDATE-docs/  GEMINI.md  copilot-instructions.md  .github/copilot-instructions.md
                   CONTRIBUTING.md (coding-standards/TDD sections → pointers)
```

## 8. Code style / conventions

- Deletions preserve git history (no `--force`, no history rewrite).
- One slice = one concern = one PR, dependency-ordered, each independently green (per
  `incremental-implementation`).
- Every retired path gets a one-line entry in the PR body explaining *why* it is Regime B.
- `CLAUDE.md` is updated in the **final** slice to drop references to retired machinery (Lifecycle
  Discipline, Skill Routing table, "Dispatching worker agents") so the doc never points at a
  deleted file mid-migration.

## 9. Boundaries

- **Always:** run `pytest -q` after every slice and keep it green (allowing only the expected
  Regime-B test-count drop); delete script+test+CI-ref together; keep `.mcp.json`/YAML valid;
  update `test_architecture_compliance.py` `ALLOWED_FILES` in the same slice as a script removal.
- **Ask first:** deleting any `data/skills_state/*.json` that a KEEP script writes (`agent_metrics`,
  `chart_metrics`, `quality_history`, `feature_registry`, `ci_health_patterns`); removing any workflow
  that also does non-sprint work; touching `defect_tracker.json`.
- **Never:** delete `src/` or content-pipeline code; delete or rewrite ADR history; remove
  `BACKLOG.md`; force-push or rewrite git history; delete a script while its test or a CI job still
  references it.

## 10. Success criteria

- [ ] `pytest tests/ -q` green after every slice; total drop equals only the retired Regime-B tests.
- [ ] `grep` for retired script names in `.github/workflows/`, `src/`, `scripts/`, `mcp_servers/`
      returns zero (outside the files being deleted).
- [ ] No `sprint-sync` / `sprint-discipline` gate remains; no workflow pushes planning work to GitHub
      issues (the migration is actually finished).
- [ ] Coding standards + Economist-voice rules exist in exactly one authoritative place; `GEMINI.md`,
      Copilot files, and CONTRIBUTING's duplicated sections are pointers.
- [ ] Exactly one ADR skill and one CI/automation skill remain.
- [ ] `docs.yml` (mkdocs) builds with no dangling nav/link to a deleted file.
- [ ] `CLAUDE.md` references no retired artifact; a single, coherent Regime A remains.
- [ ] Root tree free of stale SPRINT/badge/report artifacts.

## 11. Open questions for LGTM

1. **Regime-B code:** full retire (assumed) vs leave scripts dormant but drop skills/workflows?
2. **`.github/agents/*.agent.md` + `AGENTS.md`:** retire (assumed), or keep the personas as an
   optional `Agent`-tool roster decoupled from Scrum?
3. **`nightly-eval.yml`:** confirm it only evaluates Regime-B agents (retire) and isn't measuring
   content-pipeline quality (would move to KEEP).
4. **Ambiguous state JSONs** (`agent_metrics`, `chart_metrics`, `quality_history`,
   `feature_registry`, `ci_health_patterns`): retire or keep — depends on whether a KEEP script
   still writes them (to be resolved in `plan` with a writer-grep).
5. **Artifacts:** hard delete (assumed) vs `/archived/` move?
```
