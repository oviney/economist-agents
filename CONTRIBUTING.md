# Contributing to Economist-Agents

Thank you for your interest in contributing to the Economist-Agents project! This guide will help you understand our development workflow, quality standards, and collaboration practices.

## 🚀 Quick Start

### Prerequisites

- **Python 3.13.x** (⚠️ Python 3.14+ is not supported due to CrewAI compatibility)
- **Git** with pre-commit hooks enabled
- **Virtual environment** (venv or conda)

### Setup

1. **Clone and setup environment:**
   ```bash
   git clone https://github.com/your-org/economist-agents.git
   cd economist-agents
   python3.13 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Setup pre-commit hooks:**
   ```bash
   pre-commit install --install-hooks
   pre-commit install --hook-type pre-push
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (ANTHROPIC_API_KEY or OPENAI_API_KEY)
   ```

5. **Verify setup:**
   ```bash
   make quality  # Runs format, lint, type-check, and tests
   ```

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
- ✅ **>80% test coverage** (100% for refactored code)
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

Follow the patterns in [`skills/python-quality/SKILL.md`](skills/python-quality/SKILL.md):

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

## 🤝 Agent-Specific Contributions

### Working with Agents

Our project uses 9 specialized AI agents. When contributing, consider which agent domain your work affects:

#### Development Agents
- **@code-quality-specialist**: Code refactoring and quality enforcement
- **@test-specialist**: Test writing and coverage improvements
- **@devops**: CI/CD and deployment automation
- **@code-reviewer**: Code review and architecture validation

#### Management Agents
- **@scrum-master**: Sprint planning and process improvements
- **@po-agent**: User stories and business requirements
- **@product-research-agent**: Market analysis and feature research

#### Operations Agents
- **@git-operator**: Repository management and release processes
- **@visual-qa-agent**: Chart and design quality validation

### Agent Usage in Development

```bash
# Request code quality improvements
@code-quality-specialist Fix type hints in scripts/topic_scout.py

# Get test coverage for new code
@test-specialist Add comprehensive tests for new_feature.py

# Review architectural changes
@code-reviewer Validate new microservice architecture
```

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

### Documentation
- **Architecture**: [docs/FLOW_ARCHITECTURE.md](docs/FLOW_ARCHITECTURE.md)
- **Agent System**: [AGENTS.md](AGENTS.md)
- **API Reference**: [docs/CREWAI_API_REFERENCE.md](docs/CREWAI_API_REFERENCE.md)
- **Quality System**: [docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md)

### Skills and Standards
- **Python Quality**: [skills/python-quality/SKILL.md](skills/python-quality/SKILL.md)
- **Testing Patterns**: [skills/testing/](skills/testing/)
- **Architecture Patterns**: [docs/ADR-*.md](docs/)

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
```

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