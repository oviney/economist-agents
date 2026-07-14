#!/usr/bin/env python3
"""Regression for BUG-040 (surfaced by B-006 Checkpoint B).

Some models wrap the whole article in a Markdown code fence despite the prompt.
Stage 3 must unwrap it before dedup/validation, otherwise _strip_duplicate_article
mistakes the real frontmatter for a duplicate and deletes the body.
"""

from __future__ import annotations

from src.agent_sdk.stage3_runner import (
    _strip_duplicate_article,
    _strip_enclosing_code_fence,
)

_ARTICLE = "---\nlayout: post\ntitle: t\n---\n\nReal body paragraph.\n"


def test_bare_fence_is_stripped() -> None:
    fenced = f"```\n{_ARTICLE}```\n"
    out = _strip_enclosing_code_fence(fenced)
    assert out.startswith("---")
    assert "Real body paragraph." in out


def test_language_tagged_fence_is_stripped() -> None:
    fenced = f"```markdown\n{_ARTICLE}```"
    out = _strip_enclosing_code_fence(fenced)
    assert out.startswith("---")
    assert "Real body paragraph." in out


def test_unfenced_article_is_untouched() -> None:
    assert _strip_enclosing_code_fence(_ARTICLE) == _ARTICLE


def test_fenced_article_survives_dedup_after_unfencing() -> None:
    """The end-to-end guard: a fenced article must keep its body once unwrapped,
    where previously dedup deleted everything after the opening fence."""
    fenced = f"```\n{_ARTICLE}```\n"
    result = _strip_duplicate_article(_strip_enclosing_code_fence(fenced))
    assert result.startswith("---")
    assert "Real body paragraph." in result
