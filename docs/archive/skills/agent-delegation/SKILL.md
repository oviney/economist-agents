---
name: agent-delegation
description: Rules for assigning stories to the correct agent runtime with appropriate constraints. Use when planning sprint assignments, when deciding between Claude Code / Copilot / Human for a story, when launching parallel sub-agents.
---

# Agent Delegation

## Overview

Determines which agent runtime executes a given story, with what constraints, and under what governance. Prevents misassignment incidents (e.g., Copilot modifying existing files) and maximises parallel execution throughput.

## When to Use

- Sprint planning: assigning stories to runtimes
- Deciding whether a story needs Claude Code, Copilot, sub-agents, or human
- Launching parallel sub-agents for independent work
- Reviewing whether an assignment follows governance rules

### When NOT to Use

- For sprint ceremony process — that's `sprint-management`
- For ADR creation and review — that's `adr-governance`
- For code quality standards — that's `python-quality`

## Core Process

### Agent Runtimes

| Runtime | Role | Strengths | Constraints |
|---------|------|-----------|-------------|
| **Claude Code** | Orchestrator | Full context, multi-file edits, MCP tools, Playwright, sub-agents | — |
| **Claude Code Sub-Agents** | Parallel workers | Concurrent execution, isolated context | Cannot share state or modify same files |
| **GitHub Copilot** | Autonomous PR creator | Creates PRs with CI, works async | **DESTROYS existing files**. Limited context. No MCP. |
| **Human** | Governance | Credentials, approval, strategic judgment | — |

### Assignment Rules (first match wins)

```
Rule 1: Credentials Required
  → HUMAN (Claude Code assists via Playwright)

Rule 2: Modifies Existing Files
  → CLAUDE CODE (NEVER Copilot)

Rule 3: Multiple Independent New Files
  → CLAUDE CODE SUB-AGENTS (parallel)

Rule 4: Single New File with Dependencies
  → CLAUDE CODE (sequential)

Rule 5: Research or Exploration
  → CLAUDE CODE SUB-AGENT (Explore type)

Rule 6: Architecture Decision
  → CLAUDE CODE + Plan agent, REQUIRES human approval
```

### Governance Gates

| Gate | Trigger | Approver |
|------|---------|----------|
| Sprint planning | Before any story assignment | Human |
| Architecture review | ADRs, new agent types, schema changes | Human |
| PR review | Before merge to main | Human |
| Skill modification | Any change to `skills/*/SKILL.md` | Human (must cite data) |
| Credential operations | New API keys, service accounts | Human executes directly |
| Destructive git ops | Force push, reset, branch delete | Human confirms explicitly |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Copilot can handle this small edit to an existing file" | Copilot rewrites entire files, losing existing logic and structure — assign to Claude Code |
| "We'll run these stories sequentially, it's simpler" | Independent stories executed sequentially take 2-3x longer; sub-agents run them in parallel |
| "We don't need human approval for this architecture change" | Agents making structural decisions without governance creates direction conflicts — ADRs need sign-off |
| "Let's just do it without a GitHub issue" | Untraceable work products break sprint discipline and audit trail |
| "Sub-agents can coordinate on shared files" | Sub-agents have isolated context; sharing state between them causes race conditions and overwrites |

## Red Flags

- Copilot assigned to a story that modifies existing files
- Independent stories executed sequentially instead of in parallel
- Architecture decision made without human approval gate
- Work started without a GitHub issue
- Sub-agents assigned to modify the same file
- Credential operation attempted by an agent instead of human
- Story assignment doesn't match any rule in the assignment matrix

## Verification

- [ ] Every story has a designated runtime before implementation begins — **evidence**: sprint plan includes runtime column
- [ ] No Copilot assignments touch existing files — **evidence**: Copilot stories only create new files
- [ ] Independent stories run in parallel where possible — **evidence**: sub-agent logs show concurrent execution
- [ ] Architecture decisions have human approval — **evidence**: GitHub issue comment from human before implementation
- [ ] All work has a GitHub issue — **evidence**: every PR references an issue number
- [ ] Governance gates enforced — **evidence**: PR review required, no force pushes without explicit approval
