#!/usr/bin/env python3
"""Regression for BUG-048 (surfaced by B-010 T1 keyless run).

When the Agent SDK returns a ResultMessage with subtype
"error_max_budget_usd", _collect_text must surface a clean BudgetExceededError.
Previously it raised from inside the ``async for`` while the query() async
generator was mid-iteration, so generator finalisation raised
``RuntimeError: aclose(): asynchronous generator is already running`` — masking
the real budget error. The fix breaks out of the loop and raises after the
generator has closed.
"""

from __future__ import annotations

import asyncio

import claude_agent_sdk as sdk
import pytest

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk._shared import BudgetExceededError


def _query_yields_budget_error(text: str | None):
    async def _q(*, prompt, options):
        if text is not None:
            yield sdk.AssistantMessage(
                content=[sdk.TextBlock(text=text)], model="claude-sonnet-4-6"
            )
        yield sdk.ResultMessage(
            subtype="error_max_budget_usd",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="s",
            total_cost_usd=0.99,
        )

    return _q


def test_budget_exceeded_raises_cleanly_not_runtimeerror(monkeypatch) -> None:
    monkeypatch.setattr(s3, "query", _query_yields_budget_error("partial draft"))
    # Must be BudgetExceededError, NOT a RuntimeError('aclose(): ... already running').
    with pytest.raises(BudgetExceededError):
        asyncio.run(s3._collect_text("p", "sys", max_budget_usd=0.10))


def test_budget_error_message_carries_cap_and_cost(monkeypatch) -> None:
    monkeypatch.setattr(s3, "query", _query_yields_budget_error(None))
    with pytest.raises(BudgetExceededError) as ei:
        asyncio.run(s3._collect_text("p", "sys", max_budget_usd=0.10))
    assert "0.99" in str(ei.value)  # cost_at_abort surfaced, not swallowed
