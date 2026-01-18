# Economist-Agents Documentation

Welcome to the comprehensive documentation for the Economist-Agents project! This multi-agent content generation system produces publication-quality blog posts in The Economist's signature style.

## 🚀 Getting Started

**New to the project?** Start here:

1. **[Main README](../README.md)** - Project overview, installation, and quick start
2. **[Contributing Guidelines](../CONTRIBUTING.md)** - Development workflow, TDD, quality gates
3. **[Agent System Overview](../AGENTS.md)** - Multi-agent architecture and usage
4. **[Installation Guide](guides/CONTINUE_SETUP.md)** - Detailed setup instructions

## 📖 User Guides

### Development & Setup
- **[Blog Deployment](guides/BLOG_DEPLOYMENT.md)** - Deploy generated articles to blog repository
- **[CI/CD Monitoring](guides/CI_MONITORING_GUIDE.md)** - Monitor GitHub Actions and quality gates
- **[Copilot Integration](guides/COPILOT_SYNC.md)** - Sync agent patterns with GitHub Copilot
- **[Workflow Guide](guides/WORKFLOW_GUIDE.md)** - Development workflows and best practices
- **[Validation Reference](guides/VALIDATION_QUICK_REF.md)** - Quick validation commands

### Implementation Guides
- **[Agentic Phase 1 Plan](guides/AGENTIC_PHASE_1_PLAN.md)** - Multi-agent system implementation
- **[Implementation Roadmap](guides/IMPLEMENTATION_ROADMAP.md)** - Feature development roadmap
- **[Quality Improvement Plan](guides/QUALITY_IMPROVEMENT_PLAN.md)** - Quality enhancement strategies
- **[Git Performance Fix](guides/GIT_PERFORMANCE_FIX_REPORT.md)** - Git workflow optimizations
- **[Skills Synthesizer](guides/SKILL_SYNTHESIZER_GUIDE.md)** - Agent skills management

## 🏗️ Architecture & Design

### Architecture Decision Records (ADRs)
- **[ADR-001: Agent Configuration Extraction](architecture/ADR-001-agent-configuration-extraction.md)**
- **[ADR-002: Agent Registry Pattern](architecture/ADR-002-agent-registry-pattern.md)**
- **[ADR-003: CrewAI Migration Strategy](architecture/ADR-003-crewai-migration-strategy.md)**
- **[ADR-002 Refactoring Complete](architecture/ADR-002-REFACTORING-COMPLETE.md)**

### System Architecture
- **[Flow-Based Orchestration](FLOW_ARCHITECTURE.md)** - Deterministic state-machine design
- **[CrewAI Context Architecture](CREWAI_CONTEXT_ARCHITECTURE.md)** - Shared context system
- **[Quality System](DEFINITION_OF_DONE.md)** - Quality gates and validation layers

## 📚 Technical Reference

### API & Integration
- **[CrewAI API Reference](CREWAI_API_REFERENCE.md)** - Complete API documentation
- **[Quality Dashboard](QUALITY_DASHBOARD.md)** - Metrics and quality tracking
- **[Changelog](CHANGELOG.md)** - Complete development history

### Current Development
- **[Current Sprint](../SPRINT.md)** - Sprint 15 progress and goals
- **[Project Standards](../CLAUDE.md)** - Python coding standards and requirements

## 📦 Historical Archive

### Sprint Reports
- **[Sprint Reports](archive/sprints/)** - Complete sprint execution records
  - Sprint 4, 6, 8, 9, 14, 15 completion reports
  - Execution summaries and retrospectives
  - Performance metrics and learnings

### Story Completions
- **[Story Reports](archive/stories/)** - Individual story implementation details
  - Story 1-7 complete implementations
  - Production deployment reports
  - Validation and acceptance criteria

### System Reports
- **[CI/CD Reports](archive/ci-reports/)** - Build and deployment history
  - Coverage analysis and test results
  - Performance improvements and fixes
  - Quality gate implementations

- **[Bug Reports](archive/bugs/)** - Issue analysis and resolutions
  - Security bug summaries
  - Performance issue fixes
  - Validation reports

## 🎯 Quick Navigation

### For New Contributors
1. [Main README](../README.md) → [Contributing](../CONTRIBUTING.md) → [Installation](guides/CONTINUE_SETUP.md)
2. [Agent Overview](../AGENTS.md) → [Architecture](FLOW_ARCHITECTURE.md) → [API Reference](CREWAI_API_REFERENCE.md)

### For Developers
1. [Quality System](DEFINITION_OF_DONE.md) → [Workflow Guide](guides/WORKFLOW_GUIDE.md) → [Current Sprint](../SPRINT.md)
2. [CI/CD Guide](guides/CI_MONITORING_GUIDE.md) → [Deployment](guides/BLOG_DEPLOYMENT.md) → [Validation](guides/VALIDATION_QUICK_REF.md)

### For Architects
1. [ADR Collection](architecture/) → [Flow Architecture](FLOW_ARCHITECTURE.md) → [Context System](CREWAI_CONTEXT_ARCHITECTURE.md)
2. [Implementation Roadmap](guides/IMPLEMENTATION_ROADMAP.md) → [Quality Plan](guides/QUALITY_IMPROVEMENT_PLAN.md)

### For Project Managers
1. [Current Sprint](../SPRINT.md) → [Sprint Archive](archive/sprints/) → [Story Archive](archive/stories/)
2. [Quality Dashboard](QUALITY_DASHBOARD.md) → [CI Reports](archive/ci-reports/) → [Performance History](archive/)

---

**💡 Can't find what you're looking for?**
- Check the [main README](../README.md) for project overview
- Browse [architecture decisions](architecture/) for design rationale
- Review [archive folders](archive/) for historical context
- See [guides](guides/) for step-by-step instructions
  - Original sprint planning
  - Story definitions and acceptance criteria
  - Risk assessment
  - Time estimates

## 📖 User Guides

### Core Functionality
- [**METRICS_GUIDE.md**](METRICS_GUIDE.md) - **Essential Reading**
  - Dashboard commands and usage
  - Quality trend interpretation
  - Agent performance monitoring
  - Prediction accuracy tracking
  - Troubleshooting
  - CI/CD integration examples

- [**CHART_DESIGN_SPEC.md**](CHART_DESIGN_SPEC.md)
  - Economist visual style rules
  - Layout zones specification
  - Label positioning guidelines
  - Color palette and typography
  - Complete matplotlib templates
  - Validation checklist

### Integration & Expertise
- [**JEKYLL_EXPERTISE.md**](JEKYLL_EXPERTISE.md)
  - Jekyll integration patterns
  - Common pitfalls and fixes
  - Configuration best practices
  - SEO optimization
  - Performance tips
  - Validation checks

- [**SKILLS_LEARNING.md**](SKILLS_LEARNING.md)
  - Self-learning validation system
  - Skills database explained
  - Learning process
  - Pattern categories
  - Usage examples
  - Benefits and future enhancements

## 🏗️ Architecture & Development

### System Design
- [**ARCHITECTURE_PATTERNS.md**](ARCHITECTURE_PATTERNS.md)
  - Prompts-as-code pattern
  - Persona-based voting
  - Sequential orchestration
  - JSON intermediate format
  - Structured output specification
  - Continuous learning validation

### Development History
- [**CHANGELOG.md**](CHANGELOG.md)
  - Feature additions
  - Bug fixes (BUG-001 through BUG-017)
  - Production issues resolved
  - Enhancement history

- [**SPRINT.md**](../SPRINT.md)
  - Active sprint tracking
  - Story point estimation
  - Sprint goals and progress
  - Team velocity trends

## 🔧 Technical Reference

### Agent System
- **Research Agent** - Data verification and sourcing
- **Writer Agent** - Economist-style article drafting
- **Editor Agent** - Quality gates and style enforcement
- **Graphics Agent** - Chart generation with visual QA
- **Featured Image Agent** - DALL-E 3 editorial illustrations (NEW in Sprint 4)

### Key Scripts
- `scripts/economist_agent.py` - Main article generation orchestrator
- `scripts/topic_scout.py` - Topic discovery and ranking
- `scripts/editorial_board.py` - Multi-persona voting system
- `scripts/generate_chart.py` - Economist-style chart creation
- `scripts/featured_image_agent.py` - GenAI illustration generation (NEW)
- `scripts/metrics_dashboard.py` - Performance tracking dashboard (NEW)
- `scripts/blog_qa_agent.py` - Blog validation with self-learning
- `scripts/skills_manager.py` - Skills persistence engine

### Configuration Files
- `copilot-instructions.md` - AI pair programming guidance
- `requirements.txt` - Python dependencies
- `skills/agent_metrics.json` - Performance tracking data
- `skills/blog_qa_skills.json` - Learned validation patterns

## 📈 Metrics & Quality

### Dashboard Commands
```bash
# View quality trends
python3 scripts/metrics_dashboard.py --trend

# Agent performance drill-down
python3 scripts/metrics_dashboard.py --agent writer_agent

# Prediction accuracy
python3 scripts/metrics_dashboard.py --accuracy

# Export report
python3 scripts/metrics_dashboard.py --export report.md
```

### Quality Standards
- Quality Score: 98/100 (A+)
- Test Pass Rate: 11/11 (100%)
- Agent Performance Targets:
  - Research Agent: >80% verification rate
  - Writer Agent: >70% clean draft rate
  - Editor Agent: 100% gate pass rate
  - Graphics Agent: >80% visual QA pass rate

## 🐛 Known Issues & Fixes

### Recently Resolved
- **BUG-016**: Charts generated but not embedded (FIXED)
- **BUG-017**: Duplicate chart display (FIXED)
- **BUG-015**: Missing category tags (FIXED)

See [CHANGELOG.md](CHANGELOG.md) for complete history.

## 🚀 Sprint Planning

### Sprint 4 Summary (COMPLETE)
- **Points**: 9/9 (100%)
- **Duration**: 1 day (accelerated)
- **Quality**: 98/100 (A+)
- **Features**:
  - ✅ Agent metrics tracking
  - ✅ GenAI featured images
  - ✅ Comprehensive documentation

### Sprint 5 Recommendations
- Improve Writer Agent (reduce regenerations)
- Improve Editor Agent (prediction accuracy)
- Add metrics CI/CD gates
- Expand skills categories

See [SPRINT_4_RETROSPECTIVE.md](SPRINT_4_RETROSPECTIVE.md) for detailed Sprint 5 planning.

## 🔗 External Links

- [GitHub Repository](https://github.com/oviney/economist-agents)
- [Open Issues](https://github.com/oviney/economist-agents/issues)
- [Pull Requests](https://github.com/oviney/economist-agents/pulls)

## 📝 Contributing

Want to contribute? See:
1. Active sprint in [SPRINT.md](../SPRINT.md)
2. Open issues on GitHub
3. Architecture patterns in [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md)
4. Development history in [CHANGELOG.md](CHANGELOG.md)

## 📞 Support

- **Documentation Issues**: Open an issue on GitHub
- **Feature Requests**: Add to backlog via GitHub Issues
- **Bug Reports**: See [CHANGELOG.md](CHANGELOG.md) for template

---

**Last Updated**: January 1, 2026
**Current Sprint**: Sprint 4 (COMPLETE)
**Quality Score**: 98/100 (A+)
**Status**: Production Ready ✅
