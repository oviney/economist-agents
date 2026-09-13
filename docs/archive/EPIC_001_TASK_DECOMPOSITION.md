# EPIC-001: Production-Grade Agentic Evolution - Task Decomposition

**Epic Version**: 2.0
**Created**: 2026-01-04
**Status**: Ready for Sprint 13 Kickoff
**Total Story Points**: 9 (3 stories × 3 points each)

---

## Executive Summary

This document decomposes **EPIC-001: Production-Grade Agentic Evolution** into 18 detailed tasks (6 per story) with cross-references to existing validation schemas. The epic modernizes the economist-agents pipeline with:

1. **Deterministic Orchestration** (Flow-based state machines) - STORY-005
2. **Quality Memory Systems** (RAG with Gold Standard articles) - STORY-006
3. **ROI Measurement** (Token cost telemetry) - STORY-007

**Key Finding**: ROI Telemetry schema aligns with existing validation patterns. Recommend adding `schemas/execution_roi_schema.json` following JSON Schema Draft-07 format.

---

## STORY-005: Shift to Deterministic Backbone (3 points, P0)

**Goal**: Replace sequential orchestration with Flow-based state-machine architecture for predictable multi-agent coordination.

**Business Value**: Eliminates unpredictable agent interactions, enables complex workflows (parallel generation, conditional routing), reduces debugging time.

### Task Breakdown

#### Task 1: Flow Architecture Design (1.5h, P0)
**Description**: Design state transition map and create architectural documentation.

**Deliverables**:
- `docs/FLOW_ARCHITECTURE.md` - Flow architecture with state diagram
- State transition map: IDLE → RESEARCH → WRITE → EDIT → GRAPHICS → PUBLISH
- Conditional routing rules (e.g., "if gate fail → rework")
- Exit conditions and error handling

**Acceptance Criteria**:
- State diagram shows all agent transitions
- Conditional routing documented (3+ scenarios)
- Error handling strategy defined
- Documentation peer-reviewed

**Effort**: 1.5 hours
**Priority**: P0 (foundation for implementation)
**Dependencies**: None
**Risks**: Design may need iteration after Task 2 implementation

---

#### Task 2: Create Flow Class (2h, P0)
**Description**: Implement `ContentGenerationFlow` class in `src/economist_agents/flow.py`.

**Deliverables**:
- `src/economist_agents/flow.py` - Flow class with @start/@listen decorators
- `@start` decorator on entry point (research phase)
- `@listen` decorators for state transitions
- State tracking and logging

**Code Pattern**:
```python
from crewai.flow.flow import Flow, listen, start

class ContentGenerationFlow(Flow):
    @start()
    def research_phase(self):
        # Research agent execution
        return ResearchOutput(...)
    
    @listen(research_phase)
    def writing_phase(self, research_output):
        # Writer agent execution
        return WriterOutput(...)
    
    @listen(writing_phase)
    def editing_phase(self, writer_output):
        # Editor agent execution
        return EditorOutput(...)
```

**Acceptance Criteria**:
- Flow class imports without errors
- @start/@listen decorators correctly placed
- State transitions log to console
- Type hints for all methods

**Effort**: 2 hours
**Priority**: P0 (core implementation)
**Dependencies**: Task 1 (design complete)
**Risks**: CrewAI Flow API may differ from documentation

---

#### Task 3: Migrate economist_agent.py (3h, P0)
**Description**: Refactor `scripts/economist_agent.py` to use Flow instead of sequential orchestration.

**Deliverables**:
- Refactored `generate_economist_post()` to call Flow.kickoff()
- Remove WORKFLOW_SEQUENCE dictionary references
- Update imports to use ContentGenerationFlow
- Preserve all existing functionality (governance, metrics, output)

**Code Changes**:
```python
# OLD: Sequential orchestration
research = run_research_agent(client, topic, talking_points)
draft = run_writer_agent(client, topic, research, date_str)
edited = run_editor_agent(client, draft)

# NEW: Flow-based orchestration
flow = ContentGenerationFlow()
result = flow.kickoff(topic=topic, talking_points=talking_points)
```

**Acceptance Criteria**:
- economist_agent.py uses Flow.kickoff()
- No WORKFLOW_SEQUENCE references remain
- All existing tests pass
- Output format unchanged (markdown + charts)

**Effort**: 3 hours
**Priority**: P0 (integration)
**Dependencies**: Task 2 (Flow class complete)
**Risks**: Governance hooks may need refactoring

---

#### Task 4: State Transition Tests (1.5h, P0)
**Description**: Create integration tests for Flow state transitions.

**Deliverables**:
- `tests/test_flow_integration.py` - 3+ test cases
- Test 1: Happy path (research → write → edit → graphics)
- Test 2: Editor rejection (edit → write rework)
- Test 3: Research failure (error handling)

**Test Pattern**:
```python
def test_flow_happy_path():
    flow = ContentGenerationFlow()
    result = flow.kickoff(topic="Test Topic")
    assert result.article_path.exists()
    assert result.chart_path is not None
```

**Acceptance Criteria**:
- 3+ integration tests passing
- All state transitions covered
- Error handling validated
- Tests run in <30 seconds

**Effort**: 1.5 hours
**Priority**: P0 (validation)
**Dependencies**: Task 3 (migration complete)
**Risks**: Mocking Flow execution may be complex

---

#### Task 5: Regression Testing (1h, P0)
**Description**: Validate no regressions in article quality or agent metrics.

**Deliverables**:
- Generate 3 test articles using Flow architecture
- Compare quality metrics with baseline (gate pass rate ≥87%)
- Validate chart embedding, categories field, frontmatter
- Document any differences

**Quality Metrics**:
- Editor gate pass rate: ≥87% (current baseline)
- Chart embedding rate: 100%
- Category field present: 100%
- Frontmatter validation: 100%

**Acceptance Criteria**:
- 3 test articles generated successfully
- Quality metrics match or exceed baseline
- No defect prevention patterns triggered
- Metrics documented in FLOW_ARCHITECTURE.md

**Effort**: 1 hour
**Priority**: P0 (quality gate)
**Dependencies**: Task 4 (tests passing)
**Risks**: Quality may regress during migration

---

#### Task 6: Documentation (0.5h, P2)
**Description**: Update README.md and create migration guide.

**Deliverables**:
- Update README.md with Flow architecture notes
- Add troubleshooting section to FLOW_ARCHITECTURE.md
- Document breaking changes (if any)
- Add usage examples

**Content**:
- "How to run Flow-based generation"
- "Debugging state transitions"
- "Extending Flow with new states"
- "Migration from sequential orchestration"

**Acceptance Criteria**:
- README.md updated
- FLOW_ARCHITECTURE.md contains troubleshooting
- Examples executable
- Documentation peer-reviewed

**Effort**: 0.5 hours
**Priority**: P2 (polish)
**Dependencies**: Task 5 (regression testing complete)
**Risks**: None

---

**STORY-005 Total**: 9.5 hours → Capped at 3 story points (3 × 2.8h = 8.4h)

---

## STORY-006: Establish Style Memory RAG (3 points, P1)

**Goal**: Build RAG system with Gold Standard articles for writer/editor style reference.

**Business Value**: Improves article consistency, reduces rework from style violations, enables writer to learn from best examples.

### Task Breakdown

#### Task 1: ChromaDB Setup (1.5h, P0)
**Description**: Initialize ChromaDB vector store and test connection.

**Deliverables**:
- `src/rag/chroma_store.py` - ChromaDB initialization and CRUD operations
- Test connection with sample data
- Document collection schema and metadata
- Configure persistent storage (`data/chromadb/`)

**Code Pattern**:
```python
import chromadb
from chromadb.config import Settings

def init_chroma():
    client = chromadb.Client(Settings(
        persist_directory="./data/chromadb",
        anonymized_telemetry=False
    ))
    collection = client.get_or_create_collection("economist_style")
    return collection
```

**Acceptance Criteria**:
- ChromaDB initializes without errors
- Collection created with "economist_style" name
- Sample document inserted and retrieved
- Persistent storage working (data survives restart)

**Effort**: 1.5 hours
**Priority**: P0 (foundation)
**Dependencies**: None (ChromaDB in requirements.txt)
**Risks**: Version compatibility with ChromaDB API

---

#### Task 2: Article Ingestion Pipeline (2h, P0)
**Description**: Build pipeline to ingest Gold Standard articles from `archived/` into ChromaDB.

**Deliverables**:
- `scripts/ingest_gold_standard.py` - Ingestion script
- Parse markdown files from archived/ directory
- Extract chunks (300-500 words each)
- Generate embeddings (OpenAI text-embedding-ada-002)
- Store in ChromaDB with metadata

**Metadata Schema**:
```json
{
  "article_title": "Self-Healing Tests: Myth vs Reality",
  "chunk_id": "chunk_0",
  "section": "introduction",
  "word_count": 425,
  "date": "2025-12-31"
}
```

**Acceptance Criteria**:
- Script processes all .md files in archived/
- Chunks extracted (300-500 words each)
- Embeddings generated via OpenAI API
- Metadata preserved (title, date, section)

**Effort**: 2 hours
**Priority**: P0 (data pipeline)
**Dependencies**: Task 1 (ChromaDB setup)
**Risks**: OpenAI API rate limits during bulk ingestion

---

#### Task 3: RAG Query Tool (2.5h, P0)
**Description**: Create CrewAI tool for RAG queries accessible to agents.

**Deliverables**:
- `src/rag/style_memory_tool.py` - CrewAI tool implementation
- Semantic search with similarity threshold (0.7)
- Return top 3 most relevant chunks
- Format results for agent context

**Code Pattern**:
```python
from crewai_tools import tool

@tool("Search style memory")
def search_style_memory(query: str) -> str:
    """
    Searches Gold Standard articles for style examples.
    Args:
        query: Semantic search query (e.g., "opening hooks")
    Returns:
        Top 3 relevant article excerpts
    """
    collection = get_chroma_collection()
    results = collection.query(
        query_texts=[query],
        n_results=3,
        where={"word_count": {"$gte": 300}}
    )
    return format_results(results)
```

**Acceptance Criteria**:
- Tool decorated with @tool
- Query returns top 3 chunks
- Similarity threshold configurable (default 0.7)
- Results formatted with article context

**Effort**: 2.5 hours
**Priority**: P0 (agent integration)
**Dependencies**: Task 2 (articles ingested)
**Risks**: Query latency may exceed 500ms

---

#### Task 4: Agent Integration (2.5h, P0)
**Description**: Add style_memory_tool to Writer and Editor agents.

**Deliverables**:
- Update `agents/writer_agent.py` to include style_memory_tool
- Update `agents/editor_agent.py` to include style_memory_tool
- Update agent prompts to use tool ("Search style_memory for opening examples")
- Test tool execution in agent workflows

**Prompt Enhancement**:
```
You have access to the style_memory_tool which searches Gold Standard
articles for style examples. Use it when:
- Writing opening hooks (search "compelling openings")
- Checking voice consistency (search "Economist tone")
- Finding chart integration examples (search "chart references")
```

**Acceptance Criteria**:
- Writer agent has style_memory_tool access
- Editor agent has style_memory_tool access
- Prompts instruct agents when to use tool
- Tool execution logs show successful queries

**Effort**: 2.5 hours
**Priority**: P0 (integration)
**Dependencies**: Task 3 (tool complete)
**Risks**: Agent prompts may not trigger tool use

---

#### Task 5: RAG Integration Tests (1h, P0)
**Description**: Create tests validating RAG system end-to-end.

**Deliverables**:
- `tests/test_rag_integration.py` - 3+ test cases
- Test 1: Article ingestion (archived/ → ChromaDB)
- Test 2: Semantic search returns relevant chunks
- Test 3: Agent uses style_memory_tool successfully

**Test Pattern**:
```python
def test_rag_semantic_search():
    query = "opening hook examples"
    results = search_style_memory(query)
    assert len(results) == 3
    assert "opening" in results[0].lower()
```

**Acceptance Criteria**:
- 3+ integration tests passing
- Query latency <500ms validated
- Tool execution in agent context tested
- All tests run in <10 seconds

**Effort**: 1 hour
**Priority**: P0 (validation)
**Dependencies**: Task 4 (agent integration complete)
**Risks**: ChromaDB test isolation may need work

---

#### Task 6: Documentation (0.5h, P2)
**Description**: Create RAG_ARCHITECTURE.md with usage guide.

**Deliverables**:
- `docs/RAG_ARCHITECTURE.md` - Architecture and usage guide
- Document ChromaDB schema and metadata
- Add troubleshooting section (embedding errors, query latency)
- Update README.md with RAG setup instructions

**Content**:
- "How to add new Gold Standard articles"
- "Querying the style memory"
- "Metadata schema reference"
- "Performance tuning (chunk size, similarity threshold)"

**Acceptance Criteria**:
- RAG_ARCHITECTURE.md created
- README.md updated with setup instructions
- Examples executable
- Documentation peer-reviewed

**Effort**: 0.5 hours
**Priority**: P2 (polish)
**Dependencies**: Task 5 (tests passing)
**Risks**: None

---

**STORY-006 Total**: 10 hours → Capped at 3 story points (3 × 2.8h = 8.4h)

---

## STORY-007: Implement ROI Telemetry Hook (3 points, P2)

**Goal**: Add token cost tracking to measure human-hour ROI of agent operations.

**Business Value**: Quantifies efficiency gains, justifies investment in agentic architecture, identifies optimization opportunities.

### Task Breakdown

#### Task 1: ROI Schema Design (1h, P0)
**Description**: Design `logs/execution_roi.json` schema with rotation policy.

**Schema Structure**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Execution ROI Schema",
  "description": "Token cost tracking and ROI calculation for agent executions",
  "type": "object",
  "required": ["executions", "metadata"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["schema_version", "created", "last_updated"],
      "properties": {
        "schema_version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
        "created": {"type": "string", "format": "date-time"},
        "last_updated": {"type": "string", "format": "date-time"},
        "rotation_policy": {"type": "string", "enum": ["30-day", "90-day", "manual"]}
      }
    },
    "executions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["execution_id", "timestamp", "topic", "agents", "totals"],
        "properties": {
          "execution_id": {"type": "string", "format": "uuid"},
          "timestamp": {"type": "string", "format": "date-time"},
          "topic": {"type": "string", "minLength": 5},
          "agents": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["agent_name", "tokens_used", "model"],
              "properties": {
                "agent_name": {"type": "string", "enum": ["research", "writer", "editor", "graphics"]},
                "tokens_used": {
                  "type": "object",
                  "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
                  "properties": {
                    "prompt_tokens": {"type": "integer", "minimum": 0},
                    "completion_tokens": {"type": "integer", "minimum": 0},
                    "total_tokens": {"type": "integer", "minimum": 0}
                  }
                },
                "model": {"type": "string", "enum": ["gpt-4", "gpt-3.5-turbo"]},
                "cost_usd": {"type": "number", "minimum": 0}
              }
            }
          },
          "totals": {
            "type": "object",
            "required": ["total_tokens", "total_cost_usd", "human_hours_equivalent", "roi_multiplier"],
            "properties": {
              "total_tokens": {"type": "integer", "minimum": 0},
              "total_cost_usd": {"type": "number", "minimum": 0},
              "human_hours_equivalent": {"type": "number", "minimum": 0},
              "roi_multiplier": {"type": "number", "minimum": 0},
              "time_saved_hours": {"type": "number", "minimum": 0}
            }
          }
        }
      }
    }
  }
}
```

**Acceptance Criteria**:
- Schema follows JSON Schema Draft-07 format
- All required fields defined with types
- Enum constraints for agent_name and model
- Pattern validation for schema_version
- UUID format for execution_id
- Date-time format for timestamps

**Effort**: 1 hour
**Priority**: P0 (foundation)
**Dependencies**: None
**Risks**: Schema may need iteration after Task 2 implementation

**Schema Alignment Notes**:
- ✅ Follows same JSON Schema Draft-07 pattern as `content_queue_schema.json`
- ✅ Uses `required` arrays for mandatory fields
- ✅ Type constraints match validation patterns
- ✅ Nested objects with clear hierarchy (similar to `board_decision_schema.json`)
- ✅ Format validators (date-time, uuid) align with existing patterns
- ✅ Enum constraints for controlled vocabularies

**Recommended Actions**:
1. Create `schemas/execution_roi_schema.json` with above structure
2. Add validation function to `schemas/validate_schemas.py`:
   ```python
   def validate_execution_roi(file_path: Path = None) -> bool:
       """Validate logs/execution_roi.json"""
       if file_path is None:
           file_path = Path(__file__).parent.parent / "logs" / "execution_roi.json"
       schema_path = Path(__file__).parent / "execution_roi_schema.json"
       is_valid, errors = validate_json_file(file_path, schema_path)
       # ... validation logic
   ```
3. Update `validate_all()` to include ROI telemetry validation

---

#### Task 2: ROITracker Class (2.5h, P0)
**Description**: Create `src/telemetry/roi_tracker.py` with ROI calculation logic.

**Deliverables**:
- `src/telemetry/roi_tracker.py` - ROITracker class
- Methods: start_execution(), log_agent_tokens(), calculate_roi(), save_to_json()
- Model pricing data (GPT-4: $0.03/$0.06, GPT-3.5: $0.0015/$0.002 per 1k tokens)
- Human-hour benchmarks (writing: 2-4h/1000 words, editing: 1-2h/1000 words)

**Code Pattern**:
```python
class ROITracker:
    MODEL_PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002}
    }
    
    HUMAN_BENCHMARKS = {
        "writing": 3.0,  # hours per 1000 words
        "editing": 1.5   # hours per 1000 words
    }
    
    def start_execution(self, topic: str):
        self.execution_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.agents = []
    
    def log_agent_tokens(self, agent_name: str, tokens: dict, model: str):
        cost = self._calculate_cost(tokens, model)
        self.agents.append({
            "agent_name": agent_name,
            "tokens_used": tokens,
            "model": model,
            "cost_usd": cost
        })
    
    def calculate_roi(self, word_count: int) -> dict:
        total_cost = sum(a["cost_usd"] for a in self.agents)
        human_hours = (word_count / 1000) * (self.HUMAN_BENCHMARKS["writing"] + self.HUMAN_BENCHMARKS["editing"])
        human_cost = human_hours * 50  # $50/hour baseline
        roi_multiplier = human_cost / total_cost if total_cost > 0 else 0
        return {
            "total_tokens": sum(a["tokens_used"]["total_tokens"] for a in self.agents),
            "total_cost_usd": total_cost,
            "human_hours_equivalent": human_hours,
            "roi_multiplier": roi_multiplier,
            "time_saved_hours": human_hours
        }
```

**Acceptance Criteria**:
- ROITracker class initialized with model pricing
- log_agent_tokens() records prompt/completion tokens
- calculate_roi() returns ROI multiplier
- save_to_json() writes to logs/execution_roi.json

**Effort**: 2.5 hours
**Priority**: P0 (core implementation)
**Dependencies**: Task 1 (schema design)
**Risks**: Token counting API may not expose detailed breakdowns

---

#### Task 3: Instrument Writer/Editor (2h, P0)
**Description**: Add ROI tracking calls to Writer and Editor agents.

**Deliverables**:
- Update `agents/writer_agent.py` with ROITracker integration
- Update `agents/editor_agent.py` with ROITracker integration
- Log tokens after each LLM call
- Calculate word count from outputs

**Code Changes**:
```python
# In writer_agent.py
from src.telemetry.roi_tracker import ROITracker

def run_writer_agent(client, topic, research, date_str, tracker=None):
    if tracker:
        tracker.start_execution(topic)
    
    response = call_llm(client, prompt, msg, max_tokens=4000)
    
    if tracker:
        tracker.log_agent_tokens(
            agent_name="writer",
            tokens=response.usage,  # {prompt_tokens, completion_tokens, total_tokens}
            model=client.model
        )
    
    return draft
```

**Acceptance Criteria**:
- Writer agent logs token usage
- Editor agent logs token usage
- Tokens captured after each LLM call
- No performance regression (<10ms overhead)

**Effort**: 2 hours
**Priority**: P0 (integration)
**Dependencies**: Task 2 (ROITracker complete)
**Risks**: LLM client may not expose token usage metadata

---

#### Task 4: Integration with economist_agent.py (1.5h, P0)
**Description**: Wire ROITracker into main orchestration flow.

**Deliverables**:
- Update `generate_economist_post()` to initialize ROITracker
- Pass tracker to all agent calls
- Call calculate_roi() at end of execution
- Save to logs/execution_roi.json with rotation

**Code Pattern**:
```python
def generate_economist_post(topic, ...):
    tracker = ROITracker()
    tracker.start_execution(topic)
    
    research = run_research_agent(client, topic, talking_points, tracker)
    draft = run_writer_agent(client, topic, research, date_str, tracker)
    edited = run_editor_agent(client, draft, tracker)
    
    roi_data = tracker.calculate_roi(word_count=len(edited.split()))
    tracker.save_to_json("logs/execution_roi.json")
    
    print(f"ROI: {roi_data['roi_multiplier']:.1f}x human efficiency")
    return result
```

**Acceptance Criteria**:
- ROITracker initialized in generate_economist_post()
- Tracker passed to all agent calls
- ROI calculated at end of execution
- execution_roi.json updated with new execution

**Effort**: 1.5 hours
**Priority**: P0 (orchestration)
**Dependencies**: Task 3 (agents instrumented)
**Risks**: Flow-based orchestration (STORY-005) may complicate integration

---

#### Task 5: ROI Telemetry Tests (1.5h, P0)
**Description**: Create tests validating ROI tracking accuracy.

**Deliverables**:
- `tests/test_roi_telemetry.py` - 3+ test cases
- Test 1: ROI tracking logs token usage correctly
- Test 2: Cost calculation matches model pricing (±1% error)
- Test 3: ROI multiplier formula validates with known examples

**Test Pattern**:
```python
def test_roi_calculation():
    tracker = ROITracker()
    tracker.start_execution("Test Topic")
    
    # Simulate writer tokens
    tracker.log_agent_tokens("writer", {
        "prompt_tokens": 1000,
        "completion_tokens": 2000,
        "total_tokens": 3000
    }, "gpt-4")
    
    roi_data = tracker.calculate_roi(word_count=1000)
    
    # Expected: 3h human writing @ $50/hr = $150
    # Cost: (1000 * 0.03 + 2000 * 0.06) / 1000 = $0.15
    # ROI: $150 / $0.15 = 1000x
    assert roi_data["roi_multiplier"] > 900  # Allow 10% variance
```

**Acceptance Criteria**:
- 3+ tests passing
- Cost calculation validated (±1% error)
- ROI multiplier formula tested with known examples
- Tests run in <5 seconds

**Effort**: 1.5 hours
**Priority**: P0 (validation)
**Dependencies**: Task 4 (integration complete)
**Risks**: Human-hour benchmarks may vary significantly

---

#### Task 6: Documentation (1h, P2)
**Description**: Create TELEMETRY_GUIDE.md with ROI schema and usage examples.

**Deliverables**:
- `docs/TELEMETRY_GUIDE.md` - Telemetry guide
- Document ROI schema structure
- Add human-hour benchmarks and assumptions
- Update README.md with telemetry setup instructions
- Add example queries (aggregation, filtering)

**Content**:
- "Understanding ROI Calculation"
- "Human-Hour Benchmarks" (writing, editing, research)
- "Model Pricing Data" (GPT-4, GPT-3.5)
- "Querying execution_roi.json" (jq examples)
- "Troubleshooting" (token counting issues, cost discrepancies)

**Acceptance Criteria**:
- TELEMETRY_GUIDE.md created
- README.md updated with setup instructions
- Examples executable (jq queries work)
- Documentation peer-reviewed

**Effort**: 1 hour
**Priority**: P2 (polish)
**Dependencies**: Task 5 (tests passing)
**Risks**: None

---

**STORY-007 Total**: 9 hours → Capped at 3 story points (3 × 2.8h = 8.4h)

---

## Schema Alignment Analysis

### Existing Schema Patterns

The economist-agents project uses **JSON Schema Draft-07** with the following patterns:

1. **Type Validation**: All fields have explicit `type` constraints (string, integer, number, boolean, array, object)
2. **Required Fields**: `required` arrays enforce mandatory fields
3. **Nested Objects**: Complex structures use nested objects with their own `properties` and `required` arrays
4. **Format Validators**: Use `format` for date-time, email, uri validation
5. **Constraints**: Minimum/maximum for numbers, minLength/maxLength for strings, minItems for arrays
6. **Enums**: Controlled vocabularies use `enum` constraints

**Examples from existing schemas**:
- `content_queue_schema.json`: Nested `scores` object with 5 required integer fields (1-5 range)
- `board_decision_schema.json`: Array items with nested `votes` array, weighted_score with min/max constraints

### ROI Telemetry Schema Alignment

The proposed `execution_roi_schema.json` follows all existing patterns:

✅ **Type Validation**: All fields have explicit types
✅ **Required Fields**: `executions`, `metadata`, `agents`, `totals` all required
✅ **Nested Objects**: `metadata`, `agents`, `totals` follow nested pattern
✅ **Format Validators**: Uses `date-time` for timestamps, `uuid` for execution_id
✅ **Constraints**: Integer minimums (≥0 for tokens), pattern validation for schema_version
✅ **Enums**: `agent_name` restricted to ["research", "writer", "editor", "graphics"], `model` to ["gpt-4", "gpt-3.5-turbo"]

**Key Alignment**:
- Schema structure mirrors `board_decision_schema.json` (top-level metadata + array of items)
- Nested objects with required fields match `content_queue_schema.json` pattern
- Validation functions in `validate_schemas.py` can use same `validate_json_file()` method

### Recommended Schema Enhancements

**Recommendation 1**: Add `execution_roi_schema.json` to `schemas/` directory

**Recommendation 2**: Extend `validate_schemas.py` with ROI validation:
```python
def validate_execution_roi(file_path: Path = None) -> bool:
    """Validate logs/execution_roi.json"""
    if file_path is None:
        file_path = Path(__file__).parent.parent / "logs" / "execution_roi.json"
    
    schema_path = Path(__file__).parent / "execution_roi_schema.json"
    
    is_valid, errors = validate_json_file(file_path, schema_path)
    
    if is_valid:
        print(f"✅ {file_path.name} is valid")
    else:
        print(f"❌ {file_path.name} validation failed:")
        for error in errors:
            print(f"   • {error}")
    
    return is_valid
```

**Recommendation 3**: Update `validate_all()` to include ROI telemetry:
```python
def validate_all():
    """Validate all pipeline intermediate files"""
    results = []
    
    results.append(("content_queue.json", validate_content_queue()))
    results.append(("board_decision.json", validate_board_decision()))
    results.append(("execution_roi.json", validate_execution_roi()))  # NEW
    
    # ... existing code
```

**Recommendation 4**: Add schema validation to pre-commit hooks:
```bash
# .git/hooks/pre-commit
python3 schemas/validate_schemas.py --all
```

---

## Sprint Planning

### Sprint 13 Execution Strategy

**Capacity**: 13 story points
**Planned**: 9 story points (3 stories × 3 points)
**Buffer**: 4 points (31% reserve for quality/unknowns)

**Parallel Execution**:
- **Week 1**: STORY-005 (P0) + STORY-007 (P2) in parallel
  - STORY-005: Flow architecture (no dependencies)
  - STORY-007: ROI telemetry (no dependencies)
  - Both can start immediately

- **Week 1-2**: STORY-006 (P1) after STORY-005 kickoff
  - Soft dependency: Benefits from Flow architecture
  - Can overlap with STORY-005 Tasks 4-6
  - Can run fully in parallel with STORY-007

**Risk Mitigation**:
- STORY-005 is P0 (highest priority) - start first
- STORY-007 has no dependencies - ideal for parallel work
- STORY-006 soft dependency allows flexible scheduling

### Definition of Ready (DoR) Checklist

- [x] **Story written**: All 3 stories documented with clear goals
- [x] **Acceptance criteria defined**: 5 ACs per story in Given/When/Then format
- [x] **Quality requirements specified**: 6 categories per story
- [x] **Three Amigos review**: Dev, QA, Product perspectives documented
- [x] **Technical prerequisites validated**: CrewAI 0.95.0+, ChromaDB, OpenAI API, archived/ directory
- [x] **Dependencies identified**: STORY-005 → STORY-006 soft dependency, STORY-007 independent
- [x] **Risks documented**: Breaking changes, learning curve, latency, quality regressions
- [x] **Story points estimated**: 3 pts each (9 pts total)
- [x] **Definition of Done agreed**: Tests passing, docs updated, code reviewed, no regressions
- [x] **Schema alignment validated**: ROI telemetry follows existing JSON Schema patterns

**DoR Status**: ✅ **ALL CRITERIA MET** - Ready for Sprint 13 kickoff

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
- **Schema alignment validated**: execution_roi_schema.json follows existing patterns

### Epic Success Criteria
- All 3 stories complete (9 story points delivered)
- No regressions in existing functionality
- Business ROI validated (telemetry shows >100x efficiency)
- Architecture modernized (Flow-based, RAG-enabled, telemetry-instrumented)
- **Schema consistency**: All pipeline outputs follow JSON Schema Draft-07 patterns

---

## Appendix: Task Summary Table

| Story | Task | Effort | Priority | Dependencies | Deliverables |
|-------|------|--------|----------|--------------|--------------|
| **STORY-005** | Task 1: Flow Design | 1.5h | P0 | None | FLOW_ARCHITECTURE.md |
| | Task 2: Flow Class | 2h | P0 | Task 1 | ContentGenerationFlow class |
| | Task 3: Migrate economist_agent | 3h | P0 | Task 2 | Refactored orchestration |
| | Task 4: State Transition Tests | 1.5h | P0 | Task 3 | test_flow_integration.py |
| | Task 5: Regression Testing | 1h | P0 | Task 4 | Quality metrics validation |
| | Task 6: Documentation | 0.5h | P2 | Task 5 | README.md update |
| **STORY-006** | Task 1: ChromaDB Setup | 1.5h | P0 | None | chroma_store.py |
| | Task 2: Article Ingestion | 2h | P0 | Task 1 | ingest_gold_standard.py |
| | Task 3: RAG Query Tool | 2.5h | P0 | Task 2 | style_memory_tool.py |
| | Task 4: Agent Integration | 2.5h | P0 | Task 3 | Updated writer/editor agents |
| | Task 5: RAG Integration Tests | 1h | P0 | Task 4 | test_rag_integration.py |
| | Task 6: Documentation | 0.5h | P2 | Task 5 | RAG_ARCHITECTURE.md |
| **STORY-007** | Task 1: ROI Schema Design | 1h | P0 | None | execution_roi_schema.json |
| | Task 2: ROITracker Class | 2.5h | P0 | Task 1 | roi_tracker.py |
| | Task 3: Instrument Agents | 2h | P0 | Task 2 | Updated writer/editor |
| | Task 4: Integration | 1.5h | P0 | Task 3 | economist_agent.py integration |
| | Task 5: ROI Tests | 1.5h | P0 | Task 4 | test_roi_telemetry.py |
| | Task 6: Documentation | 1h | P2 | Task 5 | TELEMETRY_GUIDE.md |

**Total Tasks**: 18 (6 per story)
**Total Effort**: 28.5 hours (actual) → 9 story points (capped at 3 pts per story)
**Total Story Points**: 9 (3 stories × 3 points)

---

## Next Steps

1. **Create GitHub Issues**: Create issues for STORY-005/006/007, get issue numbers
2. **Create Schema File**: Add `schemas/execution_roi_schema.json` with validated structure
3. **Update Validation Utility**: Extend `schemas/validate_schemas.py` with ROI validation function
4. **Update SPRINT.md**: Add EPIC-001 section and 3 stories to Sprint 13 backlog
5. **Update sprint_tracker.json**: Add Sprint 13 with planned_stories array
6. **Sprint Kickoff**: Begin STORY-005 implementation (Flow architecture foundation)
7. **Parallel Work**: Start STORY-007 (telemetry) in parallel with STORY-005

---

## References

- [EPIC_PRODUCTION_AGENTIC_EVOLUTION.md](./EPIC_PRODUCTION_AGENTIC_EVOLUTION.md) - Full epic definition
- [BACKLOG_SETUP_REPORT.md](../BACKLOG_SETUP_REPORT.md) - Sprint planning and roadmap
- [schemas/content_queue_schema.json](../schemas/content_queue_schema.json) - Example schema pattern
- [schemas/board_decision_schema.json](../schemas/board_decision_schema.json) - Example nested object pattern
- [schemas/validate_schemas.py](../schemas/validate_schemas.py) - Validation utility
- [CrewAI Flows Documentation](https://docs.crewai.com/concepts/flows) - Flow architecture reference
- [AGENT_VELOCITY_ANALYSIS.md](./AGENT_VELOCITY_ANALYSIS.md) - 2.8h/point estimation model

---

**Document Status**: ✅ Complete and Ready for Sprint 13 Kickoff
**Schema Alignment**: ✅ Validated - ROI telemetry follows existing JSON Schema Draft-07 patterns
**Last Updated**: 2026-01-04
**Author**: @po-agent
