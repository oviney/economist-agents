#!/usr/bin/env python3
"""auto image_mode: run_pipeline generates a hero AND keeps a validator-clean
hero frontmatter alongside the chart (B-007). Keyless + offline (mocked SDK)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import src.agent_sdk.pipeline as pipe
import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.pipeline import _ensure_image_meta, _frontmatter_field, run_pipeline

_PARA = (
    "Software quality has become a boardroom concern rather than a backroom "
    "chore, and the shift shows up in how teams budget their time and trust. "
    "Engineers who once shipped on instinct now lean on dashboards, and the "
    "dashboards in turn shape which risks feel worth taking on any given day. "
    "The change is not merely procedural; it alters the culture of a team, "
    "rewarding those who can read a chart as fluently as they read a stack "
    "trace. Managers describe a quiet migration of authority from the people "
    "who write code to the systems that measure it, and the migration is not "
    "always comfortable. When a metric moves, the room reacts before anyone "
    "has asked what the number actually means, and that reflex is both the "
    "promise and the peril of a data-driven discipline. The best teams treat "
    "the dashboard as a question rather than a verdict, and the difference in "
    "outcomes is stark enough to show up in the quarterly numbers. "
)


def _full_article() -> str:
    body = "\n\n".join(
        f"## Section {t}\n\n{_PARA}\n\n{_PARA}"
        for t in ("One", "Two", "Three")
    )
    return (
        "---\nlayout: post\n"
        'title: "A Sharp Provocative Headline On Quality"\n'
        "image: /assets/images/a-sharp-provocative-headline-on-quality.png\n"
        'image_alt: "An editorial illustration of a burning dashboard."\n'
        'image_caption: "The metrics glow green while the system smoulders."\n'
        "---\n\n"
        + body
        + "\n\n## References\n\n"
        "1. State of Testing, PractiTest, 2026, https://practitest.com/x/\n"
        "2. World Quality Report, Capgemini, 2025, https://capgemini.com/y/\n"
        "3. DevOps Trends, Gartner, 2025, https://gartner.com/z/\n"
    )


_CHART = (
    '{"title": "Quality spend by function", "data": ['
    '{"metric": "Automated checks", "value": 62, "color": "navy"}, '
    '{"metric": "Manual review", "value": 13, "color": "grey"}]}'
)


def _wire(monkeypatch) -> None:
    results = iter([(_full_article(), 0.04), (_CHART, 0.01)])

    async def fake_collect(*a, **k):
        return next(results)

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")
    monkeypatch.setattr(
        s3, "build_claude_web_brief", AsyncMock(return_value=("# Brief", 0.1))
    )


def test_frontmatter_field_reads_values() -> None:
    art = '---\ntitle: "Hello World"\nimage_alt: "alt here"\n---\n\nbody'
    assert _frontmatter_field(art, "title") == "Hello World"
    assert _frontmatter_field(art, "image_alt") == "alt here"
    assert _frontmatter_field(art, "missing") == ""


def test_ensure_image_meta_backfills_when_absent() -> None:
    art = "---\nlayout: post\ntitle: t\n---\n\nbody"
    out = _ensure_image_meta(art, "the-slug", "my alt", "my caption")
    assert "image: /assets/images/the-slug.png" in out
    assert 'image_alt: "my alt"' in out
    assert 'image_caption: "my caption"' in out


def test_auto_mode_generates_hero_and_passes_validator(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    _wire(monkeypatch)

    result = asyncio.run(
        run_pipeline("topic", image_mode="auto", research_mode="claude_web")
    )

    # Validator clean (hero alt/caption present + chart embedded).
    assert result.publication_validator_passed is True
    # A hero PNG was actually produced under the drop dir.
    heroes = list((tmp_path / pipe.IMAGE_DROP_DIR).glob("*.png"))
    assert heroes, "auto mode must produce a hero image file"
    # The article keeps its hero frontmatter (not stripped) AND embeds the chart.
    assert "image:" in result.article
    assert "/assets/charts/" in result.article
