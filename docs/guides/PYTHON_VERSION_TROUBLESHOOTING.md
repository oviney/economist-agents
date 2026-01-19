# Python Version Troubleshooting Guide

## Issue: Test Collection Errors with Python 3.14+

### Symptoms
- `pytest --collect-only` fails with import errors
- Messages like "5 collection errors blocking 447 tests"
- CrewAI import failures or dependency issues
- Tests that worked previously suddenly stop collecting

### Root Cause
CrewAI 1.7.2 and related dependencies require Python 3.13 or lower. Python 3.14+ introduces breaking changes that cause import failures during test collection.

### Solution

#### Quick Fix: Use Existing Python 3.13 Environment
```bash
# Activate the working environment
source .venv/bin/activate

# Verify correct version
python --version
# Should show: Python 3.13.11

# Test collection should work
python -m pytest --collect-only tests/
# Should show: collected 538 items (not collection errors)
```

#### If No Python 3.13 Environment Exists
```bash
# Install Python 3.13 (macOS with Homebrew)
brew install python@3.13

# Create new virtual environment
python3.13 -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Verify Fix
```bash
source .venv/bin/activate

# Check Python version
python --version  # Should be 3.13.x

# Test CrewAI import
python -c "import crewai; print(f'CrewAI {crewai.__version__} imported successfully')"

# Test collection
python -m pytest --collect-only tests/ | grep "collected.*items"
# Should show: collected 538 items

# Run a quick test
python -m pytest tests/test_agent_registry_enhancement.py -v
```

### Environment Management

#### Check Available Environments
```bash
ls -la | grep venv
# Look for:
# .venv          - Default environment (should be Python 3.13)
# .venv-py313    - Python 3.13 environment
# .venv-py314    - Python 3.14 environment (broken)
```

#### Switch Environments
```bash
# Deactivate current environment
deactivate

# Activate specific environment
source .venv-py313/bin/activate  # For Python 3.13
# OR
source .venv/bin/activate        # For default environment
```

### Prevention

#### Pre-commit Hook
Add this to your shell profile (`.bashrc`, `.zshrc`) to prevent accidental Python 3.14 usage:

```bash
# Economist-agents project Python version check
check_python_version() {
    if [[ "$PWD" == *"economist-agents"* ]]; then
        if command -v python &> /dev/null; then
            python_version=$(python --version 2>&1 | cut -d' ' -f2)
            if [[ "$python_version" > "3.13" ]]; then
                echo "⚠️  WARNING: Python $python_version detected in economist-agents"
                echo "   This project requires Python 3.13 or lower for CrewAI compatibility"
                echo "   Run: source .venv/bin/activate"
            fi
        fi
    fi
}

# Run check when entering directory
cd() {
    builtin cd "$@"
    check_python_version
}
```

### Common Error Messages

#### Collection Error Example
```
FAILED tests/some_test.py::test_function - ImportError: cannot import name 'X' from 'crewai'
collected 447 items / 5 errors
```

#### CrewAI Import Error Example
```
ImportError: cannot import name 'Agent' from 'crewai'
ModuleNotFoundError: No module named 'crewai.agent'
```

#### Python Version Check
```bash
# Check current Python version
python --version

# If using system Python (likely 3.14+):
Python 3.14.2

# After activating .venv (should be 3.13):
Python 3.13.11
```

### Troubleshooting Steps

1. **Check Python version**: `python --version`
2. **Activate correct environment**: `source .venv/bin/activate`
3. **Verify CrewAI import**: `python -c "import crewai"`
4. **Test collection**: `python -m pytest --collect-only tests/`
5. **Run sample test**: `python -m pytest tests/test_agent_registry_enhancement.py`

### Success Criteria

- ✅ Python version shows 3.13.x
- ✅ CrewAI imports without errors
- ✅ `pytest --collect-only` shows "collected 538 items"
- ✅ Sample tests execute successfully
- ✅ No collection errors or import failures

### Related Files

- **Virtual Environment**: `.venv/` (default, should be Python 3.13)
- **Requirements**: `requirements.txt`, `requirements-dev.txt`
- **Test Config**: `pytest.ini`
- **CI/CD**: `.github/workflows/quality-tests.yml`

### Support

If this guide doesn't resolve the issue:
1. Check if new dependencies were added that conflict with Python 3.13
2. Verify all requirements files specify compatible versions
3. Consider updating CrewAI version (check release notes for Python 3.14 support)
4. Open an issue with full error output and environment details