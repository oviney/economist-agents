# ADR-001: Agent Framework Selection for Autonomous Content Pipeline

**Status:** Proposed
**Date:** 2026-04-05
**Decision Maker:** Ouray Viney (Engineering Lead)
**Research:** Four parallel research agents covering Anthropic Agent SDK, MCP Protocol, CrewAI current state, and existing tool stack fit

---

## Problem Statement

The economist-agents project generates Economist-style blog articles using a multi-agent pipeline. The pipeline works end-to-end (100% publish rate, 93/100 average quality score) but the "agents" are not agents — they are sequential LLM API calls with role prompts, orchestrated by CrewAI in pre-1.0 patterns.

**What we have:** Nine agent definitions (`.agent.md` files), four CrewAI crews, custom `@tool` wrappers, GPT-4o as the reasoning model, and manual invocation for every step.

**What we need:** A production content pipeline where agents autonomously research, write, illustrate, evaluate, and deploy articles — with human governance at the PR review gate and nowhere else.

---

## Objectives

The framework decision must serve these objectives, ranked by priority:

| Priority | Objective | Measure of Success |
|----------|-----------|-------------------|
| **P0** | Autonomous execution — agents work without manual step-by-step invocation | Pipeline runs end-to-end from trigger to PR with zero human prompting |
| **P0** | Quality gates — built-in guardrails prevent bad content from reaching production | Budget caps, tool permissions, deterministic validation before publish |
| **P1** | Tool reuse — same tools work in interactive dev and automated pipeline | Article evaluator, deployer, search usable from any context |
| **P1** | Cost discipline — leverage existing subscriptions, eliminate redundant spend | Reduce total monthly API cost; no new subscriptions required |
| **P2** | Vendor independence — avoid single-provider lock-in for reasoning layer | Can swap LLM provider within one sprint if needed |
| **P2** | Incremental migration — no full rewrite; migrate tool-by-tool | Each phase delivers standalone value; pipeline never goes dark |
| **P3** | Community and ecosystem — framework has active maintenance and troubleshooting resources | GitHub activity, documentation quality, production adoption evidence |

---

## Current State Inventory

### Subscriptions and API Keys (Already Paid For)

| Tool | Monthly Cost | Current Role | Utilisation |
|------|-------------|-------------|-------------|
| Claude Code + Anthropic API | ~$20 subscription + API usage | Interactive development | **High** — used for all dev work |
| OpenAI API (GPT-4o + DALL-E 3) | Pay-per-use | Primary LLM for CrewAI agents + image generation | **Medium** — pipeline runs only |
| Google Gemini / Cloud APIs | Pay-per-use | Configured but not integrated | **Zero** — paying but not using |
| GitHub Copilot | ~$19/month | Code assistance, MCP server configured | **Low** — ad-hoc code completion |
| Serper.dev | Pay-per-use | Web search for research agent | **Low** — occasional research |

### CrewAI Architecture (As-Is)

| Component | File | What It Actually Does |
|-----------|------|----------------------|
| Stage 3 Crew | `src/crews/stage3_crew.py` | Sequential: Research → Write → Graphics (GPT-4o) |
| Stage 4 Crew | `src/crews/stage4_crew.py` | Sequential: 5-gate LLM review + deterministic polish |
| Development Crew | `src/crews/development_crew.py` | Sequential: TDD Red → Green → Review → Git (never run autonomously) |
| Sprint Orchestrator | `src/crews/sprint_orchestrator_crew.py` | Parses SPRINT.md → routes stories (never run autonomously) |
| 9 Agent Definitions | `.github/agents/*.agent.md` | Documentation files — not executable agent definitions |
| Custom Tools | `@tool` decorators in scripts/ | Coupled to CrewAI runtime, not reusable elsewhere |

### What's Missing

- No MCP integration (industry standard since late 2024)
- No parallel agent execution
- No persistent state across runs
- No cost controls or budget caps
- No autonomous scheduling — every run requires manual invocation
- Development Crew and Sprint Orchestrator have never run successfully in production

---

## Options

### Option A: CrewAI v1.13 Upgrade + MCP

Upgrade the existing CrewAI codebase to modern patterns.

**What changes:**
- Upgrade to CrewAI v1.13 with Flows (`@start`, `@listen`, `@router`)
- Replace `@tool` wrappers with MCP servers via `crewai-tools[mcp]`
- Keep GPT-4o as primary LLM (or swap to any provider — CrewAI is model-agnostic)
- Add CrewAI Enterprise (AMP) for observability if needed

**Strengths:**
- Lowest migration effort — upgrade in place, not rewrite
- Model-agnostic — can use GPT-4o, Claude, Gemini, or local models
- Largest community (46K GitHub stars, 100K+ certified developers)
- CrewAI Flows provide structured orchestration (`@start`, `@listen`, `@router`)
- Proven at scale (60M+ agent executions/month across customer base)

**Weaknesses:**
- Hierarchical delegation mode is broken (documented, confirmed by community)
- Memory management degrades in long-running crews (context accumulation)
- Error handling is fragile — one agent failure stops the entire crew
- No built-in cost controls or budget caps
- Still requires manual invocation or custom scheduling wrapper
- MCP support exists but is newer and less battle-tested than native tool wrappers

**Estimated effort:** 5-8 story points for upgrade; 8-13 points for MCP extraction

### Option B: Anthropic Agent SDK + MCP Servers

Replace CrewAI with Anthropic's purpose-built agent SDK.

**What changes:**
- Replace CrewAI crews with `query()` / `ClaudeSDKClient` agent loops
- Define sub-agents via `AgentDefinition` with model tiering
- Extract all tools as MCP servers (FastMCP Python SDK)
- Use built-in `max_budget_usd`, permission hooks, and tool allowlists

**Strengths:**
- Deepest MCP integration of any framework (in-process, stdio, HTTP)
- Multi-layer guardrails (permissions, hooks, callbacks, budget caps)
- Built-in cost tracking (`total_cost_usd` on every response)
- Sub-agent pattern with model tiering (Opus/Sonnet/Haiku per task)
- Session persistence and resume for multi-turn workflows
- Powers Anthropic's own production agent systems

**Weaknesses:**
- **Claude models only** — cannot use GPT-4o, Gemini, or open-source for reasoning
- Lighter orchestration than CrewAI Flows — no DAG, no built-in state machines
- Smaller community and fewer production case studies
- Agent definitions use a simpler model than CrewAI's role/backstory/goal DSL
- Newer SDK — less community troubleshooting available

**Estimated effort:** 13-21 story points (full rewrite of crews + MCP extraction)

### Option C: Claude Code Native Orchestrator

Use Claude Code (interactive or headless) as the agent runtime.

**What changes:**
- Define specialist sub-agents as Claude Code agent definitions
- Connect MCP servers for all external tools
- Run interactively (as today) or headless in CI/CD
- Sub-agents inherit tools and run in parallel natively

**Strengths:**
- Already proven in this session — researched, wrote, validated, and deployed 9 articles
- Native parallelism, tool inheritance, and session persistence
- Built-in tools (Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, Agent)
- No additional framework dependency — Claude Code IS the framework
- Subscription already paid for

**Weaknesses:**
- **Claude models only** — same lock-in as Option B
- Headless CI/CD mode (`--dangerously-skip-permissions`) is unproven for content pipelines
- No structured orchestration primitives (no Flows, no DAG, no state machines)
- Agent definitions are less formal than CrewAI's crew/task/agent model
- Session-based — no built-in long-term memory across runs
- The orchestrator is the same product as the interactive dev tool — boundary unclear

**Estimated effort:** 8-13 story points (MCP extraction + agent definitions)

### Option D: LangGraph

Replace CrewAI with LangGraph's graph-based state machine.

**What changes:**
- Define pipeline as a directed graph with nodes (agents) and edges (transitions)
- Use LangGraph's checkpointing, human-in-the-loop, and durable execution
- Model-agnostic — works with any LLM provider
- LangSmith for observability and tracing

**Strengths:**
- Most production-mature orchestration for complex workflows
- Durable execution with checkpointing — survives crashes and restarts
- Human-in-the-loop as a first-class concept (perfect for PR review gate)
- Model-agnostic — use any combination of providers
- Graph-based design maps naturally to a content pipeline

**Weaknesses:**
- Steepest learning curve of all options
- Tied to LangChain ecosystem (heavier dependency tree)
- MCP support is indirect (through custom tool wrappers, not native)
- Community skews toward chatbot/RAG use cases, not content pipelines
- Requires substantial architectural rethinking — not an incremental migration

**Estimated effort:** 21-34 story points (full rewrite + learning curve)

---

## Comparison Against Objectives

| Objective | A: CrewAI Upgrade | B: Agent SDK | C: Claude Code | D: LangGraph |
|-----------|:-:|:-:|:-:|:-:|
| **P0: Autonomous execution** | Partial — needs scheduling wrapper | Yes — programmable via SDK | Yes — headless CI/CD mode | Yes — durable execution |
| **P0: Quality gates** | Weak — system prompts only | Strong — multi-layer guardrails | Strong — permission hooks | Medium — custom nodes |
| **P1: Tool reuse (MCP)** | Supported (v1.10+) | Deepest native | Deepest native | Indirect |
| **P1: Cost discipline** | No built-in controls | Built-in budget caps | Built-in per-session | No built-in controls |
| **P2: Vendor independence** | **Best** — any LLM | Claude only | Claude only | **Best** — any LLM |
| **P2: Incremental migration** | **Best** — upgrade in place | Medium — rewrite crews | Medium — MCP first | Worst — full rewrite |
| **P3: Community/ecosystem** | **Best** — 46K stars | Smallest | Anthropic-backed | Large — 38K stars |

---

## Phase 1: The No-Regret Move

**Regardless of which option is chosen**, extracting tools into MCP servers delivers immediate value and carries zero risk. This work is framework-agnostic — CrewAI, Agent SDK, Claude Code, and LangGraph all consume MCP servers.

| MCP Server | Wraps | Effort |
|------------|-------|--------|
| `article-evaluator` | `scripts/article_evaluator.py` | 2 pts |
| `publication-validator` | `scripts/publication_validator.py` | 2 pts |
| `blog-deployer` | `scripts/deploy_to_blog.py` | 3 pts |
| `web-researcher` | `scripts/web_research.py` + `arxiv_search.py` | 3 pts |
| `image-generator` | `scripts/featured_image_agent.py` (DALL-E) | 2 pts |
| `style-memory` | `src/tools/style_memory_tool.py` (ChromaDB) | 1 pt |
| **Total** | | **13 pts (1 sprint)** |

After Phase 1, the framework decision can be made with hands-on MCP experience and concrete data on integration effort.

---

## Financial Implications

### Current Redundancy

The project pays for three LLM providers but only actively uses one (GPT-4o via CrewAI). Claude and Gemini are paid for but underutilised or unused.

| Consolidation Scenario | Providers | Monthly API Estimate (52 articles/year) |
|------------------------|-----------|----------------------------------------|
| **Status quo** (GPT-4o reasoning + DALL-E) | OpenAI + Claude sub + Copilot sub + Gemini sub | ~$42/yr API + ~$50/mo subscriptions |
| **Claude reasoning + DALL-E images** | Anthropic + OpenAI (DALL-E only) | ~$50/yr API + ~$20/mo Claude sub + $19/mo Copilot |
| **GPT-4o reasoning + DALL-E images** | OpenAI only | ~$38/yr API + ~$20/mo OpenAI sub + $19/mo Copilot |
| **Mixed (Sonnet + Haiku tiering)** | Anthropic + OpenAI (DALL-E only) | ~$26/yr API + ~$20/mo Claude sub + $19/mo Copilot |

**Key insight:** API costs for article generation are negligible (~$1/month). The real spend is subscriptions. The framework decision should not be driven by per-token pricing.

**Gemini evaluation:** If Google Cloud APIs are not serving a specific function in the pipeline, consider cancelling the subscription. If there is a planned use (e.g., Vertex AI Search for RAG, Gemini Flash for cost-optimised subtasks), document it before Phase 2.

---

## Recommendation

**No recommendation is made.** The decision depends on how the decision maker weights the objectives:

- **If vendor independence is paramount** → Option A (CrewAI Upgrade) or Option D (LangGraph)
- **If autonomous execution with guardrails is paramount** → Option B (Agent SDK) or Option C (Claude Code)
- **If migration risk minimisation is paramount** → Option A (CrewAI Upgrade)
- **If long-term architectural soundness is paramount** → Option D (LangGraph) or Option B (Agent SDK)

**What IS recommended:**
1. Execute Phase 1 (MCP server extraction) immediately — it is prerequisite to all options and risk-free
2. Evaluate Gemini subscription — cancel or document its purpose
3. After Phase 1, run a 1-sprint proof-of-concept with the top two options against the same 3-article generation benchmark, then decide

---

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-05 | ADR proposed | Research completed by four parallel agents |
| _pending_ | Phase 1 approved | _awaiting review_ |
| _pending_ | Framework selected | _awaiting Phase 1 completion + PoC results_ |

---

## Research Sources

### Anthropic Agent SDK
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Python SDK Reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)

### MCP Protocol
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [Python MCP SDK (FastMCP)](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Server Registry (5,800+ servers)](https://github.com/modelcontextprotocol/servers)
- [MCP Roadmap 2026](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [AAIF under Linux Foundation](https://www.infoq.com/news/2025/12/agentic-ai-foundation/)

### CrewAI
- [CrewAI v1.13.0 Changelog](https://docs.crewai.com/en/changelog)
- [CrewAI Flows Documentation](https://docs.crewai.com/en/concepts/flows)
- [CrewAI MCP Integration](https://docs.crewai.com/en/mcp/overview)
- [Manager-Worker Architecture Failures](https://towardsdatascience.com/why-crewais-manager-worker-architecture-fails-and-how-to-fix-it/)
- [CrewAI 2026 Complete Review](https://ai-coding-flow.com/blog/crewai-review-2026/)

### Claude Code
- [Claude Code Sub-agents](https://code.claude.com/docs/en/sub-agents)
- [Multi-Agent PR Review Analysis](https://lilting.ch/en/articles/claude-code-multi-agent-pr-review)
- [Multi-Agent Orchestration (Open Source)](https://www.theunwindai.com/p/claude-code-s-hidden-multi-agent-orchestration-now-open-source)

### LangGraph
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Best Multi-Agent Frameworks 2026](https://gurusup.com/blog/best-multi-agent-frameworks-2026)
- [AI Agent Frameworks 2026: Trade-offs](https://www.morphllm.com/ai-agent-framework)

### Pricing
- [AI API Pricing Comparison 2026](https://intuitionlabs.ai/articles/ai-api-pricing-comparison-grok-gemini-openai-claude)
- [LLM API Pricing 2026](https://www.tldl.io/resources/llm-api-pricing-2026)

### GitHub & Tool Stack
- [GitHub MCP Server](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/use-the-github-mcp-server)
- [DALL-E MCP Server](https://github.com/Jezweb/openai-mcp)
- [Vertex AI Agent Builder](https://cloud.google.com/products/agent-builder)
