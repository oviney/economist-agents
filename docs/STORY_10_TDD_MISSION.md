# Story 10: Stage 3 Migration with TDD Enforcement

**Status**: Ready for Execution
**Sprint**: 10
**Points**: 8
**Priority**: P0 (Critical Path - Phase 2 Migration)

## Mission Overview

Migrate Stage 3 (Content Generation) from economist_agent.py to CrewAI with **STRICT TDD discipline**.

### Context

```
AS A Migration Engineer,
I WANT to migrate Stage 3 to CrewAI using Test-Driven Development,
SO THAT we have testable confidence in the migration.
```

### Success Criteria

**Technical**:
- [ ] RED: Verification script exists and FAILS initially
- [ ] GREEN: Stage3Crew implementation makes tests PASS
- [ ] REFACTOR: Code quality improved while tests stay green

**Evidence**:
- [ ] Log shows distinct RED→GREEN transition
- [ ] pytest output proves initial failure
- [ ] pytest output proves final success
- [ ] No regression (tests pass after refactoring)

## TDD Protocol (Enforced)

### Phase 1: RED State (MUST FAIL)

**Objective**: Create failing test that documents expected behavior

**Deliverable**: `tests/verify_stage3_migration.py`

**Requirements**:
1. Mock input (topic, research data)
2. Assert expected CrewAI output structure
3. Attempt to import Stage3Crew
4. **MUST show import error or assertion failure**
5. **Exit code: 1 (failure)**

**Example Test Structure**:
```python
def test_stage3_crew_exists():
    """Test: Stage3Crew class can be imported."""
    from agents.stage3_crew import Stage3Crew
    assert Stage3Crew is not None  # Will fail - module doesn't exist

def test_content_creator_agent():
    """Test: Stage3Crew has content-creator agent."""
    crew = Stage3Crew()
    assert crew.content_creator is not None
    assert crew.content_creator.role == 'content-creator'

def test_stage3_pipeline():
    """Test: Stage3Crew produces article with chart data."""
    crew = Stage3Crew()
    result = crew.run(topic='Self-Healing Tests')
    assert 'article' in result
    assert 'chart_data' in result
    assert len(result['article']) > 800  # Min word count
```

**Expected Output (RED)**:
```bash
$ pytest tests/verify_stage3_migration.py
FAILED tests/verify_stage3_migration.py::test_stage3_crew_exists
ModuleNotFoundError: No module named 'agents.stage3_crew'
=== 3 failed in 0.12s ===
```

**Evidence Required**:
- Screenshot of FAILED test output
- Error traceback showing missing module
- Exit code 1

---

### Phase 2: GREEN State (MUST PASS)

**Objective**: Implement minimum code to make tests pass

**Deliverable**: `agents/stage3_crew.py`

**Requirements**:
1. Stage3Crew class with __init__ and run() methods
2. CrewAI agents: researcher, writer, editor
3. Sequential task pipeline (Research → Write → Edit)
4. Backward compatible with economist_agent.py API
5. **Tests MUST pass after implementation**
6. **Exit code: 0 (success)**

**Implementation Guidance**:
```python
from crewai import Crew, Agent, Task

class Stage3Crew:
    """CrewAI-based Stage 3 Content Generation pipeline."""
    
    def __init__(self):
        """Initialize agents and tasks."""
        self.researcher = Agent(
            role='researcher',
            goal='Find authoritative sources and data',
            backstory='Expert research analyst...',
            tools=[web_search, arxiv_search],
        )
        
        self.writer = Agent(
            role='writer',
            goal='Write Economist-style articles',
            backstory='Technical writer with Economist training...',
        )
        
        self.editor = Agent(
            role='editor',
            goal='Enforce quality gates and style',
            backstory='Meticulous editor...',
        )
    
    def run(self, topic: str) -> dict:
        """Execute content generation pipeline."""
        # Create sequential tasks
        # Research → Write → Edit
        # Return structured output
        pass
```

**Iteration Cycle**:
1. **Iteration 1**: Create Stage3Crew skeleton → run test → see failures
2. **Iteration 2**: Add researcher agent → run test → partial pass
3. **Iteration 3**: Add writer agent → run test → more passing
4. **Iteration 4**: Add editor agent → run test → **ALL GREEN**

**Expected Output (GREEN)**:
```bash
$ pytest tests/verify_stage3_migration.py
PASSED tests/verify_stage3_migration.py::test_stage3_crew_exists
PASSED tests/verify_stage3_migration.py::test_content_creator_agent
PASSED tests/verify_stage3_migration.py::test_stage3_pipeline
=== 3 passed in 2.45s ===
```

**Evidence Required**:
- Screenshot of PASSED test output
- All assertions successful
- Exit code 0

---

### Phase 3: REFACTOR State (STAY GREEN)

**Objective**: Improve code quality without breaking tests

**Deliverable**: Enhanced `agents/stage3_crew.py`

**Requirements**:
1. Add type hints to all methods
2. Add docstrings (Google style)
3. Extract magic numbers to constants
4. Split methods >20 lines
5. Add error handling with logging
6. **Tests MUST stay green throughout**

**Refactoring Checklist**:
- [ ] Type hints: `def run(self, topic: str) -> dict[str, Any]:`
- [ ] Docstrings: Google-style docstrings on all public methods
- [ ] Constants: Extract `MIN_WORD_COUNT = 800` etc.
- [ ] Error handling: `try/except` with logging
- [ ] Method length: No method >20 lines
- [ ] Tests passing: Run pytest after EACH change

**Process**:
1. Make ONE refactoring change
2. Run `pytest tests/verify_stage3_migration.py`
3. If FAIL → revert change → try different approach
4. If PASS → commit → proceed to next change

**Expected Output (STILL GREEN)**:
```bash
$ pytest tests/verify_stage3_migration.py -v
test_stage3_crew_exists PASSED
test_content_creator_agent PASSED
test_stage3_pipeline PASSED
=== 3 passed in 2.41s ===

$ mypy agents/stage3_crew.py
Success: no issues found in 1 source file

$ ruff check agents/stage3_crew.py
All checks passed!
```

**Evidence Required**:
- Tests still passing (no regression)
- Type checking passes (mypy)
- Linting passes (ruff)
- Code quality improved (readability, maintainability)

---

## TDD Benefits

### Why TDD for This Migration?

1. **Risk Mitigation**: Stage 3 is complex (4 agents, governance, charts)
2. **Regression Prevention**: Tests catch breaking changes immediately
3. **Documentation**: Tests document expected behavior
4. **Confidence**: GREEN tests prove migration works
5. **Refactoring Safety**: Can improve code fearlessly

### RED-GREEN-REFACTOR Discipline

**RED**: Write test that fails
- Forces us to think about API design before implementation
- Documents expected behavior explicitly
- Proves test is actually testing something (not false positive)

**GREEN**: Make it work
- Minimum implementation to pass tests
- Focuses on functionality, not perfection
- Quick feedback loop

**REFACTOR**: Make it right
- Improve code quality with safety net
- No fear of breaking things (tests catch issues)
- Clean code emerges naturally

### Anti-Patterns (AVOID)

❌ **Skip RED phase**: Implementing before test fails
- Risk: Test might always pass (false positive)
- Fix: Run test first, see failure, THEN implement

❌ **Test after implementation**: Writing tests to match code
- Risk: Tests don't catch actual bugs
- Fix: Test defines behavior, code fulfills behavior

❌ **Refactor before GREEN**: Optimizing failing tests
- Risk: Complexity without proof it works
- Fix: Get to GREEN first, then refactor

❌ **Multiple changes per test run**: Refactoring too much at once
- Risk: If test fails, can't isolate cause
- Fix: One change → test → commit → next change

---

## Execution Instructions

### Prerequisites

```bash
# Ensure CrewAI environment ready
source .venv/bin/activate
pip install crewai crewai-tools

# Verify migration engineer agent exists
grep "migration-engineer" schemas/agents.yaml
```

### Run Mission

```bash
# Execute TDD mission
python3 scripts/run_story10_crew.py
```

### Validate TDD Evidence

```bash
# Check for RED phase evidence
cat docs/sprint_logs/story_10_tdd_log.md | grep "FAILED"

# Check for GREEN phase evidence
cat docs/sprint_logs/story_10_tdd_log.md | grep "PASSED"

# Verify final state
pytest tests/verify_stage3_migration.py -v
```

### Manual Verification Checklist

- [ ] Log shows ModuleNotFoundError in Task 1 (RED proof)
- [ ] Log shows all tests PASSED in Task 2 (GREEN proof)
- [ ] Log shows tests still PASSED in Task 3 (REFACTOR proof)
- [ ] Verification script exists: `tests/verify_stage3_migration.py`
- [ ] Implementation exists: `agents/stage3_crew.py`
- [ ] Type checking passes: `mypy agents/stage3_crew.py`
- [ ] Linting passes: `ruff check agents/stage3_crew.py`

---

## Success Metrics

**TDD Discipline**:
- [ ] Log proves RED state (initial test failure)
- [ ] Log proves GREEN state (test passing after implementation)
- [ ] Log proves REFACTOR safety (tests stay green)

**Code Quality**:
- [ ] Type hints: 100% coverage
- [ ] Docstrings: All public methods
- [ ] Linting: 0 errors (ruff)
- [ ] Type checking: 0 errors (mypy)

**Functionality**:
- [ ] Stage3Crew produces article output
- [ ] Backward compatible with economist_agent.py
- [ ] Maintains quality standards (Economist style, sources)

---

## Related Documentation

- **ADR-003**: CrewAI Migration Strategy (phased approach)
- **ADR-002**: Agent Registry Pattern (AgentFactory usage)
- **Story 7**: Sprint 9 closure (previous CrewAI mission)
- **SCRUM_MASTER_PROTOCOL.md**: TDD enforcement guidelines

---

## Rollback Plan

If TDD mission fails:

1. **Revert commits**: `git reset --hard HEAD~3`
2. **Delete artifacts**:
   - `rm tests/verify_stage3_migration.py`
   - `rm agents/stage3_crew.py`
3. **Document failure**: Why TDD failed, what we learned
4. **Alternative approach**: Manual testing, smaller iterations

**Trigger Conditions**:
- Tests never reach GREEN state (>4 hours stuck)
- Implementation complexity exceeds estimates by 2x
- TDD overhead not justified by benefits

---

## Notes

This mission is a **quality culture showcase**. We're demonstrating that even for complex migrations, TDD discipline creates confidence and prevents regressions. The RED→GREEN→REFACTOR cycle is not bureaucracy—it's engineering rigor.

**Key Insight**: The RED phase is not wasted time. It forces us to think about the API contract before implementation, documents expected behavior, and proves our tests actually work. A test that never failed is a test we can't trust.
