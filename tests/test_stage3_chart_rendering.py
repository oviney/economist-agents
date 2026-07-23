"""Tests for #403 slice 1: chart_renderer wired into stage3_runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.agent_sdk.chart_renderer import ChartRenderError
from src.agent_sdk.stage3_runner import _slug_for_chart, run_stage3

# ── slug derivation ──────────────────────────────────────────────────


def test_slug_comes_from_title_not_image_field() -> None:
    # B-008: the chart slug is the canonical title-based slug — NOT the hero
    # image field (which conflated the chart with the hero image and diverged
    # from the article filename).
    article = (
        '---\nlayout: post\ntitle: "The Real Headline"\n'
        "image: /assets/images/three-people-and-a-fleet.png\n"
        "---\n\nBody."
    )
    assert _slug_for_chart(article, "Some topic") == "the-real-headline"


def test_slug_falls_back_to_kebab_topic_when_no_title() -> None:
    article = "---\nlayout: post\n---\n\nBody."  # no title
    assert (
        _slug_for_chart(article, "Product Team Composition (Agentic AI)")
        == "product-team-composition-agentic-ai"
    )


def test_slug_strips_leading_and_trailing_hyphens() -> None:
    assert _slug_for_chart("---\nlayout: post\n---\n\n", "—An idea—") == "an-idea"


def test_slug_handles_topic_with_only_non_alnum() -> None:
    # No title, topic kebabs to empty -> canonical default.
    assert _slug_for_chart("---\nlayout: post\n---\n\n", "!!!") == "article"


# ── wire-up: run_stage3 produces chart_path ──────────────────────────


def test_run_stage3_renders_chart_png_to_output_charts_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end-ish: mock the two LLM calls, assert PNG file lands on disk
    and chart_path is populated on the Stage3Result."""

    # Run from inside tmp_path so output/ doesn't pollute the repo.
    monkeypatch.chdir(tmp_path)

    article_text = (
        "---\n"
        "layout: post\n"
        'title: "Test"\n'
        "date: 2026-05-24\n"
        "author: Ouray Viney\n"
        "categories:\n - Software Engineering\n"
        "image: /assets/images/test-chart-slug.png\n"
        'description: "A test article description that is exactly the right size."\n'
        "image_alt: alt\n"
        "image_caption: caption\n"
        "---\n\n"
        "Body paragraph one. As the chart shows, things are happening.\n"
    )
    chart_json = (
        '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'
    )

    # Two-call sequence: writer returns article, graphics returns JSON.
    call_results = iter([(article_text, 0.0), (chart_json, 0.0)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    monkeypatch.setattr(
        "src.agent_sdk.stage3_runner._collect_text",
        fake_collect,
    )
    monkeypatch.setattr(
        "src.agent_sdk.stage3_runner.build_research_brief",
        lambda topic: f"# Research Brief: {topic}\n\nfake source",
    )
    # Disable style memory fetch (avoids ChromaDB import / network).
    monkeypatch.setattr(
        "src.agent_sdk.stage3_runner._fetch_style_context",
        lambda topic: "",
    )

    result = asyncio.run(run_stage3("test topic"))

    assert result.chart_path is not None
    # B-008: chart PNG is named from the title ("Test") — the canonical slug —
    # not the hero image field.
    assert result.chart_path == Path("output/charts/test.png")
    assert result.chart_path.exists()
    assert result.chart_path.stat().st_size > 0


def test_run_stage3_fails_when_chart_render_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed chart spec must block a non-shippable article."""

    monkeypatch.chdir(tmp_path)

    article_text = (
        "---\nlayout: post\ntitle: x\nimage: /assets/images/x.png\n---\n\nbody"
    )
    # Empty data list — chart_renderer rejects this with ChartRenderError.
    chart_json = '{"title": "T", "data": []}'

    call_results = iter([(article_text, 0.0), (chart_json, 0.0)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    monkeypatch.setattr("src.agent_sdk.stage3_runner._collect_text", fake_collect)
    monkeypatch.setattr(
        "src.agent_sdk.stage3_runner.build_research_brief",
        lambda topic: "# brief\n\nsource",
    )
    monkeypatch.setattr(
        "src.agent_sdk.stage3_runner._fetch_style_context",
        lambda topic: "",
    )

    with pytest.raises(ChartRenderError, match="non-empty list"):
        asyncio.run(run_stage3("test"))
