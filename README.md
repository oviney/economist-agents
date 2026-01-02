# Economist Agents

**Multi-Agent Content Generation Pipeline**

[![CI](https://github.com/oviney/economist-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/ci.yml)
[![Quality Tests](https://github.com/oviney/economist-agents/actions/workflows/quality-tests.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/quality-tests.yml)
[![Sprint Discipline](https://github.com/oviney/economist-agents/actions/workflows/sprint-discipline.yml/badge.svg)](https://github.com/oviney/economist-agents/actions/workflows/sprint-discipline.yml)
[![Quality Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/quality_score.json)](https://github.com/oviney/economist-agents/blob/main/docs/QUALITY_DASHBOARD.md)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/tests_badge.json)](https://github.com/oviney/economist-agents/actions/workflows/ci.yml)
[![Sprint](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/sprint_badge.json)](https://github.com/oviney/economist-agents/blob/main/docs/SPRINT.md)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

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

## � Development Workflow

We follow a strict quality-first workflow enforced by automated gates (checkpoints that validate code).

### 1. Create a Feature Branch
```bash
git checkout -b feature/my-feature
```

### 2. Run Quality Checks
Before committing, ensure all local checks pass:
```bash
make quality
# Runs: format, lint (ruff), type-check (mypy), and test (pytest)
```

### 3. Commit with Convention
We use conventional commits. The pre-commit hook will validate your message.
```bash
git commit -m "feat: add new research capability"
```

### 4. Push and Create PR
```bash
git push origin feature/my-feature
gh pr create
```

## �📂 Project Structure

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
