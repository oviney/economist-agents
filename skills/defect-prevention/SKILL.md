# Defect Prevention Skill

## Purpose
When the editorial judge or article evaluator detects a failure pattern,
automatically codify it as a prevention rule so future articles avoid the
same defect.  This closes the feedback loop between detection and prevention.

## How Prevention Rules Work

### Existing System
`scripts/defect_prevention_rules.py` contains `DefectPrevention` class with
5 active rules learned from historical bugs (BUG-015 through BUG-022):

```python
class DefectPrevention:
    def check_all(self, content: str, metadata: dict) -> list[str]:
        """Run all prevention checks, return list of violation messages."""
        violations = []
        violations.extend(self._check_chart_embedding(content, metadata))
        violations.extend(self._check_category_present(content))
        violations.extend(self._check_duplicate_chart(content))
        violations.extend(self._check_badge_currency(content))
        violations.extend(self._check_sprint_doc_currency(content))
        return violations
```

### Rule Format
Each prevention rule is a method on `DefectPrevention` that:
1. Takes `content: str` and optional `metadata: dict`
2. Checks for a specific pattern via regex or string matching
3. Returns `list[str]` of violation messages (empty if clean)
4. Message format: `"[SEVERITY] Description (Pattern: BUG-NNN-pattern)"`

### Adding New Rules

When a new failure pattern is detected:

1. **Identify the pattern** — what specific text/structure caused the failure?
2. **Write a check method** — deterministic, no LLM needed
3. **Add to `check_all()`** — so it runs on every article
4. **Write a test** — in `tests/test_defect_prevention.py`

Example — adding a rule for missing `layout: post`:
```python
def _check_layout_field(self, content: str) -> list[str]:
    """BUG-028 prevention: Ensure layout: post in frontmatter."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3 and "layout:" not in parts[1]:
            return ["[CRITICAL] Missing layout: post in frontmatter (Pattern: BUG-028-pattern)"]
    return []
```

## Feedback Loop Architecture

```
Editorial Judge detects failure
  ↓
Log failure pattern to logs/defect_patterns.json
  ↓
Pattern analysis: is this a new pattern or known?
  ↓
If new: generate prevention rule
  ↓
Add rule to defect_prevention_rules.py
  ↓
Add rule to stage4_crew._apply_editorial_fixes() if deterministic fix possible
  ↓
Next article benefits from prevention
```

## Existing Files to Modify
- `scripts/defect_prevention_rules.py` — add new `_check_*` methods
- `src/crews/stage4_crew.py` — add deterministic fixes to `_apply_editorial_fixes()`
- `scripts/publication_validator.py` — add validation checks

## Pattern Storage Schema

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

## Integration Points
- Editorial judge (`scripts/editorial_judge.py`) — source of failure patterns
- Article evaluator (Story #116) — source of low-scoring dimensions
- Deterministic polish (`stage4_crew._apply_editorial_fixes`) — applies fixes
- Publication validator — enforces rules before publication
