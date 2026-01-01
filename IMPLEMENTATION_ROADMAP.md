# Implementation Roadmap: Agentic Architecture Evolution

**Project:** economist-agents  
**Version:** 1.0  
**Date:** 2026-01-01  
**Owner:** Ouray Viney  
**Timeline:** Q1-Q3 2026 (26 weeks)

## Executive Summary

This roadmap transforms economist-agents from a custom script-based system to a modular, framework-enhanced architecture while preserving core competitive advantages (editorial board, custom pipeline).

**Strategic Goals:**
1. **Modularity:** Agent definitions reusable across projects
2. **Extensibility:** Easy to add new agents and capabilities
3. **Community:** Share generic agents, build ecosystem
4. **Quality:** Improved content through better tools and collaboration
5. **Maintainability:** Reduce technical debt, improve testability

**Key Principles:**
- ✅ Incremental adoption (no big-bang rewrites)
- ✅ Preserve what works (custom pipeline, editorial board)
- ✅ Leverage frameworks for commodity tasks (research, writing)
- ✅ Measure everything (quality metrics, performance, costs)

## Quarter View

### Q1 2026: Foundation (Weeks 1-12)
**Theme:** Configuration extraction and framework evaluation

**Deliverables:**
- Agent configuration system (YAML)
- Agent registry pattern
- CrewAI pilot (Stage 3 only)
- MCP tool integration

**Success Criteria:**
- All agents in YAML format
- CrewAI generates equivalent content
- Web search tools operational

### Q2 2026: Integration (Weeks 13-24)
**Theme:** Production migration and community engagement

**Deliverables:**
- CrewAI production cutover
- Public skills library
- Performance dashboard
- Community documentation

**Success Criteria:**
- 100% of articles via CrewAI Stage 3
- First community contributor
- Metrics dashboard operational

### Q3 2026: Optimization (Weeks 25-36)
**Theme:** Performance tuning and advanced features

**Deliverables:**
- Agent performance optimization
- Advanced tool integrations
- Hierarchical patterns research
- Cost reduction initiatives

**Success Criteria:**
- 20% token usage reduction
- 50% fewer hallucinations
- Research spike on scaling patterns

---

## Detailed Timeline

## PHASE 1: Agent Configuration System (Weeks 1-2)

### Week 1: Schema & Loader

**ADR Reference:** ADR-001

**Tasks:**

1. **Design YAML Schema** (Day 1-2)
   - [ ] Create `agents/schema.json` with JSON Schema
   - [ ] Define required fields: `name`, `role`, `goal`, `backstory`, `system_message`
   - [ ] Define optional fields: `tools`, `scoring_criteria`, `metadata`
   - [ ] Add examples in schema documentation

2. **Implement Loader** (Day 3-4)
   - [ ] Create `scripts/agent_loader.py`
   - [ ] Implement YAML parsing with validation
   - [ ] Add error handling for malformed configs
   - [ ] Create `AgentConfig` dataclass

3. **Testing** (Day 5)
   - [ ] Write unit tests for loader
   - [ ] Create fixture YAML files for testing
   - [ ] Test edge cases (missing fields, invalid YAML)
   - [ ] Add schema validation tests

**Deliverables:**
- `agents/schema.json`
- `scripts/agent_loader.py`
- `tests/test_agent_loader.py`
- `agents/README.md` (schema documentation)

### Week 2: Migration to YAML

**Tasks:**

1. **Extract Editorial Board Agents** (Day 1-2)
   - [ ] Create `agents/editorial_board/vp_engineering.yaml`
   - [ ] Create `agents/editorial_board/senior_qe_lead.yaml`
   - [ ] Create `agents/editorial_board/data_skeptic.yaml`
   - [ ] Create `agents/editorial_board/career_climber.yaml`
   - [ ] Create `agents/editorial_board/economist_editor.yaml`
   - [ ] Create `agents/editorial_board/busy_reader.yaml`

2. **Extract Content Agents** (Day 3)
   - [ ] Create `agents/content_generation/researcher.yaml`
   - [ ] Create `agents/content_generation/writer.yaml`
   - [ ] Create `agents/content_generation/editor.yaml`
   - [ ] Create `agents/content_generation/graphics.yaml`

3. **Extract Discovery Agent** (Day 4)
   - [ ] Create `agents/discovery/topic_scout.yaml`

4. **Validation** (Day 5)
   - [ ] Run schema validation on all YAML files
   - [ ] Test loading all 11 agents
   - [ ] Verify no data loss from Python constants
   - [ ] Add pre-commit hook for YAML validation

**Deliverables:**
- 11 agent YAML files
- Pre-commit hook for validation
- Migration verification report

---

## PHASE 2: Agent Registry (Weeks 3-4)

### Week 3: Core Registry Implementation

**ADR Reference:** ADR-002

**Tasks:**

1. **Registry Core** (Day 1-3)
   - [ ] Create `scripts/agent_registry.py`
   - [ ] Implement `AgentRegistry` class
   - [ ] Add `_load_agents()` method
   - [ ] Add `get_agent()` factory method
   - [ ] Add `list_agents()` discovery method
   - [ ] Add `get_config()` inspection method

2. **LLM Provider Abstraction** (Day 4-5)
   - [ ] Create `LLMProvider` protocol
   - [ ] Implement `OpenAIProvider`
   - [ ] Implement `AnthropicProvider`
   - [ ] Add provider auto-detection from env vars
   - [ ] Test provider swapping

**Deliverables:**
- `scripts/agent_registry.py`
- `scripts/llm_providers.py`
- `tests/test_agent_registry.py`

### Week 4: Integration with Existing Scripts

**Tasks:**

1. **Refactor editorial_board.py** (Day 1-2)
   - [ ] Replace hardcoded agent instantiation with registry
   - [ ] Test voting swarm with registry-loaded agents
   - [ ] Verify output equivalence

2. **Refactor economist_agent.py** (Day 3-4)
   - [ ] Replace hardcoded agent instantiation with registry
   - [ ] Test Stage 3 with registry-loaded agents
   - [ ] Verify output equivalence

3. **Refactor topic_scout.py** (Day 5)
   - [ ] Replace hardcoded agent instantiation with registry
   - [ ] Test discovery with registry-loaded agent
   - [ ] Verify output equivalence

**Deliverables:**
- Updated `scripts/editorial_board.py`
- Updated `scripts/economist_agent.py`
- Updated `scripts/topic_scout.py`
- Integration test suite

---

## PHASE 3: MCP Tool Integration (Weeks 5-6)

### Week 5: MCP Infrastructure

**ADR Reference:** ADR-004 (to be created)

**Tasks:**

1. **MCP Setup** (Day 1-2)
   - [ ] Install MCP dependencies: `pip install mcp-client`
   - [ ] Create `scripts/mcp_tools.py`
   - [ ] Configure MCP servers in `.mcp/config.json`
   - [ ] Test basic MCP connectivity

2. **Web Search Integration** (Day 3-4)
   - [ ] Integrate Tavily Search MCP server
   - [ ] Add SerperDev for Google search
   - [ ] Create `WebSearchTool` wrapper class
   - [ ] Test search functionality

3. **Research Tools** (Day 5)
   - [ ] Integrate ArXiv API for papers
   - [ ] Create `ResearchTool` wrapper class
   - [ ] Add source verification logic
   - [ ] Test research workflow

**Deliverables:**
- `scripts/mcp_tools.py`
- `.mcp/config.json`
- `tests/test_mcp_tools.py`

### Week 6: Tool Integration with Agents

**Tasks:**

1. **Update Agent Configs** (Day 1)
   - [ ] Add `tools: [web_search]` to researcher.yaml
   - [ ] Add `tools: [arxiv_search]` to researcher.yaml
   - [ ] Add `tools: [source_verifier]` to editor.yaml

2. **Registry Tool Loading** (Day 2-3)
   - [ ] Implement `_load_tools()` in AgentRegistry
   - [ ] Create tool registry/factory
   - [ ] Test tool injection into agents

3. **Integration Testing** (Day 4-5)
   - [ ] Test researcher agent with web search
   - [ ] Test editor agent with source verification
   - [ ] Verify tool outputs in governance logs
   - [ ] Test error handling (tool failures)

**Deliverables:**
- Updated agent YAML files with tools
- Tool loading in AgentRegistry
- Integration tests for tools

---

## PHASE 4: CrewAI Migration (Weeks 7-11)

### Week 7-8: CrewAI Foundation

**ADR Reference:** ADR-003

**Tasks:**

1. **CrewAI Setup** (Week 7, Day 1-2)
   - [ ] Install CrewAI: `pip install 'crewai[tools]'`
   - [ ] Create `agents/crewai/` directory structure
   - [ ] Read CrewAI documentation and examples
   - [ ] Plan agent and task mappings

2. **Agent Definitions** (Week 7, Day 3-5)
   - [ ] Create `agents/crewai/agents.yaml`
   - [ ] Define researcher agent in CrewAI format
   - [ ] Define writer agent in CrewAI format
   - [ ] Define editor agent in CrewAI format
   - [ ] Test agent loading with CrewAI

3. **Task Definitions** (Week 8, Day 1-3)
   - [ ] Create `agents/crewai/tasks.yaml`
   - [ ] Define research_task
   - [ ] Define write_task with context dependency
   - [ ] Define edit_task with context dependency
   - [ ] Test task execution

4. **Wrapper Script** (Week 8, Day 4-5)
   - [ ] Create `scripts/crewai_stage3.py`
   - [ ] Implement crew initialization
   - [ ] Implement task orchestration
   - [ ] Add error handling and logging
   - [ ] Test basic workflow

**Deliverables:**
- `agents/crewai/agents.yaml`
- `agents/crewai/tasks.yaml`
- `scripts/crewai_stage3.py`
- Basic CrewAI workflow functional

### Week 9-10: Parallel Running & Validation

**Tasks:**

1. **Dual Pipeline** (Week 9, Day 1-3)
   - [ ] Run both old and new Stage 3 in parallel
   - [ ] Create comparison script for outputs
   - [ ] Set up metrics collection (token usage, time, quality)
   - [ ] Log differences for analysis

2. **Output Validation** (Week 9, Day 4-5)
   - [ ] Compare Hemingway scores (old vs new)
   - [ ] Compare style adherence (Economist guide)
   - [ ] Compare source verification rates
   - [ ] Analyze quality differences

3. **Tuning** (Week 10, Day 1-3)
   - [ ] Adjust agent system messages for better output
   - [ ] Tune task descriptions for clarity
   - [ ] Optimize context passing between tasks
   - [ ] A/B test different configurations

4. **Cost Analysis** (Week 10, Day 4-5)
   - [ ] Compare token usage (old vs new)
   - [ ] Analyze API costs per article
   - [ ] Optimize prompts to reduce tokens
   - [ ] Document cost findings

**Deliverables:**
- Parallel pipeline comparison results
- Quality metrics report
- Cost analysis report
- Tuned CrewAI configurations

### Week 11: Production Cutover

**Tasks:**

1. **Final Validation** (Day 1-2)
   - [ ] Run 10 full pipeline executions with CrewAI
   - [ ] Verify all quality gates pass
   - [ ] Test interactive mode with CrewAI
   - [ ] Get stakeholder approval for cutover

2. **Cutover Execution** (Day 3)
   - [ ] Update `economist_agent.py` to call `crewai_stage3.py`
   - [ ] Remove old Stage 3 agent code
   - [ ] Archive old code to `archived/stage3_legacy/`
   - [ ] Update GitHub Actions workflow

3. **Monitoring** (Day 4-5)
   - [ ] Run first production article with CrewAI
   - [ ] Monitor for errors and regressions
   - [ ] Verify output quality
   - [ ] Document any issues

**Deliverables:**
- Production cutover complete
- Old code archived
- Monitoring dashboard updated
- Post-cutover report

---

## PHASE 5: Public Skills Library (Weeks 12-15)

### Week 12-13: Library Structure

**Tasks:**

1. **Directory Organization** (Week 12, Day 1-2)
   - [ ] Create `skills/public/` directory
   - [ ] Create `skills/private/` directory
   - [ ] Move generic agents to public/
   - [ ] Keep custom personas in private/

2. **Documentation** (Week 12, Day 3-5)
   - [ ] Create `skills/README.md` with usage guide
   - [ ] Document each public agent's capabilities
   - [ ] Add contribution guidelines
   - [ ] Create examples for common use cases

3. **Reusability Enhancements** (Week 13, Day 1-3)
   - [ ] Parameterize agent configs (use template variables)
   - [ ] Create agent composition patterns
   - [ ] Add agent versioning metadata
   - [ ] Test agents in isolation

4. **Community Prep** (Week 13, Day 4-5)
   - [ ] Create PR template for contributions
   - [ ] Add agent testing requirements
   - [ ] Create agent quality checklist
   - [ ] Set up GitHub Discussions for Q&A

**Deliverables:**
- `skills/public/` with 4 generic agents
- `skills/README.md` documentation
- Contribution guidelines
- Example usage patterns

### Week 14-15: Community Launch

**Tasks:**

1. **Blog Post** (Week 14, Day 1-3)
   - [ ] Write announcement blog post
   - [ ] Include architecture diagrams
   - [ ] Add usage examples
   - [ ] Explain benefits and use cases
   - [ ] Publish to viney.ca

2. **Social Promotion** (Week 14, Day 4-5)
   - [ ] Share on LinkedIn
   - [ ] Post to relevant subreddits (r/MachineLearning, r/LLMs)
   - [ ] Share in CrewAI Discord
   - [ ] Engage with community feedback

3. **Community Engagement** (Week 15, Day 1-5)
   - [ ] Respond to GitHub issues
   - [ ] Review first community PR (if any)
   - [ ] Update documentation based on feedback
   - [ ] Monitor usage metrics
   - [ ] Iterate on library based on learnings

**Deliverables:**
- Published blog post
- Community engagement plan
- First community contributions (goal)
- Usage analytics setup

---

## PHASE 6: Performance Optimization (Weeks 16-20)

### Week 16-17: Metrics Dashboard

**Tasks:**

1. **Dashboard Setup** (Week 16, Day 1-3)
   - [ ] Install Streamlit: `pip install streamlit`
   - [ ] Create `scripts/metrics_dashboard.py`
   - [ ] Design dashboard layout (quality, cost, performance)
   - [ ] Add SQLite backend for metrics storage

2. **Metrics Collection** (Week 16, Day 4-5)
   - [ ] Add metrics logging to all agents
   - [ ] Track token usage per agent
   - [ ] Track execution time per task
   - [ ] Track quality scores (Hemingway, style, sources)

3. **Visualization** (Week 17, Day 1-3)
   - [ ] Create charts for token usage over time
   - [ ] Create quality trends visualization
   - [ ] Create cost analysis dashboard
   - [ ] Add agent comparison views

4. **GitHub Actions Integration** (Week 17, Day 4-5)
   - [ ] Add metrics collection to CI/CD
   - [ ] Generate metrics report per run
   - [ ] Store historical data
   - [ ] Set up alerts for regressions

**Deliverables:**
- `scripts/metrics_dashboard.py`
- Streamlit dashboard deployed
- Automated metrics collection
- Historical trend analysis

### Week 18-19: Agent Optimization

**Tasks:**

1. **Researcher Agent** (Week 18, Day 1-2)
   - [ ] A/B test different system messages
   - [ ] Optimize web search queries
   - [ ] Reduce hallucinations via prompt engineering
   - [ ] Measure accuracy improvements

2. **Writer Agent** (Week 18, Day 3-4)
   - [ ] A/B test writing styles
   - [ ] Optimize for readability
   - [ ] Reduce token usage via conciseness training
   - [ ] Measure style adherence

3. **Editor Agent** (Week 18, Day 5)
   - [ ] A/B test quality gate thresholds
   - [ ] Optimize source verification logic
   - [ ] Reduce false positives
   - [ ] Measure precision/recall

4. **Cost Reduction** (Week 19, Day 1-3)
   - [ ] Identify high-token-usage agents
   - [ ] Implement prompt compression techniques
   - [ ] Test cheaper models (gpt-4o-mini) for non-critical tasks
   - [ ] Measure cost savings

5. **Performance Tuning** (Week 19, Day 4-5)
   - [ ] Profile pipeline execution time
   - [ ] Parallelize independent tasks (if possible)
   - [ ] Optimize API call patterns
   - [ ] Measure speedup

**Deliverables:**
- Optimized agent configurations
- 20% token reduction (target)
- Performance tuning report
- Cost savings analysis

### Week 20: Google Analytics Integration

**ADR Reference:** Issue #24

**Tasks:**

1. **Analytics Setup** (Day 1-2)
   - [ ] Set up Google Analytics 4 for blog
   - [ ] Add tracking code to generated posts
   - [ ] Configure custom events (article views, engagement)
   - [ ] Test tracking on published articles

2. **Data Pipeline** (Day 3-4)
   - [ ] Create script to fetch GA4 data
   - [ ] Store engagement metrics in SQLite
   - [ ] Link metrics to article metadata (topic, agent config)
   - [ ] Analyze which topics perform best

3. **Feedback Loop** (Day 5)
   - [ ] Create report: "Best Performing Topics"
   - [ ] Feed data back to editorial board
   - [ ] Adjust topic scoring based on engagement
   - [ ] Document feedback mechanism

**Deliverables:**
- GA4 integration complete
- Engagement data pipeline
- Topic performance report
- Feedback loop to editorial board

---

## PHASE 7: Advanced Features (Weeks 21-24)

### Week 21-22: Hierarchical Patterns Research

**ADR Reference:** Issue #30

**Tasks:**

1. **Research Spike** (Week 21, Day 1-5)
   - [ ] Study CrewAI's manager agents
   - [ ] Study AutoGen's hierarchical group chat
   - [ ] Study LangGraph's graph-based routing
   - [ ] Identify use cases for economist-agents
   - [ ] Document findings

2. **Prototype** (Week 22, Day 1-3)
   - [ ] Build simple hierarchical agent prototype
   - [ ] Test with 2-level hierarchy (manager + workers)
   - [ ] Measure coordination overhead
   - [ ] Evaluate benefits

3. **Decision** (Week 22, Day 4-5)
   - [ ] Analyze when hierarchical patterns are needed
   - [ ] Document decision criteria
   - [ ] Create ADR if adopting hierarchical patterns
   - [ ] Archive prototype if not adopting yet

**Deliverables:**
- Research report on hierarchical patterns
- Prototype (if applicable)
- Decision document

### Week 23-24: Advanced Tool Integrations

**Tasks:**

1. **Database Integration** (Week 23, Day 1-2)
   - [ ] Set up Google Sheets MCP server
   - [ ] Create topic tracking spreadsheet
   - [ ] Allow agents to read/write to sheets
   - [ ] Test collaborative data management

2. **Publication APIs** (Week 23, Day 3-4)
   - [ ] Integrate DEV.to API for cross-posting
   - [ ] Integrate Medium API for cross-posting
   - [ ] Create automated publishing workflow
   - [ ] Test multi-platform publishing

3. **Advanced Research Tools** (Week 23, Day 5)
   - [ ] Integrate GitHub API for code examples
   - [ ] Integrate Stack Overflow search
   - [ ] Add specialized QE databases
   - [ ] Test advanced research workflows

4. **Integration Testing** (Week 24, Day 1-3)
   - [ ] Test all new tools in full pipeline
   - [ ] Verify error handling
   - [ ] Measure impact on article quality
   - [ ] Document tool usage patterns

5. **Documentation** (Week 24, Day 4-5)
   - [ ] Update tool integration guide
   - [ ] Create tool contribution guidelines
   - [ ] Add tool examples to skills library
   - [ ] Document MCP server setup

**Deliverables:**
- Database integration (Google Sheets)
- Publication APIs (DEV.to, Medium)
- Advanced research tools
- Updated documentation

---

## Success Metrics

### Quality Metrics
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Hemingway Score | <10 | <9 | Automated in editor agent |
| Style Adherence | 85% | 95% | Editor agent quality gates |
| Source Verification | 70% | 100% | All claims have URLs |
| Hallucination Rate | 15% | 5% | Editor rejections per article |

### Performance Metrics
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Pipeline Time | ~4 min | <5 min | End-to-end execution time |
| Token Usage | ~12k/article | <10k/article | LLM API tracking |
| API Cost | $0.40/article | <$0.35/article | Cost per published article |
| Success Rate | 92% | >95% | Pipeline completion rate |

### Community Metrics
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| GitHub Stars | 0 | 50 | GitHub metrics |
| Community PRs | 0 | 5 | Contributions in 6 months |
| Blog Engagement | N/A | 1000 views | First month after launch |
| Skills Downloads | 0 | 100 | Agent config reuse (if trackable) |

---

## Risk Management

### Critical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CrewAI migration breaks quality | Medium | High | Parallel running, rollback plan |
| Framework dependency issues | Low | High | Selective adoption, keep core custom |
| Cost overruns (API usage) | Medium | Medium | Monitor token usage, optimize prompts |
| Community adoption fails | High | Low | Focus on internal value first |
| Technical debt from hybrid approach | Medium | Medium | Regular architecture reviews |

### Mitigation Strategies

**CrewAI Migration Risk:**
- Run parallel pipelines for 2 weeks minimum
- Maintain rollback capability until Phase 4 complete
- Set quality gate thresholds (abort if quality drops >10%)

**Cost Overruns:**
- Monitor token usage per agent per week
- Set budget alerts ($50/month threshold)
- Optimize prompts continuously
- Test cheaper models for non-critical tasks

**Community Adoption:**
- Internal value first (don't depend on community)
- Quality over quantity (4 great agents > 20 mediocre)
- Document everything thoroughly
- Engage authentically, don't force it

---

## Governance & Decision Points

### Go/No-Go Gates

**Phase 2 → Phase 3:**
- [ ] All agents load from YAML without errors
- [ ] Registry passes all unit tests
- [ ] No performance regression vs baseline

**Phase 4 → Phase 5:**
- [ ] CrewAI generates equivalent quality articles
- [ ] API costs within 10% of baseline
- [ ] Interactive mode works with CrewAI

**Phase 6 → Phase 7:**
- [ ] Metrics dashboard operational
- [ ] Quality improvements measured and documented
- [ ] Cost reduction targets met (or acceptable variance explained)

### Weekly Review Meetings

**Cadence:** Every Friday, 30 minutes  
**Attendees:** Project owner (Ouray)  
**Agenda:**
1. Review completed tasks vs plan
2. Assess quality metrics
3. Identify blockers
4. Adjust timeline if needed
5. Document decisions

### Decision Authority

**Technical Decisions:** Ouray (project owner)  
**Architectural Changes:** Require ADR approval  
**Rollback Decisions:** Trigger conditions auto-execute  
**Community Policy:** Ouray approval required

---

## Dependencies & Prerequisites

### External Dependencies
- OpenAI API access (GPT-4o)
- Anthropic API access (Claude Sonnet 4)
- GitHub repository access
- Python 3.10+ environment

### Internal Dependencies
- ADR-001 must complete before ADR-002
- ADR-002 must complete before ADR-003
- Phase 4 depends on Phases 1-3 completion
- Phase 5 depends on Phase 4 cutover

### Knowledge Prerequisites
- Python programming
- YAML configuration
- Multi-agent patterns
- CrewAI framework basics
- MCP protocol understanding

---

## Communication Plan

### Stakeholders
- **Internal:** Self (Ouray)
- **Community:** GitHub contributors, blog readers
- **Audience:** Quality engineering professionals

### Communication Channels
- **Progress Updates:** Weekly commit summaries in CHANGELOG.md
- **Architecture Decisions:** ADRs in docs/ directory
- **Community:** GitHub Discussions, blog posts
- **Issues:** GitHub Issues with labels and milestones

### Milestones for Public Communication
1. **Week 2:** Agent configuration system complete
2. **Week 6:** MCP tools operational
3. **Week 11:** CrewAI migration complete
4. **Week 15:** Public skills library launch
5. **Week 24:** Advanced features complete

---

## Appendix: Quick Reference

### File Structure After Completion
```
economist-agents/
├── agents/
│   ├── schema.json
│   ├── README.md
│   ├── editorial_board/
│   │   └── *.yaml (6 files)
│   ├── content_generation/
│   │   └── *.yaml (4 files)
│   ├── discovery/
│   │   └── *.yaml (1 file)
│   └── crewai/
│       ├── agents.yaml
│       └── tasks.yaml
├── skills/
│   ├── public/ (generic agents)
│   └── private/ (custom agents)
├── scripts/
│   ├── agent_registry.py
│   ├── agent_loader.py
│   ├── llm_providers.py
│   ├── mcp_tools.py
│   ├── crewai_stage3.py
│   ├── metrics_dashboard.py
│   └── [existing scripts updated]
├── docs/
│   ├── ADR-001-agent-configuration-extraction.md
│   ├── ADR-002-agent-registry-pattern.md
│   ├── ADR-003-crewai-migration-strategy.md
│   └── ADR-004-mcp-tool-integration.md
└── tests/
    └── [comprehensive test suite]
```

### Command Cheatsheet
```bash
# Load all agents
python3 -c "from scripts.agent_registry import AgentRegistry; from pathlib import Path; r = AgentRegistry(Path('agents/')); print(r.list_agents())"

# Run with CrewAI
python3 scripts/crewai_stage3.py --topic "test-driving in QE"

# View metrics dashboard
streamlit run scripts/metrics_dashboard.py

# Validate all YAML configs
python3 scripts/validate_configs.py

# Run full pipeline
./scripts/run_pipeline.sh
```

### Key Contacts
- **Project Owner:** Ouray Viney
- **CrewAI Support:** https://discord.gg/crewai
- **MCP Documentation:** https://github.com/mcp
- **Community:** GitHub Discussions

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-01  
**Next Review:** 2026-01-08 (after Week 1 completion)
