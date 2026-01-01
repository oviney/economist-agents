# GitHub Issues - Agentic Architecture Evolution

This file contains all GitHub issues ready to be created in the economist-agents repository. Each issue is formatted for direct copy-paste into GitHub's issue creation form.

---

## Issue #26: Extract Agent Definitions to YAML Configuration

**Labels:** `P1-high`, `type:refactor`, `effort:medium`  
**Milestone:** Phase 1 - Foundation (Q1 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Extract all hardcoded agent prompts and configurations from Python scripts to YAML configuration files. This enables version control of agent tuning, A/B testing, reusability across projects, and non-technical stakeholder participation.

### Context

Currently, agent prompts are hardcoded as Python string constants in:
- `scripts/topic_scout.py`
- `scripts/editorial_board.py` (6 persona agents)
- `scripts/economist_agent.py` (4 content generation agents)

This creates technical debt and limits our ability to iterate on agent behavior without code changes.

### Goals

- [ ] All 11 agents defined in YAML format
- [ ] JSON Schema for validation
- [ ] Agent loader implementation
- [ ] Pre-commit hook for YAML validation
- [ ] Documentation of schema

### Acceptance Criteria

- [ ] YAML schema created: `agents/schema.json`
- [ ] Agent loader implemented: `scripts/agent_loader.py`
- [ ] All 11 agents migrated to `agents/` directory
- [ ] Unit tests pass for agent loading
- [ ] Pre-commit hook validates YAML on commit
- [ ] No behavior changes (output equivalence verified)
- [ ] Documentation updated: `agents/README.md`

### Implementation Plan

**Week 1:**
1. Design YAML schema with required/optional fields
2. Create `AgentConfig` dataclass
3. Implement YAML parser with validation
4. Write unit tests

**Week 2:**
1. Extract editorial board agents (6 files)
2. Extract content generation agents (4 files)  
3. Extract topic scout (1 file)
4. Add pre-commit validation hook
5. Verify output equivalence

### Directory Structure

```
agents/
├── schema.json
├── README.md
├── editorial_board/
│   ├── vp_engineering.yaml
│   ├── senior_qe_lead.yaml
│   ├── data_skeptic.yaml
│   ├── career_climber.yaml
│   ├── economist_editor.yaml
│   └── busy_reader.yaml
├── content_generation/
│   ├── researcher.yaml
│   ├── writer.yaml
│   ├── editor.yaml
│   └── graphics.yaml
└── discovery/
    └── topic_scout.yaml
```

### YAML Schema Example

```yaml
# agents/editorial_board/vp_engineering.yaml
name: "VP of Engineering"
role: "VP of Engineering perspective on QE"
goal: "Evaluate topics for strategic alignment with engineering priorities"
backstory: |
  You lead engineering quality at a large organization.
  You prioritize topics that have broad strategic impact.
system_message: |
  You are voting on quality engineering topics from a VP perspective.
  Score based on strategic alignment, scalability, and business impact.
tools: []
scoring_criteria:
  strategic_alignment: 0-10
  practitioner_value: 0-10
  data_availability: 0-10
metadata:
  version: "1.0"
  created: "2026-01-01"
  author: "oviney"
  category: "editorial_board"
```

### Testing Requirements

- [ ] Unit tests for YAML parsing
- [ ] Unit tests for schema validation
- [ ] Integration tests: load all 11 agents
- [ ] Regression tests: verify output equivalence
- [ ] Edge case tests: malformed YAML, missing fields

### References

- **ADR:** `docs/ADR-001-agent-configuration-extraction.md`
- **Related Issues:** #27 (Agent Registry), #28 (Public Skills Library)
- **Dependencies:** None (foundational change)

### Success Metrics

- Zero schema validation errors
- All agents load in <100ms
- 100% output equivalence with current system
- First A/B test of agent tuning completed within 1 week of completion

---

## Issue #27: Implement Agent Registry Pattern

**Labels:** `P1-high`, `type:architecture`, `effort:medium`  
**Milestone:** Phase 2 - Agent Registry (Q1 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Create a centralized `AgentRegistry` class that provides agent discovery, instantiation, and dependency injection. This enables testing with mock agents, swapping LLM providers per agent, and programmatic agent discovery.

### Context

After extracting agents to YAML (Issue #26), we need a systematic way to:
1. Discover available agents by category
2. Create agent instances with proper dependencies
3. Swap LLM providers (OpenAI ↔ Anthropic) per agent
4. Inject mock agents for testing
5. Load specific agent versions

### Goals

- [ ] Factory pattern for agent creation
- [ ] LLM provider abstraction
- [ ] Agent discovery by category
- [ ] Testability via dependency injection
- [ ] Single source of truth for agent instantiation

### Acceptance Criteria

- [ ] `AgentRegistry` class implemented
- [ ] `LLMProvider` protocol defined
- [ ] OpenAI and Anthropic providers implemented
- [ ] All scripts refactored to use registry
- [ ] Unit tests achieve 100% coverage
- [ ] Integration tests pass
- [ ] Documentation complete

### Implementation Plan

**Week 3:**
1. Create `scripts/agent_registry.py`
2. Implement `_load_agents()` and `get_agent()`
3. Create `LLMProvider` protocol
4. Implement provider classes
5. Write unit tests

**Week 4:**
1. Refactor `editorial_board.py` to use registry
2. Refactor `economist_agent.py` to use registry
3. Refactor `topic_scout.py` to use registry
4. Remove old agent instantiation code
5. Integration testing

### Architecture

```python
# scripts/agent_registry.py
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import yaml

class LLMProvider(Protocol):
    def create_client(self, model: str):
        ...

class AgentRegistry:
    def __init__(self, config_dir: Path, llm_factory: LLMProvider):
        self.config_dir = config_dir
        self.llm_factory = llm_factory
        self._agents: Dict[str, AgentConfig] = {}
        self._load_agents()
    
    def get_agent(self, name: str, model: str = "gpt-4o") -> Agent:
        """Factory method: Create agent instance"""
        ...
    
    def list_agents(self, category: str = None) -> List[str]:
        """Discover available agents"""
        ...
    
    def get_config(self, name: str) -> AgentConfig:
        """Get raw configuration for inspection"""
        ...
```

### Usage Example

```python
# Before (current state)
vp_eng_prompt = """You are VP of Engineering..."""
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(...)

# After (with registry)
registry = AgentRegistry(Path("agents/"), OpenAIProvider())
vp_eng = registry.get_agent("vp_engineering", model="gpt-4o")
response = vp_eng.respond(topic_data)

# List agents by category
board_agents = registry.list_agents(category="editorial_board")
# Returns: ['vp_engineering', 'senior_qe_lead', ...]
```

### Testing Strategy

```python
def test_load_agents_from_yaml(tmp_path):
    """Registry loads all YAML files"""
    (tmp_path / "test.yaml").write_text("""
    name: test_agent
    role: Tester
    ...
    """)
    registry = AgentRegistry(tmp_path, MockLLMProvider())
    assert "test_agent" in registry.list_agents()

def test_provider_swapping():
    """Can swap providers per agent"""
    openai_reg = AgentRegistry(Path("agents/"), OpenAIProvider())
    anthropic_reg = AgentRegistry(Path("agents/"), AnthropicProvider())
    
    agent1 = openai_reg.get_agent("writer")
    agent2 = anthropic_reg.get_agent("writer")
    
    assert type(agent1.llm_client) != type(agent2.llm_client)
```

### References

- **ADR:** `docs/ADR-002-agent-registry-pattern.md`
- **Related Issues:** #26 (YAML Extraction), #29 (MCP Tools)
- **Dependencies:** Issue #26 must be complete

### Success Metrics

- Zero direct agent instantiation in scripts (except registry)
- Can swap LLM provider with 1-line config change
- Agent loading time <50ms per agent
- 100% unit test coverage of registry

---

## Issue #28: Create Public Skills Library

**Labels:** `P2-medium`, `type:enhancement`, `effort:large`  
**Milestone:** Phase 5 - Community (Q2 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Extract generic agent definitions into a public skills library that the QE community can reuse. This establishes thought leadership, enables community contributions, and builds an ecosystem around our agentic approach.

### Context

Our agent definitions (researcher, writer, editor, data analyst) have value beyond our specific use case. By sharing generic versions, we:
1. Help others build similar systems
2. Get community feedback and improvements
3. Establish reputation in agentic AI space
4. Build towards a skills marketplace

### Goals

- [ ] Separate public (generic) from private (custom) agents
- [ ] Document each agent's capabilities and use cases
- [ ] Create contribution guidelines
- [ ] Launch with blog post and social promotion
- [ ] Attract first community contribution

### Acceptance Criteria

- [ ] Directory structure: `skills/public/` and `skills/private/`
- [ ] At least 4 generic agents in public library
- [ ] `skills/README.md` with comprehensive documentation
- [ ] Contribution guidelines (`CONTRIBUTING.md`)
- [ ] Blog post published announcing library
- [ ] First community PR submitted (within 3 months)

### Implementation Plan

**Week 12-13: Library Structure**
1. Create `skills/public/` and `skills/private/` directories
2. Move generic agents to public (researcher, writer, editor, data_analyst)
3. Keep custom personas private (6 editorial board agents)
4. Parameterize public agents (use template variables)
5. Document each agent thoroughly

**Week 14-15: Community Launch**
1. Write blog post for viney.ca
2. Create contribution guidelines
3. Share on social media (LinkedIn, Reddit, CrewAI Discord)
4. Engage with community feedback
5. Update docs based on questions

### Directory Structure

```
skills/
├── README.md                    # Main documentation
├── CONTRIBUTING.md              # How to contribute agents
├── public/                      # Generic, reusable agents
│   ├── researcher.yaml          # Web/API research agent
│   ├── technical_writer.yaml   # Generic technical writer
│   ├── editor.yaml              # Style enforcement agent
│   ├── data_analyst.yaml        # Chart/data visualization
│   └── examples/
│       └── usage_patterns.md
└── private/                     # Custom/proprietary agents
    ├── economist_editor.yaml    # Economist-specific style
    └── qe_board/
        └── *.yaml (6 personas)
```

### Public Agent Example

```yaml
# skills/public/researcher.yaml
name: "Research Agent"
role: "Research Specialist"
goal: "Find authoritative sources and verify information"
backstory: |
  You are an expert researcher who prioritizes recent publications,
  peer-reviewed research, and authoritative industry sources.
  You ALWAYS include source URLs for every claim.
tools:
  - web_search
  - arxiv_search
  - source_verifier
metadata:
  version: "1.0"
  author: "oviney"
  license: "MIT"
  category: "research"
  tags: ["research", "verification", "sources"]
  reusability: "high"
parameters:
  - name: "domain"
    description: "Research domain (e.g., 'quality engineering', 'AI')"
    default: "general"
  - name: "time_horizon"
    description: "How recent sources must be (e.g., '2 years')"
    default: "5 years"
```

### Documentation Requirements

**skills/README.md must include:**
- [ ] Overview of the skills library concept
- [ ] How to use agents in your own projects
- [ ] Agent composition patterns
- [ ] Testing guidelines
- [ ] Contribution process
- [ ] License information (MIT)
- [ ] Examples for common use cases

### Community Engagement Plan

**Blog Post Topics:**
- "Building Reusable AI Agents: A Skills Library Approach"
- "4 Production-Ready Agent Patterns for Content Generation"
- "How to Contribute to Open Source Agent Libraries"

**Promotion Channels:**
- LinkedIn (professional QE audience)
- Reddit: r/MachineLearning, r/LLMDevs, r/QualityEngineering
- CrewAI Discord (#show-and-tell)
- GitHub Topics: `ai-agents`, `multi-agent-systems`, `quality-engineering`

**Success Indicators:**
- 50+ GitHub stars within 3 months
- 5+ community PRs within 6 months
- 1000+ blog post views
- Mentioned in at least one community roundup/newsletter

### References

- **Related Issues:** #26 (YAML Extraction), #27 (Agent Registry)
- **Dependencies:** Issues #26 and #27 must be complete
- **Inspiration:** HuggingFace model hub, LangChain templates

### Testing Requirements

- [ ] Each public agent has example usage
- [ ] Agents work in isolation (no dependencies on private code)
- [ ] Template variables tested and documented
- [ ] Contribution process validated with test PR

---

## Issue #29: Integrate MCP Tools for Research Agents

**Labels:** `P2-medium`, `type:enhancement`, `effort:medium`  
**Milestone:** Phase 3 - Tool Integration (Q1 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Integrate Model Context Protocol (MCP) to give agents access to external tools: web search (Tavily), research papers (ArXiv), and source verification. This enables real-time data access, reduces hallucinations, and improves article quality.

### Context

Current agents rely solely on LLM training data, which leads to:
- Outdated information (knowledge cutoff)
- Hallucinations (no grounding in real data)
- Missing sources (can't verify claims)
- Limited research depth

MCP provides standardized tool integration for:
- Web search engines
- Academic databases
- APIs and data sources
- Custom verification tools

### Goals

- [ ] MCP infrastructure set up
- [ ] Web search operational (Tavily/SerperDev)
- [ ] ArXiv paper search integrated
- [ ] Source verification implemented
- [ ] Tools injected into research agent
- [ ] Governance logs show tool usage

### Acceptance Criteria

- [ ] MCP client installed and configured
- [ ] At least 2 search tools operational
- [ ] Research agent uses web search successfully
- [ ] Editor agent verifies sources automatically
- [ ] All claims in generated articles have source URLs
- [ ] Zero [UNVERIFIED] tags in production articles
- [ ] Tool errors handled gracefully

### Implementation Plan

**Week 5: MCP Setup**
1. Install MCP: `pip install mcp-client`
2. Create `scripts/mcp_tools.py`
3. Configure MCP servers in `.mcp/config.json`
4. Test basic connectivity

**Week 6: Tool Integration**
1. Integrate Tavily search
2. Add SerperDev for Google search
3. Integrate ArXiv API
4. Create tool wrapper classes
5. Add to AgentRegistry

### Architecture

```python
# scripts/mcp_tools.py
from mcp import MCPClient

class WebSearchTool:
    """MCP-powered web search"""
    def __init__(self, provider: str = "tavily"):
        self.client = MCPClient(f"{provider}-search")
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Execute web search and return results"""
        results = self.client.query(query, limit=max_results)
        return [SearchResult(**r) for r in results]

class ArxivSearchTool:
    """Academic paper search via ArXiv API"""
    def __init__(self):
        self.client = MCPClient("arxiv-search")
    
    def find_papers(self, topic: str, max_age_years: int = 2) -> List[Paper]:
        """Find recent papers on topic"""
        results = self.client.query(
            topic=topic,
            published_after=f"{datetime.now().year - max_age_years}-01-01"
        )
        return [Paper(**r) for r in results]

class SourceVerifier:
    """Verify that claims have authoritative sources"""
    def verify_claim(self, claim: str, context: str) -> VerificationResult:
        """Check if claim is supported by sources in context"""
        # Implementation uses LLM + web search to verify
        ...
```

### MCP Configuration

```json
// .mcp/config.json
{
  "servers": {
    "tavily-search": {
      "url": "https://api.tavily.com/search",
      "auth": {
        "type": "api_key",
        "key": "${TAVILY_API_KEY}"
      }
    },
    "serper-search": {
      "url": "https://api.serper.dev/search",
      "auth": {
        "type": "api_key", 
        "key": "${SERPER_API_KEY}"
      }
    },
    "arxiv-search": {
      "url": "http://export.arxiv.org/api/query",
      "auth": {
        "type": "none"
      }
    }
  }
}
```

### Updated Agent Configuration

```yaml
# agents/content_generation/researcher.yaml
name: "Research Agent"
role: "Research Specialist"
# ... other fields ...
tools:
  - web_search       # NEW: MCP web search
  - arxiv_search     # NEW: Academic papers
  - source_verifier  # NEW: Claim verification
```

### Testing Strategy

```python
def test_web_search_tool():
    """Web search returns valid results"""
    tool = WebSearchTool("tavily")
    results = tool.search("quality engineering trends 2026")
    
    assert len(results) > 0
    assert all(r.url.startswith("http") for r in results)
    assert all(r.title for r in results)

def test_researcher_uses_tools():
    """Research agent invokes web search"""
    registry = AgentRegistry(Path("agents/"), OpenAIProvider())
    researcher = registry.get_agent("researcher")
    
    result = researcher.research_topic("test-driven development")
    
    assert "sources" in result
    assert len(result["sources"]) > 0
    assert all("url" in s for s in result["sources"])

def test_source_verification():
    """Editor verifies all claims have sources"""
    verifier = SourceVerifier()
    
    claim = "Test-driven development reduces bugs by 40%"
    context = "According to Microsoft Research..."
    
    result = verifier.verify_claim(claim, context)
    assert result.has_source == True
```

### Integration with Pipeline

**Before (current):**
```
Research Agent → [uses training data only] → outputs with [UNVERIFIED] tags
```

**After (with MCP tools):**
```
Research Agent → [searches web, ArXiv] → outputs with source URLs
Editor Agent → [verifies sources] → rejects if missing
```

### Environment Variables

```bash
# .env
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...
# ArXiv is public, no key needed
```

### Error Handling

- [ ] Tool timeout (fallback to LLM knowledge)
- [ ] API rate limits (retry with backoff)
- [ ] Network errors (graceful degradation)
- [ ] Invalid responses (validation + fallback)

### Success Metrics

- 100% of research tasks use web search
- Zero [UNVERIFIED] tags in final articles
- Average of 5+ authoritative sources per article
- Source quality score >8/10 (measured by editor)
- Tool failure rate <5%

### References

- **MCP Protocol:** https://github.com/mcp
- **Tavily Search:** https://tavily.com
- **SerperDev:** https://serper.dev
- **ArXiv API:** https://arxiv.org/help/api
- **Related Issues:** #27 (Agent Registry), #22 (Writer Accuracy)
- **Dependencies:** Issue #27 (registry for tool injection)

---

## Issue #30: Research Hierarchical Agent Patterns

**Labels:** `P3-low`, `type:research`, `effort:small`  
**Milestone:** Phase 7 - Advanced Features (Q3 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Research spike to evaluate when/if hierarchical agent structures (manager agents, multi-level teams) would benefit economist-agents. Current flat 6-agent voting structure works well, but we may need hierarchy if we scale beyond 10 agents.

### Context

**Current Architecture:** Flat structure
- Stage 2: 6 editorial board agents (peers, no hierarchy)
- Stage 3: 4 content agents (sequential, no hierarchy)

**Potential Future Needs:**
- Multiple editorial boards (different domains: security, performance, process)
- Specialized research teams per topic
- Multi-language content generation
- Parallel article generation

**When Hierarchy Helps:**
- >10 agents need coordination
- Complex task decomposition required
- Different specialization levels (junior/senior agents)
- Parallel work streams with synchronization

### Goals

- [ ] Understand hierarchical patterns in CrewAI, AutoGen, LangGraph
- [ ] Identify use cases for economist-agents
- [ ] Prototype simple 2-level hierarchy
- [ ] Document decision criteria
- [ ] Create ADR if adopting, or park if not needed yet

### Research Questions

1. **CrewAI Manager Agents:**
   - How do manager agents delegate to workers?
   - What's the coordination overhead?
   - When does it outperform flat structures?

2. **AutoGen Hierarchical Group Chat:**
   - How are roles assigned?
   - How is context passed between levels?
   - What are the failure modes?

3. **LangGraph State Machines:**
   - When is graph-based routing better than hierarchy?
   - What's the learning curve?
   - What are the tradeoffs vs CrewAI?

4. **Economist-Agents Fit:**
   - Would editorial board benefit from a "chair" agent?
   - Could research be delegated to junior agents?
   - Is parallel article generation needed?

### Acceptance Criteria

- [ ] Research report documented (1-2 pages)
- [ ] At least 3 hierarchical patterns analyzed
- [ ] Decision criteria defined (when to use hierarchy)
- [ ] Prototype built (if applicable)
- [ ] ADR created if adopting pattern
- [ ] Or: "Not needed yet" decision documented with triggers

### Implementation Plan

**Week 21: Research (5 days)**
1. Study CrewAI manager agents (docs + examples)
2. Study AutoGen hierarchical group chat
3. Study LangGraph graph-based routing
4. Document findings in research report
5. Identify use cases for our system

**Week 22: Prototype & Decision (5 days)**
1. Build 2-level hierarchy prototype (manager + 2 workers)
2. Test coordination overhead
3. Measure vs flat structure
4. Document decision criteria
5. Create ADR or parking decision

### Prototype Example

```python
# Hierarchical editorial board experiment
manager_agent = Agent(
    role="Editorial Board Chair",
    goal="Coordinate voting and synthesize decisions",
    backstory="You manage the editorial board process"
)

technical_agents = [vp_eng, senior_qe, data_skeptic]
audience_agents = [career_climber, busy_reader]

# Manager coordinates two sub-teams
technical_vote = manager_agent.coordinate(technical_agents, topic)
audience_vote = manager_agent.coordinate(audience_agents, topic)
final_decision = manager_agent.synthesize(technical_vote, audience_vote)
```

### Decision Criteria

**Use Hierarchical Pattern When:**
- Agent count >15
- Need parallel work streams
- Task decomposition is complex (>3 levels)
- Specialization hierarchy exists (junior/senior)

**Stick with Flat Structure When:**
- Agent count <10
- Sequential tasks work fine
- Coordination overhead outweighs benefits
- Simplicity is priority

### Parking Decision Template

If hierarchy not needed yet:

```markdown
## Decision: Hierarchy Not Needed (Yet)

**Date:** 2026-XX-XX  
**Current State:** 11 agents, flat structure working well  
**Decision:** Keep flat structure, revisit when triggers hit

**Triggers to Revisit:**
- [ ] Agent count exceeds 15
- [ ] Need for parallel article generation
- [ ] Multiple editorial boards required
- [ ] Task decomposition becomes bottleneck

**Next Review:** Q4 2026 or when trigger hit
```

### Deliverables

**Research Report** (`docs/RESEARCH_HIERARCHICAL_PATTERNS.md`):
- Executive summary
- Pattern analysis (CrewAI, AutoGen, LangGraph)
- Use cases for economist-agents
- Decision criteria
- Prototype results (if built)
- Recommendation

**Optional ADR:** If adopting hierarchy pattern

### Success Metrics

- Research completed within 1 week
- Clear decision criteria documented
- If prototype built: working 2-level hierarchy demo
- Decision made: adopt or park with defined triggers

### References

- CrewAI Manager Agents: https://docs.crewai.com/concepts/agents#manager-agents
- AutoGen Hierarchical: https://microsoft.github.io/autogen/blog/2023/11/26/Agent-AutoBuild
- LangGraph: https://langchain-ai.github.io/langgraph/
- **Related Issues:** #25 (CrewAI Migration)
- **Dependencies:** Issue #25 (CrewAI) should be complete for context

---

## Issue #31: Build Agent Performance Metrics Dashboard

**Labels:** `P3-low`, `type:enhancement`, `effort:medium`  
**Milestone:** Phase 6 - Optimization (Q2 2026)  
**Assignee:** @oviney  
**Projects:** Agentic Architecture Evolution

### Description

Create a Streamlit dashboard to track agent performance over time: quality metrics (Hemingway scores, style adherence), cost metrics (token usage, API costs), and performance metrics (execution time, success rate). This enables data-driven agent optimization.

### Context

We currently have no visibility into:
- Which agents are expensive (token usage)
- Which agents produce better quality
- How quality/cost evolves over time
- Which topics perform best (engagement)

A metrics dashboard enables:
- Identify optimization opportunities
- A/B test agent configurations
- Track regression after changes
- Demonstrate ROI to stakeholders

### Goals

- [ ] Metrics collection infrastructure
- [ ] SQLite database for historical data
- [ ] Streamlit dashboard for visualization
- [ ] GitHub Actions integration (automated metrics)
- [ ] Alerting for regressions

### Acceptance Criteria

- [ ] Dashboard accessible via `streamlit run scripts/metrics_dashboard.py`
- [ ] Tracks at least 10 key metrics
- [ ] Historical data stored and queryable
- [ ] Visualization includes trends over time
- [ ] Agent comparison views
- [ ] GitHub Actions generates metrics per run
- [ ] Alerts triggered if quality drops >10%

### Implementation Plan

**Week 16-17: Dashboard Setup**
1. Install Streamlit: `pip install streamlit plotly`
2. Create `scripts/metrics_dashboard.py`
3. Design dashboard layout
4. Add SQLite backend
5. Implement metrics collection hooks

**Week 18-19: Optimization**
1. Collect baseline metrics (10 runs)
2. A/B test agent optimizations
3. Measure improvements
4. Document winning configurations

**Week 20: GA Integration**
1. Set up Google Analytics 4
2. Track article engagement
3. Link to agent/topic metadata
4. Feed data back to editorial board

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Economist Agents - Performance Dashboard                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Quality Metrics                                         │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │ Hemingway    │ Style        │ Sources      │            │
│  │ Score: 8.2   │ Score: 94%   │ Verified:100%│            │
│  │ ↓ 0.3        │ ↑ 2%         │ ↑ 15%        │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                                                             │
│  💰 Cost Metrics                                            │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │ Tokens/Article│ Cost/Article│ Monthly      │            │
│  │ 11,234       │ $0.38        │ $45.60       │            │
│  │ ↓ 8%         │ ↓ 12%        │ ↓ 10%        │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                                                             │
│  ⚡ Performance Metrics                                     │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │ Pipeline Time│ Success Rate │ Agent Errors │            │
│  │ 3:42min      │ 96%          │ 2.1%         │            │
│  │ ↓ 18s        │ ↑ 1%         │ ↓ 0.5%       │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                                                             │
│  📈 Trends (Last 30 Days)                                   │
│  [Line chart: Quality over time]                           │
│  [Line chart: Cost over time]                              │
│  [Bar chart: Agent comparison]                             │
│                                                             │
│  🎯 Top Performing Topics (by engagement)                  │
│  1. Test-Driven Development (1,234 views)                  │
│  2. Shift-Left Testing (892 views)                         │
│  3. Mutation Testing (745 views)                           │
└─────────────────────────────────────────────────────────────┘
```

### Metrics Schema

```sql
-- metrics.db schema
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    topic TEXT,
    status TEXT, -- success/failed
    duration_seconds INTEGER
);

CREATE TABLE agent_metrics (
    id INTEGER PRIMARY KEY,
    run_id INTEGER,
    agent_name TEXT,
    tokens_used INTEGER,
    cost_usd REAL,
    execution_time_seconds INTEGER,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE quality_metrics (
    id INTEGER PRIMARY KEY,
    run_id INTEGER,
    hemingway_score REAL,
    style_adherence_pct REAL,
    sources_verified_pct REAL,
    readability_grade REAL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE engagement_metrics (
    id INTEGER PRIMARY KEY,
    article_slug TEXT,
    views INTEGER,
    avg_time_on_page_seconds INTEGER,
    bounce_rate_pct REAL,
    updated_at DATETIME
);
```

### Metrics Collection

```python
# scripts/metrics_collector.py
class MetricsCollector:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path)
    
    def start_run(self, topic: str) -> int:
        """Start a new metrics run"""
        cursor = self.db.execute(
            "INSERT INTO runs (timestamp, topic, status) VALUES (?, ?, ?)",
            (datetime.now(), topic, "running")
        )
        return cursor.lastrowid
    
    def log_agent_metrics(self, run_id: int, agent_name: str, 
                         tokens: int, cost: float, time: float):
        """Log per-agent metrics"""
        self.db.execute(
            "INSERT INTO agent_metrics VALUES (?, ?, ?, ?, ?)",
            (None, run_id, agent_name, tokens, cost, time)
        )
        self.db.commit()
    
    def log_quality_metrics(self, run_id: int, hemingway: float, 
                           style: float, sources: float):
        """Log quality metrics"""
        self.db.execute(
            "INSERT INTO quality_metrics VALUES (?, ?, ?, ?, ?)",
            (None, run_id, hemingway, style, sources, None)
        )
        self.db.commit()
```

### GitHub Actions Integration

```yaml
# .github/workflows/metrics.yml
name: Collect Metrics

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run pipeline with metrics
        run: |
          python3 scripts/economist_agent.py --collect-metrics
      - name: Upload metrics
        uses: actions/upload-artifact@v3
        with:
          name: metrics-db
          path: metrics.db
      - name: Check for regressions
        run: |
          python3 scripts/check_regressions.py
          # Fails build if quality dropped >10%
```

### Key Metrics to Track

**Quality:**
- Hemingway readability score
- Economist style adherence %
- Sources verified %
- Editor rejection rate
- Readability grade level

**Cost:**
- Tokens per article
- Cost per article (USD)
- Monthly API costs
- Cost per agent
- Token efficiency (words/token)

**Performance:**
- End-to-end pipeline time
- Per-agent execution time
- Success rate %
- Error rate by type
- Retry count

**Engagement (from GA4):**
- Page views
- Average time on page
- Bounce rate
- Social shares
- Comments

### Alerting Rules

```python
# scripts/check_regressions.py
def check_regressions(current_metrics, baseline_metrics):
    alerts = []
    
    # Quality regression
    if current_metrics.hemingway > baseline_metrics.hemingway * 1.1:
        alerts.append("⚠️ Hemingway score degraded >10%")
    
    # Cost regression
    if current_metrics.cost > baseline_metrics.cost * 1.25:
        alerts.append("⚠️ Cost increased >25%")
    
    # Performance regression  
    if current_metrics.time > baseline_metrics.time * 1.5:
        alerts.append("⚠️ Pipeline time increased >50%")
    
    return alerts
```

### Success Metrics

- [ ] Dashboard deployed and accessible
- [ ] 30 days of historical data collected
- [ ] At least one optimization identified via metrics
- [ ] Regression alerts working (tested with intentional degradation)
- [ ] Team uses dashboard weekly for decisions

### References

- **Streamlit Docs:** https://docs.streamlit.io
- **Plotly Visualization:** https://plotly.com/python/
- **GA4 API:** https://developers.google.com/analytics/devguides/reporting/data/v1
- **Related Issues:** #24 (GA Integration), #22 (Writer Accuracy), #23 (Editor Accuracy)
- **Dependencies:** Issue #25 (CrewAI) for baseline metrics

---

## Summary of All Issues

| Issue | Title | Priority | Effort | Phase |
|-------|-------|----------|--------|-------|
| #26 | Extract Agent Definitions to YAML | P1-high | Medium | 1 (Weeks 1-2) |
| #27 | Implement Agent Registry Pattern | P1-high | Medium | 2 (Weeks 3-4) |
| #28 | Create Public Skills Library | P2-medium | Large | 5 (Weeks 12-15) |
| #29 | Integrate MCP Tools | P2-medium | Medium | 3 (Weeks 5-6) |
| #30 | Research Hierarchical Patterns | P3-low | Small | 7 (Weeks 21-22) |
| #31 | Build Metrics Dashboard | P3-low | Medium | 6 (Weeks 16-20) |

**How to Create Issues:**
1. Go to https://github.com/oviney/economist-agents/issues/new
2. Copy/paste each issue's content
3. Add appropriate labels and milestone
4. Assign to yourself
5. Add to project board if using GitHub Projects

**Recommended Labels:**
- Priority: `P0-critical`, `P1-high`, `P2-medium`, `P3-low`, `P4-icebox`
- Type: `type:architecture`, `type:enhancement`, `type:refactor`, `type:research`
- Effort: `effort:small`, `effort:medium`, `effort:large`

**Recommended Milestones:**
- Phase 1 - Foundation (Q1 2026)
- Phase 2 - Agent Registry (Q1 2026)
- Phase 3 - Tool Integration (Q1 2026)
- Phase 4 - CrewAI Migration (Q1 2026)
- Phase 5 - Community (Q2 2026)
- Phase 6 - Optimization (Q2 2026)
- Phase 7 - Advanced Features (Q3 2026)
