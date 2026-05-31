# TODO: Migrate domain modules from scripts/ to src/ (#344)

## In Progress

- [ ] T16 — Open PR + close #344

## Done

- [x] T0  — Scaffold src/quality/ and src/backlog/ packages
- [x] T1  — Migrate agent_reviewer.py to src/quality/
- [x] T2  — Migrate governance.py to src/quality/
- [x] T3  — Migrate chart_metrics.py to src/quality/
- [x] T4  — Migrate schema_validator.py to src/quality/
- [x] T5  — Migrate agent_metrics.py to src/quality/
- [x] T6  — Migrate defect_tracker.py to src/quality/ (+ fix latent test mock bug)
- [x] T7  — Migrate validate_closed_loop.py to src/quality/
- [x] T8  — Migrate visual_qa_zones.py to src/quality/
- [x] T9–T12 — Migrate backlog modules to src/backlog/ (single commit;
       scripts/continuous_burndown.py imports all four atomically)
- [x] T13 — Convert skills_manager bare imports to scripts.skills_manager
- [x] T14 — Remove sys.path.insert from tests/test_architecture_compliance.py
- [x] T15 — Originals removed from scripts/ via git mv (AC6 satisfied —
       no empty stubs left to archive)
- [x] T16 — Update SPEC.md §2 (12 †-rows moved to new MIGRATED section)

## Verification

- Pytest: 1756 passed, 84 skipped (matches baseline ±0)
- Ruff check: All checks passed!
- Ruff format: 229 files already formatted
- No bare-name imports of any of the 12 migrated modules remain in
  agents/, src/, tests/, or mcp_servers/
- sys.path.insert(0, str(SCRIPTS_DIR)) removed from test_architecture_compliance.py:22

## Acceptance criteria

- AC1 (12 modules to src/): ✓
- AC2 (callers updated): ✓ (agents/* + tests + scripts/continuous_burndown.py
  + scripts/economist_agent.py + scripts/quality_dashboard.py)
- AC3 (sys.path hack removed): ✓
- AC4 (pytest same count): ✓ (1756 + 84 vs 1756 + 84 baseline)
- AC5 (mock patch paths updated): ✓ (4× agent_metrics, 3× defect_tracker)
- AC6 (originals archived/removed): ✓ (originals removed via git mv)
