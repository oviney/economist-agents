#!/usr/bin/env python3
"""BUG-058: no test may depend on a third party's availability or rate limits.

`make ci-local` is the only merge gate (ADR-0015). Six tests in
``test_economist_agent.py`` made live arXiv/citation HTTP calls, so that one file
took **10m24s** — and grew, because arXiv answers HTTP 429 under repeated runs.
A gate whose runtime is set by someone else's rate limiter, and which fails
offline, is worse than a merely slow one.

These tests guard the guard: if the ``_no_network`` fixture is ever weakened or
removed, they fail.
"""

from __future__ import annotations

import socket

import pytest

from tests._netguard import LiveModelCallInTestError, NetworkAccessInTestError

# A documentation IP (RFC 5737 TEST-NET-1). Never routable, so even if the guard
# were removed this test cannot silently start making real connections.
_UNROUTABLE = ("192.0.2.1", 80)


class TestOutboundIsBlocked:
    def test_connect_to_a_remote_host_raises(self) -> None:
        with (
            socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
            pytest.raises(NetworkAccessInTestError, match="real network connection"),
        ):
            sock.connect(_UNROUTABLE)

    def test_connect_ex_to_a_remote_host_raises(self) -> None:
        # requests/urllib3 reach for connect_ex on some paths, so it needs the
        # same treatment — otherwise the guard is trivially bypassable.
        with (
            socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
            pytest.raises(NetworkAccessInTestError),
        ):
            sock.connect_ex(_UNROUTABLE)

    def test_the_error_names_the_host_and_the_remedy(self) -> None:
        with (
            socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
            pytest.raises(NetworkAccessInTestError) as exc,
        ):
            sock.connect(("export.arxiv.org", 443))
        message = str(exc.value)
        assert "export.arxiv.org" in message
        assert "BUG-058" in message


class TestLoopbackStillWorks:
    """Local servers and IPC are legitimate; only third parties are blocked."""

    def test_loopback_is_not_blocked_by_the_guard(self) -> None:
        # Connect to a real listener we own, proving the guard lets loopback pass.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect(server.getsockname())  # must not raise
                assert client.getpeername()[0] == "127.0.0.1"


class TestOptOut:
    @pytest.mark.allow_network
    def test_the_marker_removes_the_guard(self) -> None:
        # Assert the guard is absent by inspecting the attribute rather than by
        # making a real connection — a test must not reach the internet even when
        # it is permitted to.
        assert socket.socket.connect.__name__ != "guarded_connect"

    def test_the_guard_is_installed_without_the_marker(self) -> None:
        assert socket.socket.connect.__name__ == "guarded_connect"


class TestLiveModelCallsAreBlocked:
    """The socket guard cannot see Agent SDK calls — they spawn a subprocess CLI,
    not an in-process socket. B-016b's hero step held its own reference to
    _collect_text, so tests patching stage3_runner._collect_text did not cover
    it and `make ci-local` started making real model calls."""

    def test_the_sdk_query_chokepoint_is_blocked(self) -> None:
        import src.agent_sdk.stage3_runner as stage3_runner

        with pytest.raises(LiveModelCallInTestError, match="real Agent SDK"):
            stage3_runner.query(prompt="hello", options=None)

    def test_collect_text_cannot_reach_the_model(self) -> None:
        import asyncio

        import src.agent_sdk.stage3_runner as stage3_runner

        with pytest.raises(LiveModelCallInTestError):
            asyncio.run(stage3_runner._collect_text("hi", "sys"))

    def test_the_hero_path_cannot_reach_the_model_either(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        # The specific gap that caused this: hero_author._collect_text is a
        # DIFFERENT reference from stage3_runner._collect_text.
        from src.agent_sdk.hero_author import author_hero_svg

        result = author_hero_svg(brief="draw", slug="s", images_dir=tmp_path)
        assert result.path is None
        assert "real Agent SDK" in result.error
