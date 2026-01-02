# Documentation Index

Welcome to the Economist Agents documentation! This page provides easy navigation to all guides, reports, and technical documentation.

## 🚀 Getting Started

**New to the project?** Start here:
1. [Main README](../README.md) - Overview, quick start, architecture
2. [SPRINT_4_COMPLETE.md](../SPRINT_4_COMPLETE.md) - Latest features and testing results
3. [METRICS_GUIDE.md](METRICS_GUIDE.md) - How to use the metrics dashboard

## 📊 Sprint 4 Reports (January 1, 2026)

The latest sprint delivered **metrics tracking** and **GenAI featured images**:

### Primary Reports
- [**SPRINT_4_COMPLETE.md**](../SPRINT_4_COMPLETE.md) ⭐ **START HERE**
  - Full delivery summary
  - Testing results
  - Production deployment status
  - Files changed and features added

- [**SPRINT_4_RETROSPECTIVE.md**](SPRINT_4_RETROSPECTIVE.md)
  - Complete sprint analysis
  - Story-by-story breakdown
  - Metrics comparison (Sprint 3 vs 4)
  - Learnings and action items
  - Sprint 5 recommendations

- [**SPRINT_4_PLAN.md**](SPRINT_4_PLAN.md)
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
