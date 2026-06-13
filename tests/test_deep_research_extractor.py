#!/usr/bin/env python3
"""Tests for the Deep Research extractor (#390). LLM calls mocked."""

from __future__ import annotations

import asyncio

from src.agent_sdk.research import extractor
from src.agent_sdk.research.extractor import _parse_extraction, extract_passages

_SOURCES = [
    {"title": "A", "url": "https://a", "snippet": "80% of teams report X."},
    {"title": "B", "url": "https://b", "snippet": "Adoption doubled in 2026."},
]


def _patch_llm(monkeypatch, text: str, cost: float = 0.005) -> list[int]:
    counter = [0]

    async def _fake(prompt, system_prompt, model, max_budget_usd=None):
        counter[0] += 1
        return text, cost

    monkeypatch.setattr(extractor, "research_llm_call", _fake)
    return counter


def test_empty_sources_makes_no_llm_call(monkeypatch) -> None:
    counter = _patch_llm(monkeypatch, "{}")

    result, cost = asyncio.run(extract_passages("q?", []))

    assert result == {"subquestion": "q?", "passages": [], "confidence": 0.0}
    assert cost == 0.0
    assert counter[0] == 0


def test_valid_extraction_parsed(monkeypatch) -> None:
    _patch_llm(
        monkeypatch,
        '{"passages": ["80% of teams report X."], "confidence": 0.8}',
        cost=0.004,
    )

    result, cost = asyncio.run(extract_passages("q?", _SOURCES))

    assert result["subquestion"] == "q?"
    assert result["passages"] == ["80% of teams report X."]
    assert result["confidence"] == 0.8
    assert cost == 0.004


def test_confidence_clamped_to_unit_interval() -> None:
    assert (
        _parse_extraction('{"passages": [], "confidence": 5}', [])["confidence"] == 1.0
    )
    assert (
        _parse_extraction('{"passages": [], "confidence": -2}', [])["confidence"] == 0.0
    )


def test_malformed_output_falls_back_to_snippets(monkeypatch) -> None:
    _patch_llm(monkeypatch, "the model rambled and produced no JSON")

    result, _ = asyncio.run(extract_passages("q?", _SOURCES))

    # retrieved evidence is preserved via the snippets, at low confidence
    assert result["passages"] == ["80% of teams report X.", "Adoption doubled in 2026."]
    assert 0.0 < result["confidence"] < 0.5


def test_fenced_json_object_parsed() -> None:
    text = '```json\n{"passages": ["p1"], "confidence": 0.6}\n```'
    parsed = _parse_extraction(text, _SOURCES)
    assert parsed["passages"] == ["p1"]
    assert parsed["confidence"] == 0.6
