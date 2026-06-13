#!/usr/bin/env python3
"""Regression guard: stdio MCP servers must launch and stay protocol-clean.

The MCP client (Claude Code) starts each server with ``python mcp_servers/<name>.py``.
When launched that way, ``sys.path[0]`` is the ``mcp_servers/`` directory rather
than the project root, so a server that imports ``scripts.*`` or ``src.*`` without
bootstrapping the repo root onto ``sys.path`` crashes with ``ModuleNotFoundError``
and the client reports ``MCP error -32000: Connection closed``.

On a stdio transport, **stdout carries the JSON-RPC stream**. Any stray ``print``
in an imported module — including ones that only fire later, on the first
``tools/call`` when a lazy singleton is constructed — corrupts that stream and
reproduces the same "Connection closed" failure, just deferred from launch to
first use. So these tests assert two things:

1. The server launches and answers ``initialize`` (no import crash).
2. Every line the server writes to stdout is valid JSON-RPC — across launch,
   handshake, ``tools/list`` and an actual ``tools/call`` — so a stray print on
   any reachable path is caught.

The unit tests in this package patch ``sys.path`` before importing the server
module, which masks the launch failure; these spawn a real subprocess instead.

Usage:
    pytest tests/test_mcp_servers/test_server_launch.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# stdio servers that import local packages (scripts.* / src.*) and need no
# external API keys to complete an initialize handshake.
_LOCAL_SERVERS = [
    "published_topics_server",
    "style_memory_server",
    "article_evaluator_server",
    "publication_validator_server",
]

# A representative, side-effect-light tool call per server that constructs the
# server's lazily-initialised backing object (the path where stray prints hide).
_TOOL_CALLS = {
    "published_topics_server": ("get_archive_stats", {}),
    "style_memory_server": ("query_style_memory", {"query": "test"}),
}

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
_INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def _run_server(
    server: str, payloads: list[dict[str, Any]]
) -> subprocess.CompletedProcess[str]:
    """Spawn a server standalone and feed it newline-delimited JSON-RPC messages."""
    script = _REPO_ROOT / "mcp_servers" / f"{server}.py"
    assert script.exists(), f"missing server script: {script}"
    stdin = "".join(json.dumps(p) + "\n" for p in payloads)
    # cwd is the repo root, but `python path/to/x.py` still puts the script dir
    # (not cwd) on sys.path[0] — so the bootstrap is what actually matters.
    return subprocess.run(
        [sys.executable, str(script)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_REPO_ROOT),
    )


def _assert_stdout_all_json_rpc(
    server: str, stdout: str, stderr: str
) -> list[dict[str, Any]]:
    """Every non-empty stdout line must parse as a JSON-RPC object."""
    messages: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:  # pragma: no cover - failure path
            pytest.fail(
                f"{server} wrote non-JSON to stdout (corrupts the stdio stream): "
                f"{line!r}\nstderr:\n{stderr}"
            )
        assert isinstance(message, dict) and message.get("jsonrpc") == "2.0", (
            f"{server} stdout line is not a JSON-RPC message: {line!r}"
        )
        messages.append(message)
    return messages


@pytest.mark.parametrize("server", _LOCAL_SERVERS)
def test_server_launches_and_completes_handshake(server: str) -> None:
    """Each stdio server, launched standalone, answers initialize on stdout."""
    proc = _run_server(server, [_INITIALIZE])

    assert "ModuleNotFoundError" not in proc.stderr, (
        f"{server} failed to import when launched standalone:\n{proc.stderr}"
    )
    messages = _assert_stdout_all_json_rpc(server, proc.stdout, proc.stderr)
    init_result = next((m for m in messages if m.get("id") == 1), None)
    assert init_result is not None, f"{server} returned no initialize response"
    assert "result" in init_result, f"{server} did not return an initialize result"
    assert init_result["result"].get("protocolVersion")


@pytest.mark.parametrize("server", sorted(_TOOL_CALLS))
def test_tool_call_keeps_stdout_protocol_clean(server: str) -> None:
    """A real tools/call must not leak any non-JSON-RPC output to stdout.

    Regression for #414: lazily-constructed backing objects (StyleMemoryTool /
    ArticleArchive) previously printed status banners to stdout on first use,
    corrupting the JSON-RPC stream after a clean handshake.
    """
    tool_name, arguments = _TOOL_CALLS[server]
    proc = _run_server(
        server,
        [
            _INITIALIZE,
            _INITIALIZED,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        ],
    )

    assert "ModuleNotFoundError" not in proc.stderr, proc.stderr
    # Purity is the assertion that matters: every stdout line is JSON-RPC, even
    # though the tool call itself may succeed or return a JSON-RPC error.
    _assert_stdout_all_json_rpc(server, proc.stdout, proc.stderr)
