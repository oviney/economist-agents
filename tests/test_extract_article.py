#!/usr/bin/env python3
"""Regression for BUG-047 (surfaced by B-009/B-010 T1 keyless run).

The writer sometimes prepends conversational preamble (and/or a stray ``---``
markdown rule) before the real frontmatter, failing the well-formed check and
forcing a budget-burning retry. ``_extract_article`` recovers the article
in-place so the first attempt succeeds instead of retrying.

Ports the recovery from the (closed) PR #441, reusing the existing
``_strip_enclosing_code_fence`` rather than a duplicate fence helper.
"""

from __future__ import annotations

from src.agent_sdk.stage3_runner import _extract_article

_ARTICLE = "---\nlayout: post\ntitle: t\n---\n\nReal body paragraph.\n"


def test_conversational_preamble_is_discarded() -> None:
    # The exact failure shape from the T1 diagnostic.
    noisy = (
        "The search tool is wired to arXiv, returning nothing relevant to "
        "software economics. I'll write the article grounded in known data.\n\n"
        f"{_ARTICLE}"
    )
    assert _extract_article(noisy) == _ARTICLE


def test_preamble_plus_fence_is_recovered() -> None:
    noisy = f"Here is the article you asked for:\n\n```yaml\n{_ARTICLE}```\n"
    out = _extract_article(noisy)
    assert out.startswith("---\nlayout: post")
    assert "Real body paragraph." in out
    assert "```" not in out


def test_clean_article_is_unchanged() -> None:
    assert _extract_article(_ARTICLE) == _ARTICLE


def test_prose_without_frontmatter_is_left_for_the_wellformed_check() -> None:
    # No frontmatter at all → returned (near) as-is so the caller still rejects it.
    prose = "Just some prose with no frontmatter and no article structure."
    assert not _extract_article(prose).startswith("---")
