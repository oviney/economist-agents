# Multi-Agent System Documentation

The Economist-Agents project uses a sophisticated multi-agent architecture with 9 specialized AI agents that collaborate to produce publication-quality content and maintain development excellence.

## 🤖 Agent Registry System

Agents are automatically discovered via the Agent Registry Pattern (ADR-002). Agent definitions are stored as `.agent.md` files in the `.github/agents/` directory and loaded dynamically at runtime.

### Discovery Mechanism

```python
# Automatic agent discovery
registry = AgentRegistry()
all_agents = registry.create_all_agents()
available_agents = registry.list_agents()  # Returns 9 agents

# Get specific agent
po_agent = registry.get_agent("po-agent")
```

### Agent Configuration Format

Each agent definition includes:
- **Name & Description**: Role and responsibilities
- **Model**: Anthropic Claude Sonnet 4 (claude-sonnet-4-20250514)
- **Tools**: Available tools (bash, file_search, github_project_add_issue)
- **Skills**: Domain-specific knowledge patterns

## 📋 Available Agents

### Development & Quality Agents

#### **@code-quality-specialist**
- **Role**: TDD-based refactoring and quality standards enforcement
- **Responsibilities**: Type hints, docstrings, error handling, code modernization
- **Tools**: bash, file_search
- **Skills**: skills/python-quality
- **Workflow**: RED → GREEN → REFACTOR (strict TDD)

#### **@test-specialist**
- **Role**: Comprehensive test writing and quality assurance
- **Responsibilities**: Unit tests, integration tests, test coverage, test strategy
- **Tools**: bash, file_search
- **Skills**: skills/testing
- **Standards**: >80% coverage required, 100% for refactored code

#### **@devops**
- **Role**: CI/CD automation and deployment infrastructure
- **Responsibilities**: GitHub Actions, deployment pipelines, infrastructure automation
- **Tools**: bash, file_search
- **Skills**: skills/quality-gates

#### **@code-reviewer**
- **Role**: Code review and architectural guidance
- **Responsibilities**: Code review, architecture validation, best practices enforcement
- **Tools**: bash, file_search
- **Standards**: SOLID principles, maintainability, performance

### Project Management Agents

#### **@scrum-master**
- **Role**: Sprint orchestrator, process enforcer, and team facilitator
- **Responsibilities**: Sprint planning, backlog management, Agile ceremonies
- **Tools**: bash, github_project_add_issue
- **Skills**: skills/sprint-management
- **Process**: Two-stage intake (Minimal DoR → Full DoR → Sprint Planning)

#### **@po-agent** (Product Owner)
- **Role**: Product strategy and backlog refinement
- **Responsibilities**: User stories, acceptance criteria, business value prioritization
- **Tools**: bash, github_project_add_issue
- **Skills**: Product management patterns

#### **@product-research-agent**
- **Role**: Market analysis and competitive intelligence
- **Responsibilities**: Market research, competitive analysis, user needs assessment
- **Tools**: bash, file_search
- **Skills**: Research methodologies, market analysis

### Operations & Specialized Agents

#### **@git-operator**
- **Role**: Version control and repository management
- **Responsibilities**: Git workflows, branch management, release coordination
- **Tools**: bash, file_search
- **Standards**: Conventional commits, clean history, code review process

#### **@visual-qa-agent**
- **Role**: Chart and design validation
- **Responsibilities**: Visual quality assurance, chart validation, design consistency
- **Tools**: bash, file_search
- **Metrics**: 88% pass rate, 28.6% escape rate baseline

## 🎯 Agent Usage Examples

### Development Workflow
```bash
# Quality enforcement
@code-quality-specialist Fix all ruff/mypy violations in scripts/
@test-specialist Create comprehensive tests for scripts/editorial_board.py
@code-quality-specialist Add type hints to scripts/topic_scout.py

# Code review
@code-reviewer Review PR #123 for architectural compliance
@devops Set up CI/CD pipeline for new microservice
```

### Project Management
```bash
# Sprint management
@scrum-master Plan Sprint 16 with 13 story points capacity
@po-agent Create user stories for dark mode feature
@product-research-agent Analyze competitor blog platforms

# Operations
@git-operator Create release branch for v2.1.0
@visual-qa-agent Validate chart quality for Q4 report
```

## 🔧 Agent Integration with CrewAI

### Stage 3 Crew (Content Generation)
- **Research Agent**: Market analysis and content research
  - ✨ **NEW**: Fresh Academic Sources via arXiv API integration
  - 🔬 Access to cutting-edge 2026 research papers (vs stale 2023-2024 training data)
  - 📊 Real-time competitive intelligence from pre-publication academic research
  - 🎯 Business Value: Eliminates "dated sources" limitation, provides fresh insights
- **Writer Agent**: Article writing in Economist style
- **Graphics Agent**: Chart and visualization creation
- **Status**: ✅ Operational (100% test pass rate)

### Stage 4 Crew (Editorial Review)
- **Editor Agent**: 5-gate quality validation system
- **Quality Gates**: Opening, Evidence, Voice, Structure, Chart
- **Status**: ✅ Operational (95% gate pass rate target)

## 🛠️ Skills System Integration

Each agent has access to domain-specific skills stored in the `skills/` directory:

### Available Skills Categories
- **skills/python-quality**: Python coding standards and best practices
- **skills/testing**: Testing patterns, coverage standards, TDD workflows
- **skills/quality-gates**: CI/CD setup, pre-commit hooks, automation
- **skills/sprint-management**: Agile ceremonies, story management, velocity tracking

### Skills Loading
```python
# Agents automatically load their assigned skills
code_agent = registry.get_agent("code-quality-specialist")
# Automatically loads skills/python-quality patterns
```

## 🚀 Quick Start Guide

### 1. Agent Discovery
```python
from src.registry import AgentRegistry

# Initialize registry
registry = AgentRegistry()

# List all available agents
print(registry.list_agents())
# Output: ['code-quality-specialist', 'devops', 'git-operator', ...]
```

### 2. Create Agents
```python
# Create all agents
all_agents = registry.create_all_agents()

# Create specific agent
scrum_master = registry.get_agent("scrum-master")
```

### 3. Agent Collaboration
```python
# Agents work together through the context system
from scripts.context_manager import ContextManager

ctx = ContextManager("docs/STORY_N_CONTEXT.md")
# All agents share context automatically
```

## 📊 Agent Performance Metrics

| Agent | Success Rate | Average Response Time | Key Metrics |
|-------|-------------|-------------------|-------------|
| **code-quality-specialist** | 95% | ~30s | 0 ruff violations, 100% type coverage |
| **test-specialist** | 92% | ~45s | >80% test coverage, 100% for refactored code |
| **scrum-master** | 98% | ~15s | Accurate story points, clear acceptance criteria |
| **visual-qa-agent** | 88% | ~25s | 28.6% escape rate baseline |
| **devops** | 94% | ~60s | CI/CD pipeline success, deployment automation |

## 🔄 Agent Lifecycle

### 1. Discovery Phase
- Agent definitions loaded from `.github/agents/*.agent.md`
- Registry validates required fields (name, description, model, tools)
- Skills patterns loaded and associated

### 2. Instantiation Phase
- Agent created with context injection (AGILE_MINDSET system prompt)
- Tool access configured based on agent definition
- Skills knowledge loaded into agent memory

### 3. Execution Phase
- Agents collaborate through shared context system
- Results tracked for performance metrics
- Skills patterns updated based on outcomes

## 🔗 Integration Points

### GitHub Actions
- **quality-tests.yml**: Triggered by code quality agents
- **sprint-discipline.yml**: Monitored by scrum master agent
- **content-pipeline.yml**: Used by content generation crews

### Quality System
- **Pre-commit Hooks**: Enforced by code quality agents
- **Definition of Done**: Validated by test specialist and scrum master
- **Gate System**: 4-layer validation with agent participation

### Context Sharing
- **Thread-Safe**: Concurrent agent access with threading.Lock
- **Performance**: 143ms load, 162ns access, 0.5MB memory
- **Audit Trail**: Complete modification history for compliance

## 📚 Related Documentation

- **Agent Registry Pattern**: [ADR-002](docs/ADR-002-agent-registry-pattern.md)
- **CrewAI Integration**: [docs/CREWAI_CONTEXT_ARCHITECTURE.md](docs/CREWAI_CONTEXT_ARCHITECTURE.md)
- **Skills System**: [skills/README.md](skills/README.md)
- **Flow Architecture**: [docs/FLOW_ARCHITECTURE.md](docs/FLOW_ARCHITECTURE.md)
- **Quality System**: [docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md)

## 🎯 Success Criteria

Agents are considered successful when they achieve:
- ✅ **Accuracy**: >90% success rate in task completion
- ✅ **Performance**: <60s average response time
- ✅ **Quality**: Meet Definition of Done requirements
- ✅ **Collaboration**: Effective context sharing and handoffs
- ✅ **Learning**: Skills patterns improve over time

For agent-specific metrics and detailed usage examples, see the individual agent documentation in `.github/agents/`.
