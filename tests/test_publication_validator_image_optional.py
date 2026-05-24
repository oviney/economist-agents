"""Tests for #403 slice 2 (Task 2.1): image: optional + file-must-exist."""

from __future__ import annotations

from pathlib import Path

from scripts.publication_validator import PublicationValidator


def _article(extra_fm: str = "", body: str = "Body paragraph.\n") -> str:
    """Build a minimal valid article. ``extra_fm`` adds frontmatter lines."""
    return (
        "---\n"
        "layout: post\n"
        'title: "Test"\n'
        "date: 2026-05-24\n"
        "author: Ouray Viney\n"
        "categories:\n - Software Engineering\n"
        'description: "A description that is the right size for SEO."\n'
        f"{extra_fm}"
        "---\n\n"
        f"{body}"
    )


def _v() -> PublicationValidator:
    return PublicationValidator(expected_date="2026-05-24")


# ── chart-only mode (no image: line) — should NOT flag image-related issues ──


def test_no_image_line_does_not_emit_missing_image() -> None:
    v = _v()
    v._check_image_contract(_article())
    image_issues = [i for i in v.issues if "image" in i["check"]]
    assert image_issues == []


def test_no_image_line_does_not_require_image_alt_or_caption() -> None:
    v = _v()
    v._check_image_contract(_article())
    # Pre-#403 the contract required image_alt + image_caption even when
    # image: was missing; #403 makes the three a unit.
    assert not any(i["check"] == "missing_image_alt" for i in v.issues)
    assert not any(i["check"] == "missing_image_caption" for i in v.issues)


# ── image: present + file exists — passes ──


def test_image_present_with_file_on_disk_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "output" / "posts" / "images" / "x.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"fake png")

    v = _v()
    v._check_image_contract(
        _article(
            extra_fm=(
                "image: /assets/images/x.png\n"
                "image_alt: an editorial illustration\n"
                'image_caption: "A caption."\n'
            )
        )
    )
    assert not any(i["check"] == "missing_image_file" for i in v.issues)


# ── image: present + file missing — CRITICAL fail with path in message ──


def test_image_present_but_file_missing_emits_critical(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    v = _v()
    v._check_image_contract(
        _article(
            extra_fm=(
                "image: /assets/images/missing.png\n"
                "image_alt: alt\n"
                'image_caption: "cap"\n'
            )
        )
    )
    missing = [i for i in v.issues if i["check"] == "missing_image_file"]
    assert len(missing) == 1
    assert missing[0]["severity"] == "CRITICAL"
    assert "missing.png" in missing[0]["message"]
    # Operator-facing fix instructions name the exact drop path
    assert "output/posts/images/missing.png" in missing[0]["fix"]


# ── image: present requires alt + caption ──


def test_image_present_without_alt_still_flags_missing_alt(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output" / "posts" / "images").mkdir(parents=True)
    (tmp_path / "output" / "posts" / "images" / "x.png").write_bytes(b"x")

    v = _v()
    v._check_image_contract(
        _article(
            extra_fm=(
                'image: /assets/images/x.png\nimage_caption: "cap"\n'  # alt omitted
            )
        )
    )
    assert any(i["check"] == "missing_image_alt" for i in v.issues)


def test_image_present_without_caption_flags_missing_caption(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output" / "posts" / "images").mkdir(parents=True)
    (tmp_path / "output" / "posts" / "images" / "x.png").write_bytes(b"x")

    v = _v()
    v._check_image_contract(
        _article(
            extra_fm=(
                "image: /assets/images/x.png\nimage_alt: alt\n"  # caption omitted
            )
        )
    )
    assert any(i["check"] == "missing_image_caption" for i in v.issues)


# ── default fallback still rejected ──


def test_blog_default_svg_still_rejected() -> None:
    v = _v()
    v._check_image_contract(
        _article(
            extra_fm=(
                "image: /assets/images/blog-default.svg\n"
                "image_alt: alt\n"
                'image_caption: "cap"\n'
            )
        )
    )
    assert any(i["check"] == "default_image_fallback" for i in v.issues)


# ── path resolution helper ──


def test_resolve_image_path_maps_assets_images_to_output_posts_images() -> None:
    assert PublicationValidator._resolve_image_path("/assets/images/x.png") == Path(
        "output/posts/images/x.png"
    )


def test_resolve_image_path_returns_none_for_unexpected_prefix() -> None:
    # Absolute URLs or non-/assets/images/ paths should not be checked
    # (the validator's job is only to enforce the standard layout).
    assert PublicationValidator._resolve_image_path("https://cdn.x/img.png") is None
    assert PublicationValidator._resolve_image_path("/assets/charts/x.png") is None
