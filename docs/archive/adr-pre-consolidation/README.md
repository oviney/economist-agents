# Pre-Consolidation ADR Archive

These ADR files were duplicates of canonical ADRs that lived in `docs/adr/`
or at the `docs/` root prior to the Sprint 21 ADR consolidation
(Story #177).

They are preserved here for git history continuity and so that any
external links to the old paths have a trail to follow, but they are
**not canonical** and should not be referenced in new documentation.

## Mapping to Canonical ADRs

| Archived file | Canonical replacement |
|---------------|----------------------|
| `ADR-001-agent-configuration-extraction.md` | [`docs/adr/0001-extract-agent-definitions-to-yaml.md`](../../adr/0001-extract-agent-definitions-to-yaml.md) |
| `ADR-002-agent-registry-pattern.md` | [`docs/adr/0002-agent-registry-pattern.md`](../../adr/0002-agent-registry-pattern.md) |
| `ADR-003-crewai-migration-strategy.md` | [`docs/adr/0003-phased-crewai-migration.md`](../../adr/0003-phased-crewai-migration.md) (Superseded by 0006) |

## Why Archived

Prior to Sprint 21 the repo had three competing ADR directories with
colliding numbers:

- `docs/adr/` (new Sprint 20 ADRs)
- `docs/` root (pre-Sprint 20 ADRs)
- `docs/architecture/` (orphaned duplicates — these files)

This caused governance bug #173. The Sprint 21 consolidation:

1. Established `docs/adr/` as the single canonical location
2. Renumbered all eight real ADRs into a global `NNNN-kebab-title.md`
   MADR sequence
3. Added bidirectional supersession links for ADRs 0003 and 0006
4. Archived these duplicates here
5. Created `skills/adr-governance/SKILL.md` to prevent recurrence
6. Added a CI lint (`scripts/lint_adrs.py`) that forbids new ADRs
   outside `docs/adr/`

See Story #177 for the full consolidation record.
