---
name: mcp-development
description: Standards for building MCP servers in this project. Use when creating a new MCP server, when reviewing MCP server code, when debugging import or tool registration issues.
---

# MCP Server Development

## Overview

Every MCP server must use the official SDK import (`from mcp.server.fastmcp import FastMCP`), return structured error dicts instead of exceptions, and follow the template below. This skill exists because agents consistently use the wrong import.

## When to Use

- Creating a new MCP server in `mcp_servers/`
- Reviewing an MCP server PR for correctness
- Debugging import errors or tool registration failures
- Writing tests for MCP server tools

### When NOT to Use

- For general Python quality standards — that's `python-quality`
- For test coverage requirements — that's `testing`
- For CI/CD pipeline configuration — that's `quality-gates`

## Core Process

### The Critical Import

```python
# CORRECT — official MCP SDK
from mcp.server.fastmcp import FastMCP

# WRONG — third-party package, different API
from fastmcp import FastMCP
```

**Dependency:** `mcp>=1.0.0` in `requirements.txt`. Never add `fastmcp` as separate dependency.

### Server Template

```python
#!/usr/bin/env python3
"""<Name> MCP Server.

<One-line description.>

Tools:
    <tool_name>: <what it does>

Usage:
    python -m mcp_servers.<module_name>
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("<server-name>")


@mcp.tool()
def my_tool(param: str, count: int = 5) -> dict[str, Any]:
    """One-line description of the tool.

    Args:
        param: What this parameter controls.
        count: How many results to return.

    Returns:
        Dict with results or error information.
    """
    try:
        result = do_work(param, count)
        return {"success": True, "data": result}
    except SpecificError as e:
        logger.exception("Known failure mode")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in my_tool")
        return {"success": False, "error": f"Unexpected: {e}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 9 Mandatory Rules

1. **Import:** Always `from mcp.server.fastmcp import FastMCP`
2. **Decorator:** Always `@mcp.tool()` with parentheses
3. **Type hints:** Full type hints on all parameters and return type
4. **Docstrings:** Google-style with Args and Returns sections
5. **Error handling:** Never raise exceptions; return `{"success": False, "error": "..."}`
6. **Transport:** `mcp.run(transport="stdio")` under `__main__` guard
7. **Naming:** kebab-case server names (`"article-evaluator"`)
8. **Location:** All servers in `mcp_servers/` directory
9. **Logging:** `logging.getLogger(__name__)`, not `print()`

### Testing Standards

- Test location: `tests/test_mcp_servers/test_<server_name>.py`
- Mock all external calls (no real API/network traffic)
- Minimum test categories: happy path, error handling, edge cases, server registration
- Coverage: ≥80%
- Use `mcp._tool_manager._tools` for tool introspection (no public `.tools` attribute)

### Configuration

Register in `.mcp.json`:
```json
{
  "mcpServers": {
    "article-evaluator": {
      "command": "python",
      "args": ["-m", "mcp_servers.article_evaluator_server"],
      "transport": "stdio"
    }
  }
}
```

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "The `fastmcp` package has better ergonomics" | It's a different package with an incompatible API — this caused 4/5 Copilot PRs to fail in Sprint 18 |
| "We can skip the parentheses on `@mcp.tool`" | Inconsistent with SDK docs and breaks in some versions |
| "Raising exceptions is simpler than returning dicts" | Exceptions crash the MCP client connection; structured errors keep the session alive |
| "We don't need all those test categories" | Registration tests catch the import bug; error tests catch exception leaks — both are Sprint 18 bugs |

## Red Flags

- `from fastmcp import FastMCP` anywhere in the codebase
- `fastmcp` listed as a dependency in `requirements.txt`
- `@mcp.tool` without parentheses
- Tool function that raises instead of returning error dict
- `print()` used instead of `logging.getLogger()`
- MCP server file outside `mcp_servers/` directory
- Test that makes real API calls or network requests

## Verification

- [ ] Import is `from mcp.server.fastmcp import FastMCP` — **evidence**: grep confirms no `from fastmcp`
- [ ] All tools use `@mcp.tool()` with parentheses — **evidence**: grep `@mcp.tool[^(]` returns empty
- [ ] All tools have type hints and Google-style docstrings — **evidence**: mypy passes, docstring present
- [ ] No tools raise exceptions — **evidence**: every tool body wrapped in try/except returning dicts
- [ ] Tests exist with ≥80% coverage — **evidence**: `pytest --cov` output
- [ ] Server registered in `.mcp.json` — **evidence**: JSON entry matches server name
