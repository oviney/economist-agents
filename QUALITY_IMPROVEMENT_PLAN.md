# Quality Improvement Plan - Post-Mortem Analysis

**Date**: 2026-01-01  
**Context**: Analysis of bugs found during production deployment

## Bugs Found Today

| Bug | Root Cause | Detection | Impact |
|-----|------------|-----------|--------|
| **#16**: Charts not embedded | Writer Agent lacked explicit embedding instruction | Manual review | HIGH - Invisible charts |
| **#17**: Duplicate chart display | Writer Agent added `image:` field unnecessarily | Manual review | MEDIUM - Visual duplication |
| **#15**: Missing category tag | Writer Agent didn't include `categories` in front matter | Manual review | MEDIUM - Navigation broken |

## Pattern Analysis

### 🔴 Critical Gap: No Self-Validation

**Problem**: Agents generate output but don't validate their own work.

**Evidence**:
- Writer Agent created articles without `categories` field (required by template)
- Writer Agent didn't embed charts even though chart_path was provided
- No agent checked "did I do what I was supposed to do?"

**Impact**: Multi-layer validation failures cascade to production

---

### 🔴 Critical Gap: Manual Bug Discovery

**Problem**: All three bugs found by human inspection, not automated tests.

**Evidence**:
- Chart embedding bug: Noticed article lacked chart
- Duplicate chart: Noticed during site review
- Missing category: Noticed during site review

**Impact**: Bugs reach production, require reactive fixes

---

### 🟠 Systemic Issue: Incomplete Validation Coverage

**Current State**:
```
Writer Agent → Publication Validator → Blog QA → Production
     ❌              ❌ (missed)         ❌           🔥
```

**Gaps**:
1. **Publication Validator** had no check for orphaned charts (added post-bug)
2. **Blog QA** didn't validate chart references (added post-bug)
3. **No front matter schema validation** - categories field not enforced
4. **No end-to-end testing** - full pipeline never tested

---

### 🟠 Systemic Issue: No Feedback Loop

**Problem**: Bugs found in production don't automatically improve agent prompts.

**Current Process**:
1. Bug found manually
2. Fix applied reactively
3. Agent prompt updated manually
4. No verification that fix prevents recurrence

**Missing**:
- Automated regression tests
- Prompt effectiveness tracking
- Production monitoring

---

## Proposed Improvements

### 1. Self-Validating Agents ⭐ (HIGH IMPACT)

**Concept**: Each agent validates its own output before returning.

**Implementation**:
```python
def run_writer_agent(client, topic, research_brief, chart_filename=None):
    # Generate article
    draft = call_llm(...)
    
    # SELF-VALIDATION
    validation_errors = []
    
    # Check 1: If chart_filename provided, verify it's embedded
    if chart_filename:
        if f"![" not in draft or chart_filename not in draft:
            validation_errors.append("CRITICAL: Chart not embedded")
    
    # Check 2: Front matter has required fields
    if not has_required_front_matter(draft, ['layout', 'title', 'date', 'categories']):
        validation_errors.append("CRITICAL: Missing required front matter")
    
    # If validation fails, regenerate with corrections
    if validation_errors:
        print("⚠️  Writer self-validation failed, regenerating...")
        draft = regenerate_with_fixes(client, draft, validation_errors)
    
    return draft
```

**Benefits**:
- Catches errors at source
- Reduces downstream validation burden
- Faster feedback loop

**Effort**: 1-2 days per agent

---

### 2. Front Matter Schema Validation ⭐ (HIGH IMPACT)

**Concept**: Enforce required front matter fields before publication.

**Implementation**:
```python
# In publication_validator.py

REQUIRED_FRONT_MATTER = {
    'layout': {'type': 'string', 'required': True},
    'title': {'type': 'string', 'required': True},
    'date': {'type': 'string', 'required': True, 'format': 'YYYY-MM-DD'},
    'categories': {'type': 'array', 'required': True, 'min_items': 1},
    'ai_assisted': {'type': 'boolean', 'required': True}
}

def validate_front_matter_schema(article_text):
    """Enforce complete front matter schema"""
    front_matter = extract_front_matter(article_text)
    
    errors = []
    for field, spec in REQUIRED_FRONT_MATTER.items():
        if spec['required'] and field not in front_matter:
            errors.append(f"Missing required field: {field}")
    
    return errors
```

**Benefits**:
- Prevents missing field bugs (like #15)
- Enforces consistency
- Self-documenting requirements

**Effort**: 2-3 hours

---

### 3. Chart Integration Testing ⭐ (HIGH IMPACT)

**Concept**: Automated tests for chart generation → embedding → validation flow.

**Implementation**:
```python
# tests/test_chart_integration.py

def test_chart_embedded_when_generated():
    """Ensure charts are always embedded if generated"""
    # Generate article with chart data
    research = {"chart_data": {"title": "Test Chart", ...}}
    article = run_writer_agent(client, "Test Topic", research, "test.png")
    
    # Verify chart is embedded
    assert "![" in article, "Chart not embedded"
    assert "test.png" in article, "Chart filename not in article"

def test_no_orphaned_charts():
    """Publication validator catches orphaned charts"""
    article_without_chart = "---\ntitle: Test\n---\nContent"
    chart_file = "test.png"
    
    # Create chart file
    Path(f"output/charts/{chart_file}").touch()
    
    # Should fail validation
    validator = PublicationValidator()
    valid, issues = validator.validate(article_without_chart)
    
    assert not valid
    assert any("orphaned" in str(i).lower() for i in issues)
```

**Benefits**:
- Catches integration bugs before production
- Documents expected behavior
- Enables confident refactoring

**Effort**: 1 day (Issue #6)

---

### 4. Production Monitoring & Auto-Detection 🎯 (MEDIUM IMPACT)

**Concept**: Detect quality issues in deployed articles automatically.

**Implementation**:
```python
# scripts/production_monitor.py

def scan_live_articles():
    """Check deployed articles for common issues"""
    blog_url = "https://www.viney.ca"
    issues_found = []
    
    for article_url in get_recent_articles(blog_url):
        html = fetch_article(article_url)
        
        # Check 1: Category tag displayed?
        if not has_category_tag(html):
            issues_found.append({
                'url': article_url,
                'issue': 'missing_category_tag',
                'severity': 'medium'
            })
        
        # Check 2: Chart images load?
        for chart_url in extract_chart_urls(html):
            if not image_exists(chart_url):
                issues_found.append({
                    'url': article_url,
                    'issue': 'broken_chart',
                    'severity': 'high'
                })
        
        # Check 3: Duplicate content?
        if has_duplicate_images(html):
            issues_found.append({
                'url': article_url,
                'issue': 'duplicate_chart',
                'severity': 'medium'
            })
    
    if issues_found:
        create_github_issues(issues_found)
        alert_team(issues_found)
```

**Benefits**:
- Proactive bug detection
- Continuous quality monitoring
- Automated issue filing

**Effort**: 1-2 days

---

### 5. Agent Prompt Effectiveness Tracking 📊 (MEDIUM IMPACT)

**Concept**: Measure which prompt changes actually improve quality.

**Implementation**:
```python
# In skills_manager.py - extend for agent prompts

class PromptEffectivenessTracker:
    def record_generation(self, agent_name, prompt_version, outcome):
        """Track success/failure of agent outputs"""
        self.metrics.append({
            'agent': agent_name,
            'prompt_version': prompt_version,
            'outcome': outcome,  # 'success' | 'validation_failed' | 'production_bug'
            'timestamp': datetime.now()
        })
    
    def get_effectiveness(self, agent_name, time_window='7d'):
        """Calculate success rate for agent"""
        recent = filter_by_time_window(self.metrics, time_window)
        agent_runs = [m for m in recent if m['agent'] == agent_name]
        
        if not agent_runs:
            return None
        
        success_rate = len([r for r in agent_runs if r['outcome'] == 'success']) / len(agent_runs)
        return {
            'agent': agent_name,
            'success_rate': success_rate,
            'total_runs': len(agent_runs),
            'common_failures': get_common_failures(agent_runs)
        }
```

**Benefits**:
- Data-driven prompt optimization
- Identify which agents need improvement
- Track improvement over time

**Effort**: 3-4 hours (Issue #7)

---

### 6. Visual Regression Testing 🎨 (MEDIUM IMPACT)

**Concept**: Automated screenshot comparison for charts.

**Implementation**:
```python
# tests/visual_regression/test_charts.py

def test_chart_layout_regression():
    """Ensure chart layouts don't regress"""
    chart_spec = {"title": "Test", "data": [...]}
    
    # Generate chart
    chart_path = run_graphics_agent(client, chart_spec, "test.png")
    
    # Compare to baseline
    baseline_path = "tests/fixtures/charts/baseline-chart.png"
    diff = compare_images(chart_path, baseline_path, threshold=0.95)
    
    assert diff < 0.05, f"Chart differs by {diff*100}%"
    
    # Visual QA validation
    qa_result = run_visual_qa_agent(client, chart_path)
    assert qa_result['overall_pass'], f"Visual QA failed: {qa_result['critical_issues']}"
```

**Benefits**:
- Prevents chart rendering regressions
- Automates visual QA
- Builds confidence in chart generation

**Effort**: 2-3 days (Issue #6)

---

### 7. Feedback Loop: Production → Agent Prompts 🔄 (HIGH IMPACT)

**Concept**: Automatically strengthen agent prompts based on production bugs.

**Implementation**:
```python
# scripts/prompt_strengthener.py

def learn_from_production_bug(bug_issue_number):
    """Extract lessons from GitHub issue and update agent prompts"""
    issue = fetch_github_issue(bug_issue_number)
    
    # Parse issue for agent failures
    affected_agent = identify_agent(issue)
    failure_pattern = extract_failure_pattern(issue)
    
    # Generate prompt enhancement
    enhancement = generate_prompt_fix(affected_agent, failure_pattern)
    
    # Create PR with prompt update
    create_prompt_update_pr(
        agent=affected_agent,
        enhancement=enhancement,
        references=f"Fixes #{bug_issue_number}"
    )
```

**Example**: After Issue #16 (charts not embedded)
```python
# Auto-generated prompt enhancement:
CHART_EMBEDDING_CHECK = """
CRITICAL: If chart_data was provided, you MUST:
1. Embed chart using markdown: ![Title](path)
2. Reference chart in text: "As the chart shows..."
3. Place chart after discussing the data

SELF-CHECK before finishing:
□ Chart markdown present?
□ Chart path matches provided filename?
□ Chart referenced in surrounding text?

If ANY checkbox is unchecked, regenerate with fixes.
"""
```

**Benefits**:
- Continuous prompt improvement
- Prevents bug recurrence
- Scales learning across agents

**Effort**: 2-3 days

---

## Implementation Priority

### Phase 1: Immediate (This Week)
1. ✅ **Front Matter Schema Validation** - 2-3 hours - Prevents #15 recurrence
2. ✅ **Chart Integration Tests** - 1 day - Prevents #16 recurrence
3. ✅ **Visual QA Metrics Tracking** (Issue #7) - 2-3 hours - Enables data-driven improvements

### Phase 2: Short-term (Next 2 Weeks)
4. **Self-Validating Writer Agent** - 1-2 days - Catches errors at source
5. **Production Monitor** - 1-2 days - Proactive bug detection
6. **Visual Regression Tests** (Issue #6) - 2-3 days - Automated chart QA

### Phase 3: Long-term (Next Month)
7. **Prompt Effectiveness Tracking** - 1 day - Measure prompt improvements
8. **Feedback Loop Automation** - 2-3 days - Continuous learning from bugs

---

## Success Metrics

**Quantitative Goals** (3-month horizon):
- Reduce production bugs from **3/week → 0.5/week** (83% reduction)
- Increase automated bug detection from **0% → 80%**
- Improve agent output quality from **manual fixes → self-correcting**
- Achieve **95%+ Visual QA pass rate**

**Qualitative Goals**:
- Zero manual bug hunting (proactive monitoring)
- Agents self-correct common mistakes
- Continuous improvement without human intervention
- Confident deployments (comprehensive test coverage)

---

## Architecture: Quality Gates

**Current**:
```
Writer → [Validator] → [Blog QA] → Production
         (reactive)    (reactive)      🔥
```

**Improved**:
```
Writer (self-validate) → [Validator++] → [Integration Tests] → [Visual QA] → Production Monitor
   ✅ Self-check           ✅ Schema         ✅ E2E             ✅ Charts      ✅ Continuous
```

**Key Principle**: **Shift quality left** - catch errors as early as possible, ideally at the agent that created them.

---

## Next Actions

1. **Today**: Implement Front Matter Schema Validation (2-3 hours)
2. **Tomorrow**: Add Chart Integration Tests (1 day)
3. **This Week**: Complete Issue #7 - Visual QA Metrics (2-3 hours)
4. **Next Week**: Implement Self-Validating Writer Agent (1-2 days)

---

## Appendix: Lessons Learned

### What Worked Well
- Multi-layer validation (caught some issues)
- GitHub issue tracking (audit trail)
- Skills-based learning system (Blog QA)
- Pre-commit hooks (Jekyll validation)

### What Needs Improvement
- Agent self-awareness (don't validate own work)
- Schema enforcement (required fields not validated)
- Test coverage (no integration tests)
- Production monitoring (manual bug discovery)
- Feedback loop (bugs don't strengthen prompts automatically)

### Key Insight
> "The best time to catch a bug is when the agent creates it. The second best time is before it reaches production. The worst time is after deployment."

All three of today's bugs could have been caught by agent self-validation.
