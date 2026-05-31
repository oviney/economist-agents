"""Tests for #403 slice 2 (Task 2.2): BUG-017 false-positive fix.

The old rule fired whenever an article had BOTH ``image:`` in frontmatter
AND ANY ``![...]​(*.png)`` markdown in the body — regardless of whether
the two paths point to the same file. Reproduced 2026-05-18 (issue #402):
hero in ``/assets/images/X.png`` + chart in ``/assets/charts/X.png`` was
flagged as duplicate even though they are two distinct files. Fix: only
flag when the paths actually resolve to the same file.
"""

from __future__ import annotations

from scripts.defect_prevention_rules import DefectPrevention


def _article(image: str, body_chart_path: str | None) -> str:
    """Build a minimal article with a frontmatter image and optional
    body chart embed."""
    fm = (
        f"---\nlayout: post\ntitle: x\ndate: 2026-05-24\nimage: {image}\n---\n\nBody.\n"
    )
    if body_chart_path is not None:
        fm += f"\n![Chart]({body_chart_path})\n"
    return fm


def _check(content: str) -> str:
    """Run only _check_duplicate_chart and return its message ('' = clean)."""
    return DefectPrevention()._check_duplicate_chart(content, {})


# ── true positives — rule SHOULD fire ────────────────────────────────


def test_fires_when_hero_and_chart_point_to_identical_path() -> None:
    msg = _check(_article("/assets/charts/x.png", "/assets/charts/x.png"))
    assert msg
    assert "Duplicate chart display" in msg
    assert "/assets/charts/x.png" in msg


def test_fires_when_paths_differ_only_in_double_slash() -> None:
    # Normalisation should treat /assets//charts/x.png and
    # /assets/charts/x.png as the same path.
    msg = _check(_article("/assets//charts/x.png", "/assets/charts/x.png"))
    assert msg


# ── false positives — rule MUST NOT fire (the #402 fix) ──────────────


def test_does_not_fire_when_hero_in_images_and_chart_in_charts() -> None:
    """The hero/chart layout that the writer prompt produces — different
    parent dirs sharing the same slug. These are two real files; not a
    duplicate. Reproduces #402."""
    msg = _check(
        _article(
            "/assets/images/product-team-composition.png",
            "/assets/charts/product-team-composition.png",
        )
    )
    assert msg == ""


def test_does_not_fire_when_paths_have_different_basenames() -> None:
    msg = _check(_article("/assets/images/x.png", "/assets/charts/y.png"))
    assert msg == ""


def test_does_not_fire_when_no_chart_embed_in_body() -> None:
    msg = _check(_article("/assets/images/x.png", None))
    assert msg == ""


def test_does_not_fire_when_no_image_field() -> None:
    body = (
        "---\nlayout: post\ntitle: x\ndate: 2026-05-24\n---\n\n"
        "Body.\n\n![Chart](/assets/charts/x.png)\n"
    )
    assert _check(body) == ""


def test_does_not_fire_on_article_without_frontmatter() -> None:
    assert _check("Plain markdown, no frontmatter.\n") == ""


# ── multiple chart embeds — fire if any matches the hero ─────────────


def test_fires_when_any_of_multiple_chart_embeds_matches_hero() -> None:
    body = (
        "---\nlayout: post\ntitle: x\n"
        "image: /assets/charts/x.png\n---\n\n"
        "First chart: ![a](/assets/charts/other.png)\n"
        "Second chart: ![b](/assets/charts/x.png)\n"
    )
    msg = _check(body)
    assert msg
