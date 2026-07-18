#!/usr/bin/env python3
"""Tests for the keyless claude_web researcher (B-006).

Claude does its own live web research via the Agent SDK's WebSearch/WebFetch
tools — no Serper, no ANTHROPIC_API_KEY. These tests fake the SDK query()
generator so they stay offline and keyless, and assert the researcher:
- returns a brief string with the anti-fabrication guardrail contract,
- surfaces the SDK cost,
- enables the WebSearch/WebFetch tools,
- constructs no anthropic client and reads no SERPER_API_KEY.
"""

from __future__ import annotations

import asyncio

import claude_agent_sdk as sdk

from src.agent_sdk.research import claude_web


def _fake_query(messages, captured: dict | None = None):
    async def _q(*, prompt, options):
        if captured is not None:
            captured["prompt"] = prompt
            captured["options"] = options
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


def _assistant(text: str) -> sdk.AssistantMessage:
    return sdk.AssistantMessage(
        content=[sdk.TextBlock(text=text)], model="claude-sonnet-4-6"
    )


def test_returns_brief_with_guardrails_and_cost(monkeypatch) -> None:
    body = (
        "## AI in software testing\n"
        "- According to PractiTest 2026 State of Testing, 81% of testers use AI "
        "tools. Source: https://www.practitest.com/state-of-testing/"
    )
    monkeypatch.setattr(
        claude_web, "query", _fake_query([_assistant(body), _result("success", 0.2)])
    )

    brief, cost = asyncio.run(claude_web.build_claude_web_brief("AI testing"))

    assert "# Research Brief: AI testing" in brief
    # Anti-fabrication guardrail contract (same as the deterministic brief).
    assert "Do NOT invent statistics" in brief
    assert "81%" in brief
    assert "https://www.practitest.com/state-of-testing/" in brief
    assert cost == 0.2


def test_enables_web_tools_and_is_keyless(monkeypatch) -> None:
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    captured: dict = {}
    monkeypatch.setattr(
        claude_web,
        "query",
        _fake_query([_assistant("- claim. Source: https://x.test")], captured),
    )

    brief, _ = asyncio.run(claude_web.build_claude_web_brief("topic"))

    tools = list(captured["options"].allowed_tools)
    assert "WebSearch" in tools
    assert "WebFetch" in tools
    assert brief  # non-empty even with every key unset


def test_empty_response_still_returns_guardrail_header(monkeypatch) -> None:
    monkeypatch.setattr(claude_web, "query", _fake_query([_result("success", 0.0)]))

    brief, cost = asyncio.run(claude_web.build_claude_web_brief("topic"))

    assert "# Research Brief: topic" in brief
    assert cost == 0.0
