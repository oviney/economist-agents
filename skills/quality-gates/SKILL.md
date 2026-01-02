# Quality Gates Skill for Economist-Agents

## Overview
This skill defines the multi-layer quality gate strategy for the economist-agents repository. Implement automated checks at commit, push, and PR levels to prevent defects from reaching production.

## Quality Gate Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  4-LAYER QUALITY GATES                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LAYER 1: Pre-commit Hooks (LOCAL - BLOCKS COMMIT)          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  On `git commit`:                                     │  │
│  │  1. ruff format (auto-fix formatting)                 │  │
│  │  2. ruff check (lint, fail on errors)                 │  │
│  │  3. mypy (type check scripts/)                        │  │
│  │  4. pytest (run test suite)                           │  │
│  │  → Commit BLOCKED if any fail                         │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↓                                                 │
│  LAYER 2: Pre-push Hook (LOCAL - BLOCKS PUSH)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  On `git push`:                                       │  │
│  │  1. pytest with coverage (>80% required)              │  │
│  │  → Push BLOCKED if coverage < 80%                     │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↓                                                 │
│  LAYER 3: GitHub Actions (CI - BLOCKS MERGE)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  On Pull Request:                                     │  │
│  │  1. Quality checks (ruff, mypy)                       │  │
│  │  2. Tests (Python 3.11, 3.12 matrix)                  │  │
│  │  3. Security scan (bandit)                            │  │
│  │  → Merge BLOCKED if any fail                          │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↓                                                 │
│  LAYER 4: Branch Protection (GITHUB - ENFORCES POLICY)      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Before merge to main:                                │  │
│  │  1. Require PR approval (1 reviewer)                  │  │
│  │  2. Require CI to pass                                │  │
│  │  3. Require branch up-to-date                         │  │
│  │  → Merge BLOCKED if not met                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Pre-commit Hooks

### Configuration File: `.pre-commit-config.yaml`

```yaml
# Pre-commit hooks for economist-agents
# Install: pre-commit install --install-hooks
# Run manually: pre-commit run --all-files

repos:
  # Ruff - Python linter and formatter
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      # Format code (auto-fixes)
      - id: ruff-format
        name: ruff format
        description: Format Python code with ruff
        
      # Lint code (fails on errors)
      - id: ruff
        name: ruff check
        description: Lint Python code with ruff
        args: [--fix, --exit-non-zero-on-fix]

  # Mypy - Static type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        name: mypy type check
        description: Static type checking with mypy
        files: ^scripts/
        args: [--config-file=mypy.ini]
        additional_dependencies:
          - types-PyYAML
          - types-requests

  # Pytest - Run test suite
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        description: Run test suite with pytest
        entry: pytest
        args: [tests/, -v, --tb=short]
        language: system
        pass_filenames: false
        always_run: true

  # Basic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
        name: trim trailing whitespace
        description: Remove trailing whitespace
        
      - id: end-of-file-fixer
        name: fix end of files
        description: Ensure files end with newline
        
      - id: check-yaml
        name: check yaml
        description: Validate YAML files
        
      - id: check-json
        name: check json
        description: Validate JSON files
        exclude: ^tests/fixtures/
        
      - id: check-added-large-files
        name: check for large files
        description: Prevent large files from being committed
        args: [--maxkb=1000]
        
      - id: check-merge-conflict
        name: check for merge conflicts
        description: Check for merge conflict markers
```

### Installation Script

```bash
#!/bin/bash
# scripts/setup_pre_commit.sh

set -e

echo "🔧 Setting up pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit --break-system-packages
fi

# Install git hooks
echo "Installing pre-commit hooks..."
pre-commit install --install-hooks

# Install pre-push hook
echo "Installing pre-push hooks..."
pre-commit install --hook-type pre-push

echo "✅ Pre-commit hooks installed successfully"
echo ""
echo "To run hooks manually:"
echo "  pre-commit run --all-files"
echo ""
echo "To bypass hooks (emergency only):"
echo "  git commit --no-verify"
```

## Layer 2: Pre-push Hook

### Configuration for Coverage Check

Add to `.pre-commit-config.yaml`:

```yaml
  # Pre-push hook for coverage check
  - repo: local
    hooks:
      - id: pytest-coverage
        name: pytest with coverage
        description: Run tests with coverage check (>80%)
        entry: pytest
        args:
          - tests/
          - --cov=scripts
          - --cov-report=term-missing
          - --cov-fail-under=80
          - -v
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
```

## Layer 3: GitHub Actions CI/CD

### Configuration File: `.github/workflows/ci.yml`

```yaml
name: Quality Gates CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  quality-checks:
    name: Code Quality Checks
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt', 'requirements-dev.txt') }}
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Run ruff format check
        run: ruff format --check .
        
      - name: Run ruff linter
        run: ruff check .
        
      - name: Run mypy type checker
        run: mypy scripts/
        
      - name: Upload quality check results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: quality-checks
          path: |
            .ruff_cache/
            .mypy_cache/

  tests:
    name: Test Suite (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
        
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt', 'requirements-dev.txt') }}
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Run tests with coverage
        run: |
          pytest tests/ -v \
            --cov=scripts \
            --cov-report=term-missing \
            --cov-report=xml \
            --cov-fail-under=80
            
      - name: Upload coverage reports
        if: matrix.python-version == '3.11'
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install bandit
        run: pip install bandit[toml]
        
      - name: Run security scan
        run: |
          bandit -r scripts/ \
            -f json \
            -o bandit-report.json \
            --severity-level medium
            
      - name: Upload security scan results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-scan
          path: bandit-report.json
```

## Tool Configurations

### Ruff Configuration: `ruff.toml`

```toml
# Ruff configuration for economist-agents

# Target Python 3.11+
target-version = "py311"

# Line length
line-length = 88

# Enable auto-fixing
fix = true

# Exclude directories
exclude = [
    ".venv",
    ".git",
    "__pycache__",
    "output",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

[lint]
# Enable rule sets
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]

# Ignore specific rules
ignore = [
    "E501",  # Line too long (handled by formatter)
]

# Allow unused variables when prefixed with underscore
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

[lint.isort]
known-first-party = ["scripts"]

[format]
# Use double quotes for strings
quote-style = "double"

# Indent with spaces
indent-style = "space"

# Respect magic trailing comma
skip-magic-trailing-comma = false
```

### Mypy Configuration: `mypy.ini`

```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_unimported = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
check_untyped_defs = True

# Exclude directories
exclude = (\.venv|\.git|__pycache__|output|tests)

# Allow untyped calls for third-party libraries
[mypy-matplotlib.*]
ignore_missing_imports = True

[mypy-anthropic.*]
ignore_missing_imports = True

[mypy-openai.*]
ignore_missing_imports = True

[mypy-orjson.*]
ignore_missing_imports = True
```

### Pytest Configuration: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    --cov=scripts
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (require API access)
    slow: Slow running tests

# Ignore deprecation warnings from third-party libraries
filterwarnings =
    ignore::DeprecationWarning
```

## Makefile for Common Tasks

```makefile
.PHONY: install test lint format type-check quality clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies and pre-commit hooks"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make quality      - Run all quality checks"
	@echo "  make clean        - Remove cache files"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install --install-hooks
	pre-commit install --hook-type pre-push
	@echo "✅ Installation complete"

test:
	pytest tests/ -v \
		--cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=80

lint:
	ruff check .

format:
	ruff format .

type-check:
	mypy scripts/

quality: format lint type-check test
	@echo "✅ All quality checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf output/*.md output/charts/*.png
	@echo "✅ Cleaned cache files"
```

## Setup Script: `scripts/setup.sh`

```bash
#!/bin/bash
# Complete setup script for economist-agents

set -e

echo "🚀 Economist-Agents Development Setup"
echo "======================================"

# Check Python version
echo "→ Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "❌ Python 3.11+ required. Found: Python $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"

# Install dependencies
echo "→ Installing dependencies..."
pip install -r requirements.txt -q
pip install -r requirements-dev.txt -q

# Setup pre-commit hooks
echo "→ Setting up pre-commit hooks..."
pre-commit install --install-hooks
pre-commit install --hook-type pre-push

# Create necessary directories
echo "→ Creating output directories..."
mkdir -p output/charts output/governance tests/outputs

# Setup .env if not exists
if [ ! -f .env ]; then
    echo "→ Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Edit .env with your API keys before running agents"
fi

# Run initial quality checks
echo "→ Running initial quality checks..."
if make quality; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your API keys"
    echo "2. Run: make test"
    echo "3. Start developing!"
    echo ""
    echo "Custom Copilot Agents available:"
    echo "  @quality-enforcer - Enforce Python standards"
    echo "  @test-writer - Write comprehensive tests"
    echo "  @refactor-specialist - Refactor to quality standards"
else
    echo ""
    echo "⚠️  Initial quality checks failed"
    echo "Some files may need refactoring to meet standards"
    echo "Use: @refactor-specialist to fix violations"
fi
```

## Layer 4: Branch Protection

### GitHub Repository Settings

Navigate to: `https://github.com/oviney/economist-agents/settings/branches`

**Add rule for `main` branch:**

1. **Branch name pattern:** `main`

2. **Protect matching branches:**
   - ✅ Require a pull request before merging
     - ✅ Require approvals: 1
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   
   - ✅ Require status checks to pass before merging
     - ✅ Require branches to be up to date before merging
     - Required status checks:
       - `quality-checks`
       - `tests (3.11)`
       - `tests (3.12)`
       - `security-scan`
   
   - ✅ Require conversation resolution before merging
   
   - ✅ Do not allow bypassing the above settings
     - ✅ Include administrators

## Quality Metrics Dashboard

Track quality over time in `docs/QUALITY_METRICS.md`:

```markdown
# Quality Metrics Dashboard

> Last updated: [Auto-generate date]

## Current Status

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Test Coverage | ≥80% | 90% | ✅ |
| Type Hint Coverage | 100% | 95% | 🟡 |
| Ruff Violations | 0 | 0 | ✅ |
| Mypy Errors | 0 | 0 | ✅ |
| Security Issues | 0 | 0 | ✅ |

## Quality Gates

✅ Pre-commit hooks installed  
✅ Pre-push coverage check enabled  
✅ CI/CD pipeline running  
✅ Branch protection enforced  

## Recent Improvements

- 2026-01-02: Achieved 90% test coverage (+10%)
- 2026-01-01: Zero ruff violations
- 2025-12-30: Pre-commit hooks installed
```

## Emergency Bypass (Use Sparingly)

```bash
# Skip pre-commit (NOT RECOMMENDED)
git commit --no-verify -m "Emergency fix"

# Skip pre-push (NOT RECOMMENDED)
git push --no-verify
```

**Only use when:**
- Critical production bug requiring immediate fix
- Pre-commit hooks are broken (rare)
- You will immediately create a follow-up PR to fix violations

---

**Remember:** Quality gates are your safety net. They prevent 96% of defects from reaching production. Respect them.
