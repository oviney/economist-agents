# Skills

This directory holds **`SKILL.md` workflow definitions** — the operational
playbooks that govern how work is done in this repository. Skills are the **single
source of truth** for *how* to do something; the content-pipeline agents
([`agents/`](../agents/README.md)) are *who* does it.

Skill routing follows the upstream
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) guide as the
single source of truth for skill semantics and lifecycle. See
[`CLAUDE.md`](../CLAUDE.md) for the non-negotiable routing contract.

> **Not to be confused with** `agents/skills_configs/` — that directory holds reusable
> *agent YAML templates*, documented in
> [`agents/skills_configs/README.md`](../agents/skills_configs/README.md). This README
> covers the `SKILL.md` workflow definitions only.

---

## Lifecycle skills (govern all work)

Every non-trivial task moves through these phases in order. Improvising the lifecycle
by hand instead of invoking the skill is a blocker.

| Phase | Skill | Purpose |
|-------|-------|---------|
| triage | `using-agent-skills` | Meta-skill: maps a task to the right phase skill |
| context | `context-engineering` | Focus context at session start |
| refine | `idea-refine` | Clarify vague requests before speccing |
| spec | `spec-driven-development` | Spec → human review → plan → human review → implement |
| plan | `planning-and-task-breakdown` | Dependency graph before sprint planning |
| build | `incremental-implementation` | Thin slices, each tested and committed |
| test | `test-driven-development` | RED → GREEN → REFACTOR |
| review | `code-review-and-quality` | Multi-axis review before merge |
| ship | `shipping-and-launch` | Pre-launch checklist, staged rollout, rollback |

Supporting engineering skills used throughout the lifecycle: `api-and-interface-design`,
`source-driven-development`, `debugging-and-error-recovery`, `deprecation-and-migration`,
`git-workflow-and-versioning`, `performance-optimization`, `security-and-hardening`,
`documentation-and-adrs`, `ci-cd-and-automation`, `code-simplification`,
`frontend-ui-engineering`, `browser-testing-with-devtools`.

---

## Domain skills (this project)

| Skill | Purpose |
|-------|---------|
| `economist-writing` | The writing standard for every article in the pipeline |
| `research-sourcing` | Source freshness, diversity, and attribution requirements |
| `editorial-illustration` | Visual standards for featured images and charts |
| `article-evaluation` | Score articles on 5 quality dimensions deterministically |
| `visual-qa` | Validate Economist-style charts for publication |
| `quality-gates` | Multi-layer automated checks at commit, push, and CI |
| `python-quality` | Python coding standards for the pipeline |
| `testing` | Testing patterns for the multi-agent system |
| `defect-prevention` | Codify failure patterns as deterministic prevention rules |
| `devops` | Infrastructure automation and CI/CD health |
| `observability` | Track article quality metrics over time and alert on degradation |
| `architecture-patterns` | Multi-agent design patterns and audit rubric |
| `agent-delegation` | Route stories to the correct agent runtime |
| `agent-traceability` | Structured JSON audit trail for every agent action |
| `adr-governance` | ADR numbering, supersession, and lifecycle rules |
| `mcp-development` | Standards for building MCP servers in this project |
| `sprint-management` | Sprint lifecycle management |
| `scrum-master` | Ceremony enforcement and data-driven performance |

Each skill lives at `skills/<name>/SKILL.md`. Some carry `references/` and
supporting assets alongside the `SKILL.md`.

---

## Adding or modifying a skill

1. Follow the structure of an existing `SKILL.md` (frontmatter + workflow body).
2. Keep the skill focused on **one** workflow; cross-reference rather than duplicate.
3. If it changes the lifecycle, update the routing contract in [`CLAUDE.md`](../CLAUDE.md).
4. See the [documentation-and-adrs](documentation-and-adrs/SKILL.md) skill for how to
   record the decision.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the review checklist.
