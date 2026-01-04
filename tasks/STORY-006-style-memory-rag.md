# STORY-006: Establish Style Memory RAG

**Type**: Technical Enhancement  
**Priority**: P1 (High)  
**Story Points**: 3  
**Sprint**: Sprint 13  
**Created**: 2026-01-04  
**Status**: Ready for Development  
**Epic**: EPIC-001 Production-Grade Agentic Evolution

## User Story

As an Editor Agent, I need access to Gold Standard style examples via RAG retrieval so that I can improve GATE 3 (Voice) consistency from 87% to 95%+ pass rate by referencing concrete published articles instead of relying on prompt-only knowledge.

## Context

**Current State**:
- Editor GATE 3 (Voice) pass rate: 87% (target: 95%)
- Editor relies on prompt-only knowledge for style enforcement
- archived/ directory contains production-quality Gold Standard articles (0-10 articles initially)
- No mechanism to retrieve relevant style examples during editing

**Target State**:
- Vector store (ChromaDB) populated with archived/*.md embeddings
- style_memory_tool.py CrewAI tool for semantic search
- Editor Agent (Stage4Crew) has tool access
- Query latency <500ms, relevance score >0.7 for top results

**Business Impact**:
- **Quality**: Editor consistency improvement (87% → 95%+ GATE 3 pass rate)
- **Maintainability**: Concrete style patterns vs abstract rules
- **Scalability**: Grows knowledge base as more Gold Standard articles added

## Agents Requiring Style Memory Skills

Based on crew analysis (src/crews/stage3_crew.py, stage4_crew.py):

### ✅ **Editor Agent** (Stage4Crew) - PRIMARY BENEFICIARY
- **Location**: src/crews/stage4_crew.py (_create_reviewer_agent)
- **Current State**: No tools configured, prompt-only style knowledge
- **Required Skill**: style_memory_tool.py for GATE 3 (Voice) evaluation
- **Integration Point**: Add to agent's tools list in _create_reviewer_agent()
- **Prompt Enhancement**: Update backstory to suggest tool usage for style validation

### ❌ **Research Agent** (Stage3Crew) - NOT REQUIRED
- **Rationale**: Research Agent gathers factual data, not style guidance
- **Current Role**: Verify sources, compile statistics, flag unverified claims
- **No Style Memory Need**: Operates on data, not editorial standards

### ❌ **Writer Agent** (Stage3Crew) - NOT REQUIRED
- **Rationale**: Writer Agent generates first draft following prompt guidelines
- **Current Role**: Compose article with British spelling, banned phrase avoidance
- **No Style Memory Need**: Style enforcement happens at Editor stage, not writing stage
- **Efficiency**: Keep Writer prompt-driven (fast), let Editor refine with RAG (thorough)

## Acceptance Criteria

- [ ] **AC1**: Given vector store populated with archived/*.md articles, When Editor evaluates GATE 3 (VOICE), Then style examples retrieved in <500ms
  - **Developer Research Phase**: Evaluate ChromaDB vs FAISS vs Pinecone for query latency
  - **Research Deliverable**: Benchmark report comparing vector databases (latency, memory, setup complexity)
  - **Decision Criteria**: <500ms p95 latency, <100MB storage, Python-native preferred

- [ ] **AC2**: Given minimum 1 Gold Standard article indexed, When query executed, Then relevance score >0.7 for top-1 result
  - **Developer Research Phase**: Test OpenAI text-embedding-ada-002 semantic similarity accuracy
  - **Research Deliverable**: Embeddings quality report with style query examples (good/bad voice samples)
  - **Decision Criteria**: >0.7 relevance for known-good style matches, <0.3 for known-bad

- [ ] **AC3**: Given style_memory_tool integrated, When Stage4Crew executes, Then Editor has tool access in tools list
  - **Developer Research Phase**: Analyze CrewAI tool pattern (BaseTool vs @tool decorator)
  - **Research Deliverable**: Tool integration guide with code examples for Stage4Crew
  - **Decision Criteria**: Tool callable from agent, proper error handling, JSON-serializable results

- [ ] **AC4**: Given Editor prompt updated, When GATE 3 evaluation occurs, Then prompt suggests style_memory_tool usage
  - **Developer Research Phase**: Review existing Editor backstory for enhancement opportunities
  - **Research Deliverable**: Prompt engineering recommendations (what to add/remove)
  - **Decision Criteria**: Tool usage suggested but not forced, graceful degradation if tool unavailable

- [ ] **AC5**: Given 3+ integration tests, When pytest executed, Then all tests pass validating RAG retrieval
  - **Developer Research Phase**: Identify test scenarios (embeddings pipeline, query retrieval, agent integration)
  - **Research Deliverable**: Test plan with fixtures, mocks, and assertion strategies
  - **Decision Criteria**: 3+ tests covering happy path, edge cases (empty archive, low relevance)

## Technical Approach

### Phase 1: Research & Design (Developer Agent - THIS TASK FILE)

**Task 1.1: Vector Database Evaluation (2h, P0)**
- **Objective**: Select optimal vector store for style memory use case
- **Research Questions**:
  1. ChromaDB vs FAISS vs Pinecone - latency benchmarks (<500ms target)?
  2. Storage footprint for 10-100 Gold Standard articles (<100MB target)?
  3. Python integration complexity (pip install simplicity)?
  4. Persistent storage strategy (local filesystem vs cloud)?
- **Deliverable**: `docs/research/VECTOR_DB_COMPARISON.md` with recommendation
- **Decision**: ChromaDB recommended (lightweight, Python-native, persistent)

**Task 1.2: Embeddings Pipeline Design (2h, P0)**
- **Objective**: Design pipeline for archived/*.md → embeddings → ChromaDB
- **Research Questions**:
  1. OpenAI text-embedding-ada-002 - semantic similarity accuracy for style?
  2. Preprocessing strategy (strip front matter, extract core content)?
  3. Batch vs incremental indexing (Gold Standard corpus is static initially)?
  4. Relevance score threshold (0.7 sufficient for style matching)?
- **Deliverable**: `docs/research/EMBEDDINGS_PIPELINE_DESIGN.md` with architecture diagram
- **Prototype**: Simple script testing embedding quality on 1-2 sample articles

**Task 1.3: CrewAI Tool Pattern Analysis (1.5h, P0)**
- **Objective**: Understand how to create/integrate tools with Stage4Crew Editor
- **Research Questions**:
  1. BaseTool vs @tool decorator - which for style_memory_tool.py?
  2. Agent tools list configuration in _create_reviewer_agent()?
  3. Prompt engineering - how to suggest tool usage without forcing?
  4. Error handling - tool failure fallback strategy?
- **Deliverable**: `docs/research/CREWAI_TOOL_INTEGRATION.md` with code examples
- **Reference**: Examine existing tools in codebase (if any)

**Task 1.4: Editor Integration Strategy (1.5h, P0)**
- **Objective**: Plan minimal changes to Stage4Crew for tool integration
- **Research Questions**:
  1. Current Editor backstory - where to add style_memory_tool reference?
  2. GATE 3 (VOICE) evaluation - when should tool be called?
  3. Prompt modification - explicit "Use style_memory_tool.query('...')" instruction?
  4. Graceful degradation - Editor must function if RAG unavailable?
- **Deliverable**: `docs/research/EDITOR_INTEGRATION_PLAN.md` with before/after prompts
- **Review**: Current stage4_crew.py _create_reviewer_agent() implementation

**Task 1.5: Test Strategy Planning (1.5h, P1)**
- **Objective**: Define integration test scenarios for RAG validation
- **Research Questions**:
  1. Test 1: Embeddings pipeline - how to mock OpenAI API?
  2. Test 2: Style query retrieval - fixture articles for known-good results?
  3. Test 3: Agent tool calling - how to validate Editor uses tool correctly?
  4. Edge cases: Empty archive directory, low relevance queries (<0.7)?
- **Deliverable**: `docs/research/RAG_TEST_PLAN.md` with pytest fixtures
- **Dependencies**: ChromaDB test client, mock OpenAI responses

**Task 1.6: Risk Analysis & Mitigation (1h, P2)**
- **Objective**: Identify technical risks and mitigation strategies
- **Research Areas**:
  1. Embedding quality - what if style nuances not captured?
  2. Relevance tuning - 0.7 threshold too strict/loose?
  3. Storage growth - vector store exceeding 100MB cap?
  4. Cold start latency - ChromaDB slow on first query?
  5. Empty archive - graceful degradation strategy?
- **Deliverable**: Risk register in `docs/research/STYLE_MEMORY_RISKS.md`
- **Mitigation**: Threshold configurability, pre-warming, error handling

**TOTAL RESEARCH EFFORT: 9.5 hours ≈ 3.4 story points → FITS 3-point cap**

### Phase 2: Implementation (Future Sprint)

(To be planned after research phase complete - separate task file will be created)

1. Task 2.1: Vector Database Setup (src/rag/chroma_client.py)
2. Task 2.2: Embeddings Pipeline (src/rag/embeddings_pipeline.py)
3. Task 2.3: Style Memory Tool (src/tools/style_memory_tool.py)
4. Task 2.4: Editor Integration (src/crews/stage4_crew.py)
5. Task 2.5: Integration Tests (tests/test_style_memory_rag.py)
6. Task 2.6: Documentation (docs/RAG_ARCHITECTURE.md)

## Quality Requirements

### Content Quality
- **Embedding Accuracy**: >90% semantic similarity for known-good style matches
- **Relevance Threshold**: >0.7 for top-1 result, validates tool usefulness
- **Tool Output**: JSON-serializable excerpts with scores (CrewAI requirement)

### Performance
- **Query Latency**: <500ms p95 (Editor blocking on tool call)
- **Index Size**: <100MB for 10-100 articles (storage constraint)
- **Concurrent Queries**: Support 3+ agents if multi-agent future workflow

### Accessibility
- **Tool Description**: Clear docstring for agent (how to query, interpret results)
- **Error Messages**: Human-readable failures (no API stack traces)

### Security
- **PII Protection**: No personally identifiable info in embeddings
- **Input Sanitization**: Query strings sanitized before OpenAI API
- **Rate Limiting**: OpenAI API calls throttled (cost control)

### Maintainability
- **Vector Store Versioning**: Track embedding model (text-embedding-ada-002 version)
- **Reindexing Process**: Documented in RAG_ARCHITECTURE.md (when to rebuild index)
- **Test Coverage**: >80% for RAG module (src/rag/*, src/tools/style_memory_tool.py)

## Definition of Done

### Research Phase (THIS SPRINT - Sprint 13)
- [ ] All 6 research tasks complete (9.5 hours)
- [ ] Vector database recommendation documented (ChromaDB rationale)
- [ ] Embeddings pipeline design with architecture diagram
- [ ] CrewAI tool pattern guide with code examples
- [ ] Editor integration plan with before/after prompts
- [ ] Test plan with fixtures and mocks
- [ ] Risk register with mitigation strategies
- [ ] Research deliverables reviewed by team (technical validation)

### Implementation Phase (FUTURE SPRINT - To Be Planned)
- [ ] ChromaDB client initialized (src/rag/chroma_client.py)
- [ ] Embeddings pipeline functional (handles 0-10 archived/ articles)
- [ ] style_memory_tool.py created (CrewAI tool pattern)
- [ ] Editor agent integrated (Stage4Crew._create_reviewer_agent)
- [ ] 3+ integration tests passing
- [ ] RAG_ARCHITECTURE.md documentation complete
- [ ] Code reviewed and merged to main
- [ ] No regression in Editor performance (≥87% baseline maintained)

## Estimated Effort

**Research Phase**: 9.5 hours = 3.4 story points → **CAPPED AT 3 POINTS**  
**Implementation Phase**: ~10 hours (separate story, future sprint)  
**Total Epic Effort**: ~20 hours (split across 2 sprints for manageability)

## Priority & Dependencies

**Priority**: P1 (High - Quality enhancement, soft dependency on STORY-005 Flow)

**Dependencies**:
- archived/ directory (Gold Standard articles - may be empty initially, 0-10 expected)
- Editor Agent in Stage4Crew (src/crews/stage4_crew.py - exists)
- OpenAI API key (text-embedding-ada-002 access - assumed available)
- ChromaDB library (pip install chromadb - research will validate choice)

**Blockers**: None - research phase can start immediately

## Risks & Mitigation

### Technical Risks
1. **Embedding Quality**: OpenAI embeddings may not capture style nuances
   - **Mitigation**: Test with known good/bad style examples, validate >0.7 relevance
   - **Research Task**: Task 1.2 includes prototype testing embedding quality

2. **Relevance Tuning**: 0.7 threshold may be too strict or too loose
   - **Mitigation**: Make threshold configurable, validate with real queries
   - **Research Task**: Task 1.6 covers threshold sensitivity analysis

3. **Storage Costs**: Vector store may grow beyond 100MB cap
   - **Mitigation**: Prune low-relevance entries, implement archival strategy
   - **Research Task**: Task 1.1 benchmarks storage footprint

4. **Query Latency**: Cold start performance issues with ChromaDB
   - **Mitigation**: Pre-warm vector store on application startup
   - **Research Task**: Task 1.1 includes latency benchmarking (cold/warm)

5. **Empty Archive**: archived/ may have 0 articles initially
   - **Mitigation**: Graceful degradation, tool returns empty results with clear message
   - **Research Task**: Task 1.5 includes edge case testing (empty directory)

### Process Risks
6. **Scope Creep**: RAG system could expand beyond Editor (Writer, Research agents)
   - **Mitigation**: Hard scoping to Editor GATE 3 only, document future expansion
   - **Decision**: Research confirms Writer/Research agents NOT in scope

7. **Research Paralysis**: Too much analysis, delayed implementation
   - **Mitigation**: Time-box research to 9.5 hours, deliver "good enough" recommendations
   - **Quality Gate**: Research complete = 6 deliverables produced, not perfection

## Success Metrics

### Research Phase Success
- **Research Completeness**: 6/6 deliverables produced (100%)
- **Decision Clarity**: Vector DB recommendation clear (ChromaDB yes/no)
- **Implementation Readiness**: Implementation phase can start without additional research
- **Team Confidence**: Technical validation meeting confirms research findings

### Implementation Phase Success (Future Sprint)
- **Editor Improvement**: GATE 3 (Voice) pass rate 87% → 95%+ (8 percentage point gain)
- **Query Performance**: <500ms p95 latency achieved (ChromaDB benchmark)
- **Test Coverage**: 3+ integration tests passing, >80% code coverage
- **Production Readiness**: No regression, graceful degradation validated

## Notes

**Gold Standard Article Selection Criteria** (for future reference):
- Production-quality articles from archived/
- Exemplifies Economist voice (British spelling, sharp wit, banned phrase avoidance)
- Proper structure (strong opening, sourced evidence, logical flow, strong ending)
- Chart integration best practices (if applicable)
- Ideal corpus size: 10-100 articles (balance between diversity and index size)

**Future Enhancements** (Post-MVP):
- Writer Agent style memory (optional - research confirmed NOT required for Sprint 13)
- Multi-language embeddings (if international Economist style needed)
- Active learning (feedback loop from Editor GATE 3 failures → improve corpus)
- Style drift detection (monitor embedding distribution over time)

---

**Created**: 2026-01-04  
**Author**: @scrum-master  
**Reviewed**: Pending team validation  
**Status**: Ready for Developer Agent research phase kickoff
