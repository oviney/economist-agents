#!/usr/bin/env python3
"""Tests for the Gemini hero tier (B-007). No network: the genai client is
faked; the key-gating and response-parsing paths are exercised directly."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import src.agent_sdk.gemini_image as gem


def test_returns_none_without_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert gem.generate_gemini_hero("a prompt", tmp_path / "x.png") is None


def _install_fake_genai(monkeypatch, image_bytes: bytes | None) -> dict:
    """Install a fake ``google.genai`` module that returns image_bytes."""
    calls: dict = {}

    class _Inline:
        def __init__(self, data):
            self.data = data

    class _Part:
        def __init__(self, data):
            self.inline_data = _Inline(data) if data is not None else None

    class _Content:
        def __init__(self, data):
            self.parts = [_Part(data)]

    class _Candidate:
        def __init__(self, data):
            self.content = _Content(data)

    class _Response:
        def __init__(self, data):
            self.candidates = [_Candidate(data)]

    class _Models:
        def generate_content(self, *, model, contents, config):
            calls["model"] = model
            calls["contents"] = contents
            return _Response(image_bytes)

    class _Client:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.models = _Models()

    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = _Client
    types_mod = types.ModuleType("google.genai.types")
    types_mod.GenerateContentConfig = lambda **kw: kw
    google_mod = types.ModuleType("google")
    google_mod.genai = genai_mod

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_mod)
    return calls


def test_writes_png_and_appends_style(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "free-studio-key")
    calls = _install_fake_genai(monkeypatch, b"PNGDATA")

    out = gem.generate_gemini_hero("a lonely server at dusk", tmp_path / "h.png")

    assert out is not None and out.read_bytes() == b"PNGDATA"
    assert calls["api_key"] == "free-studio-key"
    # House style is appended to the caller's brief.
    assert "Economist" in calls["contents"]


def test_returns_none_when_no_image_in_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    _install_fake_genai(monkeypatch, None)
    assert gem.generate_gemini_hero("prompt", tmp_path / "h.png") is None
