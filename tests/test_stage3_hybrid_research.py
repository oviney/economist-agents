#!/usr/bin/env python3
"""Integration tests for hybrid-research wiring in Stage 3 (#389).

Covers the slices that connect the writer search tool to the runner:
- the stat-survival contract (writer-fetched stats are not stripped by the audit
  once their source is appended to the brief),
- ``_collect_text`` actually forwarding the tool config to the SDK options,
- ``run_stage3`` appending the fetched-source supplement to the brief the audit
  sees and recording the search-call count.

The SDK is never invoked live — ``query`` / ``_collect_text`` are mocked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk._shared import audit_article_stats
from src.agent_sdk.tools import research_tools
from src.agent_sdk.tools.research_tools import SourceFetchSession


def test_writer_fetched_stat_survives_audit_when_brief_augmented(monkeypatch) -> None:
    """A stat from a writer-fetched source must survive the stat audit once the
    source is appended to the brief — and be stripped without it (control)."""
    monkeypatch.setattr(
        research_tools,
        "_run_provider_search",
        lambda q, n: [
            {"title": "Gartner", "url": "https://g/x", "snippet": "an 80% cut in costs"}
        ],
    )
    session = SourceFetchSession()
    session.search("qa roi")

    article = (
        "---\nlayout: post\ntitle: x\n---\n\n"
        "Self-healing tests deliver an 80% cut in costs.\n"
    )
    base_brief = "# Brief\n\nNo numbers here."

    # Control: without the supplement the fabricated-looking stat is stripped.
    stripped = audit_article_stats(article, base_brief)
    assert "80% cut" not in stripped

    # With the supplement appended, the cited stat survives.
    augmented = base_brief + session.brief_supplement()
    kept = audit_article_stats(article, augmented)
    assert "80% cut" in kept


def test_collect_text_passes_tool_config_to_options(monkeypatch) -> None:
    """_collect_text must forward mcp_servers/allowed_tools/max_turns to the SDK."""
    captured: dict = {}

    async def fake_query(*, prompt, options):
        captured["options"] = options
        return
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(s3, "query", fake_query)

    text, cost = asyncio.run(
        s3._collect_text(
            "prompt",
            "system",
            mcp_servers={"research": object()},
            allowed_tools=["mcp__research__search_for_source"],
            max_turns=8,
        )
    )

    opts = captured["options"]
    assert opts.max_turns == 8
    assert opts.allowed_tools == ["mcp__research__search_for_source"]
    assert "research" in opts.mcp_servers
    assert (text, cost) == ("", 0.0)


def test_collect_text_defaults_remain_toolless_single_turn(monkeypatch) -> None:
    """Default call (e.g. the graphics agent) stays single-turn with no tools."""
    captured: dict = {}

    async def fake_query(*, prompt, options):
        captured["options"] = options
        return
        yield  # pragma: no cover

    monkeypatch.setattr(s3, "query", fake_query)
    asyncio.run(s3._collect_text("p", "s"))

    opts = captured["options"]
    assert opts.max_turns == 1
    assert opts.allowed_tools == []
    assert opts.mcp_servers == {}


def test_run_stage3_appends_supplement_and_records_search_calls(
    tmp_path: Path, monkeypatch
) -> None:
    """run_stage3 must append the fetched-source supplement to the brief the
    audit sees, and record the writer's search-call count."""
    monkeypatch.chdir(tmp_path)

    class StubSession:
        max_calls = 3
        calls_made = 2

        def brief_supplement(self) -> str:
            return "\n\nSUPPLEMENT_MARKER_42pct"

    monkeypatch.setattr(s3, "SourceFetchSession", lambda *a, **k: StubSession())
    monkeypatch.setattr(s3, "build_search_tool", lambda session: object())
    monkeypatch.setattr(s3, "create_sdk_mcp_server", lambda name, tools: {name: tools})

    article_text = (
        "---\nlayout: post\ntitle: x\n"
        "image: /assets/images/test-slug.png\n---\n\n"
        "Body paragraph. As the chart shows, things happen.\n"
    )
    chart_json = (
        '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'
    )
    call_results = iter([(article_text, 0.0), (chart_json, 0.0)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    captured_brief: dict = {}

    def fake_audit(article: str, research_brief: str) -> str:
        captured_brief["brief"] = research_brief
        return article

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_audit_article_stats", fake_audit)
    monkeypatch.setattr(
        s3, "build_research_brief", lambda topic: "# Brief\n\nseed source"
    )
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")

    result = asyncio.run(s3.run_stage3("test topic"))

    assert "SUPPLEMENT_MARKER_42pct" in captured_brief["brief"]
    assert result.writer_search_calls == 2
