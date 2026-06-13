#!/usr/bin/env python3
"""Integration tests for the research_mode switch in Stage 3 (#390).

Verifies the deterministic default is unchanged and that research_mode="deep"
routes to build_deep_research_brief and records its cost. The writer/graphics
LLM calls, research, and style memory are all mocked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.stage3_runner import run_stage3

_ARTICLE = (
    "---\nlayout: post\ntitle: x\n"
    "image: /assets/images/test-slug.png\n---\n\n"
    "Body paragraph. As the chart shows, things happen.\n"
)
_CHART_JSON = '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'


def _wire_writer(monkeypatch) -> None:
    call_results = iter([(_ARTICLE, 0.04), (_CHART_JSON, 0.01)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")


def test_default_mode_uses_deterministic_research(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _wire_writer(monkeypatch)
    det = Mock(return_value="# Brief\n\nseed source")
    deep = AsyncMock(return_value=("# Deep brief", 0.5))
    monkeypatch.setattr(s3, "build_research_brief", det)
    monkeypatch.setattr(s3, "build_deep_research_brief", deep)

    result = asyncio.run(run_stage3("topic"))

    det.assert_called_once_with("topic")
    deep.assert_not_called()
    assert result.research_cost_usd == 0.0


def test_deep_mode_uses_deep_research_and_records_cost(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _wire_writer(monkeypatch)
    det = Mock(return_value="# Brief\n\nseed")
    deep = AsyncMock(return_value=("# Deep brief\n\nsourced passage", 0.5))
    monkeypatch.setattr(s3, "build_research_brief", det)
    monkeypatch.setattr(s3, "build_deep_research_brief", deep)

    result = asyncio.run(run_stage3("topic", research_mode="deep"))

    deep.assert_awaited_once_with("topic")
    det.assert_not_called()
    assert result.research_cost_usd == 0.5
    # research cost flows into the run total alongside writer + graphics
    assert result.total_cost_usd == pytest.approx(0.04 + 0.01 + 0.5)


def test_env_var_overrides_argument(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RESEARCH_MODE", "deep")
    _wire_writer(monkeypatch)
    det = Mock(return_value="# Brief")
    deep = AsyncMock(return_value=("# Deep brief", 0.3))
    monkeypatch.setattr(s3, "build_research_brief", det)
    monkeypatch.setattr(s3, "build_deep_research_brief", deep)

    # argument says deterministic, but RESEARCH_MODE=deep wins
    result = asyncio.run(run_stage3("topic", research_mode="deterministic"))

    deep.assert_awaited_once()
    det.assert_not_called()
    assert result.research_cost_usd == 0.3
