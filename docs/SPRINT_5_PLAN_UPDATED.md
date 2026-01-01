# Sprint 5 Plan - UPDATED with Quality Metrics

**Sprint Goal**: Fix GitHub workflow + Improve agent accuracy + Add defect tracking  
**Duration**: 5 days (Jan 2-6, 2026)  
**Total Points**: 9 points (was 7, added defect tracking)  
**Team**: 1 developer + AI pair programming

---

## 🚨 Critical Update: Defect Tracking Added

**User Feedback**: "I don't see any defect or bug metrics. We also need to report on bugs leaked to production."

**Response**:
1. ✅ **Created** `scripts/defect_tracker.py` (immediate action)
2. ✅ **Tracked** 4 known bugs (BUG-015 to BUG-020)
3. ✅ **Calculated** Defect Escape Rate: **50%** (2/4 production bugs)
4. 📋 **Added** Story 5 (2 pts): Dashboard integration
5. 📋 **Backlog** Issue #24: Google Analytics integration (5 pts, Sprint 6+)

---

## Sprint Context

### Sprint 4 Post-Mortem Findings

**What Went Wrong**:
1. ❌ **GitHub auto-close broken** - Issues #19, #14 not closed despite "Closes" in commit
2. ❌ **File not committed** - SPRINT_4_COMPLETE.md created but not added to git
3. ❌ **Process breakdown** - GitHub integration docs exist but weren't followed
4. ❌ **No defect metrics** - Bugs tracked in issues but no escape rate visibility

**Root Causes**:
- Incorrect commit message syntax (keyword in bullets, not body)
- Manual git operations without validation
- No pre-commit hooks enforcing GitHub patterns
- **No systematic defect tracking** (metrics gap identified by user)

**Impact**:
- Sprint 4 completion falsely reported
- Technical debt created
- Trust in automation eroded
- **Defect escape rate unknown** (now revealed: 50%)

---

## Sprint 5 Stories (UPDATED)

### Story 1: Fix GitHub Auto-Close Integration (P0) - **1 point**

**Issue**: [#21](https://github.com/oviney/economist-agents/issues/21)  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Restore GitHub auto-close functionality with validation

**Tasks**:
- [ ] Create pre-commit hook `.git/hooks/pre-commit`
- [ ] Validate commit message for: `Closes #\d+`, `Fixes #\d+`, `Resolves #\d+`
- [ ] Reject commits with invalid syntax
- [ ] Update copilot-instructions.md with GitHub patterns
- [ ] Test with dummy issue (create, close via commit, verify on GitHub)
- [ ] Document correct syntax in GITHUB_SPRINT_INTEGRATION.md

**Acceptance Criteria**:
- ✅ Pre-commit hook blocks invalid "Closes" syntax
- ✅ Test issue auto-closes when commit pushed
- ✅ Documentation updated with examples
- ✅ This story's issue (#21) closes when story completes

**Risk**: Low - Clear requirements, straightforward implementation

---

### Story 2: Improve Writer Agent Accuracy (P1) - **3 points**

**Issue**: [#22](https://github.com/oviney/economist-agents/issues/22)  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Reduce regenerations and improve clean draft rate

**Current Metrics** (from agent_metrics.json):
- Clean draft rate: **66.7%** (2/3 runs)
- Regenerations: **1.0 avg**
- Common issues: Missing categories field, word count mismatches

**Target**:
- Clean draft rate: **>80%**
- Regenerations: **<0.5 avg**

**Tasks**:
- [ ] Analyze writer_agent.py validation failures from Sprint 4
- [ ] Update WRITER_AGENT_PROMPT:
  - Explicit requirement: `categories: [quality-engineering, testing]`
  - Adjust word count target (800 words too rigid?)
  - Add self-validation checklist before returning
- [ ] Add front matter schema validation before draft return
- [ ] Test with 5 article generations
- [ ] Measure metrics improvement

**Acceptance Criteria**:
- ✅ Writer Agent includes categories field in all drafts
- ✅ Clean draft rate >80% over 5 test runs
- ✅ Regenerations <0.5 avg over 5 test runs
- ✅ agent_metrics.json shows improvement

**Risk**: Medium - Prompt tuning is iterative, may need multiple attempts

---

### Story 3: Improve Editor Agent Prediction Accuracy (P1) - **2 points**

**Issue**: [#23](https://github.com/oviney/economist-agents/issues/23)  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Improve prediction accuracy from 33% to >60%

**Current Metrics**:
- Prediction: "All gates pass (5/5)"
- Actual: 6/7 gates passed
- **Accuracy**: 33% (predictions too optimistic)

**Target**:
- **Prediction accuracy >60%**

**Tasks**:
- [ ] Review editor_agent.py prompt for overly optimistic language
- [ ] Add realistic pass/fail criteria based on gate strictness
- [ ] Align predictions with actual gate check logic
- [ ] Test with 5 article generations
- [ ] Measure prediction accuracy

**Acceptance Criteria**:
- ✅ Editor Agent predictions align with actual gate results
- ✅ Prediction accuracy >60% over 5 test runs
- ✅ agent_metrics.json shows improvement
- ✅ No more "All gates pass" when gates fail

**Risk**: Medium - May reveal that gates are too strict, requiring gate tuning

---

### Story 4: Pre-Commit Validation (P2) - **1 point** [STRETCH GOAL]

**Issue**: TBD (create if time allows)  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Extend pre-commit hook with comprehensive checks

**Tasks**:
- [ ] Validate all modified files are staged (`git status`)
- [ ] Check for large files (>5MB)
- [ ] Ensure YAML front matter valid in markdown files
- [ ] Run quality tests before allowing commit
- [ ] Block commits with validation flags ([NEEDS SOURCE], [UNVERIFIED])

**Acceptance Criteria**:
- ✅ Hook catches common mistakes
- ✅ Blocks bad commits automatically
- ✅ Provides helpful error messages

**Risk**: Low - Optional enhancement, drop if time constrained

---

### Story 5: Add Defect Tracking to Dashboard (P1) - **2 points** [NEW]

**Issue**: [#25](https://github.com/oviney/economist-agents/issues/25)  
**Owner**: Dev team  
**Status**: Foundation complete, dashboard integration needed

**Goal**: Make defect metrics visible and actionable

**Current State**:
✅ **Foundation complete** (implemented during sprint planning):
- `scripts/defect_tracker.py` created (318 lines)
- 4 bugs tracked (BUG-015 to BUG-020)
- Defect escape rate calculated: **50%**
- Markdown report generation working

**Remaining Tasks**:
- [ ] Integrate defect_tracker with `metrics_dashboard.py`
- [ ] Display defect metrics:
  - Total bugs (by severity)
  - Defect escape rate (with trend)
  - Open bugs count
  - Mean time to fix
  - Bugs by component
- [ ] Add alert if escape rate > 20%
- [ ] Add CLI: `python3 scripts/defect_tracker.py --report`
- [ ] Update `agent_metrics.py` to track validation failures as potential bugs

**Acceptance Criteria**:
- ✅ Dashboard shows defect section
- ✅ Escape rate visible with target (<10%)
- ✅ Alert triggers if escape rate > 20%
- ✅ Report command generates markdown
- ✅ Pre-commit hook updates defect metrics

**Quality Targets**:
- Defect Escape Rate: **<10%** (industry standard)
- Current: **50%** (needs improvement)

**Risk**: Low - Foundation done, straightforward integration

---

## Quality Metrics Summary

### Current State (Baseline)

**Agent Performance**:
- Research Agent: 73% verification rate (target: >80%)
- Writer Agent: 67% clean draft rate (target: >80%)
- Editor Agent: 33% prediction accuracy (target: >60%)
- Graphics Agent: 83% visual QA pass (target: >90%)

**Defect Metrics** (NEW):
- Total bugs tracked: **4**
- Fixed bugs: **3** (75%)
- Production escapes: **2**
- **Defect Escape Rate: 50%** (target: <10%)

**Process Metrics**:
- GitHub auto-close success: **0%** (critical failure)
- Documentation completeness: **100%**
- Documentation compliance: **60%** (needs improvement)

### Sprint 5 Targets

**By End of Sprint**:
- GitHub auto-close: **100%** success (Story 1)
- Writer clean draft: **>80%** (Story 2)
- Editor predictions: **>60%** accuracy (Story 3)
- Defect visibility: **100%** (Story 5)
- Defect escape rate: **<10%** over next 10 bugs

---

## Sprint Backlog (Prioritized)

**Committed** (9 points):
1. Story 1: GitHub Auto-Close (P0, 1pt) - Issue #21
2. Story 2: Writer Agent (P1, 3pts) - Issue #22
3. Story 3: Editor Agent (P1, 2pts) - Issue #23
4. Story 5: Defect Dashboard (P1, 2pts) - Issue #25 [NEW]
5. Story 4: Pre-Commit (P2, 1pt) - Stretch goal

**Future Sprints**:
6. Story 6: Google Analytics Integration (P2, 5pts) - Issue #24 [NEW]
   - Track page views, engagement, bounce rate
   - Link content quality to user behavior
   - Close feedback loop
   - **Recommended**: Sprint 6 or 7

---

## Risk Assessment

### High Risk
- **Story 2 & 3**: Prompt tuning is iterative, may not hit targets in one sprint
  - **Mitigation**: Test frequently, partial improvement acceptable

### Medium Risk
- **Story 5**: Dashboard integration may reveal UI/UX issues
  - **Mitigation**: Foundation solid, focus on simple display first

### Low Risk
- **Story 1**: Clear requirements, straightforward implementation
- **Story 4**: Optional, can be deferred without impact

### New Risk: Scope Creep
- Added 2 points (Story 5) mid-planning
- **Mitigation**: Story 5 foundation done, only integration remains
- **Contingency**: Drop Story 4 if needed

---

## Definition of Done (UPDATED)

For each story:
- ✅ Code implemented and tested
- ✅ Tests pass (manual or automated)
- ✅ Documentation updated
- ✅ Commit uses correct "Closes #X" syntax (NEW)
- ✅ **Issue auto-closed by GitHub** (CRITICAL TEST) (NEW)
- ✅ Metrics collected (if applicable) (NEW)
- ✅ **Defect tracker updated** (if bug fix) (NEW)
- ✅ Sprint report links to artifacts

For Sprint 5 overall:
- ✅ All committed stories complete
- ✅ GitHub auto-close working (100% success rate)
- ✅ Agent metrics show improvement
- ✅ **Defect metrics visible in dashboard** (NEW)
- ✅ Zero production escapes during sprint
- ✅ Sprint retrospective published

---

## Daily Standup Questions (UPDATED)

1. What did I complete yesterday?
2. What will I work on today?
3. Any blockers?
4. **Did GitHub auto-close work for yesterday's commits?** (NEW)
5. **Any bugs discovered? Logged in defect_tracker?** (NEW)
6. Are metrics improving? (check agent_metrics.json)

---

## Success Metrics

**Sprint 5 will be successful if**:
- ✅ GitHub auto-close: 100% success rate (Story 1)
- ✅ Writer Agent: >80% clean draft rate (Story 2)
- ✅ Editor Agent: >60% prediction accuracy (Story 3)
- ✅ Defect metrics: Visible in dashboard (Story 5)
- ✅ Zero manual issue closures needed
- ✅ All story issues auto-closed by commits
- ✅ **Defect escape rate trending toward <10%** (NEW)

**Stretch goals**:
- ✅ Pre-commit validation complete (Story 4)
- ✅ All 9 points delivered

---

## Velocity Tracking

```
Sprint 2: 8 points ✅
Sprint 3: 5 points ✅
Sprint 4: 9 points ✅ (with issues)

Sprint 5: 9 points (target)
  - 7 original points
  - 2 added for defect tracking (foundation done)
```

**Justification for 9 points**:
- Story 5 foundation already complete (defect_tracker.py)
- Only dashboard integration remains (simpler than net-new)
- Conservative on other stories (3+2+1 = 6 points)
- Total: 6 core + 2 integration + 1 stretch = 9

---

## Process Improvements

Based on Sprint 4 post-mortem:

1. **Validate before claiming done**
   - Check GitHub to confirm issue closed
   - Don't say "complete" until verified on GitHub

2. **Test immediately**
   - Create dummy issues to test auto-close
   - Don't wait until end of sprint

3. **Use pre-commit hooks**
   - Enforce patterns automatically
   - Reduce human error

4. **Metrics-driven**
   - Use agent_metrics.json to prioritize work
   - Use defect_tracker.json to measure quality
   - Track trends, not just point-in-time

5. **Document bugs systematically**
   - Log every bug in defect_tracker
   - Track discovery stage (dev vs production)
   - Calculate escape rate

---

## Sprint 5 Schedule

**Day 1 (Jan 2)**:
- Morning: Story 1 (GitHub auto-close)
- Afternoon: Test auto-close, validate

**Day 2 (Jan 3)**:
- Morning: Story 2 (Writer Agent) - analysis & prompt updates
- Afternoon: Test Writer Agent (3 generations)

**Day 3 (Jan 4)**:
- Morning: Story 2 continued (if needed)
- Afternoon: Story 3 (Editor Agent) - prompt updates

**Day 4 (Jan 5)**:
- Morning: Story 3 continued + testing
- Afternoon: Story 5 (Defect Dashboard) - integration

**Day 5 (Jan 6)**:
- Morning: Story 4 (Stretch goal) or Story 5 polish
- Afternoon: Testing, metrics validation, retrospective

**Contingency**: Drop Story 4 if Stories 2-3 need extra time

---

## Backlog Updates

**New Issues Created**:
- [#24](https://github.com/oviney/economist-agents/issues/24): Google Analytics Integration (P2, 5pts) - Sprint 6+
- [#25](https://github.com/oviney/economist-agents/issues/25): Defect Dashboard Integration (P1, 2pts) - Sprint 5

**Sprint 6 Candidates** (preliminary):
- Issue #24: Google Analytics Integration (5 pts)
- Issue #10: Expand Skills Categories (3 pts)
- Issue #9: Anti-Pattern Detection (3 pts)
- Issue #12: CONTRIBUTING.md (1 pt)

---

## Communication Plan

**Sprint Start**: This document (SPRINT_5_PLAN.md)  
**Daily Updates**: Update SPRINT.md with progress  
**Sprint End**: SPRINT_5_RETROSPECTIVE.md with:
- Metrics comparison (before/after)
- Defect escape rate analysis
- Process improvements validation
- Sprint 6 recommendations

**Stakeholder Updates**:
- User feedback addressed: Defect tracking implemented ✅
- Google Analytics added to backlog ✅
- Quality visibility increased ✅

---

## Notes

**User Feedback Integration** (Jan 1, 2026):
> "I don't see any defect or bug metrics. We also need to report on bugs leaked to production. Also, what about end to end metrics like using the Google Analytics APIs?"

**Response Actions**:
1. ✅ **Immediate**: Created defect_tracker.py, tracked known bugs
2. ✅ **Sprint 5**: Added Story 5 (defect dashboard, 2pts)
3. ✅ **Backlog**: Created Issue #24 (Google Analytics, 5pts, P2)
4. ✅ **Quality Focus**: Defect escape rate now core metric

**Quality Philosophy Shift**:
- Before: Track agent performance only
- After: Track agent performance + bugs + user engagement
- Goal: Complete feedback loop from generation → quality → user impact

**Defect Escape Rate Targets**:
- Current: **50%** (2/4 bugs leaked to production)
- Sprint 5 target: Visibility + tracking
- Long-term target: **<10%** (industry standard)

---

**Sprint 5 Status**: Ready to begin  
**Updated**: January 1, 2026 (defect tracking added)  
**Next Review**: Day 3 (mid-sprint check)

