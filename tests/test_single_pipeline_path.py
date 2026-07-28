#!/usr/bin/env python3
"""B-021 slice 3: the pipeline has exactly ONE path, and it is the one that works.

Before this, ``--image-mode hero`` was the DEFAULT and was dead: it ran the
retired human-image handshake, told the operator to paste a prompt into
chat.openai.com, and exited 10 without ever reaching Stage 4. The only mode that
ran end to end was ``chart_only`` — which, since B-016b, ships a Claude-drawn
hero, so its name lied too. The handshake existed to receive art from a raster
image model that Operating Constraint #4 forbids, and ``image_gate`` (BUG-060)
gated PNGs that path no longer produces.

These tests pin the contract that replaced all of it: no modes, no handshake,
no resume — run the topic, get an article.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import src.agent_sdk.pipeline as pipe

_ARTICLE = (
    "---\nlayout: post\ntitle: x\nimage: /assets/images/x-hero.svg\n---\n\n"
    "Body paragraph. As the chart shows, things happen.\n"
)


def _stage3(hero: Path | None, image_prompt: str = "") -> AsyncMock:
    """A Stage 3 result standing in for a completed generation."""
    result = AsyncMock()
    result.article = _ARTICLE
    result.chart_data = {"title": "T", "data": []}
    result.hero_path = hero
    result.image_prompt = image_prompt
    return result


# ── the CLI surface ───────────────────────────────────────────────────


@pytest.mark.parametrize("flag", ["--image-mode", "--resume", "--no-image"])
def test_the_handshake_flags_are_gone(flag: str, capsys) -> None:
    """Each flag selected or served the dead path. argparse must now reject it."""
    with pytest.raises(SystemExit) as excinfo:
        pipe.main([flag, "anything"])

    assert excinfo.value.code == 2, "argparse rejects unknown flags with exit 2"
    assert flag in capsys.readouterr().err


def test_no_exit_code_reserves_the_handshake_anymore() -> None:
    """Exit 10/11 meant 'paused for a human image' and 'the PNG gate failed'.
    Nothing can emit them now, so nothing may claim them."""
    assert not hasattr(pipe, "EXIT_HANDSHAKE_PENDING")
    assert not hasattr(pipe, "EXIT_IMAGE_GATE_FAILED")


def test_the_handshake_machinery_is_removed() -> None:
    for name in (
        "_run_stage3_with_handshake",
        "_print_handshake_message",
        "_run_resume",
    ):
        assert not hasattr(pipe, name), f"{name} still exists"


def test_the_png_image_gate_module_is_removed() -> None:
    """BUG-060: PNG magic bytes + 1792x1024 checks, dead since heroes became SVG."""
    with pytest.raises(ModuleNotFoundError):
        __import__("src.agent_sdk.image_gate")


# ── the surviving path ────────────────────────────────────────────────


def test_run_pipeline_no_longer_takes_an_image_mode() -> None:
    assert "image_mode" not in inspect.signature(pipe.run_pipeline).parameters


def test_a_drawn_hero_keeps_its_frontmatter(tmp_path: Path, monkeypatch) -> None:
    """The B-020 run-4 defect: stripping image_alt from an article that HAS a
    hero got it rejected by the blog for a missing image_alt."""
    monkeypatch.chdir(tmp_path)
    hero = tmp_path / "x-hero.svg"
    hero.write_text("<svg/>")
    monkeypatch.setattr(pipe, "run_stage3", AsyncMock(return_value=_stage3(hero)))
    monkeypatch.setattr(pipe, "run_stage4", lambda article, chart: _stage4(article))

    result = asyncio.run(pipe.run_pipeline("topic"))

    assert "image:" in result.article


def test_without_a_hero_the_prompt_is_surfaced_for_the_reviewer(
    tmp_path: Path, monkeypatch
) -> None:
    """Constraint #4 keeps the prompt sidecar available for hand-supplied art."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        pipe,
        "run_stage3",
        AsyncMock(return_value=_stage3(None, image_prompt="Draw a thing")),
    )
    monkeypatch.setattr(pipe, "run_stage4", lambda article, chart: _stage4(article))

    result = asyncio.run(pipe.run_pipeline("topic"))

    assert "Draw a thing" in result.article


def _stage4(article: str):
    """Minimal Stage 4 stand-in — the article passes through untouched."""
    from types import SimpleNamespace

    return SimpleNamespace(
        article=article,
        editorial_score=80,
        gates_passed=4,
        publication_ready=True,
        publication_validator_passed=True,
        publication_validator_issues=[],
        score_details={},
        wall_seconds=0.0,
    )
