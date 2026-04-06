# ADR-0008: Agent Skill Governance — Delegation, Lifecycle, and Marketplace

**Status:** Proposed
**Date:** 2026-04-05
**Decision Maker:** Ouray Viney (Engineering Lead)
**Research:** Operational experience from Sprints 16-20 across Claude Code, GitHub Copilot, and Claude sub-agents; [ADR-0006](0006-agent-framework-selection.md) agent framework; [ADR-0007](0007-content-intelligence-engine.md) content intelligence engine

---

## Problem Statement

The economist-agents pipeline now has **14 skills**, **12 registered agents** (agent-registry-spec.md), and **3 execution runtimes** (Claude Code, GitHub Copilot, Claude sub-agents). Work gets done, but how it gets assigned, which skills apply, and whether skills are improving — all live in human memory, not in code.

**What we have:**

| Asset | Count | Status |
|-------|-------|--------|
| Skills (`skills/*/SKILL.md`) | 14 | Static, unversioned, no eval metrics |
| Agent definitions (`agent-registry-spec.md`) | 12 | Documented but not enforced |
| Execution runtimes | 3 | Claude Code, Copilot, sub-agents |
| Governance gates | Pipeline only | Approval gates between content stages |
| Delegation rules | 0 | Lives in human memory and chat history |

**What's missing:**

| Gap | Risk |
|-----|------|
| No delegation rules | Wrong agent gets assigned, destroys files (Copilot incident) or blocks on sequential work that could be parallel |
| No skill versioning | Can't tell if skill v2 produces better outcomes than v1 |
| No performance feedback | GA4/GSC data exists (Sprint 20) but doesn't flow back to evaluate skills |
| No skill discovery | New skills are hand-written; no mechanism to adopt community best practices |
| No skill evaluation | No way to answer "is our research-sourcing skill actually producing fresher sources?" |

---

## Objectives

| Priority | Objective | Measure of Success |
|----------|-----------|-------------------|
| **P0** | Codified delegation — given a story, deterministic agent assignment | `skills/agent-delegation/SKILL.md` consulted before every story assignment |
| **P0** | Skill versioning — track skill evolution with measurable outcomes | Every skill has `version`, `last_evaluated`, `eval_criteria` in frontmatter |
| **P1** | Performance-linked evaluation — GA4/GSC data feeds back to skill assessment | Quarterly skill scorecard: which skills correlate with high-engagement articles |
| **P1** | Skill schema — portable, self-describing, machine-readable | Standard frontmatter schema adopted across all 14 skills |
| **P2** | Marketplace readiness — skills can be exported, discovered, imported | Packaging spec that works with public registries |
| **P2** | Continuous improvement loop — skill improvements are data-driven, not ad-hoc | Improvement proposals reference performance data, not intuition |

---

## Decision 1: Agent Delegation Matrix

### Execution Runtimes

| Runtime | Strengths | Constraints | Assign When |
|---------|-----------|-------------|-------------|
| **Claude Code (primary)** | Full codebase context, orchestration, multi-file edits, browser automation, MCP tools | Single-threaded within conversation | Modifications to existing files, orchestration, architecture, debugging, multi-step workflows |
| **Claude Code sub-agents** | Parallel execution, isolated context, full tool access | No shared state between agents, cannot modify same files | Independent new file creation, parallel research, test writing |
| **GitHub Copilot** | Autonomous PR creation, CI integration | Destroys existing files when modifying (known issue); limited context window | **New file creation ONLY** — never assign modification stories |
| **Human** | Judgment, credentials, account access, approvals | Expensive, non-scalable | Credentials setup, account configuration, architecture approval, PR review |

### Assignment Rules

Given a story, apply these rules in order:

```
1. REQUIRES credentials/accounts/browser login?
   → Assign to HUMAN (with Claude Code browser assist via Playwright MCP)

2. MODIFIES existing files?
   → Assign to CLAUDE CODE (primary)
   → NEVER assign to Copilot (destroys files)

3. CREATES new file(s) with NO dependencies between them?
   → Assign to CLAUDE CODE SUB-AGENTS (parallel)
   → Alternative: Copilot (if file is self-contained)

4. CREATES new file(s) with dependencies?
   → Assign to CLAUDE CODE (sequential)

5. RESEARCH or EXPLORATION task?
   → Assign to CLAUDE CODE SUB-AGENT (Explore type)

6. ARCHITECTURE decision?
   → Assign to CLAUDE CODE with Plan agent first
   → Requires HUMAN approval before implementation
```

### Governance Gates

| Gate | When | Who Approves |
|------|------|-------------|
| Sprint planning | Before stories are assigned | Human (engineering lead) |
| Architecture decisions | ADRs, schema changes, new agent types | Human review |
| PR review | Before merge to main | Human (or automated CI for test-only PRs) |
| Skill changes | Before modifying existing skills | Human review of performance data justification |
| Credential access | Any new service account or API key | Human executes |

---

## Decision 2: Skill Schema

### Current State

Skills are markdown files with no standard structure. Some have sections, some don't. None have version numbers or evaluation criteria.

### Proposed Schema

Every skill MUST have this frontmatter:

```yaml
---
name: research-sourcing
version: 1.0.0
description: One-line purpose of this skill
category: content-pipeline | content-intelligence | engineering | governance
author: ouray.viney
created: 2026-01-15
last_evaluated: 2026-04-05

# Which agents use this skill (from agent-registry-spec.md)
agents:
  - Researcher
  - Scout

# How to measure if this skill is working
eval_criteria:
  - metric: source_freshness_ratio
    description: "Ratio of sources from current/previous year"
    target: ">= 0.6"
    source: article-evaluator
  - metric: source_diversity_score
    description: "Number of distinct source types per article"
    target: ">= 3 of 5 types"
    source: article-evaluator

# Skills this one depends on
dependencies: []

# Skills that should be applied alongside this one
complements:
  - economist-writing
---
```

### Migration Plan

| Phase | Action | Effort |
|-------|--------|--------|
| 1 | Add frontmatter to all 14 existing skills | 1 sprint, Copilot (new content at top of files) |
| 2 | Create `scripts/skill_evaluator.py` that reads eval_criteria and checks article outputs | 2 points |
| 3 | Wire skill evaluator into post-publish pipeline | 1 point |

---

## Decision 3: Performance-Linked Skill Evaluation

### The Feedback Loop

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Skills      │───>│  Agents      │───>│  Articles     │───>│  GA4/GSC    │
│  (v1.0.0)    │    │  execute     │    │  published    │    │  measures   │
└─────────────┘    └─────────────┘    └──────────────┘    └──────┬──────┘
      ^                                                          │
      │            ┌─────────────────────────────────────────────┘
      │            v
      │     ┌──────────────┐    ┌──────────────────┐
      └─────│  Skill        │<───│  Quarterly        │
            │  Evaluator    │    │  Skill Scorecard  │
            └──────────────┘    └──────────────────┘
```

### Evaluation Cadence

| Frequency | Action | Owner |
|-----------|--------|-------|
| Per article | Article evaluator scores against skill criteria | Automated (Editor agent) |
| Weekly | GA4/GSC ETL updates performance.db | Automated (scripts/ga4_etl.py, gsc_etl.py) |
| Quarterly | Skill scorecard: correlate skill criteria scores with GA4 engagement | Human-triggered, agent-generated |
| On demand | Skill improvement proposal: "skill X correlates with low engagement — here's why" | Agent-generated, human-approved |

### Scorecard Output

```
Skill Scorecard — Q2 2026
══════════════════════════════════════════════
Skill                  Version  Articles  Avg Score  Avg Engagement  Correlation
─────────────────────  ───────  ────────  ─────────  ──────────────  ───────────
research-sourcing      1.0.0    12        4.2/5      0.73            +0.61 ↑
economist-writing      1.0.0    12        3.8/5      0.68            +0.45
editorial-illustration 1.0.0    12        4.5/5      0.71            +0.12
article-evaluation     1.0.0    12        4.0/5      0.70            +0.33

Recommendation: research-sourcing has strongest correlation with engagement.
                editorial-illustration scores high but weak engagement link.
                Consider: illustration quality may not drive engagement.
```

---

## Decision 4: Skill Marketplace Specification

### Packaging Format

A skill is a directory with a standard structure:

```
skills/research-sourcing/
├── SKILL.md              # Skill definition (with frontmatter schema)
├── CHANGELOG.md          # Version history with rationale
├── examples/             # Example inputs/outputs demonstrating the skill
│   ├── good-example.md
│   └── bad-example.md
├── eval/                 # Evaluation fixtures
│   └── test_cases.yaml   # Input/expected-output pairs for benchmarking
└── meta.yaml             # Machine-readable metadata (mirrors SKILL.md frontmatter)
```

### Discovery and Import

| Phase | Mechanism | Timeline |
|-------|-----------|----------|
| **Now** | Manual: browse GitHub repos tagged `agent-skill`, copy skill directory | Sprint 21 |
| **Next** | Registry: `skills.json` index file listing available skills with metadata | Sprint 23 |
| **Future** | CLI: `python scripts/skill_manager.py install <repo>/<skill>` | Sprint 25+ |

### Import Protocol

When importing a community skill:

1. **Evaluate** — run the skill's `eval/test_cases.yaml` against your pipeline
2. **Benchmark** — compare output quality against your current skill for the same category
3. **Adapt** — fork and modify for your voice/standards (skills are starting points, not rigid templates)
4. **Version** — imported skills get `version: 1.0.0-imported` until locally validated
5. **Attribute** — `author` field tracks original source

### Contribution Model

To contribute a skill back to the community:

1. Skill must have complete frontmatter schema
2. Must include at least 2 examples (good + bad)
3. Must include eval test cases
4. Must have been evaluated against at least 5 articles
5. Strip any proprietary data from examples
6. License: MIT (default) or as specified

---

## Decision 5: Governance Skill

A new skill `skills/agent-delegation/SKILL.md` codifies the delegation matrix as an executable reference that agents consult before story assignment. See the companion file for the full skill definition.

---

## Implementation Roadmap

| Sprint | Stories | Points | Outcome |
|--------|---------|--------|---------|
| **20** (current) | ADR-003 + delegation skill | 5 | Governance framework codified |
| **21** | Add frontmatter to 14 existing skills | 3 | All skills versioned and evaluable |
| **21** | Create skill evaluator script | 2 | Automated skill scoring |
| **22** | Wire skill evaluator into post-publish pipeline | 1 | Feedback loop operational |
| **23** | Quarterly skill scorecard generator | 2 | Performance-linked evaluation |
| **25+** | Skill marketplace CLI | 3 | Import/export/discover community skills |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-governance slows velocity | Stories take longer to assign than to implement | Keep delegation rules to 6 simple rules, not a policy document |
| Skill versioning becomes bureaucratic | Teams avoid updating skills | Auto-increment version on any SKILL.md change via pre-commit hook |
| Marketplace skills don't fit our voice | Imported skills produce off-brand content | Mandatory adaptation step; never use community skills verbatim |
| Correlation ≠ causation in skill scoring | Bad skill changes based on spurious correlations | Require 10+ articles before drawing conclusions; human approval on all skill changes |

---

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent delegation | 6-rule assignment matrix in `skills/agent-delegation/SKILL.md` | Simple, deterministic, covers all current runtimes |
| Skill schema | YAML frontmatter with version, eval_criteria, agents, dependencies | Machine-readable, backward-compatible with existing markdown |
| Feedback loop | Quarterly scorecards correlating skill scores with GA4 engagement | Actionable cadence without over-reacting to noise |
| Marketplace | Directory-based packaging, manual import now, CLI later | Start simple, evolve based on actual community engagement |
| Governance | Human approves architecture + skill changes; agents execute within boundaries | Matches existing sprint discipline and PR review model |
