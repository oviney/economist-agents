# Sprint 13 Implementation Roadmap - Production-Grade Agentic Evolution

**Sprint Start**: 2026-01-04  
**Sprint Duration**: 1 week (5 working days)  
**Capacity**: 13 story points (9 committed + 4 buffer)  
**Epic**: EPIC-001 Production-Grade Agentic Evolution  
**Engineering Lead**: @migration-engineer  

---

## Executive Summary

Sprint 13 implements João Moura's production-grade AI principles across 3 parallel tracks:

1. **Track 1: Deterministic Backbone (STORY-005, 3 pts, P0)** - Flow-based orchestration replaces brittle WORKFLOW_SEQUENCE
2. **Track 2: Style Memory RAG (STORY-006, 3 pts, P1)** - Vector store with Gold Standard articles for Editor
3. **Track 3: ROI Telemetry (STORY-007, 3 pts, P2)** - Token cost tracking proves 100x efficiency

**Success Criteria**: Flow operational, RAG retrieves style examples, execution_roi.json logs accurate costs.

---

## Sprint 13 Stories Overview

| Story | Points | Priority | Track | Dependencies | Parallel Execution |
|-------|--------|----------|-------|--------------|-------------------|
| STORY-005 | 3 | P0 | Deterministic Backbone | None | Can run with STORY-007 |
| STORY-006 | 3 | P1 | Style Memory RAG | Soft on STORY-005 | Start after STORY-005 kickoff |
| STORY-007 | 3 | P2 | ROI Telemetry | None | Can run with STORY-005 |

**Total Committed**: 9 points  
**Buffer**: 4 points (31% reserve for unknowns)  
**Sprint Rating Target**: 9.0/10 (exceptional delivery)

---

## Implementation Strategy

### Week 1 Timeline (Parallel Execution)

**Monday (Day 1)**: Foundation Kickoff
- Morning: STORY-005 Task 1 (Flow Architecture Design - 1.5h)
- Afternoon: STORY-007 Task 1 (ROI Schema Design - 1h) + STORY-005 Task 2 (Flow Class - 2h)
- **Gate 1**: Flow architecture approved → STORY-006 can start

**Tuesday (Day 2)**: Core Implementation
- Morning: STORY-005 Task 3 (Migrate economist_agent.py - 3h)
- Afternoon: STORY-007 Task 2 (ROI Tracker - 2.5h) + STORY-006 Task 1 (ChromaDB Setup - 1.5h)
- **Gate 2**: Flow migration complete → Integration testing begins

**Wednesday (Day 3)**: Integration & Validation
- Morning: STORY-005 Task 4 (State Transition Tests - 1.5h) + STORY-006 Task 2 (Embeddings Pipeline - 2h)
- Afternoon: STORY-007 Task 3 (Instrument Agents - 2h) + STORY-005 Task 5 (Regression Testing - 1h)
- **Gate 3**: All tests passing → Documentation phase

**Thursday (Day 4)**: RAG Completion + Documentation
- Morning: STORY-006 Task 3 (Style Memory Tool - 2h) + STORY-007 Task 4 (Validation Tests - 1.5h)
- Afternoon: STORY-006 Task 4 (Editor Integration - 1.5h) + STORY-007 Task 5 (Aggregation Queries - 1.5h)
- **Gate 4**: RAG operational → Final polish

**Friday (Day 5)**: Polish + Sprint Close
- Morning: STORY-006 Task 5 (Integration Tests - 1.5h) + All Task 6 Documentation (1.5h total)
- Afternoon: Sprint retrospective, quality score report, Sprint 14 planning
- **Gate 5**: Sprint 13 complete → Retrospective

---

## STORY-005: Shift to Deterministic Backbone (3 pts, P0)

### Acceptance Criteria
- [ ] ContentGenerationFlow class created with @start/@listen decorators
- [ ] WORKFLOW_SEQUENCE removed, Flow.kickoff() operational
- [ ] State transition tests pass (<30s execution)
- [ ] Regression testing: gate pass rate ≥87%, chart embedding 100%
- [ ] Documentation: FLOW_ARCHITECTURE.md + README.md updated

### Task Checklist
- [ ] **Task 1** (1.5h): Flow architecture design → docs/FLOW_ARCHITECTURE.md
- [ ] **Task 2** (2h): Create ContentGenerationFlow class → src/economist_agents/flow.py
- [ ] **Task 3** (3h): Migrate economist_agent.py to Flow.kickoff()
- [ ] **Task 4** (1.5h): State transition tests → tests/test_flow_integration.py
- [ ] **Task 5** (1h): Regression testing (3 test articles, quality metrics)
- [ ] **Task 6** (0.5h): Documentation (README.md, FLOW_ARCHITECTURE.md)

### Critical Path
1. Task 1 must complete before Task 2 (design before implementation)
2. Task 2 must complete before Task 3 (Flow class before migration)
3. Task 3 must complete before Task 4 (migration before testing)
4. Task 5 blocks sprint completion (regression validation required)

### Risks & Mitigation
- **Risk**: Flow migration breaks existing agent behavior
  - **Mitigation**: Keep economist_agent.py.backup for quick rollback
- **Risk**: CrewAI Flow API differs from documentation
  - **Mitigation**: Test basic Flow pattern in Task 2 before full migration

---

## STORY-006: Establish Style Memory RAG (3 pts, P1)

### Acceptance Criteria
- [ ] Vector store populated with archived/*.md articles, query <500ms
- [ ] Minimum 1 Gold Standard article indexed, relevance >0.7
- [ ] style_memory_tool integrated with Stage4Crew Editor
- [ ] Editor prompt updated to suggest tool usage for GATE 3
- [ ] 3+ integration tests passing (embeddings, retrieval, agent integration)

### Task Checklist (Research Phase - THIS SPRINT)
- [ ] **Task 1.1** (2h): Vector database evaluation → docs/research/VECTOR_DB_COMPARISON.md
- [ ] **Task 1.2** (2h): Embeddings pipeline design → docs/research/EMBEDDINGS_PIPELINE_DESIGN.md
- [ ] **Task 1.3** (1.5h): CrewAI tool pattern analysis → docs/research/CREWAI_TOOL_INTEGRATION.md
- [ ] **Task 1.4** (1.5h): Editor integration strategy → docs/research/EDITOR_INTEGRATION_PLAN.md
- [ ] **Task 1.5** (1.5h): Test strategy planning → docs/research/RAG_TEST_PLAN.md
- [ ] **Task 1.6** (1h): Risk analysis & mitigation → docs/research/STYLE_MEMORY_RISKS.md

### Critical Path
1. Task 1.1 must complete first (database selection drives all other decisions)
2. Task 1.2 depends on Task 1.1 (embeddings pipeline uses selected database)
3. Task 1.3 and Task 1.4 can run in parallel (tool pattern independent of integration)
4. Task 1.5 and Task 1.6 can run in parallel (testing and risks independent)

### Risks & Mitigation
- **Risk**: archived/ directory empty (no Gold Standard articles)
  - **Mitigation**: Graceful degradation, use example articles from docs/
- **Risk**: ChromaDB setup complexity exceeds estimates
  - **Mitigation**: Fall back to simple in-memory vector store for MVP

**NOTE**: STORY-006 is RESEARCH PHASE ONLY in Sprint 13. Implementation phase deferred to Sprint 14.

---

## STORY-007: Implement ROI Telemetry (3 pts, P2)

### Acceptance Criteria
- [ ] execution_roi.json logs token usage with <10ms overhead
- [ ] Cost calculation accuracy ±1% vs API billing
- [ ] ROI multiplier >100x efficiency (human baseline: $350, agent: ~$3)
- [ ] Writer/Editor agents tracked with per-agent breakdown
- [ ] 3+ integration tests passing (cost calculation, ROI, persistence)

### Task Checklist
- [ ] **Task 1** (1h): ROI schema design → schemas/execution_roi_schema.json
- [ ] **Task 2** (2.5h): ROI tracker implementation → src/telemetry/roi_tracker.py
- [ ] **Task 3** (2h): Instrument agent registry → scripts/agent_registry.py modified
- [ ] **Task 4** (1.5h): Validation tests → tests/test_roi_telemetry.py
- [ ] **Task 5** (1.5h): Aggregation queries → scripts/roi_analyzer.py
- [ ] **Task 6** (0.5h): Documentation (README.md, docs/ROI_TELEMETRY.md)

### Critical Path
1. Task 1 must complete before Task 2 (schema before implementation)
2. Task 2 must complete before Task 3 (tracker before instrumentation)
3. Task 3 must complete before Task 4 (instrumentation before testing)
4. Task 5 can run in parallel with Task 4 (queries independent of tests)

### Risks & Mitigation
- **Risk**: Token usage extraction from CrewAI responses unclear
  - **Mitigation**: Start with manual logging, refine extraction in Task 3
- **Risk**: Performance overhead exceeds 10ms target
  - **Mitigation**: Async logging, background thread for I/O

---

## Quality Gates

### Gate 1: Flow Architecture Approved (Monday EOD)
**Trigger**: STORY-005 Task 1 complete  
**Validation**:
- State diagram shows all transitions
- Conditional routing documented
- Tech Lead approval obtained

**Pass Criteria**: Flow architecture document approved, no blockers identified  
**Fail Action**: Revise architecture, re-approve Tuesday morning

---

### Gate 2: Flow Migration Complete (Tuesday EOD)
**Trigger**: STORY-005 Task 3 complete  
**Validation**:
- economist_agent.py uses Flow.kickoff()
- WORKFLOW_SEQUENCE removed
- Local test generates article

**Pass Criteria**: Article generated successfully, no exceptions  
**Fail Action**: Debug migration, extend Task 3 to Wednesday morning

---

### Gate 3: All Tests Passing (Wednesday EOD)
**Trigger**: STORY-005 Task 4 + STORY-007 Task 4 complete  
**Validation**:
- Flow integration tests: 3+ passing, <30s
- ROI telemetry tests: 3+ passing, ±1% accuracy
- CI/CD green

**Pass Criteria**: All tests green, no regressions  
**Fail Action**: Fix failing tests, extend to Thursday morning

---

### Gate 4: RAG Operational (Thursday EOD)
**Trigger**: STORY-006 research tasks complete  
**Validation**:
- Vector database selected (ChromaDB recommended)
- Embeddings pipeline designed
- Tool integration plan approved

**Pass Criteria**: Research phase complete, implementation ready for Sprint 14  
**Fail Action**: Complete remaining research Friday morning

---

### Gate 5: Sprint 13 Complete (Friday EOD)
**Trigger**: All documentation complete  
**Validation**:
- All acceptance criteria met (STORY-005: 5/5, STORY-006: research, STORY-007: 5/5)
- Quality score ≥9.0/10
- No regressions in article quality

**Pass Criteria**: Sprint 13 closed, Sprint 14 planning ready  
**Fail Action**: Document incomplete work, adjust Sprint 14 scope

---

## Success Metrics

### STORY-005: Flow-Based Orchestration
- **Metric 1**: WORKFLOW_SEQUENCE references = 0 (target: 0)
- **Metric 2**: State transition tests <30s (target: <30s)
- **Metric 3**: Gate pass rate ≥87% (target: no regression)
- **Metric 4**: Chart embedding 100% (target: 100%)

### STORY-006: Style Memory RAG (Research Phase)
- **Metric 1**: Vector database recommendation documented (ChromaDB expected)
- **Metric 2**: Embeddings pipeline design complete (architecture diagram)
- **Metric 3**: Tool integration plan approved (Stage4Crew modifications)
- **Metric 4**: Test strategy documented (3+ test cases defined)

### STORY-007: ROI Telemetry
- **Metric 1**: Token tracking overhead <10ms (target: <10ms)
- **Metric 2**: Cost calculation ±1% accurate (target: ±1%)
- **Metric 3**: ROI multiplier >100x (target: >100x efficiency)
- **Metric 4**: Per-agent breakdown accurate (research, writer, editor, graphics)

---

## Sprint 13 Retrospective (Friday)

### Questions to Answer
1. **What worked well?**
   - Parallel execution (3 tracks running simultaneously)
   - Clear acceptance criteria (no ambiguity)
   - Research phase separation for STORY-006

2. **What didn't work?**
   - Any blocked dependencies?
   - Any estimates significantly off?
   - Any quality regressions?

3. **What should we improve?**
   - Task breakdown accuracy
   - Integration test strategies
   - Documentation completeness

4. **Sprint Rating**: Target 9.0/10
   - Exceptional delivery: All 3 stories complete
   - Quality maintained: No regressions
   - Foundation solid: Sprint 14 ready to build on

---

## Sprint 14 Planning (Preview)

Based on Sprint 13 completion:

**STORY-006 Implementation Phase** (5 pts, P0):
- Task 2.1: Vector database setup (src/rag/chroma_client.py)
- Task 2.2: Embeddings pipeline (src/rag/embeddings_pipeline.py)
- Task 2.3: Style memory tool (src/tools/style_memory_tool.py)
- Task 2.4: Editor integration (src/crews/stage4_crew.py)
- Task 2.5: Integration tests (tests/test_style_memory_rag.py)

**STORY-008: Multi-Agent Parallel Generation** (5 pts, P1):
- Leverage Flow architecture (STORY-005 foundation)
- Implement parallel research + writing + graphics
- Target: 3x throughput improvement

**STORY-009: Advanced Quality Dashboard** (3 pts, P2):
- Integrate ROI telemetry (STORY-007 data)
- Flow execution visualization
- Real-time agent status monitoring

---

## File Tracking

### Files Created (Sprint 13)
- `tasks/STORY-005-deterministic-backbone.md`
- `tasks/STORY-006-style-memory-rag.md` (already exists, reviewed)
- `tasks/STORY-007-roi-telemetry.md`
- `docs/SPRINT_13_IMPLEMENTATION_ROADMAP.md` (this file)
- `src/economist_agents/flow.py` (200 lines)
- `src/telemetry/roi_tracker.py` (200 lines)
- `scripts/roi_analyzer.py` (150 lines)
- `schemas/execution_roi_schema.json` (150 lines)
- `tests/test_flow_integration.py` (150 lines)
- `tests/test_roi_telemetry.py` (100 lines)
- `docs/FLOW_ARCHITECTURE.md` (150 lines)
- `docs/ROI_TELEMETRY.md` (100 lines)
- `docs/research/VECTOR_DB_COMPARISON.md` (STORY-006)
- `docs/research/EMBEDDINGS_PIPELINE_DESIGN.md` (STORY-006)
- `docs/research/CREWAI_TOOL_INTEGRATION.md` (STORY-006)
- `docs/research/EDITOR_INTEGRATION_PLAN.md` (STORY-006)
- `docs/research/RAG_TEST_PLAN.md` (STORY-006)
- `docs/research/STYLE_MEMORY_RISKS.md` (STORY-006)

### Files Modified (Sprint 13)
- `scripts/economist_agent.py` (200 lines changed)
- `scripts/sm_agent.py` (WORKFLOW_SEQUENCE deprecated)
- `scripts/agent_registry.py` (50 lines changed)
- `src/crews/stage3_crew.py` (20 lines changed)
- `src/crews/stage4_crew.py` (20 lines changed)
- `README.md` (40 lines added)
- `requirements.txt` (add crewai>=0.95.0)

---

## Team Assignments

**@migration-engineer** (Technical Lead):
- STORY-005: Flow architecture design + implementation
- STORY-007: ROI telemetry design + implementation
- Code reviews for all stories
- Integration testing coordination

**@product-research** (Research Lead):
- STORY-006: Vector database evaluation
- STORY-006: Embeddings pipeline design
- STORY-006: RAG architecture recommendations

**@qa** (Quality Assurance):
- Test strategy validation (all stories)
- Regression testing (STORY-005)
- Integration test coverage (all stories)
- CI/CD pipeline monitoring

**@scrum-master** (Process Lead):
- Sprint tracking and velocity monitoring
- Daily standup facilitation
- Blocker resolution
- Sprint retrospective moderation

---

## Communication Plan

### Daily Standup (15 min, 9:00 AM)
**Format**:
- Yesterday: What was completed?
- Today: What's planned?
- Blockers: Any impediments?

**Example**:
- "@migration-engineer: Completed STORY-005 Task 1 (Flow design). Today: Task 2 (Flow class). No blockers."

### Mid-Sprint Check-In (Wednesday, 30 min)
**Agenda**:
- Review progress vs. plan (9/13 points expected)
- Identify risks to Sprint 13 completion
- Adjust execution plan if needed

### Sprint Review (Friday, 1 hour)
**Agenda**:
- Demo STORY-005 (Flow orchestration)
- Demo STORY-007 (ROI telemetry)
- Review STORY-006 research deliverables
- Quality score presentation
- Sprint 14 preview

---

## Definition of Done (Sprint 13)

### Story-Level DoD
- [ ] All acceptance criteria met (5/5 for each story)
- [ ] Code reviewed and approved by Tech Lead
- [ ] Tests passing in CI/CD (>80% coverage)
- [ ] Documentation complete (README.md, story-specific docs)
- [ ] No regressions in article quality (gate pass rate, chart embedding)

### Sprint-Level DoD
- [ ] All 3 stories complete (9/9 points delivered)
- [ ] Quality score ≥9.0/10
- [ ] Sprint retrospective complete
- [ ] Sprint 14 backlog refined
- [ ] CHANGELOG.md updated with Sprint 13 summary

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Flow migration breaks existing behavior | Medium | High | Keep backup, comprehensive tests, rollback plan |
| ChromaDB setup exceeds estimates | Low | Medium | Fall back to in-memory vector store for MVP |
| Token usage extraction unclear | Medium | Medium | Start with manual logging, refine in Task 3 |
| Performance overhead >10ms | Low | Low | Async logging, background threads |
| Test coverage insufficient | Medium | High | TDD approach, test-first implementation |
| Sprint 13 capacity overflow | Low | Medium | 4-point buffer (31% reserve) |

---

## Appendix: Technical References

### CrewAI Flow API
- **Documentation**: https://docs.crewai.com/flows
- **Decorators**: `@start()`, `@listen(previous_method)`
- **State Passing**: Return dict from each method
- **Error Handling**: Raise exceptions for escalation

### Vector Database Options
- **ChromaDB**: Lightweight, Python-native, persistent storage
- **FAISS**: High-performance, in-memory, Facebook AI
- **Pinecone**: Cloud-hosted, managed, scalable

### LLM Pricing (2024)
- **GPT-4o**: $0.005 / $0.015 per 1K tokens (input/output)
- **Claude Sonnet**: $0.003 / $0.015 per 1K tokens (input/output)
- **Human Rate**: $50/hour (senior writer baseline)

---

**Roadmap Version**: 1.0  
**Created**: 2026-01-04  
**Last Updated**: 2026-01-04  
**Owner**: @migration-engineer  
**Approved By**: Tech Lead, Product Owner, Scrum Master  
**Sprint Status**: IN PROGRESS  
