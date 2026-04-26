# Skill Anatomy

The canonical format for `skills/<name>/SKILL.md` files in this repository.

A SKILL.md file is a domain-specific knowledge document that one or more agents reference during execution. It encodes the **rules, processes, anti-patterns, and verification steps** for a single domain — e.g. `python-quality`, `economist-writing`, `architecture-patterns`. The purpose of this anatomy is to keep skills consistent so the architect's audit (`scripts/architecture_audit.py`) and the skills validator (`scripts/validate_skills.py`) can score them deterministically and so agents that depend on them can invoke them by stable section name.

## File and directory contract

- Path: `skills/<kebab-case-name>/SKILL.md`.
- The frontmatter `name:` field MUST equal the parent directory name.
- One SKILL.md per directory. No nested SKILL.md files.

## Required frontmatter

```yaml
---
name: <kebab-case-name>
description: <one sentence describing when to use this skill — used by agents to decide relevance>
---
```

The `description` is the primary trigger — write it so the architect or any consuming agent can decide whether to load this skill from the description alone. Avoid generic phrasing ("guidelines for X") and prefer trigger phrases ("Use when configuring the writer agent…", "Apply during code review when…").

## Required sections

Every SKILL.md MUST have these six top-level sections, in this order. All 17 skills currently in the repo follow this structure — the validator enforces it.

### 1. `## Overview`
One or two paragraphs. State what this skill is *for* and what it is *not* for. End with a sentence describing who or what consumes it (which agent, which gate, which workflow).

### 2. `## When to Use`
A bulleted list of concrete situations where the skill applies. Each bullet should be specific enough that a reader can match a real task to it without ambiguity.

Include a `### When NOT to Use` subsection that lists adjacent skills the reader might be looking for instead. Cross-reference them by slug.

### 3. `## Core Process`
The substantive content of the skill. This is where the rules, patterns, rubrics, or step-by-step procedures live. A subtitle is allowed (e.g. `## Core Process: The 10 Rules`, `## Core Process: 4-Layer Architecture`) — the validator matches the `## Core Process` prefix.

Use sub-headings (`###`) freely. Tables, fenced code blocks, and rubrics are encouraged — they make the skill machine-readable as well as human-readable.

### 4. `## Common Rationalizations`
A two-column table or bulleted list pairing the kind of rationalisation that leads to skipping the skill with the corrective reality. Examples:

| Rationalization | Reality |
|----------------|---------|
| "We can hand-edit it just this once" | Hand edits skip the gate that catches the next regression. |

This section exists because skills exist to resist convenient shortcuts. Documenting the shortcut explicitly makes it easier to refuse.

### 5. `## Red Flags`
A bulleted list of warning signs that the skill is being applied incorrectly or being bypassed. Used by reviewers to catch silent drift.

### 6. `## Verification`
How to check that the skill was actually applied — the test, the linter rule, the manual check. If the skill is enforced by a gate or hook, name it explicitly with the file path.

## Example structure

```markdown
---
name: example-skill
description: Use when X, to ensure Y, by following Z.
---

# Example Skill

## Overview

One or two paragraphs.

## When to Use

- Bullet 1
- Bullet 2

### When NOT to Use

- For X — that's `other-skill`

## Core Process

### Step 1
…

### Step 2
…

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| … | … |

## Red Flags

- …

## Verification

- Run `pytest tests/test_example.py`
- The pre-commit hook `…` enforces it
```

## Validator behaviour

`scripts/validate_skills.py` checks every `skills/<name>/SKILL.md` for:

1. Valid YAML frontmatter parses cleanly.
2. `name` field equals the parent directory name.
3. `description` is non-empty.
4. The six required sections (`## Overview`, `## When to Use`, `## Core Process` *(prefix-match — subtitle allowed)*, `## Common Rationalizations`, `## Red Flags`, `## Verification`) are all present.

Adding a SKILL.md that fails any of these checks fails the pre-commit hook and CI.

## References

- The skills library lives at `skills/`. See `skills/README.md` for the index.
- Format originally adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).
- The architect agent's rubric (`skills/architecture-patterns/SKILL.md`) and the validator (`scripts/validate_skills.py`) operate on this contract.
