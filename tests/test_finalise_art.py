"""B-042 AC6: `make art` folds the owner's art in, and never overwrites it.

The one rule that matters here: a hand-made PNG wins. Silently replacing the
owner's own chart with a spec-rendered one would be the automation this item
exists to remove, reintroduced at the last possible step.

Spec: docs/specs/mandatory-chart-setpoint.md — S3, AC6.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.finalise_art import finalise

_ARTICLE = (
    '---\nlayout: post\ntitle: "My Slug"\n---\n\n'
    "Body paragraph one.\n\n## References\n\n1. A\n"
)

_VALID_SPEC = {
    "title": "The rework tax",
    "data": [
        {"metric": "No automation", "value": 40, "unit": "%"},
        {"metric": "Full pyramid", "value": 12, "unit": "%"},
    ],
}

_UNFRAMED_SPEC = {
    "title": "",
    "data": [{"metric": "", "value": 40, "unit": "%"}],
}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output" / "posts").mkdir(parents=True)
    (tmp_path / "output" / "charts").mkdir(parents=True)
    (tmp_path / "output" / "posts" / "my-slug.md").write_text(_ARTICLE)
    return tmp_path


def _write_spec(workspace: Path, spec: dict) -> None:
    (workspace / "output" / "charts" / "my-slug.spec.json").write_text(json.dumps(spec))


def _write_hero(workspace: Path) -> None:
    images = workspace / "output" / "posts" / "images"
    images.mkdir(parents=True, exist_ok=True)
    (images / "my-slug-hero.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><desc>A drawn scene</desc></svg>'
    )


class TestTheOwnersArtIsNeverOverwritten:
    def test_an_existing_png_is_left_alone(self, workspace: Path) -> None:
        """The rule that keeps the fully-manual route open."""
        png = workspace / "output" / "charts" / "my-slug.png"
        png.write_bytes(b"HAND-MADE")
        _write_spec(workspace, _VALID_SPEC)

        assert finalise("my-slug") == 0
        assert png.read_bytes() == b"HAND-MADE", "the owner's chart was overwritten"

    def test_the_spec_renders_when_no_png_exists(self, workspace: Path) -> None:
        _write_spec(workspace, _VALID_SPEC)
        assert finalise("my-slug") == 0
        assert (workspace / "output" / "charts" / "my-slug.png").is_file()


class TestTheEmbedFollowsTheChart:
    def test_an_embed_is_written_when_a_chart_exists(self, workspace: Path) -> None:
        _write_spec(workspace, _VALID_SPEC)
        finalise("my-slug")
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "![Chart](/assets/charts/my-slug.png)" in article
        assert article.index("![Chart]") < article.index("## References")

    def test_no_chart_means_no_embed(self, workspace: Path) -> None:
        """An embed is a claim that a figure exists. With no chart, no claim."""
        assert finalise("my-slug") == 0
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "![Chart]" not in article

    def test_an_unframed_spec_is_refused_and_leaves_no_embed(
        self, workspace: Path, capsys
    ) -> None:
        """The proposal's placeholders must not render into a titleless chart.

        This is the property that makes an untouched proposal safe to ship in
        the packet: if the owner never edits it, nothing is produced.
        """
        _write_spec(workspace, _UNFRAMED_SPEC)
        assert finalise("my-slug") == 0
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "![Chart]" not in article
        assert not (workspace / "output" / "charts" / "my-slug.png").exists()
        assert "still has the placeholders" in capsys.readouterr().err


class TestTheHeroIsLinked:
    def test_image_points_at_the_drawn_hero(self, workspace: Path) -> None:
        _write_hero(workspace)
        finalise("my-slug")
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "image: /assets/images/my-slug-hero.svg" in article

    def test_alt_text_comes_from_the_drawing(self, workspace: Path) -> None:
        """The SVG's <desc> describes what was drawn; the writer's alt was a brief."""
        _write_hero(workspace)
        finalise("my-slug")
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "A drawn scene" in article

    def test_a_missing_hero_leaves_image_absent_and_warns(
        self, workspace: Path, capsys
    ) -> None:
        """Absent is a clean deploy refusal; a broken path breaks the Jekyll build."""
        assert finalise("my-slug") == 0
        article = (workspace / "output" / "posts" / "my-slug.md").read_text()
        assert "image:" not in article
        assert "deploy will refuse" in capsys.readouterr().err


def test_a_missing_article_is_an_error(workspace: Path) -> None:
    assert finalise("no-such-slug") == 1
