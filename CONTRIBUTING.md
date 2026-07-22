# Contributing to Economist-Agents

Thank you for your interest in contributing to the Economist-Agents project! This guide will help you understand our development workflow, quality standards, and collaboration practices.

## 🚀 Quick Start

### Prerequisites

- **Python 3.12** (pinned in `.python-version`; single version per ADR-0015)
- **Git** with pre-commit hooks enabled
- **Virtual environment** (venv)

### Setup

1. **Clone and setup environment:**
   ```bash
   git clone https://github.com/oviney/economist-agents.git
   cd economist-agents
   python3 -m venv .venv
   # On stock Debian/Ubuntu ensurepip is stripped, so the venv has no pip —
   # bootstrap it:
   curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Setup pre-commit hooks:**
   ```bash
   pre-commit install --install-hooks
   pre-commit install --hook-type pre-push
   ```

4. **Configure environment (keyless — no paid AI keys):**
   ```bash
   # To publish generated articles, set a FREE GitHub token with push access to
   # oviney/blog (Contents + Pull requests: write). No AI key is needed —
   # writing/graphics/research run on the Claude subscription via the Agent SDK.
   export BLOG_REPO_TOKEN=<your fine-grained PAT>
   ```
   See `docs/keyless-pipeline-runbook.md` for the full keyless run.

5. **Verify (before every merge — you are the gate):**
   ```bash
   make ci-local   # full pre-merge gate: ruff, mypy, tests+coverage (70% +
                   # src/quality 90%), bandit, destructive-change guard.
   ```
   There is no GitHub Actions CI and `main` is not branch-protected (ADR-0015):
   `make ci-local` is the source of truth. `make quality` is the faster subset.

## ✏️ Generating an article — the image handshake (#403)

The pipeline is **two-step** to keep the cost of a featured image zero
(no paid DALL-E/Imagen/etc. API). Stage 3 produces the article + chart
and pauses with a paste-ready prompt; you generate the image yourself
in chat.openai.com (or any web image tool) and drop the PNG at a known
path; `--resume` then runs Stage 4 and finalises the article.

### Step 1 — run Stage 3

```bash
python -m src.agent_sdk.pipeline "your noun-phrasey topic"
```

Stage 3 writes:

- `output/posts/<slug>.md` — the article draft
- `output/charts/<slug>.png` — the rendered chart (matplotlib, no API)
- `output/posts/<slug>.image_prompt.md` — the prompt to paste into ChatGPT
- `output/state/<slug>.json` — handshake state for `--resume`

Then it **exits 10** and prints the prompt + the exact drop path + the
resume command. Cost so far is the Stage 3 LLM spend only (~$0.30).

### Step 2 — generate the hero image

Open chat.openai.com, paste the prompt from
`output/posts/<slug>.image_prompt.md`, generate the image, and save the
PNG (1792×1024 landscape) to:

```
output/posts/images/<slug>.png
```

The deterministic gate enforces format/dimensions/size; visual quality
is your call.

### Step 3 — resume

```bash
# With a hero image:
python -m src.agent_sdk.pipeline --resume <slug>

# Or chart-only (no hero — the chart becomes the visual anchor):
python -m src.agent_sdk.pipeline --resume <slug> --no-image
```

Stage 4 polishes the article, runs the publication validator, and
writes the final version back to `output/posts/<slug>.md`.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0    | Stage 4 complete (full pipeline done) |
| 1    | Operator error (unknown slug, missing article) |
| 2    | Research providers failed (transient — retry or rephrase) |
| 3    | Research providers returned zero sources (topic too narrow) |
| 10   | Stage 3 complete — awaiting image-prompt handshake |
| 11   | `--resume` image-gate failed (missing/wrong-size/wrong-dims PNG) |

### Deploying

After Stage 4 passes, the article at `output/posts/<slug>.md` is ready
for `python -m scripts.deploy_to_blog --article output/posts/<slug>.md`.
See the deploy script's `--help` for blog-repo config.

## 🎯 Development Workflow

We follow a **quality-first workflow** with automated gates (checkpoints) to ensure code excellence.

### 1. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Development Cycle

#### Test-Driven Development (TDD)
Follow the RED → GREEN → REFACTOR cycle:

```bash
# 1. RED: Write failing test
def test_new_feature():
    result = new_function()
    assert result == expected

# 2. GREEN: Implement minimal solution
def new_function():
    return expected

# 3. REFACTOR: Improve while keeping tests green
```

#### Quality Standards (Mandatory)

**All code must meet these standards:**

- ✅ **Type hints on all functions** (`mypy scripts/` passes)
- ✅ **Docstrings for all public functions** (Google style)
- ✅ **>70% aggregate test coverage** (CI gate: `--cov-fail-under=70` across `src/` + `scripts/`)
- ✅ **>90% coverage on `src/quality/*`** (CI gate: per-module floor; see `.github/workflows/ci.yml` step "Enforce src/quality/ per-module coverage gate (#393)")
- ✅ **>80% target on new code** (100% for refactored code)
- ✅ **Zero linting violations** (`ruff check .` passes)
- ✅ **Proper error handling** with specific exceptions
- ✅ **Use `orjson` instead of `json`**
- ✅ **Use `logger` instead of `print()` for output**

### 3. Commit Process

**Fast commits** (no test suite):
```bash
git add .
git commit -m "feat: add new research capability"
# Runs: ruff format + ruff check (~0.5s)
```

**Pre-push validation** (automatic):
```bash
git push origin feature/your-branch
# Automatically runs: pytest + quality checks (~7.5s)
```

**Emergency bypass** (use sparingly):
```bash
git push --no-verify  # Skip tests for urgent hotfixes only
```

### 4. Pre-commit Hook Performance

| Hook | Trigger | Duration | Purpose |
|------|---------|----------|---------|
| `ruff-format` | commit | ~300ms | Auto-format Python code |
| `ruff check` | commit | ~200ms | Lint code (checks only) |
| `pytest` | push | ~7.5s | Full test suite (447 tests) |
| `check-yaml` | commit | ~50ms | YAML syntax validation |
| `check-json` | commit | ~50ms | JSON syntax validation |

## 🧪 Testing Strategy

### Test Categories

1. **Unit Tests**: Test individual functions/classes in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Quality Gates**: Automated validation checkpoints

### Writing Tests

```python
# tests/test_example.py
import pytest
from unittest.mock import Mock, patch
from scripts.my_module import my_function

def test_my_function_success():
    """Test successful execution of my_function."""
    # Arrange
    input_data = {"key": "value"}
    expected = {"result": "processed"}

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected

@patch('scripts.my_module.external_api')
def test_my_function_with_mock(mock_api):
    """Test my_function with mocked external dependency."""
    # Arrange
    mock_api.return_value = {"api": "response"}

    # Act & Assert
    result = my_function({})
    assert result is not None
    mock_api.assert_called_once()
```

### Running Tests

```bash
# Quick test run
make test

# Full quality checks
make quality

# Specific test file
pytest tests/test_example.py -v

# With coverage
pytest tests/ --cov=scripts --cov-report=html
```

## 🏗️ Code Style Guide

### Python Coding Standards

Follow the patterns in [`skills/python-quality/SKILL.md`](skills/python-quality/SKILL.md). The canonical SKILL.md format is documented in [`docs/skill-anatomy.md`](docs/skill-anatomy.md) and enforced by `scripts/validate_skills.py` in pre-commit and CI.

#### Example: Good Code

```python
from typing import Any, Dict, List
import logging
import orjson
from pathlib import Path

logger = logging.getLogger(__name__)

def process_data(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process input data and return formatted results.

    Args:
        input_data: Dictionary containing raw data to process

    Returns:
        List of processed data dictionaries

    Raises:
        ValueError: If input_data is empty or invalid
        FileNotFoundError: If required config file is missing
    """
    if not input_data:
        raise ValueError("Input data cannot be empty")

    try:
        config = _load_config()
        results = []

        for item in input_data.get('items', []):
            processed = _transform_item(item, config)
            results.append(processed)

        logger.info(f"Processed {len(results)} items successfully")
        return results

    except Exception as e:
        logger.error(f"Failed to process data: {e}")
        raise

def _load_config() -> Dict[str, Any]:
    """Load configuration from config file."""
    config_path = Path("config/settings.json")

    try:
        with open(config_path, "rb") as f:
            return orjson.loads(f.read())
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
```

#### Common Anti-Patterns to Avoid

```python
# ❌ Bad: No type hints, poor error handling
import json

def process(data):
    file = open("config.json")
    config = json.load(file)
    print(f"Processing {len(data)} items")
    return [item for item in data]

# ❌ Bad: Using print() instead of logging
def my_function():
    print("Debug info")  # Use logger.debug() instead

# ❌ Bad: Broad exception catching
try:
    risky_operation()
except:  # Too broad
    pass  # Silent failure
```

## 🧠 Agent Development: Edit Prompts First

A core architectural principle in this project is **Prompts as Code**: agent behaviour is defined by large prompt constants at the top of Python files, not by procedural logic. When modifying any agent's behaviour, **edit the prompt constants first** — they are the source of truth.

### Why Prompts Are First-Class Code

Agent prompt constants (e.g., `RESEARCH_AGENT_PROMPT`, `WRITER_AGENT_PROMPT`) are:
- **Versionable**: Every behaviour change is captured in git history
- **Reviewable**: PRs show exactly what changed in agent instructions
- **Testable**: Prompt constraints can be validated by automated tests
- **Explicit**: Intent is readable without running the code

### Finding the Right Prompt

| Agent | File | Notes |
|-------|------|-------|
| Research | `src/crews/stage3_crew.py` | Deterministic web search (arXiv + Google) — no LLM agent |
| Writer Agent | `src/crews/stage3_crew.py` | Backstory + task description define style rules |
| Graphics Agent | `src/crews/stage3_crew.py` | Chart data generation |
| Editor Agent | `src/crews/stage3_crew.py` | Quality gate review |
| Topic Scout | `scripts/topic_scout.py` | `SCOUT_AGENT_PROMPT` |
| Editorial Board | `scripts/editorial_board.py` | Per-persona prompt strings |

### Workflow for Agent Changes

```bash
# 1. Identify the prompt constant that controls the behaviour
grep -n "PROMPT\|system_message" scripts/economist_agent.py

# 2. Edit the prompt in the source file
# e.g., add a new constraint to WRITER_AGENT_PROMPT

# 3. Update any related tests that validate prompt content
pytest tests/test_economist_agent.py -v

# 4. Run quality checks
make quality
```

### Banned Patterns in the Writer Agent

The `WRITER_AGENT_PROMPT` enforces strict Economist voice rules. When contributing to writer-related code, preserve these constraints:

**Forbidden openings:** "In today's world...", "It's no secret that...", "In recent years..."
**Banned phrases:** "game-changer", "paradigm shift", "leverage" (as verb)
**Forbidden closings:** "Only time will tell...", "In conclusion..."
**Mandatory style:** British spelling (organisation, favour, analyse), no exclamation points

See [`docs/ARCHITECTURE_PATTERNS.md`](docs/ARCHITECTURE_PATTERNS.md) for the full list of architectural patterns enforced across agents.

---

## 📚 Contributing to the Public Skills Library

The `agents/skills_configs/` directory is an open, community-maintained library of generic
agent definitions.  Contributing a new agent or improving an existing one is one of
the most impactful ways to help the wider agentic-AI community.

### What belongs in `agents/skills_configs/`

A public skills library agent should be:

- **Generic** — usable outside this repository without modification.
- **Documented** — includes `metadata.use_cases` and `metadata.customisation_notes`.
- **Self-contained** — the `system_message` encodes all necessary instructions.
- **Prompt-only** — no hard-coded references to internal URLs, API keys, or secrets.

### Step-by-step: adding a new public agent

1. **Create your YAML file** in `agents/skills_configs/<agent-name>.yaml`.
   Follow the schema defined in `agents/schema.json`.

2. **Include all required fields** (example for a "Fact Checker" agent):
   ```yaml
   name: "Fact Checker"
   role: "Fact Checker"
   goal: "Verify factual claims in draft content against authoritative sources"
   backstory: |
     A Fact Checker who verifies every claim in a draft before publication.
     Traces statistics to primary sources, flags unverifiable assertions,
     and corrects errors without changing the author's voice.
   system_message: |
     You are a Fact Checker. For each claim in the draft, locate the primary
     source, confirm the figure is accurate, and flag anything unverifiable.
     Output a JSON report with fields: claim, verdict, source, notes.
   tools:
     - web_search
     - file_search
   metadata:
     version: "1.0"
     created: "YYYY-MM-DD"
     author: "your-github-username"
     category: "content_generation"   # discovery | editorial_board | content_generation
     visibility: "public"
     use_cases:
       - "Pre-publication fact verification for articles"
       - "Compliance checking against regulatory statements"
     customisation_notes: |
       To adapt for a specific domain, add domain-specific authoritative sources
       to the system_message and adjust the output schema to match your workflow.
   ```

3. **Validate** your YAML against the schema:
   ```bash
   python3 -c "
   import yaml, json, jsonschema
   schema = json.load(open('agents/schema.json'))
   agent  = yaml.safe_load(open('agents/skills_configs/fact-checker.yaml'))
   jsonschema.validate(agent, schema)
   print('Valid')
   "
   ```

4. **Update `skills/README.md`** — add a row to the *Available Agents* table.

5. **Open a Pull Request** using the label `skills-library`.
   Use the PR template below.

### Skills Library PR template

```markdown
## Summary
Adding [Agent Name] to agents/skills_configs/.

## Agent Overview
- **Role**: Short description
- **Use cases**: Bullet list of 2–4 use cases
- **Customisation tips**: How to adapt it

## Checklist
- [ ] YAML validates against agents/schema.json
- [ ] metadata.visibility = "public"
- [ ] metadata.customisation_notes is present
- [ ] skills/README.md updated (Available Agents table)
- [ ] No secrets, API keys, or internal URLs in system_message
- [ ] Tested manually with at least one LLM
```

### Improving an existing public agent

- Increment `metadata.version` (patch, minor, or major — see `skills/README.md`).
- Describe the change in your PR body.
- If the output format changes (major bump), note any migration steps.

### Adding or modifying a SKILL.md

Every `skills/*/SKILL.md` must follow the canonical anatomy in
[`docs/skill-anatomy.md`](docs/skill-anatomy.md): two-field frontmatter
(`name` matches directory, `description` ends with terminal punctuation)
and the six required `##` body sections (Overview, When to Use, Core
Process, Common Rationalizations, Red Flags, Verification).

Run the validator locally before committing:

```bash
python scripts/validate_skills.py
```

The same script runs in pre-commit (`validate-skills` hook) and in the
Quality Gates CI workflow, so a non-compliant skill blocks the merge.

---

## 📋 Pull Request Process

### Before Creating a PR

1. **Ensure all tests pass**:
   ```bash
   make quality  # Must pass before PR
   ```

2. **Update documentation**:
   - Update relevant README sections
   - Add/update docstrings
   - Update CHANGELOG.md if needed

3. **Follow Definition of Done** (see [`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md)):
   - Story-level DoD met
   - Code quality standards enforced
   - CI/CD passing
   - Documentation updated

### PR Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix/feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Quality Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes to existing APIs

## Related Issues
Closes #123
```

### PR Review Process

1. **Automated Checks**: GitHub Actions run quality tests
2. **Agent Validation**: Relevant agents may provide feedback
3. **Human Review**: Team member reviews for business logic
4. **Approval**: PR approved when all checks pass

## 🔄 Sprint Participation

We follow Agile/SAFe practices with 1-week sprints:

### Sprint Capacity
- **Duration**: 1 week
- **Capacity**: 13 story points per sprint
- **Average**: 2.8 hours per story point

### Participating in Sprints

1. **Sprint Planning**: Attend planning sessions or async story refinement
2. **Daily Standups**: Share progress, blockers, and plans
3. **Sprint Review**: Demonstrate completed work
4. **Retrospectives**: Provide feedback for continuous improvement

### Story Development

Follow the Definition of Ready (DoR) and Definition of Done (DoD):

**Definition of Ready (DoR)**:
- Clear acceptance criteria
- Business value understood
- Technical approach defined
- Dependencies identified

**Definition of Done (DoD)**:
- All acceptance criteria met
- Code reviewed and approved
- Tests written and passing
- Documentation updated
- Deployed to staging

## 🐛 Bug Reports and Issues

### Reporting Bugs

Use our issue templates and provide:

1. **Clear description** of the problem
2. **Steps to reproduce** the issue
3. **Expected vs actual behavior**
4. **Environment details** (Python version, OS, dependencies)
5. **Error messages** and stack traces
6. **Screenshots** if applicable

### Bug Priority Levels

- **P0 (Critical)**: Production down, data loss, security vulnerability
- **P1 (High)**: Major feature broken, significant user impact
- **P2 (Medium)**: Minor feature issues, workaround available
- **P3 (Low)**: Cosmetic issues, nice-to-have improvements

## 🎯 Quality Metrics

We track these quality metrics:

| Metric | Target | Current |
|--------|--------|---------|
| **Test Coverage** | >80% | Monitored per PR |
| **Defect Escape Rate** | <20% | Tracked via quality dashboard |
| **Gate Pass Rate** | 95% | Validated by editor agent |
| **Critical Bug TTD** | <2 days | Monitored in sprints |

## 📚 Additional Resources

### 📖 Documentation Hub

**[Complete Documentation Hub](docs/README.md)** — navigation to all guides, architecture, and references.

### Getting Started
- **[README](README.md)** — Project overview and quick start
- **[Flow Architecture](docs/FLOW_ARCHITECTURE.md)** — Pipeline architecture and stage design
- **[Installation Guide](docs/guides/CONTINUE_SETUP.md)** — Detailed setup instructions

### Architecture & Design Decisions

All Architecture Decision Records (ADRs) live in `docs/adr/` and record major design choices with their rationale:

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](docs/adr/0001-extract-agent-definitions-to-yaml.md) | Extract Agent Definitions to YAML | Accepted |
| [ADR-0002](docs/adr/0002-agent-registry-pattern.md) | Agent Registry Pattern | Accepted |
| [ADR-0003](docs/adr/0003-phased-crewai-migration.md) | Phased CrewAI Migration | Superseded by ADR-0006 |
| [ADR-0004](docs/adr/0004-python-version-constraint.md) | Python Version Constraint | Accepted |
| [ADR-0005](docs/adr/0005-agile-discipline-enforcement.md) | Agile Discipline Enforcement | Accepted |
| [ADR-0006](docs/adr/0006-agent-framework-selection.md) | Agent Framework Selection | Proposed |
| [ADR-0007](docs/adr/0007-content-intelligence-engine.md) | Content Intelligence Engine | Proposed |
| [ADR-0008](docs/adr/0008-agent-skill-governance.md) | Agent Skill Governance | Proposed |

Use [`docs/adr/TEMPLATE.md`](docs/adr/TEMPLATE.md) when proposing a new ADR.

- **[Architecture Patterns](docs/ARCHITECTURE_PATTERNS.md)** — Prompts-as-code, persona voting, sequential orchestration
- **[Flow Architecture](docs/FLOW_ARCHITECTURE.md)** — Deterministic state-machine design

### Skills and Standards
- **[Python Quality](skills/python-quality/SKILL.md)** — Type hints, docstrings, `orjson`, logging
- **[Testing Patterns](skills/testing/SKILL.md)** — TDD workflow, coverage, mocking
- **[Quality Gates](skills/quality-gates/SKILL.md)** — Automated validation checkpoints
- **[Economist Writing](skills/economist-writing/SKILL.md)** — Voice, style, and banned patterns
- **[Defect Prevention](skills/defect-prevention/SKILL.md)** — Bug history and prevention strategies
- **[MCP Development](skills/mcp-development/SKILL.md)** — Model Context Protocol server patterns
- **[ADR Governance](skills/adr-governance/SKILL.md)** — ADR numbering and lifecycle rules

### Quality & Process
- **[Quality System](docs/DEFINITION_OF_DONE.md)** — Definition of Done and quality gates
- **[Quality Dashboard](docs/QUALITY_DASHBOARD.md)** — Metrics and quality tracking
- **[Skills Learning System](docs/SKILLS_LEARNING.md)** — Self-improving validation documentation
- **[Agent Prompt Patterns](docs/AGENT_PROMPT_PATTERNS.md)** — Prompt engineering patterns
- **[Chart Design Spec](docs/CHART_DESIGN_SPEC.md)** — Economist visual style rules

### Commands Reference

```bash
# Development
make test          # Run tests
make quality       # Full quality checks
make format        # Format code
make lint          # Lint code

# Git
git push           # Triggers pre-push tests
git push --no-verify  # Emergency bypass

# Agent interaction
@agent-name Your request here

# Pre-commit
pre-commit run --all-files  # Manual hook run
pre-commit install          # Enable hooks

# Skills / Architecture
python3 scripts/architecture_review.py --full-review --export-docs
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog --show-skills
python3 scripts/sync_copilot_context.py  # Sync patterns to Copilot
```

## 🔄 Skills Learning System

The project has a **self-improving validation system** built around accumulated skills patterns. Understanding it helps contributors avoid introducing known anti-patterns and enables them to extend the knowledge base.

### How Skills Work

Skills are structured knowledge patterns stored in JSON files under `skills/`. Each entry records:
- **Pattern name and category** (e.g., `banned_openings`, `chart_not_embedded`)
- **Severity** (critical / high / medium / low)
- **Detection check** (what the validator looks for)
- **Auto-fix** if applicable

### Key Skills Files

| File | Purpose |
|------|---------|
| `data/skills_state/blog_qa_skills.json` | Blog validation patterns — grows with each QA run |
| `data/skills_state/defect_tracker.json` | Bug history with root-cause analysis |
| `data/skills_state/copilot_behavior_patterns.json` | Anti-patterns for GitHub Copilot to avoid |
| `skills/python-quality/SKILL.md` | Python coding standards (type hints, docstrings, `orjson`) |
| `skills/testing/SKILL.md` | TDD workflow and coverage requirements |
| `skills/economist-writing/SKILL.md` | Economist voice and style rules |

### Self-Learning Validation

`scripts/blog_qa_agent.py` automatically learns from each validation run:

```bash
# Run with learning enabled (default)
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog

# View all learned patterns
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog --show-skills
```

Each run:
1. **Applies** known patterns to catch issues faster
2. **Records** new patterns when novel issues are detected
3. **Persists** knowledge to `data/skills_state/blog_qa_skills.json` for future runs

### Adding New Patterns

When you fix a recurring bug, persist the knowledge so it won't regress:

```python
from scripts.skills_manager import SkillsManager

manager = SkillsManager("data/skills_state/blog_qa_skills.json")
manager.learn_pattern(
    category="content_quality",
    issue="missing_chart_embed",
    severity="critical",
    check="Verify article body contains <img> tag for generated chart",
    example="Chart file created but markdown embed line absent",
)
```

### Architecture Review

`scripts/architecture_review.py` analyses the codebase and updates `docs/ARCHITECTURE_PATTERNS.md`:

```bash
# Full review — learns 12+ architectural patterns and exports docs
python3 scripts/architecture_review.py --full-review --export-docs

# View currently learned patterns
python3 scripts/architecture_review.py --show-skills
```

See [`docs/SKILLS_LEARNING.md`](docs/SKILLS_LEARNING.md) for complete documentation on the learning system.

---

## 🤝 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: Request reviews from team members
- **Agent Assistance**: Use @agent-name for domain-specific help

## 🎉 Recognition

We appreciate all contributions! Contributors will be:
- Listed in release notes for significant contributions
- Mentioned in sprint retrospectives
- Eligible for maintainer status after consistent high-quality contributions

## 📜 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

---

**Thank you for helping make Economist-Agents better!** 🚀

For questions or clarification on any part of this guide, please open an issue or ask in GitHub Discussions.