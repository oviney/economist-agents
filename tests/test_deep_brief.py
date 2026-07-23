#!/usr/bin/env python3
"""B-012: opt-in deep-brief research mode — load a deep-research brief file for
the writer, EXCLUDING refuted claims (they must never reach the writer)."""

from __future__ import annotations

from src.agent_sdk.pipeline import load_brief_file

_BRIEF = """# Research brief — Does X?

## Verified claims

1. **A real, verified finding.**
   — [example.com](https://example.com) · verified 3-0

## Refuted / unverified — DO NOT USE without re-checking

- ✗ A discredited claim that must not reach the writer.
- ✗ Another walked-back number.

## Sources

- [example.com](https://example.com)
"""


def test_confirmed_claims_are_kept(tmp_path) -> None:
    p = tmp_path / "brief.md"
    p.write_text(_BRIEF)
    out = load_brief_file(p)
    assert "A real, verified finding" in out
    assert "example.com" in out  # sources retained


def test_refuted_claims_are_excluded(tmp_path) -> None:
    p = tmp_path / "brief.md"
    p.write_text(_BRIEF)
    out = load_brief_file(p)
    assert "discredited" not in out
    assert "walked-back" not in out
    assert "Refuted" not in out


def test_brief_without_refuted_section_is_returned_whole(tmp_path) -> None:
    p = tmp_path / "brief.md"
    p.write_text("# Brief\n\n## Verified claims\n\n1. Only good claims here.\n")
    out = load_brief_file(p)
    assert "Only good claims here" in out
