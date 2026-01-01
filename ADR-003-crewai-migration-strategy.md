# ADR-003: Phased CrewAI Migration Strategy

**Status:** Proposed  
**Date:** 2026-01-01  
**Deciders:** Ouray Viney (Agentic AI Architect)  
**Dependencies:** ADR-001, ADR-002

## Context

The economist-agents system uses a custom 3-stage pipeline with 11 agents. After reviewing multi-agent frameworks (CrewAI, AutoGen, LangGraph), we need to decide:

1. Should we migrate to a framework?
2. If yes, which framework and what parts?
3. What's the migration strategy to minimize risk?

**Current Architecture:**
```
Stage 1: Discovery (topic_scout.py)
  └─> content_queue.json

Stage 2: Editorial Board (editorial_board.py)
  └─> 6 persona agents vote
  └─> board_decision.json

Stage 3: Content Generation (economist_agent.py)
  └─> Research → Graphics → Writer → Editor
  └─> Markdown + PNG
```

**Framework Analysis:**

| Framework | Strengths | Weaknesses | Fit Score |
|-----------|-----------|------------|-----------|
| CrewAI | Role-based, YAML configs, active community | Python-only, opinionated orchestration | 8/10 |
| AutoGen | Flexible, multi-language, research-backed | Steep learning curve, verbose config | 6/10 |
| LangGraph | Graph-based routing, precise control | Requires LangChain knowledge, complex | 5/10 |

## Decision

**We will pursue SELECTIVE, PHASED migration to CrewAI:**

### ✅ MIGRATE TO CrewAI
1. **Agent Definitions** (Stage 3: Content Generation)
   - Research Agent → CrewAI agent with web search tools
   - Writer Agent → CrewAI agent with Economist style constraints
   - Editor Agent → CrewAI agent with quality gates
   - Graphics Agent → Custom (CrewAI doesn't handle matplotlib well)

2. **Task Orchestration** (Stage 3 only)
   - Sequential tasks: Research → Write → Edit
   - Built-in task delegation and handoffs
   - Automatic context passing between agents

### ❌ KEEP CUSTOM IMPLEMENTATION
1. **Pipeline Orchestration** (Stages 1-3 coordination)
   - Custom 3-stage workflow is our competitive advantage
   - No framework does multi-stage pipelines with human review gates
   - GitHub Actions integration is custom

2. **Editorial Board** (Stage 2: Voting Swarm)
   - Weighted scoring algorithm is domain-specific
   - 6-persona debate doesn't map to CrewAI's task model
   - Keep as custom Python orchestration

3. **Topic Scout** (Stage 1: Discovery)
   - Simple single-agent workflow
   - No collaboration needed
   - Framework overhead not justified

## Architecture After Migration

```
┌─────────────────────────────────────────────────────────┐
│  CUSTOM PIPELINE ORCHESTRATION (Keep)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Stage 1: Discovery (CUSTOM)                            │
│  ┌──────────────────────────────────────────┐           │
│  │ topic_scout.py                           │           │
│  │ - Custom agent (no framework)            │           │
│  └──────────────────────────────────────────┘           │
│           ↓ content_queue.json                          │
│                                                          │
│  Stage 2: Editorial Board (CUSTOM)                      │
│  ┌──────────────────────────────────────────┐           │
│  │ editorial_board.py                       │           │
│  │ - Custom voting algorithm                │           │
│  │ - 6 persona agents (YAML configs)        │           │
│  └──────────────────────────────────────────┘           │
│           ↓ board_decision.json                         │
│                                                          │
│  Stage 3: Content Generation (CREWAI)                   │
│  ┌──────────────────────────────────────────┐           │
│  │ CrewAI Workflow                          │           │
│  │                                          │           │
│  │  Agents (agents.yaml):                  │           │
│  │   - researcher                           │           │
│  │   - writer                               │           │
│  │   - editor                               │           │
│  │                                          │           │
│  │  Tasks (tasks.yaml):                    │           │
│  │   - research_task → researcher           │           │
│  │   - write_task → writer                  │           │
│  │   - edit_task → editor                   │           │
│  │                                          │           │
│  │  Tools:                                  │           │
│  │   - web_search (MCP)                    │           │
│  │   - data_analyzer                        │           │
│  │                                          │           │
│  └──────────────────────────────────────────┘           │
│           ↓                                              │
│  ┌──────────────────────────────────────────┐           │
│  │ graphics_agent.py (CUSTOM)               │           │
│  │ - Matplotlib chart generation            │           │
│  └──────────────────────────────────────────┘           │
│           ↓ Markdown + PNG                              │
└─────────────────────────────────────────────────────────┘
```

## Phased Migration Plan

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Set up CrewAI infrastructure without changing behavior

**Tasks:**
- [ ] Install CrewAI: `pip install crewai crewai-tools`
- [ ] Create `agents/crewai/agents.yaml` with 3 agents (research, writer, editor)
- [ ] Create `agents/crewai/tasks.yaml` with 3 tasks
- [ ] Create wrapper script `scripts/crewai_stage3.py`
- [ ] Run both old and new Stage 3 in parallel, compare outputs
- [ ] Verify output equivalence (markdown diff, metrics)

**Success Criteria:**
- ✅ CrewAI generates equivalent articles to old system
- ✅ No regression in Hemingway scores or style adherence
- ✅ Migration path documented

### Phase 2: Tool Integration (Weeks 3-4)
**Goal:** Add real-time research capabilities via MCP

**Tasks:**
- [ ] Integrate Tavily web search tool
- [ ] Add SerperDev for Google search
- [ ] Connect to ArXiv API for research papers
- [ ] Add source verification to research agent
- [ ] Update `CHART_DESIGN_SPEC.md` with data sourcing requirements

**Success Criteria:**
- ✅ Research agent uses live web search (not just training data)
- ✅ All claims have source URLs in governance logs
- ✅ Zero [UNVERIFIED] tags in generated articles

### Phase 3: Cut Over (Week 5)
**Goal:** Replace old Stage 3 with CrewAI implementation

**Tasks:**
- [ ] Update `economist_agent.py` to call `crewai_stage3.py`
- [ ] Remove old agent code (research, writer, editor)
- [ ] Keep graphics agent custom (matplotlib generation)
- [ ] Update GitHub Actions workflow
- [ ] Run full pipeline end-to-end
- [ ] Archive old code to `archived/stage3_legacy/`

**Success Criteria:**
- ✅ Full pipeline runs without errors
- ✅ Generated content meets quality gates
- ✅ No increase in API costs (monitor token usage)

### Phase 4: Optimization (Weeks 6-8)
**Goal:** Tune CrewAI agents for performance

**Tasks:**
- [ ] A/B test different agent role definitions
- [ ] Optimize system messages for token efficiency
- [ ] Add human-in-the-loop approval gates (CrewAI callbacks)
- [ ] Implement retry logic for failed tasks
- [ ] Add observability (log agent interactions)

**Success Criteria:**
- ✅ 20% reduction in token usage vs Phase 3
- ✅ 50% reduction in hallucinations (measured by editor rejections)
- ✅ Interactive mode works with CrewAI

## Consequences

### Positive

1. **Built-in Collaboration:** CrewAI handles agent-to-agent communication
2. **Tool Ecosystem:** Access to pre-built tools (web search, databases)
3. **Community Support:** Active Discord, documentation, examples
4. **YAML Configuration:** Easier to tune agents without code changes
5. **Memory Management:** CrewAI handles conversation context automatically
6. **Error Handling:** Built-in retry logic and fallbacks

### Negative

1. **Framework Dependency:** Now coupled to CrewAI's release cycle
2. **Learning Curve:** Team needs to learn CrewAI patterns
3. **Migration Risk:** Behavior may change subtly during migration
4. **Limited Flexibility:** CrewAI's task model may not fit all future use cases
5. **Debugging Complexity:** Framework adds layers to debug

### Neutral

1. **Partial Migration:** Reduces risk but creates hybrid architecture
2. **Graphics Agent:** Stays custom (CrewAI doesn't help with matplotlib)
3. **Cost Impact:** Likely neutral (same LLM calls, different wrapper)

## Rollback Plan

If CrewAI migration fails:

1. **Phase 1-2 Rollback:** Keep old Stage 3 code (not deleted until Phase 3)
2. **Phase 3 Rollback:** Restore from `archived/stage3_legacy/`
3. **Phase 4 Rollback:** Revert to Phase 3 baseline configuration

**Trigger Conditions for Rollback:**
- Quality scores drop >10% for 3 consecutive runs
- API costs increase >25%
- Pipeline failure rate >5%
- Team votes to abort (2/3 majority)

## Alternative Approaches Considered

### 1. Full Pipeline Migration to CrewAI
**Pros:** Unified framework, simpler architecture  
**Cons:** Lose our competitive advantage (custom editorial board)  
**Verdict:** Rejected - editorial board is our IP

### 2. AutoGen Instead of CrewAI
**Pros:** More flexible, research-backed  
**Cons:** Steeper learning curve, more verbose  
**Verdict:** Deferred - CrewAI better for role-based agents

### 3. LangGraph for State Machine
**Pros:** Precise control over workflows  
**Cons:** Requires LangChain expertise, complexity overhead  
**Verdict:** Rejected - overkill for sequential tasks

### 4. Build Our Own Framework
**Pros:** Total control, no dependencies  
**Cons:** Massive engineering effort, reinventing wheel  
**Verdict:** Rejected - not core competency

### 5. No Migration (Status Quo)
**Pros:** No risk, no work  
**Cons:** Technical debt grows, can't leverage community tools  
**Verdict:** Rejected - need to evolve architecture

## Success Metrics

**Quality Metrics:**
- [ ] Hemingway readability score: <10 (maintain current level)
- [ ] Economist style adherence: >90% (measured by editor agent)
- [ ] Source verification: 100% of claims have URLs

**Performance Metrics:**
- [ ] Pipeline execution time: <5 minutes (current: ~4 minutes)
- [ ] Token usage: <15k tokens per article (current: ~12k)
- [ ] API cost: <$0.50 per article (current: ~$0.40)

**Reliability Metrics:**
- [ ] Pipeline success rate: >95%
- [ ] Zero regressions in governance logs
- [ ] Interactive mode works (human approval gates)

## Configuration Examples

### CrewAI agents.yaml
```yaml
researcher:
  role: >
    Quality Engineering Research Specialist
  goal: >
    Find the latest data, research papers, and industry trends
    relevant to the assigned topic
  backstory: >
    You are an expert researcher who knows how to find authoritative
    sources and verify information. You prioritize recent publications,
    industry reports, and peer-reviewed research.
  tools:
    - web_search
    - arxiv_search
    - source_verifier
  verbose: true

writer:
  role: >
    Economist-Style Technical Writer
  goal: >
    Write clear, engaging prose that explains complex QE topics
    in The Economist's signature style
  backstory: >
    You write for The Economist. Your prose is crisp, uses British
    spelling, avoids throat-clearing, and always grounds claims in data.
  tools: []
  verbose: true

editor:
  role: >
    Quality Assurance Editor
  goal: >
    Enforce The Economist style guide and verify all claims are sourced
  backstory: >
    You are a meticulous editor who catches every deviation from style,
    every unsubstantiated claim, and every readability issue.
  tools:
    - hemingway_scorer
    - source_checker
  verbose: true
```

### CrewAI tasks.yaml
```yaml
research_task:
  description: >
    Research the topic: {topic}
    
    Find:
    - Latest industry trends and statistics
    - Recent research papers (last 2 years)
    - Expert opinions and case studies
    - Relevant data for visualization
    
    Output must include source URLs for all claims.
  expected_output: >
    JSON with research findings:
    - key_statistics: [...]
    - research_papers: [...]
    - industry_trends: [...]
    - sources: [...]
  agent: researcher

write_task:
  description: >
    Write an Economist-style article based on the research.
    
    Requirements:
    - 800-1200 words
    - British spelling
    - Hemingway readability score < 10
    - No throat-clearing (jump straight in)
    - All claims sourced
    
    Use research from: {research_output}
  expected_output: >
    Markdown article with:
    - Title
    - Byline
    - Body (3-5 sections)
    - Citations
  agent: writer
  context:
    - research_task

edit_task:
  description: >
    Edit the article for style, clarity, and accuracy.
    
    Check:
    - Economist style guide compliance
    - All claims have sources
    - Readability (Hemingway < 10)
    - British spelling
    - No [UNVERIFIED] tags
    
    Article to edit: {article_draft}
  expected_output: >
    Final article in Markdown format, ready for publication
  agent: editor
  context:
    - write_task
```

## References

- CrewAI Documentation: https://docs.crewai.com
- CrewAI GitHub Examples: https://github.com/crewAIInc/crewAI-examples
- Multi-Agent Patterns: https://www.anthropic.com/research/building-effective-agents
- Related ADRs: ADR-001, ADR-002, ADR-004

## Notes

This migration is **selective by design**. We keep our competitive advantages (custom pipeline, editorial board) while leveraging CrewAI for commodity workflows (research, writing, editing). This hybrid approach minimizes risk while gaining framework benefits.
