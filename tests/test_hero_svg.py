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

import subprocess
from pathlib import Path

import pytest

from src.agent_sdk import hero_svg
from src.agent_sdk.hero_svg import HeroSvgError, check_hero_svg, render_to_png


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

    def test_desc_written_as_a_drawing_brief_is_rejected(self) -> None:
        """The exact string that reddened ``oviney/blog``'s ``main`` five times.

        ``pipeline._hero_description`` harvests ``<desc>`` into the published
        ``image_alt``, and the blog's ``PROMPT_ALT_PATTERN`` rejects prompt
        language there. A brief that survives this gate becomes a red ``main``
        downstream, so it has to fail here instead.
        """
        svg = _svg().replace(
            "<desc>An engineer presses a green button while coins pour into a drain.</desc>",
            "<desc>An Economist-style editorial illustration of a quality inspector "
            "stamping approved on a crumbling tower of software containers.</desc>",
        )
        with pytest.raises(HeroSvgError, match="prompt"):
            check_hero_svg(svg)

    @pytest.mark.parametrize(
        "brief",
        [
            "A photorealistic server room at dusk.",
            "A duotone chart bleeding red ink across a ledger.",
            "A technical diagram of a pipeline with three broken stages.",
            "An infographic of rising costs beside a falling headcount.",
            "A cartoon auditor asleep at a desk of alarms.",
        ],
    )
    def test_every_prompt_term_the_blog_rejects_is_rejected_here(
        self, brief: str
    ) -> None:
        """Mirrors the blog's pattern term for term; divergence is the bug."""
        svg = _svg().replace(
            "<desc>An engineer presses a green button while coins pour into a drain.</desc>",
            f"<desc>{brief}</desc>",
        )
        with pytest.raises(HeroSvgError, match="prompt"):
            check_hero_svg(svg)

    def test_a_plain_description_of_the_drawing_still_passes(self) -> None:
        """The guard must not reject alt text that describes what was drawn."""
        svg = _svg().replace(
            "<desc>An engineer presses a green button while coins pour into a drain.</desc>",
            "<desc>A quality inspector stamps approved on a crumbling tower of "
            "software containers while engineering squads look on below.</desc>",
        )
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


class TestRenderToPng:
    """Rasterise so Claude and the operator can *look* — the structural gate
    cannot see composition, and constraint #4 requires looking at the render.

    No test spawns Chrome: BUG-058 is the cautionary case for tests that reach
    outside the process.
    """

    def test_invokes_chrome_headless_with_the_right_geometry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svg = tmp_path / "h.svg"
        svg.write_text(_svg())
        png = tmp_path / "h.png"
        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(argv)
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
            return subprocess.CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(hero_svg.subprocess, "run", fake_run)
        monkeypatch.setattr(
            hero_svg.shutil, "which", lambda _: "/usr/bin/google-chrome"
        )

        assert render_to_png(svg, png) == png
        argv = calls[0]
        assert "--headless" in argv
        assert any(a.startswith("--screenshot=") for a in argv)
        assert any("1600,900" in a for a in argv)
        assert argv[-1].startswith("file://")

    def test_missing_chrome_degrades_to_none_rather_than_raising(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A vision *malfunction* must never affect the pipeline (spec failure
        # policy, row 2). No Chrome means no critique, not a failed article.
        svg = tmp_path / "h.svg"
        svg.write_text(_svg())
        monkeypatch.setattr(hero_svg.shutil, "which", lambda _: None)
        # Since BUG-068 an empty PATH is no longer "no Chrome" — app-bundle
        # locations are searched too — so the bundle candidates must be cleared
        # as well or this passes only on machines without Chrome installed.
        monkeypatch.setattr(hero_svg, "_CHROME_APP_PATHS", ())
        assert render_to_png(svg, tmp_path / "h.png") is None

    def test_chrome_failure_degrades_to_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svg = tmp_path / "h.svg"
        svg.write_text(_svg())
        monkeypatch.setattr(
            hero_svg.shutil, "which", lambda _: "/usr/bin/google-chrome"
        )
        monkeypatch.setattr(
            hero_svg.subprocess,
            "run",
            lambda *a, **k: subprocess.CompletedProcess(
                a[0] if a else [], 1, "", "boom"
            ),
        )
        assert render_to_png(svg, tmp_path / "h.png") is None

    def test_timeout_degrades_to_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svg = tmp_path / "h.svg"
        svg.write_text(_svg())
        monkeypatch.setattr(
            hero_svg.shutil, "which", lambda _: "/usr/bin/google-chrome"
        )

        def raise_timeout(*a, **k):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd="chrome", timeout=30)

        monkeypatch.setattr(hero_svg.subprocess, "run", raise_timeout)
        assert render_to_png(svg, tmp_path / "h.png") is None

    def test_a_silent_no_output_run_degrades_to_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Chrome exits 0 but writes nothing — the failure mode that would
        # otherwise hand a nonexistent path to the vision step.
        svg = tmp_path / "h.svg"
        svg.write_text(_svg())
        monkeypatch.setattr(
            hero_svg.shutil, "which", lambda _: "/usr/bin/google-chrome"
        )
        monkeypatch.setattr(
            hero_svg.subprocess,
            "run",
            lambda *a, **k: subprocess.CompletedProcess([], 0, "", ""),
        )
        assert render_to_png(svg, tmp_path / "h.png") is None
