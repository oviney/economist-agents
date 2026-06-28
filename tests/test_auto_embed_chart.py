"""Tests for _auto_embed_chart — the mandatory-chart auto-embed gate.

Regression focus: in chart_only mode the hero ``image:`` frontmatter is stripped,
so the slug must fall back to the title. Without that, the chart is never
embedded and the article fails the CRITICAL missing_chart validator check.
"""

from __future__ import annotations

from src.agent_sdk._shared import _auto_embed_chart

_BODY = "Some analysis. As the chart shows, things rose.\n\n## References\n\n1. X\n"


def test_embeds_chart_from_hero_image_slug() -> None:
    article = (
        "---\ntitle: My Piece\nimage: /assets/images/rlhf-trends.png\n---\n\n" + _BODY
    )
    out = _auto_embed_chart(article)
    assert "![Chart](/assets/charts/rlhf-trends.png)" in out


def test_embeds_chart_from_title_when_image_frontmatter_stripped() -> None:
    """chart_only mode strips ``image:`` — the slug must fall back to the title."""
    article = '---\ntitle: "RLHF for Language Models"\n---\n\n' + _BODY
    out = _auto_embed_chart(article)
    assert "![Chart](/assets/charts/rlhf-for-language-models.png)" in out
    # embedded before the References section
    assert out.index("![Chart]") < out.index("## References")


def test_no_embed_when_neither_image_nor_title() -> None:
    article = "---\nlayout: post\n---\n\n" + _BODY
    assert _auto_embed_chart(article) == article


def test_idempotent_when_chart_already_present() -> None:
    article = (
        "---\ntitle: X\n---\n\nText.\n\n![Chart](/assets/charts/x.png)\n\n"
        "## References\n\n1. Y\n"
    )
    assert _auto_embed_chart(article) == article
