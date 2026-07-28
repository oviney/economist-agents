#!/usr/bin/env python3
"""B-019: the generated front matter must satisfy ``oviney/blog``'s post contract.

Publishing the first real article failed the blog's ``validate-editorial`` job
four times, each on a rule our own ``publication_validator`` does not have. Every
fix was applied to the live post by hand. These tests pin the generator-side
contract so the next article deploys unedited.

Measured contract: ``docs/blog-integration-constraints.md`` →
"The post front-matter contract".
"""

from __future__ import annotations

import re
from pathlib import Path

from src.agent_sdk._shared import apply_editorial_fixes
from src.agent_sdk.pipeline import _link_hero_asset

_DATE = "2026-07-26"

_BODY = (
    "\n\n## Opening\n\nFlaky tests cost real money. As the chart shows, the "
    "bill lands on payroll.\n\n## References\n\n1. A\n2. B\n3. C\n"
)


def _fm(article: str) -> str:
    """The front-matter block of a finalized article."""
    assert article.startswith("---")
    return article.split("---", 2)[1]


def _line(article: str, key: str) -> str:
    match = re.search(rf"^{key}:.*$", _fm(article), re.MULTILINE)
    return match.group(0) if match else ""


class TestCategoriesAreQuoted:
    """The blog's parser splits on ``", "`` — an unquoted list reads as ONE
    invalid category and hard-fails ``validate-post-quality.sh``."""

    def test_unquoted_inline_list_is_rewritten_quoted(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [Quality Engineering, Test Automation]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert (
            _line(out, "categories")
            == 'categories: ["Quality Engineering", "Test Automation"]'
        )

    def test_block_style_list_is_rewritten_inline_and_quoted(self) -> None:
        # Block-style YAML is not detected by the blog's line-based parser.
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories:\n  - Quality Engineering\n  - Security\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "categories") == (
            'categories: ["Quality Engineering", "Security"]'
        )
        assert "\n  - Quality Engineering" not in out

    def test_lowercase_variants_are_normalised_and_quoted(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [quality-engineering, test automation]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert (
            _line(out, "categories")
            == 'categories: ["Quality Engineering", "Test Automation"]'
        )

    def test_already_canonical_is_left_alone(self) -> None:
        canonical = 'categories: ["Quality Engineering"]'
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n{canonical}\n---' + _BODY
        )
        assert _line(apply_editorial_fixes(article, _DATE), "categories") == canonical


class TestCategoriesAreValidated:
    """Only the blog's four values are accepted; anything else is an ERROR there."""

    def test_off_list_category_is_dropped(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [Quality Engineering, DevOps]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "categories") == 'categories: ["Quality Engineering"]'

    def test_all_off_list_falls_back_to_the_default(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [DevOps, Culture]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "categories") == 'categories: ["Quality Engineering"]'

    def test_duplicates_are_collapsed(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [Security, security, Security]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "categories") == 'categories: ["Security"]'


class TestTagsDeriveFromCanonicalCategories:
    """Tags are kebab-cased categories (BUG-057), so they must be derived AFTER
    the categories line is canonical — otherwise a block-style list yields only
    the fallback tags."""

    def test_block_style_categories_still_produce_matching_tags(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories:\n  - Test Automation\n  - Security\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "tags") == "tags: [test-automation, security]"

    def test_dropped_category_does_not_leak_into_tags(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "categories: [Security, DevOps]\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert "devops" not in _line(out, "tags")


class TestSubtitleIsAlwaysEmitted:
    """``subtitle`` is a required field on the blog and was never emitted —
    a hard ERROR on every article we would publish."""

    def test_subtitle_is_backfilled_when_absent(self) -> None:
        article = f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n---' + _BODY
        out = apply_editorial_fixes(article, _DATE)
        assert _line(out, "subtitle").startswith("subtitle:")
        assert len(_line(out, "subtitle")) > len("subtitle: ")

    def test_a_writer_supplied_subtitle_is_left_alone(self) -> None:
        supplied = 'subtitle: "What a green build hides"'
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n{supplied}\n---' + _BODY
        )
        assert _line(apply_editorial_fixes(article, _DATE), "subtitle") == supplied

    def test_backfilled_subtitle_respects_the_word_cap(self) -> None:
        long_description = " ".join(f"word{i}" for i in range(80))
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            f'description: "{long_description}"\n---' + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        value = _line(out, "subtitle").split(":", 1)[1].strip().strip('"')
        # The blog's hard cap is 60 words; we target the 40-word soft cap.
        assert 0 < len(value.split()) <= 40

    def test_subtitle_is_quoted_so_a_colon_cannot_break_the_yaml(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            'description: "Flaky tests: the invisible tax"\n---' + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        value = _line(out, "subtitle").split(":", 1)[1].strip()
        assert value.startswith('"') and value.endswith('"')


class TestPlaceholderImageIsStripped:
    """The writer prompt used to ask for a literal ``/assets/images/SLUG.png``,
    which can never resolve. Per BUG-055 an absent ``image:`` is safe and a
    broken one is not, so strip it rather than quarantine the article."""

    def test_literal_slug_placeholder_is_removed(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "image: /assets/images/SLUG.png\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert not re.search(r"^image:", _fm(out), re.MULTILINE)

    def test_angle_bracket_placeholder_is_removed(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "image: /assets/images/<slug>-hero.svg\n---" + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert not re.search(r"^image:", _fm(out), re.MULTILINE)

    def test_a_real_looking_image_path_is_kept(self) -> None:
        real = "image: /assets/images/flaky-tests-hero.svg"
        article = f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n{real}\n---' + _BODY
        assert _line(apply_editorial_fixes(article, _DATE), "image") == real

    def test_image_alt_and_caption_are_not_touched(self) -> None:
        # Only the path is a placeholder; the writer's visual concept survives
        # because B-016 still needs it as the hero brief.
        article = (
            f'---\nlayout: post\ntitle: "T"\ndate: {_DATE}\n'
            "image: /assets/images/SLUG.png\n"
            'image_alt: "A developer watching a green dashboard"\n'
            'image_caption: "The build is green; the budget drains"\n---' + _BODY
        )
        out = apply_editorial_fixes(article, _DATE)
        assert "image_alt:" in _fm(out) and "image_caption:" in _fm(out)


class TestHeroAssetIsLinked:
    """The blog **requires** ``image:`` — both validate-posts.sh and
    validate-post-quality.sh error without it, and the path must resolve.

    Measured 2026-07-26 with scripts/acceptance_blog_frontmatter.sh: an article
    with no hero is rejected ("hero image not set"), which means **there is no
    publishable chart-only article**. This closes the B-015 open question. Here
    we only *link* an existing asset; drawing it is B-016b.
    """

    def test_an_existing_hero_svg_is_linked(self, tmp_path: Path) -> None:
        images = tmp_path / "images"
        images.mkdir()
        (images / "my-slug-hero.svg").write_text("<svg/>")
        article = '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n'
        out = _link_hero_asset(article, "my-slug", images_dir=images)
        assert "image: /assets/images/my-slug-hero.svg" in out

    def test_a_png_hero_is_linked_when_that_is_what_exists(
        self, tmp_path: Path
    ) -> None:
        images = tmp_path / "images"
        images.mkdir()
        (images / "my-slug-hero.png").write_text("stub")
        article = '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n'
        out = _link_hero_asset(article, "my-slug", images_dir=images)
        assert "image: /assets/images/my-slug-hero.png" in out

    def test_svg_wins_when_both_exist(self, tmp_path: Path) -> None:
        # Constraint #4 prefers SVG: the blog's responsive-image include rewrites
        # .png -> .webp, so a .png hero needs a .webp sibling and an .svg does not.
        images = tmp_path / "images"
        images.mkdir()
        (images / "my-slug-hero.png").write_text("stub")
        (images / "my-slug-hero.svg").write_text("<svg/>")
        article = '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n'
        assert "my-slug-hero.svg" in _link_hero_asset(
            article, "my-slug", images_dir=images
        )

    def test_no_hero_asset_leaves_the_key_absent(self, tmp_path: Path) -> None:
        # Absent is safe; an unresolvable path breaks the Jekyll build (BUG-055).
        images = tmp_path / "images"
        images.mkdir()
        article = '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n'
        out = _link_hero_asset(article, "my-slug", images_dir=images)
        assert not re.search(r"^image:", _fm(out), re.MULTILINE)

    def test_an_existing_correct_image_line_is_replaced_not_duplicated(
        self, tmp_path: Path
    ) -> None:
        images = tmp_path / "images"
        images.mkdir()
        (images / "my-slug-hero.svg").write_text("<svg/>")
        article = (
            '---\nlayout: post\ntitle: "T"\nimage: /assets/images/stale.png\n'
            "---\n\nBody.\n"
        )
        out = _link_hero_asset(article, "my-slug", images_dir=images)
        assert len(re.findall(r"^image:", _fm(out), re.MULTILINE)) == 1
        assert "stale.png" not in out

    def test_an_article_without_frontmatter_is_untouched(self, tmp_path: Path) -> None:
        images = tmp_path / "images"
        images.mkdir()
        (images / "my-slug-hero.svg").write_text("<svg/>")
        assert _link_hero_asset("no frontmatter", "my-slug", images_dir=images) == (
            "no frontmatter"
        )


class TestHeroMetadataSurvivesWhenAHeroExists:
    """chart_only was built on 'this article ships without a hero', which B-016b
    made false. It stripped image_alt/image_caption and injected a 'generate an
    image from this prompt' comment — so the blog rejected the article for
    'missing image_alt' even though a hero had been drawn (B-020 run 4)."""

    @staticmethod
    def _article() -> str:
        return (
            '---\nlayout: post\ntitle: "T"\n'
            'image_alt: "A developer waiting beside a queue of review cards"\n'
            'image_caption: "Waiting is the work nobody bills"\n'
            "---\n\n## Body\n\nText. As the chart shows, it costs.\n\n"
            "## References\n\n1. A\n2. B\n3. C\n"
        )

    def test_alt_and_caption_are_kept_when_a_hero_was_drawn(self) -> None:
        from src.agent_sdk.pipeline import _prepare_for_stage4

        out = _prepare_for_stage4(self._article(), hero_drawn=True)
        assert "image_alt:" in out
        assert "image_caption:" in out

    def test_alt_and_caption_are_stripped_when_no_hero_exists(self) -> None:
        # Unchanged behaviour for the genuinely-heroless case.
        from src.agent_sdk.pipeline import _prepare_for_stage4

        out = _prepare_for_stage4(self._article(), hero_drawn=False)
        assert "image_alt:" not in out

    def test_the_hero_prompt_comment_is_not_injected_when_a_hero_exists(self) -> None:
        from src.agent_sdk.pipeline import _maybe_inject_hero_prompt

        out = _maybe_inject_hero_prompt(
            "---\nlayout: post\n---\n\nBody.\n",
            image_prompt="draw something",
            hero_drawn=True,
        )
        assert "HERO IMAGE" not in out

    def test_the_hero_prompt_comment_is_still_injected_without_a_hero(self) -> None:
        from src.agent_sdk.pipeline import _maybe_inject_hero_prompt

        out = _maybe_inject_hero_prompt(
            "---\nlayout: post\n---\n\nBody.\n",
            image_prompt="draw something",
            hero_drawn=False,
        )
        assert "HERO IMAGE" in out


class TestAltTextComesFromTheDrawing:
    """The writer's image_alt is a drawing BRIEF ("An Economist-style editorial
    illustration of...") and the blog rejects that as prompt text, not alt text.
    The hero SVG's own <desc> describes what was actually drawn, which is what a
    screen reader needs. Found by B-020 run 5."""

    @staticmethod
    def _hero(desc: str) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
            f"<title>T</title><desc>{desc}</desc></svg>"
        )

    def test_alt_is_replaced_with_the_heros_description(self, tmp_path: Path) -> None:
        from src.agent_sdk.pipeline import _link_hero_asset

        images = tmp_path / "images"
        images.mkdir()
        desc = "A developer reaches toward a towering stack of amber review cards."
        (images / "s-hero.svg").write_text(self._hero(desc))
        article = (
            '---\nlayout: post\ntitle: "T"\n'
            'image_alt: "An Economist-style editorial illustration of a developer"\n'
            "---\n\nBody.\n"
        )
        out = _link_hero_asset(article, "s", images_dir=images)
        assert f'image_alt: "{desc}"' in out
        assert "editorial illustration" not in out

    def test_a_hero_without_a_desc_leaves_the_existing_alt_alone(
        self, tmp_path: Path
    ) -> None:
        from src.agent_sdk.pipeline import _link_hero_asset

        images = tmp_path / "images"
        images.mkdir()
        (images / "s-hero.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
            "<title>T</title></svg>"
        )
        article = '---\nlayout: post\ntitle: "T"\nimage_alt: "kept"\n---\n\nBody.\n'
        assert 'image_alt: "kept"' in _link_hero_asset(article, "s", images_dir=images)

    def test_alt_is_added_when_the_writer_omitted_it(self, tmp_path: Path) -> None:
        from src.agent_sdk.pipeline import _link_hero_asset

        images = tmp_path / "images"
        images.mkdir()
        (images / "s-hero.svg").write_text(self._hero("A quiet queue of cards."))
        out = _link_hero_asset(
            '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n', "s", images_dir=images
        )
        assert 'image_alt: "A quiet queue of cards."' in out

    def test_a_desc_with_quotes_cannot_break_the_yaml(self, tmp_path: Path) -> None:
        from src.agent_sdk.pipeline import _link_hero_asset

        images = tmp_path / "images"
        images.mkdir()
        (images / "s-hero.svg").write_text(self._hero('A "quoted" phrase inside.'))
        out = _link_hero_asset(
            '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n', "s", images_dir=images
        )
        import yaml

        yaml.safe_load(out.split("---", 2)[1])  # must parse
