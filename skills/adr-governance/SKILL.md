---
name: adr-governance
version: 1.0.0
description: Rules for writing, numbering, and superseding Architectural Decision Records so the ADR tree stays coherent and auditable
category: governance
author: ouray.viney
created: 2026-04-06
last_evaluated: 2026-04-06

agents:
  - Product Owner
  - Scrum Master
  - Developer
  - Reviewer

eval_criteria:
  - metric: adr_lint_pass_rate
    description: "Percentage of commits touching docs/adr/ that pass scripts/lint_adrs.py"
    target: "1.0"
    source: ci
  - metric: supersession_link_integrity
    description: "Every Superseded ADR has a Supersedes link pointing back, and vice versa"
    target: "1.0"
    source: scripts/lint_adrs.py
  - metric: adr_location_uniqueness
    description: "Zero ADR files exist outside docs/adr/"
    target: "1.0"
    source: scripts/lint_adrs.py

dependencies:
  - sprint-management

complements:
  - agent-delegation
  - quality-gates
---

# ADR Governance Skill

## Purpose

Keep the Architectural Decision Record tree coherent, auditable, and
immutable. Every significant architectural decision in the repo lives
in a single canonical location with a consistent format, a deterministic
numbering scheme, and a formal supersession lifecycle.

This skill codifies the rules that Sprint 21 consolidation (Story #177)
put in place after the repo accumulated 11+ ADR files across three
directories with colliding numbers.

## When to Invoke

- Any PR that adds or modifies a file under `docs/adr/`
- Any architectural debate in chat that produces a decision ("should we
  use X framework", "how should we structure Y")
- Any proposal to deprecate or replace an existing architectural
  approach
- Any status transition on an existing ADR (Proposed → Accepted,
  Accepted → Superseded)

## The Rules

### Rule 1: One Canonical Location

All ADRs live in `docs/adr/`. No exceptions.

**Forbidden paths:**
- `docs/ADR-*.md` (pre-consolidation legacy location)
- `docs/architecture/ADR*.md` (pre-consolidation legacy location)
- Any ADR in a component-specific subdirectory

The CI lint (`scripts/lint_adrs.py`) enforces this automatically.

### Rule 2: MADR Filename Format

Filename pattern: `NNNN-kebab-case-title.md`

- `NNNN` is a 4-digit number, zero-padded, globally sequential across
  the entire repo
- Title is lowercase kebab-case, descriptive of the decision
- Example: `0006-agent-framework-selection.md`

**Numbering rule:** PR author claims the next available number at PR
open time. If two PRs collide at merge, the rebaser bumps to the next
number. Numbers are never reused, even for rejected or superseded
ADRs.

### Rule 3: Mandatory Header Format

Every ADR starts with exactly these fields:

```markdown
# ADR-NNNN: Title

**Status:** <one of: Proposed | Accepted | Rejected | Deprecated | Superseded>
**Date:** YYYY-MM-DD
**Decision Maker:** <name or role>
**Supersedes:** <ADR-NNNN link, if applicable>
**Superseded by:** <ADR-NNNN link, if applicable>
```

**Status values are a closed set.** No "Implemented", no "Approved",
no emoji, no "In Progress". Use only the five allowed values.

### Rule 4: Mandatory Body Sections

```markdown
## Context
Why are we making this decision? What forces are at play?

## Decision
What is the decision, in one clear paragraph?

## Alternatives Considered
What other options were on the table? Why rejected?

## Consequences
What becomes easier? Harder? What follow-up work is implied?
```

Additional sections (Research, Objectives, Risks) are welcome but
these four are required.

### Rule 5: Immutability After Accepted

Once an ADR's status is `Accepted`, the body is immutable. Typos and
broken links can be fixed, but the decision content, rationale, and
consequences cannot be rewritten. If the context changes, write a new
ADR that supersedes it.

**Why:** ADRs document *what was true when the decision was made*.
Rewriting history defeats their purpose. Git blame should show the
original rationale.

### Rule 6: Bidirectional Supersession

When a new ADR supersedes an old one:

1. New ADR header gets `Supersedes: [ADR-NNNN](link)`
2. New ADR body includes a supersession note explaining *why the
   context changed* (not just "we decided differently")
3. Old ADR status changes to `Superseded`
4. Old ADR header gets `Status: Superseded by [ADR-NNNN](link) as of YYYY-MM-DD`
5. Old ADR body gets a supersession note pointing to the replacement

The CI lint verifies both sides of the link. Breaking one side fails
the build.

### Rule 7: Not Everything Is an ADR

ADRs are for architectural decisions that are expensive to reverse:
framework choice, data model, security model, agent delegation
matrix, API contracts.

ADRs are NOT for:
- Implementation status reports ("REFACTORING-COMPLETE") — belong in
  PR descriptions or CHANGELOG
- Coding conventions — belong in `docs/ARCHITECTURE_PATTERNS.md` or
  a skill
- Sprint plans — belong in sprint docs
- Bug fix rationale — belong in commit messages

If you're unsure, ask: "If we reversed this in six months, would it
cost more than a day?" If no, it's not an ADR.

### Rule 8: Index in mkdocs.yml

Every ADR must be referenced in `mkdocs.yml` under the ADRs nav
section. Orphaned ADRs (not in the nav) fail the CI lint.

## Delegation

Per [ADR-0008 Agent Skill Governance](../../adr/0008-agent-skill-governance.md)
and [agent-delegation](../agent-delegation/SKILL.md):

| Action | Who |
|--------|-----|
| Draft new ADR | Any agent, typically Developer or Scrum Master |
| Propose ADR (status: Proposed) | Any agent |
| Accept ADR (status: Accepted) | **Engineering Lead only** — human approval |
| Reject ADR (status: Rejected) | **Engineering Lead only** |
| Supersede ADR (status: Superseded) | **Engineering Lead only** — paired with new Accepted ADR |
| Deprecate ADR (status: Deprecated) | **Engineering Lead only** |

Status transitions to Accepted/Rejected/Deprecated/Superseded are
architectural decisions in themselves and fall under
`agent-delegation` Rule 6 (architecture → human approval required).

## Template

See [docs/adr/TEMPLATE.md](../../adr/TEMPLATE.md) for the canonical
starting template. Copy it to a new file, assign the next number,
fill in the sections, and open a PR.

## Tooling

- `scripts/lint_adrs.py` — CI lint enforcing all rules above. Runs in
  pre-commit and in CI on every PR touching `docs/adr/` or
  `mkdocs.yml`.
- Future (issue #178): evaluate [Log4brains](https://github.com/thomvaill/log4brains)
  for static-site rendering of the ADR supersession graph.

## Anti-Patterns

### 1. Editing an Accepted ADR
**What happens:** Git blame no longer shows the original rationale,
readers can't tell what was true when the decision was made.
**Rule:** Immutable after Accepted. Write a new ADR if the context
changes.

### 2. Deleting a Rejected or Superseded ADR
**What happens:** Future teams re-litigate the same debates without
knowing why the original choice was made or rejected.
**Rule:** Never delete. Mark as Rejected or Superseded and keep the
file.

### 3. Duplicating ADRs Across Directories
**What happens:** Readers get conflicting versions; status drift
between copies (see Sprint 21 #173).
**Rule:** One canonical location. CI lint blocks files outside
`docs/adr/`.

### 4. Using ADRs as Implementation Reports
**What happens:** The ADR tree becomes a dumping ground for status
updates, obscuring the real architectural decisions.
**Rule:** ADRs document decisions, not implementation progress. Use
PR descriptions and CHANGELOG for status.

### 5. Vague Status Values
**What happens:** "Implemented", "Approved", "In Progress" — the
status field becomes unparseable and CI can't enforce rules.
**Rule:** Closed status set only. Lint rejects anything else.

## Example: Sprint 21 Consolidation

Story #177 applied this skill to consolidate 11+ ADR files. The
process:

1. Inventory all ADR files across three directories
2. Identify canonical vs duplicate vs not-an-ADR
3. Renumber to global MADR sequence in `docs/adr/`
4. Add bidirectional supersession between ADR-0003 and ADR-0006
5. Archive orphaned duplicates to `docs/archive/adr-pre-consolidation/`
6. Delete non-ADR content (ADR-002-REFACTORING-COMPLETE)
7. Create this skill and the CI lint
8. Update mkdocs.yml, docs/README.md, docs/index.md to match

This was a one-time consolidation. Going forward, this skill prevents
the problem from recurring.
