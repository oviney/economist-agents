#!/usr/bin/env python3
"""Tests for Stage4Crew deterministic editorial post-processing."""

import pytest

from src.agent_sdk._shared import (
    _BANNED_CLOSINGS,
    _enforce_heading_limit,
)
from src.agent_sdk._shared import (
    apply_editorial_fixes as _apply_editorial_fixes,
)


class TestBritishSpelling:
    """British spelling replacements."""

    def test_organization_to_organisation(self) -> None:
        result = _apply_editorial_fixes("The organization grew.")
        assert "organisation" in result
        assert "organization" not in result

    def test_optimize_to_optimise(self) -> None:
        result = _apply_editorial_fixes("We optimize the process.")
        assert "optimise" in result

    def test_analyze_to_analyse(self) -> None:
        result = _apply_editorial_fixes("They analyze the data.")
        assert "analyse" in result

    def test_behavior_to_behaviour(self) -> None:
        result = _apply_editorial_fixes("User behavior changed.")
        assert "behaviour" in result


class TestBannedPhrases:
    """Banned phrase removal."""

    def test_game_changer_removed(self) -> None:
        result = _apply_editorial_fixes("This is a game-changer for testing.")
        assert "game-changer" not in result

    def test_paradigm_shift_removed(self) -> None:
        result = _apply_editorial_fixes("A paradigm shift in quality.")
        assert "paradigm shift" not in result

    def test_case_insensitive_removal(self) -> None:
        result = _apply_editorial_fixes("This is a GAME-CHANGER.")
        assert "game-changer" not in result.lower()


class TestExclamationPoints:
    """Exclamation point removal."""

    def test_exclamation_replaced_with_period(self) -> None:
        result = _apply_editorial_fixes("This is great!")
        assert "!" not in result
        assert "This is great." in result

    def test_exclamation_preserved_in_code_blocks(self) -> None:
        article = "Text here.\n\n```python\nprint('hello!')\n```\n\nMore text!"
        result = _apply_editorial_fixes(article)
        assert "hello!" in result  # preserved in code block
        assert result.endswith("More text.")  # fixed outside code block


class TestDateFix:
    """YAML frontmatter date correction."""

    def test_wrong_date_corrected(self) -> None:
        article = '---\nlayout: post\ntitle: "Test"\ndate: 2024-01-01\n---\n\nContent'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert "date: 2026-04-03" in result
        assert "date: 2024-01-01" not in result

    def test_correct_date_unchanged(self) -> None:
        article = '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-03\n---\n\nContent'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert "date: 2026-04-03" in result

    def test_no_date_fix_when_not_provided(self) -> None:
        article = "---\nlayout: post\ndate: 2024-01-01\n---\n\nContent"
        result = _apply_editorial_fixes(article, current_date=None)
        assert "date: 2024-01-01" in result


class TestArticleIntegrity:
    """Verify fixes don't destroy article content."""

    def test_frontmatter_preserved(self) -> None:
        article = '---\nlayout: post\ntitle: "Quality Engineering"\ndate: 2026-04-03\n---\n\nContent here.'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert result.startswith("---\n")
        assert "layout: post" in result
        assert 'title: "Quality Engineering"' in result
        assert "Content here." in result

    def test_long_article_not_truncated(self) -> None:
        body = " ".join(["word"] * 1000)
        article = f'---\ntitle: "Test"\ndate: 2026-04-03\n---\n\n{body}'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert len(result.split()) >= 1000

    def test_double_spaces_cleaned(self) -> None:
        result = _apply_editorial_fixes("This is a  game-changer  for testing.")
        assert "  " not in result


class TestHedgingPhrases:
    """Hedging phrase removal (SKILL.md Rule 4)."""

    def test_it_is_worth_noting_removed(self) -> None:
        result = _apply_editorial_fixes("It is worth noting that quality matters.")
        assert "it is worth noting" not in result.lower()

    def test_it_should_be_noted_removed(self) -> None:
        result = _apply_editorial_fixes("It should be noted that costs have risen.")
        assert "it should be noted" not in result.lower()

    def test_one_might_removed(self) -> None:
        result = _apply_editorial_fixes("One might expect the results to be clear.")
        assert "one might" not in result.lower()

    def test_it_would_be_misguided_removed(self) -> None:
        result = _apply_editorial_fixes(
            "It would be misguided to ignore these findings.",
        )
        assert "it would be misguided" not in result.lower()

    def test_in_practical_terms_removed(self) -> None:
        result = _apply_editorial_fixes(
            "In practical terms, this means faster delivery.",
        )
        assert "in practical terms" not in result.lower()


class TestVerbosePadding:
    """Verbose padding removal (SKILL.md Rule 6)."""

    def test_it_goes_without_saying_removed(self) -> None:
        result = _apply_editorial_fixes(
            "It goes without saying that testing is important.",
        )
        assert "it goes without saying" not in result.lower()

    def test_needless_to_say_removed(self) -> None:
        result = _apply_editorial_fixes("Needless to say, quality is paramount.")
        assert "needless to say" not in result.lower()

    def test_as_mentioned_earlier_removed(self) -> None:
        result = _apply_editorial_fixes("As mentioned earlier, the team struggled.")
        assert "as mentioned earlier" not in result.lower()

    def test_content_retained_after_padding_removal(self) -> None:
        result = _apply_editorial_fixes("Needless to say, the framework works well.")
        assert "the framework works well" in result


class TestCategoryNormalization:
    """Category casing normalization to Title Case (blog contract, GH #319)."""

    def test_kebab_to_title_case(self) -> None:
        article = '---\ncategories: ["quality-engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "Quality Engineering" in result
        # Scoped to the categories line: the derived `tags:` line is *required*
        # to be lowercase-hyphen (BUG-057), so a document-wide assertion here
        # would forbid a correct tag value.
        categories_line = next(
            ln for ln in result.split("\n") if ln.startswith("categories:")
        )
        assert "quality-engineering" not in categories_line

    def test_lowercase_spaces_to_title_case(self) -> None:
        article = '---\ncategories: ["software engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "Software Engineering" in result

    def test_already_title_case_unchanged(self) -> None:
        article = '---\ncategories: ["Quality Engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "Quality Engineering" in result

    def test_test_automation_normalized_to_title(self) -> None:
        article = '---\ncategories: ["test-automation"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "Test Automation" in result


class TestStage4NoLongerEmbedsACharter:
    """B-042: Stage 4 stopped inserting a chart embed unconditionally.

    An embed is a *claim that a figure exists*, and Stage 4 was in no position
    to make it: the PNG was often never rendered, so the embed satisfied
    `missing_chart` with a broken link. The embed now happens in `make art`,
    after the owner has actually made the chart — see
    `tests/test_finalise_art.py`. `_auto_embed_chart` itself is unchanged and
    still tested there.
    """

    def test_no_chart_is_embedded_by_stage_four(self) -> None:
        article = (
            "---\ntitle: My Slug\nimage: /assets/images/my-slug.png\n---\n"
            "Article body.\n\n## References\n\n1. Source"
        )
        assert "![Chart]" not in _apply_editorial_fixes(article)

    def test_an_existing_chart_embed_is_left_alone(self) -> None:
        """The owner's own embed must survive Stage 4 untouched."""
        article = (
            "---\ntitle: My Slug\nimage: /assets/images/my-slug.png\n---\n"
            "Body.\n\n![Chart](/assets/charts/my-slug.png)\n\n## References\n"
        )
        assert _apply_editorial_fixes(article).count("![Chart]") == 1


class TestNewHedgingPhrases:
    """New hedging phrases added in Story 1."""

    def test_one_suspects_removed(self) -> None:
        """Article containing 'One suspects' has the phrase stripped."""
        result = _apply_editorial_fixes("One suspects the future is bleak.")
        assert "One suspects" not in result
        assert "the future is bleak" in result

    def test_it_is_clear_that_removed(self) -> None:
        """Article containing 'it is clear that' has the phrase stripped."""
        result = _apply_editorial_fixes("It is clear that progress has stalled.")
        assert "it is clear that" not in result.lower()
        assert "progress has stalled" in result

    def test_one_suspects_in_closing_banned(self) -> None:
        """'One suspects' appears in _BANNED_CLOSINGS."""
        assert "One suspects" in _BANNED_CLOSINGS


class TestHeadingLimitEnforcement:
    """Heading count enforcement (Story 3)."""

    def test_headings_under_limit_unchanged(self) -> None:
        """Article with 3 headings passes through unchanged."""
        article = (
            "---\ntitle: Test\n---\n\n"
            "## Introduction\n\nParagraph one.\n\n"
            "## Analysis\n\nParagraph two.\n\n"
            "## Conclusion\n\nParagraph three.\n"
        )
        result = _enforce_heading_limit(article)
        assert result.count("\n## ") == 3

    def test_headings_over_limit_merged(self) -> None:
        """Article with 6 headings is reduced to 4."""
        sections = []
        line = "Line.\n"
        for i in range(6):
            body = line * (i + 1)
            sections.append(f"## Section {i + 1}\n\n{body}")
        article = "---\ntitle: Test\n---\n\n" + "\n".join(sections)
        result = _enforce_heading_limit(article)
        heading_count = sum(
            1
            for line in result.split("\n")
            if line.startswith("## ") and line.strip() != "## References"
        )
        assert heading_count == 4

    def test_references_heading_not_counted(self) -> None:
        """Article with 4 body headings + ## References stays unchanged."""
        article = (
            "---\ntitle: Test\n---\n\n"
            "## Introduction\n\nText.\n\n"
            "## Analysis\n\nText.\n\n"
            "## Results\n\nText.\n\n"
            "## Outlook\n\nText.\n\n"
            "## References\n\n1. Source A\n"
        )
        result = _enforce_heading_limit(article)
        # All 4 body headings + References should remain
        all_headings = [line for line in result.split("\n") if line.startswith("## ")]
        assert len(all_headings) == 5
        body_headings = [h for h in all_headings if h.strip() != "## References"]
        assert len(body_headings) == 4


class TestDescriptionTruncation:
    """Description field truncation to 160 chars."""

    def test_long_description_truncated(self) -> None:
        desc = "A" * 200
        article = f'---\ndescription: "{desc}"\n---\nBody'
        result = _apply_editorial_fixes(article)
        # Extract description from result
        import re

        match = re.search(r'description:\s*"([^"]+)"', result)
        assert match is not None
        assert len(match.group(1)) <= 160
        assert match.group(1).endswith("...")

    def test_short_description_unchanged(self) -> None:
        article = '---\ndescription: "A short description."\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "A short description." in result

    def test_exactly_160_unchanged(self) -> None:
        desc = "A" * 160
        article = f'---\ndescription: "{desc}"\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert desc in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ---------------------------------------------------------------------------
# BUG-055: never emit `image: ""` — Liquid treats an empty string as TRUTHY
# ---------------------------------------------------------------------------


class TestEmptyImageFrontmatterNeverEmitted:
    """An empty ``image: ""`` breaks the blog's REQUIRED ``build`` check.

    ``_layouts/post.html`` guards the hero with ``{% if page.image %}``, but in
    Liquid only ``nil``/``false`` are falsy — an empty string passes the guard,
    so ``responsive-image.html`` renders an ``<img>`` with no usable ``src`` and
    html-proofer fails: "image has no src or srcset attribute". Our own
    validator treats absent and empty identically (chart-only mode), so the key
    must simply be OMITTED when there is no hero.
    """

    def test_chart_only_article_omits_image_key(self) -> None:
        article = (
            "---\n"
            "layout: post\n"
            'title: "A Specific Descriptive Title"\n'
            "---\n\n"
            "Body paragraph with enough text to look like prose.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-24")
        assert 'image: ""' not in out, (
            'empty image: breaks the blog build (Liquid treats "" as truthy)'
        )
        assert "image: ''" not in out

    def test_existing_real_image_is_preserved(self) -> None:
        article = (
            "---\n"
            "layout: post\n"
            'title: "A Specific Descriptive Title"\n'
            "image: /assets/images/real-hero.png\n"
            "---\n\n"
            "Body paragraph.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-24")
        assert "/assets/images/real-hero.png" in out


# ---------------------------------------------------------------------------
# BUG-057: the blog requires >=2 lowercase-hyphen tags in inline bracket format
# ---------------------------------------------------------------------------


class TestTagsAlwaysEmitted:
    """``oviney/blog``'s ``scripts/validate-posts.sh`` requires a ``tags`` field
    with **>= 2** tags, inline bracket format, **all lowercase-hyphen**. The
    pipeline never emitted one, so the first real article published failed the
    blog's ``validate-editorial`` gate. Derive tags from ``categories`` so every
    article satisfies the contract by construction.
    """

    def test_tags_derived_from_categories(self) -> None:
        article = (
            "---\nlayout: post\n"
            'title: "A Specific Descriptive Title"\n'
            "categories: [Quality Engineering, Test Automation]\n"
            "---\n\nBody.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-25")
        assert "tags: [quality-engineering, test-automation]" in out

    def test_tags_are_lowercase_hyphen_only(self) -> None:
        article = (
            "---\nlayout: post\n"
            'title: "A Specific Descriptive Title"\n'
            'categories: ["Software Engineering", "Security"]\n'
            "---\n\nBody.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-25")
        tags_line = next(ln for ln in out.split("\n") if ln.startswith("tags:"))
        value = tags_line.split(":", 1)[1].strip().strip("[]")
        assert value == value.lower(), f"tags must be lowercase: {tags_line}"
        assert not any(c.isupper() for c in value)
        assert len([t for t in value.split(",") if t.strip()]) >= 2

    def test_at_least_two_tags_even_from_one_category(self) -> None:
        article = (
            "---\nlayout: post\n"
            'title: "A Specific Descriptive Title"\n'
            'categories: ["Quality Engineering"]\n'
            "---\n\nBody.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-25")
        tags_line = next(ln for ln in out.split("\n") if ln.startswith("tags:"))
        value = tags_line.split(":", 1)[1].strip().strip("[]")
        count = len([t for t in value.split(",") if t.strip()])
        assert count >= 2, f"blog requires >=2 tags, got {count}: {tags_line}"

    def test_existing_tags_preserved(self) -> None:
        article = (
            "---\nlayout: post\n"
            'title: "A Specific Descriptive Title"\n'
            'categories: ["Quality Engineering"]\n'
            "tags: [flaky-tests, continuous-integration]\n"
            "---\n\nBody.\n"
        )
        out = _apply_editorial_fixes(article, current_date="2026-07-25")
        assert "tags: [flaky-tests, continuous-integration]" in out
        assert out.count("tags:") == 1
