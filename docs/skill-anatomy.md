# Skill Anatomy

The canonical format every `skills/*/SKILL.md` file in this repo must
follow. Adapted from the addyosmani/agent-skills convention. Enforced
by `scripts/validate_skills.py` (CI) and the pre-commit hook.

## File location

One skill per directory under `skills/`. The skill file is always named
`SKILL.md` (uppercase). The directory name is the canonical skill id
and must match the `name:` frontmatter field.

```
skills/
  economist-writing/
    SKILL.md
  python-quality/
    SKILL.md
  ...
```

## Frontmatter

YAML between `---` delimiters at the top of the file. Two required
fields, no others permitted:

```markdown
---
name: economist-writing
description: One-sentence description of when to use this skill. Should help an agent decide whether to load it.
---
```

- `name` — must equal the parent directory name. Lowercase kebab-case.
- `description` — single sentence, ends with a period, includes "Use
  when..." or "Use to..." so the trigger condition is explicit.

## Body — six required sections

Every skill body must contain these `##` headings, in this order. The
validator only checks that the headings exist; the contents are at the
author's discretion.

### `## Overview`

One paragraph: what the skill does and why it exists.

### `## When to Use`

Bulleted list of trigger conditions. Should be specific enough that an
agent can pattern-match against a user request. May include a `### When
NOT to Use` subsection.

### `## Core Process`

The actual procedure or rules. Sub-headings, tables, numbered lists,
and code samples are all welcome here. This is the longest section.

### `## Common Rationalizations`

A two-column markdown table mapping the temptation to the reality. Use
this section to head off shortcuts before they happen.

```markdown
| Rationalization | Reality |
|-----------------|---------|
| "We can skip step 3 just this once" | Skipping step 3 caused incident #117; never skip |
```

### `## Red Flags`

Bulleted list of warning signs that the skill is being misapplied or
that something has drifted off-pattern. Used by reviewers to spot bad
output quickly.

### `## Verification`

Bulleted checklist of how to prove the skill ran correctly. Each item
should reference the concrete evidence (a test, a CI check, a file
artefact, a metric). Format:

```markdown
- [ ] <claim> — **evidence**: <specific check>
```

## Optional but encouraged

- `## Examples` — concrete inputs and outputs
- `## References` — links to related ADRs, skills, or external docs

## Validation

Run `python scripts/validate_skills.py` to check the whole tree. The
script exits 0 when every `skills/*/SKILL.md` file:

1. Has the two required frontmatter fields and nothing else.
2. Has `name` equal to its parent directory name.
3. Contains all six required `##` body sections.

The same script runs in pre-commit and in the Quality Gates CI
workflow, so any non-compliant skill blocks merge.

## See also

- `skills/README.md` — the index of all skills in this repo
- `.claude-plugin/plugin.json` — plugin manifest pointing at the
  `skills` directory
- ADR-0008 — agent + skill governance
