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

## Red Flags

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
