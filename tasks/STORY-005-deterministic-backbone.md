# STORY-005: Shift to Deterministic Backbone (Flow-Based Orchestration)

**Story Points**: 3 (capped from 3.4, actual effort 9.5 hours)  
**Priority**: P0 (Architectural Foundation)  
**Epic**: EPIC-001 Production-Grade Agentic Evolution  
**Status**: IN PROGRESS  
**Sprint**: 13  

## User Story

As a **system architect**, I need **deterministic flow-based orchestration** so that **agent routing is reliable, testable, and observable**.

## Business Value

- **100% Reliability**: Eliminate routing failures that cause silent agent drops
- **Visibility**: Clear state transitions for debugging and monitoring
- **Testability**: Explicit state machine enables unit testing of transitions
- **Foundation**: Required for STORY-006 (Style Memory RAG) integration

**João Moura Principle**: "Orchestration must be deterministic and observable. No magic routing—explicit state machines win."

## Acceptance Criteria

- [ ] **AC1**: ContentGenerationFlow class created in `src/economist_agents/flow.py` using CrewAI v0.95.0+ Flow API with @start/@listen decorators
- [ ] **AC2**: All agent transitions explicitly defined (research→writer→editor→graphics→publish) with conditional routing for editor rejection
- [ ] **AC3**: WORKFLOW_SEQUENCE dictionary removed from `scripts/sm_agent.py` and replaced with Flow.kickoff() calls
- [ ] **AC4**: State transition tests pass (happy path, editor rejection, research failure) in <30 seconds
- [ ] **AC5**: Regression validation shows gate pass rate ≥87% and chart embedding 100% (no quality degradation)

## Task Breakdown (6 tasks, 9.5 hours total)

### Task 1: Flow Architecture Design (1.5h, P0)
**Goal**: Design state machine architecture before implementation

**Subtasks**:
1. Create `docs/FLOW_ARCHITECTURE.md` with:
   - State transition diagram (IDLE → RESEARCH → WRITE → EDIT → GRAPHICS → PUBLISH)
   - Conditional routing rules (if editor fails → rework loop)
   - Error handling strategy (research failure → escalation)
   - State persistence design (track current state for resume)

2. Review CrewAI Flow API documentation:
   - @start() decorator pattern
   - @listen() decorator pattern
   - State passing between methods
   - Error propagation rules

3. Validate against current WORKFLOW_SEQUENCE:
   - Map `sm_agent.py` line 205 WORKFLOW_SEQUENCE to Flow states
   - Identify conditional logic gaps (editor rejection not in WORKFLOW_SEQUENCE)
   - Document migration path

**Definition of Done**:
- [ ] `docs/FLOW_ARCHITECTURE.md` created with complete state diagram
- [ ] State transitions documented: 6+ states with 8+ transitions
- [ ] Conditional routing documented (3+ scenarios)
- [ ] Error handling strategy defined
- [ ] Approved by Tech Lead (architecture review)

**Acceptance Validation**:
State diagram shows all agent transitions, conditional routing documented (3+ scenarios), error handling strategy defined.

---

### Task 2: Create Flow Class (2h, P0)
**Goal**: Implement ContentGenerationFlow with @start/@listen decorators

**Subtasks**:
1. Create `src/economist_agents/flow.py`:
   ```python
   from crewai.flow.flow import Flow, listen, start
   from typing import Dict, Any
   
   class ContentGenerationFlow(Flow):
       """
       Deterministic orchestration for content generation pipeline.
       
       State transitions:
       IDLE → RESEARCH → WRITE → EDIT → GRAPHICS → PUBLISH
       
       Conditional routing:
       - If editor rejects: EDIT → WRITE (rework loop)
       - If research fails: RESEARCH → ESCALATION
       """
       
       @start()
       def research_phase(self) -> Dict[str, Any]:
           """Execute research agent, gather sources and data."""
           # Implementation from stage3_crew.py research_agent
           pass
       
       @listen(research_phase)
       def writing_phase(self, research_output: Dict[str, Any]) -> Dict[str, Any]:
           """Execute writer agent, generate article draft."""
           # Implementation from stage3_crew.py writer_agent
           pass
       
       @listen(writing_phase)
       def editing_phase(self, writer_output: Dict[str, Any]) -> Dict[str, Any]:
           """Execute editor agent, apply 5 quality gates."""
           # Implementation from stage4_crew.py reviewer_agent
           pass
       
       @listen(editing_phase)
       def graphics_phase(self, editor_output: Dict[str, Any]) -> Dict[str, Any]:
           """Execute graphics agent, generate charts."""
           # Conditional: skip if no chart_data
           pass
       
       @listen(graphics_phase)
       def publish_phase(self, graphics_output: Dict[str, Any]) -> Dict[str, Any]:
           """Final validation and output generation."""
           # Implementation from economist_agent.py output logic
           pass
   ```

2. Integrate Stage3Crew and Stage4Crew:
   - Import `Stage3Crew` from `src/crews/stage3_crew.py`
   - Import `Stage4Crew` from `src/crews/stage4_crew.py`
   - Call crew.kickoff() within each Flow method
   - Pass outputs between methods via return values

3. Add state tracking:
   - Log state transitions: `logger.info(f"Transitioning: {from_state} → {to_state}")`
   - Track execution time per state
   - Persist state to `skills/flow_state.json` for resume capability

4. Implement conditional routing:
   - Check editor output for gate failures
   - If gates_failed > 2: return to writing_phase with feedback
   - If research fails: raise EscalationRequired exception

**Definition of Done**:
- [ ] `src/economist_agents/flow.py` created (200+ lines)
- [ ] All 5 Flow methods implemented (@start/@listen decorators)
- [ ] Stage3Crew and Stage4Crew integrated
- [ ] State logging operational (console + JSON)
- [ ] Conditional routing implemented (editor rejection loop)
- [ ] Unit tests pass: `pytest tests/test_flow_class.py -v`

**Acceptance Validation**:
ContentGenerationFlow class exists with @start/@listen decorators, all agent transitions implemented, state logging operational.

---

### Task 3: Migrate economist_agent.py (3h, P0)
**Goal**: Refactor main orchestration to use Flow.kickoff()

**Subtasks**:
1. Backup current implementation:
   ```bash
   cp scripts/economist_agent.py scripts/economist_agent.py.backup
   ```

2. Refactor `generate_economist_post()` function:
   - Remove manual agent calls (run_research_agent, run_writer_agent, etc.)
   - Replace with:
     ```python
     from src.economist_agents.flow import ContentGenerationFlow
     
     def generate_economist_post(topic, category, talking_points, output_dir):
         flow = ContentGenerationFlow()
         result = flow.kickoff(inputs={'topic': topic, 'category': category})
         return result
     ```

3. Preserve existing functionality:
   - Keep governance gates (GovernanceTracker integration)
   - Keep metrics collection (AgentMetrics tracking)
   - Keep output formatting (markdown generation, chart paths)
   - Keep validation (PublicationValidator checks)

4. Update imports:
   - Remove: `from agents.research_agent import run_research_agent`
   - Remove: `from agents.writer_agent import run_writer_agent`
   - Add: `from src.economist_agents.flow import ContentGenerationFlow`

5. Test locally:
   ```bash
   python3 scripts/economist_agent.py --topic "Test Article"
   ```

**Definition of Done**:
- [ ] `scripts/economist_agent.py` refactored (200+ lines changed)
- [ ] Flow.kickoff() replaces manual agent orchestration
- [ ] Governance, metrics, validation preserved
- [ ] Backup created for rollback
- [ ] Local test generates article successfully
- [ ] Commit with message: "STORY-005: Migrate to Flow orchestration"

**Acceptance Validation**:
WORKFLOW_SEQUENCE dictionary removed, Flow.kickoff() operational, all existing features preserved (governance, metrics, output).

---

### Task 4: State Transition Tests (1.5h, P0)
**Goal**: Validate Flow state machine with comprehensive test cases

**Subtasks**:
1. Create `tests/test_flow_integration.py`:
   ```python
   import pytest
   from src.economist_agents.flow import ContentGenerationFlow
   
   def test_happy_path():
       """Test complete flow: research → write → edit → graphics → publish"""
       flow = ContentGenerationFlow()
       result = flow.kickoff(inputs={'topic': 'Test Article'})
       
       assert result['status'] == 'published'
       assert 'article' in result
       assert result['gates_passed'] >= 4  # Minimum 4/5 gates
   
   def test_editor_rejection_loop():
       """Test conditional routing: editor fails → return to writer"""
       flow = ContentGenerationFlow()
       # Mock editor to fail gates
       result = flow.kickoff(inputs={'topic': 'Bad Article'})
       
       # Should trigger rework loop
       assert result['iterations'] >= 2
       assert 'rework_applied' in result
   
   def test_research_failure():
       """Test error handling: research fails → escalation"""
       flow = ContentGenerationFlow()
       # Mock research to fail
       with pytest.raises(EscalationRequired):
           flow.kickoff(inputs={'topic': 'Unavailable Data'})
   ```

2. Add integration tests:
   - Test state persistence (pause/resume)
   - Test state transition logging (verify JSON output)
   - Test metrics collection (execution time per state)

3. Validate test performance:
   ```bash
   time pytest tests/test_flow_integration.py -v
   # Must complete in <30 seconds
   ```

**Definition of Done**:
- [ ] `tests/test_flow_integration.py` created (150+ lines)
- [ ] 3+ test cases passing (happy path, rejection loop, error handling)
- [ ] All tests run in <30 seconds
- [ ] Coverage ≥80%: `pytest --cov=src.economist_agents.flow`
- [ ] CI/CD integration: tests run on every commit

**Acceptance Validation**:
State transition tests pass (3+ cases), execution <30 seconds, coverage >80%.

---

### Task 5: Regression Testing (1h, P0)
**Goal**: Validate no quality degradation from Flow migration

**Subtasks**:
1. Generate 3 test articles using Flow:
   ```bash
   python3 scripts/economist_agent.py --topic "AI Testing Tools"
   python3 scripts/economist_agent.py --topic "DevOps Transformation"
   python3 scripts/economist_agent.py --topic "Quality Metrics That Matter"
   ```

2. Measure quality metrics:
   - Gate pass rate: Target ≥87% (current baseline)
   - Chart embedding: Target 100% (must be in article markdown)
   - Word count: Target 800+ words
   - British spelling: Zero American spellings
   - Banned phrases: Zero occurrences

3. Compare against baseline:
   - Load `skills/agent_metrics.json`
   - Calculate: Flow gate pass rate vs. baseline (87%)
   - Calculate: Flow chart embedding vs. baseline (100%)
   - Document any regressions

4. Validate governance:
   - Check `skills/governance/*.json` files created
   - Verify approval gates triggered
   - Confirm audit trail complete

**Definition of Done**:
- [ ] 3 test articles generated successfully
- [ ] Gate pass rate ≥87% (no regression)
- [ ] Chart embedding 100% (no regression)
- [ ] Quality metrics documented in `docs/STORY-005-REGRESSION-REPORT.md`
- [ ] All tests archived in `tests/fixtures/flow_regression/`
- [ ] Approved by Quality Lead

**Acceptance Validation**:
Regression testing shows gate pass rate ≥87%, chart embedding 100%, no quality degradation.

---

### Task 6: Documentation (0.5h, P2)
**Goal**: Update project documentation with Flow architecture

**Subtasks**:
1. Update `README.md`:
   ```markdown
   ## Architecture
   
   ### Flow-Based Orchestration (v3.0)
   
   Content generation uses CrewAI Flow API for deterministic state transitions:
   
   ```
   IDLE → RESEARCH → WRITE → EDIT → GRAPHICS → PUBLISH
                              ↑        ↓
                              └────────┘ (rework loop)
   ```
   
   See `docs/FLOW_ARCHITECTURE.md` for detailed design.
   ```

2. Update `docs/FLOW_ARCHITECTURE.md`:
   - Add troubleshooting section:
     - "Flow stuck in rework loop": Check editor gate criteria
     - "State persistence failure": Verify skills/flow_state.json writable
     - "Conditional routing not triggering": Check editor output format

3. Add architecture diagrams:
   - Export state diagram from Task 1 to PNG
   - Add to README.md and FLOW_ARCHITECTURE.md

**Definition of Done**:
- [ ] README.md updated with Flow architecture section
- [ ] FLOW_ARCHITECTURE.md has troubleshooting section
- [ ] Architecture diagram exported to PNG
- [ ] Links verified: `./verify_links.sh`

**Acceptance Validation**:
Documentation updated (README.md, FLOW_ARCHITECTURE.md), troubleshooting guide complete.

---

## Technical Specifications

### CrewAI Flow API Requirements
- **Version**: CrewAI v0.95.0+
- **Decorators**: `@start()`, `@listen(previous_method)`
- **State Passing**: Return dict from each method, passed as argument to next
- **Error Handling**: Raise exceptions for escalation, catch in Flow orchestrator

### File Modifications
- **CREATE**: `src/economist_agents/flow.py` (200 lines)
- **CREATE**: `docs/FLOW_ARCHITECTURE.md` (150 lines)
- **CREATE**: `tests/test_flow_integration.py` (150 lines)
- **MODIFY**: `scripts/economist_agent.py` (200 lines changed)
- **DELETE**: WORKFLOW_SEQUENCE from `scripts/sm_agent.py` lines 205-210
- **CREATE**: `docs/STORY-005-REGRESSION-REPORT.md` (50 lines)

### Integration Points
- **Stage3Crew**: `src/crews/stage3_crew.py` (research, writer, graphics agents)
- **Stage4Crew**: `src/crews/stage4_crew.py` (reviewer, editor agents)
- **AgentMetrics**: `scripts/agent_metrics.py` (execution time tracking)
- **GovernanceTracker**: `scripts/governance.py` (approval gates)

### Quality Gates
- [ ] All unit tests pass: `pytest tests/test_flow_class.py -v`
- [ ] Integration tests pass: `pytest tests/test_flow_integration.py -v`
- [ ] Regression tests pass: gate rate ≥87%, chart embedding 100%
- [ ] Code coverage ≥80%: `pytest --cov=src.economist_agents.flow`
- [ ] Documentation complete: README.md and FLOW_ARCHITECTURE.md updated

### Risk Mitigation
1. **Conditional routing complexity**: Start with simple if/else, avoid nested conditionals
2. **State persistence overhead**: Use lightweight JSON, <10ms overhead
3. **CrewAI version compatibility**: Pin v0.95.0+ in requirements.txt
4. **Regression risk**: Keep economist_agent.py.backup for quick rollback

## Dependencies

**Blocks**:
- STORY-006 (Style Memory RAG) - Soft dependency, RAG tool benefits from Flow state tracking

**Blocked By**:
- None (P0 architectural foundation)

**Parallel Execution**:
- STORY-007 (ROI Telemetry) can run in parallel

## Validation Checklist

- [ ] Task 1: Flow architecture design approved
- [ ] Task 2: ContentGenerationFlow class implemented
- [ ] Task 3: economist_agent.py migrated to Flow.kickoff()
- [ ] Task 4: State transition tests passing (<30s)
- [ ] Task 5: Regression testing complete (gate rate ≥87%)
- [ ] Task 6: Documentation updated (README.md, FLOW_ARCHITECTURE.md)
- [ ] All acceptance criteria met (5/5)
- [ ] Code review approved by Tech Lead
- [ ] Quality Lead sign-off on regression results

---

**Created**: 2026-01-04  
**Last Updated**: 2026-01-04  
**Assigned To**: @migration-engineer  
**Story Status**: IN PROGRESS  
