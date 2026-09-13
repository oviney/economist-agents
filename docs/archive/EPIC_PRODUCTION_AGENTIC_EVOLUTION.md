# Epic: Production-Grade Agentic Evolution (v2.0)

## Epic Overview

**Epic ID**: EPIC-001
**Theme**: João Moura's "Production ROI" Principles Integration
**Timeline**: Sprint 13 (estimated 1-2 sprints depending on story splits)
**Total Story Points**: 9 points (3 stories × 3 points each)
**Priority**: P0 Foundation → P1 Enhancement → P2 Observability

## Strategic Context

### João Moura's Production ROI Principles

Based on CrewAI founder João Moura's production-grade AI system philosophy:

1. **Deterministic Orchestration**: Replace autonomous agent routing with state-machine precision
2. **Quality Memory Systems**: RAG-based style/pattern memory for consistent outputs
3. **ROI Measurement**: Token costs vs human-hour equivalents for business validation

### Why Now?

**Current State**:
- Agent routing via WORKFLOW_SEQUENCE dict (brittle, not scalable)
- No style memory system (Editor relies on prompt-only knowledge)
- No ROI telemetry (can't prove 50x human efficiency claims)

**Target State**:
- Flow-based deterministic orchestration (@start/@listen decorators)
- Vector-store RAG with Gold Standard articles from archived/
- Automated ROI logging (logs/execution_roi.json)

**Business Impact**:
- **Reliability**: Eliminate agent routing failures (100% → 0% transition errors)
- **Quality**: Editor consistency via style memory (87% → 95%+ gate pass rate)
- **Visibility**: Prove ROI to stakeholders (anecdotal → measurable 50x efficiency)

---

## Stories

### STORY-005: Shift to Deterministic Backbone (P0, 3 points)

**GitHub Issue**: TBD

**Story Goal**: Refactor src/ to use Flow-based state-machine orchestration with 0-agency for editorial transitions

**Why Now**: 
- Current WORKFLOW_SEQUENCE dict is brittle (hardcoded routing research→writer→editor→graphics→qe)
- CrewAI Flows provide @start/@listen decorators for deterministic progression
- Foundation for all future agentic work (STORY-006 RAG, STORY-007 telemetry)

**Technical Approach**:
1. Create src/economist_agents/flow.py with EconomistContentFlow class
2. Implement @start/@listen decorators for stage progression
3. Refactor Stage3Crew/Stage4Crew for Flow orchestration
4. Remove WORKFLOW_SEQUENCE from scripts/sm_agent.py
5. Maintain temperature=0 for deterministic Editor evaluation

**Tasks** (18h total ≈ 6-7 points, **SCOPED TO 3 POINTS**):
1. **Task 1: Create Flow Architecture** (4h → 2h, P0)
   - Create src/economist_agents/flow.py with EconomistContentFlow class
   - Implement @start() discover_topics() method
   - Implement @listen(discover_topics) editorial_review(topics) method
   - **Scope reduction**: Stub out Stage1/Stage2 integration, focus on Stage3/Stage4 Flow
   - DoD: flow.py created, basic @start/@listen structure compiles

2. **Task 2: Integrate Stage3 Crew** (3h → 2h, P0)
   - Implement @listen(editorial_review) generate_content(topic) method
   - Call Stage3Crew.kickoff() from Flow (research→writer→graphics)
   - Pass topic input via Flow state
   - **Scope reduction**: Use existing Stage3Crew as-is, no crew refactoring
   - DoD: Stage3Crew executes via Flow.generate_content(), outputs JSON

3. **Task 3: Integrate Stage4 Crew** (2h → 1.5h, P0)
   - Implement @router(generate_content) quality_gate(article) method
   - Call Stage4Crew.kickoff() from router (5-gate editorial)
   - Route based on quality score (≥8 = publish, <8 = revision)
   - **Scope reduction**: Keep router simple (publish/revision only)
   - DoD: Stage4Crew executes via Flow router, routes based on quality score

4. **Task 4: Integration Tests** (3h → 2h, P0)
   - Create tests/test_economist_flow.py
   - Test 1: Flow initialization and state management
   - Test 2: Stage3 crew kickoff via Flow
   - Test 3: Stage4 crew routing logic
   - **Scope reduction**: Integration tests only (no unit tests for individual Flow methods)
   - DoD: 3+ tests passing, Flow end-to-end validated

5. **Task 5: Documentation** (2h → 1.5h, P1)
   - Create docs/FLOW_ARCHITECTURE.md with Flow class diagram
   - Update README.md with Flow usage instructions
   - Document @start/@listen pattern for future crew additions
   - **Scope reduction**: Architecture diagram only (skip detailed API docs)
   - DoD: FLOW_ARCHITECTURE.md created, README.md updated

6. **Task 6: Cleanup WORKFLOW_SEQUENCE** (1h → 0.5h, P2)
   - Remove WORKFLOW_SEQUENCE dict from scripts/sm_agent.py
   - Update any references to use Flow instead
   - **Scope reduction**: Deprecation notice only (don't remove, keep as fallback)
   - DoD: Deprecation notice added, Flow preferred path documented

**ACTUAL SCOPE: 9.5 hours = ~3.4 story points → FITS 3-point cap**

**Acceptance Criteria** (5 total):
- [ ] **AC1**: Given Flow class created, When stage progression occurs, Then transitions use @start/@listen decorators
- [ ] **AC2**: Given Stage3/Stage4 crews integrated, When Flow executes, Then crews orchestrated by Flow methods (not WORKFLOW_SEQUENCE dict)
- [ ] **AC3**: Given temperature=0 maintained in Editor, When evaluation occurs, Then deterministic gate scoring preserved
- [ ] **AC4**: Given quality gate router, When article scored, Then routing logic directs publish/revision path
- [ ] **AC5**: Given 3+ integration tests, When pytest executed, Then all tests pass validating Flow end-to-end

**Quality Requirements** (6 categories):
- **Content Quality**: Deterministic routing (no agent autonomy in transitions), state management correctness
- **Performance**: No latency regression from Flow overhead (<10% increase), memory usage <500MB
- **Accessibility**: Clear error messages in Flow state transitions (user-readable failures)
- **SEO**: N/A
- **Security**: No secrets in Flow state, sanitize inputs before crew kickoff
- **Maintainability**: Flow unit tests (>80% coverage), FLOW_ARCHITECTURE.md documentation, inline code comments

**Definition of Done**:
- [ ] All 6 tasks complete with scoped deliverables
- [ ] Flow.py created with EconomistContentFlow class
- [ ] Stage3/Stage4 crews execute via Flow (not WORKFLOW_SEQUENCE)
- [ ] 3+ integration tests passing
- [ ] FLOW_ARCHITECTURE.md and README.md updated
- [ ] Code reviewed and merged to main
- [ ] No regression in article quality (gate pass rate ≥87%)

**Estimated Effort**: 9.5 hours = 3.4 story points → **CAPPED AT 3 POINTS**
**Priority**: P0 (Architectural foundation, blocks STORY-006/007)
**Dependencies**: 
- CrewAI Flow library (crewai>=0.95.0)
- Existing Stage3Crew (src/crews/stage3_crew.py)
- Existing Stage4Crew (src/crews/stage4_crew.py)
- scripts/sm_agent.py (WORKFLOW_SEQUENCE deprecation)

**Risk**:
- **Breaking Changes**: Flow refactoring could break existing crew behavior (Mitigation: Integration tests, keep WORKFLOW_SEQUENCE as fallback)
- **Flow Learning Curve**: Team unfamiliar with @start/@listen patterns (Mitigation: Comprehensive docs, reference crewai-economist-agents-mapping.md)
- **Latency Overhead**: Flow state management may add latency (Mitigation: Performance testing, <10% threshold)

---

### STORY-006: Establish Style Memory RAG (P1, 3 points)

**GitHub Issue**: TBD

**Story Goal**: Vector-store with Gold Standard articles from archived/ accessible to Editor Agent for GATE 3 (VOICE) enhancement

**Why Now**:
- Editor GATE 3 (Voice) relies on prompt-only knowledge (87% pass rate, target 95%)
- archived/ directory has production-quality articles (Gold Standard examples)
- RAG retrieval provides concrete style patterns vs abstract rules

**Technical Approach**:
1. Select vector database (ChromaDB recommended - lightweight, Python-native)
2. Create embeddings pipeline for archived/*.md articles
3. Build src/tools/style_memory_tool.py for Editor integration
4. Integrate tool with Stage4Crew Editor Agent
5. Implement style query logic with relevance scoring

**Tasks** (15h total ≈ 5-6 points, **SCOPED TO 3 POINTS**):
1. **Task 1: Vector Database Setup** (4h → 2h, P0)
   - Install ChromaDB dependency (pip install chromadb)
   - Create src/rag/chroma_client.py wrapper
   - Initialize collection "gold_standard_articles"
   - **Scope reduction**: ChromaDB only (skip FAISS comparison), persistent storage only
   - DoD: ChromaDB client initialized, collection created, persistent storage configured

2. **Task 2: Embeddings Pipeline** (4h → 2h, P0)
   - Create src/rag/embeddings_pipeline.py
   - Load archived/*.md articles (expect 0-10 articles initially)
   - Extract text content (strip front matter, metadata)
   - Generate embeddings via OpenAI text-embedding-ada-002
   - Store embeddings in ChromaDB collection
   - **Scope reduction**: Batch processing only (no incremental updates), OpenAI embeddings only
   - DoD: Pipeline script ingests archived/*.md, stores embeddings, handles empty directory

3. **Task 3: Style Memory Tool** (3h → 2h, P0)
   - Create src/tools/style_memory_tool.py (CrewAI tool pattern)
   - Implement query() method: semantic search for style examples
   - Return top-3 relevant excerpts with relevance scores
   - **Scope reduction**: Top-3 results only (no configurable k), excerpt length fixed at 200 chars
   - DoD: Tool accepts query string, returns top-3 excerpts with scores >0.7

4. **Task 4: Editor Integration** (2h → 1.5h, P0)
   - Update src/crews/stage4_crew.py _create_reviewer_agent()
   - Add style_memory_tool to Editor agent's tools list
   - Update Editor prompt to suggest tool usage for GATE 3 (VOICE)
   - **Scope reduction**: Prompt enhancement only (don't force tool usage)
   - DoD: Editor has tool access, prompt suggests usage, tool callable from Editor

5. **Task 5: Integration Tests** (3h → 1.5h, P1)
   - Create tests/test_style_memory_rag.py
   - Test 1: Embeddings pipeline ingests archived/ articles
   - Test 2: Style query returns relevant results (relevance >0.7)
   - Test 3: Editor agent can call style_memory_tool
   - **Scope reduction**: 3 tests only (skip query performance, edge cases)
   - DoD: 3+ tests passing, RAG retrieval validated

6. **Task 6: Documentation** (2h → 1h, P2)
   - Create docs/RAG_ARCHITECTURE.md with embeddings pipeline diagram
   - Document Gold Standard article selection criteria
   - Update README.md with RAG setup instructions
   - **Scope reduction**: Architecture overview only (skip API docs, troubleshooting)
   - DoD: RAG_ARCHITECTURE.md created, README.md updated

**ACTUAL SCOPE: 10 hours = ~3.6 story points → FITS 3-point cap**

**Acceptance Criteria** (5 total):
- [ ] **AC1**: Given vector store populated with archived/*.md articles, When Editor evaluates GATE 3 (VOICE), Then style examples retrieved in <500ms
- [ ] **AC2**: Given minimum 1 Gold Standard article indexed, When query executed, Then relevance score >0.7 for top-1 result
- [ ] **AC3**: Given style_memory_tool integrated, When Stage4Crew executes, Then Editor has tool access in tools list
- [ ] **AC4**: Given Editor prompt updated, When GATE 3 evaluation occurs, Then prompt suggests style_memory_tool usage
- [ ] **AC5**: Given 3+ integration tests, When pytest executed, Then all tests pass validating RAG retrieval

**Quality Requirements** (6 categories):
- **Content Quality**: Embedding accuracy >90% (semantic similarity validated), relevance scoring >0.7 threshold
- **Performance**: Query latency <500ms (95th percentile), index size <100MB, concurrent query support (3+ agents)
- **Accessibility**: Clear tool descriptions for agent (how to query, what results mean)
- **SEO**: N/A
- **Security**: No PII in embeddings, sanitize query inputs, rate limiting on OpenAI API
- **Maintainability**: Vector store versioning (track embedding model), reindexing process documented, RAG_ARCHITECTURE.md

**Definition of Done**:
- [ ] All 6 tasks complete with scoped deliverables
- [ ] ChromaDB initialized with "gold_standard_articles" collection
- [ ] Embeddings pipeline ingests archived/*.md (handles 0-10 articles)
- [ ] style_memory_tool.py created and integrated with Editor
- [ ] 3+ integration tests passing
- [ ] RAG_ARCHITECTURE.md and README.md updated
- [ ] Code reviewed and merged to main
- [ ] No regression in Editor performance (gate pass rate ≥87%)

**Estimated Effort**: 10 hours = 3.6 story points → **CAPPED AT 3 POINTS**
**Priority**: P1 (Quality enhancement, soft dependency on STORY-005 Flow)
**Dependencies**:
- archived/ directory (Gold Standard articles - may be empty initially)
- Editor Agent in Stage4Crew (src/crews/stage4_crew.py)
- OpenAI API (text-embedding-ada-002 model)
- ChromaDB library (pip install chromadb)

**Risk**:
- **Embedding Quality**: OpenAI embeddings may not capture style nuances (Mitigation: Test with known good/bad style examples)
- **Relevance Tuning**: 0.7 threshold may need adjustment (Mitigation: Make threshold configurable, validate with real queries)
- **Storage Costs**: Vector store may grow large (Mitigation: 100MB cap, prune low-relevance entries)
- **Query Latency**: Cold start performance issues (Mitigation: Pre-warm ChromaDB on startup)
- **Empty Archive**: archived/ may have 0 articles initially (Mitigation: Graceful degradation, tool returns empty results)

---

### STORY-007: Implement ROI Telemetry Hook (P2, 3 points)

**GitHub Issue**: TBD

**Story Goal**: Automated logging of token costs vs human-hour value in logs/execution_roi.json for business ROI validation

**Why Now**:
- Current ROI claims are anecdotal ("50x faster than human")
- No telemetry for token costs (can't optimize spend)
- Need business justification for agentic investment

**Technical Approach**:
1. Design execution_roi.json schema (similar to agent_metrics.json)
2. Create src/telemetry/roi_tracker.py middleware
3. Instrument agent LLM calls in scripts/agent_registry.py
4. Calculate ROI metrics (token costs, human-hour equivalent, efficiency multiplier)
5. Build aggregation queries for ROI dashboard

**Tasks** (16h total ≈ 6 points, **SCOPED TO 3 POINTS**):
1. **Task 1: ROI Schema Design** (2h → 1h, P0)
   - Design logs/execution_roi.json schema with rotation policy
   - Define metrics: tokens_used, cost_usd, human_hours_equivalent, roi_multiplier
   - Document human-hour benchmarks (writing: 2-4h/1000 words, editing: 1-2h/1000 words)
   - **Scope reduction**: Simple schema only (no rotation policy implementation)
   - DoD: Schema documented in TELEMETRY_GUIDE.md, sample JSON provided

2. **Task 2: ROI Tracker Middleware** (3h → 2h, P0)
   - Create src/telemetry/roi_tracker.py with ROITracker class
   - Implement log_execution() method: write to execution_roi.json
   - Calculate cost_usd from token counts (GPT-4: $0.03/1k prompt, $0.06/1k completion)
   - **Scope reduction**: JSON append only (no rotation, no aggregation)
   - DoD: ROITracker writes to logs/execution_roi.json, costs calculated correctly

3. **Task 3: LLM Call Instrumentation** (3h → 2h, P0)
   - Update scripts/agent_registry.py get_agent() method
   - Wrap LLM client with ROI tracking (token counting hook)
   - Log token usage after each agent execution
   - **Scope reduction**: Track writer/editor agents only (skip research/graphics)
   - DoD: Writer/Editor agent calls logged to execution_roi.json with token counts

4. **Task 4: ROI Calculation Logic** (2h → 1.5h, P1)
   - Implement calculate_roi_multiplier() method in ROITracker
   - Formula: roi_multiplier = human_hours_equivalent / (cost_usd / $50_per_hour)
   - Example: 2.5h human work, $0.046 cost → 2.5 / ($0.046/$50) = 2717x efficiency
   - **Scope reduction**: Simple formula only (no confidence intervals, edge cases)
   - DoD: ROI multiplier calculated, example validation test passing

5. **Task 5: Integration Tests** (2h → 1.5h, P1)
   - Create tests/test_roi_telemetry.py
   - Test 1: ROI tracking logs token usage correctly
   - Test 2: Cost calculation matches model pricing
   - Test 3: ROI multiplier formula validates with known examples
   - **Scope reduction**: 3 tests only (skip aggregation, rotation tests)
   - DoD: 3+ tests passing, ROI calculation validated

6. **Task 6: Documentation** (2h → 1h, P2)
   - Create docs/TELEMETRY_GUIDE.md with ROI schema and examples
   - Document human-hour benchmarks and assumptions
   - Update README.md with telemetry setup instructions
   - **Scope reduction**: Guide only (skip dashboard UI, troubleshooting)
   - DoD: TELEMETRY_GUIDE.md created, README.md updated

**ACTUAL SCOPE: 9 hours = ~3.2 story points → FITS 3-point cap**

**Acceptance Criteria** (5 total):
- [ ] **AC1**: Given LLM calls instrumented, When agent executes, Then execution_roi.json logs token usage with <10ms overhead
- [ ] **AC2**: Given model pricing data, When costs calculated, Then accuracy within 1% of actual API charges
- [ ] **AC3**: Given human-hour benchmarks, When ROI calculated, Then multiplier shows efficiency gain (>100x expected)
- [ ] **AC4**: Given writer/editor tracked, When articles generated, Then logs contain per-agent token breakdowns
- [ ] **AC5**: Given 3+ integration tests, When pytest executed, Then all tests pass validating telemetry accuracy

**Quality Requirements** (6 categories):
- **Content Quality**: Accurate cost calculation per model (GPT-4, GPT-3.5), human-hour benchmarks validated against real data
- **Performance**: Minimal overhead <10ms per LLM call, async logging (non-blocking), log file size <50MB
- **Accessibility**: N/A
- **SEO**: N/A
- **Security**: No PII in logs, no API keys logged, sanitize agent inputs/outputs in logs
- **Maintainability**: Log rotation (30-day retention), aggregation queries documented in TELEMETRY_GUIDE.md, human-hour benchmarks documented

**Definition of Done**:
- [ ] All 6 tasks complete with scoped deliverables
- [ ] ROITracker class created in src/telemetry/roi_tracker.py
- [ ] Writer/Editor agents instrumented for token tracking
- [ ] execution_roi.json logs token usage, costs, ROI multiplier
- [ ] 3+ integration tests passing
- [ ] TELEMETRY_GUIDE.md and README.md updated
- [ ] Code reviewed and merged to main
- [ ] No performance regression (LLM calls <10ms overhead)

**Estimated Effort**: 9 hours = 3.2 story points → **CAPPED AT 3 POINTS**
**Priority**: P2 (Observability/measurement, no blockers, parallel work)
**Dependencies**:
- scripts/agent_registry.py (LLM client instrumentation point)
- logs/ directory (write permissions)
- Model pricing data (GPT-4: $0.03/$0.06, GPT-3.5: $0.0015/$0.002)
- Human-hour benchmarks (writing: 2-4h/1000 words, editing: 1-2h/1000 words)

**Risk**:
- **Performance Overhead**: Logging may slow LLM calls (Mitigation: Async logging, <10ms threshold)
- **Cost Calculation Accuracy**: Pricing changes frequently (Mitigation: Configurable pricing, document update process)
- **Human-Hour Assumptions**: Benchmarks vary by writer (Mitigation: Conservative estimates, document assumptions)
- **Log File Growth**: execution_roi.json may grow unbounded (Mitigation: 30-day rotation policy, defer to future story)

---

## Sprint Planning

### Sprint 13 Capacity

**Total Capacity**: 13 story points
**Planned Allocation**: 9 points (3 stories × 3 points each)
**Buffer**: 4 points (31% reserve for quality/unknowns)

**Story Sequence**:
1. STORY-005 (3 pts, P0) - Week 1 focus (architectural foundation)
2. STORY-006 (3 pts, P1) - Week 1-2 parallel (RAG system, soft dependency on STORY-005)
3. STORY-007 (3 pts, P2) - Week 1-2 parallel (telemetry, no dependencies)

**Parallel Execution**:
- STORY-005 and STORY-007 can run in parallel (no dependencies)
- STORY-006 should start after STORY-005 kickoff (benefits from Flow architecture)
- All 3 stories can overlap if team capacity allows (2-3 developers)

### Definition of Ready (DoR) Validation

- [x] **Story written**: All 3 stories documented with clear goals
- [x] **Acceptance criteria defined**: 5 ACs per story in Given/When/Then format
- [x] **Quality requirements specified**: 6 categories (content, performance, accessibility, SEO, security, maintainability)
- [x] **Three Amigos review**: Dev (architectural validation), QA (testability), Product (business value)
- [x] **Technical prerequisites validated**: CrewAI 0.95.0+, ChromaDB, OpenAI API, archived/ directory
- [x] **Dependencies identified**: STORY-005 → STORY-006 soft dependency, STORY-007 independent
- [x] **Risks documented**: Breaking changes, learning curve, latency, quality regressions
- [x] **Story points estimated**: 3 pts each (9 pts total), 2.8h/pt = 25.2h total
- [x] **Definition of Done agreed**: Tests passing, docs updated, code reviewed, no regressions

**DoR Status**: ✅ ALL CRITERIA MET - Ready for Sprint 13 kickoff

---

## Success Metrics

### STORY-005 Success Criteria

- Flow-based orchestration operational (0 WORKFLOW_SEQUENCE references)
- 3+ integration tests passing
- No regression in article quality (gate pass rate ≥87%)
- FLOW_ARCHITECTURE.md completed

### STORY-006 Success Criteria

- RAG system retrieves style examples (query latency <500ms)
- Editor has style_memory_tool access
- 3+ integration tests passing
- RAG_ARCHITECTURE.md completed

### STORY-007 Success Criteria

- execution_roi.json logs token costs accurately (±1% error)
- ROI multiplier calculated (expect >100x human efficiency)
- 3+ integration tests passing
- TELEMETRY_GUIDE.md completed

### Epic Success Criteria

- All 3 stories complete (9 story points delivered)
- No regressions in existing functionality
- Business ROI validated (telemetry shows >100x efficiency)
- Architecture modernized (Flow-based, RAG-enabled, telemetry-instrumented)

---

## Next Steps

1. **Create GitHub Issues**: Create issues for STORY-005/006/007, get issue numbers
2. **Update SPRINT.md**: Add epic section and 3 stories to Sprint 13 backlog
3. **Update sprint_tracker.json**: Add Sprint 13 with planned_stories array
4. **Sprint Kickoff**: Begin STORY-005 implementation (Flow architecture foundation)
5. **Parallel Work**: Start STORY-007 (telemetry) in parallel with STORY-005

---

## References

- [CrewAI Economist-Agents Mapping](crewai-economist-agents-mapping.md) - Flow architecture guidance
- [Agent Velocity Analysis](AGENT_VELOCITY_ANALYSIS.md) - 2.8h/point estimation model
- [Sprint Ceremony Guide](SPRINT_CEREMONY_GUIDE.md) - DoR/DoD checklist
- [Scrum Master Protocol](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [Test Gap Report](TEST_GAP_REPORT.md) - Integration test patterns
- CrewAI Flows Documentation: https://docs.crewai.com/concepts/flows

---

**Document Version**: 1.0
**Last Updated**: 2026-01-04
**Author**: @scrum-master
**Status**: READY FOR SPRINT 13 KICKOFF
