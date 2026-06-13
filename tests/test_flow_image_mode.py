#!/usr/bin/env python3
"""Tests for the run_flow() image-handshake policy (#410).

The flow's Python-API image policy:
- chart_only (default): no paid image API; run_pipeline strips the hero
  frontmatter before Stage 4 so a missing hero never forces a revision, and the
  draft ships image-less (NOT the blog-default.svg fallback, which the
  publication validator rejects at deploy).
- hero (opt-in): generate a DALL-E featured image after Stage 3.

DALL-E and the pipeline are mocked — no paid calls, no network. run_pipeline /
refine_image_metadata are patched as AsyncMocks so the real asyncio.run drives
them (no un-awaited-coroutine warnings).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

import src.agent_sdk.pipeline as pipeline
from scripts.publication_validator import PublicationValidator
from src.agent_sdk.pipeline import _strip_image_frontmatter
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
_ARTICLE_IMAGELESS = _strip_image_frontmatter(_ARTICLE)


def _result(article: str = _ARTICLE) -> _FakePipelineResult:
    return _FakePipelineResult(
        article=article, chart_data={"title": "C"}, publication_validator_issues=[]
    )


# ── flow constructor ──────────────────────────────────────────────────────


def test_invalid_image_mode_rejected() -> None:
    with pytest.raises(ValueError, match="image_mode"):
        EconomistContentFlow(image_mode="bogus")  # type: ignore[arg-type]


def test_default_image_mode_is_chart_only() -> None:
    assert EconomistContentFlow().image_mode == "chart_only"


# ── flow.generate_content ─────────────────────────────────────────────────


@patch("src.economist_agents.flow.generate_featured_image")
@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_chart_only_skips_dalle_and_ships_imageless(
    mock_run_pipeline: AsyncMock, mock_image: Mock
) -> None:
    mock_run_pipeline.return_value = _result(_ARTICLE_IMAGELESS)
    flow = EconomistContentFlow()  # default chart_only

    draft = flow.generate_content({"topic": "AI testing"})

    assert mock_run_pipeline.await_args.kwargs.get("image_mode") == "chart_only"
    mock_image.assert_not_called()
    # image-less, NOT the blog-default.svg fallback (which deploy rejects)
    assert draft["featured_image"] == ""
    assert draft["publication_validator_passed"] is True
    assert draft["article"].startswith("---")


@patch("src.economist_agents.flow.refine_image_metadata", new_callable=AsyncMock)
@patch("src.economist_agents.flow.generate_featured_image", return_value=True)
@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_hero_mode_calls_dalle(
    mock_run_pipeline: AsyncMock,
    mock_image: Mock,
    mock_refine: AsyncMock,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = _result()
    mock_refine.return_value = {"image_alt": "a", "image_caption": "c"}
    flow = EconomistContentFlow(image_mode="hero")

    draft = flow.generate_content({"topic": "AI coding"})

    assert mock_run_pipeline.await_args.kwargs.get("image_mode") == "hero"
    mock_image.assert_called_once()
    assert draft["featured_image"].endswith(".png")


@patch("src.economist_agents.flow.refine_image_metadata", new_callable=AsyncMock)
@patch("src.economist_agents.flow.generate_featured_image", return_value=False)
@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_hero_mode_without_openai_key_degrades_gracefully(
    mock_run_pipeline: AsyncMock,
    mock_image: Mock,
    mock_refine: AsyncMock,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock_run_pipeline.return_value = _result()
    mock_refine.return_value = {"image_alt": "", "image_caption": ""}
    flow = EconomistContentFlow(image_mode="hero")

    # Must not raise; falls back to the default image when generation fails.
    draft = flow.generate_content({"topic": "AI"})

    assert draft["featured_image"] == "/assets/images/blog-default.svg"


# ── deploy-time publication contract (the Critical the review caught) ──────


def test_chart_only_article_passes_image_contract() -> None:
    """The image-less chart_only article must clear the publication validator's
    image contract — no default_image_fallback, no missing_image_file."""
    validator = PublicationValidator(require_image_file=True)
    validator._check_image_contract(_ARTICLE_IMAGELESS)
    blocking = [
        i
        for i in validator.issues
        if i["check"] in ("default_image_fallback", "missing_image_file")
    ]
    assert blocking == []


def test_default_svg_fallback_would_be_rejected_control() -> None:
    """Control: the old behaviour (shipping blog-default.svg) IS rejected."""
    validator = PublicationValidator(require_image_file=True)
    validator._check_image_contract(
        _ARTICLE.replace("/assets/images/t.png", "/assets/images/blog-default.svg")
    )
    assert any(i["check"] == "default_image_fallback" for i in validator.issues)


# ── revision path carries the image policy ────────────────────────────────


@patch("src.economist_agents.flow.generate_featured_image")
@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_revision_carries_chart_only_image_mode(
    mock_run_pipeline: AsyncMock, mock_image: Mock, tmp_path, monkeypatch
) -> None:
    """A chart_only flow must run revision in chart_only mode too, or it would
    re-open the #403 missing-image false rejection on the revision path."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = _result(_ARTICLE_IMAGELESS)
    flow = EconomistContentFlow()  # chart_only
    flow.state = {
        "selected_topic": {"topic": "X"},
        "revision_feedback": ["fix it"],
        "retry_count": 0,
        "article_draft": {},
    }

    flow.request_revision()

    assert mock_run_pipeline.await_args.kwargs.get("image_mode") == "chart_only"
    mock_image.assert_not_called()


# ── run_pipeline image_mode seam ──────────────────────────────────────────


def _run_pipeline_capturing_stage4(image_mode: str) -> str:
    """Run run_pipeline with stage3/stage4 mocked; return the article Stage 4 saw."""
    stage3 = SimpleNamespace(
        article=_ARTICLE,
        chart_data={"title": "C"},
        total_cost_usd=0.05,
        writer_cost_usd=0.04,
        graphics_cost_usd=0.01,
        research_cost_usd=0.0,
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
