#!/usr/bin/env python3
"""The flow's image contract — one path, image-less draft, no paid image API.

Replaces ``test_flow_image_mode.py``. There is no image *mode* to test any more:
B-021 gave ``run_pipeline`` a single path, and B-022 removed the flow's
``image_mode`` along with the DALL-E branch behind it. What survives is the
contract that branch existed to satisfy, and the reason it had to go:

- The draft ships **image-less**, never ``blog-default.svg``. The default-image
  fallback is a CRITICAL deploy-time rejection, so the old ``hero`` mode's
  graceful degradation degraded straight into an unpublishable article.
- The hero itself rides in the article frontmatter, drawn by Stage 3 (B-016b).

``run_pipeline`` is patched as an AsyncMock so the real ``asyncio.run`` drives it
(no un-awaited-coroutine warnings). Nothing paid, nothing networked.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

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


# ── the flow takes one path ───────────────────────────────────────────────


def test_the_flow_takes_no_image_policy_argument() -> None:
    """B-022: the constructor no longer offers a choice, because there isn't one."""
    import inspect

    params = inspect.signature(EconomistContentFlow.__init__).parameters
    assert "image_mode" not in params


def test_the_flow_no_longer_reaches_for_dalle() -> None:
    """The adapter must be unreferenced from flow.py — not merely unused."""
    import src.economist_agents.flow as flow_module

    assert not hasattr(flow_module, "generate_featured_image")


@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_generate_content_ships_the_draft_image_less(
    mock_run_pipeline: AsyncMock,
) -> None:
    mock_run_pipeline.return_value = _result(_ARTICLE_IMAGELESS)
    flow = EconomistContentFlow()

    draft = flow.generate_content({"topic": "AI testing"})

    assert "image_mode" not in mock_run_pipeline.await_args.kwargs
    # image-less, NOT the blog-default.svg fallback (which deploy rejects)
    assert draft["featured_image"] == ""
    assert draft["publication_validator_passed"] is True
    assert draft["article"].startswith("---")


@patch("src.economist_agents.flow.run_pipeline", new_callable=AsyncMock)
def test_the_revision_path_takes_the_same_single_path(
    mock_run_pipeline: AsyncMock, tmp_path, monkeypatch
) -> None:
    """Revision must not reintroduce a second policy — that was the #403
    missing-image false rejection."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = _result(_ARTICLE_IMAGELESS)
    flow = EconomistContentFlow()
    flow.state = {
        "selected_topic": {"topic": "X"},
        "revision_feedback": ["fix it"],
        "retry_count": 0,
        "article_draft": {},
    }

    flow.request_revision()

    assert "image_mode" not in mock_run_pipeline.await_args.kwargs


# ── deploy-time publication contract ──────────────────────────────────────


def test_the_image_less_article_passes_the_image_contract() -> None:
    """No default_image_fallback, no missing_image_file."""
    validator = PublicationValidator(require_image_file=True)
    validator._check_image_contract(_ARTICLE_IMAGELESS)
    blocking = [
        i
        for i in validator.issues
        if i["check"] in ("default_image_fallback", "missing_image_file")
    ]
    assert blocking == []


def test_the_default_svg_fallback_is_rejected_control() -> None:
    """Control, and the reason B-022 was a removal rather than a repair: the
    DALL-E branch's own failure path shipped blog-default.svg, which deploy
    rejects outright."""
    validator = PublicationValidator(require_image_file=True)
    validator._check_image_contract(
        _ARTICLE.replace("/assets/images/t.png", "/assets/images/blog-default.svg")
    )
    assert any(i["check"] == "default_image_fallback" for i in validator.issues)
