# Research Brief: Fresh Data Integration Options for Agentic Flows

**Prepared for**: Product Research Agent / Architecture Decision
**Date**: 2026-01-25
**Context**: Evaluating approaches to enable research beyond LLM training data cutoffs

---

## Problem Statement

Our agentic research flow is limited to the LLM's training data (OpenAI: ~April 2024 cutoff). For competitive intelligence and cutting-edge research, we need real-time data access.

**Current State**:
- arXiv integration exists (`scripts/arxiv_search.py`) - provides fresh academic papers
- ChromaDB RAG exists (`src/tools/style_memory_tool.py`) - provides style pattern retrieval
- LLM: OpenAI GPT-4o (training cutoff limits freshness)

---

## Option Analysis

### Option 1: Custom CrewAI Tools (Current Approach)

**What it is**: Build Python functions with `@tool` decorators for each data source.

**Example** (our current arXiv integration):
```python
@tool("arXiv Search")
def arxiv_search(query: str, max_papers: int = 5) -> str:
    """Search arXiv for recent academic papers."""
    return search_arxiv_for_topic(query, max_papers)
```

**Pros**:
- Full control over implementation
- No external dependencies beyond API clients
- Already working for arXiv

**Cons**:
- Each integration is custom code
- Not reusable across projects
- Maintenance burden per data source
- No standardization

**Effort**: 2-8 story points per data source

---

### Option 2: Model Context Protocol (MCP)

**What it is**: Open standard (Anthropic, now Linux Foundation) for connecting LLMs to external tools/data. CrewAI has native support as of 2025.

**Architecture**:
```
┌─────────────────┐     ┌─────────────────┐
│   CrewAI Agent  │────▶│   MCP Server    │────▶ External APIs
│   (mcps=[...])  │◀────│  (standardized) │◀──── Fresh Data
└─────────────────┘     └─────────────────┘
```

**CrewAI Integration** (native support):
```python
from crewai import Agent

research_agent = Agent(
    role="Research Analyst",
    mcps=["fetch", "brave-search", "arxiv"]  # Simple DSL syntax
)
```

**Available MCP Servers** (pre-built):
| Server | Purpose | Freshness |
|--------|---------|-----------|
| `@anthropic/fetch` | Fetch any URL, convert to markdown | Real-time |
| `brave-search` | Web search | Real-time |
| `mcp-server-arxiv` | arXiv papers | Real-time |
| `tavily-mcp` | AI-optimized web search | Real-time |
| `mcp-server-sqlite` | Database queries | Real-time |
| `serpapi-mcp` | Google search results | Real-time |

**Pros**:
- Industry standard (Anthropic, OpenAI, Google, Microsoft adopted)
- Pre-built servers for common data sources
- Reusable across projects and frameworks
- Active ecosystem (97M+ monthly SDK downloads)
- CrewAI native support via `mcps=[]` syntax
- Separation of concerns (tools run as separate processes)

**Cons**:
- Learning curve for MCP server development
- Security considerations (prompt injection, tool permissions)
- Some servers may need customization
- Dependency on external MCP server processes

**Effort**:
- Using pre-built servers: 1-2 story points
- Building custom MCP server: 5-8 story points

**Sources**:
- https://docs.crewai.com/en/mcp/overview
- https://modelcontextprotocol.io/specification/2025-11-25
- https://pypi.org/project/crewai-mcp-toolbox/

---

### Option 3: Hybrid Approach

**What it is**: Use MCP for common integrations, custom tools for specialized needs.

**Implementation**:
```python
research_agent = Agent(
    role="Research Analyst",
    mcps=["brave-search", "fetch"],  # MCP for web/URLs
    tools=[arxiv_search_tool, proprietary_data_tool]  # Custom for specialized
)
```

**Pros**:
- Best of both worlds
- Leverage MCP ecosystem for common needs
- Custom tools for proprietary/specialized data
- Gradual migration path

**Cons**:
- Two patterns to maintain
- Slight complexity increase

**Effort**: Incremental (add MCP alongside existing tools)

---

### Option 4: Switch LLM Provider to Claude

**What it is**: Replace OpenAI with Claude (Anthropic) for native MCP support.

**Pros**:
- Native MCP support (Claude built MCP)
- Potentially better tool use performance
- Direct integration without adapters

**Cons**:
- Migration effort for existing prompts
- May need prompt adjustments
- Cost comparison needed

**Effort**: 3-5 story points (LLM client abstraction exists)

---

## Evaluation Criteria

| Criterion | Weight | Option 1 | Option 2 | Option 3 | Option 4 |
|-----------|--------|----------|----------|----------|----------|
| Time to fresh data | 25% | Medium | Fast | Fast | Fast |
| Maintenance burden | 20% | High | Low | Medium | Low |
| Ecosystem/reusability | 15% | None | High | Medium | High |
| Implementation effort | 15% | Low | Low | Low | Medium |
| Future-proofing | 15% | Low | High | High | High |
| Risk | 10% | Low | Medium | Low | Medium |

---

## Recommendation Criteria

Consider:
1. **Immediate need**: How urgently do we need fresh data beyond arXiv?
2. **Data sources required**: Web search? News? Financial data? Patents?
3. **Team familiarity**: Comfort with MCP vs custom tools?
4. **Long-term strategy**: Are we building reusable infrastructure?

---

## Questions for Agent Analysis

1. Given our current architecture (CrewAI + OpenAI + arXiv), what's the fastest path to web search capability?
2. Should we migrate to MCP incrementally or all at once?
3. Is switching from OpenAI to Claude justified for MCP benefits?
4. What specific MCP servers would provide the most value for our research use case?
5. What's the risk/reward of each approach?

---

## References

- CrewAI MCP Documentation: https://docs.crewai.com/en/mcp/overview
- MCP Specification (Nov 2025): https://modelcontextprotocol.io/specification/2025-11-25
- crewai-mcp-toolbox: https://pypi.org/project/crewai-mcp-toolbox/
- MCP Server Registry: https://github.com/modelcontextprotocol/servers
- Our arXiv Integration: `/home/user/economist-agents/scripts/arxiv_search.py`
- Our Research Agent: `/home/user/economist-agents/agents/research_agent.py`
