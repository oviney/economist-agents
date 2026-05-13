# Plan: Delete or archive dead files in scripts/ (issue #327)

**Spec**: SPEC.md
**Date**: 2026-05-10

## Dependency graph

```
T1 (DELETE 22 files) ──► T2 (fix ALLOWED_FILES in test_architecture_compliance.py)
                               └──► T3 (ARCHIVE 44 files → scripts/archived/)
                                          └──► T4 (grep AC4 + full pytest + close #327)
```

T1 and T2 are coupled — the ALLOWED_FILES cleanup is only meaningful after
the run_story*.py files are deleted. T3 is independent of T1/T2 (no imports
change) but is easiest to verify after T1/T2 are green. T4 is the final gate.

---

## Tasks

### T1 — Delete the 22 confirmed-dead files

```bash
cd scripts && rm \
  fix_story11_import.py fix_typo.py \
  run_dev_crew.py run_dev_sprint_crew.py run_meta_sprint.py \
  run_story2_crew.py run_story7_crew.py run_story10_crew.py \
  run_story10_fix.py run_story11_crew.py \
  spike_crewai_baseline.py \
  test_agent_integration.py test_dev_crew_workflow.py \
  test_full_workflow_streamlined.py test_gap_analyzer.py \
  test_git_operations_direct.py test_hybrid_approach_validation.py \
  test_metrics.py test_real_debug_story.py test_setup.py \
  test_simple_git_workflow.py test_sprint_15_orchestration.py
```

DoD:
- `ls scripts/run_story*.py scripts/spike_*.py scripts/test_*.py` → all missing
- `pytest tests/ -q` → same count as before T1

---

### T2 — Remove stale entries from ALLOWED_FILES in test_architecture_compliance.py

`tests/test_architecture_compliance.py` has an `ALLOWED_FILES` set listing
scripts permitted to import LLM libraries directly. Four deleted files are
in that set:
- `run_story2_crew.py`
- `run_story7_crew.py`
- `run_story10_crew.py`
- `run_story11_crew.py`

Remove those four entries. No other change to the file.

DoD:
- `grep "run_story" tests/test_architecture_compliance.py` → 0 lines
- `pytest tests/test_architecture_compliance.py -v` → all pass

---

### T3 — Move 44 ARCHIVE files to scripts/archived/

Create `scripts/archived/` if it doesn't exist (it already does — leave
`scripts/archived/legacy_sync/` untouched).

Move each of the 44 ARCHIVE files (see SPEC.md §2 ARCHIVE table).
`templates/mission_template.py` → `scripts/archived/templates/mission_template.py`.

No `src/` imports reference any ARCHIVE file (verified by AC4 grep in T4).

DoD:
- All 44 files present under `scripts/archived/`
- None of the 44 remain in `scripts/`
- `pytest tests/ -q` → same count

---

### T4 — Final verification + close #327

1. AC4: `grep -rn "from scripts\." src/ | grep -v __pycache__`
   — every match must be a KEEP file
2. AC5: `pytest tests/test_architecture_compliance.py::TestNoCrewAIInSrcOrTests -v`
   — both guard tests pass
3. Full suite: `pytest tests/ -q` — count unchanged from pre-T1 baseline
4. Commit all three batches (T1+T2 together, T3 separately)
5. Close #327
