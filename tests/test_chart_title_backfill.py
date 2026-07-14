#!/usr/bin/env python3
"""Regression for BUG-042 (B-006 Checkpoint B run 3): a chart spec missing a
title must be backfilled from the article/topic, not crash the render."""

from __future__ import annotations

from src.agent_sdk.stage3_runner import _ensure_chart_title

_ART = '---\nlayout: post\ntitle: "The Cost of Flaky Tests"\n---\n\nBody.\n'


def test_missing_title_backfilled_from_article() -> None:
    out = _ensure_chart_title({"data": [{"metric": "a", "value": 1}]}, _ART, "topic")
    assert out["title"] == "The Cost of Flaky Tests"
    assert out["data"] == [{"metric": "a", "value": 1}]


def test_empty_title_backfilled() -> None:
    out = _ensure_chart_title({"title": "  ", "data": []}, _ART, "topic")
    assert out["title"] == "The Cost of Flaky Tests"


def test_falls_back_to_topic_without_frontmatter() -> None:
    assert _ensure_chart_title({}, "no frontmatter", "My Topic")["title"] == "My Topic"


def test_existing_title_preserved() -> None:
    out = _ensure_chart_title({"title": "Real Title", "data": []}, _ART, "topic")
    assert out["title"] == "Real Title"
