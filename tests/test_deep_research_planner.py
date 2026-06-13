#!/usr/bin/env python3
"""Tests for the Deep Research planner (#390). LLM calls mocked."""

from __future__ import annotations

import asyncio

from src.agent_sdk.research import planner
from src.agent_sdk.research.planner import _parse_subquestions, plan_subquestions


def _patch_llm(monkeypatch, text: str, cost: float = 0.01) -> None:
    async def _fake(prompt, system_prompt, model, max_budget_usd=None):
        return text, cost

    monkeypatch.setattr(planner, "research_llm_call", _fake)


def test_parses_plain_json_array() -> None:
    assert _parse_subquestions('["a?", "b?", "c?"]') == ["a?", "b?", "c?"]


def test_parses_fenced_and_prose_wrapped_json() -> None:
    text = 'Here are the sub-questions:\n```json\n["one?", "two?"]\n```\nDone.'
    assert _parse_subquestions(text) == ["one?", "two?"]


def test_caps_at_five_subquestions() -> None:
    out = _parse_subquestions('["1","2","3","4","5","6","7"]')
    assert len(out) == 5


def test_drops_blank_entries() -> None:
    assert _parse_subquestions('["a?", "", "  ", "b?"]') == ["a?", "b?"]


def test_unparseable_output_returns_empty() -> None:
    assert _parse_subquestions("no array here") == []
    assert _parse_subquestions("[not valid json}") == []


def test_plan_subquestions_returns_questions_and_cost(monkeypatch) -> None:
    _patch_llm(monkeypatch, '["What is X?", "How does Y work?"]', cost=0.02)

    questions, cost = asyncio.run(plan_subquestions("Topic"))

    assert questions == ["What is X?", "How does Y work?"]
    assert cost == 0.02


def test_plan_subquestions_empty_on_bad_output(monkeypatch) -> None:
    _patch_llm(monkeypatch, "I could not decompose this.", cost=0.01)

    questions, cost = asyncio.run(plan_subquestions("Topic"))

    assert questions == []
    assert cost == 0.01
