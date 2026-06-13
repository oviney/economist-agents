#!/usr/bin/env python3
"""Tests for the Deep Research synthesizer (#390). LLM calls mocked."""

from __future__ import annotations

import asyncio

from src.agent_sdk.research import synthesizer
from src.agent_sdk.research.synthesizer import _parse_verdict, assess_completeness

_FINDINGS = [
    {"subquestion": "q1?", "passages": ["p1"], "confidence": 0.8},
    {"subquestion": "q2?", "passages": [], "confidence": 0.0},
]


def _patch_llm(monkeypatch, text: str, cost: float = 0.01) -> None:
    async def _fake(prompt, system_prompt, model, max_budget_usd=None):
        return text, cost

    monkeypatch.setattr(synthesizer, "research_llm_call", _fake)


def test_enough_true_clears_gaps() -> None:
    verdict = _parse_verdict('{"enough": true, "gaps": ["ignored?"]}')
    assert verdict == {"enough": True, "gaps": []}


def test_not_enough_returns_gaps() -> None:
    verdict = _parse_verdict('{"enough": false, "gaps": ["new q1?", "new q2?"]}')
    assert verdict == {"enough": False, "gaps": ["new q1?", "new q2?"]}


def test_gaps_capped() -> None:
    verdict = _parse_verdict('{"enough": false, "gaps": ["1","2","3","4","5","6","7"]}')
    assert len(verdict["gaps"]) == 5


def test_unparseable_output_stops_loop() -> None:
    # Safe default: stop rather than spin.
    assert _parse_verdict("no json here") == {"enough": True, "gaps": []}


def test_assess_completeness_returns_verdict_and_cost(monkeypatch) -> None:
    _patch_llm(monkeypatch, '{"enough": false, "gaps": ["gap?"]}', cost=0.03)

    verdict, cost = asyncio.run(assess_completeness("Topic", _FINDINGS))

    assert verdict == {"enough": False, "gaps": ["gap?"]}
    assert cost == 0.03
