#!/usr/bin/env python3
"""BUG-062 regression: the hero-prompt scaffolding comment must never ship in a
post that already has a real hero image.

The published flaky-tests article carried the full
``<!-- HERO IMAGE - generate an image from the prompt below... -->`` block,
prompt text and all, while ``image:`` in its frontmatter already pointed at a
generated SVG. B-016 added hero generation; the placeholder emitter was left in
place and the two paths never learned about each other. Invisible to readers, so
no gate and no human review caught it.
"""

from __future__ import annotations

from src.agent_sdk.pipeline import (
    _inject_hero_prompt_comment,
    _strip_hero_prompt_comment,
)

_PROMPT = (
    "Generate an editorial illustration for the article.\n"
    "Subject: an engineer pressing a green tick button.\n"
    "Palette: Economist red, deep navy, off-white"
)

_WITH_HERO = (
    "---\n"
    "layout: post\n"
    "title: t\n"
    "image: /assets/images/some-slug-hero.svg\n"
    "---\n"
    "\n"
    "First body paragraph.\n"
)

_NO_HERO = "---\nlayout: post\ntitle: t\n---\n\nFirst body paragraph.\n"


class TestInjectionIsSuppressedWhenAHeroExists:
    """The emitter must not add a placeholder for an image that is already set."""

    def test_no_comment_injected_when_image_frontmatter_is_set(self) -> None:
        out = _inject_hero_prompt_comment(_WITH_HERO, _PROMPT)

        assert "<!-- HERO IMAGE" not in out
        assert "Palette: Economist red" not in out
        # ...and the article is otherwise untouched.
        assert out == _WITH_HERO

    def test_comment_still_injected_when_there_is_no_hero(self) -> None:
        out = _inject_hero_prompt_comment(_NO_HERO, _PROMPT)

        assert "<!-- HERO IMAGE" in out
        assert "an engineer pressing a green tick button" in out

    def test_empty_image_value_is_not_treated_as_a_hero(self) -> None:
        # BUG-055 established that image: "" is not a real hero. It must still
        # get a placeholder rather than being read as "hero already present".
        article = _WITH_HERO.replace(
            "image: /assets/images/some-slug-hero.svg", 'image: ""'
        )
        out = _inject_hero_prompt_comment(article, _PROMPT)

        assert "<!-- HERO IMAGE" in out


class TestStripping:
    """Whatever slipped through earlier must be removable at finalisation."""

    def test_strips_the_placeholder_when_a_hero_is_present(self) -> None:
        leaked = (
            "---\n"
            "layout: post\n"
            "image: /assets/images/some-slug-hero.svg\n"
            "---\n"
            "\n"
            "<!-- HERO IMAGE — generate an image from the prompt below, then "
            "replace this whole comment with it "
            "(see output/posts/<slug>.image_prompt.md):\n"
            "\n"
            f"{_PROMPT}\n"
            "-->\n"
            "\n"
            "First body paragraph.\n"
        )
        out = _strip_hero_prompt_comment(leaked)

        assert "<!-- HERO IMAGE" not in out
        assert "Palette: Economist red" not in out
        # Frontmatter and body survive intact.
        assert "image: /assets/images/some-slug-hero.svg" in out
        assert "First body paragraph." in out
        assert out.startswith("---\n")

    def test_keeps_the_placeholder_when_there_is_no_hero(self) -> None:
        # Chart-only posts legitimately ship with the placeholder: it is how the
        # reviewer knows to draw the hero. Only remove it once a hero exists.
        chart_only = _inject_hero_prompt_comment(_NO_HERO, _PROMPT)
        out = _strip_hero_prompt_comment(chart_only)

        assert "<!-- HERO IMAGE" in out

    def test_is_a_no_op_on_an_article_that_never_had_one(self) -> None:
        assert _strip_hero_prompt_comment(_WITH_HERO) == _WITH_HERO

    def test_round_trip_leaves_no_scaffolding(self) -> None:
        """The exact BUG-062 sequence: chart-only inject, then a hero arrives."""
        chart_only = _inject_hero_prompt_comment(_NO_HERO, _PROMPT)
        with_hero = chart_only.replace(
            "title: t\n", "title: t\nimage: /assets/images/some-slug-hero.svg\n"
        )

        out = _strip_hero_prompt_comment(with_hero)

        assert "<!-- HERO IMAGE" not in out
        assert "image_prompt.md" not in out
        assert "First body paragraph." in out
