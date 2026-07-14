# Economist-Agents Documentation Hub

> This documentation is also available at [oviney.github.io/economist-agents](https://oviney.github.io/economist-agents)

Welcome to the documentation for the Economist-Agents project -- a multi-agent content generation system that produces publication-quality blog posts in The Economist's signature style.

---

## Getting Started

**New to the project?** Start here:

1. **[Main README](../README.md)** - Project overview, installation, and quick start
2. **[Contributing Guidelines](../CONTRIBUTING.md)** - Development workflow, TDD, quality gates
3. **[Agent System Overview](../AGENTS.md)** - Multi-agent architecture and usage
4. **[Installation Guide](guides/CONTINUE_SETUP.md)** - Detailed setup instructions

## User Guides

### Development & Setup
- **[Blog Deployment](guides/BLOG_DEPLOYMENT.md)** - Deploy generated articles to blog repository
- **[CI/CD Monitoring](guides/CI_MONITORING_GUIDE.md)** - Monitor GitHub Actions and quality gates
- **[Copilot Integration](guides/COPILOT_SYNC.md)** - Sync agent patterns with GitHub Copilot
- **[Workflow Guide](guides/WORKFLOW_GUIDE.md)** - Development workflows and best practices
- **[Validation Reference](guides/VALIDATION_QUICK_REF.md)** - Quick validation commands
- **[Python Version Troubleshooting](guides/PYTHON_VERSION_TROUBLESHOOTING.md)** - Python environment fixes

### Implementation Guides
- **[Agentic Phase 1 Plan](guides/AGENTIC_PHASE_1_PLAN.md)** - Multi-agent system implementation
- **[Implementation Roadmap](guides/IMPLEMENTATION_ROADMAP.md)** - Feature development roadmap
- **[Quality Improvement Plan](guides/QUALITY_IMPROVEMENT_PLAN.md)** - Quality enhancement strategies
- **[Git Performance Fix](guides/GIT_PERFORMANCE_FIX_REPORT.md)** - Git workflow optimizations
- **[Skills Synthesizer](guides/SKILL_SYNTHESIZER_GUIDE.md)** - Agent skills management

## Architecture & Design

### Architecture Decision Records

All ADRs live in `docs/adr/` with a single global MADR numbering sequence. See [skills/adr-governance](../skills/adr-governance/SKILL.md) for the rules. Consolidated from three competing directories in Sprint 21 (Story #177).

- **[ADR-0001: Extract Agent Definitions to YAML](adr/0001-extract-agent-definitions-to-yaml.md)** — Accepted
- **[ADR-0002: Agent Registry Pattern](adr/0002-agent-registry-pattern.md)** — Accepted
- **[ADR-0003: Phased CrewAI Migration](adr/0003-phased-crewai-migration.md)** — **Superseded by ADR-0006**
- **[ADR-0004: Python Version Constraint](adr/0004-python-version-constraint.md)** — Accepted
- **[ADR-0005: Agile Discipline Enforcement](adr/0005-agile-discipline-enforcement.md)** — Accepted
- **[ADR-0006: Agent Framework Selection](adr/0006-agent-framework-selection.md)** — supersedes ADR-0003 (CrewAI retired; Anthropic Agent SDK adopted)
- **[ADR-0007: Content Intelligence Engine](adr/0007-content-intelligence-engine.md)**
- **[ADR-0008: Agent Skill Governance](adr/0008-agent-skill-governance.md)**
- **[ADR-0009: Architecture Audit Rubric](adr/0009-architecture-audit-rubric.md)**
- **[ADR-0010: Migrate domain modules from scripts/ to src/](adr/0010-scripts-to-src-migration.md)** — Accepted (implemented via #344)
- **[ADR-0011: Opt-in Recursive Deep Research](adr/0011-opt-in-recursive-deep-research.md)**

Use [docs/adr/TEMPLATE.md](adr/TEMPLATE.md) when writing a new ADR.

### System Architecture
- **[Flow-Based Orchestration](FLOW_ARCHITECTURE.md)** - Deterministic state-machine design
- **[Autonomous Orchestration Strategy](AUTONOMOUS_ORCHESTRATION_STRATEGY.md)** - Autonomous agent coordination
- **[Architecture Patterns](ARCHITECTURE_PATTERNS.md)** - Prompts-as-code, persona voting, sequential orchestration
- **[Agent Registry Spec](agent-registry-spec.md)** - Agent registration and discovery
- **[Quality System](DEFINITION_OF_DONE.md)** - Quality gates and validation layers

## Skills

The `skills/` directory holds **39 `SKILL.md` workflow definitions**. See
[`skills/README.md`](../skills/README.md) for the full library. They fall into two groups.

### Lifecycle skills (from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) — govern all work)
- **[using-agent-skills](../skills/using-agent-skills/SKILL.md)** — meta-skill: maps a task to the right phase skill
- **[idea-refine](../skills/idea-refine/SKILL.md)** — clarify vague requests before speccing
- **[spec-driven-development](../skills/spec-driven-development/SKILL.md)** — spec → review → plan → review → implement
- **[planning-and-task-breakdown](../skills/planning-and-task-breakdown/SKILL.md)** — dependency graph before sprint planning
- **[incremental-implementation](../skills/incremental-implementation/SKILL.md)** — thin, tested, committed slices
- **[test-driven-development](../skills/test-driven-development/SKILL.md)** — RED → GREEN → REFACTOR
- **[code-review-and-quality](../skills/code-review-and-quality/SKILL.md)** — multi-axis review before merge
- **[shipping-and-launch](../skills/shipping-and-launch/SKILL.md)** — pre-launch checklist and staged rollout
- **[context-engineering](../skills/context-engineering/SKILL.md)** — focus context at session start
- Plus supporting engineering skills: `api-and-interface-design`, `debugging-and-error-recovery`,
  `deprecation-and-migration`, `git-workflow-and-versioning`, `performance-optimization`,
  `security-and-hardening`, `source-driven-development`, `documentation-and-adrs`,
  `ci-cd-and-automation`, `code-simplification`, `frontend-ui-engineering`,
  `browser-testing-with-devtools`.

### Domain skills
- **[economist-writing](../skills/economist-writing/SKILL.md)** — the writing standard for every article
- **[research-sourcing](../skills/research-sourcing/SKILL.md)** — source freshness, diversity, attribution
- **[editorial-illustration](../skills/editorial-illustration/SKILL.md)** — featured images and chart visuals
- **[article-evaluation](../skills/article-evaluation/SKILL.md)** — score articles on 5 quality dimensions
- **[visual-qa](../skills/visual-qa/SKILL.md)** — validate Economist-style charts for publication
- **[quality-gates](../skills/quality-gates/SKILL.md)** — multi-layer automated checks
- **[python-quality](../skills/python-quality/SKILL.md)** — Python coding standards
- **[testing](../skills/testing/SKILL.md)** — testing patterns for the pipeline
- **[defect-prevention](../skills/defect-prevention/SKILL.md)** — pattern → rule → test
- **[devops](../skills/devops/SKILL.md)** — CI/CD and infrastructure
- **[observability](../skills/observability/SKILL.md)** — quality metrics over time and alerting
- **[architecture-patterns](../skills/architecture-patterns/SKILL.md)** — multi-agent design and audit rubric
- **[agent-delegation](../skills/agent-delegation/SKILL.md)** — routing stories to the right agent runtime
- **[agent-traceability](../skills/agent-traceability/SKILL.md)** — structured agent action audit trails
- **[adr-governance](../skills/adr-governance/SKILL.md)** — ADR numbering, supersession, lifecycle
- **[mcp-development](../skills/mcp-development/SKILL.md)** — MCP server development standards
- **[sprint-management](../skills/sprint-management/SKILL.md)** — sprint lifecycle management
- **[scrum-master](../skills/scrum-master/SKILL.md)** — ceremony enforcement and performance

## Scripts & Tools

### Key Scripts
- `python -m src.agent_sdk.pipeline "<topic>"` - Stage 3 (draft + chart), then pauses for the image handshake
- `python -m src.agent_sdk.pipeline --resume <slug>` - Stage 4 (finalise) after the image is supplied
- `src/economist_agents/flow.py` - Flow orchestration (`run_flow`)
- `scripts/topic_scout.py` - Topic discovery and ranking
- `scripts/editorial_board.py` - Multi-persona voting system
- `scripts/generate_chart.py` - Economist-style chart creation
- `scripts/featured_image_agent.py` - DALL·E featured-image generation
- `scripts/publication_validator.py` - Final publication quality gate
- `scripts/quality_dashboard.py` - Quality tracking dashboard
- `scripts/blog_quality_audit.py` - Blog validation
- `scripts/deploy_to_blog.py` - Deploy an approved article to the blog repo

> Note: `scripts/economist_agent.py` is **deprecated** (it emits a warning); the pipeline
> now runs through `src/agent_sdk/`.

### Content Intelligence ETL
- `scripts/ga4_etl.py` - Google Analytics 4 data extraction pipeline
- `scripts/gsc_etl.py` - Google Search Console data extraction pipeline

## Technical Reference

### API & Integration
- **[Agent Prompt Patterns](AGENT_PROMPT_PATTERNS.md)** - Prompt engineering patterns
- **[Agent Quality Gates](AGENT_QUALITY_GATES.md)** - Gate definitions and thresholds
- **[Quality Dashboard](QUALITY_DASHBOARD.md)** - Metrics and quality tracking
- **[Changelog](CHANGELOG.md)** - Complete development history

### Current Development
- **[Backlog](../BACKLOG.md)** - Source of record for planning items (`B-NNN`). PRs live on GitHub via the `gh` CLI.
- **[Project Operating Mode & Standards](../CLAUDE.md)** - Lifecycle discipline, skill routing, coding standards
- **[Sprint Discipline Guide](SPRINT_DISCIPLINE_GUIDE.md)** - Sprint process and ceremonies

> Historical sprint planning lives in [`../SPRINT.md`](../SPRINT.md) and the
> [sprint archive](archive/sprints/). Day-to-day work is now tracked in `BACKLOG.md`.

## Historical Archive

### Sprint Reports
- **[Sprint Reports](archive/sprints/)** - Complete sprint execution records
- **[Sprint Logs](sprint_logs/)** - Detailed sprint session logs

### Story Completions
- **[Story Reports](archive/stories/)** - Individual story implementation details

### System Reports
- **[CI/CD Reports](archive/ci-reports/)** - Build and deployment history
- **[Bug Reports](archive/bugs/)** - Issue analysis and resolutions

## Performance & Metrics

- **[Agent Velocity Analysis](AGENT_VELOCITY_ANALYSIS.md)** - Agent throughput metrics
- **[Metrics Guide](METRICS_GUIDE.md)** - Dashboard commands and quality trend interpretation
- **[Chart Design Spec](CHART_DESIGN_SPEC.md)** - Economist visual style rules and matplotlib templates

---

## Quick Navigation

### For New Contributors
1. [Main README](../README.md) -- [Contributing](../CONTRIBUTING.md) -- [Installation](guides/CONTINUE_SETUP.md)
2. [Agent Overview](../AGENTS.md) -- [Architecture](FLOW_ARCHITECTURE.md)

### For Developers
1. [Quality System](DEFINITION_OF_DONE.md) -- [Workflow Guide](guides/WORKFLOW_GUIDE.md) -- [Backlog](../BACKLOG.md)
2. [CI/CD Guide](guides/CI_MONITORING_GUIDE.md) -- [Deployment](guides/BLOG_DEPLOYMENT.md) -- [Validation](guides/VALIDATION_QUICK_REF.md)

### For Architects
1. [ADR-0006 Framework](adr/0006-agent-framework-selection.md) — [ADR-0007 Content Intelligence](adr/0007-content-intelligence-engine.md) — [ADR-0008 Skill Governance](adr/0008-agent-skill-governance.md)
2. [Flow Architecture](FLOW_ARCHITECTURE.md) — [Architecture Patterns](ARCHITECTURE_PATTERNS.md)

### For Project Managers
1. [Backlog](../BACKLOG.md) -- [Sprint Archive](archive/sprints/) -- [Story Archive](archive/stories/)
2. [Quality Dashboard](QUALITY_DASHBOARD.md) -- [CI Reports](archive/ci-reports/) -- [Velocity Analysis](AGENT_VELOCITY_ANALYSIS.md)

---

## External Links

- [GitHub Repository](https://github.com/oviney/economist-agents)
- [Open Issues](https://github.com/oviney/economist-agents/issues)
- [Pull Requests](https://github.com/oviney/economist-agents/pulls)
- [MkDocs Site](https://oviney.github.io/economist-agents)

---

**Last Updated**: July 14, 2026
**Planning source of record**: [`BACKLOG.md`](../BACKLOG.md)
**LLM**: Claude (Anthropic) primary · OpenAI for DALL·E images only
