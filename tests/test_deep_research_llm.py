#!/usr/bin/env python3
"""Tests for the research Agent SDK helper (#390).

Exercises the real message-iteration body of research_llm_call by faking the
SDK query() generator — the one piece of genuine SDK integration in the package.
"""

from __future__ import annotations

import asyncio

import claude_agent_sdk as sdk

from src.agent_sdk.research import _llm


def _fake_query(messages):
    async def _q(*, prompt, options):
        for message in messages:
            yield message

    return _q


def _result(subtype: str, cost: float) -> sdk.ResultMessage:
    return sdk.ResultMessage(
        subtype=subtype,
        duration_ms=1,
        duration_api_ms=1,
        is_error=subtype != "success",
        num_turns=1,
        session_id="s",
        total_cost_usd=cost,
    )


def test_accumulates_text_and_captures_cost(monkeypatch) -> None:
    messages = [
        sdk.AssistantMessage(
            content=[sdk.TextBlock(text="Hello "), sdk.TextBlock(text="world")],
            model="claude-haiku-4-5",
        ),
        _result("success", 0.05),
    ]
    monkeypatch.setattr(_llm, "query", _fake_query(messages))

    text, cost = asyncio.run(
        _llm.research_llm_call("prompt", "system", "claude-haiku-4-5")
    )

    assert text == "Hello world"
    assert cost == 0.05


def test_budget_exceeded_returns_partial_without_raising(monkeypatch) -> None:
    """Unlike _collect_text, research_llm_call does NOT raise on budget abort —
    it returns the partial text so the layer falls back gracefully."""
    messages = [
        sdk.AssistantMessage(
            content=[sdk.TextBlock(text="partial")], model="claude-sonnet-4-6"
        ),
        _result("error_max_budget_usd", 2.5),
    ]
    monkeypatch.setattr(_llm, "query", _fake_query(messages))

    text, cost = asyncio.run(
        _llm.research_llm_call("prompt", "system", "claude-sonnet-4-6", 2.5)
    )

    assert text == "partial"
    assert cost == 2.5


def test_no_assistant_message_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(_llm, "query", _fake_query([_result("success", 0.0)]))

    text, cost = asyncio.run(
        _llm.research_llm_call("prompt", "system", "claude-haiku-4-5")
    )

    assert text == ""
    assert cost == 0.0
