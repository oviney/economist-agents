# TODO: Delete or archive dead files in scripts/ (#327)

## In Progress

- [ ] T3 — Move 38 ARCHIVE files to scripts/archived/; verify pytest count unchanged

## Pending

- [ ] T4 — AC4 grep + AC5 guard + full pytest + commit + close #327

## Done

- [x] T1 — Delete 22 confirmed-dead files from scripts/; verify pytest count unchanged (1817 tests collected)
- [x] T2 — Remove 4 stale run_story*.py entries from ALLOWED_FILES in test_architecture_compliance.py (13/13 pass)
- [x] T2.5 — Second staff-engineer pass reclassified 7 ARCHIVE → KEEP (live `agents/` + test callers); SPEC §2 amended; ADR-0010 filed for follow-up `scripts/` → `src/` migration
