#!/usr/bin/env python3
"""Tests for the run_flow() image-handshake policy (#410).

The flow's Python-API image policy:
- chart_only (default): no paid image API; run_pipeline strips the hero
  frontmatter before Stage 4 so a missing hero never forces a revision.
- hero (opt-in): generate a DALL-E featured image after Stage 3.

DALL-E and the pipeline are mocked — no paid calls, no network.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import src.agent_sdk.pipeline as pipeline
from src.economist_agents.flow import EconomistContentFlow


@dataclass
class _FakePipelineResult:
    article: str
    chart_data: dict
    editorial_score: int = 88
    gates_passed: int = 5
    publication_ready: bool = True
    publication_validator_passed: bool = True
    publication_validator_issues: list = None  # type: ignore[assignment]
    total_cost_usd: float = 0.05
    writer_cost_usd: float = 0.04
    graphics_cost_usd: float = 0.01
    writer_model: str = "claude-sonnet-4-6"
    graphics_model: str = "claude-sonnet-4-6"
    stage3_seconds: float = 1.0
    stage4_seconds: float = 0.01
    article_chars: int = 500


_ARTICLE = (
    '---\nlayout: post\ntitle: "T"\ndate: 2026-06-13\nauthor: "Ouray Viney"\n'
    'description: "A concise description for the test article frontmatter."\n'
    'categories: ["quality-engineering"]\nimage: /assets/images/t.png\n'
    "image_alt: alt\nimage_caption: cap\n---\n\nBody.\n"
)


def _result() -> _FakePipelineResult:
    return _FakePipelineResult(
        article=_ARTICLE, chart_data={"title": "C"}, publication_validator_issues=[]
    )


# ── flow constructor ──────────────────────────────────────────────────────


def test_invalid_image_mode_rejected() -> None:
    with pytest.raises(ValueError, match="image_mode"):
        EconomistContentFlow(image_mode="bogus")


def test_default_image_mode_is_chart_only() -> None:
    assert EconomistContentFlow().image_mode == "chart_only"


# ── flow.generate_content ─────────────────────────────────────────────────


@patch("src.economist_agents.flow.generate_featured_image")
@patch("src.economist_agents.flow.asyncio.run")
@patch("src.economist_agents.flow.run_pipeline")
def test_chart_only_skips_dalle_and_passes_mode(
    mock_run_pipeline: Mock, mock_asyncio_run: Mock, mock_image: Mock
) -> None:
    mock_asyncio_run.return_value = _result()
    flow = EconomistContentFlow()  # default chart_only

    draft = flow.generate_content({"topic": "AI testing"})

    # run_pipeline told to run chart-only
    assert mock_run_pipeline.call_args.kwargs.get("image_mode") == "chart_only"
    # no paid image API, no vision-refine second asyncio.run
    mock_image.assert_not_called()
    assert mock_asyncio_run.call_count == 1
    # ships on the default image, draft is otherwise intact
    assert draft["featured_image"] == "/assets/images/blog-default.svg"
    assert draft["publication_validator_passed"] is True
    assert draft["article"].startswith("---")


@patch("src.economist_agents.flow.generate_featured_image", return_value=True)
@patch("src.economist_agents.flow.asyncio.run")
@patch("src.economist_agents.flow.run_pipeline")
def test_hero_mode_calls_dalle_and_passes_mode(
    mock_run_pipeline: Mock, mock_asyncio_run: Mock, mock_image: Mock
) -> None:
    mock_asyncio_run.side_effect = [
        _result(),
        {"image_alt": "a", "image_caption": "c"},
    ]
    flow = EconomistContentFlow(image_mode="hero")

    draft = flow.generate_content({"topic": "AI coding"})

    assert mock_run_pipeline.call_args.kwargs.get("image_mode") == "hero"
    mock_image.assert_called_once()
    assert draft["featured_image"].endswith(".png")


# ── run_pipeline image_mode seam ──────────────────────────────────────────


def _run_pipeline_capturing_stage4(image_mode: str) -> str:
    """Run run_pipeline with stage3/stage4 mocked; return the article Stage 4 saw."""
    stage3 = SimpleNamespace(
        article=_ARTICLE,
        chart_data={"title": "C"},
        total_cost_usd=0.05,
        writer_cost_usd=0.04,
        graphics_cost_usd=0.01,
        writer_model="m",
        graphics_model="m",
        wall_seconds=1.0,
    )
    stage4 = SimpleNamespace(
        article=_ARTICLE,
        editorial_score=88,
        gates_passed=5,
        publication_ready=True,
        publication_validator_passed=True,
        publication_validator_issues=[],
        wall_seconds=0.01,
    )
    seen: dict = {}

    def _fake_stage4(article: str, chart_data: dict):
        seen["article"] = article
        return stage4

    async def _fake_stage3(*a, **k):
        return stage3

    with (
        patch.object(pipeline, "run_stage3", _fake_stage3),
        patch.object(pipeline, "run_stage4", _fake_stage4),
        patch.object(pipeline, "_append_cost_log", lambda *a, **k: None),
    ):
        asyncio.run(pipeline.run_pipeline("topic", image_mode=image_mode))
    return seen["article"]


def test_run_pipeline_chart_only_strips_hero_before_stage4() -> None:
    seen = _run_pipeline_capturing_stage4("chart_only")
    assert "image:" not in seen
    assert "image_alt:" not in seen
    assert "image_caption:" not in seen
    assert "Body." in seen  # body preserved


def test_run_pipeline_hero_keeps_image_before_stage4() -> None:
    seen = _run_pipeline_capturing_stage4("hero")
    assert "image: /assets/images/t.png" in seen
