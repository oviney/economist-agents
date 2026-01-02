# Economist Agents

**Multi-Agent Content Generation Pipeline**

![Quality Score](https://img.shields.io/badge/Quality_Score-67%2F100-yellow)
![Test Coverage](https://img.shields.io/badge/Coverage-52%25-yellow)
![Sprint](https://img.shields.io/badge/Sprint-6-blue)
![Python](https://img.shields.io/badge/Python-3.11+-blue)

A sophisticated multi-agent system that produces publication-quality blog posts in The Economist's signature style. This project orchestrates specialized AI agents for topic discovery, editorial voting, research, writing, editing, and chart generation.

## 🚀 Project Status

**Current Phase:** Quality & Prevention (Sprint 6)

- **Defect Prevention:** Automated system catching 83% of historical bug patterns
- **Green Software:** Self-validating agents reducing token waste by 30%
- **Quality Gates:** 4-layer validation (Pre-commit, GitHub Actions, Agent Self-Correction, Publication Validator)

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/economist-agents.git
   cd economist-agents
   ```

2. **Run setup script:**
   ```bash
   ./scripts/setup.sh
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

## 🔄 Development Workflow

We follow a strict quality-first workflow enforced by automated gates.

### 1. Create a Feature Branch
```bash
git checkout -b feature/my-feature
```

### 2. Run Quality Checks
Before committing, ensure all local checks pass:
```bash
make check
# Runs: ruff, mypy, pytest, and custom validators
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

## 📜 License

Proprietary. All rights reserved.
