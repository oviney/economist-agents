---
name: python-quality
description: Python coding standards for the economist-agents multi-agent pipeline. Use when writing new Python code, when reviewing PRs for code quality, when configuring linting and type checking.
---

# Python Quality

## Overview

Coding standards for the economist-agents content pipeline. Type hints mandatory, docstrings required, `orjson` not `json`, `logger` not `print()`. All code must pass ruff, mypy, and pytest before commit.

## When to Use

- Writing any new Python code in this repo
- Reviewing PRs for code quality compliance
- Configuring linting, formatting, or type checking
- Debugging import structure or dependency issues

### When NOT to Use

- For CI/CD configuration — that's `quality-gates`
- For test patterns and coverage — that's `testing`
- For MCP server specifics — that's `mcp-development`

## Core Process

### Mandatory Standards

1. **Type hints** on all function signatures. Use `dict[str, Any]` for JSON, `T | None` for nullable. Run mypy.
2. **Docstrings** on all public functions — Google style with Args, Returns, Raises.
3. **`orjson`** for JSON serialization, never `json`.
4. **`logger`** for output, never `print()`. Use `logging.getLogger(__name__)`.
5. **Specific exceptions** — never bare `except:`. Catch `APIError`, `JSONDecodeError`, etc.
6. **Context managers** for file I/O — always `with open(...)`.
7. **No mutable defaults** — `def f(items: list | None = None)`, never `def f(items=[])`.
8. **Snake_case** functions/variables, **PascalCase** classes, **UPPER_CASE** constants.
9. **88-char line limit** (ruff formatter standard).
10. **No credentials in code** — `.env` + `os.getenv()` only.

### Import Structure

```python
# Standard library
import logging
from pathlib import Path
from typing import Any

# Third-party
import orjson
from anthropic import Anthropic

# Local
from scripts.validation import validate_agent_output

logger = logging.getLogger(__name__)
```

### Agent Function Pattern

```python
AGENT_PROMPT = """You are a research agent..."""

def run_agent(client: Anthropic, topic: dict[str, Any]) -> dict[str, Any]:
    """Run agent with structured output.

    Args:
        client: Anthropic API client.
        topic: Topic dictionary with title and description.

    Returns:
        Agent output with content and usage keys.

    Raises:
        APIError: If API call fails after retries.
    """
    try:
        response = client.messages.create(...)
        return {"content": response.content, "usage": response.usage}
    except APIError as e:
        logger.error("Agent API call failed: %s", e)
        raise
```

### File I/O Pattern

```python
def save_output(data: dict[str, Any], path: Path) -> None:
    """Save agent output to JSON."""
    with open(path, "wb") as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
```

### Before Committing

```bash
ruff format .                                    # Format
ruff check .                                     # Lint
mypy scripts/                                    # Type check
pytest tests/ -v --cov=scripts --cov-report=term-missing  # Test
```

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "`json` is in the stdlib, why add a dependency?" | `orjson` is 10x faster and handles bytes natively — agent pipelines serialize constantly |
| "`print()` is fine for debugging" | `print()` in production code bypasses log levels, can't be filtered, and breaks structured logging |
| "`Any` type is easier" | `Any` defeats the purpose of type checking — use specific types for agent inputs/outputs |
| "Docstrings are overhead for internal functions" | Internal functions become public when agents compose them — docstrings are the API contract |
| "We'll add type hints later" | Type hints later means mypy debt later; adding them at write time costs 5% more, removing debt costs 50% more |

## Red Flags

- `import json` instead of `import orjson`
- `print()` used for error reporting or logging
- Functions without type hints or docstrings
- Bare `except:` clause
- Mutable default arguments (`def f(items=[])`)
- Wildcard imports (`from module import *`)
- API keys hardcoded or logged
- `pandas` used instead of `polars` for data frames
- Commented-out code or debug `breakpoint()` statements

## Verification

- [ ] All functions have type hints — **evidence**: `mypy scripts/` passes with zero errors
- [ ] All public functions have docstrings — **evidence**: grep for `def ` without preceding docstring
- [ ] `orjson` used for JSON — **evidence**: `grep -r "import json" scripts/` returns empty (excluding tests)
- [ ] `logger` used, not `print()` — **evidence**: `grep -rn "print(" scripts/` returns only non-error output
- [ ] No bare except clauses — **evidence**: `grep -rn "except:" scripts/` returns empty
- [ ] ruff format + check pass — **evidence**: `ruff format --check . && ruff check .` exits 0
- [ ] Test coverage ≥80% — **evidence**: `pytest --cov` output
