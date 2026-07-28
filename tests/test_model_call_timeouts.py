#!/usr/bin/env python3
"""Regression for BUG-059: every model call must be bounded in WALL CLOCK, not
just in cost.

``max_budget_usd`` stops a call from *spending*; it does nothing about a call
that stalls. Before this fix, ``stage3_runner._collect_text`` and both research
collectors awaited the Agent SDK's ``query()`` generator with no timeout, so a
hung call blocked Stage 3 forever with no output and no way to tell "slow" from
"dead" — hero draws legitimately run 440-600s, so the operator has no baseline.

The hero path was already bounded at its call site (``hero_author`` wraps
``_collect_text`` in ``asyncio.wait_for``); these tests cover the three
collectors that were not.

Bounds here are tiny so the suite stays fast. No test may reach a real model
(BUG-058, BUG-062) — ``query`` is always faked.
"""

from __future__ import annotations

import asyncio

import pytest

import src.agent_sdk.research._llm as research_llm
import src.agent_sdk.research.claude_web as claude_web
import src.agent_sdk.stage3_runner as s3
from src.agent_sdk._shared import ModelCallTimeoutError

_TINY_BOUND_S = 0.05


def _stalling_query(*args, **kwargs):
    """An SDK query that accepts the call and then never produces anything."""

    async def _gen():
        await asyncio.sleep(30)
        yield None  # pragma: no cover — the bound must fire first

    return _gen()


# ── stage3_runner._collect_text ───────────────────────────────────────


def test_collect_text_raises_a_typed_timeout_instead_of_hanging(monkeypatch) -> None:
    monkeypatch.setattr(s3, "query", _stalling_query)

    with pytest.raises(ModelCallTimeoutError) as excinfo:
        asyncio.run(s3._collect_text("prompt", "system", timeout_s=_TINY_BOUND_S))

    assert excinfo.value.timeout_s == _TINY_BOUND_S


def test_the_timeout_message_names_the_call_and_the_bound(monkeypatch) -> None:
    """An operator reading a log must learn WHICH call hung and for how long."""
    monkeypatch.setattr(s3, "query", _stalling_query)

    with pytest.raises(ModelCallTimeoutError) as excinfo:
        asyncio.run(
            s3._collect_text(
                "prompt", "system", timeout_s=_TINY_BOUND_S, label="writer"
            )
        )

    message = str(excinfo.value)
    assert "writer" in message
    assert "0.05" in message or "0.1" in message


def test_the_bound_actually_fires_promptly(monkeypatch) -> None:
    """A bound that only fires after the stall completes is not a bound."""
    monkeypatch.setattr(s3, "query", _stalling_query)

    loop = asyncio.new_event_loop()
    try:
        start = loop.time()
        with pytest.raises(ModelCallTimeoutError):
            loop.run_until_complete(
                s3._collect_text("prompt", "system", timeout_s=_TINY_BOUND_S)
            )
        elapsed = loop.time() - start
    finally:
        loop.close()

    assert elapsed < 5, f"bound took {elapsed:.1f}s to fire"


def test_a_healthy_call_is_untouched_by_the_bound(monkeypatch) -> None:
    """The guard must not change the happy path."""

    def _fast_query(*args, **kwargs):
        async def _gen():
            yield s3.AssistantMessage(
                content=[s3.TextBlock(text="hello")], model="claude-sonnet-4-6"
            )

        return _gen()

    monkeypatch.setattr(s3, "query", _fast_query)

    text, cost = asyncio.run(s3._collect_text("p", "s", timeout_s=30))

    assert text == "hello"
    assert cost == 0.0


def test_collect_text_is_bounded_by_default(monkeypatch) -> None:
    """A caller that passes no bound must still get one — that was the defect."""
    monkeypatch.setattr(s3, "query", _stalling_query)
    monkeypatch.setattr(s3, "DEFAULT_CALL_TIMEOUT_S", _TINY_BOUND_S)

    with pytest.raises(ModelCallTimeoutError):
        asyncio.run(s3._collect_text("prompt", "system"))


# ── research collectors ───────────────────────────────────────────────


def test_research_llm_call_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr(research_llm, "query", _stalling_query)

    with pytest.raises(ModelCallTimeoutError):
        asyncio.run(
            research_llm.research_llm_call(
                "p", "s", "claude-sonnet-4-6", timeout_s=_TINY_BOUND_S
            )
        )


def test_claude_web_brief_soft_degrades_on_a_stall(monkeypatch) -> None:
    """Research already degrades softly on SDK failure; a stall must be no worse
    than that — an empty brief returned promptly, never an infinite wait."""
    monkeypatch.setattr(claude_web, "query", _stalling_query)

    brief, cost = asyncio.run(
        claude_web.build_claude_web_brief("topic", timeout_s=_TINY_BOUND_S)
    )

    assert "Research Brief: topic" in brief
    assert cost == 0.0
