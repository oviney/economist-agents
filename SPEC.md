# SPEC: Migrate domain modules from scripts/ to src/ (issue #344)

**Status**: APPROVED (worker dispatch 2026-05-15; implements ADR-0010)
**GitHub issue**: oviney/economist-agents#344
**ADR**: docs/adr/0010-scripts-to-src-migration.md
**Date**: 2026-05-15

---

## 1. Objective

Relocate the 12 domain modules currently in `scripts/` to appropriate
`src/` subpackages, update all live callers to use the new import paths,
remove the load-bearing `sys.path.insert(0, str(SCRIPTS_DIR))` hack from
`tests/test_architecture_compliance.py:22`, and archive the original
files to `scripts/archived/`.

This unblocks the final 7 archive moves from #327 and removes the
bare-name import path that masks import-graph problems.

---

## 2. Package layout decision

The 12 modules split into two cohesive subpackages by domain:

### `src/quality/` — quality, governance, and metrics (8 modules)

| Module (new path) | Old path |
|---|---|
| `src/quality/agent_reviewer.py` | `scripts/agent_reviewer.py` |
| `src/quality/agent_metrics.py` | `scripts/agent_metrics.py` |
| `src/quality/chart_metrics.py` | `scripts/chart_metrics.py` |
| `src/quality/defect_tracker.py` | `scripts/defect_tracker.py` |
| `src/quality/governance.py` | `scripts/governance.py` |
| `src/quality/schema_validator.py` | `scripts/schema_validator.py` |
| `src/quality/validate_closed_loop.py` | `scripts/validate_closed_loop.py` |
| `src/quality/visual_qa_zones.py` | `scripts/visual_qa_zones.py` |

### `src/backlog/` — backlog and CI tooling (4 modules)

| Module (new path) | Old path |
|---|---|
| `src/backlog/backlog_groomer.py` | `scripts/backlog_groomer.py` |
| `src/backlog/ci_health_monitor.py` | `scripts/ci_health_monitor.py` |
| `src/backlog/migrate_backlog_to_github.py` | `scripts/migrate_backlog_to_github.py` |
| `src/backlog/validate_documentation_accuracy.py` | `scripts/validate_documentation_accuracy.py` |

Each subpackage gets an `__init__.py` (empty, to declare the package).

**Rationale**: ADR-0010 suggested `src/economist_agents/quality/`, but
top-level `src/quality/` and `src/backlog/` match the existing layout
(`src/agent_sdk/`, `src/telemetry/`, `src/tools/`, `src/utils/`) and
keep import paths short.

---

## 3. Caller updates

### Group A — `agents/` and live tests (7 caller files)

| Caller | Old import | New import |
|---|---|---|
| `agents/writer_agent.py` | `from agent_reviewer import …`<br>`from governance import …` | `from src.quality.agent_reviewer import …`<br>`from src.quality.governance import …` |
| `agents/research_agent.py` | `from agent_reviewer import …`<br>`from governance import …` | `from src.quality.agent_reviewer import …`<br>`from src.quality.governance import …` |
| `agents/graphics_agent.py` | `from chart_metrics import …` | `from src.quality.chart_metrics import …` |
| `tests/test_quality_system.py` | `from agent_reviewer import …`<br>`from schema_validator import …` | `from src.quality.agent_reviewer import …`<br>`from src.quality.schema_validator import …` |
| `tests/test_quality_dashboard.py` | `patch("agent_metrics.AgentMetrics.…")`<br>`patch("scripts.defect_tracker.DefectTracker.…")` | `patch("src.quality.agent_metrics.AgentMetrics.…")`<br>`patch("src.quality.defect_tracker.DefectTracker.…")` |
| `tests/test_closed_loop_validation.py` | subprocess call to `scripts/validate_closed_loop.py` | subprocess call to `python -m src.quality.validate_closed_loop` |

### Group B — KEEP scripts (3 caller files)

| Caller | Old import | New import |
|---|---|---|
| `scripts/continuous_burndown.py` | `from backlog_groomer import …`<br>`from ci_health_monitor import …`<br>`from migrate_backlog_to_github import …`<br>`from validate_documentation_accuracy import …` | `from src.backlog.backlog_groomer import …`<br>`from src.backlog.ci_health_monitor import …`<br>`from src.backlog.migrate_backlog_to_github import …`<br>`from src.backlog.validate_documentation_accuracy import …` |
| `scripts/economist_agent.py` | `from agent_metrics import …`<br>`from chart_metrics import …`<br>`from governance import …`<br>`from visual_qa_zones import …` | `from src.quality.agent_metrics import …`<br>`from src.quality.chart_metrics import …`<br>`from src.quality.governance import …`<br>`from src.quality.visual_qa_zones import …` |
| `scripts/quality_dashboard.py` | `from agent_metrics import …`<br>`from defect_tracker import …` | `from src.quality.agent_metrics import …`<br>`from src.quality.defect_tracker import …` |

### Auxiliary: `skills_manager` (not migrated but blocks sys.path removal)

`scripts/skills_manager.py` is bare-imported by:
- `scripts/validate_closed_loop.py` (which itself is being migrated)
- `tests/test_quality_system.py:21`
- `tests/test_closed_loop_validation.py:19`

To make the `sys.path` hack removable, these callers will use the
fully-qualified `from scripts.skills_manager import SkillsManager`
form (which resolves via `pythonpath = .` in `pytest.ini`).

---

## 4. Removing the sys.path hack

After all callers in §3 use fully-qualified paths, remove
`sys.path.insert(0, str(SCRIPTS_DIR))` from
`tests/test_architecture_compliance.py:22`. The `SCRIPTS_DIR` variable
remains because the file uses it to iterate `scripts/*.py` for the
ADR-002 compliance check.

---

## 5. Archive

After all callers are updated and tests pass, move the original 12
files to `scripts/archived/`:

```bash
git mv scripts/agent_reviewer.py scripts/archived/
git mv scripts/agent_metrics.py scripts/archived/
git mv scripts/chart_metrics.py scripts/archived/
git mv scripts/defect_tracker.py scripts/archived/
git mv scripts/governance.py scripts/archived/
git mv scripts/schema_validator.py scripts/archived/
git mv scripts/validate_closed_loop.py scripts/archived/
git mv scripts/visual_qa_zones.py scripts/archived/
git mv scripts/backlog_groomer.py scripts/archived/
git mv scripts/ci_health_monitor.py scripts/archived/
git mv scripts/migrate_backlog_to_github.py scripts/archived/
git mv scripts/validate_documentation_accuracy.py scripts/archived/
```

---

## 6. Acceptance criteria (from #344)

- **AC1** — All 12 modules relocated to `src/quality/` or `src/backlog/`.
- **AC2** — All caller files updated (Group A: 6 files; Group B: 3 files).
- **AC3** — `sys.path.insert(0, str(SCRIPTS_DIR))` removed from
  `tests/test_architecture_compliance.py:22`.
- **AC4** — `pytest tests/ -q` passes with the same count (±0) vs starting
  state (1741 passed, 84 skipped on `main` post-Wave-3).
- **AC5** — Mock-patch paths updated.
- **AC6** — The 12 modules moved to `scripts/archived/`.

---

## 7. Boundaries

### Always do
- One commit per module migration.
- Run `pytest tests/ -q` and `ruff check --no-fix` + `ruff format --check`
  after each slice.

### Never do
- Migrate all 12 in a single commit.
- Touch unrelated code or apply drive-by formatters.
- Skip mock-patch path updates — they fail silently when wrong.
