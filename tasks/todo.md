# TODO: Repo Process Consolidation

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/repo-process-consolidation.md`](../docs/specs/repo-process-consolidation.md)

## Wave 1 — Safe retirement (executing)

- [ ] **W1-0**: Correct the spec (skills_manager/skills_gap → KEEP; personas/scripts → Wave 2 deferred)
- [ ] **W1-1**: Delete stale snapshot artifacts + fix `README.md` + `mkdocs.yml`
  - AC: files gone; `git grep` finds no dangling ref in README/mkdocs; `docs.yml` builds
- [ ] **W1-2**: Delete `skills/sprint-management/`, `skills/scrum-master/` + fix `mkdocs.yml` nav
  - AC: dirs gone; `validate_skills.py` still passes (globs remaining skills); nav clean
- [ ] **W1-3**: Delete sprint workflows + drop `sprint_validator` step from `quality-tests.yml`
  - AC: `sprint-discipline.yml`, `sprint-sync.yml`, `remediation-sync.yml` gone; quality-tests.yml valid YAML
- [ ] **W1-4**: Shrink `GEMINI.md`, both copilot files, `CONTRIBUTING.md` dup → pointers to CLAUDE.md + skills
  - AC: coding standards stated once (authoritative); other files point, don't restate
- [ ] **W1-5**: Sync `CLAUDE.md` — remove references to retired machinery
  - AC: CLAUDE.md points at nothing deleted
- [ ] **Checkpoint**: push; confirm `ci.yml` / `quality-tests.yml` / `docs.yml` green in CI

## Wave 2 — Deferred (needs human decision / ADR — NOT in this pass)

- [ ] **W2-A**: Decide keep-vs-retire AgentRegistry (ADR-002): personas + AGENTS.md + agent_registry.py + 3 tests
- [ ] **W2-B**: Retire sm/po/orchestrator/continuous_burndown/sprint_validator scripts + tests + state disentangle
- [ ] **W2-C**: Retire nightly-eval.yml + measure_sm_effectiveness.py + sync-copilot.yml
