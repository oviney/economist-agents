# Agent Registry Specification

Canonical reference for the Claude Code sub-agent architecture. Each agent is instantiated as a Claude Code sub-agent (`AgentDefinition`) with the skills, MCP tools, and model tier specified below.

This replaces the previous CrewAI-based agent definitions.

---

## Agent Summary

| Agent | Category | Replaces | Model | Skills | MCP Tools |
|-------|----------|----------|-------|--------|-----------|
| Researcher | Content Pipeline | Stage 3 Research task | sonnet | research-sourcing | web-researcher, style-memory |
| Writer | Content Pipeline | Stage 3 Writer task | opus | economist-writing | style-memory |
| Illustrator | Content Pipeline | Stage 3 Graphics task | haiku | editorial-illustration | image-generator (DALL-E) |
| Editor | Content Pipeline | Stage 4 Editorial Review | sonnet | article-evaluation, economist-writing | article-evaluator, publication-validator |
| Publisher | Content Pipeline | deploy_to_blog.py manual invocation | haiku | devops | blog-deployer, GitHub Copilot MCP |
| Analyst | Content Intelligence | New (ADR-002) | sonnet | content-intelligence (new) | GA4 MCP, GSC MCP |
| Scout | Content Intelligence | topic_scout.py + editorial board | sonnet | research-sourcing | web-researcher, style-memory |
| Developer | Engineering | code-quality-specialist + test-specialist | opus | python-quality, testing, defect-prevention | GitHub Copilot MCP, built-in (Read, Edit, Bash, Grep, Glob) |
| Reviewer | Engineering | code-reviewer | sonnet | quality-gates, python-quality | GitHub Copilot MCP, built-in (Read, Grep, Glob) |
| Ops | Engineering | devops + git-operator (merged) | haiku | devops, sprint-management, quality-gates | GitHub Copilot MCP, built-in (Bash) |
| Product Owner | Governance | po-agent | sonnet | sprint-management | GitHub Copilot MCP (issues, projects, milestones) |
| Scrum Master | Governance | scrum-master | sonnet | scrum-master, sprint-management, agent-traceability | GitHub Copilot MCP, observability tools |

---

## Content Pipeline Agents

### Researcher

- **Replaces:** Stage 3 Research task
- **Skills:** research-sourcing
- **MCP Tools:** web-researcher, style-memory
- **Model:** sonnet
- **Purpose:** Find fresh, diverse sources (3+ from current/previous year). Search web, arXiv, and company engineering blogs. Check style memory for voice consistency.

### Writer

- **Replaces:** Stage 3 Writer task
- **Skills:** economist-writing
- **MCP Tools:** style-memory
- **Model:** opus
- **Purpose:** Draft Economist-style articles. Must follow 10 rules from economist-writing skill. Query style memory for voice patterns. 700-1000 words, British spelling, thesis-driven, no lists in prose.

### Illustrator

- **Replaces:** Stage 3 Graphics task
- **Skills:** editorial-illustration
- **MCP Tools:** image-generator (DALL-E)
- **Model:** haiku
- **Purpose:** Generate DALL-E prompt following editorial illustration skill (painterly, human figures, no text, muted colours). Call image-generator MCP to produce PNG.

### Editor

- **Replaces:** Stage 4 Editorial Review
- **Skills:** article-evaluation, economist-writing
- **MCP Tools:** article-evaluator, publication-validator
- **Model:** sonnet
- **Purpose:** 5-gate quality review (opening, evidence, voice, structure, visual). Run article-evaluator MCP for deterministic scoring. Run publication-validator for final gate. Reject if <80% or critical failures.

### Publisher

- **Replaces:** deploy_to_blog.py manual invocation
- **Skills:** devops
- **MCP Tools:** blog-deployer, GitHub Copilot MCP
- **Model:** haiku
- **Purpose:** Deploy article to blog repo via PR. Copy images (PNG + webp). Create PR with review checklist.

---

## Content Intelligence Agents (ADR-002)

### Analyst

- **Replaces:** New agent (no predecessor)
- **Skills:** content-intelligence (new skill needed)
- **MCP Tools:** GA4 MCP (google-analytics-mcp), GSC MCP (google-search-console-mcp-python)
- **Model:** sonnet
- **Purpose:** Pull weekly performance data. Compute composite engagement scores. Identify top/bottom performers. Find content gaps from GSC keyword data (high impressions, low CTR, no matching article).

### Scout

- **Replaces:** topic_scout.py + editorial board enhancement
- **Skills:** research-sourcing
- **MCP Tools:** web-researcher, style-memory (topic dedup collection)
- **Model:** sonnet
- **Purpose:** Monitor HN, Reddit, dev.to for trending developer topics. Score sentiment velocity. Detect consensus topics (>80% one direction) as contrarian opportunities. Check published article archive for dedup (>0.8 similarity = reject).

---

## Engineering Agents

### Developer

- **Replaces:** code-quality-specialist + test-specialist
- **Skills:** python-quality, testing, defect-prevention
- **MCP Tools:** GitHub Copilot MCP, built-in (Read, Edit, Bash, Grep, Glob)
- **Model:** opus
- **Purpose:** TDD implementation. Write failing tests first, then implement. Type hints mandatory. Docstrings required. >80% coverage. Mock external APIs in tests.

### Reviewer

- **Replaces:** code-reviewer
- **Skills:** quality-gates, python-quality
- **MCP Tools:** GitHub Copilot MCP, built-in (Read, Grep, Glob)
- **Model:** sonnet
- **Purpose:** Architecture and code quality review. Check for OWASP top 10 vulnerabilities. Verify test coverage. Review PR diffs for file gutting (Copilot guardrail).

### Ops

- **Replaces:** devops + git-operator (merged)
- **Skills:** devops, sprint-management, quality-gates
- **MCP Tools:** GitHub Copilot MCP, built-in (Bash)
- **Model:** haiku
- **Purpose:** Branch management, CI/CD operations, commit with proper standards, push with sprint story references.

---

## Governance Agents

### Product Owner

- **Replaces:** po-agent
- **Skills:** sprint-management
- **MCP Tools:** GitHub Copilot MCP (issues, projects, milestones)
- **Model:** sonnet
- **Purpose:** Generate user stories with acceptance criteria (Given/When/Then). Estimate story points (1pt = 2.8hrs, 3pt cap). Prioritise backlog. Create GitHub issues.

### Scrum Master

- **Replaces:** scrum-master
- **Skills:** scrum-master, sprint-management, agent-traceability
- **MCP Tools:** GitHub Copilot MCP, observability tools
- **Model:** sonnet
- **Purpose:** Validate Definition of Ready (8-point checklist). Plan sprints in SPRINT.md. Track progress. Enforce quality gates (DoR, commit standards, PR linkage). Generate retrospectives.

---

## Dropped Agents

| Former Agent | Disposition |
|---|---|
| product-research-agent | Absorbed into Scout |
| visual-qa-agent | Absorbed into Editor (image validation is a tool check, not an agent) |
| git-operator (separate) | Merged with devops into Ops |

---

## Model Tiering Strategy

| Tier | Model | Cost (input/output per 1M tokens) | Assigned Agents | Rationale |
|------|-------|------------------------------------|-----------------|-----------|
| Tier 1 | Opus | $5 / $25 | Writer, Developer | Quality-critical reasoning requiring deep analysis |
| Tier 2 | Sonnet | $3 / $15 | Researcher, Editor, Analyst, Scout, Reviewer, Product Owner, Scrum Master | Balanced cost-to-quality for structured tasks |
| Tier 3 | Haiku | $1 / $5 | Illustrator, Publisher, Ops | Mechanical tasks with well-defined inputs/outputs |

---

## Implementation Notes

- Each agent is defined as a Claude Code sub-agent (`AgentDefinition`) or `AGENTS.md` file.
- Skills are loaded as system prompt context (not separate tools).
- MCP tools are inherited from parent session or explicitly configured per agent.
- Agents communicate via the orchestrator-subagent pattern (results flow back to parent).
- No shared memory between agents -- state passes through the orchestrator.
- Budget caps: `max_budget_usd` set per agent invocation to prevent runaway costs.
