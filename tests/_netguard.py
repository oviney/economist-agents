"""Outbound-network guard for the test suite (BUG-058).

Lives in its own module rather than in ``conftest.py`` so that the exception has
**one** identity. ``conftest.py`` is imported by pytest as the top-level module
``conftest``, so a test doing ``from tests.conftest import ...`` would get a
second, unrelated class object and ``pytest.raises`` would not match it. Both
``conftest`` and the tests import this module by the same dotted path
(``pythonpath = .`` in pytest.ini makes ``tests`` an implicit namespace package).
"""

from __future__ import annotations

import socket
from typing import Any

#: Connections we do not consider "the outside world" — local servers and IPC.
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


class NetworkAccessInTestError(RuntimeError):
    """A test attempted a real outbound network connection."""


def _message(host: object) -> str:
    return (
        f"Test attempted a real network connection to {host!r}. Mock it "
        "(CLAUDE.md: 'Mock APIs in tests'), or mark the test "
        "@pytest.mark.allow_network with a justification. See BUG-058."
    )


def _is_local(address: Any) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    return not isinstance(host, str) or host in _LOOPBACK


def _host_of(address: Any) -> Any:
    return address[0] if isinstance(address, tuple) else address


def install(monkeypatch: Any) -> None:
    """Patch ``socket.socket`` so non-loopback connections raise."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(self: socket.socket, address: Any, *a: Any, **kw: Any) -> Any:
        if _is_local(address):
            return real_connect(self, address, *a, **kw)
        raise NetworkAccessInTestError(_message(_host_of(address)))

    def guarded_connect_ex(
        self: socket.socket, address: Any, *a: Any, **kw: Any
    ) -> Any:
        if _is_local(address):
            return real_connect_ex(self, address, *a, **kw)
        raise NetworkAccessInTestError(_message(_host_of(address)))

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


class LiveModelCallInTestError(RuntimeError):
    """A test reached the real Agent SDK instead of a stub."""


def install_model_guard(monkeypatch: Any) -> None:
    """Block live Agent SDK calls from tests.

    The socket guard cannot see these: ``claude_agent_sdk.query`` spawns a
    subprocess CLI, so no in-process socket is opened. Found the hard way — the
    B-016b hero step holds its OWN reference to ``_collect_text``, so the ~10
    test files that patch ``stage3_runner._collect_text`` did not cover it, and
    ``make ci-local`` began making real model calls and writing generated SVGs
    into ``output/``.

    ``stage3_runner.query`` is the single chokepoint: every model call in the
    pipeline funnels through ``_collect_text``, which uses it. Tests that
    legitimately exercise ``_collect_text`` internals patch it themselves, and
    their patch is applied after this one, so it wins.
    """
    import src.agent_sdk.stage3_runner as stage3_runner

    def blocked(*args: Any, **kwargs: Any) -> Any:
        raise LiveModelCallInTestError(
            "Test reached the real Agent SDK. Patch the boundary you are "
            "exercising (e.g. stage3_runner._collect_text, or "
            "hero_author._collect_text — they are SEPARATE references), or mark "
            "the test @pytest.mark.allow_network with a justification."
        )

    monkeypatch.setattr(stage3_runner, "query", blocked)
