#!/usr/bin/env python3
"""Regression for BUG-044 (B-006 Checkpoint B run 4): Stage 3 must regenerate the
writer draft a bounded number of times when it emits malformed output, rather
than aborting the run on a single bad (non-deterministic) draft."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.stage3_runner import MalformedArticleError, run_stage3

_GOOD = (
    "---\nlayout: post\ntitle: t\n"
    "image: /assets/images/test-slug.png\n---\n\n"
    "Body paragraph. As the chart shows, things happen.\n"
)
_CHART = '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'
_EMPTY_BODY = "---\nlayout: post\ntitle: t\n---\n\n"  # frontmatter, no body
_FENCE_ONLY = "```\n"  # code fence that dedup would reduce to nothing


def _wire(monkeypatch, writer_outputs: list[str]) -> None:
    """Feed the writer bad drafts then a good one, then the chart JSON."""
    calls = iter([(o, 0.01) for o in writer_outputs] + [(_CHART, 0.01)])

    async def fake_collect(*args, **kwargs):
        return next(calls)

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")
    monkeypatch.setattr(s3, "build_research_brief", lambda topic: "# Brief")


def test_retries_past_malformed_drafts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    # First two drafts are malformed (empty body, then bare fence); third is good.
    _wire(monkeypatch, [_EMPTY_BODY, _FENCE_ONLY, _GOOD])

    result = asyncio.run(run_stage3("topic"))

    assert result.article.startswith("---")
    assert "things happen" in result.article


def test_raises_after_exhausting_attempts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    # All attempts malformed → raise after _WRITER_MAX_ATTEMPTS.
    _wire(monkeypatch, [_EMPTY_BODY] * s3._WRITER_MAX_ATTEMPTS)

    with pytest.raises(MalformedArticleError, match="after 3 attempts"):
        asyncio.run(run_stage3("topic"))


def test_good_first_draft_does_not_retry(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _wire(monkeypatch, [_GOOD])  # exactly one writer draft available

    result = asyncio.run(run_stage3("topic"))
    assert "things happen" in result.article
