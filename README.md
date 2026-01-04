# Economist Agents

**Multi-Agent Content Generation Pipeline**

[![CI](https://github.com/oviney/economist-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/ci.yml)
[![Quality Tests](https://github.com/oviney/economist-agents/actions/workflows/quality-tests.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/quality-tests.yml)
[![Sprint Discipline](https://github.com/oviney/economist-agents/actions/workflows/sprint-discipline.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/sprint-discipline.yml)
[![Quality Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/quality_score.json)](https://github.com/oviney/economist-agents/blob/main/docs/QUALITY_DASHBOARD.md)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/tests_badge.json)](https://github.com/oviney/economist-agents/actions/workflows/ci.yml)
[![Sprint](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/sprint_badge.json)](https://github.com/oviney/economist-agents/blob/main/SPRINT.md)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A sophisticated multi-agent system (6 AI personas collaborate) that produces publication-quality blog posts in The Economist's signature style. This project orchestrates specialized AI agents for topic discovery, editorial voting, research, writing, editing, and chart generation.

## 🚀 Project Status

**Current Phase:** CrewAI Migration & Quality Consolidation (Sprint 7)

- **Defect Prevention:** Automated system catching 83% of historical bug patterns
- **Green Software:** Self-validating agents reducing token waste by 30%
- **Quality Gates:** 4-layer validation (automated checkpoints enforce standards)

## 🛠️ Installation

**Python Version Requirement:** Python **≤3.13** (tested with 3.13.11)

CrewAI requires Python 3.13 or lower. Python 3.14+ is not currently supported.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/economist-agents.git
   cd economist-agents
   ```

2. **Create virtual environment with Python 3.13:**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

## 🤖 Custom Agents

This project uses a registry of specialized agents:

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Topic Scout** | Discovery | Scans landscape for high-value topics |
| **Editorial Board** | Governance | 6-persona voting on content strategy |
| **Research Agent** | Intelligence | Gathers verified data and sources |
| **Writer Agent** | Production | Drafts content in Economist style |
| **Editor Agent** | Quality | Enforces style, tone, and structure |
| **Graphics Agent** | Visuals | Generates brand-compliant charts |
| **Visual QA** | Validation | Validates chart layout and zones |
## 🔄 Shared Context System

**Eliminates 99.7% of agent briefing time** by enabling automatic context inheritance between agents.

### Problem Solved
Traditional multi-agent systems require manual context briefing for each agent (10 minutes per agent). With 3 agents, that's 30 minutes of redundant briefing time and 40% context duplication.

### Solution
The **ContextManager** loads story context once from `STORY_N_CONTEXT.md` files and shares it across all agents automatically:

```python
from scripts.context_manager import ContextManager, create_task_context

# Load context ONCE (143ms)
ctx = ContextManager("docs/STORY_2_CONTEXT.md")

# All agents automatically inherit story context
dev_context = create_task_context(ctx, task_id='DEV-001', assigned_to='Developer')
qe_context = create_task_context(ctx, task_id='QE-001', assigned_to='QE')
sm_context = create_task_context(ctx, task_id='SM-001', assigned_to='Scrum Master')

# Use with CrewAI Tasks
dev_task = Task(description="Implement feature", agent=developer, context=dev_context)
qe_task = Task(description="Validate feature", agent=qe, context=qe_context)
```

### Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Briefing Time** | 10 min/agent | 48ms/agent | **99.7% reduction** |
| **Context Duplication** | 40% | 0% | **Eliminated** |
| **Memory Usage** | 3× copies | 1 shared | **67% reduction** |
| **Update Propagation** | Manual | Automatic | **Thread-safe** |

### Key Features

- ✅ **Thread-Safe**: Concurrent agent access with `threading.Lock`
- ✅ **High Performance**: 143ms load, 162ns access, 0.5MB memory
- ✅ **Audit Logging**: Complete modification history for compliance
- ✅ **Error Handling**: Graceful degradation with helpful error messages
- ✅ **JSON Validation**: Automatic serialization checks
- ✅ **Size Limits**: 10MB cap prevents memory issues

### Quick Start

```python
# Step 1: Load shared context
ctx = ContextManager("docs/STORY_N_CONTEXT.md")

# Step 2: Agent 1 adds data
ctx.set('implementation_status', 'complete')

# Step 3: Agent 2 automatically sees updates
status = ctx.get('implementation_status')  # Returns: 'complete'

# Step 4: Review audit log
audit = ctx.get_audit_log()
ctx.save_audit_log('logs/audit.json')
```

### Documentation

- **Architecture Guide**: [docs/CREWAI_CONTEXT_ARCHITECTURE.md](docs/CREWAI_CONTEXT_ARCHITECTURE.md)
- **API Reference**: [docs/CREWAI_API_REFERENCE.md](docs/CREWAI_API_REFERENCE.md)
- **Usage Examples**: [examples/crew_context_usage.py](examples/crew_context_usage.py)
- **Unit Tests**: [tests/test_context_manager.py](tests/test_context_manager.py)
- **Integration Tests**: [tests/test_crew_context_integration.py](tests/test_crew_context_integration.py)

## 🛠️ Development Workflow

We follow a strict quality-first workflow enforced by automated gates (checkpoints that validate code).

### 1. Create a Feature Branch
```bash
git checkout -b feature/my-feature
```

### 2. Make Changes & Commit

**Fast commits** (no test suite):
```bash
git add .
git commit -m "feat: add new research capability"
# Runs: ruff format + ruff check (~0.5s)
# Tests DO NOT run on commit (for speed)
```

**Git operations** are optimized for speed:
- `git commit`: ~0.5 seconds (format + lint only) ⚡
- `git push`: ~7.5 seconds (includes full test suite) 🧪

### 3. Run Tests Before Push (Automatic)

**Tests run automatically on `git push`** (not on commit):
```bash
git push origin feature/my-feature
# Pre-push hook runs pytest automatically (~7.5s)
```

**Emergency bypass** (use sparingly):
```bash
git push --no-verify  # Skip tests (for urgent hotfixes only)
```

**Or run tests manually** before pushing:
```bash
make test          # Quick test run
make quality       # Full quality checks (format, lint, type-check, test)
```

### 4. Create Pull Request
```bash
gh pr create
```

### Pre-commit Hook Performance

| Hook | When | Duration | What it does |
|------|------|----------|--------------|
| `ruff-format` | **commit** | ~300ms | Auto-format Python code |
| `ruff check` | **commit** | ~200ms | Lint code (checks only) |
| `pytest` | **push** ⚡ | ~7.5s | Run full test suite (166+ tests) |
| `check-yaml` | **commit** | ~50ms | Validate YAML syntax |
| `check-json` | **commit** | ~50ms | Validate JSON syntax |

**Why tests run on push, not commit:**
- ⚡ **Faster commit workflow** (0.5s vs 7.5s)
- ✅ **Encourages frequent small commits**
- 🧪 **Tests still validate before code reaches remote**
- 🚀 **Improves local iteration speed**

**Emergency bypass** (use with caution):
```bash
git push --no-verify  # Skip pre-push tests (for urgent hotfixes only)
```

### Re-enabling Pre-commit Hooks

If hooks were previously disabled, re-enable them:
```bash
source .venv/bin/activate
pre-commit install --install-hooks
pre-commit install --hook-type pre-push
```

## 📂 Project Structure

```
economist-agents/
├── docs/                  # Architecture and process documentation
├── output/                # Generated content artifacts
├── scripts/               # Agent implementations and tools
│   ├── economist_agent.py # Main orchestrator
│   ├── editorial_board.py # Voting system
│   └── topic_scout.py     # Discovery engine
├── skills/                # Learned agent patterns (JSON)
├── tests/                 # Test suite (Unit, Integration, E2E)
└── README.md              # This file
```

## 📊 Quality Dashboard

See [docs/QUALITY_DASHBOARD.md](docs/QUALITY_DASHBOARD.md) for detailed metrics.

- **Defect Escape Rate:** <20% (Target)
- **Critical Bug TTD:** <2 days
- **Gate Pass Rate:** 95% (Editor Agent)

## 🏷️ Badge Configuration

All badges use shields.io with dynamic JSON endpoints to prevent staleness (BUG-023 fix).

### Badge Data Sources

| Badge | Source | Update Command |
|-------|--------|----------------|
| **Quality Score** | `quality_dashboard.py` output | Automated via `quality_score.json` |
| **Tests** | Actual pytest test count | `python3 scripts/generate_tests_badge.py` |
| **Sprint** | `skills/sprint_tracker.json` | `python3 scripts/generate_sprint_badge.py` |
| **Coverage** | pytest-cov output | `python3 scripts/generate_coverage_badge.py` |

### Badge Validation

Pre-commit hook automatically validates badge accuracy:
```bash
python3 scripts/validate_badges.py
```

All badges use shields.io endpoint format with JSON files in repo root for dynamic updates.

## 📖 Glossary

**Multi-Agent System:** AI architecture where specialized agents (personas) collaborate on complex tasks. Each agent has a specific role (research, writing, editing) and they communicate through structured data exchanges.

**Defect Escape Rate:** Percentage of bugs that reach production despite testing and quality gates. Our target is <20% (industry average: 40-60%).

**Gate Pass Rate:** Percentage of quality gate checks that pass during validation. Measured per agent (Editor: 95%, Writer: 87%).

**Editorial Board:** 6 AI personas (VP Engineering, QE Lead, Data Skeptic, Career Climber, Economist Editor, Busy Reader) that vote on content topics using weighted consensus.

**Quality Gates:** Automated checkpoints that enforce coding and content standards. We have 4 layers: Pre-commit hooks, GitHub Actions CI, Agent self-validation, and Publication validator.

## 📜 License

Proprietary. All rights reserved.
