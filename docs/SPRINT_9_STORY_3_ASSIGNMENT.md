# Sprint 9 Story 3: Measure PO Agent Effectiveness

**Status**: ASSIGNED to @refactor-specialist  
**Priority**: P0  
**Story Points**: 2  
**Started**: 2026-01-03  
**Parallel Execution**: YES (independent of CI fixes)

---

## Objective

Validate PO Agent meets >90% AC acceptance rate target by measuring real-world effectiveness with diverse user requests.

**Success Criteria**:
- [x] Story assigned and work begun
- [ ] 10 diverse user requests generated
- [ ] PO Agent run for each request  
- [ ] Acceptance criteria reviewed for quality
- [ ] Acceptance rate calculated
- [ ] Results documented with recommendations

---

## Task Breakdown

### Task 1: Generate 10 Diverse User Requests (30 min)

**Description**: Create realistic user requests spanning different complexity levels and domains

**Acceptance Criteria**:
- Requests cover LOW, MEDIUM, HIGH complexity
- Mix of feature requests, bug fixes, enhancements
- Different domains: content generation, quality, infrastructure, testing
- Each request 1-3 sentences

**Example Requests**:
```
LOW:    "Add a 'last updated' timestamp to article metadata"
MEDIUM: "Implement retry logic for failed LLM API calls"
HIGH:   "Create automated test suite for agent coordination"
```

**Deliverable**: `skills/po_agent_test_requests.json`

---

### Task 2: Run PO Agent for Each Request (45 min)

**Description**: Execute PO Agent against all 10 test requests and capture outputs

**Command**:
```bash
# For each request
python3 scripts/po_agent.py --request "USER_REQUEST_TEXT" --backlog skills/po_agent_test_backlog.json
```

**Acceptance Criteria**:
- All 10 requests processed successfully
- Generated stories captured to `skills/po_agent_test_backlog.json`
- No errors or crashes during execution
- Stories include: user_story, acceptance_criteria, story_points

**Deliverable**: `skills/po_agent_test_backlog.json` with 10 stories

---

### Task 3: Review Acceptance Criteria Quality (45 min)

**Description**: Manual quality review of generated AC against PO Agent standards

**Review Checklist** (for EACH story):

**Format Validation**:
- [ ] Uses Given/When/Then format consistently
- [ ] Each AC is independently testable
- [ ] Clear, unambiguous language
- [ ] No vague terms ("should", "properly", "correctly")

**Completeness Validation**:
- [ ] 3-7 AC per story (appropriate coverage)
- [ ] Happy path covered
- [ ] Edge cases identified
- [ ] Error handling addressed
- [ ] Quality requirements specified (performance, security, etc.)

**Testability Validation**:
- [ ] Can be automated as test cases
- [ ] Observable outcomes defined
- [ ] Success criteria measurable
- [ ] No interpretation needed

**Acceptance Decision**:
- **ACCEPT**: Meets all criteria, ready for implementation
- **MINOR ISSUES**: Acceptable with minor refinement
- **REJECT**: Major flaws, needs rework

**Scoring**:
- ACCEPT = 1.0 (full credit)
- MINOR ISSUES = 0.75 (partial credit)
- REJECT = 0.0 (no credit)

**Deliverable**: `skills/po_agent_test_review.json` with per-story scores

---

### Task 4: Calculate Acceptance Rate (15 min)

**Description**: Compute acceptance rate from review scores

**Formula**:
```
Acceptance Rate = (Sum of Scores / Total Stories) × 100%

Example:
8 ACCEPT (8.0) + 1 MINOR (0.75) + 1 REJECT (0.0) = 8.75 / 10 = 87.5%
```

**Acceptance Criteria**:
- Acceptance rate calculated accurately
- Breakdown by score type (ACCEPT, MINOR, REJECT)
- Statistical confidence noted (n=10 is small sample)
- Comparison to >90% target

**Deliverable**: Acceptance rate metric in report

---

### Task 5: Document Results (30 min)

**Description**: Comprehensive report with findings and recommendations

**Report Structure** (`docs/SPRINT_9_STORY_3_COMPLETE.md`):

```markdown
# Sprint 9 Story 3: PO Agent Effectiveness Measurement

## Executive Summary
- **Acceptance Rate**: X.X% (target: >90%)
- **Sample Size**: 10 stories
- **Result**: PASS/FAIL (meets target?)

## Test Requests
[Table of 10 requests with complexity levels]

## Generated Stories
[Summary of each story with AC count, story points]

## Quality Review
[Detailed findings per story]
- Story 1: ACCEPT - Well-formed Given/When/Then...
- Story 2: MINOR - Edge cases need refinement...
- Story 3: REJECT - Vague success criteria...

## Acceptance Rate Calculation
- ACCEPT: N stories (N × 1.0 = X.X)
- MINOR: N stories (N × 0.75 = X.X)
- REJECT: N stories (N × 0.0 = 0.0)
- **Total**: X.X / 10 = XX.X%

## Root Cause Analysis (if <90%)
[Why did stories fail? Prompt issues? Edge case handling?]

## Recommendations
[Actionable improvements for Sprint 10]

## Sprint 9 Story 3 Status
- [x] All tasks complete
- [x] Acceptance rate measured
- [x] Documentation complete
- [ ] Sprint 9 progress updated (30% → 50%)
```

**Deliverable**: `docs/SPRINT_9_STORY_3_COMPLETE.md`

---

## Test Data Schema

### po_agent_test_requests.json
```json
{
  "test_date": "2026-01-03",
  "requests": [
    {
      "id": 1,
      "complexity": "LOW",
      "domain": "content",
      "text": "Add a 'last updated' timestamp to article metadata"
    }
  ]
}
```

### po_agent_test_backlog.json
```json
{
  "stories": [
    {
      "request_id": 1,
      "user_story": "As a...",
      "acceptance_criteria": ["Given...", "When...", "Then..."],
      "story_points": 2,
      "priority": "P1"
    }
  ]
}
```

### po_agent_test_review.json
```json
{
  "review_date": "2026-01-03",
  "reviews": [
    {
      "story_id": 1,
      "format_validation": true,
      "completeness_validation": true,
      "testability_validation": true,
      "decision": "ACCEPT",
      "score": 1.0,
      "notes": "Well-formed AC with clear success criteria"
    }
  ],
  "summary": {
    "total_stories": 10,
    "accept_count": 8,
    "minor_count": 1,
    "reject_count": 1,
    "acceptance_rate": 87.5
  }
}
```

---

## Definition of Done

**Story 3 is COMPLETE when**:
- [x] Assignment created and work started
- [ ] 10 test requests generated (`skills/po_agent_test_requests.json`)
- [ ] PO Agent executed for all requests (`skills/po_agent_test_backlog.json`)
- [ ] Quality review completed (`skills/po_agent_test_review.json`)
- [ ] Acceptance rate calculated and documented
- [ ] Comprehensive report created (`docs/SPRINT_9_STORY_3_COMPLETE.md`)
- [ ] Results show >90% acceptance OR clear recommendations for improvement
- [ ] Sprint 9 progress updated (30% → 50%)
- [ ] CHANGELOG.md updated with Story 3 completion

---

## Quality Gates

**Gate 1: Test Request Quality**
- Requests span LOW/MEDIUM/HIGH complexity
- Realistic user scenarios
- No trivial or duplicate requests

**Gate 2: PO Agent Execution**
- All 10 requests processed without errors
- Generated stories have required fields
- Story points within reasonable range (1-8)

**Gate 3: Review Rigor**
- Manual review uses defined checklist
- Scoring consistent across stories
- Clear justification for REJECT decisions

**Gate 4: Statistical Validity**
- Sample size (n=10) noted as limitation
- Confidence interval acknowledged
- Recommendation for larger sample in Sprint 10 if needed

---

## Integration with Sprint 9

**Parallel Execution Strategy**:
- **Story 1**: Editor Agent fixes (pending CI resolution)
- **Story 2**: CI/CD infrastructure (@quality-enforcer, active)
- **Story 3**: PO Agent measurement (@refactor-specialist, START NOW)

**Why Parallel**:
- Story 3 independent of CI status
- No dependencies on Editor Agent or infrastructure
- Uses po_agent.py directly (tested in Sprint 8)
- Can deliver value while CI being fixed

**Progress Tracking**:
- Sprint 9 capacity: 15 points
- Current: Story 0 complete (2 pts) = 13% complete
- After Story 3: 2+2 = 4 pts = 27% complete
- Target EOD Day 2: 40% (6 pts)

---

## Risk Mitigation

**Risk 1: PO Agent not installed/configured**
- Mitigation: Test with single request first
- Fallback: Use Sprint 8 PO Agent examples if needed

**Risk 2: Acceptance rate <90%**
- Expected: First measurement may reveal issues
- Mitigation: Clear recommendations for improvement
- Sprint 10: Implement fixes, remeasure

**Risk 3: Manual review subjectivity**
- Mitigation: Use explicit checklist, document reasoning
- Future: Automated AC quality scoring

---

## Commands Reference

```bash
# Test PO Agent availability
python3 scripts/po_agent.py --help

# Generate story from request
python3 scripts/po_agent.py --request "Add timestamp to articles" \
  --backlog skills/po_agent_test_backlog.json

# View generated backlog
cat skills/po_agent_test_backlog.json | jq .

# Run all 10 requests (automated)
for req in $(jq -r '.requests[].text' skills/po_agent_test_requests.json); do
  python3 scripts/po_agent.py --request "$req" --backlog skills/po_agent_test_backlog.json
done
```

---

## Assigned To

**Agent**: @refactor-specialist  
**Chat**: Chat 3 (parallel execution)  
**Start Time**: 2026-01-03 (Day 2, immediately)  
**Expected Duration**: 2.5 hours (2 story points × 2.8h/pt = 5.6h, but measurement work is faster)  
**Status**: ASSIGNED, ready to begin

---

## Context for @refactor-specialist

**What You Need to Know**:
1. **Sprint 8 Context**: PO Agent created and tested (9/9 test cases passing)
2. **Sprint 9 Goal**: Validate autonomous orchestration agents meet quality targets
3. **This Story**: Measure PO Agent effectiveness independently of CI issues
4. **Your Role**: Execute measurement, review quality, report findings objectively

**Sprint 8 PO Agent Results** (baseline):
- Created in Story 1 (3/3 points delivered)
- Test coverage: 9/9 passing
- Capabilities: Story generation, AC generation, estimation, escalation
- **Gap**: Live validation with human PO deferred to Sprint 9 (this story)

**What Success Looks Like**:
- Objective measurement (no bias toward "passing")
- Clear evidence for >90% target (or documented why not)
- Actionable recommendations if improvements needed
- Foundation for Sprint 10 enhancements

**You Have Full Autonomy To**:
- Design test requests (representative scenarios)
- Score AC quality (use checklist rigorously)
- Recommend improvements (even if rate is high)
- Flag concerns (edge cases, limitations)

---

## Questions for @scrum-master

**Before Starting**:
- [ ] Do I have access to po_agent.py? (test with --help)
- [ ] Should I use Sprint 8 backlog or create new test backlog?
- [ ] Any specific user request types to prioritize?

**During Execution**:
- If PO Agent fails on a request, do I:
  * Count as REJECT? (penalize agent)
  * Exclude from sample? (measure only successful runs)
  * Document as escalation? (flag for investigation)

**Reporting**:
- If acceptance rate is 85-89% (close but below target), do I:
  * Mark story as FAIL? (strict interpretation)
  * Mark as PARTIAL? (acknowledge near-miss)
  * Recommend immediate iteration? (Sprint 9 Story 4?)

---

## Start Here

```bash
# Step 1: Verify PO Agent availability
cd /Users/ouray.viney/code/economist-agents
source .venv/bin/activate
python3 scripts/po_agent.py --help

# Step 2: Create test requests file
# See Task 1 for schema and examples

# Step 3: Run first test request (validation)
python3 scripts/po_agent.py --request "Add timestamp to articles" \
  --backlog skills/po_agent_test_backlog.json

# Step 4: Review generated story
cat skills/po_agent_test_backlog.json | jq '.stories[-1]'

# Step 5: If successful, proceed with full test suite
# See Task 2 for automation commands
```

**Ready to Begin**: YES ✅  
**Blockers**: NONE (independent work)  
**Estimated Completion**: EOD Day 2 (2026-01-03)

---

**Assignment Created**: 2026-01-03  
**Created By**: @scrum-master  
**Sprint**: Sprint 9 Day 2  
**Last Updated**: 2026-01-03
