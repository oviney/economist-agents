#!/usr/bin/env python3
"""Tests for the keyless editorial hero + unified hero entrypoint (B-007)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

import src.agent_sdk.hero_image as hero


def test_editorial_hero_renders_expected_size(tmp_path: Path) -> None:
    out = hero.render_editorial_hero(
        "A Provocative Headline About Software Quality",
        "A sharp editorial dek that frames the argument.",
        tmp_path / "hero.png",
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1792, 1024)
        assert img.format == "PNG"


def test_editorial_hero_is_deterministic(tmp_path: Path) -> None:
    a = hero.render_editorial_hero("Same Title", "dek", tmp_path / "a.png")
    b = hero.render_editorial_hero("Same Title", "dek", tmp_path / "b.png")
    assert a.read_bytes() == b.read_bytes()


def test_different_titles_differ(tmp_path: Path) -> None:
    a = hero.render_editorial_hero("Title One", "dek", tmp_path / "a.png")
    b = hero.render_editorial_hero("Title Two", "dek", tmp_path / "b.png")
    assert a.read_bytes() != b.read_bytes()


def test_long_headline_still_renders(tmp_path: Path) -> None:
    long_title = "The " + "Very " * 30 + "Long Headline That Must Not Overflow"
    out = hero.render_editorial_hero(long_title, "dek", tmp_path / "long.png")
    with Image.open(out) as img:
        assert img.size == (1792, 1024)


def test_generate_hero_is_keyless(tmp_path: Path, monkeypatch) -> None:
    """generate_hero must draw a hero with NO API key of any kind (Operating
    Constraint #1/#4: no image-gen API, keyless-only)."""
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    out = hero.generate_hero(
        "Headline", "alt text describing the scene", "caption", tmp_path / "h.png"
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1792, 1024)
