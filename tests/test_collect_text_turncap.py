#!/usr/bin/env python3
"""Regression for BUG-041 (surfaced by B-006 Checkpoint B run 2).

The subscription CLI raises 'Reached maximum number of turns (N)' instead of
returning a ResultMessage. _collect_text must proceed with any text already
collected rather than crashing the whole pipeline — but still re-raise when no
text was produced or the error is unrelated.
"""

from __future__ import annotations

import asyncio

import claude_agent_sdk as sdk
import pytest

import src.agent_sdk.stage3_runner as s3


def _query_yields_then_raises(text: str | None, exc: Exception):
    async def _q(*, prompt, options):
        if text is not None:
            yield sdk.AssistantMessage(
                content=[sdk.TextBlock(text=text)], model="claude-sonnet-4-6"
            )
        raise exc

    return _q


def test_turn_cap_with_partial_text_is_tolerated(monkeypatch) -> None:
    monkeypatch.setattr(
        s3,
        "query",
        _query_yields_then_raises(
            '{"title": "T"}', Exception("Reached maximum number of turns (4)")
        ),
    )
    text, cost = asyncio.run(s3._collect_text("p", "sys"))
    assert text == '{"title": "T"}'
    assert cost == 0.0


def test_turn_cap_with_no_text_reraises(monkeypatch) -> None:
    monkeypatch.setattr(
        s3,
        "query",
        _query_yields_then_raises(
            None, Exception("Reached maximum number of turns (1)")
        ),
    )
    with pytest.raises(Exception, match="maximum number of turns"):
        asyncio.run(s3._collect_text("p", "sys"))


def test_unrelated_error_always_reraises(monkeypatch) -> None:
    monkeypatch.setattr(
        s3,
        "query",
        _query_yields_then_raises("some text", RuntimeError("network exploded")),
    )
    with pytest.raises(RuntimeError, match="network exploded"):
        asyncio.run(s3._collect_text("p", "sys"))
