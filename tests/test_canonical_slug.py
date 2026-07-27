#!/usr/bin/env python3
"""B-008: one canonical slug across the article file, chart PNG, and image-prompt
sidecar. In chart_only runs the hero `image:` field is empty, and the chart slug
used to fall back to the *topic* while the article file and chart embed used the
*title* — so the embed could point at a PNG that doesn't exist.

B-019 extends the same function to satisfy the blog's URL slug policy
(``oviney/blog`` ``docs/URL_SLUG_POLICY.md``): target <=50 chars, complete words,
stop-words dropped, no double hyphens. Because there is exactly ONE derivation,
shortening inside it keeps the B-008 invariant by construction — every consumer
moves together.
"""

from __future__ import annotations

import re

from src.agent_sdk._shared import _auto_embed_chart, canonical_slug
from src.agent_sdk.pipeline import _slug_from_article
from src.agent_sdk.stage3_runner import _slug_for_chart

_CHART_ONLY_ARTICLE = (
    '---\ntitle: "The Real Title"\nimage: ""\n---\n\n## Body\n\nSome text.\n'
)

#: The title that shipped the first real article. Its naive slug was 76 chars —
#: 16 over the blog's hard cap — and had to be renamed by hand post-publish,
#: which 404s the original URL (there is no jekyll-redirect-from).
_REAL_LONG_TITLE = (
    "Green Light, Red Ledger: Flaky Tests Are Engineering's Costliest Invisible Tax"
)
_LONG_ARTICLE = f'---\ntitle: "{_REAL_LONG_TITLE}"\n---\n\n## Body\n\nText.\n'

#: The blog's hard cap is 60 and it warns from 55; the policy targets 50.
_POLICY_TARGET = 50


def test_chart_and_article_slug_agree_when_image_absent() -> None:
    # The chart PNG/sidecar slug and the article-file slug must be identical.
    # "The" is dropped as a stop word per the blog's slug policy (B-019).
    chart = _slug_for_chart(_CHART_ONLY_ARTICLE, "unrelated-topic")
    article = _slug_from_article(_CHART_ONLY_ARTICLE, "unrelated-topic")
    assert chart == article == "real-title"


def test_both_fall_back_to_the_same_slug_without_a_title() -> None:
    text = "no frontmatter at all"
    assert _slug_for_chart(text, "My Topic!") == _slug_from_article(text, "My Topic!")


class TestPolicyLength:
    """The blog rejects a filename slug over 60 chars, and there are no redirects."""

    def test_the_real_76_char_title_is_shortened_to_the_policy_target(self) -> None:
        slug = canonical_slug(_LONG_ARTICLE, "topic")
        assert len(slug) <= _POLICY_TARGET, f"{len(slug)} chars: {slug}"

    def test_a_short_title_is_left_alone(self) -> None:
        article = '---\ntitle: "Flaky Tests Cost Real Money"\n---\n'
        assert canonical_slug(article, "topic") == "flaky-tests-cost-real-money"

    def test_a_title_of_only_stop_words_still_yields_a_slug(self) -> None:
        article = '---\ntitle: "The And Of To"\n---\n'
        assert canonical_slug(article, "topic")


class TestPolicyShape:
    """Shortening must never produce the truncation the policy exists to prevent."""

    def test_never_cuts_mid_word(self) -> None:
        # Every word in the slug must be a whole word from the title.
        title_words = set(re.findall(r"[a-z0-9]+", _REAL_LONG_TITLE.lower()))
        slug_words = canonical_slug(_LONG_ARTICLE, "topic").split("-")
        assert set(slug_words) <= title_words, slug_words

    def test_possessive_does_not_leave_a_stray_letter(self) -> None:
        # "Engineering's" must not become "engineering-s-".
        slug = canonical_slug(_LONG_ARTICLE, "topic")
        assert "-s-" not in slug and not slug.endswith("-s")

    def test_no_double_hyphen(self) -> None:
        article = '---\ntitle: "Testing -- The Hard Way: Part 2"\n---\n'
        assert "--" not in canonical_slug(article, "topic")

    def test_no_leading_or_trailing_hyphen(self) -> None:
        article = '---\ntitle: "...Quality, Measured..."\n---\n'
        slug = canonical_slug(article, "topic")
        assert slug == slug.strip("-")


class TestExplicitSlugField:
    """The writer proposes a slug; the derivation is the guarantee (B-019)."""

    def test_a_valid_slug_field_wins_over_the_title(self) -> None:
        article = (
            f'---\ntitle: "{_REAL_LONG_TITLE}"\n'
            "slug: flaky-tests-invisible-tax\n---\n\nBody.\n"
        )
        assert canonical_slug(article, "topic") == "flaky-tests-invisible-tax"

    def test_an_over_long_slug_field_falls_back_to_the_derivation(self) -> None:
        bad = "a" * 61
        article = f'---\ntitle: "{_REAL_LONG_TITLE}"\nslug: {bad}\n---\n'
        slug = canonical_slug(article, "topic")
        assert slug != bad and len(slug) <= _POLICY_TARGET

    def test_a_malformed_slug_field_falls_back_to_the_derivation(self) -> None:
        # Uppercase, spaces, underscores, and double hyphens are all invalid.
        for bad in ("Not A Slug", "under_scored", "double--hyphen", "-leading"):
            article = f'---\ntitle: "{_REAL_LONG_TITLE}"\nslug: {bad}\n---\n'
            slug = canonical_slug(article, "topic")
            assert slug != bad, bad
            assert len(slug) <= _POLICY_TARGET


class TestInvariantHoldsUnderShortening:
    """B-008: shortening must move every consumer together, not just the filename."""

    def test_all_three_derivations_agree_on_a_long_title(self) -> None:
        assert (
            _slug_for_chart(_LONG_ARTICLE, "topic")
            == _slug_from_article(_LONG_ARTICLE, "topic")
            == canonical_slug(_LONG_ARTICLE, "topic")
        )

    def test_the_chart_embed_points_at_the_shortened_slug(self) -> None:
        # The in-body embed is the fourth consumer and is generated separately.
        embedded = _auto_embed_chart(_LONG_ARTICLE)
        slug = canonical_slug(_LONG_ARTICLE, "topic")
        assert f"/assets/charts/{slug}.png" in embedded

    def test_an_explicit_slug_field_moves_every_consumer(self) -> None:
        article = (
            f'---\ntitle: "{_REAL_LONG_TITLE}"\n'
            "slug: flaky-tests-invisible-tax\n---\n\nBody.\n"
        )
        assert (
            _slug_for_chart(article, "topic")
            == _slug_from_article(article, "topic")
            == "flaky-tests-invisible-tax"
        )
        assert "/assets/charts/flaky-tests-invisible-tax.png" in _auto_embed_chart(
            article
        )
