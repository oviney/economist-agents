"""Deterministic frame-edge measurement for hero renders — B-027.

Constraint #4 says "always look at the rendered result before shipping". During
the article-two review that looking produced a **false** defect report: a hero was
called clipped at the top on the strength of a glance at a thumbnail. A four-line
check of the rendered PNG's border rows disproved it — the top rows were pure
background. The wrong call cost a $0.49 redraw that fixed nothing.

The nine structural rules check viewBox presence, numerics, aspect ratio, element
counts and text bans. **None measures whether drawn content reaches the frame
edge.** Real clipping has happened: B-020 recorded a clipped queue stack and a
chart line running off the right edge.

The measurement is taken on the rendered PNG, not the SVG. A true SVG bounding box
needs transform composition and path-data parsing — hard, and prone to false
failures on valid heroes.

**The discriminator is coverage, not contact.** A naive "is there non-background
pixel on the border" test reports a false positive on every hero with a full-bleed
background or floor band, which is most of them — the shipped exemplar included.
An element spanning an entire edge is a deliberate full-bleed; one spanning a
*fraction* of an edge is a shape running out of frame. So the signal is a
partial-coverage run against the edge's own dominant colour.

Reports, never gates (B-016b's standing rule): composition findings inform the
reviewer and must not quarantine a publishable article.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.agent_sdk.hero_svg import report_edge_contact

_CREAM = (243, 239, 228)
_NAVY = (11, 43, 70)
_RED = (227, 18, 11)


def _png(tmp_path: Path, name: str, draw=None) -> Path:  # type: ignore[no-untyped-def]
    """Write a 400x225 (16:9) test image, optionally mutated by ``draw``."""
    im = Image.new("RGB", (400, 225), _CREAM)
    if draw is not None:
        draw(im)
    path = tmp_path / name
    im.save(path)
    return path


class TestEdgeContactControls:
    """Legitimate framing must stay silent, or the check is noise."""

    def test_uniform_background_reports_nothing(self, tmp_path: Path) -> None:
        """A flat canvas touches every edge by definition and is not a defect."""
        assert report_edge_contact(_png(tmp_path, "flat.png")) == []

    def test_full_bleed_floor_band_reports_nothing(self, tmp_path: Path) -> None:
        """THE control case a naive border check fails.

        The shipped hero has exactly this: a dark band spanning the full width at
        the bottom. Border pixels differ from the canvas background, so a contact
        test flags it — but it spans the entire edge, which is what full-bleed
        means.
        """

        def draw(im: Image.Image) -> None:
            for x in range(400):
                for y in range(195, 225):
                    im.putpixel((x, y), _NAVY)

        assert report_edge_contact(_png(tmp_path, "band.png", draw)) == []

    def test_inset_shape_reports_nothing(self, tmp_path: Path) -> None:
        """A shape comfortably inside the frame is the well-composed case."""

        def draw(im: Image.Image) -> None:
            for x in range(150, 250):
                for y in range(80, 140):
                    im.putpixel((x, y), _RED)

        assert report_edge_contact(_png(tmp_path, "inset.png", draw)) == []


class TestEdgeContactDetection:
    """A shape running out of frame must be reported."""

    def test_shape_crossing_the_top_edge_is_reported(self, tmp_path: Path) -> None:
        """The defect B-020 recorded for real: a card clipped by the top edge."""

        def draw(im: Image.Image) -> None:
            for x in range(120, 260):  # 35% of the width — a partial run
                for y in range(0, 60):
                    im.putpixel((x, y), _RED)

        findings = report_edge_contact(_png(tmp_path, "clipped-top.png", draw))

        assert len(findings) == 1
        assert "top" in findings[0].lower()

    def test_shape_crossing_the_right_edge_is_reported(self, tmp_path: Path) -> None:
        """B-020 also recorded a chart line running off the right edge."""

        def draw(im: Image.Image) -> None:
            for x in range(360, 400):
                for y in range(60, 150):  # 40% of the height
                    im.putpixel((x, y), _NAVY)

        findings = report_edge_contact(_png(tmp_path, "clipped-right.png", draw))

        assert len(findings) == 1
        assert "right" in findings[0].lower()

    def test_reports_each_offending_edge_separately(self, tmp_path: Path) -> None:
        """Two edges breached means two findings, so the reviewer knows where."""

        def draw(im: Image.Image) -> None:
            for x in range(120, 260):
                for y in range(0, 60):
                    im.putpixel((x, y), _RED)
            for x in range(0, 40):
                for y in range(60, 150):
                    im.putpixel((x, y), _NAVY)

        findings = report_edge_contact(_png(tmp_path, "clipped-two.png", draw))

        assert len(findings) == 2
        joined = " ".join(findings).lower()
        assert "top" in joined and "left" in joined


class TestEdgeContactIsAMeasurementNotAVerdict:
    """The limitation is pinned here so nobody "fixes" it by suppressing it."""

    def test_deliberate_bleed_off_is_also_reported(self, tmp_path: Path) -> None:
        """A desk running off one side reads identically to a clipped shape.

        This is the shipped hero's own geometry — a desk rect from x=0 stopping at
        x=680 — and it is correct composition, not a defect. It is still reported,
        because intent is not visible in pixels. The wording says so, and the
        judgement stays with a human.

        If someone later adds a heuristic to silence this case, this test fails and
        the docstring explains why that heuristic would be wrong.
        """

        def draw(im: Image.Image) -> None:
            for x in range(0, 240):  # from the left edge, stopping well short
                for y in range(170, 190):
                    im.putpixel((x, y), _NAVY)

        findings = report_edge_contact(_png(tmp_path, "desk.png", draw))

        assert len(findings) == 1
        assert "left" in findings[0].lower()
        # Phrased as an observation, never as a defect verdict.
        assert "clipped" not in findings[0].lower().split("accidental")[0]


class TestEdgeContactDegradation:
    """This is a reporter. It must never be the reason a run fails."""

    def test_missing_render_returns_empty_rather_than_raising(
        self, tmp_path: Path
    ) -> None:
        """No render means no measurement, not an error (B-016b failure policy)."""
        assert report_edge_contact(tmp_path / "never-written.png") == []

    def test_unreadable_file_returns_empty_rather_than_raising(
        self, tmp_path: Path
    ) -> None:
        """A corrupt PNG must not take the pipeline down."""
        bad = tmp_path / "corrupt.png"
        bad.write_bytes(b"not a png at all")

        assert report_edge_contact(bad) == []
