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

### Architecture Decision Records (ADRs)

#### Current ADRs (docs/adr/)
- **[ADR-001: Agent Framework Selection](adr/ADR-001-agent-framework-selection.md)** - Framework choice and rationale
- **[ADR-002: Content Intelligence Engine](adr/ADR-002-content-intelligence-engine.md)** - GA4/GSC analytics pipeline, sentiment analysis, dedup, content gaps
- **[ADR-003: Agent Skill Governance](adr/ADR-003-agent-skill-governance.md)** - Skill lifecycle, ownership, quality standards

#### Legacy ADRs (docs/)
- **[ADR-001: Agent Configuration Extraction](ADR-001-agent-configuration-extraction.md)**
- **[ADR-002: Agent Registry Pattern](ADR-002-agent-registry-pattern.md)**
- **[ADR-003: CrewAI Migration Strategy](ADR-003-crewai-migration-strategy.md)**
- **[ADR-004: Python Version Constraint](ADR-004-python-version-constraint.md)**
- **[ADR-005: Agile Discipline Enforcement](ADR-005-agile-discipline-enforcement.md)**

### System Architecture
- **[Flow-Based Orchestration](FLOW_ARCHITECTURE.md)** - Deterministic state-machine design
- **[Autonomous Orchestration Strategy](AUTONOMOUS_ORCHESTRATION_STRATEGY.md)** - Autonomous agent coordination
- **[CrewAI Context Architecture](CREWAI_CONTEXT_ARCHITECTURE.md)** - Shared context system
- **[Architecture Patterns](ARCHITECTURE_PATTERNS.md)** - Prompts-as-code, persona voting, sequential orchestration
- **[Agent Registry Spec](agent-registry-spec.md)** - Agent registration and discovery
- **[Quality System](DEFINITION_OF_DONE.md)** - Quality gates and validation layers

## Skills

### Agent Skills
- **[Agent Delegation](../skills/agent-delegation/SKILL.md)** - Cross-agent task routing and delegation
- **[MCP Development](../skills/mcp-development/SKILL.md)** - Model Context Protocol server development patterns
- **[Research Sourcing](../skills/research-sourcing/SKILL.md)** - Data verification and sourcing
- **[Economist Writing](../skills/economist-writing/SKILL.md)** - Economist-style article drafting
- **[Editorial Illustration](../skills/editorial-illustration/SKILL.md)** - DALL-E 3 editorial illustrations
- **[Article Evaluation](../skills/article-evaluation/SKILL.md)** - Article quality evaluation
- **[Quality Gates](../skills/quality-gates/SKILL.md)** - Quality enforcement
- **[Python Quality](../skills/python-quality/SKILL.md)** - Python coding standards
- **[Testing](../skills/testing/SKILL.md)** - Test patterns and TDD
- **[Defect Prevention](../skills/defect-prevention/SKILL.md)** - Defect analysis and prevention
- **[DevOps](../skills/devops/SKILL.md)** - CI/CD and infrastructure
- **[Sprint Management](../skills/sprint-management/SKILL.md)** - Sprint planning and tracking
- **[Scrum Master](../skills/scrum-master/SKILL.md)** - Agile ceremonies and facilitation
- **[Agent Traceability](../skills/agent-traceability/SKILL.md)** - Agent action audit trails
- **[Observability](../skills/observability/SKILL.md)** - Monitoring and alerting

## Scripts & Tools

### Key Scripts
- `scripts/economist_agent.py` - Main article generation orchestrator
- `scripts/topic_scout.py` - Topic discovery and ranking
- `scripts/editorial_board.py` - Multi-persona voting system
- `scripts/generate_chart.py` - Economist-style chart creation
- `scripts/featured_image_agent.py` - GenAI illustration generation
- `scripts/metrics_dashboard.py` - Performance tracking dashboard
- `scripts/blog_qa_agent.py` - Blog validation with self-learning
- `scripts/skills_manager.py` - Skills persistence engine

### Content Intelligence ETL
- `scripts/ga4_etl.py` - Google Analytics 4 data extraction pipeline
- `scripts/gsc_etl.py` - Google Search Console data extraction pipeline

## Technical Reference

### API & Integration
- **[CrewAI API Reference](CREWAI_API_REFERENCE.md)** - Complete API documentation
- **[Agent Prompt Patterns](AGENT_PROMPT_PATTERNS.md)** - Prompt engineering patterns
- **[Agent Quality Gates](AGENT_QUALITY_GATES.md)** - Gate definitions and thresholds
- **[Quality Dashboard](QUALITY_DASHBOARD.md)** - Metrics and quality tracking
- **[Changelog](CHANGELOG.md)** - Complete development history

### Current Development
- **[Current Sprint](../SPRINT.md)** - Sprint 20 (active); Sprints 16-19 complete
- **[Project Standards](../CLAUDE.md)** - Python coding standards and requirements
- **[Sprint Discipline Guide](SPRINT_DISCIPLINE_GUIDE.md)** - Sprint process and ceremonies

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
2. [Agent Overview](../AGENTS.md) -- [Architecture](FLOW_ARCHITECTURE.md) -- [API Reference](CREWAI_API_REFERENCE.md)

### For Developers
1. [Quality System](DEFINITION_OF_DONE.md) -- [Workflow Guide](guides/WORKFLOW_GUIDE.md) -- [Current Sprint](../SPRINT.md)
2. [CI/CD Guide](guides/CI_MONITORING_GUIDE.md) -- [Deployment](guides/BLOG_DEPLOYMENT.md) -- [Validation](guides/VALIDATION_QUICK_REF.md)

### For Architects
1. [ADR-001 Framework](adr/ADR-001-agent-framework-selection.md) -- [ADR-002 Content Intelligence](adr/ADR-002-content-intelligence-engine.md) -- [ADR-003 Skill Governance](adr/ADR-003-agent-skill-governance.md)
2. [Flow Architecture](FLOW_ARCHITECTURE.md) -- [Context System](CREWAI_CONTEXT_ARCHITECTURE.md) -- [Architecture Patterns](ARCHITECTURE_PATTERNS.md)

### For Project Managers
1. [Current Sprint](../SPRINT.md) -- [Sprint Archive](archive/sprints/) -- [Story Archive](archive/stories/)
2. [Quality Dashboard](QUALITY_DASHBOARD.md) -- [CI Reports](archive/ci-reports/) -- [Velocity Analysis](AGENT_VELOCITY_ANALYSIS.md)

---

## External Links

- [GitHub Repository](https://github.com/oviney/economist-agents)
- [Open Issues](https://github.com/oviney/economist-agents/issues)
- [Pull Requests](https://github.com/oviney/economist-agents/pulls)
- [MkDocs Site](https://oviney.github.io/economist-agents)

---

**Last Updated**: April 5, 2026
**Current Sprint**: Sprint 20 (Active)
**Status**: Production Ready
