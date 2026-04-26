---
name: architecture-patterns
description: Reference patterns for designing and reviewing CrewAI multi-agent systems. Use when designing a new crew or flow, reviewing a proposed agent configuration, or auditing an existing system against industry conventions.
---

# Architecture Patterns

## Overview

The reference for the AI Architect agent and any reviewer evaluating CrewAI multi-agent designs. Anchors decisions to documented CrewAI / AutoGen patterns and to the in-repo precedents in `src/economist_agents/flow.py`, `src/crews/stage3_crew.py`, and `src/crews/stage4_crew.py`. The goal is to prevent reinvention — every recommendation should cite a pattern, not an opinion.

## When to Use

- Designing a new crew, flow, or agent
- Reviewing a proposed agent config (frontmatter, tools, skills, body)
- Auditing an existing system for compliance (target ≥85%)
- Weighing trade-offs between sequential / hierarchical / Flow orchestration
- Writing an ADR for a structural change

### When NOT to Use

- For story decomposition — that's `agent-delegation`
- For ADR formatting and numbering — that's `adr-governance`
- For Python coding standards — that's `python-quality`

## Core Patterns

### CrewAI

| Pattern | Use when | Avoid when |
|---------|----------|-----------|
| **Sequential `Crew`** | 2–5 step pipeline, each task feeds the next | Steps can run in parallel |
| **Hierarchical `Crew`** | Manager delegates to specialists with branching | Pipeline is strictly linear |
| **`Flow` with `@start` / `@listen` / `@router`** | Stateful multi-stage orchestration with branching, retries, gates | A single crew suffices |
| **`Task(context=[upstream])`** | Downstream task needs upstream output | Tasks are independent |
| **`Agent(memory=True)`** | Multi-turn reasoning across tasks | One-shot generation — costs tokens |
| **`Agent(tools=[...])`** | Agent needs deterministic capability | A skill or prompt rule suffices |
| **`Agent(reasoning=True)`** | Strategic planning before action | Routine generation |

In-repo precedents:

- `src/economist_agents/flow.py` — Flow with research → write → edit → validate gate
- `src/crews/stage3_crew.py` — Sequential crew (Writer → Graphics → Editor)
- `src/crews/stage4_crew.py` — Deterministic post-processing, NOT a crew (intentional — no LLM)

### AutoGen (referenced for patterns, not used in this repo)

- `AssistantAgent` + `UserProxyAgent` — split LLM work from tool execution.
- `GroupChat` — turn-taking among ≥3 agents with a manager picking the next speaker.
- Function calling vs tool calling — function calling is per-turn, tool calling is structured.

Use AutoGen patterns as a reference for naming and topology, even when implementing in CrewAI.

### Anti-Patterns

| Anti-pattern | Symptom | Fix |
|-------------|---------|-----|
| **Context starvation** | Downstream task re-derives state | Add `context=[upstream_task]` |
| **Hidden coupling** | Two agents share assumed shape with no schema | Define a Pydantic model or JSON schema |
| **Sequential when hierarchical fits** | Fan-out work coerced into a chain | Switch to hierarchical crew or Flow router |
| **Hierarchical when sequential fits** | Manager overhead on a 2-step chain | Drop manager, use sequential crew |
| **Tool sprawl** | Single agent with >5 tools | Split into specialists |
| **Memory by default** | `memory=True` without retrieval requirement | Disable; only enable when state is reused |
| **Flow-vs-Crew confusion** | Flow used for sequential single-agent work | Use a Crew |

## Configuration Rubric

Every agent file under `.github/agents/*.agent.md` is scored 0–2 on six dimensions (max 12). Compliance score = `(total / 12) × 100`. System compliance = mean across all agents. **Threshold: 85%.**

| Dimension | 0 | 1 | 2 |
|-----------|---|---|---|
| **Frontmatter completeness** | Missing or unparseable | `name`+`description` only | `name`, `description`, `model`, `tools`, `skills` all present |
| **Role clarity** | Generic ("AI assistant") | Specific but overlaps another agent | Specific and non-overlapping |
| **Tool minimality** | No tools or kitchen-sink list | Reasonable but unjustified | Each tool justified by a concrete responsibility |
| **Skills mapping** | No skills referenced | Listed but not used in body | Explicitly invoked in instructions |
| **Body cohesion** | Stream of consciousness | Sectioned but rambling | Sectioned with quality gates / output format |
| **Output contract** | None | Implied | Explicit format (JSON shape, Markdown template, return type) |

The audit script `scripts/architecture_audit.py` automates the deterministic dimensions (frontmatter completeness, basic body cohesion, tool count). Subjective dimensions (role clarity, skills usage, output contract content) are scored heuristically and refined by the architect on review.

## Decision Format

Architectural decisions get an ADR (`docs/adr/NNNN-*.md`) following `docs/adr/TEMPLATE.md`. Always include a Mermaid diagram for structural changes. Always list ≥2 alternatives — if you can't, the decision isn't architecturally significant.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "A new agent will be cleaner than reusing an existing one" | Adding agents costs tokens and increases coordination overhead. Extend before fragmenting. |
| "Memory makes it smarter" | Memory adds tokens per turn. Only justified by a retrieval requirement, not by feel. |
| "Hierarchical is more flexible" | Hierarchical adds a manager. Use only when branching exists; otherwise sequential is faster and cheaper. |
| "Tools are free, add what we might need" | Tool sprawl confuses the model and bloats schemas. Each tool needs a justification. |
| "We'll add an ADR later" | Decisions without an ADR get reversed on the next refactor. Write it now. |
