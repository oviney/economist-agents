#!/usr/bin/env python3
"""Regression guard: stdio MCP servers must launch as standalone subprocesses.

The MCP client (Claude Code) starts each server with ``python mcp_servers/<name>.py``.
When launched that way, ``sys.path[0]`` is the ``mcp_servers/`` directory rather
than the project root, so a server that imports ``scripts.*`` or ``src.*`` without
bootstrapping the repo root onto ``sys.path`` crashes with ``ModuleNotFoundError``
and the client reports ``MCP error -32000: Connection closed``.

The unit tests in this package patch ``sys.path`` before importing the server
module, which masks that failure. These tests deliberately do NOT — they spawn the
server exactly as the client does and assert a clean JSON-RPC ``initialize``
handshake on stdout, with no import error on stderr.

Usage:
    pytest tests/test_mcp_servers/test_server_launch.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# stdio servers that import local packages (scripts.* / src.*) and need no
# external API keys to complete an initialize handshake.
_SERVERS = [
    "published_topics_server",
    "style_memory_server",
    "article_evaluator_server",
    "publication_validator_server",
]

_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    },
}


@pytest.mark.parametrize("server", _SERVERS)
def test_server_launches_and_completes_handshake(server: str) -> None:
    """Each stdio server, launched standalone, answers initialize on stdout."""
    script = _REPO_ROOT / "mcp_servers" / f"{server}.py"
    assert script.exists(), f"missing server script: {script}"

    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(_INITIALIZE) + "\n",
        capture_output=True,
        text=True,
        timeout=30,
        # cwd intentionally the repo root: even so, `python path/to/x.py` puts the
        # script dir (not cwd) on sys.path[0], so the bootstrap is what matters.
        cwd=str(_REPO_ROOT),
    )

    assert "ModuleNotFoundError" not in proc.stderr, (
        f"{server} failed to import when launched standalone:\n{proc.stderr}"
    )

    first_line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    assert first_line, f"{server} produced no stdout. stderr:\n{proc.stderr}"

    message = json.loads(first_line)
    assert message.get("id") == 1
    assert "result" in message, f"{server} did not return an initialize result"
    assert message["result"].get("protocolVersion")
