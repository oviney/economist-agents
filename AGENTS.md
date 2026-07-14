# Agents

This repository uses two distinct sets of agents:

1. **Development & process agents** — the fleet that *builds and maintains* the
   pipeline (code quality, testing, review, DevOps, planning). Defined in
   `.github/agents/*.agent.md` and loaded by the registry. **This document covers these.**
2. **Content-pipeline agents** — the agents that *produce articles* (topic scout,
   editorial board, researcher, writer, editor, graphics). Defined as YAML under
   `agents/`. See [`agents/README.md`](agents/README.md).

---

## Agent registry

Development agents follow the **Agent Registry Pattern**
([ADR-0002](docs/adr/0002-agent-registry-pattern.md)). Definitions are stored as
`.agent.md` files in `.github/agents/` and loaded at runtime by
`scripts/agent_registry.py`.

```python
from scripts.agent_registry import AgentRegistry

registry = AgentRegistry()
registry.list_agents()               # -> ['architect', 'code-quality-specialist', ...]
config = registry.get_agent_config("scrum-master")
agent  = registry.get_agent("po-agent")     # optional model override: get_agent(name, model=...)
```

### Definition format

Each `.agent.md` file is YAML frontmatter followed by the agent's system prompt:

```yaml
---
name: architect
description: AI Architect for designing, validating, and auditing multi-agent systems
model: claude-sonnet-4-20250514
tools:
  - bash
  - file_search
skills:
  - skills/architecture-patterns
  - skills/agent-delegation
  - skills/adr-governance
---

# AI Architect Agent
You are an AI Architect specialising in multi-agent systems...
```

Required frontmatter fields: `name`, `description`, `model`, `tools`, `skills`
(validated by the architecture audit rubric — see
[ADR-0009](docs/adr/0009-architecture-audit-rubric.md)).

---

## The 10 development agents

| Agent | Role | Skills |
|-------|------|--------|
| **@architect** | Designs, validates, and audits multi-agent architecture; authors ADRs | `architecture-patterns`, `agent-delegation`, `adr-governance`, `spec-driven-development`, `using-agent-skills` |
| **@code-quality-specialist** | TDD-based refactoring and coding-standard enforcement | `python-quality` |
| **@code-reviewer** | Code review, architecture validation, best-practice enforcement | `code-review-and-quality` |
| **@devops** | CI/CD automation and deployment infrastructure | `devops`, `ci-cd-and-automation`, `quality-gates` |
| **@git-operator** | Git workflows, branch management, release coordination | `git-workflow-and-versioning` |
| **@po-agent** | Product strategy, user stories, acceptance criteria | product/backlog patterns |
| **@product-research-agent** | Market analysis and competitive intelligence | research methodologies |
| **@scrum-master** | Sprint orchestration and Agile ceremonies | `scrum-master`, `sprint-management` |
| **@test-specialist** | Test strategy, unit/integration tests, coverage | `testing`, `test-driven-development` |
| **@visual-qa-agent** | Chart and design validation | `visual-qa` |

> The `model`, `tools`, and `skills` for each agent are the source of truth in its
> `.agent.md` file — the table above summarises them. Run
> `python scripts/architecture_audit.py` to validate every definition against the
> compliance rubric (6 dimensions × 0–2 pts; ≥85% threshold).

---

## Using agents

Development agents are invoked by name in the agentic workflow:

```text
@code-quality-specialist  Fix all ruff/pyright violations in scripts/
@test-specialist          Add tests for src/agent_sdk/stage4_runner.py
@code-reviewer            Review the current diff for correctness and security
@architect                Validate this proposed crew config against the rubric
@scrum-master             Break B-004 into dependency-ordered tasks
```

### Dispatching worker agents

When dispatching agents via the `Agent` tool to orchestrate the fleet, the brief
**must** include the worker discipline contract from
[`docs/worker-brief-contract.md`](docs/worker-brief-contract.md). Workers that
produce output without evidence of `Skill` invocations are rejected and re-dispatched.

---

## How agents relate to skills

Every agent references one or more `skills/*/SKILL.md` workflows. Skills are the
**single source of truth** for *how* work is done; agents are *who* does it. The six
lifecycle skills (`spec-driven-development`, `planning-and-task-breakdown`,
`incremental-implementation`, `test-driven-development`, `code-review-and-quality`,
`shipping-and-launch`) govern all work regardless of which agent is acting. See
[`CLAUDE.md`](CLAUDE.md) for the skill-routing contract and
[`skills/README.md`](skills/README.md) for the full library.

---

## Content-pipeline agents

The agents that actually write articles are configured separately as YAML under
`agents/` and run through the Anthropic Agent SDK
(`src/agent_sdk/`). They are **not** in the registry above. The pipeline flow is:

- **Topic scout** (`agents/discovery/`) → candidate topics
- **Editorial board** (`agents/editorial_board/`) → weighted vote across seven personas
- **Content generation** (`agents/content_generation/`) → researcher → writer → editor → graphics

See [`agents/README.md`](agents/README.md) for their schema, loader, and weights.

---

## Related documentation

- **[Agent Registry Pattern (ADR-0002)](docs/adr/0002-agent-registry-pattern.md)**
- **[Extract Agent Definitions to YAML (ADR-0001)](docs/adr/0001-extract-agent-definitions-to-yaml.md)**
- **[Agent Framework Selection (ADR-0006)](docs/adr/0006-agent-framework-selection.md)** — CrewAI retired; Anthropic Agent SDK adopted
- **[Skills library](skills/README.md)** · **[Flow architecture](docs/FLOW_ARCHITECTURE.md)** · **[Definition of Done](docs/DEFINITION_OF_DONE.md)**
