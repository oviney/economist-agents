# Economist-Style Content Agents

A multi-agent AI system that generates publication-quality blog posts in The Economist's signature style: clear prose, rigorous data analysis, and professional visualizations.

## What This Does

This is **not** a blog - it's a **content generation pipeline** that produces articles for your blog. Think of it as a team of AI writers, editors, and researchers that work together to create high-quality content.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    3-STAGE PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STAGE 1: Discovery                                         │
│  ┌──────────────────┐                                       │
│  │  TOPIC SCOUT     │  Scans QE landscape                   │
│  │                  │  → content_queue.json                 │
│  └──────────────────┘                                       │
│           ↓                                                 │
│  STAGE 2: Editorial Board (6 persona agents)                │
│  ┌──────────────────┐                                       │
│  │  VOTING SWARM    │  Debates & scores topics              │
│  │                  │  → board_decision.json                │
│  └──────────────────┘                                       │
│           ↓                                                 │
│  STAGE 3: Content Generation                                │
│  ┌──────────────────┐                                       │
│  │  Research Agent  │  Gathers data                         │
│  │  Graphics Agent  │  Creates charts                       │
│  │  Writer Agent    │  Drafts article                       │
│  │  Editor Agent    │  Enforces style                       │
│  │                  │  → Markdown + PNG                     │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Or manually:
pip install anthropic openai matplotlib numpy python-slugify pyyaml
```

### 2. Set API Key (SECURE METHOD)

**🔒 Recommended: Use .env file** ([Security Guide](.github/API_KEY_SECURITY.md))
```bash
# One-time setup
./scripts/setup_env.sh

# Edit with your real key
nano .env
```

This creates a secure `.env` file with 600 permissions that's automatically ignored by git.

**Option A: Use OpenAI** (recommended if you have existing credits)
```bash
# In .env file:
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

**Option B: Use Anthropic Claude**
```bash
# In .env file:
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Alternative: Environment Variables** (less secure, not persisted)
```bash
export OPENAI_API_KEY='sk-...'
export LLM_PROVIDER='openai'  # Optional, auto-detected
```

**Supported Models**:
- OpenAI: `gpt-4o` (default), `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`
- Anthropic: `claude-sonnet-4-20250514` (default), `claude-opus-4-...`

**⚠️ Security Reminders**:
- Never commit API keys to git (`.env` is in `.gitignore`)
- Use separate keys for dev/prod
- Rotate keys immediately if exposed
- See [API_KEY_SECURITY.md](.github/API_KEY_SECURITY.md) for complete guide

### 3. Run the Pipeline

**Automated Mode** (default):
```bash
# Stage 1: Discover topics
python3 scripts/topic_scout.py

# Stage 2: Editorial board votes
python3 scripts/editorial_board.py

# Stage 3: Generate article (no human input)
python3 scripts/economist_agent.py
```

**Interactive Mode** (with human review):
```bash
# Generate with approval gates between stages
python3 scripts/economist_agent.py --interactive

# All agent outputs saved to output/governance/
# Review and approve at each stage
```

See [Governance Guide](docs/GOVERNANCE_GUIDE.md) for details on human review features.

### 4. Output
- Article: `output/YYYY-MM-DD-article-title.md`
- Chart: `output/charts/article-title.png`
- Governance logs (interactive mode): `output/governance/SESSION_ID/`

## Governance & Human Review

**NEW**: Interactive mode with approval gates and audit trails!

```bash
# Enable human review at each stage
python3 scripts/economist_agent.py --interactive
```

**Features**:
- ✅ **Approval Gates**: Review and approve after research, writing, editing
- ✅ **Saved Outputs**: Every agent's work saved as JSON for inspection
- ✅ **Audit Trail**: Complete decision logs for compliance
- ✅ **Governance Reports**: Human-readable summaries of each session

**What Gets Saved**:
- `research_agent.json` - Data points, sources, verification
- `writer_agent.json` - Draft article and metadata
- `editor_agent.json` - Quality gates and final version
- `governance_report.md` - Complete session summary

See [Governance Guide](docs/GOVERNANCE_GUIDE.md) for complete documentation.

## Integration with Your Blog

Point the output directory to your blog's `_posts/` folder:

```bash
export OUTPUT_DIR="/path/to/your/blog/_posts"
python3 scripts/economist_agent.py
```

Or use GitHub Actions to automatically commit generated content to your blog repo.

## Governance & Quality Control

**4 Human Checkpoints:**
1. **Topic Review**: After scout, review `content_queue.json`
2. **Editorial Decision**: After board, review `board_decision.json`
3. **Article Review**: Before publishing, review generated markdown
4. **Publication**: Manually commit to your blog repo

**Enforced Quality Gates:**
- ✅ Economist voice (no throat-clearing)
- ✅ British spelling
- ✅ Data sourced (no [UNVERIFIED] claims)
- ✅ Readability (Hemingway score < 10)

## Project Structure

```
economist-agents/
├── scripts/
│   ├── topic_scout.py       # Stage 1: Topic discovery
│   ├── editorial_board.py   # Stage 2: Voting swarm
│   ├── economist_agent.py   # Stage 3: Article generation
│   ├── generate_chart.py    # Chart generator
│   └── visual_qa.py         # Chart quality checks
├── docs/
│   └── CHART_DESIGN_SPEC.md # Visual style guide
├── copilot-instructions.md   # AI agent guidance
└── README.md                 # This file
```

## Configuration

All agents use prompts-as-code (constants at top of Python files). To customize:

1. **Edit prompts** in `scripts/*.py` files
2. **Adjust personas** in `scripts/editorial_board.py`
3. **Modify style** in `docs/CHART_DESIGN_SPEC.md`

## License

MIT - Use this to generate content for any blog or publication.
