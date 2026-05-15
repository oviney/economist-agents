# Plan: Migrate domain modules from scripts/ to src/ (issue #344)

**Spec**: SPEC.md
**ADR**: docs/adr/0010-scripts-to-src-migration.md
**Date**: 2026-05-15

## Dependency graph

```
T0 (create src/quality/, src/backlog/ packages)
  │
  ├──► T1..T8 (migrate Group A — 8 modules, one per slice)
  │       ├── T1: agent_reviewer (callers: writer_agent, research_agent, test_quality_system)
  │       ├── T2: governance (callers: writer_agent, research_agent, economist_agent)
  │       ├── T3: chart_metrics (callers: graphics_agent, economist_agent)
  │       ├── T4: schema_validator (callers: test_quality_system)
  │       ├── T5: agent_metrics (callers: economist_agent, quality_dashboard, test_quality_dashboard mocks)
  │       ├── T6: defect_tracker (callers: quality_dashboard, test_quality_dashboard mocks)
  │       ├── T7: validate_closed_loop (callers: test_closed_loop_validation subprocess)
  │       └── T8: visual_qa_zones (callers: economist_agent)
  │
  ├──► T9..T12 (migrate Group B — 4 modules, one per slice)
  │       ├── T9:  backlog_groomer
  │       ├── T10: ci_health_monitor
  │       ├── T11: migrate_backlog_to_github
  │       └── T12: validate_documentation_accuracy
  │       (all four callers in scripts/continuous_burndown.py)
  │
  ├──► T13 (skills_manager: convert to fully-qualified imports)
  │
  ├──► T14 (remove sys.path hack from tests/test_architecture_compliance.py)
  │
  ├──► T15 (move 12 originals to scripts/archived/)
  │
  └──► T16 (update SPEC.md §2 - mark †-rows as MIGRATED; final verification)
```

Each task is one commit. Verification after every task:
- `pytest tests/ -q` shows same pass/skip count as baseline
- `ruff check --no-fix` and `ruff format --check` clean

## Baseline

Before starting, capture baseline test count: `pytest tests/ -q`.
Expected: 1741 passed, 84 skipped (per worker brief).

## Tasks

### T0 — Create empty src/quality/ and src/backlog/ packages

- Create `src/quality/__init__.py` (empty)
- Create `src/backlog/__init__.py` (empty)
- Verify: `pytest tests/ -q` unchanged

### T1..T8 — Group A migrations (one module per commit)

For each module M (in T1..T8):
1. `git mv scripts/M.py src/quality/M.py`
2. Update bare-name imports in all callers to `from src.quality.M import …`
3. Run `pytest tests/ -q` — must show baseline count
4. Run ruff — must be clean
5. Commit: `refactor: migrate scripts/M.py to src/quality/M.py (#344)`

### T9..T12 — Group B migrations (one module per commit)

For each module M (in T9..T12):
1. `git mv scripts/M.py src/backlog/M.py`
2. Update `scripts/continuous_burndown.py` to `from src.backlog.M import …`
3. Run tests + ruff
4. Commit: `refactor: migrate scripts/M.py to src/backlog/M.py (#344)`

### T13 — Convert skills_manager bare imports to fully-qualified

Files: `tests/test_quality_system.py`, `tests/test_closed_loop_validation.py`.
Change `from skills_manager import SkillsManager`
to `from scripts.skills_manager import SkillsManager`.

Verify pytest unchanged, commit.

### T14 — Remove sys.path hack

`tests/test_architecture_compliance.py:22`: remove
`sys.path.insert(0, str(SCRIPTS_DIR))`. Keep `import sys` only if still
used; otherwise remove that too. Keep `SCRIPTS_DIR` (used for file scan).

Verify pytest unchanged, commit.

### T15 — Move 12 originals to scripts/archived/

Single commit: `git mv` all 12 to `scripts/archived/`. Run full test
suite + ruff. Commit.

### T16 — Update SPEC.md §2 and final verification

Update the 12 KEEP entries marked `†` in SPEC.md §2 — they now
classify as MIGRATED rather than KEEP. Add a note at the top of §2
linking to this issue's PR.

Final checks:
- `pytest tests/ -q` shows baseline count
- `ruff check --no-fix && ruff format --check` clean
- `grep -rEn '^(from|import) (agent_reviewer|governance|chart_metrics|schema_validator|agent_metrics|defect_tracker|validate_closed_loop|backlog_groomer|ci_health_monitor|migrate_backlog_to_github|validate_documentation_accuracy|visual_qa_zones)\b' agents/ src/ tests/ mcp_servers/` returns ZERO results

Commit and open PR.
