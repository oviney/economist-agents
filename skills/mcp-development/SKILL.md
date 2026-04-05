# MCP Server Development Skill

## Purpose
Define the standard for building MCP (Model Context Protocol) servers
in this project.  Every MCP server must follow these patterns exactly.
This skill exists because Copilot agents consistently get the import
wrong — using third-party packages instead of the official SDK.

## The Critical Import

```python
# ✅ CORRECT — official MCP SDK
from mcp.server.fastmcp import FastMCP

# ❌ WRONG — third-party package, different API
from fastmcp import FastMCP
```

**Dependency:** `mcp>=1.0.0` in `requirements.txt`.  Never add
`fastmcp` as a separate dependency.  The `FastMCP` class lives inside
the `mcp` package at `mcp.server.fastmcp`.

## Server Template

Every MCP server in this project follows this structure:

```python
#!/usr/bin/env python3
"""<Name> MCP Server (Story <number>).

<One-line description of what this server exposes.>

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
        # Implementation here
        return {"success": True, "data": result}
    except SomeSpecificError as e:
        logger.exception("Descriptive message")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## Mandatory Rules

### 1. Import
Always `from mcp.server.fastmcp import FastMCP`.  Never `from fastmcp`.

### 2. Decorator
Always `@mcp.tool()` with parentheses.  Not `@mcp.tool` (no parens).

### 3. Type hints
Every tool function must have full type hints on parameters and return
type.  Use `dict[str, Any]` for complex returns, `list[str]` for
simple lists.

### 4. Docstrings
Every tool must have a Google-style docstring with Args and Returns
sections.  The first line becomes the tool description in MCP
discovery.

### 5. Error handling
Tools must **never raise exceptions** to MCP clients.  Catch all
expected errors and return structured error dicts:

```python
# ✅ CORRECT — structured error
return {"success": False, "error": "GITHUB_TOKEN not set"}

# ❌ WRONG — exception propagates to client
raise ValueError("GITHUB_TOKEN not set")
```

Wrap the entire tool body in try/except for unexpected errors:

```python
@mcp.tool()
def my_tool(content: str) -> dict[str, Any]:
    """Process content."""
    try:
        result = do_work(content)
        return {"success": True, "data": result}
    except SpecificError as e:
        logger.exception("Known failure mode")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in my_tool")
        return {"success": False, "error": f"Unexpected: {e}"}
```

### 6. Transport
Always `mcp.run(transport="stdio")` under `if __name__ == "__main__":`
guard.  stdio for local dev, HTTP for CI/CD (future).

### 7. Server naming
Use kebab-case for server names: `"article-evaluator"`,
`"blog-deployer"`, `"web-researcher"`.

### 8. Module location
All servers live in `mcp_servers/` directory.  File name matches
server purpose: `mcp_servers/article_evaluator_server.py`.

### 9. Logging
Use `logging.getLogger(__name__)`, not `print()`.  Log at INFO on
tool entry/exit, ERROR on failures.

## Testing Standards

### Test file location
`tests/test_mcp_servers/test_<server_name>.py`

### Mock all external calls
No real API calls, no real git operations, no real network traffic
in tests.  Use `unittest.mock.patch` or `pytest-mock`.

### Test categories (minimum)

1. **Happy path** — tool returns expected result on valid input
2. **Error handling** — tool returns structured error on bad input,
   missing credentials, network failures
3. **Edge cases** — empty input, missing directories, malformed data
4. **Server registration** — verify server name and tool names:

```python
class TestMcpServerRegistration:
    def test_server_name(self) -> None:
        from mcp_servers.my_server import mcp
        assert mcp.name == "my-server"

    def test_tools_registered(self) -> None:
        from mcp_servers.my_server import mcp
        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        assert "my_tool" in tool_names
```

Note: use `mcp._tool_manager._tools` (underscore prefix) — the
`ToolManager` does not expose a public `.tools` attribute.

### Coverage
Minimum 80%.  Uncovered lines should only be `__main__` blocks
and `sys.path` guards.

### Test isolation
Use `tmp_path` fixture for file operations.  Use `monkeypatch` for
environment variables.  Use `EphemeralClient` for ChromaDB tests.

## Requirements

The only dependency needed is `mcp>=1.0.0` in `requirements.txt`.

**Do not add:**
- `fastmcp` (separate package, wrong API)
- `mcp-server-*` (these are pre-built servers, not the SDK)

## Configuration

Register servers in `.mcp.json` at project root:

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

## Anti-Patterns (From Sprint 18 Bugs)

1. **The fastmcp import** — `from fastmcp import FastMCP` uses a
   different third-party package with incompatible API.  This caused
   4 of 5 Copilot PRs to fail review in Sprint 18.

2. **Missing parentheses** — `@mcp.tool` without `()` may work with
   some versions but is inconsistent with the SDK documentation.

3. **Inconsistent requirements** — PRs adding `fastmcp>=0.1.0`,
   `fastmcp>=2.0.0`, `fastmcp>=3.0.0` in different PRs.  Standardise
   on `mcp>=1.0.0` only.

4. **Raw exceptions** — Letting `ValueError` or `KeyError` propagate
   from a tool crashes the MCP client connection.  Always catch and
   return structured dicts.

5. **Public `.tools` attribute** — `mcp._tool_manager.tools` does not
   exist.  Use `mcp._tool_manager._tools` (private attribute).

## Integration Points

- **All MCP servers** in `mcp_servers/` must follow this skill
- **Copilot agent** should reference this skill when assigned MCP
  server stories
- **Claude Code** follows this skill for Story 18.3 and future
  MCP server work
- **Code reviewer** validates against these rules during PR review
