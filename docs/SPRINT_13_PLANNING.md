# Sprint 13 Planning - Production-Grade Agentic Evolution

**Sprint Duration**: January 6-12, 2026 (1 week, 5 working days)  
**Sprint Goal**: Initiate João Moura's Production ROI principles - Research phase for deterministic orchestration and style memory  
**Total Capacity**: 13 story points  
**Sprint Status**: PLANNING COMPLETE ✅

## Sprint Overview

### Strategic Context

Sprint 13 begins **EPIC-001: Production-Grade Agentic Evolution** implementing CrewAI founder João Moura's production-grade AI system philosophy:

1. **Deterministic Orchestration**: Replace autonomous agent routing with state-machine precision (Flows)
2. **Quality Memory Systems**: RAG-based style/pattern memory for consistent outputs
3. **ROI Measurement**: Token costs vs human-hour equivalents for business validation

### Current State vs Target State

| Aspect | Current State | Target State (Sprint 13) |
|--------|--------------|--------------------------|
| **Orchestration** | WORKFLOW_SEQUENCE dict (brittle hardcoded routing) | Flow-based @start/@listen decorators |
| **Style Memory** | None (prompt-only knowledge) | Vector store RAG with Gold Standard articles |
| **ROI Telemetry** | Anecdotal claims (50x faster) | Automated token cost logging |
| **Editor GATE 3** | 87% pass rate | 95%+ pass rate (via style memory) |
| **Routing Reliability** | Manual agent coordination | Deterministic state-machine transitions |

## Sprint Backlog

### Story Priority Sequence

**Sprint 13 Focus**: Research & Foundation (Parallel Tracks)

1. **STORY-005**: Shift to Deterministic Backbone (3 pts, P0) - **Track 1: Architecture**
2. **STORY-006**: Establish Style Memory RAG (3 pts, P1) - **Track 2: Research Phase** ✅ TASK FILE CREATED
3. **STORY-007**: Implement ROI Telemetry Hook (3 pts, P2) - **Track 3: Observability**

**Total Committed**: 9 story points (69% capacity)  
**Buffer**: 4 story points (31% reserve for quality/unknowns)

---

## STORY-006: Style Memory RAG - Research Phase ✅

**Status**: Task file created, ready for Developer Agent kickoff  
**Task File**: `tasks/STORY-006-style-memory-rag.md`  
**Story Points**: 3 (research phase only)  
**Priority**: P1 (High - Quality enhancement)

### Agent Skills Analysis

Based on crew analysis (src/crews/stage3_crew.py, stage4_crew.py), determined which agents require Style Memory skills:

#### ✅ **Editor Agent (Stage4Crew) - PRIMARY BENEFICIARY**
- **Current State**: No tools configured, prompt-only style knowledge
- **Required Skill**: style_memory_tool.py for GATE 3 (Voice) evaluation
- **Integration Point**: src/crews/stage4_crew.py (_create_reviewer_agent)
- **Rationale**: Editor evaluates Economist voice compliance - needs concrete examples
- **Impact**: 87% → 95%+ GATE 3 pass rate (8 percentage point improvement)

#### ❌ **Research Agent (Stage3Crew) - NOT REQUIRED**
- **Rationale**: Research Agent gathers factual data, not style guidance
- **Current Role**: Verify sources, compile statistics, flag unverified claims
- **No Style Memory Need**: Operates on data, not editorial standards

#### ❌ **Writer Agent (Stage3Crew) - NOT REQUIRED**
- **Rationale**: Writer Agent generates first draft following prompt guidelines
- **Current Role**: Compose article with British spelling, banned phrase avoidance
- **No Style Memory Need**: Style enforcement happens at Editor stage, not writing stage
- **Efficiency**: Keep Writer prompt-driven (fast), let Editor refine with RAG (thorough)
- **Architecture Decision**: Separation of concerns - Writer creates, Editor refines with memory

### Research Phase Tasks (9.5 hours = 3.4 pts → capped at 3 pts)

**Task 1.1: Vector Database Evaluation** (2h, P0)
- Objective: Compare ChromaDB vs FAISS vs Pinecone
- Research Questions: Latency (<500ms?), storage (<100MB?), Python integration
- Deliverable: `docs/research/VECTOR_DB_COMPARISON.md`
- Recommendation: ChromaDB (lightweight, Python-native, persistent)

**Task 1.2: Embeddings Pipeline Design** (2h, P0)
- Objective: Design archived/*.md → embeddings → ChromaDB pipeline
- Research Questions: OpenAI ada-002 semantic accuracy, preprocessing, relevance threshold (0.7?)
- Deliverable: `docs/research/EMBEDDINGS_PIPELINE_DESIGN.md` + prototype
- Prototype: Test embedding quality on 1-2 sample articles

**Task 1.3: CrewAI Tool Pattern Analysis** (1.5h, P0)
- Objective: Understand tool creation/integration for Stage4Crew
- Research Questions: BaseTool vs @tool decorator, tools list config, prompt engineering
- Deliverable: `docs/research/CREWAI_TOOL_INTEGRATION.md` with code examples
- Reference: Examine existing tools in codebase (if any)

**Task 1.4: Editor Integration Strategy** (1.5h, P0)
- Objective: Plan minimal changes to Stage4Crew for tool integration
- Research Questions: Editor backstory enhancement, GATE 3 tool calling, graceful degradation
- Deliverable: `docs/research/EDITOR_INTEGRATION_PLAN.md` with before/after prompts
- Review: Current stage4_crew.py _create_reviewer_agent() implementation

**Task 1.5: Test Strategy Planning** (1.5h, P1)
- Objective: Define integration test scenarios for RAG validation
- Research Questions: Mock OpenAI API, fixture articles, agent tool calling validation
- Deliverable: `docs/research/RAG_TEST_PLAN.md` with pytest fixtures
- Edge Cases: Empty archive directory, low relevance queries (<0.7)

**Task 1.6: Risk Analysis & Mitigation** (1h, P2)
- Objective: Identify technical risks and mitigation strategies
- Research Areas: Embedding quality, relevance tuning, storage growth, cold start, empty archive
- Deliverable: Risk register in `docs/research/STYLE_MEMORY_RISKS.md`
- Mitigation: Threshold configurability, pre-warming, error handling

### Acceptance Criteria

- [ ] AC1: Vector store retrieves style examples in <500ms (research benchmark completed)
- [ ] AC2: Relevance score >0.7 for top-1 result (embeddings quality validated)
- [ ] AC3: Tool integration pattern documented (CrewAI tool pattern guide created)
- [ ] AC4: Editor prompt enhancement strategy defined (before/after prompts documented)
- [ ] AC5: Test plan with 3+ scenarios (pytest fixtures and mocks designed)

### Dependencies

- archived/ directory (Gold Standard articles - may be empty initially, expect 0-10 articles)
- OpenAI API key (text-embedding-ada-002 access)
- ChromaDB library evaluation (pip install chromadb)
- Stage4Crew Editor Agent (src/crews/stage4_crew.py - exists)

### Definition of Done (Research Phase)

- [ ] All 6 research tasks complete (9.5 hours invested)
- [ ] Vector database recommendation documented (ChromaDB rationale)
- [ ] Embeddings pipeline design with architecture diagram
- [ ] CrewAI tool pattern guide with code examples
- [ ] Editor integration plan with before/after prompts
- [ ] Test plan with fixtures and mocks
- [ ] Risk register with mitigation strategies
- [ ] Research deliverables reviewed by team (technical validation)

---

## Other Sprint 13 Stories (To Be Tasked)

### STORY-005: Shift to Deterministic Backbone (3 pts, P0)

**Status**: Awaiting task file creation  
**Story Goal**: Refactor src/ to use Flow-based state-machine orchestration  
**Key Changes**:
- Create src/economist_agents/flow.py with @start/@listen decorators
- Integrate Stage3Crew/Stage4Crew with Flow orchestration
- Deprecate WORKFLOW_SEQUENCE dict (keep as fallback)
- Add integration tests for Flow end-to-end

**Next Step**: Create `tasks/STORY-005-flow-orchestration.md`

### STORY-007: Implement ROI Telemetry Hook (3 pts, P2)

**Status**: Awaiting task file creation  
**Story Goal**: Automated logging of token costs vs human-hour value  
**Key Changes**:
- Design execution_roi.json schema (similar to agent_metrics.json)
- Create src/telemetry/roi_tracker.py middleware
- Instrument agent LLM calls in scripts/agent_registry.py
- Calculate ROI metrics (token costs, human-hour equivalent, efficiency multiplier)

**Next Step**: Create `tasks/STORY-007-roi-telemetry.md`

---

## Sprint Execution Strategy

### Parallel Execution Model

Sprint 13 designed for **3 parallel tracks** (assuming 2-3 developers available):

**Track 1: Architecture Foundation (STORY-005)** - P0, Blocking for Tracks 2-3
- Developer: Architect/Senior Dev
- Focus: Flow-based orchestration, Stage3/Stage4 integration
- Duration: Days 1-3 (Front-loaded)
- Risk: Breaking changes (mitigated by integration tests, WORKFLOW_SEQUENCE fallback)

**Track 2: Quality Enhancement (STORY-006 Research)** - P1, Soft Dependency on Track 1
- Developer: Developer Agent (Research Specialist)
- Focus: RAG system research, tool pattern analysis, Editor integration design
- Duration: Days 1-3 (Parallel with Track 1)
- Risk: Research paralysis (mitigated by time-boxing to 9.5 hours)

**Track 3: Observability (STORY-007)** - P2, No Dependencies
- Developer: DevOps/Backend Dev
- Focus: Telemetry middleware, token cost tracking, ROI dashboard
- Duration: Days 2-5 (Can start after Track 1 kickoff)
- Risk: Performance overhead (mitigated by async logging, <10ms target)

### Daily Standup Questions

**Day 1** (Monday):
- Track 1: Flow architecture created? Basic @start/@listen compiling?
- Track 2: Vector DB comparison started? ChromaDB benchmarks running?
- Track 3: execution_roi.json schema designed?

**Day 2** (Tuesday):
- Track 1: Stage3Crew integrated with Flow? Writer→Editor transitions working?
- Track 2: Embeddings pipeline design complete? OpenAI ada-002 prototype tested?
- Track 3: roi_tracker.py middleware created? LLM instrumentation working?

**Day 3** (Wednesday):
- Track 1: Stage4Crew router implemented? Quality gate routing functional?
- Track 2: CrewAI tool pattern analysis complete? Editor integration plan drafted?
- Track 3: Token cost calculation accurate within 1%?

**Day 4** (Thursday):
- Track 1: Integration tests passing? FLOW_ARCHITECTURE.md drafted?
- Track 2: Test plan complete? Risk analysis finished?
- Track 3: ROI multiplier calculated? Dashboard queries working?

**Day 5** (Friday):
- All Tracks: Code reviews complete? Documentation merged? Retrospective prep?

### Success Metrics

**Sprint Completion Criteria**:
- 9/9 story points delivered (STORY-005, 006 research, 007)
- 0 regressions (existing functionality preserved)
- Quality gates maintained (Editor ≥87% baseline, no test failures)
- All DoD criteria met (tests passing, docs updated, code reviewed)

**Quality Targets**:
- **STORY-005**: Flow orchestration operational, 3+ integration tests passing
- **STORY-006**: Research complete, 6/6 deliverables produced, implementation-ready
- **STORY-007**: execution_roi.json logging token costs, ±1% accuracy

**Business Impact** (Sprint 13):
- **Reliability**: Flow foundation laid (eliminates WORKFLOW_SEQUENCE brittleness)
- **Quality**: Style memory research complete (enables 87%→95% Editor improvement)
- **Visibility**: ROI telemetry operational (measurable efficiency claims)

---

## Risks & Mitigation

### Sprint-Level Risks

**Risk 1: Flow Learning Curve**
- **Probability**: Medium
- **Impact**: High (blocks STORY-006/007 if delayed)
- **Mitigation**: Comprehensive FLOW_ARCHITECTURE.md docs, reference crewai examples, keep WORKFLOW_SEQUENCE fallback

**Risk 2: Empty Archive Directory**
- **Probability**: High (archived/ may have 0-10 articles initially)
- **Impact**: Low (RAG research proceeds with mock data)
- **Mitigation**: Graceful degradation design, tool returns empty results, documented in research

**Risk 3: Parallel Track Coordination**
- **Probability**: Medium
- **Impact**: Medium (merge conflicts, integration issues)
- **Mitigation**: Daily standups, clear Track 1/2/3 separation, frequent git pulls

**Risk 4: Research Scope Creep (STORY-006)**
- **Probability**: Medium
- **Impact**: Medium (research never finishes, delays implementation)
- **Mitigation**: Time-box to 9.5 hours, 6 deliverables defined, "good enough" research standard

### Technical Debt

**Accumulated Debt** (From Previous Sprints):
- WORKFLOW_SEQUENCE dict deprecation (addressed in STORY-005)
- No style memory for Editor (addressed in STORY-006)
- Anecdotal ROI claims (addressed in STORY-007)

**New Debt Created** (Sprint 13):
- Flow architecture may need refinement (accept for MVP, iterate later)
- RAG relevance tuning ongoing (0.7 threshold configurable, revisit after data collection)

---

## Sprint Ceremonies

### Sprint Planning (Monday 9am) ✅ COMPLETE
- **Duration**: 2 hours
- **Attendees**: Scrum Master, Product Owner, Development Team
- **Outcomes**: 
  - Sprint 13 backlog finalized (9 story points committed)
  - STORY-006 task file created (tasks/STORY-006-style-memory-rag.md)
  - Agent skills analysis complete (Editor only, not Writer/Research)
  - Parallel execution tracks defined

### Daily Standups (10am daily)
- **Format**: What did I do? What will I do? Any blockers?
- **Track 1 (STORY-005)**: Flow architecture progress
- **Track 2 (STORY-006)**: Research deliverables status
- **Track 3 (STORY-007)**: Telemetry integration progress

### Sprint Review (Friday 3pm)
- **Duration**: 1 hour
- **Demo**:
  - Track 1: Flow orchestration live demo (Stage3→Stage4 via @start/@listen)
  - Track 2: Research findings presentation (vector DB recommendation, tool pattern guide)
  - Track 3: ROI dashboard prototype (execution_roi.json viewer)

### Sprint Retrospective (Friday 4pm)
- **Duration**: 1 hour
- **Topics**:
  - What went well? (Parallel tracks, research time-boxing)
  - What needs improvement? (Track coordination, documentation completeness)
  - Action items for Sprint 14

---

## Definition of Ready (Sprint 13)

**For STORY-005 (Flow Orchestration)**:
- [x] Story written with clear goal (Flow-based state-machine orchestration)
- [x] Acceptance criteria defined (5 AC total)
- [x] Dependencies identified (CrewAI Flow library, Stage3/Stage4 crews)
- [x] Story points estimated (3 points = 9.5 hours)
- [x] Priority set (P0 - Architectural foundation)
- [ ] Task file created (PENDING - to be created by Scrum Master)

**For STORY-006 (Style Memory RAG)**:
- [x] Story written with clear goal (Vector store with Gold Standard articles)
- [x] Acceptance criteria defined (5 AC total)
- [x] Dependencies identified (archived/ directory, OpenAI API, ChromaDB)
- [x] Story points estimated (3 points = 9.5 hours research)
- [x] Priority set (P1 - Quality enhancement)
- [x] Task file created (tasks/STORY-006-style-memory-rag.md) ✅

**For STORY-007 (ROI Telemetry)**:
- [x] Story written with clear goal (Token cost logging and ROI calculation)
- [x] Acceptance criteria defined (5 AC total)
- [x] Dependencies identified (agent_registry.py, model pricing data)
- [x] Story points estimated (3 points = 9 hours)
- [x] Priority set (P2 - Observability)
- [ ] Task file created (PENDING - to be created by Scrum Master)

---

## Next Steps

### Immediate (Sprint 13 Day 1 - Monday)

1. **Create Remaining Task Files** (Scrum Master) - 2 hours
   - [ ] `tasks/STORY-005-flow-orchestration.md` (detailed task breakdown for Track 1)
   - [ ] `tasks/STORY-007-roi-telemetry.md` (detailed task breakdown for Track 3)

2. **Developer Agent: Begin Research Phase** (Track 2) - 2 hours
   - [ ] Kick off Task 1.1: Vector Database Evaluation
   - [ ] Start ChromaDB vs FAISS vs Pinecone benchmarks
   - [ ] Document initial findings in `docs/research/VECTOR_DB_COMPARISON.md`

3. **Architect: Begin Flow Architecture** (Track 1) - 2 hours
   - [ ] Create `src/economist_agents/flow.py` skeleton
   - [ ] Implement basic @start/@listen decorators
   - [ ] Test Flow initialization and state management

4. **DevOps: Design ROI Schema** (Track 3) - 2 hours
   - [ ] Design execution_roi.json schema (similar to agent_metrics.json)
   - [ ] Identify LLM instrumentation points in scripts/agent_registry.py
   - [ ] Research model pricing data sources (OpenAI pricing API)

### Medium-Term (Sprint 13 Week 1)

**Days 1-3**: Parallel execution on all 3 tracks (see Daily Standup Questions above)

**Days 4-5**: Integration, testing, documentation, code reviews

**Friday**: Sprint review, retrospective, Sprint 14 planning prep

---

## Success Definition

**Sprint 13 Successful If**:
- [x] Sprint planning complete (task files created, backlog groomed) ✅
- [ ] STORY-005 complete (Flow operational, integration tests passing)
- [ ] STORY-006 research complete (6/6 deliverables, implementation-ready)
- [ ] STORY-007 complete (execution_roi.json logging, ROI dashboard prototype)
- [ ] 0 regressions (existing functionality preserved)
- [ ] All DoD criteria met (tests, docs, reviews)
- [ ] Team velocity ≥13 story points delivered

**Business Value Delivered**:
- **Foundation**: Deterministic orchestration replaces brittle WORKFLOW_SEQUENCE
- **Readiness**: Style memory research enables Sprint 14 implementation
- **Visibility**: ROI telemetry provides measurable efficiency data for stakeholders

---

**Created**: 2026-01-04  
**Author**: @scrum-master  
**Status**: Sprint 13 Planning Complete - Ready for Kickoff ✅  
**Next Review**: Monday 9am Sprint Planning Meeting
