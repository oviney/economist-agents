# Story 1: Validate Quality System in Production - Test Plan

**Sprint**: 2
**Story Points**: 2
**Priority**: P0 (Must Do)
**Status**: In Progress

---

## Objective

Prove the quality system (self-validating agents, automated reviewers, publication validator) works end-to-end by generating a real article and observing validation behaviors.

---

## Test Strategy

### 1. Baseline Comparison
**Before quality system** (Issues #15-17):
- Articles published with missing fields (layout field)
- Charts generated but not embedded (#16)
- Duplicate chart displays (#17)
- Weak endings published ("In conclusion...")

**After quality system** (Expected):
- Self-validation catches issues before final output
- Regeneration fixes critical problems
- Publication validator blocks bad articles
- Quality gates enforce standards

### 2. Test Scenarios

#### Scenario A: Generate Article with Quality System
**Input**: Topic from content queue
**Expected**:
- Research agent validates output structure
- Writer agent self-validates against banned patterns
- Editor agent checks for weak endings
- Publication validator runs final gates

#### Scenario B: Observe Self-Validation Logs
**Expected**:
- See "🔍 Self-validating..." messages in output
- Issues detected and flagged
- Regeneration triggered for critical issues

#### Scenario C: Verify Quality Gates
**Expected**:
- Publication validator blocks articles with issues
- Articles quarantined if validation fails
- Clear feedback on what needs fixing

---

## Test Execution Plan

### Phase 1: Setup (5 min)
1. ✅ Validate sprint alignment with pre-work check
2. ✅ Review Story 1 tasks and acceptance criteria
3. ✅ Check API keys configured
4. ⏳ Set OUTPUT_DIR for test run
5. ⏳ Create test run directory

### Phase 2: Generate Test Article (15-20 min)
1. ⏳ Run economist_agent.py with test topic
2. ⏳ Capture all console output (self-validation logs)
3. ⏳ Observe agent behaviors:
   - Research agent output validation
   - Writer agent self-check
   - Editor agent quality gates
   - Publication validator final check
4. ⏳ Note any regenerations triggered

### Phase 3: Analysis (10-15 min)
1. ⏳ Review generated article for quality
2. ⏳ Check if self-validation caught issues
3. ⏳ Verify regeneration behavior
4. ⏳ Test publication validator manually if needed
5. ⏳ Compare against pre-quality-system baseline

### Phase 4: Documentation (10 min)
1. ⏳ Document self-validation effectiveness
2. ⏳ Record metrics (issues caught, regenerations)
3. ⏳ Compare to baseline (Issues #15-17)
4. ⏳ Update SPRINT.md with progress
5. ⏳ Create findings report

### Phase 5: Commit & Report (5 min)
1. ⏳ Commit findings
2. ⏳ Update sprint status
3. ⏳ Report results

**Total Estimated Time**: 45-55 minutes

---

## Acceptance Criteria Checklist

- [ ] Article generates without quality issues
- [ ] Self-validation catches at least 1 issue
- [ ] Regeneration fixes issue automatically
- [ ] Metrics collected for effectiveness

---

## Metrics to Collect

1. **Self-Validation Coverage**
   - Research agent: Validates output structure? (Y/N)
   - Writer agent: Checks banned patterns? (Y/N)
   - Editor agent: Detects weak endings? (Y/N)

2. **Issue Detection**
   - Number of issues flagged by self-validation
   - Types of issues (critical vs. warning)
   - Issues caught vs. missed

3. **Regeneration Effectiveness**
   - Regenerations triggered: Count
   - Issues fixed by regeneration: Count
   - Issues remaining after regeneration: Count

4. **Publication Validation**
   - Articles blocked by validator: Count
   - Validation checks passed: Count / Total
   - Quarantined articles: Count

5. **Baseline Comparison**
   - Issues #15-17 would be caught? (Y/N for each)
   - Improvement in article quality: Subjective assessment

---

## Success Criteria

**Minimum Success**:
- Article generates successfully
- At least 1 issue caught by self-validation
- Publication validator runs without errors

**Full Success**:
- All self-validation checks operational
- At least 1 regeneration triggered and fixes issue
- Final article passes all quality gates
- Clear evidence system prevents Issues #15-17 recurrence

---

## Risk Mitigation

**Risk 1**: API keys not configured
- Mitigation: Check .env file, use test mode if needed

**Risk 2**: Generation takes too long
- Mitigation: Use shorter topic, accept partial validation

**Risk 3**: Self-validation doesn't trigger
- Mitigation: Document findings, investigate why

---

## Test Environment

- **Date**: 2026-01-01
- **Output Directory**: `output/test-story-1/`
- **Topic Source**: Content queue or manual selection
- **Expected Runtime**: 5-10 minutes per article generation

---

**Status**: Ready to execute Phase 1 ✅
