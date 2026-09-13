# Agent Quality Gates

Quality gates define the minimum standards each agent must meet before output is accepted.

## Purpose

- **Prevent Low-Quality Outputs**: Block outputs that don't meet standards
- **Measure First-Time-Right Rate**: Track how often agents pass on first try
- **Identify Problem Agents**: Agents with low pass rates need improvement
- **Optimize Token Efficiency**: Reduce rework and regeneration costs

## Quality Gate Definitions

### Research Agent

**Gate 1: Verification Rate**
- **Threshold**: ≥80% of data points must be verified
- **Check**: `verified / total_data_points >= 0.8`
- **Failure**: Unverified claims present, sources missing

**Gate 2: Source Attribution**
- **Threshold**: Every statistic must have named source
- **Check**: No `[UNVERIFIED]` or `[NEEDS SOURCE]` flags
- **Failure**: Unsourced claims in output

**Gate 3: Data Quality**
- **Threshold**: Structured JSON output present
- **Check**: `chart_data` or `data_points` field exists
- **Failure**: No quantitative data for article

**Quality Score Formula**:
```python
quality_score = verification_rate if all_gates_pass else verification_rate * 0.5
```

---

### Writer Agent

**Gate 1: Style Compliance**
- **Threshold**: Zero banned phrases
- **Check**: `banned_phrases == 0`
- **Failure**: Contains "game-changer", "paradigm shift", "leverage" (verb), etc.

**Gate 2: Chart Embedding**
- **Threshold**: Chart markdown present if chart_data provided
- **Check**: `chart_embedded == True`
- **Failure**: Chart generated but not referenced in article

**Gate 3: British Spelling**
- **Threshold**: No American spellings (organisation, favour, analyse)
- **Check**: Scan for American variants
- **Failure**: Found "organization", "favor", "analyze"

**Gate 4: Validation Pass**
- **Threshold**: Self-validation or Publication Validator passes
- **Check**: `validation_passed == True`
- **Failure**: Critical issues detected (banned openings, missing sources, etc.)

**Quality Score Formula**:
```python
quality_score = 100
if banned_phrases > 0:
    quality_score -= (banned_phrases * 10)
if not chart_embedded:
    quality_score -= 20
if not validation_passed:
    quality_score -= 30
quality_score = max(0, quality_score)
```

---

### Graphics Agent

**Gate 1: Visual QA Pass**
- **Threshold**: All zone integrity checks pass
- **Check**: `visual_qa_passed == True`
- **Failure**: Zone violations, overlapping elements

**Gate 2: Zone Violations**
- **Threshold**: Zero zone violations
- **Check**: `zone_violations == 0`
- **Failure**: Title/red bar overlap, labels in X-axis zone, etc.

**Gate 3: Style Compliance**
- **Threshold**: Economist colors and fonts correct
- **Check**: Red bar (#e3120b), background (#f1f0e9), navy (#17648d)
- **Failure**: Wrong colors or missing red bar

**Quality Score Formula**:
```python
quality_score = 100 if visual_qa_passed else 0
if zone_violations > 0:
    quality_score -= (zone_violations * 15)
quality_score = max(0, quality_score)
```

---

### Editor Agent

**Gate 1: Opening Check**
- **Threshold**: No banned openings
- **Check**: First 2 sentences don't contain "In today's world...", "It's no secret...", etc.
- **Failure**: Throat-clearing detected

**Gate 2: Evidence Check**
- **Threshold**: All statistics sourced
- **Check**: No `[NEEDS SOURCE]` flags remain
- **Failure**: Unsourced claims in final output

**Gate 3: Voice Check**
- **Threshold**: British spelling, active voice, no clichés
- **Check**: Zero banned phrases after editing
- **Failure**: Style violations persist

**Gate 4: Closing Check**
- **Threshold**: No summary endings
- **Check**: Last 2 paragraphs don't contain "In conclusion...", "remains to be seen...", etc.
- **Failure**: Weak ending detected

**Gate 5: Chart Integration Check**
- **Threshold**: Chart referenced naturally in text
- **Check**: Chart markdown present and mentioned in prose
- **Failure**: Chart embedded but not discussed

**Quality Score Formula**:
```python
quality_score = (gates_passed / 5) * 100
if quality_issues:
    quality_score -= (len(quality_issues) * 5)
quality_score = max(0, quality_score)
```

---

### Visual QA Agent

**Gate 1: Zone Integrity**
- **Threshold**: All zones separated (red bar, title, chart, x-axis, source)
- **Check**: No overlapping elements
- **Failure**: Elements crossing zone boundaries

**Gate 2: Label Positioning**
- **Threshold**: All labels in clear space, not on data lines
- **Check**: No label-to-label or label-to-line overlap
- **Failure**: Labels colliding with data

**Gate 3: Style Compliance**
- **Threshold**: Colors, fonts, gridlines match spec
- **Check**: Red bar present, horizontal gridlines only
- **Failure**: Vertical gridlines or wrong colors

**Quality Score Formula**:
```python
quality_score = 100 if all_gates_pass else 0
# Binary: either passes all checks or fails
```

---

## Implementation

### In Code

```python
# Example: Writer Agent quality gate check
def check_writer_quality_gates(output: dict) -> tuple[bool, float]:
    """
    Returns: (passed: bool, quality_score: float)
    """
    gates_passed = True
    quality_score = 100

    # Gate 1: Banned phrases
    if output['banned_phrases'] > 0:
        gates_passed = False
        quality_score -= (output['banned_phrases'] * 10)

    # Gate 2: Chart embedding
    if not output['chart_embedded']:
        gates_passed = False
        quality_score -= 20

    # Gate 3: Validation
    if not output['validation_passed']:
        gates_passed = False
        quality_score -= 30

    quality_score = max(0, quality_score)
    return (gates_passed, quality_score)
```

### In Metrics Tracking

```python
metrics.track_writer_agent(
    word_count=1200,
    banned_phrases=0,           # Gate 1
    validation_passed=True,     # Gate 4
    regenerations=0,
    chart_embedded=True,        # Gate 2
    token_usage=3000
)

# Automatically calculates:
# - quality_score
# - cost_per_quality_unit
# - validation_pass_rate (over time)
```

---

## Pass Rate Targets

**Acceptable Performance**:
- Research Agent: ≥90% verification rate, 100% pass rate
- Writer Agent: ≥80% clean drafts, ≤20% rework rate
- Graphics Agent: ≥90% visual QA pass, 0 violations
- Editor Agent: ≥80% gate pass rate (4/5 gates)
- Visual QA Agent: 100% (binary pass/fail)

**Warning Threshold**:
- Any agent below 70% pass rate needs investigation
- Rework rate >30% indicates prompt engineering issues
- Quality score trending downward over 5 runs requires intervention

**Critical Threshold**:
- Pass rate <50% = CRITICAL - agent must be reworked
- Cost per quality unit >2x baseline = token wastage unacceptable
- 3+ consecutive failures = escalate to engineering team

---

## Quality Score Impact on Cost

**Formula**:
```
Cost Per Quality Unit = (token_usage × (regenerations + 1)) / quality_score
```

**Example Scenarios**:

**Scenario 1: High Quality, First Try** ✅
- Token usage: 3000
- Regenerations: 0
- Quality score: 100
- Cost: 3000 / 100 = **30 tokens per quality unit**

**Scenario 2: Low Quality, Multiple Tries** ❌
- Token usage: 3000
- Regenerations: 2
- Quality score: 60 (validation failed)
- Cost: (3000 × 3) / 60 = **150 tokens per quality unit** (5x worse!)

**Scenario 3: Medium Quality, One Retry** ⚠️
- Token usage: 3000
- Regenerations: 1
- Quality score: 80 (chart not embedded)
- Cost: (3000 × 2) / 80 = **75 tokens per quality unit** (2.5x worse)

**Insight**: Low quality outputs dramatically increase cost due to rework. A single regeneration doubles token cost. Quality gates prevent expensive rework cycles.

---

## Alert Triggers

**Automated Alerts** (when these conditions met):

1. **Agent Pass Rate Alert**
   - Trigger: Pass rate drops below 70% over last 5 runs
   - Action: Review agent prompt, check for systematic issues

2. **Token Efficiency Alert**
   - Trigger: Cost per quality unit >2x baseline
   - Action: Investigate why regenerations increasing

3. **Quality Trend Alert**
   - Trigger: Quality score declining over 5 consecutive runs
   - Action: Check for prompt degradation or environment changes

4. **Rework Rate Alert**
   - Trigger: Rework rate >30% (Writer or Graphics agents)
   - Action: Enhance self-validation prompts

5. **Critical Failure Alert**
   - Trigger: 3 consecutive failures for any agent
   - Action: STOP - escalate to engineering, don't waste more tokens

---

## Dashboard Integration

Quality gates feed into agent performance dashboard:

```
AGENT PERFORMANCE DASHBOARD
═══════════════════════════════════════════════════════════════

Agent             | Runs | Pass Rate | Quality | Rework | Cost/Q
──────────────────|------|-----------|---------|--------|--------
Research Agent    |  10  |   90%     |  85/100 |   0%   |  35
Writer Agent      |  10  |   70%     |  78/100 |  30%   |  58 ⚠️
Graphics Agent    |  10  |   80%     |  75/100 |  20%   |  45
Editor Agent      |  10  |   90%     |  88/100 |   0%   |  32
Visual QA Agent   |  10  |  100%     | 100/100 |   0%   |  15

⚠️ ALERTS:
- Writer Agent below 75% pass rate (70%) - needs prompt review
- Writer Agent cost efficiency 58 tokens/quality (1.7x baseline)
```

---

## Continuous Improvement Process

1. **Track Metrics**: Every agent run records quality gates
2. **Identify Patterns**: Dashboard shows which agents struggle
3. **Root Cause Analysis**: Why is agent failing gates?
4. **Prompt Engineering**: Enhance prompts to address failures
5. **Validate Improvement**: Next runs should show better pass rates
6. **Iterate**: Repeat until all agents >80% pass rate

**Example**:
- Writer Agent passes only 70% of time
- Root cause: Chart embedding failures (Gate 2)
- Fix: Enhanced prompt with explicit embedding instructions
- Result: Pass rate improves to 90%, cost drops 30%

---

## Version History

**v1.0** (2026-01-01):
- Initial quality gates definition
- All 5 agent types covered
- Quality score formulas documented
- Cost efficiency calculations added
- Alert thresholds defined

**Maintained By**: Quality Engineering Team
**Review Frequency**: After every 10 agent runs
**Update Trigger**: New gate failures discovered, baseline shifts
