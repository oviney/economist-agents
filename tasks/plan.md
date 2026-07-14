# Plan: Repo Process Consolidation

Derived from `docs/specs/repo-process-consolidation.md` after a dependency/coupling
investigation. **The investigation revised the spec:** several artifacts the spec put in
"RETIRE" are load-bearing for the KEEP test suite and are moved to a deferred, ADR-gated wave.

## Verification constraint

The full suite (1433 tests) **cannot be run in this environment** — `pip install -r requirements.txt`
fails building the `sgmllib3k` wheel (feedparser dep). Verification therefore relies on:
- **Local inspection/grep** for config + doc + artifact changes (no test imports them).
- **`scripts/validate_skills.py`** (globs `*/SKILL.md`; frontmatter-only — deleting a skill dir is safe).
- **CI** (`ci.yml`, `quality-tests.yml`, `docs.yml`) after push for the full-suite green.

## Coupling map (the reason for the re-slice)

| Target | Coupled to (KEEP) | Verdict |
|---|---|---|
| Sprint *skills* (`sprint-management`, `scrum-master`) | `validate_skills.py` globs only; `mkdocs.yml` nav | **Safe** — delete + fix nav |
| Sprint *workflows* (`sprint-discipline`, `sprint-sync`) | none (YAML, not pytest) | **Safe** |
| Stale artifacts (SPRINT.md, SPRINT_15_*, badges, `.deployment_state`, root `SPEC.md`, `.github/BACKLOG.md`, `.github` sprint docs, root sprint shell wrappers) | `README.md`, `mkdocs.yml`, the sprint workflows themselves | **Safe** — delete + fix README/nav |
| Instruction dup (`GEMINI.md`, root + `.github/copilot-instructions.md`, `CONTRIBUTING.md`) | none (prose) | **Safe** — shrink to pointers |
| `.github/agents/*.agent.md` (10 personas) + `AGENTS.md` + `scripts/agent_registry.py` | `test_llm_providers.py` (`list_agents()>0`, `match="scrum-master"`), `test_agent_registry_enhancement.py`, `test_architect_agent.py` — **ADR-002** | **DEFERRED** — architectural; needs ADR |
| `scripts/{sm,po,orchestrator}_agent.py`, `continuous_burndown.py`, `sprint_validator.py` + their tests | share `escalations/task_queue/sprint_tracker.json` writers with `src/backlog/*`, `src/quality/*`; `quality-tests.yml` runs `sprint_validator --validate-sprint || true` | **DEFERRED** — needs per-slice test removal + CI edit |
| `scripts/skills_manager.py`, `skills_gap_analyzer.py` | `src/quality/validate_closed_loop.py` imports `SkillsManager`; `chart_metrics.py` integrates it; `test_closed_loop_validation.py`, `test_validate_closed_loop.py`, `test_quality_system.py` | **RECLASSIFY → KEEP** (not Regime B) |
| State JSONs (`agent_metrics`, `chart_metrics`, `feature_registry`) | written by KEEP `src/quality/*`, `economist_agent.py` | **KEEP** |
| State JSONs (`sprint_tracker`, `task_queue`, `escalations`) | written by both Regime-B scripts **and** `src/backlog/*` | **DEFERRED** — with the scripts |

## Waves

### Wave 1 — Safe retirement (execute now, CI-verified)
Vertical slices; each independently committable; none touches a pytest import.

1. **Stale artifacts** — delete snapshot files + fix `README.md` badges/links + `mkdocs.yml` nav.
2. **Sprint skills** — delete `skills/sprint-management/`, `skills/scrum-master/` + fix `mkdocs.yml` nav.
3. **Sprint workflows** — delete `sprint-discipline.yml`, `sprint-sync.yml`; drop the `sprint_validator --validate-sprint || true` step from `quality-tests.yml`. (`remediation-sync.yml` is KEEP — content remediation, not sprint.)
4. **Instruction consolidation** — shrink `GEMINI.md`, root + `.github/copilot-instructions.md`, and `CONTRIBUTING.md`'s duplicated coding-standards/TDD prose to pointers at `CLAUDE.md` + skills.
5. **CLAUDE.md sync** — remove references to retired machinery so the doc points at nothing deleted.

### Wave 2 — Deferred (needs a decision / ADR before code deletion)
Do **not** execute under this plan. Requires a new spec/ADR:
- **W2-A** Retire or keep the AgentRegistry system (ADR-002): 10 personas + `AGENTS.md` + `agent_registry.py` + 3 KEEP tests. Decision: delete the whole cluster (write ADR superseding ADR-002) **or** keep it as a decoupled `Agent`-tool roster.
- **W2-B** Retire the autonomous agent scripts (`sm/po/orchestrator_agent`, `continuous_burndown`, `sprint_validator`) + their tests + disentangle `sprint_tracker/task_queue/escalations` writers in `src/backlog/*`.
- **W2-C** `nightly-eval.yml` + `scripts/benchmarks/measure_sm_effectiveness.py` (SM benchmark) + `sync-copilot.yml` — retire with W2-B.

### Spec correction
Update `docs/specs/repo-process-consolidation.md`: move `skills_manager`/`skills_gap_analyzer` to KEEP;
move personas/registry/agent-scripts to a Wave-2 "deferred, ADR-gated" section with the coupling evidence.

## Checkpoints
- After Wave 1: `git grep` finds no dangling reference to a deleted file in `README.md`, `mkdocs.yml`, `.github/workflows/`, `CLAUDE.md`; `docs.yml` build green; `ci.yml`/`quality-tests.yml` green in CI.
- Before Wave 2: human decision on W2-A (keep vs retire AgentRegistry).
