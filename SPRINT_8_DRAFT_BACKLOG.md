# Sprint 8 Draft Backlog

**Generated**: 2026-01-02 (During Sprint 7 Story 3 execution)
**Planning Context**: Preparing for Sprint 8 while Sprint 7 research/implementation in progress
**Capacity**: 13-16 story points (consistent with Sprint 7 velocity)
**Sprint Duration**: 1 week (5 working days)
**Story Cap**: 3 points max per story (prevents 6+ hour marathons)

---

## Sprint 8 Goal (Proposed)

**Primary Focus**: Implement quality improvements from Sprint 7 diagnostics + high-value features from backlog

**Secondary Focus**: Close test gaps and enhance Writer Agent capabilities

**Success Criteria**:
- Sprint 7 diagnostic recommendations implemented
- FEATURE-001 deployed (references section)
- Test gaps reduced by 50%
- Zero defect escapes

---

## Sprint 8 Capacity Analysis

**Target Capacity**: 13-16 story points
- **Low estimate**: 13 points (conservative, accounts for unknowns)
- **High estimate**: 16 points (aggressive, assumes no blockers)
- **Recommended commit**: 14 points (balanced)

**Execution Model**: 2-3 parallel tracks
- **Track 1**: Writer Agent enhancements (FEATURE-001, diagnostic fixes)
- **Track 2**: Test gap closure (integration tests, Visual QA)
- **Track 3**: Quality infrastructure (metrics, validation)

**Story Size Distribution** (applying 3-point cap):
- P0 stories: 2-3 points each (critical path)
- P1 stories: 2-3 points each (important but flexible)
- P2 stories: 1-2 points each (nice-to-have, buffer)

---

## Backlog: High Priority (P0)

### Story 1: FEATURE-001 - Add References Section (2 pts, P0) ⭐

**Source**: `skills/feature_registry.json` (reclassified from BUG-024)
**GitHub Issue**: #40
**Component**: writer_agent
**Priority**: HIGH (credibility requirement)

**User Story**: As a reader, I need to see references and citations for article claims so that I can verify information and explore sources.

**Acceptance Criteria**:
- [x] All generated articles include 'References' section before closing
- [x] References formatted in Economist style (Author, 'Title', Publication, Date)
- [x] Minimum 3+ authoritative sources cited
- [x] Research Agent sources automatically included in references
- [x] Links to sources include proper anchor text (not 'click here')
- [x] Publication Validator blocks articles without references section

**Quality Requirements**:
- Content: Economist-style formatting, minimum 3 sources, authoritative sources preferred
- Accessibility: Descriptive anchor text, semantic list markup
- SEO: rel='nofollow' for external links (if policy requires)
- Maintainability: Validator tests, formatting guide in prompt

**Implementation Notes**:
- Enhance WRITER_AGENT_PROMPT with references section template
- Add Publication Validator check #8 for references presence
- Update Blog QA agent to validate reference formatting
- Create Economist-style reference formatting examples
- Research Agent already collects sources - format for output

**Estimated Time**: 4-5 hours (2 points)
- Prompt enhancement: 1 hour
- Validator check: 1 hour
- Blog QA updates: 1 hour
- Testing & validation: 1-2 hours

**Dependencies**: None (standalone work)

**Parallel Track**: Track 1 (Writer Agent)

---

### Story 2: Implement Sprint 7 Editor Diagnostic Recommendations (3 pts, P0)

**Source**: Sprint 7 Story 1 - Editor Agent Diagnostic Suite
**Context**: Editor Agent gate pass rate declined to 87.2% (target: 95%+)
**GitHub Issue**: TBD (create during planning)

**User Story**: As the system, I need the Editor Agent to restore 95%+ gate pass rate so that article quality remains consistently high.

**Acceptance Criteria**:
- [x] Editor Agent prompt strengthened with explicit validation checklist
- [x] Pass/fail output required for each quality gate
- [x] Pattern detection enhanced (remove [NEEDS SOURCE] flags explicitly)
- [x] Gate ambiguity eliminated (YES/NO indicators for boolean checks)
- [x] Validation: 10+ test articles show 95%+ gate pass rate
- [x] Metrics tracked: gate pass rate before/after improvements

**Implementation Options** (from diagnostic):
1. **Option 1** (RECOMMENDED): Strengthen Editor Agent Prompt
   - Effort: LOW (2-4 hours)
   - Impact: HIGH
   - Add explicit validation checklist with pass/fail criteria

2. **Option 2**: Deploy Pre-Editor Automated Validator
   - Effort: MEDIUM (4-6 hours)
   - Impact: HIGH
   - Shift-left validation before Editor Agent runs

3. **Option 3**: Decompose Editor into Multi-Agent Pipeline
   - Effort: HIGH (12-20 hours)
   - Impact: VERY HIGH (long-term)
   - StyleCheck → FactCheck → StructureCheck specialized agents

**Selected Approach**: Option 1 (best effort/impact ratio)

**Quality Requirements**:
- Performance: 95%+ gate pass rate (from 87.2%)
- Consistency: Zero ambiguous gate assessments
- Validation: Pattern detection effectiveness measured
- Testing: 10+ test articles for statistical significance

**Implementation Notes**:
- Enhance EDITOR_AGENT_PROMPT with explicit checklist
- Require PASS/FAIL output format for each gate
- Add examples of good/bad patterns
- Test with diverse article types
- Track gate pass rate improvements

**Estimated Time**: 6-8 hours (3 points)
- Prompt redesign: 2 hours
- Testing & validation: 2-3 hours
- Metrics collection: 1 hour
- Documentation: 1-2 hours

**Dependencies**: Sprint 7 Story 1 complete (diagnostic results available)

**Parallel Track**: Track 1 (Writer Agent - can run parallel with Story 1)

---

### Story 3: Close Integration Test Gap (3 pts, P0)

**Source**: Sprint 7 Story 2 - Test Gap Detection Automation
**Context**: Integration tests: 42.9% gap (3/7 bugs missed at this level)
**GitHub Issue**: TBD (create during planning)

**User Story**: As a developer, I need comprehensive integration tests so that agent coordination bugs are caught before deployment.

**Acceptance Criteria**:
- [x] Agent pipeline end-to-end tests implemented
  - Research → Writer → Editor → Validator flow
  - Chart generation → embedding → Visual QA flow
  - Governance gates and approval workflows
- [x] Test coverage for 3 historically-missed bugs:
  - BUG-016: Chart generated but not embedded
  - BUG-020: GitHub integration failures
  - BUG-015: Jekyll layout missing elements
- [x] Mock LLM responses for deterministic testing
- [x] CI/CD integration working
- [x] Test pass rate: 100% on fresh environments

**Quality Requirements**:
- Coverage: All agent-to-agent handoffs tested
- Reliability: Tests pass on fresh clone (no state dependencies)
- Performance: Full suite completes in <5 minutes
- Maintainability: Clear test names, comprehensive assertions

**Implementation Notes**:
- Create `tests/test_agent_integration.py`
- Mock Anthropic API calls with fixture responses
- Test happy path + error conditions
- Validate data flow between agents
- Test governance approval gates
- Ensure Jekyll layout validation

**Estimated Time**: 6-8 hours (3 points)
- Test framework setup: 2 hours
- Happy path tests: 2 hours
- Error condition tests: 2 hours
- CI/CD integration: 1 hour
- Documentation: 1 hour

**Dependencies**: Sprint 7 Story 2 complete (gap analysis results)

**Parallel Track**: Track 2 (Test Infrastructure)

---

## Backlog: Medium Priority (P1)

### Story 4: Enhance Visual QA Coverage (3 pts, P1)

**Source**: Sprint 7 Story 2 - Test Gap Detection Automation
**Context**: Visual QA: 28.6% gap (2/7 bugs missed, zone violations)
**GitHub Issue**: TBD (create during planning)

**User Story**: As a Graphics Agent, I need enhanced Visual QA so that 80% of chart layout bugs are caught before publication.

**Acceptance Criteria**:
- [x] Programmatic zone boundary validation (red bar, title, chart, x-axis, source)
- [x] Pixel-based validation for critical boundaries
- [x] Fail-fast errors for zone violations
- [x] Pre-LLM validation reduces Visual QA load
- [x] Historical bug patterns (BUG-008, others) prevented
- [x] Catch rate: 80%+ of known zone violation patterns

**Quality Requirements**:
- Performance: Zone validation <1 second per chart
- Accuracy: Zero false positives on valid charts
- Coverage: All 5 chart zones validated
- Integration: Works with existing Visual QA agent

**Implementation Notes**:
- Create `scripts/validate_chart_zones.py`
- Add programmatic boundary checks (y-coordinates)
- Integrate with run_graphics_agent()
- Add to quality gate before Visual QA
- Test against historical bug examples
- Validate with PIL/matplotlib inspection

**Estimated Time**: 6-8 hours (3 points)
- Zone validator: 2-3 hours
- Integration: 1-2 hours
- Testing: 2 hours
- Documentation: 1 hour

**Dependencies**: None (standalone work)

**Parallel Track**: Track 2 (Test Infrastructure)

---

### Story 5: Automate Manual Testing Scenarios (2 pts, P2)

**Source**: Sprint 7 Story 2 - Test Gap Detection Automation
**Context**: Manual tests: 28.6% gap (2/7 bugs missed)
**GitHub Issue**: TBD (create during planning)

**User Story**: As a QA engineer, I need automated tests for historically-manual scenarios so that I can eliminate 60% of manual testing burden.

**Acceptance Criteria**:
- [x] Badge accuracy validation automated (BUG-023 scenario)
- [x] README-metrics consistency checks
- [x] Jekyll layout rendering tests
- [x] Pre-commit hooks enforce validation
- [x] CI/CD runs all automated checks
- [x] Manual testing time reduced 60%

**Quality Requirements**:
- Reliability: Tests catch badge staleness before commit
- Speed: Validation completes in <30 seconds
- Coverage: All manual test scenarios automated
- Maintainability: Easy to add new scenarios

**Implementation Notes**:
- Enhance `scripts/validate_badges.py`
- Add README-quality_score consistency checks
- Create Jekyll layout validation tests
- Integrate into pre-commit hook
- Add to GitHub Actions workflow
- Document automated coverage

**Estimated Time**: 4-5 hours (2 points)
- Automation scripts: 2 hours
- Integration: 1 hour
- Testing: 1 hour
- Documentation: 0.5 hours

**Dependencies**: None (standalone work)

**Parallel Track**: Track 2 (Test Infrastructure)

---

## Backlog: Low Priority (P2)

### Story 6: Auto-Generate Prevention Rules from Test Gaps (2 pts, P2)

**Source**: Sprint 7 Story 2 - Test Gap Detection Automation (Recommendation #4)
**Context**: Test gap analysis identifies patterns, but rule generation is manual
**GitHub Issue**: TBD (create during planning)

**User Story**: As the defect prevention system, I need to auto-generate prevention rules from test gap patterns so that 70% of historically-missed bug patterns are prevented.

**Acceptance Criteria**:
- [x] Test gap analyzer suggests prevention rules automatically
- [x] Rules mapped to root cause + test gap combination
- [x] Auto-generate `defect_prevention_rules.py` entries
- [x] Validation: Rules catch 70%+ of historical patterns
- [x] Integration with existing prevention system
- [x] Documentation: rule generation logic explained

**Quality Requirements**:
- Accuracy: Generated rules have <10% false positive rate
- Coverage: 70%+ of test gap patterns covered
- Integration: Seamless with existing prevention system
- Maintainability: Clear rule generation logic

**Implementation Notes**:
- Enhance `scripts/test_gap_analyzer.py`
- Add rule generation logic (template-based)
- Map test gaps to prevention patterns
- Validate against historical bugs
- Integrate with defect_prevention_rules.py
- Test rule effectiveness

**Estimated Time**: 4-5 hours (2 points)
- Rule generation logic: 2 hours
- Validation: 1 hour
- Integration: 1 hour
- Documentation: 0.5 hours

**Dependencies**: Sprint 7 Story 2 complete

**Parallel Track**: Track 3 (Quality Infrastructure)

---

### Story 7: Sprint 7 Prevention Dashboard (2 pts, P2)

**Source**: Sprint 7 Story 3 (deferred due to insufficient data)
**Context**: Now have 7 bugs with RCA - sufficient for dashboard
**GitHub Issue**: TBD (create during planning)

**User Story**: As a quality engineer, I need a prevention effectiveness dashboard so that I can visualize which prevention strategies are most effective.

**Acceptance Criteria**:
- [x] Dashboard visualizes prevention strategy distribution
- [x] Shows prevention effectiveness by root cause
- [x] Tracks test gap closure over time
- [x] Prevention test coverage visualization
- [x] Trend analysis: prevention effectiveness improving?
- [x] Actionable insights surfaced

**Quality Requirements**:
- Usability: Dashboard loads in <2 seconds
- Accuracy: Metrics match defect_tracker.json
- Coverage: All prevention strategies visualized
- Maintainability: Auto-updates on new bug data

**Implementation Notes**:
- Create `scripts/generate_prevention_dashboard.py`
- Use matplotlib for visualizations
- Generate HTML dashboard with charts
- Integrate with quality_dashboard.py
- Add to CI/CD for automatic updates
- Test with historical bug data

**Estimated Time**: 4-5 hours (2 points)
- Dashboard generator: 2 hours
- Visualizations: 1 hour
- Integration: 1 hour
- Documentation: 0.5 hours

**Dependencies**: Sprint 7 Story 3 results (diagnostic data)

**Parallel Track**: Track 3 (Quality Infrastructure)

---

## Sprint 8 Capacity Allocation

### Recommended Commitment (14 points)

**Track 1: Writer Agent Enhancements** (5 points)
- Story 1: FEATURE-001 - References Section (2 pts, P0) ⭐
- Story 2: Editor Diagnostic Fixes (3 pts, P0)

**Track 2: Test Infrastructure** (6 points)
- Story 3: Integration Tests (3 pts, P0)
- Story 4: Visual QA Enhancement (3 pts, P1)

**Track 3: Quality Infrastructure (if capacity allows)** (3 points)
- Story 5: Automate Manual Tests (2 pts, P2)
- Story 7: Prevention Dashboard (2 pts, P2) - Pick one

**Buffer**: 2 points (Stories 6-7 are stretch goals)

### Conservative Commitment (13 points)

Drop Story 4 (Visual QA Enhancement) to 13 points.

### Aggressive Commitment (16 points)

Add Story 5 + Story 7 for 16 points total.

---

## Parallel Track Strategy

### Track 1: Writer Agent (Stories 1-2)
**Dependencies**: None (can start immediately)
**Lead**: Writer Agent specialist
**Duration**: 2-3 days
**Deliverables**:
- References section functional
- Editor Agent restored to 95%+ gate pass rate
- Validation metrics collected

### Track 2: Test Infrastructure (Stories 3-4-5)
**Dependencies**: Sprint 7 Story 2 complete
**Lead**: Test infrastructure specialist
**Duration**: 3-4 days
**Deliverables**:
- Integration test suite operational
- Visual QA zone validation working
- Manual test scenarios automated

### Track 3: Quality Infrastructure (Stories 6-7)
**Dependencies**: Sprint 7 complete, Track 2 progressing
**Lead**: Quality metrics specialist
**Duration**: 2 days
**Deliverables**:
- Prevention rule generation automated
- Prevention dashboard live

### Coordination Points
- **Day 1-2**: All tracks start independently
- **Day 3**: Mid-sprint checkpoint (are we on track?)
- **Day 4-5**: Integration testing (validate all pieces work together)
- **Day 5**: Sprint review prep

---

## Risks & Mitigation

### Risk 1: Editor Agent diagnostic fixes don't achieve 95% target
**Likelihood**: MEDIUM
**Impact**: HIGH (blocks quality improvement)
**Mitigation**:
- Start with Option 1 (prompt strengthening)
- If fails, pivot to Option 2 (pre-editor validator)
- Option 3 deferred to Sprint 9 if needed

### Risk 2: Integration test mocking complexity
**Likelihood**: MEDIUM
**Impact**: MEDIUM (delays Story 3)
**Mitigation**:
- Use simple fixture-based mocking
- Start with happy path, add error cases later
- Defer complex scenarios to Sprint 9

### Risk 3: Parallel tracks create integration issues
**Likelihood**: LOW (tracks are independent)
**Impact**: MEDIUM (delays integration)
**Mitigation**:
- Daily standup to coordinate
- Integration testing on Day 4-5
- Clear API contracts between components

### Risk 4: Insufficient time for Story 4-5 (P1/P2 stories)
**Likelihood**: MEDIUM
**Impact**: LOW (nice-to-have features)
**Mitigation**:
- P0 stories (1-3) take priority
- Defer P1/P2 to Sprint 9 if needed
- Buffer built into estimate (14/16 points committed)

---

## Success Criteria

### Must-Have (P0 Stories)
- [x] FEATURE-001 deployed (references section working)
- [x] Editor Agent restored to 95%+ gate pass rate
- [x] Integration test suite operational (100% pass rate)

### Should-Have (P1 Stories)
- [x] Visual QA zone validation working
- [x] Test gap closure: 50% improvement

### Nice-to-Have (P2 Stories)
- [x] Manual test automation: 60% burden reduction
- [x] Prevention dashboard live
- [x] Prevention rule auto-generation

### Quality Gates
- **Zero defect escapes** during Sprint 8
- **100% test pass rate** maintained
- **Quality score**: ≥67/100 (maintain Sprint 5 baseline)
- **Velocity**: 13-16 points delivered

---

## Story Selection Guidance for Planning

### If Starting Fresh (No Sprint 7 Diagnostic Results Yet)
**Recommend**: Defer Sprint 8 until Sprint 7 complete
**Reason**: Stories 2-4 depend on Sprint 7 diagnostic findings

### If Sprint 7 Diagnostics Available (Current State)
**Recommend**: Proceed with 14-point commitment
- Lock in: Stories 1-3 (P0, 8 points)
- Likely: Story 4 (P1, 3 points)
- Stretch: Stories 5 or 7 (P2, 2 points each)

### If Time-Constrained
**Recommend**: 13-point conservative commit
- Lock in: Stories 1-3 (P0, 8 points)
- Add: Story 5 (P2, 2 points)
- Defer: Stories 4, 6, 7 to Sprint 9

### If High Confidence
**Recommend**: 16-point aggressive commit
- All tracks: Stories 1-5, 7
- Parallel execution: 3 independent tracks
- Risk: High coordination overhead

---

## Next Steps

### Before Sprint 8 Starts
1. [ ] Complete Sprint 7 retrospective
2. [ ] Review this draft backlog with team
3. [ ] Finalize story selection (13/14/16 points?)
4. [ ] Create GitHub issues for selected stories
5. [ ] Assign stories to parallel tracks
6. [ ] Validate Sprint 7 deliverables available

### During Sprint 8 Planning
1. [ ] Confirm Sprint 7 diagnostic results
2. [ ] Validate story estimates (2-3 points each)
3. [ ] Assign track leads
4. [ ] Set daily standup schedule
5. [ ] Identify integration points
6. [ ] Document dependencies

### Sprint 8 Kickoff
1. [ ] Update SPRINT.md with Sprint 8 details
2. [ ] Start all 3 tracks in parallel
3. [ ] Daily standup: coordinate across tracks
4. [ ] Mid-sprint checkpoint: validate progress
5. [ ] Sprint review: demo all deliverables

---

## Related Documentation

- [Sprint 7 Story 1: Editor Agent Diagnostic Suite](docs/EDITOR_AGENT_DIAGNOSIS.md)
- [Sprint 7 Story 2: Test Gap Detection Automation](docs/TEST_GAP_REPORT.md)
- [Feature Registry](skills/feature_registry.json) - FEATURE-001 details
- [Defect Tracker](skills/defect_tracker.json) - Historical bug RCA
- [Agent Velocity Analysis](docs/AGENT_VELOCITY_ANALYSIS.md) - Story sizing guidance
- [Sprint Planning Guide](SPRINT.md) - Current sprint status

---

**Status**: DRAFT - Ready for Sprint 8 Planning Session
**Last Updated**: 2026-01-02 (During Sprint 7 Story 3 execution)
**Author**: Scrum Master (Quality-Enforcer Agent)
