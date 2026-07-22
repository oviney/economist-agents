#!/usr/bin/env python3
"""Regression for BUG-049 (surfaced by B-010 T1 validation run).

_optimize_search_terms substring-replaced mapping keys, so 'AI' fired inside
'drain' -> 'dr artificial intelligence OR machine learning n', producing junk
arXiv queries. Replacement must be word-boundary-aware.
"""

from __future__ import annotations

from scripts.arxiv_search import ArxivSearcher


def _opt(query: str) -> str:
    return ArxivSearcher(max_results=3, days_back=60)._optimize_search_terms(query)


def test_ai_is_not_expanded_inside_other_words() -> None:
    out = _opt("Why flaky tests quietly drain engineering budgets")
    # 'drain' must survive intact — no 'AI' expansion injected mid-word.
    assert "drain" in out
    assert "artificial intelligence" not in out


def test_ai_as_a_standalone_word_is_expanded() -> None:
    out = _opt("AI in testing")
    assert "artificial intelligence OR machine learning" in out


def test_roi_not_expanded_inside_words() -> None:
    # e.g. 'heroism' contains 'roi' as a substring.
    out = _opt("heroism in engineering")
    assert "heroism" in out
    assert "return on investment" not in out
