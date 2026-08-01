---
name: defect-prevention
description: Codify editorial failure patterns as deterministic prevention rules. Use when a new bug pattern is detected by the editorial judge, when adding post-mortem rules after a defective article ships.
---

# Defect Prevention

## Overview

Automatically converts detected failure patterns into deterministic prevention rules so future articles avoid the same defect. Closes the feedback loop between detection and prevention.

## When to Use

- Editorial judge or article evaluator detects a recurring failure pattern
- A new bug (BUG-NNN) has been root-caused and needs a prevention rule
- Adding a deterministic fix to the editorial polish stage

### When NOT to Use

- One-off content issues that won't recur (e.g., a typo in a single article)
- Stylistic preferences — those belong in `economist-writing`
- Issues requiring LLM judgment — prevention rules must be deterministic

## Core Process

```
1. Editorial Judge detects failure
   ↓
2. Log failure pattern to logs/defect_patterns.json
   ↓
3. Pattern analysis: new or known?
   ↓
4. If new → generate prevention rule method
   ↓
5. Add to DefectPrevention.check_all()
   ↓
6. Add deterministic fix to stage4_crew._apply_editorial_fixes() if possible
   ↓
7. Write test in tests/test_defect_prevention.py
   ↓
8. Next article benefits from prevention
```

### Rule Format

Each prevention rule is a method on `DefectPrevention` that:

1. Takes `content: str` and optional `metadata: dict`
2. Checks for a specific pattern via regex or string matching
3. Returns `list[str]` of violation messages (empty if clean)
4. Message format: `"[SEVERITY] Description (Pattern: BUG-NNN-pattern)"`

### Adding a New Rule

```python
def _check_layout_field(self, content: str) -> list[str]:
    """BUG-028 prevention: Ensure layout: post in frontmatter."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3 and "layout:" not in parts[1]:
            return ["[CRITICAL] Missing layout: post in frontmatter (Pattern: BUG-028-pattern)"]
    return []
```

### Pattern Storage Schema

```json
{
  "patterns": [
    {
      "id": "PATTERN-001",
      "detected_by": "editorial_judge",
      "check_name": "image_exists",
      "failure_message": "Image not found: /assets/images/test.png",
      "article": "2026-04-04-article.md",
      "timestamp": "2026-04-04T12:00:00Z",
      "prevention_rule_added": true,
      "rule_location": "defect_prevention_rules.py::_check_image_path"
    }
  ]
}
```

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "This bug only happened once" | If it happened once without a rule, it will happen again — codify it |
| "The LLM can just learn not to do that" | LLMs have no memory between runs; only deterministic rules persist |
| "We'll fix it in code review" | Human review doesn't scale; automated prevention catches 100% of known patterns |
| "The rule is too strict" | Better to have a false positive that gets refined than a missed defect in production |

## The defects tests cannot find: gaps in what is checked at all

A prevention rule guards a pattern *inside* the thing being checked. It cannot
guard something the check never sees. Two of the four defects closed on
2026-07-28 were of that second kind, and **neither was found by a failing test —
both were found by reading code adjacent to an unrelated fix:**

- **BUG-064** — `_graphics_with_retry` handed every attempt the FULL budget
  instead of the remaining balance, so three retries could spend 3× the operator's
  cap. Found while fixing **BUG-061**, its exact mirror image in the *writer* loop.
  Every test passed throughout: the suite asserted the retry *policy*, never the
  budget *arithmetic*, and nothing compared the two loops to each other.
- **BUG-065** — the hero-prompt comment reached a published post. The validator
  has a check built for exactly this ("placeholder text that should never be
  published") and it could not fire, because the comment is injected *after*
  Stage 4 by design. The artefact the validator blessed was not the artefact that
  shipped (ADR-0017).

**The generalisable habit:** when you fix a defect, read the *sibling* — the other
retry loop, the other entry point, the other deploy path. Both of these bugs were
one function away from a fix that was already being made. And when a gate exists
for a class of problem that still escaped, ask whether the gate can *see* the
thing at all before adding a pattern to it — a rule that can never fire is worse
than no rule, because it reads like protection.

Neither of these belongs in `check_all()`. They are recorded here because the
lesson is about *where to look*, not about a pattern to match.

## The defect that was never there: asserting from a surface reading

The costliest defects in this repo's record are not the ones that shipped. They
are the three that **did not exist** and were acted on anyway. Each was asserted
from a glance, and each was disproved by a single command that takes under a
second:

| Claim | Disproved by | Cost of not running it first |
|---|---|---|
| A hero image had a clipped top card | a four-line border-pixel check | a $0.49 redraw that fixed nothing (B-027) |
| `.gitignore` left `defect_tracker.json` untracked, so three defects existed on one laptop only | `git ls-files` | a whole backlog item, opened and withdrawn (~~B-025~~) |
| `backup/integration-test-20260728` was "the only copy" of the auth work | `git branch --contains 73e73c0` | three days of caution shaping B-023's framing |

The shape is identical every time. An observation arrives that *looks* like
evidence — a thumbnail, a `git add` hint about a directory pattern, a branch name
with "backup" in it. It gets promoted to a finding without the one check that
would settle it, and then work is built on top.

Note what the second one actually was: `git add` printed *"The following paths
are ignored… data/skills_state"*, a **hint** about the directory pattern. The
already-tracked file was staged anyway and went into the commit. A hint was read
as an error.

**The rule: before an observation becomes a finding, name the command that would
disprove it — then run that command first.**

If you cannot name such a command, say so explicitly and mark the claim as
unverified rather than asserting it. This is cheap: all three commands above are
sub-second, and all three were available at the moment the claim was made.

This is a *habit*, not a `check_all()` rule — there is no artefact to pattern-match
against. It is recorded here because three instances make it a class, not an
accident.

## Red Flags

- **A claim about the repo's state that no command was run to confirm** — "the
  only copy", "that file is untracked", "the image is clipped". Run the command.
- **A tool hint read as a tool error** — `git add`'s ignored-paths notice is the
  worked example. Check the exit code and the resulting state, not the prose.
- **A gate that cannot see what it is meant to guard** — e.g. a check that runs
  before the content it validates is injected. Verify the ordering, not just the
  pattern.
- **A fix applied to one of two mirrored code paths** — retry loops, deploy entry
  points, `deploy()`/`deploy_review()`. Fix the sibling or log why not.
- Prevention rule uses LLM calls instead of deterministic checks
- Rule added to `check_all()` but no corresponding test written
- Pattern logged but no prevention rule created within the same sprint
- Rule silently passes without a violation message format (`[SEVERITY] ... (Pattern: BUG-NNN)`)
- Duplicate rules checking the same pattern with different names

## Verification

- [ ] New rule method exists on `DefectPrevention` class with `_check_` prefix
- [ ] Rule is called from `check_all()` — **evidence**: grep shows the method in the call chain
- [ ] Test exists in `tests/test_defect_prevention.py` covering both pass and fail cases
- [ ] Pattern logged in `logs/defect_patterns.json` with `prevention_rule_added: true`
- [ ] If deterministic fix is possible, added to `stage4_crew._apply_editorial_fixes()`

### Integration Points

- `scripts/defect_prevention_rules.py` — add new `_check_*` methods
- `src/crews/stage4_crew.py` — add deterministic fixes to `_apply_editorial_fixes()`
- `scripts/publication_validator.py` — add validation checks
- `scripts/editorial_judge.py` — source of failure patterns
