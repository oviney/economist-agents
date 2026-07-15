#!/usr/bin/env python3
"""The hero-image PROMPT is surfaced for review-time image generation (B-007;
CLAUDE.md Operating Constraint #4). The pipeline generates no image itself."""

from __future__ import annotations

from src.agent_sdk.pipeline import _inject_hero_prompt_comment

_PROMPT = (
    "Generate an editorial illustration for the article.\n"
    "Subject: a lonely server glowing red at dusk.\n"
    "Style: bold, high-contrast, no text."
)


def test_prompt_injected_after_frontmatter() -> None:
    article = "---\nlayout: post\ntitle: t\n---\n\nFirst body paragraph.\n"
    out = _inject_hero_prompt_comment(article, _PROMPT)

    # Frontmatter is preserved and still first.
    assert out.startswith("---\nlayout: post\ntitle: t\n---")
    # The prompt rides in an HTML comment (invisible when rendered, visible in
    # the PR diff) placed above the body.
    assert "<!-- HERO IMAGE" in out
    assert "a lonely server glowing red at dusk" in out
    assert out.index("<!-- HERO IMAGE") < out.index("First body paragraph.")


def test_comment_does_not_disturb_body_text() -> None:
    article = "---\ntitle: t\n---\n\nBody stays intact.\n"
    out = _inject_hero_prompt_comment(article, _PROMPT)
    assert "Body stays intact." in out


def test_no_frontmatter_still_prepends_prompt() -> None:
    out = _inject_hero_prompt_comment("just a body", _PROMPT)
    assert out.startswith("<!-- HERO IMAGE")
    assert "just a body" in out
