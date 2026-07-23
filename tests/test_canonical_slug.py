#!/usr/bin/env python3
"""B-008: one canonical slug across the article file, chart PNG, and image-prompt
sidecar. In chart_only runs the hero `image:` field is empty, and the chart slug
used to fall back to the *topic* while the article file and chart embed used the
*title* — so the embed could point at a PNG that doesn't exist."""

from __future__ import annotations

from src.agent_sdk.pipeline import _slug_from_article
from src.agent_sdk.stage3_runner import _slug_for_chart

_CHART_ONLY_ARTICLE = (
    '---\ntitle: "The Real Title"\nimage: ""\n---\n\n## Body\n\nSome text.\n'
)


def test_chart_and_article_slug_agree_when_image_absent() -> None:
    # The chart PNG/sidecar slug and the article-file slug must be identical.
    chart = _slug_for_chart(_CHART_ONLY_ARTICLE, "unrelated-topic")
    article = _slug_from_article(_CHART_ONLY_ARTICLE, "unrelated-topic")
    assert chart == article == "the-real-title"


def test_both_fall_back_to_the_same_slug_without_a_title() -> None:
    text = "no frontmatter at all"
    assert _slug_for_chart(text, "My Topic!") == _slug_from_article(text, "My Topic!")
