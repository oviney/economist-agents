#!/usr/bin/env python3
"""Regression for BUG-043 + B-007: a chart spec missing a title must be
backfilled data-descriptively (subtitle, else a neutral label) — NEVER the
article headline — and must not crash the render."""

from __future__ import annotations

from src.agent_sdk.stage3_runner import _ensure_chart_title

_ART = '---\nlayout: post\ntitle: "The Cost of Flaky Tests"\n---\n\nBody.\n'


def test_missing_title_backfilled_from_subtitle() -> None:
    out = _ensure_chart_title(
        {"subtitle": "% change since 2022", "data": [{"metric": "a", "value": 1}]},
        _ART,
        "topic",
    )
    assert out["title"] == "% change since 2022"
    assert out["data"] == [{"metric": "a", "value": 1}]


def test_missing_title_and_subtitle_uses_neutral_label() -> None:
    out = _ensure_chart_title({"data": [{"metric": "a", "value": 1}]}, _ART, "topic")
    assert out["title"] == "Key figures"


def test_backfill_never_uses_the_article_headline() -> None:
    """The load-bearing B-007 assertion: the chart title must not be the
    article title, even when the graphics model omits a title/subtitle."""
    out = _ensure_chart_title({"data": []}, _ART, "The Cost of Flaky Tests")
    assert out["title"] != "The Cost of Flaky Tests"
    assert out["title"] != "topic"


def test_empty_title_backfilled() -> None:
    out = _ensure_chart_title({"title": "  ", "subtitle": "sub", "data": []}, _ART, "t")
    assert out["title"] == "sub"


def test_existing_title_preserved() -> None:
    out = _ensure_chart_title({"title": "Real Title", "data": []}, _ART, "topic")
    assert out["title"] == "Real Title"
