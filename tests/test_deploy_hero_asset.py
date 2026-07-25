#!/usr/bin/env python3
"""B-016: ship the Claude-authored hero illustration alongside the article.

The hero is authored as **SVG** (code-drawn, keyless — Claude has no raster image
model, and constraint #1 forbids a keyed image service). Two things follow:

* the hero must be copied from the frontmatter ``image:`` reference, not guessed
  from ``<slug>.png`` — an SVG hero was silently never copied, so the rendered
  post showed a broken ``<img>``;
* an ``.svg`` needs **no** ``.webp`` sibling. The blog's ``responsive-image.html``
  does ``replace: '.png', '.webp'``, so only a ``.png`` hero triggers the
  ``<source srcset>`` that html-proofer then demands.

Both ``deploy()`` (post path) and ``deploy_review()`` (B-013 path) must ship it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.deploy_to_blog as dtb

_BODY = " ".join(["word"] * 850)
_REFS = """## References

1. Gartner, ["World Quality Report"](https://example.com/a), 2024
2. Google, ["Flaky Tests"](https://example.com/b), 2023
3. METR, ["Productivity"](https://example.com/c), 2025
"""


def _article(image_line: str) -> str:
    return (
        "---\n"
        "layout: post\n"
        'title: "A Specific Descriptive Article Title"\n'
        "date: 2026-01-15\n"
        'author: "Ouray Viney"\n'
        'categories: ["Quality Engineering"]\n'
        f"{image_line}"
        'image_alt: "An engineer presses a green tick as coins drain away"\n'
        'image_caption: "Illustration: the green build that costs money"\n'
        'description: "A concise description for SEO purposes here"\n'
        "---\n\n"
        f"{_BODY}\n\n"
        "![Chart](output/charts/my-draft.png)\n\n"
        f"{_REFS}\n"
    )


# ── pure helper: which hero does the frontmatter point at? ────────────────


class TestHeroAssetRef:
    def test_extracts_svg_hero(self) -> None:
        art = _article("image: /assets/images/my-draft-hero.svg\n")
        assert dtb._hero_asset_ref(art) == "my-draft-hero.svg"

    def test_extracts_png_hero(self) -> None:
        art = _article("image: /assets/images/my-draft.png\n")
        assert dtb._hero_asset_ref(art) == "my-draft.png"

    def test_no_image_key_returns_none(self) -> None:
        assert dtb._hero_asset_ref(_article("")) is None

    def test_empty_image_returns_none(self) -> None:
        # BUG-055: an empty value is not a hero reference.
        assert dtb._hero_asset_ref(_article('image: ""\n')) is None


# ── copying, with the webp rule ──────────────────────────────────────────


class TestCopyHeroAsset:
    @pytest.fixture(autouse=True)
    def _cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output" / "posts" / "images").mkdir(parents=True)

    def test_svg_hero_copied_without_webp(self, tmp_path: Path) -> None:
        src = tmp_path / "output" / "posts" / "images" / "my-draft-hero.svg"
        src.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        dest = tmp_path / "blog" / "assets" / "images"
        dest.mkdir(parents=True)

        dtb._copy_hero_asset(
            _article("image: /assets/images/my-draft-hero.svg\n"), dest
        )

        assert (dest / "my-draft-hero.svg").exists()
        # An SVG must NOT get a .webp — responsive-image only swaps .png.
        assert not list(dest.glob("*.webp"))

    def test_missing_referenced_hero_raises(self, tmp_path: Path) -> None:
        dest = tmp_path / "blog" / "assets" / "images"
        dest.mkdir(parents=True)
        with pytest.raises(dtb.DeployError, match="Hero asset not found"):
            dtb._copy_hero_asset(
                _article("image: /assets/images/absent-hero.svg\n"), dest
            )

    def test_no_hero_reference_is_a_noop(self, tmp_path: Path) -> None:
        dest = tmp_path / "blog" / "assets" / "images"
        dest.mkdir(parents=True)
        dtb._copy_hero_asset(_article(""), dest)  # must not raise
        assert not list(dest.iterdir())


# ── deploy_review ships the hero (B-013 + B-016 together) ─────────────────


class TestReviewDeployShipsHero:
    def test_svg_hero_copied_and_staged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        article = tmp_path / "2026-01-15-my-draft.md"
        article.write_text(_article("image: /assets/images/my-draft-hero.svg\n"))
        charts = tmp_path / "output" / "charts"
        charts.mkdir(parents=True)
        (charts / "my-draft.png").write_bytes(b"PNG")
        images = tmp_path / "output" / "posts" / "images"
        images.mkdir(parents=True)
        (images / "my-draft-hero.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'/>"
        )

        commands: list[str] = []
        seen: dict[str, bool] = {}

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            blog = Path("temp_blog_repo")
            if cmd.startswith("git clone"):
                (blog / "_review").mkdir(parents=True, exist_ok=True)
                (blog / "assets" / "charts").mkdir(parents=True, exist_ok=True)
            if cmd.startswith("git add"):
                seen["hero"] = (
                    blog / "assets" / "images" / "my-draft-hero.svg"
                ).exists()
            return ""

        with patch.object(dtb, "run_command", side_effect=fake_run_command):
            dtb.deploy_review(
                article_path=article,
                blog_owner="o",
                blog_repo="r",
                token="t",
            )

        assert seen.get("hero"), "hero SVG was not copied into the blog clone"
        add = next(c for c in commands if c.startswith("git add") and c != "git add -u")
        assert "assets/images" in add, f"hero path not staged; got {add!r}"
