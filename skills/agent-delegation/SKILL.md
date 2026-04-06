---
name: agent-delegation
version: 1.0.0
description: Rules for assigning stories to the correct agent runtime with appropriate constraints
category: governance
author: ouray.viney
created: 2026-04-05
last_evaluated: 2026-04-05

agents:
  - Product Owner
  - Scrum Master

eval_criteria:
  - metric: assignment_accuracy
    description: "Percentage of stories assigned to correct runtime without rework"
    target: ">= 0.95"
    source: sprint-retrospective
  - metric: parallel_utilization
    description: "Percentage of independent stories executed in parallel vs sequential"
    target: ">= 0.70"
    source: sprint-retrospective

dependencies: []

complements:
  - sprint-management
  - quality-gates
---

# Agent Delegation Skill

## Purpose

Determine which agent runtime executes a given story, with what
constraints, and under what governance. This skill prevents
misassignment incidents (e.g., Copilot modifying existing files)
and maximizes parallel execution throughput.

## Agent Runtimes

### Claude Code (Primary)
- **Role:** Orchestrator. Reads, edits, and coordinates across the
  full codebase.
- **Strengths:** Full context window, multi-file edits, MCP tool
  access, browser automation via Playwright, sub-agent spawning.
- **Assign when:** Story modifies existing files, requires
  orchestration across multiple files, or needs interactive
  debugging.

### Claude Code Sub-Agents
- **Role:** Parallel workers. Execute independent tasks
  concurrently.
- **Strengths:** Parallel execution, isolated context prevents
  interference, full tool access.
- **Constraints:** Cannot share state or modify the same files.
  Each agent works on its own files.
- **Assign when:** Two or more new files need creation with no
  dependencies between them. Research tasks that can run
  concurrently.

### GitHub Copilot
- **Role:** Autonomous PR creator for isolated new files.
- **Strengths:** Creates PRs with CI integration, works
  asynchronously.
- **Constraints:** DESTROYS existing files when asked to modify
  them. Limited context window. Cannot access MCP tools.
- **Assign when:** Story creates a single new self-contained file
  with no imports from files being concurrently modified.
- **NEVER assign when:** Story modifies any existing file.

### Human
- **Role:** Governance, credentials, judgment calls.
- **Strengths:** Access to accounts, passwords, approval authority,
  strategic judgment.
- **Assign when:** Story requires credential setup, account
  configuration, architecture approval, or involves sensitive
  operations on shared infrastructure.

## Assignment Rules

Apply these rules in order. First match wins.

### Rule 1: Credentials Required
```
IF story requires login, API keys, account setup, or browser auth
THEN assign to HUMAN
     Claude Code assists via Playwright MCP for navigation
```

### Rule 2: Modifies Existing Files
```
IF story modifies any existing file in the codebase
THEN assign to CLAUDE CODE (primary)
     NEVER assign to Copilot
```

### Rule 3: Multiple Independent New Files
```
IF story creates 2+ new files with NO dependencies between them
THEN assign to CLAUDE CODE SUB-AGENTS (parallel)
     Each agent creates one file + its tests
     Primary Claude Code orchestrates and verifies
```

### Rule 4: Single New File with Dependencies
```
IF story creates new file(s) that import from existing code
THEN assign to CLAUDE CODE (primary, sequential)
```

### Rule 5: Research or Exploration
```
IF story is pure research (no code changes)
THEN assign to CLAUDE CODE SUB-AGENT (Explore type)
     Results feed back to primary for synthesis
```

### Rule 6: Architecture Decision
```
IF story produces an ADR, schema change, or new agent type
THEN assign to CLAUDE CODE with Plan agent first
     REQUIRES human approval before implementation begins
```

## Governance Gates

| Gate | Trigger | Approver |
|------|---------|----------|
| Sprint planning | Before any story assignment | Human |
| Architecture review | ADRs, new agent types, schema changes | Human |
| PR review | Before merge to main | Human |
| Skill modification | Any change to `skills/*/SKILL.md` | Human (must cite performance data) |
| Credential operations | New API keys, service accounts | Human executes directly |
| Destructive git ops | Force push, reset, branch delete | Human confirms explicitly |

## Anti-Patterns

### 1. Assigning Copilot to Modify Existing Files
**What happens:** Copilot rewrites entire files, losing existing
logic, comments, and structure.
**Rule:** Copilot creates new files ONLY.

### 2. Sequential Execution of Independent Stories
**What happens:** Sprint takes 3x longer than necessary.
**Rule:** If stories touch different files with no shared state,
launch sub-agents in parallel.

### 3. Skipping Human Approval on Architecture
**What happens:** Agents make structural decisions that conflict
with project direction.
**Rule:** ADRs and schema changes require human sign-off before
implementation.

### 4. Ad-Hoc Work Without Sprint Tracking
**What happens:** Work products are untraceable, no GitHub issue
trail, no PR linkage.
**Rule:** Non-trivial work gets a GitHub issue before
implementation begins.

## Example: Sprint 20 Delegation

Story 20.1 (credentials setup):
- Requires account access and browser login
- **Rule 1 applies** -> Human + Claude Code (Playwright assist)

Story 20.2 (GA4 ETL script):
- Creates new file `scripts/ga4_etl.py`
- No dependency on Story 20.3

Story 20.3 (GSC ETL script):
- Creates new file `scripts/gsc_etl.py`
- No dependency on Story 20.2

Stories 20.2 + 20.3:
- **Rule 3 applies** -> Claude Code sub-agents (parallel)
- Result: both completed in ~2.5 minutes vs ~5 minutes sequential

Story 20.4 (ADR-003):
- Architecture decision
- **Rule 6 applies** -> Claude Code with human approval
