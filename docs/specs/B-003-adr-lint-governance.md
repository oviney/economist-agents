# Spec: B-003 — Repair adr-lint gate + ADR governance drift

> Slice 1 of the 2026-06-14 backlog sprint (see `BACKLOG.md` → Sprint Goal).
> Source item: `BACKLOG.md` B-003 (was GitHub #428).

## Objective

The `adr-lint` pre-commit hook is broken and is silently blocking **all** commits
that touch `docs/adr/`, which means no new ADR can be landed through the gate.
Restoring the hook also un-masks two pre-existing governance violations the broken
hook had been hiding. We will:

1. **Restore the gate** so `adr-lint` runs and passes on a clean tree.
2. **Fix the drift the gate exposes** (ADR-0010 non-compliance).
3. **Land ADR-0011 (Deep Research)** — the #390 decision currently undocumented as an ADR.

**Success = `pre-commit run adr-lint --all-files` exits 0**, ADR-0010 and ADR-0011
are both compliant and present in `mkdocs.yml`, and the docs site builds.

## Root cause (verified 2026-06-14)

- `.pre-commit-config.yaml:64` → `entry: .venv/bin/python scripts/lint_adrs.py`.
- `scripts/lint_adrs.py` **does not exist**; it was archived to
  `scripts/archived/lint_adrs.py` during the ADR-0010 scripts→src migration. The
  hook therefore fails with `can't open file '.../scripts/lint_adrs.py'` on any
  `docs/adr/` change.
- The archived script's `repo_root` default is `Path(__file__).parent.parent`. From
  `scripts/lint_adrs.py` that resolves to the **repo root** (correct); from
  `scripts/archived/` it resolves to `scripts/` (wrong). → Restoring to `scripts/`
  needs no `--repo-root` flag.
- Lint exposes: ADR-0010 status `Implemented` ∉ allowed set
  `{Proposed, Accepted, Rejected, Deprecated, Superseded}`; and ADR-0010 absent from
  `mkdocs.yml` nav (nav currently stops at ADR-0009).

## Decision: restore to `scripts/`, not migrate to `src/`

`lint_adrs.py` is dev/governance tooling, not pipeline runtime code, and the active
hook already references `scripts/lint_adrs.py`. **Restore the file to `scripts/`**
(lowest-risk, matches both the hook path and the `repo_root` default). Migrating it
into `src/` + repointing the hook + patching `repo_root` is strictly more change for
no behavioural gain. *(Flag: this lightly contradicts ADR-0010's "archive" intent —
but the file was archived while still wired to a live hook, i.e. archived in error.)*

## Commands

```
Restore script:   git mv scripts/archived/lint_adrs.py scripts/lint_adrs.py
Run the gate:     pre-commit run adr-lint --all-files
Lint directly:    .venv/bin/python scripts/lint_adrs.py
Build docs:       mkdocs build --strict
Tests:            pytest -q          # if a governance test is added
```

## Scope of changes (≤5 files)

| File | Change |
|------|--------|
| `scripts/lint_adrs.py` | Restore from `scripts/archived/` via `git mv` (history preserved) |
| `docs/adr/0010-scripts-to-src-migration.md` | Status `Implemented` → `Accepted` |
| `docs/adr/0011-opt-in-recursive-deep-research.md` | **New** — author from the BACKLOG.md draft |
| `mkdocs.yml` | Add ADR-0010 and ADR-0011 to the `ADRs:` nav block |

## Code style / ADR format

ADR-0011 follows `docs/adr/TEMPLATE.md` and the existing 0001–0010 format. Required
header line the linter parses: `**Status:** Accepted`. Body uses the
Context / Decision / Consequences / References sections from the BACKLOG.md draft
verbatim (Status: Accepted · Date: 2026-06-13 · Decision Maker: Ouray Viney).

## Testing Strategy

- **Primary gate:** `pre-commit run adr-lint --all-files` exits 0.
- **Docs:** `mkdocs build` (non-strict) succeeds — this matches CI, which deploys via
  `mkdocs gh-deploy` (`.github/workflows/docs.yml`), **not** `--strict`. NOTE:
  `mkdocs build --strict` aborts on **149 pre-existing warnings already present on
  `main`** (unrelated to this slice — stale links in `skills/README.md`,
  `AUTONOMOUS_ORCHESTRATION_STRATEGY.md`, etc.). Fixing strict-mode debt is **out of
  scope** for B-003.
- **Noticed, not touching (out of scope):** ADR-0010 contains a broken relative link
  (`../../SPEC.md` → resolves to a missing target). Pre-existing; not decision content;
  left as-is per the "ask first" boundary on ADR-0010 content.
- **Regression guard (lightweight):** the lint script *is* the regression test for
  ADR compliance. No new pytest needed unless review wants the hook path asserted;
  if so, add a one-test check that `scripts/lint_adrs.py` exists and is executable.

## Boundaries

- **Always:** run `adr-lint` + `mkdocs build --strict` before committing; preserve
  git history via `git mv`.
- **Ask first:** any change to ADR-0010's *decision content* (we only touch its
  status field + nav, not its substance); moving the script into `src/`.
- **Never:** edit ADRs 0001–0009; weaken the linter's allowed-status set to make
  `Implemented` pass (fix the ADR, not the rule).

## Success Criteria

1. `scripts/lint_adrs.py` exists and runs from repo root with no flags.
2. `pre-commit run adr-lint --all-files` exits 0.
3. ADR-0010 status is `Accepted` and appears in `mkdocs.yml` nav.
4. ADR-0011 exists, is lint-compliant, and appears in `mkdocs.yml` nav.
5. `mkdocs build` (non-strict, matches CI) succeeds and renders ADR-0010 + 0011.
6. A trivial `docs/adr/` edit can pass through the pre-commit gate (the original bug).

## Open Questions

None blocking. One flagged decision (restore-to-`scripts/` vs migrate-to-`src/`) is
resolved above in favour of restore; raise in review if you disagree.
