#!/usr/bin/env python3
"""Regression tests for chart-embed bugs surfaced by B-006 Checkpoint A.

BUG-039: apply_editorial_fixes stripped exclamation marks with a blind
``line.replace("!", ".")`` that also mangled the Markdown image token "![",
turning ``![alt](chart.png)`` into ``.[alt](chart.png)`` and breaking the embed.

BUG-040: run_pipeline chart_only stripped the ``image:`` slug before Stage 4,
so ``_auto_embed_chart`` could not derive the chart path and the required chart
was never embedded.
"""

from __future__ import annotations

from src.agent_sdk._shared import apply_editorial_fixes


def test_bug038_image_embed_survives_exclamation_strip() -> None:
    """A Markdown image embed must not be mangled by the exclamation strip."""
    article = (
        "---\nlayout: post\ntitle: t\n---\n\n"
        "A sentence with excitement! And more.\n\n"
        "![Chart caption](/assets/charts/x.png)\n\n"
        "Closing line.\n"
    )
    out = apply_editorial_fixes(article)

    # The image token is preserved verbatim...
    assert "![Chart caption](/assets/charts/x.png)" in out
    assert ".[Chart caption]" not in out
    # ...while a real exclamation mark in prose is still normalised away.
    assert "excitement!" not in out


def test_bug038_bang_before_bracket_only_is_preserved() -> None:
    """Only "![" is spared; a bang followed by other chars still becomes a dot."""
    out = apply_editorial_fixes("Wow! See ![alt](/assets/charts/y.png) now.\n")
    assert "Wow." in out
    assert "![alt](/assets/charts/y.png)" in out
