#!/usr/bin/env python3
"""B-016b slice 1: the deterministic structural gate for a generated hero SVG.

Spec: ``docs/specs/B-016b-automatic-hero-svg.md``.

Every threshold here is derived from the hero that actually shipped with the
first article (5.7 KB, 66 primitives, one ``<title>``, one ``<desc>``, zero
``<text>``, no external ``href``), not invented. The gate cannot judge
composition — that is the vision critique's job in a later slice — so it only
checks what a computer can check reliably.
"""

from __future__ import annotations

import pytest

from src.agent_sdk.hero_svg import HeroSvgError, check_hero_svg


def _svg(body: str = "", **attrs: str) -> str:
    """A minimal hero that passes every rule, with overrides for one-rule tests."""
    merged = {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": "1600",
        "height": "900",
        "viewBox": "0 0 1600 900",
    }
    merged.update(attrs)
    rendered = " ".join(f'{k}="{v}"' for k, v in merged.items() if v is not None)
    shapes = body or "\n".join(
        f'<rect x="{i * 10}" y="10" width="20" height="20" fill="#0f3a5f"/>'
        for i in range(14)
    )
    return (
        f"<svg {rendered}>"
        "<title>A green build drains the budget</title>"
        "<desc>An engineer presses a green button while coins pour into a drain.</desc>"
        f"{shapes}</svg>"
    )


class TestTheKnownGoodHeroPasses:
    """If the gate rejects the hero we actually shipped, the gate is wrong."""

    def test_the_shipped_hero_passes(self) -> None:
        from pathlib import Path

        shipped = next(Path("output/posts/images").glob("*-hero.svg"), None)
        if shipped is None:
            pytest.skip("no shipped hero available in this checkout")
        check_hero_svg(shipped.read_text())  # must not raise

    def test_the_synthetic_minimum_passes(self) -> None:
        check_hero_svg(_svg())


class TestParsesAsXml:
    def test_truncated_svg_is_rejected(self) -> None:
        # A truncated SVG renders as a blank image rather than failing loudly.
        with pytest.raises(HeroSvgError, match="not well-formed"):
            check_hero_svg('<svg xmlns="http://www.w3.org/2000/svg"><rect/>')

    def test_empty_string_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError):
            check_hero_svg("")

    def test_prose_wrapper_is_rejected(self) -> None:
        # The model likes to explain itself; the caller must strip that first.
        with pytest.raises(HeroSvgError):
            check_hero_svg("Here is your hero:\n<svg/>")


class TestRootElement:
    def test_non_svg_root_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="root element"):
            check_hero_svg("<html><body/></html>")

    def test_missing_viewbox_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="viewBox"):
            check_hero_svg(_svg(viewBox=None))  # type: ignore[arg-type]

    def test_malformed_viewbox_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="viewBox"):
            check_hero_svg(_svg(viewBox="not numbers"))


class TestAspectRatio:
    def test_sixteen_by_nine_passes(self) -> None:
        check_hero_svg(_svg(viewBox="0 0 1920 1080"))

    def test_square_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="aspect ratio"):
            check_hero_svg(_svg(viewBox="0 0 900 900"))

    def test_portrait_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="aspect ratio"):
            check_hero_svg(_svg(viewBox="0 0 900 1600"))

    def test_two_percent_off_is_tolerated(self) -> None:
        # 1600x891 is ~1.796 vs 1.778 — inside the 2% band.
        check_hero_svg(_svg(viewBox="0 0 1600 891"))

    def test_zero_height_is_rejected_not_a_zero_division(self) -> None:
        with pytest.raises(HeroSvgError):
            check_hero_svg(_svg(viewBox="0 0 1600 0"))


class TestAccessibilityElements:
    def test_missing_title_is_rejected(self) -> None:
        svg = _svg().replace("<title>A green build drains the budget</title>", "")
        with pytest.raises(HeroSvgError, match="title"):
            check_hero_svg(svg)

    def test_missing_desc_is_rejected(self) -> None:
        svg = _svg().replace(
            "<desc>An engineer presses a green button while coins pour into a drain.</desc>",
            "",
        )
        with pytest.raises(HeroSvgError, match="desc"):
            check_hero_svg(svg)

    def test_duplicate_title_is_rejected(self) -> None:
        svg = _svg().replace("<title>", "<title>x</title><title>", 1)
        with pytest.raises(HeroSvgError, match="title"):
            check_hero_svg(svg)

    def test_empty_title_is_rejected(self) -> None:
        svg = _svg().replace("A green build drains the budget", "   ")
        with pytest.raises(HeroSvgError, match="title"):
            check_hero_svg(svg)


class TestNoWordsInTheImage:
    """Constraint: no text, words, captions, or logos rendered in the artwork."""

    def test_text_element_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="text"):
            check_hero_svg(
                _svg(body='<text x="10" y="10">Flaky</text>' + "<rect/>" * 14)
            )

    def test_tspan_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="text"):
            check_hero_svg(_svg(body="<tspan>Flaky</tspan>" + "<rect/>" * 14))

    def test_title_and_desc_are_not_mistaken_for_rendered_text(self) -> None:
        # They are accessibility metadata, never painted. Required, not banned.
        check_hero_svg(_svg())


class TestSelfContained:
    def test_external_href_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="<image>|external"):
            check_hero_svg(
                _svg(body='<image href="https://example.com/a.png"/>' + "<rect/>" * 14)
            )

    def test_xlink_href_is_rejected(self) -> None:
        # A real SVG declares the prefix; an undeclared one is caught earlier as
        # malformed XML, which is also correct but tests a different rule.
        with pytest.raises(HeroSvgError, match="<image>|external"):
            check_hero_svg(
                _svg(
                    body='<image xlink:href="http://example.com/a.png"/>'
                    + "<rect/>" * 14,
                    **{"xmlns:xlink": "http://www.w3.org/1999/xlink"},
                )
            )

    def test_undeclared_namespace_prefix_is_rejected_as_malformed(self) -> None:
        with pytest.raises(HeroSvgError, match="not well-formed"):
            check_hero_svg(_svg(body='<image xlink:href="a.png"/>' + "<rect/>" * 14))

    def test_a_relative_image_path_is_rejected_too(self) -> None:
        # Not caught by URL filtering — <image> is banned outright.
        with pytest.raises(HeroSvgError, match="<image>"):
            check_hero_svg(_svg(body='<image href="a.png"/>' + "<rect/>" * 14))

    def test_internal_fragment_reference_is_allowed(self) -> None:
        # url(#gradient) and href="#id" are self-contained and idiomatic.
        body = (
            '<defs><linearGradient id="g"/></defs>'
            '<rect fill="url(#g)" width="10" height="10"/>' + "<rect/>" * 14
        )
        check_hero_svg(_svg(body=body))


class TestNoActiveContent:
    """This markup is served to readers by the blog."""

    def test_script_element_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="script"):
            check_hero_svg(_svg(body="<script/>" + "<rect/>" * 14))

    def test_event_handler_attribute_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="handler"):
            check_hero_svg(_svg(body='<rect onclick="alert(1)"/>' + "<rect/>" * 14))


class TestNotEmpty:
    def test_too_few_primitives_is_rejected(self) -> None:
        # Guards the near-blank output; the shipped hero has 66.
        with pytest.raises(HeroSvgError, match="primitive"):
            check_hero_svg(_svg(body='<rect width="10" height="10"/>'))

    def test_exactly_at_the_floor_passes(self) -> None:
        check_hero_svg(_svg(body='<rect width="9" height="9"/>' * 12))


class TestSizeCeiling:
    def test_oversized_source_is_rejected(self) -> None:
        with pytest.raises(HeroSvgError, match="bytes|size"):
            check_hero_svg(_svg(body='<path d="M0 0 ' + "L1 1 " * 30000 + '"/>'))


class TestErrorQuality:
    def test_the_message_names_the_failing_rule(self) -> None:
        with pytest.raises(HeroSvgError) as exc:
            check_hero_svg(_svg(viewBox="0 0 900 900"))
        # Actionable like ChartRenderError: says what is wrong and the numbers.
        assert "aspect ratio" in str(exc.value)
        assert "1.0" in str(exc.value) or "900" in str(exc.value)
