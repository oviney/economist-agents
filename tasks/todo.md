# TODO: Delete or archive dead files in scripts/ (#327)

## In Progress

- [ ] T4 — Open PR + close #327

## Pending

## Verification done in T3

- AC1 (22 deleted): ✓ committed in T1
- AC2 (33 archived): ✓ git mv complete, scripts/archived/ now has 32 + 1 nested
- AC3 (pytest same count): ✓ 1817 collected pre+post; 1734 pass / 84 skip / 0 fail
- AC4 (no archive paths in src/agents/tests imports): ✓ all 29 referenced modules are KEEP
- AC5 (TestNoCrewAIInSrcOrTests): ✓ 2/2 pass
- AC6 (4 run_story entries removed from ALLOWED_FILES): ✓ committed in T2

## Done

- [x] T1 — Delete 22 confirmed-dead files from scripts/; verify pytest count unchanged (1817 tests collected)
- [x] T2 — Remove 4 stale run_story*.py entries from ALLOWED_FILES in test_architecture_compliance.py (13/13 pass)
- [x] T2.5 — Staff-engineer reclassification: 12 ARCHIVE → KEEP total (7 from initial pre-execution review for `agents/` + test callers; 5 more after `test_continuous_burndown` collection error revealed callers in KEEP scripts). SPEC §2 amended in two rounds; ADR-0010 filed for follow-up `scripts/` → `src/` migration
- [x] T3 — Moved 33 ARCHIVE files to scripts/archived/ via git mv; removed `crewai_agents.py` and `visual_qa.py` from ALLOWED_FILES in test_architecture_compliance.py; updated docstring exceptions list; flipped `("crewai_agents.py", True)` → `("crewai_agents.py", False)` in parametrized test
