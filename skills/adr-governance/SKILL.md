---
name: adr-governance
description: Rules for writing, numbering, and superseding Architectural Decision Records. Use when creating a new ADR, when changing an ADR's status, when consolidating or auditing the ADR tree.
---

# ADR Governance

## Overview

Keeps the Architectural Decision Record tree coherent, auditable, and immutable. Every significant architectural decision lives in `docs/adr/` with consistent format, deterministic numbering, and formal supersession lifecycle.

## When to Use

- Any PR that adds or modifies a file under `docs/adr/`
- Any architectural debate that produces a decision
- Any proposal to deprecate or replace an existing approach
- Any status transition (Proposed -> Accepted, Accepted -> Superseded)

### When NOT to Use

- Implementation status reports — belong in PR descriptions or CHANGELOG
- Coding conventions — belong in `docs/ARCHITECTURE_PATTERNS.md` or a skill
- Sprint plans — belong in sprint docs
- Bug fix rationale — belong in commit messages
- Decisions reversible in under a day — not worth an ADR

## Core Process

### The 8 Rules

**Rule 1: One Canonical Location.** All ADRs live in `docs/adr/`. No files in `docs/ADR-*.md` or `docs/architecture/ADR*.md`. CI lint enforces this.

**Rule 2: MADR Filename Format.** Pattern: `NNNN-kebab-case-title.md`. Zero-padded 4-digit number, globally sequential. Numbers never reused.

**Rule 3: Mandatory Header.**
```markdown
# ADR-NNNN: Title

**Status:** Proposed | Accepted | Rejected | Deprecated | Superseded
**Date:** YYYY-MM-DD
**Decision Maker:** <name or role>
**Supersedes:** <ADR-NNNN link, if applicable>
**Superseded by:** <ADR-NNNN link, if applicable>
```
Status values are a closed set — no "Implemented", "Approved", "In Progress".

**Rule 4: Mandatory Body Sections.** Context, Decision, Alternatives Considered, Consequences. Additional sections welcome.

**Rule 5: Immutability After Accepted.** Body is immutable once Accepted. Typo fixes allowed; decision content cannot be rewritten. If context changes, write a new ADR that supersedes.

**Rule 6: Bidirectional Supersession.** New ADR gets `Supersedes:` link. Old ADR status changes to `Superseded` with back-link. CI lint verifies both sides.

**Rule 7: Not Everything Is an ADR.** Only for decisions expensive to reverse: framework choice, data model, security model, agent delegation, API contracts. Ask: "If reversed in 6 months, would it cost more than a day?"

**Rule 8: Index in mkdocs.yml.** Every ADR must be in the nav section. Orphaned ADRs fail CI lint.

### Delegation Matrix

| Action | Who |
|--------|-----|
| Draft new ADR | Any agent |
| Propose (status: Proposed) | Any agent |
| Accept / Reject / Supersede / Deprecate | **Engineering Lead only** — human approval required |

### Tooling

- `scripts/lint_adrs.py` — CI lint enforcing all rules (pre-commit + CI)
- Template: `docs/adr/TEMPLATE.md`

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "This decision isn't important enough for an ADR" | If reversing it costs more than a day, it needs one — that's the threshold |
| "I'll just update the existing ADR instead of writing a new one" | Rewriting history defeats the purpose; git blame should show original rationale |
| "We can delete rejected ADRs to keep things clean" | Future teams re-litigate the same debates without knowing why options were rejected |
| "The ADR can live next to the code it describes" | Multiple locations cause drift and collisions — one canonical directory prevents this |
| "We don't need the lint — we'll be careful" | Sprint 21 found 11+ files across 3 directories with colliding numbers; careful doesn't scale |

## Red Flags

- ADR file exists outside `docs/adr/` (legacy location drift)
- Accepted ADR body modified (rationale rewrite)
- Supersession link only goes one direction (missing back-link)
- Status value not in the closed set (Proposed/Accepted/Rejected/Deprecated/Superseded)
- ADR not referenced in `mkdocs.yml` nav section
- ADR used for implementation status instead of architectural decision
- Number collision between two ADRs

## Verification

- [ ] ADR lives in `docs/adr/` — **evidence**: `scripts/lint_adrs.py` passes, no files in legacy locations
- [ ] Filename matches `NNNN-kebab-case-title.md` — **evidence**: lint check
- [ ] Header has all required fields (Status, Date, Decision Maker) — **evidence**: lint check
- [ ] Body has all 4 mandatory sections — **evidence**: grep for `## Context`, `## Decision`, `## Alternatives`, `## Consequences`
- [ ] If superseding: bidirectional links present — **evidence**: lint verifies both sides
- [ ] Referenced in `mkdocs.yml` — **evidence**: lint check for orphaned ADRs
- [ ] `scripts/lint_adrs.py` passes in CI — **evidence**: green CI check
