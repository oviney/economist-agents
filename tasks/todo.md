# TODO: Delete or archive dead files in scripts/ (#327)

## In Progress

- [ ] T3 — Move 44 ARCHIVE files to scripts/archived/; verify pytest count unchanged

## Pending

- [ ] T4 — AC4 grep + AC5 guard + full pytest + commit + close #327

## Done

- [x] T1 — Delete 22 confirmed-dead files from scripts/; verify pytest count unchanged (1817 tests collected)
- [x] T2 — Remove 4 stale run_story*.py entries from ALLOWED_FILES in test_architecture_compliance.py (13/13 pass)
