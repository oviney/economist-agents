"""BUG-072: a real PNG hero crashed `make art`.

``_hero_description`` reads the hero to pull alt text out of an SVG ``<desc>``.
It called ``path.read_text()`` unconditionally, so a genuine PNG — binary —
raised ``UnicodeDecodeError`` and took the whole ``make art`` step down.

``.png`` is a first-class hero format: ``_HERO_SUFFIXES`` lists it, and the
deploy step generates the ``.webp`` sibling a PNG hero needs. So this was not
an unsupported path, it was a supported one that had never been exercised.

Why the suite missed it, again: the PNG heroes in
``test_frontmatter_blog_contract.py`` are created with
``(images / "my-slug-hero.png").write_text("stub")`` — a *text file with a .png
name*. ``read_text()`` succeeds on those. Found on 2026-08-02 by putting a real
Gemini PNG on disk and running ``make art``.
"""

from __future__ import annotations

from pathlib import Path

from src.agent_sdk.pipeline import _hero_description, _link_hero_asset

#: The first eight bytes of any PNG. Enough to make the file genuinely binary.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02\x03" * 16

_ARTICLE = '---\nlayout: post\ntitle: "My Slug"\n---\n\nBody.\n'


class TestABinaryHeroDoesNotCrash:
    def test_a_real_png_yields_no_description(self, tmp_path: Path) -> None:
        hero = tmp_path / "my-slug-hero.png"
        hero.write_bytes(_PNG_MAGIC)

        assert _hero_description(hero) == ""

    def test_linking_a_real_png_hero_succeeds(self, tmp_path: Path) -> None:
        """The end-to-end property: `make art` must survive a PNG hero."""
        (tmp_path / "my-slug-hero.png").write_bytes(_PNG_MAGIC)

        out = _link_hero_asset(_ARTICLE, "my-slug", images_dir=tmp_path)

        assert "image: /assets/images/my-slug-hero.png" in out

    def test_an_svg_desc_is_still_read(self, tmp_path: Path) -> None:
        """Scope guard: the SVG path is the reason this function exists."""
        hero = tmp_path / "my-slug-hero.svg"
        hero.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><desc>Scissors cutting a '
            "ribbon</desc></svg>"
        )

        assert _hero_description(hero) == "Scissors cutting a ribbon"

    def test_a_missing_hero_yields_no_description(self, tmp_path: Path) -> None:
        assert _hero_description(tmp_path / "absent-hero.svg") == ""
