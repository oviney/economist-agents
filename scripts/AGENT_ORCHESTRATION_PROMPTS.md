# Agent Orchestration Prompts
**Sprint 15 - Integration and Production Deployment**  
**Generated**: 2026-01-11  
**Purpose**: Ready-to-use prompts for orchestrating all 12 agents

---

## Sprint 15 Current Context (Day 4 - January 11, 2026)

**Sprint Goal**: Integration and Production Deployment  
**Progress**: 5/13 points complete (38%)  
**Timeline**: Day 4 of sprint, 6 days remaining  

**Story Status**:
- ✅ Story 9: COMPLETE (5 pts) - Integration work
- 🔄 Story 8: Validation phase (3 pts) - Quality checks in progress
- 🔄 Story 10: In progress (5 pts) - Deployment preparation

**Sprint Health**: ⚠️ Behind pace (should be at ~6 pts by Day 4)  
**Risk Level**: MEDIUM - Need to accelerate Story 8 completion to stay on track

---

## Sprint 15 Agent Prompts (Ready to Execute)

### Management Layer - Current Sprint Context

#### 1. Scrum Master - Sprint Health Assessment
```
@scrum-master, provide Sprint 15 health report:

Current state:
- Sprint: 15 (Integration and Production Deployment)
- Day: 4 of 10
- Progress: 5/13 points (38%)
- Velocity target: Should be at 52% by Day 5
- Behind pace: Yes (14% gap)

Story status analysis:
- Story 9: COMPLETE ✅ (5 pts) - What was delivered?
- Story 8: Validation phase (3 pts) - What's blocking completion?
- Story 10: In progress (5 pts) - What's the ETA?

Required outputs:
1. **Burndown analysis**: Are we on track to complete 13 pts?
2. **Blocker identification**: What's slowing Story 8?
3. **Risk assessment**: Will we meet sprint goal?
4. **Acceleration plan**: How to get back on pace by Day 6?
5. **Escalation decision**: Do we need to reduce scope?

Recommendations:
- Should Story 10 be simplified?
- Should Story 8 get additional resources?
- Can we parallelize any work?

Decision needed by EOD: Continue current pace or adjust sprint scope?
```

#### 2. Product Owner - Story 8 Completion Push
```
@po-agent, unblock Story 8 for immediate completion:

Story 8 context:
- Title: [Validation/Quality work - 3 pts]
- Status: Validation phase (stuck here for 1+ days)
- Sprint: 15, Priority: P0
- Blocking: Story 10 can't fully deploy without Story 8 validation

Analysis needed:
1. What are the acceptance criteria for Story 8?
2. Which criteria are complete vs incomplete?
3. Are there any criteria blockers (unclear requirements)?
4. Can we reduce scope to get Story 8 to DONE today?
5. What's the minimum viable completion?

Validation tasks to complete:
- [ ] Identify remaining acceptance criteria
- [ ] Break into sub-tasks (30-60 min each)
- [ ] Assign clear owners to each sub-task
- [ ] Remove any gold-plating or nice-to-haves
- [ ] Set completion deadline: EOD January 11

Output:
1. Story 8 remaining work breakdown
2. Scope reduction recommendations (if any)
3. Clear definition of "DONE" for Story 8
4. Next 2 hours of work plan
```

#### 3. DevOps - CI/CD Health for Integration Sprint
```
@devops, validate integration readiness:

Sprint 15 context: Integration and Production Deployment
Current work: Integrating multiple components for production

Critical checks for Day 4:
1. **CI/CD Pipeline Status**:
   - Run: `python3 scripts/ci_health_check.py --detailed`
   - All workflows green? Any red builds?
   - Integration tests passing?

2. **Deployment Readiness**:
   - Production branch status
   - Environment configurations validated
   - Secret/credential management checked

3. **Integration Test Coverage**:
   - Story 9 integration tests added?
   - Story 8 validation tests green?
   - Story 10 deployment tests ready?

4. **Sprint Velocity Tracking**:
   - Generate burndown for Sprint 15 (Day 1-4)
   - Compare to Sprint 14 (9/9 pts, 100%)
   - Identify velocity drop causes

5. **Production Blockers**:
   - Any failed security scans?
   - Dependency vulnerabilities?
   - Performance regressions?

Output format:
- CI/CD Health: ✅ Green / ⚠️ Yellow / ❌ Red
- Integration blockers: [LIST]
- Deployment risks: [LIST]
- Velocity trend: Sprint 14 vs Sprint 15
- Recommendations for next 24 hours
```

#### 4. Git Operator - Story Completion Commits
```
@git-operator, prepare Story 8 completion commit:

Story 8 is moving to COMPLETE status today (target: EOD)

Pre-commit checklist:
1. **Verify completeness**:
   - [ ] All Story 8 acceptance criteria met
   - [ ] Tests added and passing
   - [ ] Documentation updated
   - [ ] No TODOs or FIXMEs remaining

2. **Stage changes**:
   ```bash
   git status
   git add [Story 8 files]
   ```

3. **Double commit protocol** (pre-commit hooks):
   ```bash
   git commit -m "Draft"
   # If hooks modify files:
   git add -u
   git commit --amend --no-edit
   ```

4. **Commit message format**:
   ```
   Story 8: [Validation/Quality work] - COMPLETE
   
   - [Key deliverable 1]
   - [Key deliverable 2]
   - [Test coverage added]
   - [Documentation updated]
   
   Progress: Story 8 Complete ✅ (3 pts)
   Sprint 15: 8/13 pts (62%)
   ```

5. **Push and verify**:
   ```bash
   git push origin main
   # Wait for CI to go green
   # Verify no broken tests
   ```

6. **Update sprint tracker**:
   - Mark Story 8 as COMPLETE in sprint_tracker.json
   - Update SPRINT.md progress (8/13 pts)
   - Move to Story 10 focus

Execute when Story 8 work is validated and ready.
```

---

### Quality Engineering - Current Sprint Focus

#### 5. Code Quality Specialist - Story 8 Quality Validation
```
@code-quality-specialist, validate Story 8 code quality:

Context: Story 8 is in validation phase, needs quality sign-off to complete

Quality gates for Story 8:
1. **Type Safety**:
   - Run: `mypy scripts/[Story 8 files]`
   - Zero type errors required
   - All functions have type hints

2. **Code Formatting**:
   - Run: `ruff format --check scripts/[Story 8 files]`
   - All files properly formatted
   - No style violations

3. **Linting**:
   - Run: `ruff check scripts/[Story 8 files]`
   - Zero linting errors
   - No code smell warnings

4. **Documentation**:
   - All public functions have docstrings
   - Google-style format enforced
   - README/CHANGELOG updated

5. **Error Handling**:
   - Proper exception handling present
   - No bare except clauses
   - Logger used instead of print()

TDD validation:
- [ ] Tests were written BEFORE implementation
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage >80%: `pytest --cov=scripts`

Execute quality check:
```bash
make quality  # Should show 0 violations
```

Output:
- Quality score: PASS/FAIL
- Violations found: [LIST]
- Corrective actions needed: [LIST]
- Estimated fix time: X minutes
- Story 8 ready for merge: YES/NO
```

#### 6. Test Specialist - Story 8 Test Validation
```
@test-specialist, validate Story 8 test coverage:

Story 8 is in validation phase - test coverage must be proven

Test validation checklist:
1. **Run full test suite**:
   ```bash
   pytest tests/ -v --cov=scripts --cov-report=term-missing
   ```

2. **Story 8 specific coverage**:
   - Identify Story 8 files: [LIST FILES]
   - Check coverage for each: >80% required
   - Missing coverage lines: [IDENTIFY]

3. **Test pyramid validation**:
   - Unit tests: How many added for Story 8?
   - Integration tests: Any new integration tests?
   - E2E tests: Required for Story 8?

4. **Edge case coverage**:
   - Error handling tested?
   - Boundary conditions tested?
   - Invalid input handling tested?

5. **Regression prevention**:
   - All existing tests still pass?
   - No test modifications that weaken assertions?
   - No tests skipped or commented out?

Baseline before Story 8:
- Total tests: X
- Coverage: Y%
- Failures: 0

After Story 8:
- Total tests: X + [NEW]
- Coverage: Y% + [DELTA]
- Failures: 0 (required)

Output:
- Story 8 test coverage: X%
- Coverage delta: +Y%
- Tests added: Z
- Tests passing: ALL/SOME (must be ALL)
- Story 8 test validation: PASS/FAIL
- Ready for merge: YES/NO
```

#### 7. Visual QA - Story 9 Chart Validation (Retrospective)
```
@visual-qa-agent, validate Story 9 charts (completed work):

Story 9 is COMPLETE - retrospective validation of charts produced

Chart validation (if Story 9 included charts):
1. **Locate charts**: 
   ```bash
   find output/charts -name "*story9*" -type f
   ```

2. **Apply 5-gate validation** to each chart:
   - GATE 1: Layout integrity (red bar, spacing, no overlap)
   - GATE 2: Typography (readable, properly positioned)
   - GATE 3: Style compliance (Economist colors, gridlines)
   - GATE 4: Data integrity (labels, values visible)
   - GATE 5: Export quality (resolution, format)

3. **Document quality score**:
   - Charts validated: X
   - Gates passed: Y/5 per chart
   - Overall quality: EXCELLENT/GOOD/NEEDS WORK

4. **Archive for sprint retrospective**:
   - Quality benchmark for Sprint 15
   - Compare to Sprint 14 chart quality
   - Identify improvements for Story 10

If Story 9 had no charts:
- Confirm: "Story 9 did not include chart generation"
- Mark validation as N/A

Output:
- Story 9 chart count: X
- Quality score: Y/5 average
- Visual QA retrospective: [INSIGHTS]
- Recommendations for Story 10: [LIST]
```

---

## Immediate Action Plan (Next 4 Hours)

**Priority 1: Complete Story 8 (Target: EOD January 11)**
1. @po-agent - Break down remaining Story 8 work into 30-min tasks
2. @code-quality-specialist - Run quality validation on Story 8 code
3. @test-specialist - Validate Story 8 test coverage >80%
4. @git-operator - Prepare Story 8 completion commit
5. @scrum-master - Verify Story 8 meets Definition of Done

**Priority 2: Accelerate Story 10 (Target: Complete by January 13)**
1. @po-agent - Review Story 10 scope, identify any reduction opportunities
2. @devops - Validate deployment readiness (CI/CD, environments)
3. @scrum-master - Daily check-in on Story 10 progress

**Priority 3: Sprint Health Monitoring**
1. @scrum-master - Generate burndown chart after Story 8 completes
2. @devops - Compare Sprint 15 velocity to Sprint 14
3. @scrum-master - Decide if scope adjustment needed by January 12

---

## Management Layer Agents

### 1. Scrum Master Agent
**Role**: Sprint orchestrator, process enforcer, ceremony facilitator  
**Model**: Claude Sonnet 4  
**Primary Skills**: Sprint management, GitHub MCP integration

#### Orchestration Prompt
```
@scrum-master, I need you to:
- Check sprint health for Sprint 15 (Day 4, 5/13 pts complete)
- Identify what stories are in progress vs complete
- Flag any blockers or risks to sprint completion
- Recommend next priorities to complete sprint goal: "Integration and Production Deployment"

Context:
- Story 9: COMPLETE ✅ (5 pts)
- Story 8: Validation phase (3 pts)
- Story 10: In progress (5 pts)

Output format:
1. Sprint health assessment
2. Story status breakdown
3. Blocker analysis
4. Recommended actions for next 2 days
```

#### Daily Standup Prompt
```
@scrum-master, run daily standup check:

Questions:
1. What was completed yesterday?
2. What's planned for today?
3. Any blockers?
4. Is CI green?
5. Is documentation current?

Check sprint_tracker.json and report status.
```

---

### 2. Product Owner Agent
**Role**: Backlog refinement, acceptance criteria generation  
**Model**: Claude Sonnet 4  
**Primary Skills**: Story creation, Definition of Ready validation

#### Orchestration Prompt
```
@po-agent, I have a new feature request:

Request: [DESCRIBE REQUEST]

Tasks:
1. Convert to user story format (As a [role], I need [capability], so that [value])
2. Generate 5-7 testable acceptance criteria in Given/When/Then format
3. Identify edge cases and quality requirements
4. Estimate story complexity (1-8 points, Fibonacci)
5. Flag any ambiguities requiring clarification

Validate against DoR:
- WHO benefits (clear role/persona)
- WHAT needs to be done (specific capability)
- WHY it's valuable (business/user outcome)
- Acceptance criteria (testable, specific)
- Dependencies identified
- Story points estimated
```

#### Story Refinement Prompt
```
@po-agent, refine this story for sprint readiness:

Story ID: STORY-XXX
Title: [TITLE]
Description: [CURRENT DESCRIPTION]

Tasks:
1. Review acceptance criteria completeness
2. Break into tasks if >5 points
3. Identify test scenarios
4. Check for technical dependencies
5. Validate DoR compliance
6. Recommend sprint assignment (15 or 16)
```

---

### 3. DevOps Agent
**Role**: CI/CD pipeline maintenance, GitHub Projects v2 owner  
**Model**: Claude Sonnet 4  
**Primary Skills**: Infrastructure automation, monitoring

#### Orchestration Prompt
```
@devops, execute infrastructure health check:

Tasks:
1. Run `python3 scripts/ci_health_check.py --detailed`
2. Check GitHub Actions status (all workflows green?)
3. Verify test coverage badges current
4. Check for dependency security vulnerabilities
5. Report sprint velocity trends (last 3 sprints)

Output:
- CI/CD health: ✅/⚠️/❌
- Failed workflows (if any)
- Coverage delta from Sprint 14
- Security scan results
- Velocity chart recommendation
```

#### GitHub Projects Sync Prompt
```
@devops, sync sprint to GitHub Projects:

Sprint: 15
Stories: 8, 9, 10

Tasks:
1. Create/update project board for Sprint 15
2. Add custom fields (story points, priority, status)
3. Link issues to project
4. Generate burndown data snapshot
5. Update project board status from sprint_tracker.json

Ensure:
- Story points field configured
- Sprint milestone set
- Kanban view active
```

---

### 4. Git Operator Agent
**Role**: Repository librarian, commit standard enforcer  
**Model**: Claude Sonnet 4  
**Primary Skills**: Git operations, pre-commit hooks

#### Orchestration Prompt
```
@git-operator, execute clean commit protocol:

Changes: [LIST FILES CHANGED]
Story: STORY-XXX

Tasks:
1. Stage changes: git add [files]
2. Run pre-commit hooks (double commit protocol)
3. Format commit message:
   ```
   Story XXX: [Short Title]
   
   - [Detail 1]
   - [Detail 2]
   
   Progress: Story XXX [Status]
   ```
4. Push to origin/main
5. Verify CI triggers

Pre-commit handling:
- If hooks modify files: `git add -u && git commit --amend --no-edit`
- Always verify green build after push
```

---

## Quality Engineering Agents

### 5. Code Quality Specialist
**Role**: Refactoring and modernization using TDD  
**Model**: Claude Sonnet 4  
**Primary Skills**: Type hints, docstrings, quality standards

#### Orchestration Prompt
```
@code-quality-specialist, modernize this module:

File: scripts/[FILENAME].py

TDD Workflow:
1. **RED**: Write failing test for desired behavior
2. **GREEN**: Write minimal code to pass test
3. **REFACTOR**: Improve while keeping tests green

Quality checklist:
- [ ] Add type hints to all functions
- [ ] Add Google-style docstrings
- [ ] Replace print() with logger.error() for errors
- [ ] Add proper exception handling
- [ ] Extract prompts to module constants
- [ ] Use orjson instead of json
- [ ] Run `ruff format scripts/[FILENAME].py`
- [ ] Run `mypy scripts/[FILENAME].py`
- [ ] Verify all tests pass

Never:
- Write implementation before test
- Skip type hints
- Commit if `make quality` fails
```

#### Legacy Migration Prompt
```
@code-quality-specialist, migrate legacy code:

Legacy file: scripts/[OLD_FILE].py
Target: scripts/[NEW_FILE].py

Process:
1. Analyze legacy implementation
2. Write comprehensive test suite (TDD RED)
3. Implement modern replacement (TDD GREEN)
4. Refactor while keeping tests green (TDD REFACTOR)
5. Ensure backward compatibility
6. Update all imports/references
7. Document migration in CHANGELOG.md

Success criteria:
- 100% test coverage for new code
- All existing tests pass
- Type hints complete
- Documentation updated
```

---

### 6. Test Specialist
**Role**: Comprehensive test writing, 100% green build  
**Model**: Claude Sonnet 4  
**Primary Skills**: pytest, fixtures, Test Pyramid

#### Orchestration Prompt
```
@test-specialist, write comprehensive tests:

Module: [MODULE_NAME]
Coverage target: >80%

Test Pyramid approach:
1. **Unit Tests** (70%): Test individual functions
2. **Integration Tests** (20%): Test component interactions
3. **E2E Tests** (10%): Test full workflows

Workflow:
1. Run `pytest tests/ -v` (baseline)
2. Write unit tests for all public functions
3. Create fixtures for test data (avoid fragile mocks)
4. Write integration tests for workflows
5. Run `pytest tests/ -v --cov=scripts`
6. Achieve >80% coverage
7. Ensure all tests pass

Fixture pattern:
```python
@pytest.fixture
def sample_data():
    """Provide realistic test data"""
    return {
        "key": "value",
        "nested": {"data": 123}
    }

def test_function(sample_data):
    result = function_under_test(sample_data)
    assert result == expected
```

Never skip running tests before AND after changes.
```

#### Test Gap Detection Prompt
```
@test-specialist, identify test gaps:

Module: scripts/[FILENAME].py

Analysis:
1. Run coverage: `pytest tests/ --cov=scripts/[FILENAME] --cov-report=term-missing`
2. Identify untested functions
3. Identify untested branches
4. Identify missing edge cases
5. Recommend test additions

Output:
- Current coverage: X%
- Untested functions: [LIST]
- Missing edge cases: [LIST]
- Recommended tests: [DESCRIPTIONS]
```

---

### 7. Visual QA Agent
**Role**: Economist-style chart validation using Claude vision  
**Model**: Claude Sonnet 4 (vision-enabled)  
**Primary Skills**: Visual validation, layout verification

#### Orchestration Prompt
```
@visual-qa-agent, validate chart quality:

Chart: output/charts/[FILENAME].png

Quality gates (all must PASS):

**GATE 1: LAYOUT INTEGRITY**
- [ ] Red bar at top fully visible
- [ ] Title BELOW red bar (≥10px gap)
- [ ] No text overlapping
- [ ] No elements clipped at edges
- [ ] Source line visible at bottom

**GATE 2: TYPOGRAPHY**
- [ ] Title bold and readable
- [ ] Subtitle gray and smaller
- [ ] Axis labels legible
- [ ] No text cutoff

**GATE 3: STYLE COMPLIANCE**
- [ ] Red bar color #e3120b
- [ ] Economist color palette used
- [ ] Gridlines horizontal only
- [ ] Background #f1f0e9

**GATE 4: DATA INTEGRITY**
- [ ] All data labels present
- [ ] Values visible and accurate
- [ ] Legend clear (if present)

**GATE 5: EXPORT QUALITY**
- [ ] Resolution ≥300 DPI
- [ ] No compression artifacts
- [ ] File size reasonable

Output format:
- Overall: PASS/FAIL
- Failed gates: [LIST]
- Corrective actions: [RECOMMENDATIONS]
```

---

## Content Production Agents

### 8. Research Agent
**Role**: Data gathering and verification for articles  
**Function**: `research_agent.research()`  
**Primary Skills**: Source validation, fact-checking

#### Orchestration Prompt
```
@research-agent, gather data for article:

Topic: [ARTICLE TOPIC]
Focus: [KEY QUESTIONS/ANGLES]

Requirements:
1. Find 5-10 verified statistics with sources
2. Identify headline stat (most compelling number)
3. Generate chart data (time series or comparison)
4. Find contrarian angle (challenges conventional wisdom)
5. Flag any unverified claims

Output structure:
{
  "headline_stat": {
    "value": "Most compelling number",
    "source": "Organization, Report, Date",
    "verified": true
  },
  "data_points": [
    {
      "stat": "Specific number/percentage",
      "source": "Organization name",
      "year": "2024",
      "url": "URL if available",
      "verified": true
    }
  ],
  "chart_data": {
    "title": "Economist-style noun phrase",
    "type": "line|bar|scatter",
    "data": [...],
    "source_line": "Sources: Name1; Name2"
  },
  "contrarian_angle": "Surprising finding",
  "unverified_claims": ["DO NOT USE"]
}

Critical rules:
- Every stat MUST have named source
- Mark unverified claims clearly
- Prefer primary sources (surveys, reports)
- Flag conflicting numbers from different sources
```

---

### 9. Writer Agent
**Role**: Economist-style article composition  
**Function**: `writer_agent.write_article()`  
**Primary Skills**: Economist voice, chart integration

#### Orchestration Prompt
```
@writer-agent, compose Economist-style article:

Topic: [TITLE]
Research data: [RESEARCH OUTPUT]
Chart spec: [CHART DATA]
Word count: 800-1200

Economist voice requirements:

**Structure:**
1. OPENING: Lead with most striking fact (NO throat-clearing)
2. BODY: 3-4 sections with ## noun phrase headers
3. CHART EMBEDDING: 
   - Place chart markdown after discussing data
   - Reference naturally: "As the chart shows..."
   - Pattern: [paragraph] → ![Chart](path.png) → [insight]

**Voice:**
- British spelling (organisation, favour, analyse)
- Active voice ("Teams use AI" not "AI is used")
- Confident statements (no hedging)
- Concrete nouns, strong verbs

**BANNED phrases:**
- "In today's fast-paced world..."
- "game-changer" / "paradigm shift"
- "leverage" (as verb)
- "it could be argued that"

**Chart integration checklist:**
- [ ] Chart markdown embedded in body
- [ ] Chart referenced in surrounding text
- [ ] Placement after data discussion
- [ ] Natural reference (not "see figure 1")

Output: YAML with article content + chart spec
```

---

### 10. Graphics Agent
**Role**: Economist-style chart generation  
**Function**: `graphics_agent.generate_chart()`  
**Primary Skills**: Matplotlib, zone layouts, inline labels

#### Orchestration Prompt
```
@graphics-agent, generate Economist chart:

Chart spec:
{
  "title": "[TITLE]",
  "subtitle": "[UNITS/DESCRIPTION]",
  "type": "line|bar|scatter",
  "data": [...],
  "source_line": "Sources: [NAMES]"
}

Output path: output/charts/[FILENAME].png

Layout zones (strict boundaries):
1. RED BAR ZONE (y: 0.96-1.00)
2. TITLE ZONE (y: 0.85-0.94) - title y=0.90, subtitle y=0.85
3. CHART ZONE (y: 0.15-0.78) - data + inline labels
4. X-AXIS ZONE (y: 0.08-0.14) - axis labels ONLY
5. SOURCE ZONE (y: 0.01-0.06) - attribution

Inline label rules:
- Labels in CLEAR SPACE (never on data lines)
- Use xytext offset to push away from anchor
- For low series: place ABOVE line in gap (never below into X-axis)
- Preferred: end-of-line position

Colors:
- Background: #f1f0e9
- Red bar: #e3120b
- Primary: #17648d (navy)
- Secondary: #843844 (burgundy), #51bec7 (teal)
- Gridlines: #cccccc (horizontal only)

Validation:
- Run @visual-qa-agent after generation
- Fix any gate failures
- Re-generate until all gates PASS
```

---

### 11. Editor Agent
**Role**: 5-gate editorial quality validation  
**Function**: `editor_agent.review_article()`  
**Primary Skills**: Quality gates, style enforcement

#### Orchestration Prompt
```
@editor-agent, review article for publication:

Article: [ARTICLE CONTENT]
Charts: [CHART PATHS]

Apply 5 quality gates (ALL must PASS):

**GATE 1: OPENING - PASS/FAIL**
- Strong hook (data-driven)
- No throat-clearing
- No banned phrases ("In today's world...")
Rationale: [EXPLAIN]

**GATE 2: EVIDENCE - PASS/FAIL**
- All statistics sourced
- Primary sources used
- No unverified claims
Rationale: [EXPLAIN]

**GATE 3: VOICE - PASS/FAIL**
- British spelling (organisation, analyse)
- Active voice (>80%)
- No banned phrases ("game-changer", "leverage")
- Confident tone
Rationale: [EXPLAIN]

**GATE 4: STRUCTURE - PASS/FAIL**
- Logical flow (each section advances argument)
- Strong ending (not summary)
- Headers are noun phrases
Rationale: [EXPLAIN]

**GATE 5: CHART INTEGRATION - PASS/FAIL or N/A**
- Chart embedded in body (markdown present)
- Natural text reference
- Placement after data discussion
Rationale: [EXPLAIN]

**Overall decision:**
- APPROVED for publication (5/5 gates pass)
- REVISION REQUIRED (list failing gates + corrections)

Temperature: 0 (deterministic evaluation)
```

---

## Workflow Orchestration Examples

### Example 1: Full Article Production Pipeline

```bash
# Step 1: Research
@research-agent, gather data for "AI Testing Automation Trends"
Focus: adoption rates, ROI data, contrarian angles

# Step 2: Write article
@writer-agent, compose article using research data
Include chart integration from research output

# Step 3: Generate chart
@graphics-agent, create chart from writer's chart_spec
Output: output/charts/ai_testing_trends.png

# Step 4: Visual QA
@visual-qa-agent, validate chart quality
Fix any gate failures, regenerate if needed

# Step 5: Editorial review
@editor-agent, apply 5 quality gates to article
Fix revisions until all gates PASS

# Step 6: Git commit
@git-operator, commit approved article
Story: STORY-XXX, Status: Complete
```

### Example 2: Code Quality Sprint

```bash
# Step 1: PO defines story
@po-agent, create story for "Modernize agent_metrics.py"
Include type hints, docstrings, test coverage

# Step 2: Test specialist writes tests
@test-specialist, write comprehensive tests for agent_metrics.py
Target: >80% coverage, Test Pyramid approach

# Step 3: Code quality refactors
@code-quality-specialist, modernize agent_metrics.py using TDD
Follow RED → GREEN → REFACTOR cycle

# Step 4: Test specialist validates
@test-specialist, run full test suite
Verify no regressions, coverage improved

# Step 5: Git commit
@git-operator, commit refactored module
Story: STORY-XXX, include test results
```

### Example 3: Sprint Health Check

```bash
# Daily standup
@scrum-master, run daily standup for Sprint 15
Report: completed yesterday, planned today, blockers

# Mid-sprint checkpoint
@scrum-master, assess sprint health (Day 4 of 10)
Current: 5/13 pts, Stories 8-10 status, risks?

# DevOps validation
@devops, verify CI/CD health
Check: green build, coverage stable, no security issues

# Sprint retrospective (end of sprint)
@scrum-master, facilitate Sprint 15 retrospective
What went well? What to improve? Action items for Sprint 16?
```

---

## Agent Interaction Patterns

### Sequential Pipeline
Research → Writer → Graphics → Visual QA → Editor → Git Operator

### Parallel Quality Checks
- Code Quality + Test Specialist (independent)
- Visual QA + Editor (independent gates)

### Escalation Paths
Agent → Scrum Master → Product Owner (for blockers/ambiguities)

---

## Success Metrics

Track these for each agent invocation:

1. **Execution Time**: Minutes from prompt to completion
2. **Quality Score**: Pass rate on validation gates
3. **Revision Cycles**: Number of iterations to approval
4. **Blocker Rate**: Escalations requiring human intervention
5. **Velocity Impact**: Story points delivered per sprint

---

## Agent Status Monitoring

Check agent health:
```bash
# List all available agents
python3 scripts/agent_registry.py

# Get agent configuration
python3 scripts/agent_registry.py scrum-master

# Check running processes
ps aux | grep "python.*agent" | grep -v grep

# View agent status signals
cat skills/agent_status.json
```

---

**End of Orchestration Guide**  
For updates or agent modifications, see `.github/agents/*.agent.md`
