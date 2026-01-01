# Agent Quality Standards

**Inspired by:** Nick Tune's "Code Quality Foundations for AI-assisted Codebases"

This document defines the quality standards that all agents MUST follow when generating content. These are enforced through automated reviews and hard blocks.

---

## Core Principles

1. **Completeness Over Speed**: Never return incomplete output
2. **Verification Over Assumption**: Check claims with sources
3. **Self-Validation**: Validate own output before returning
4. **Explicit Over Implicit**: Make structure and requirements explicit

---

## RULES: Agent Output Standards

### Research Agent Standards

**MANDATORY FIELDS** (Agent MUST include):
```json
{
  "headline_stat": {
    "value": "string (specific number/percentage)",
    "source": "string (organization name, NOT URL)",
    "year": "string (YYYY format)",
    "verified": true
  },
  "data_points": [
    {
      "stat": "string (specific, quantified)",
      "source": "string (named organization/report)",
      "year": "string (YYYY)",
      "url": "string (source URL if available)",
      "verified": boolean
    }
  ],
  "chart_data": {
    "title": "string (noun phrase, NOT sentence)",
    "subtitle": "string (what is shown, units)",
    "type": "line|bar|scatter",
    "data": [...]
  }
}
```

**BANNED PATTERNS**:
- ❌ Generic sources: "studies show", "research indicates", "experts say"
- ❌ Missing verification flags
- ❌ Data without named source
- ❌ Relative dates: "recent study" (use specific year)

**QUALITY METRICS**:
- Verification rate: ≥ 90% of data points verified
- Named sources: 100% of statistics
- Chart data completeness: All required fields present

---

### Writer Agent Standards

**MANDATORY FRONT MATTER FIELDS**:
```yaml
---
layout: post                    # REQUIRED - No default
title: "Specific Context"       # REQUIRED - Must be specific (≥6 words)
date: YYYY-MM-DD               # REQUIRED - TODAY's date from system
categories: [primary, secondary] # REQUIRED - At least 1 category
author: "The Economist"         # OPTIONAL - Defaults to site config
---
```

**BANNED OPENINGS** (Auto-reject if detected):
- "In today's fast-paced world..."
- "It's no secret that..."
- "When it comes to..."
- "In recent years..."
- "Amidst the [noun] surrounding..."
- Any throat-clearing before the hook

**BANNED PHRASES**:
- "game-changer", "paradigm shift", "revolutionary"
- "leverage" (as verb)
- "it could be argued that", "some might say"
- "at the end of the day"

**BANNED CLOSINGS** (Auto-reject if detected):
- "In conclusion...", "To conclude...", "In summary..."
- "Only time will tell..."
- "remains to be seen"
- "will depend largely on..."
- Any summary of what was already said

**CHART EMBEDDING RULES** (If chart provided):
- MUST include: `![Chart title](chart_path)`
- MUST reference in text: "As the chart shows..." or similar
- MUST place after discussing relevant data

**QUALITY METRICS**:
- Banned pattern count: 0
- Front matter completeness: 100%
- Chart embedding: 100% if chart provided
- Readability score: Hemingway ≤ 10

---

### Editor Agent Standards

**QUALITY GATES** (All must PASS):

1. **Opening Gate**: First sentence contains striking fact
2. **Evidence Gate**: Every statistic has named source
3. **Voice Gate**: British spelling, active voice, no clichés
4. **Structure Gate**: Each section advances argument
5. **Ending Gate**: Implication/prediction, NOT summary

**VERIFICATION REMOVAL** (CRITICAL):
- MUST remove all `[NEEDS SOURCE]` flags
- MUST remove all `[UNVERIFIED]` markers
- MUST delete or properly source flagged claims
- Presence of flags = AUTOMATIC REJECTION

**QUALITY METRICS**:
- Gates passed: 5/5
- Verification flags: 0
- Weak endings fixed: 100%

---

### Graphics Agent Standards

**LAYOUT ZONES** (No violations allowed):
```
RED BAR ZONE:    y: 0.96 - 1.00  (red bar only)
TITLE ZONE:      y: 0.85 - 0.94  (title, subtitle)
CHART ZONE:      y: 0.15 - 0.78  (data, labels)
X-AXIS ZONE:     y: 0.08 - 0.14  (x-axis labels ONLY)
SOURCE ZONE:     y: 0.01 - 0.06  (source line)
```

**LABEL POSITIONING RULES**:
- Labels MUST be offset from data lines (xytext minimum ±15 points)
- NO labels in X-axis zone
- End-of-line value labels REQUIRED
- Inline labels in CLEAR SPACE only

**BANNED PATTERNS**:
- ❌ Legend boxes (use inline labels)
- ❌ Vertical gridlines (horizontal only)
- ❌ Labels overlapping data lines
- ❌ Elements crossing zone boundaries

**QUALITY METRICS**:
- Zone integrity: 100%
- Label collision: 0
- Color compliance: 100%

---

## REVIEWS: Automated Quality Checks

### Self-Validation Loop (Pre-Return)

Every agent MUST validate its own output before returning:

```python
def validate_own_output(agent_output, agent_type):
    """
    Each agent validates its output before returning.
    Returns: (is_valid, issues_list)
    """
    if agent_type == "writer":
        issues = []
        
        # Check 1: Required front matter
        if not has_required_front_matter(agent_output):
            issues.append("CRITICAL: Missing required front matter fields")
        
        # Check 2: Chart embedding (if chart provided)
        if chart_filename and not chart_embedded(agent_output, chart_filename):
            issues.append("CRITICAL: Chart not embedded")
        
        # Check 3: Banned patterns
        banned = detect_banned_patterns(agent_output)
        if banned:
            issues.append(f"BANNED: {banned}")
        
        # Check 4: Verification flags
        if "[NEEDS SOURCE]" in agent_output or "[UNVERIFIED]" in agent_output:
            issues.append("CRITICAL: Verification flags present")
        
        return len(issues) == 0, issues
```

### Automatic Agent Review

After agent completes, a **Reviewer Agent** automatically checks:

```yaml
# Agent Review Workflow
1. Writer produces draft
2. Writer self-validates (catches 80% of issues)
3. If self-validation passes:
   - Reviewer Agent evaluates against standards
   - Reviewer provides scored feedback
4. If issues found:
   - Agent regenerates with fixes
   - Max 2 regeneration attempts
5. If still failing:
   - Flag for human review
   - Log to skills system
```

**Reviewer Agent Focus Areas**:
- **Completeness**: All required fields present?
- **Correctness**: Follows banned/required patterns?
- **Consistency**: Matches style guide?
- **Quality**: Meets metric thresholds?

---

## BLOCKS: Hard Quality Gates

### Pre-Commit Validation (Git Hook)

Before any content is committed:

```bash
#!/bin/bash
# .git/hooks/pre-commit (in blog repo)

# 1. Lint all articles
python3 ~/code/economist-agents/scripts/blog_qa_agent.py \
  --blog-dir . \
  --post _posts/*.md

# 2. Schema validation
python3 ~/code/economist-agents/scripts/schema_validator.py \
  --strict \
  --post _posts/*.md

# 3. Publication validator
python3 ~/code/economist-agents/scripts/publication_validator.py \
  --blog-dir .

if [ $? -ne 0 ]; then
    echo "❌ Quality checks failed. Commit blocked."
    exit 1
fi
```

### Schema Enforcement

**Front Matter Schema** (JSON Schema enforced):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["layout", "title", "date", "categories"],
  "properties": {
    "layout": {
      "type": "string",
      "enum": ["post", "page", "default"]
    },
    "title": {
      "type": "string",
      "minLength": 10,
      "pattern": "^(?!.*(Myth|Reality|Guide|Tips|Everything)).*"
    },
    "date": {
      "type": "string",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
    },
    "categories": {
      "type": "array",
      "minItems": 1,
      "maxItems": 3,
      "items": {
        "type": "string",
        "enum": ["quality-engineering", "test-automation", "performance", "ai-testing"]
      }
    }
  },
  "additionalProperties": true
}
```

### Output Complexity Limits

**Article Constraints** (Auto-reject if exceeded):
```yaml
max_word_count: 1500
min_word_count: 800
max_paragraphs_without_header: 4
max_consecutive_sentences: 5
max_readability_score: 10  # Hemingway scale
```

**Chart Constraints**:
```yaml
max_series: 3          # Too many lines = unreadable
min_data_points: 3     # Too few = not useful
max_title_length: 50   # Characters
required_elements:
  - red_bar
  - title
  - subtitle
  - source_line
```

---

## CONVENTIONS: Style and Patterns

### Standard Patterns (Always Use These)

**Opening Pattern**:
```
[Striking statistic]. [Contrasting observation/fact]. [Implication].

Example:
"Self-healing tests promise an 80% cut in maintenance costs. Only 10% of 
companies achieve it. The gap reveals a fundamental misunderstanding of 
what 'self-healing' means."
```

**Data Introduction Pattern**:
```
According to [Organization], [specific finding]. [Chart reference].

Example:
"According to Tricentis's 2024 survey, AI test generation adoption reached 
78% last year. As the chart shows, maintenance burden fell by only 18%."
```

**Ending Pattern**:
```
[Clear prediction or implication]. [Who wins/loses]. [Why it matters].

Example:
"Companies that invest in robust test infrastructure will outpace competitors. 
Those that chase AI magic bullets will bleed talent and ship slower. The 
choice is becoming binary."
```

### Anti-Patterns (Never Use These)

**Generic Naming**:
- ❌ `helper.py`, `utils.py`, `common.py`
- ✅ `front_matter_validator.py`, `chart_layout_calculator.py`

**Vague Functions**:
- ❌ `process_data()`, `handle_result()`, `do_work()`
- ✅ `validate_front_matter_schema()`, `embed_chart_in_article()`

**Magic Numbers**:
- ❌ `if score > 7:`
- ✅ `if score > QUALITY_GATE_THRESHOLD:`

---

## ENFORCEMENT: Quality Metrics

### Success Thresholds

**Agent Output Quality**:
```yaml
research_agent:
  verification_rate: ≥ 90%
  named_sources: 100%
  chart_completeness: 100%

writer_agent:
  front_matter_complete: 100%
  banned_patterns: 0
  chart_embedding: 100% (if chart provided)
  verification_flags: 0

editor_agent:
  gates_passed: 5/5
  verification_cleanup: 100%

graphics_agent:
  zone_integrity: 100%
  label_collisions: 0
  visual_qa_pass: ≥ 95%
```

**Pipeline Quality**:
```yaml
self_validation_catch_rate: ≥ 80%    # Issues caught before review
automated_review_catch_rate: ≥ 95%   # Issues caught before human
human_review_rejection_rate: ≤ 5%    # Issues reaching human
```

### Continuous Improvement

**Skills Learning** (Automated):
```python
# When validation fails, learn the pattern
if validation_failure:
    skills_manager.learn_pattern(
        category=agent_type,
        pattern_id=generate_pattern_id(failure),
        pattern_data={
            "severity": classify_severity(failure),
            "pattern": extract_pattern(failure),
            "check": generate_check_code(failure),
            "learned_from": f"Issue #{issue_number}"
        }
    )
```

**Prompt Strengthening** (Quarterly):
- Review all learned patterns
- Identify top 10 recurring issues
- Update agent prompts with explicit rules
- Regenerate test content to verify improvements

---

## TESTING: Validation of Validators

### Test Coverage Requirements

Every validator MUST have:
```yaml
unit_tests:
  - Happy path (valid input)
  - Each rejection case (invalid inputs)
  - Edge cases (boundary conditions)
  - Malformed input handling

integration_tests:
  - Full agent pipeline
  - Self-validation loops
  - Review workflows
  - Schema enforcement

coverage_threshold: 90%  # Minimum
```

### Validator Self-Checks

**Meta-validation**: Validators validate their own output

```python
def test_publication_validator_completeness():
    """Ensure validator checks all required fields"""
    required_checks = [
        'verification_flags',
        'yaml_format',
        'date_matching',
        'generic_titles',
        'placeholder_text',
        'missing_layout',
        'orphaned_charts',
        'missing_categories'  # NEW from Issue #15
    ]
    
    validator = PublicationValidator()
    actual_checks = validator.get_check_names()
    
    assert set(required_checks).issubset(set(actual_checks)), \
        f"Missing checks: {set(required_checks) - set(actual_checks)}"
```

---

## DOCUMENTATION: Living Standards

These standards are **living documents**:

1. **Every Bug = New Rule**: When a bug reaches production, add a rule to prevent it
2. **Quarterly Review**: Update prompts with top 10 learned patterns
3. **Version Control**: All changes tracked in git with rationale
4. **Audit Trail**: Link each rule to the issue/bug that created it

**Update Process**:
```bash
# When adding new standard
git commit -m "Add rule: Chart embedding mandatory (from Issue #16)"

# When strengthening existing rule
git commit -m "Strengthen: Front matter validation (caught Issue #15 pattern)"
```

---

## REFERENCES

- **Inspiration**: [Code Quality Foundations for AI-assisted Codebases](https://medium.com/nick-tune-tech-strategy-blog/code-quality-foundations-for-ai-assisted-codebases-4880f5948394) by Nick Tune
- **Implementation**: [QUALITY_IMPROVEMENT_PLAN.md](../QUALITY_IMPROVEMENT_PLAN.md)
- **Skills System**: [SKILLS_LEARNING.md](SKILLS_LEARNING.md)
- **Change Log**: [CHANGELOG.md](CHANGELOG.md) - See 2026-01-01 session

---

**Last Updated**: 2026-01-01  
**Version**: 1.0  
**Status**: Active - Enforced via automated reviews and git hooks
