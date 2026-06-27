#!/usr/bin/env python3
"""Tests for the writer-callable research tool (#389).

Providers are mocked — no live API calls. Covers the SourceFetchSession budget,
dedupe, and failure-resilience contracts, the brief supplement, and the SDK
tool wrapper's JSON output.
"""

from __future__ import annotations

import asyncio

import orjson

from src.agent_sdk.tools import research_tools
from src.agent_sdk.tools.research_tools import (
    DEFAULT_SEARCH_CALL_BUDGET,
    SourceFetchSession,
    build_search_tool,
)

_SAMPLE = [
    {"title": "Gartner Report", "url": "https://g.example/r", "snippet": "80% cut."},
]


def _patch_provider(monkeypatch, fn) -> list[int]:
    """Patch the provider seam; return a call counter list (counter[0])."""
    counter = [0]

    def _wrapped(query: str, max_results: int):
        counter[0] += 1
        return fn(query, max_results)

    monkeypatch.setattr(research_tools, "_run_provider_search", _wrapped)
    return counter


def test_search_returns_sources(monkeypatch) -> None:
    _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()

    results = session.search("self-healing tests roi")

    assert results == _SAMPLE
    assert session.calls_made == 1
    assert session.fetched == _SAMPLE


def test_budget_is_hard_capped(monkeypatch) -> None:
    counter = _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession(max_calls=3)

    for i in range(3):
        assert session.search(f"distinct query {i}") == _SAMPLE
    # 4th distinct query exceeds the budget → empty, provider NOT hit again.
    assert session.search("distinct query 4") == []
    assert session.calls_made == 3
    assert counter[0] == 3


def test_default_budget_is_three() -> None:
    assert DEFAULT_SEARCH_CALL_BUDGET == 3
    assert SourceFetchSession().max_calls == 3


def test_identical_query_is_deduped(monkeypatch) -> None:
    counter = _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()

    session.search("Same Query")
    session.search("same query")  # case-insensitive cache hit
    session.search("  same query  ")  # whitespace-insensitive cache hit

    assert counter[0] == 1, "identical queries must hit the cache, not the provider"
    assert session.calls_made == 1


def test_provider_failure_returns_empty_and_does_not_raise(monkeypatch) -> None:
    def _boom(query: str, max_results: int):
        raise RuntimeError("provider down")

    _patch_provider(monkeypatch, _boom)
    session = SourceFetchSession()

    assert session.search("anything") == []
    assert session.calls_made == 1  # the failed attempt still consumes budget


def test_brief_supplement_lists_fetched_sources(monkeypatch) -> None:
    _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()
    session.search("q")

    supplement = session.brief_supplement()

    assert "Writer-fetched sources" in supplement
    assert "Gartner Report" in supplement
    assert "https://g.example/r" in supplement


def test_brief_supplement_empty_when_nothing_fetched() -> None:
    assert SourceFetchSession().brief_supplement() == ""


def test_tool_returns_json_results(monkeypatch) -> None:
    _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()
    search_tool = build_search_tool(session)

    out = asyncio.run(search_tool.handler({"query": "roi of qa", "max_results": 2}))

    text = out["content"][0]["text"]
    assert orjson.loads(text) == _SAMPLE
    assert session.calls_made == 1


def test_provider_search_returns_and_maps_arxiv_results(monkeypatch) -> None:
    """arXiv papers are returned and mapped to title/url/snippet; Semantic
    Scholar is not consulted when arXiv has results."""
    monkeypatch.setattr(
        "scripts.arxiv_search.search_arxiv_for_topic",
        lambda q, max_papers: {
            "insights": {
                "papers_analyzed": [
                    {"title": "A", "url": "https://a", "key_insight": "arxiv snip"}
                ]
            }
        },
    )

    def _ss_must_not_be_called(q, max_papers):  # pragma: no cover
        raise AssertionError("Semantic Scholar must not be called when arXiv hits")

    monkeypatch.setattr(
        "scripts.semantic_scholar_search.search_semantic_scholar_for_topic",
        _ss_must_not_be_called,
    )

    out = research_tools._run_provider_search("q", 3)

    assert out == [{"title": "A", "url": "https://a", "snippet": "arxiv snip"}]


def test_provider_search_falls_back_to_semantic_scholar(monkeypatch) -> None:
    """When arXiv returns nothing, Semantic Scholar's ``papers`` list is read
    and mapped (title / url / abstract)."""
    monkeypatch.setattr(
        "scripts.arxiv_search.search_arxiv_for_topic",
        lambda q, max_papers: {"insights": {"papers_analyzed": []}},
    )
    monkeypatch.setattr(
        "scripts.semantic_scholar_search.search_semantic_scholar_for_topic",
        lambda q, max_papers: {
            "success": True,
            "papers": [{"title": "S", "url": "https://s", "abstract": "ss snip"}],
        },
    )

    out = research_tools._run_provider_search("q", 5)

    assert {"title": "S", "url": "https://s", "snippet": "ss snip"} in out


def test_tool_malformed_max_results_does_not_raise(monkeypatch) -> None:
    """A non-numeric max_results from the model must not break the tool handler."""
    _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()
    search_tool = build_search_tool(session)

    out = asyncio.run(search_tool.handler({"query": "roi", "max_results": "three"}))

    assert orjson.loads(out["content"][0]["text"]) == _SAMPLE


def test_tool_empty_query_short_circuits(monkeypatch) -> None:
    counter = _patch_provider(monkeypatch, lambda q, n: list(_SAMPLE))
    session = SourceFetchSession()
    search_tool = build_search_tool(session)

    out = asyncio.run(search_tool.handler({"query": "   "}))

    assert out["content"][0]["text"] == "[]"
    assert counter[0] == 0, "empty query must not hit the provider"
