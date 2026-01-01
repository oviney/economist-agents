# Sprint 5 Plan - GitHub Integration & Quality Improvements

**Sprint Goal**: Fix GitHub workflow integration and improve agent accuracy  
**Duration**: 5 days (Jan 2-6, 2026)  
**Total Points**: 7 points (conservative after Sprint 4's 9-point stretch)  
**Team**: 1 developer + AI pair programming

---

## Sprint Context

### Sprint 4 Post-Mortem Findings

**What Went Wrong**:
1. ❌ **GitHub auto-close broken** - Issues #19, #14 not closed despite "Closes" in commit
2. ❌ **File not committed** - SPRINT_4_COMPLETE.md created but not added to git
3. ❌ **Process breakdown** - GitHub integration docs exist but weren't followed

**Root Causes**:
- Incorrect commit message syntax (keyword in bullets, not body)
- Manual git operations without validation
- No pre-commit hooks enforcing GitHub patterns

**Impact**:
- Sprint 4 completion falsely reported
- Technical debt created
- Trust in automation eroded

### Lessons Learned

1. **Documentation ≠ Execution** - Having GITHUB_SPRINT_INTEGRATION.md doesn't mean it's being followed
2. **Validation gaps** - Need automated checks, not just instructions
3. **AI agent limitations** - I (Copilot) didn't validate GitHub syntax before committing

---

## Sprint 5 Stories

### Story 1: Fix GitHub Auto-Close Integration (P0) - **1 point**

**Issue**: #21  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Restore GitHub auto-close functionality with validation

**Tasks**:
- [ ] Create pre-commit hook `.git/hooks/pre-commit`
- [ ] Validate commit message for: `Closes #\d+`, `Fixes #\d+`, `Resolves #\d+`
- [ ] Reject commits with invalid syntax
- [ ] Update copilot-instructions.md with GitHub patterns
- [ ] Test with dummy issue to verify auto-close works
- [ ] Document correct syntax in GITHUB_SPRINT_INTEGRATION.md

**Acceptance Criteria**:
- Pre-commit hook installed and working
- Test commit properly closes an issue
- Documentation updated
- No more manual issue closures needed

**Complexity**: Low - Well-defined problem with clear solution

---

### Story 2: Improve Writer Agent Accuracy (P1) - **3 points**

**Issue**: TBD (to be created)  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Reduce Writer Agent regenerations from 1 per article to 0

**Current State** (from metrics):
- Writer Agent: 66.7% clean draft rate
- Average regenerations: 1 per article
- Common issues: Missing categories field, word count

**Tasks**:
- [ ] Analyze writer_agent validation failures
- [ ] Update WRITER_AGENT_PROMPT to include categories field
- [ ] Adjust word count expectations (800 words too high?)
- [ ] Add self-validation for required YAML fields
- [ ] Test with 5 article generations
- [ ] Measure improvement in metrics

**Acceptance Criteria**:
- Writer Agent clean draft rate >80%
- Average regenerations <0.5
- Categories field always present
- Word count matches expectations

**Complexity**: Medium - Requires prompt tuning and testing

---

### Story 3: Improve Editor Agent Prediction Accuracy (P1) - **2 points**

**Issue**: TBD  
**Owner**: Dev team  
**Status**: Not started

**Goal**: Improve Editor Agent prediction accuracy from 33% to >60%

**Current State** (from metrics):
- Editor Agent prediction accuracy: 33.3%
- Prediction: "All gates pass (5/5)"
- Actual: 6/7 gates passed

**Tasks**:
- [ ] Review editor prompt for overly optimistic predictions
- [ ] Add realistic pass/fail criteria
- [ ] Align predictions with actual gate checks
- [ ] Test with 5 article generations
- [ ] Measure improvement in metrics

**Acceptance Criteria**:
- Editor prediction accuracy >60%
- Predictions align with reality
- No more "all gates pass" false positives

**Complexity**: Low-Medium - Prompt adjustment

---

### Story 4: Add Git Pre-Commit Validation (P2) - **1 point**

**Issue**: TBD  
**Owner**: Dev team  
**Status**: Not started (stretch goal)

**Goal**: Prevent common git mistakes

**Tasks**:
- [ ] Validate all modified files are staged
- [ ] Check for large files (>5MB)
- [ ] Ensure YAML front matter valid
- [ ] Run quality tests before commit
- [ ] Block commit if tests fail

**Acceptance Criteria**:
- Pre-commit hook validates all changes
- Large files rejected
- Invalid YAML rejected
- Tests must pass

**Complexity**: Low - Extend existing hook

---

## Sprint Metrics

### Velocity Target

```
Sprint 2: 8 points (100%) ✅
Sprint 3: 5 points (100%) ✅
Sprint 4: 9 points (100%) ✅ (but with quality issues)

Average: 7.3 points
Sprint 5 Target: 7 points (conservative)
```

**Rationale**: After Sprint 4's execution issues, taking conservative approach to rebuild trust in process.

### Quality Gates

**Must Pass**:
- ✅ All stories have acceptance criteria
- ✅ GitHub auto-close tested and working
- ✅ No manual issue closures
- ✅ All files committed before marking complete
- ✅ Metrics show improvement in agent performance

**Sprint Success Criteria**:
- 100% story completion (7/7 points)
- GitHub workflow fully automated
- Writer Agent >80% clean draft rate
- Editor Agent >60% prediction accuracy
- Zero "Closes #X" failures

---

## Risk Assessment

### High Risk

**Risk**: GitHub integration fix doesn't work  
**Mitigation**: Test immediately with dummy issue, iterate if needed  
**Contingency**: Manual closures with Issue #20 tracking the tech debt

### Medium Risk

**Risk**: Agent improvements don't show metrics gains  
**Mitigation**: Have fallback prompts ready, test incrementally  
**Contingency**: Revert changes, analyze failure, defer to Sprint 6

### Low Risk

**Risk**: Pre-commit hook breaks existing workflow  
**Mitigation**: Thoroughly test before enforcing  
**Contingency**: Disable hook, fix issues, re-enable

---

## Definition of Done

**For Each Story**:
- [ ] All acceptance criteria met
- [ ] Code committed with proper "Closes #X" syntax
- [ ] Tests passing (if applicable)
- [ ] Documentation updated
- [ ] Metrics collected (for agent stories)
- [ ] Issue auto-closed by GitHub ✅ **NEW REQUIREMENT**
- [ ] Retrospective notes added

**For Sprint**:
- [ ] All 7 points delivered
- [ ] Sprint retrospective completed
- [ ] Metrics dashboard shows improvements
- [ ] Zero manual issue closures
- [ ] Sprint 6 planned

---

## Daily Standup Questions

1. What did I complete yesterday?
2. What will I complete today?
3. Any blockers?
4. **NEW**: Did GitHub auto-close work on my last commit? ✅

---

## Sprint Backlog (Ranked by Priority)

**Sprint 5 (Committed - 7 pts)**:
1. Story 1: Fix GitHub Auto-Close (P0, 1 pt) - Issue #21
2. Story 2: Improve Writer Agent (P1, 3 pts)
3. Story 3: Improve Editor Agent (P1, 2 pts)
4. Story 4: Pre-Commit Validation (P2, 1 pt) - Stretch

**Next Sprint (Candidates)**:
5. Issue #10: Expand Skills Categories (P3, 2 pts)
6. Issue #9: Anti-Pattern Detection (P3, 3 pts)
7. Issue #12: CONTRIBUTING.md (P4, 1 pt)
8. Issue #8: Integration Tests (P3, 5 pts)

---

## Success Metrics

### Primary (Must Achieve)

- ✅ GitHub auto-close working (100% success rate)
- ✅ Writer Agent clean draft rate: >80%
- ✅ Editor Agent prediction accuracy: >60%
- ✅ All 7 story points delivered

### Secondary (Nice to Have)

- Pre-commit hook preventing common mistakes
- Improved documentation with learnings
- Sprint 6 backlog groomed and ready

---

## Communication Plan

**Daily**:
- Self-standup notes in SPRINT.md
- GitHub issue updates

**Mid-Sprint (Day 3)**:
- Progress check: 3-4 points complete?
- Risk assessment: Are we on track?
- Adjust scope if needed

**End of Sprint (Day 5)**:
- Sprint retrospective (SPRINT_5_RETROSPECTIVE.md)
- Metrics comparison
- Sprint 6 planning

---

## Process Improvements (Learned from Sprint 4)

1. **Validate GitHub Syntax Before Commit**
   - Pre-commit hook (Story 1)
   - Copilot AI validation (update instructions)

2. **Check Git Status After Every Operation**
   - Don't claim "committed" until `git status` is clean
   - Verify files are tracked: `git ls-files | grep <filename>`

3. **Test Auto-Close Immediately**
   - Create dummy issue: "Test: Sprint X auto-close"
   - Commit with: "Test commit\n\nCloses #X"
   - Verify issue closes before marking sprint complete

4. **Metrics-Driven Improvements**
   - Use agent_metrics.json to prioritize work
   - Set clear before/after targets
   - Measure improvement, not just feature completion

---

## References

- **Bug Report**: Issue #20 (GitHub integration broken)
- **Story**: Issue #21 (Fix auto-close)
- **Metrics**: skills/agent_metrics.json
- **Integration Docs**: docs/GITHUB_SPRINT_INTEGRATION.md
- **Sprint 4 Review**: docs/SPRINT_4_RETROSPECTIVE.md

---

**Sprint 5 Planning Complete**  
**Next Action**: Create Story 2 and 3 GitHub issues  
**Team Capacity**: 7 points over 5 days  
**Confidence**: Medium (rebuilding after Sprint 4 issues)

