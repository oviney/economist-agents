---
name: agent-architecture
description: Rules for designing, reviewing, and validating multi-agent systems with explicit contracts, diagrams, ADRs, security, and performance evidence.
---

# Agent Architecture

## Overview

Use this skill to design or review multi-agent systems. It keeps agents from growing into undocumented prompt bundles by requiring clear contracts, architecture diagrams, trade-off analysis, security review, performance review, and verification evidence.

The current production architecture is governed by ADR-0006: Anthropic Agent SDK plus MCP is the runtime, while CrewAI and AutoGen remain useful reference patterns. Do not reintroduce a deprecated runtime without a new ADR.

## When to Use

- Designing a new agent, crew, workflow, MCP server, or orchestration path
- Reviewing an `.agent.md` definition for role, goal, backstory, tools, and boundaries
- Comparing architecture options such as deterministic code, Agent SDK, MCP tools, CrewAI, AutoGen, or LangGraph
- Drafting or reviewing an ADR for framework, agent authority, tool access, data flow, or security decisions
- Auditing an existing multi-agent system for compliance, bottlenecks, and production readiness

### When NOT to Use

- Small prompt copy edits with no architecture or authority change
- Pure content-generation work where the agent topology is unchanged
- Runtime debugging after the architecture is already fixed; use the debugging workflow instead

## Core Process

### 1. Establish the Contract

Document each agent's role, goal, backstory, tools, model, skills, input schema, output schema, owner, escalation rule, and success metric. Missing contracts are findings, not implementation details.

### 2. Map the Workflow

Use C4 context/container views for system boundaries and Mermaid sequence diagrams for agent handoffs. Identify state ownership, shared context, retries, and human review gates.

### 3. Compare Proven Patterns

Compare at least two viable patterns before recommending one. Use repository ADRs first, then established framework patterns from CrewAI, AutoGen, Agent SDK, MCP, or other accepted references. State why each rejected option is worse for this repository.

### 4. Review Risk

Cover security implications, credential management, tool permissions, prompt injection, untrusted data, file-system scope, external API exposure, latency, token budget, cache opportunities, rate limits, and rollback.

### 5. Produce Evidence

Return an architecture compliance score on a 0-100 scale. A production-ready design must score above 85 and include tests, observability, rollback, and linked evidence from files, ADRs, skills, or framework documentation.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "The prompt explains the architecture" | Prompts are not enough; contracts and diagrams make handoffs reviewable |
| "CrewAI has a pattern for this, so use CrewAI" | ADR-0006 controls the runtime; use CrewAI as a reference unless a new ADR changes the decision |
| "This agent only needs one more tool" | Every new tool changes the security boundary and needs justification |
| "We can measure performance later" | Latency, token budget, and rate limits shape the design and must be considered before production |
| "A score is subjective" | A structured score forces explicit findings and makes review trends visible |

## Red Flags

- Agent has tools but no permission boundary or credential handling guidance
- Workflow has serial LLM calls without latency or budget analysis
- Agent outputs are free-form where downstream code expects structured data
- Design skips alternatives and jumps straight to implementation
- Recommendation contradicts an accepted ADR without proposing a superseding ADR
- No human review gate for production behavior, tool authority, or external writes
- Architecture compliance score is above 85 without tests, rollback, and observability evidence

## Verification

- [ ] Every agent has role, goal, backstory, tools, model, skills, inputs, outputs, owner, and escalation rule
- [ ] Non-trivial workflows include C4 or Mermaid diagrams
- [ ] At least two architecture options are compared with pros, cons, and risks
- [ ] Recommendation cites repository ADRs or established framework patterns
- [ ] Security review covers credentials, tool permissions, prompt injection, and untrusted data
- [ ] Performance review covers latency, token budget, context pressure, caching, and rate limits
- [ ] Architecture compliance score is calculated and justified
- [ ] Production-ready claims include tests, observability, rollback, and human review gates
