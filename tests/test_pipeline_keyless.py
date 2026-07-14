#!/usr/bin/env python3
"""Keyless pipeline wiring + Checkpoint A (B-006).

Proves research_mode="claude_web" routes Stage 3 to the keyless claude_web
researcher (not the Serper-backed deterministic brief), and that a chart_only
run with ALL paid keys unset reaches Stage 4 and passes the publication
validator — without constructing any anthropic client or reading SERPER_API_KEY.

The Agent SDK is never invoked live: the writer/graphics collect calls and the
claude_web brief are mocked, so the test stays offline and free.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

import src.agent_sdk.pipeline as pipe
import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.pipeline import _slug_from_article, run_pipeline
from src.agent_sdk.stage3_runner import run_stage3

# Minimal draft for the routing tests (mocked at the run_stage3 seam, so it
# never reaches the validator).
_ARTICLE = (
    "---\nlayout: post\ntitle: x\n---\n\n"
    "Body paragraph. As the chart shows, things happen.\n"
)
_CHART_JSON = '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'

# A realistic draft mirroring real Stage 3 output: valid multi-word title, an
# ``image:`` slug (Stage 4 derives the chart path from it), ≥700 words, ≤4
# headings, no inline chart embed (the writer relies on _auto_embed_chart), and
# a References section with ≥3 entries. Checkpoint A runs the REAL Stage 4 +
# validator over this.
_PARA = (
    "The rise of automated quality engineering has reshaped how software teams "
    "measure progress across the release cycle. Most organisations now treat "
    "release confidence as a first-class signal rather than an afterthought, and "
    "that shift has changed both cost structures and daily culture. Teams that "
    "once leaned on manual regression passes have moved toward continuous "
    "verification, folding checks into every merge request they open. Managers "
    "say the hardest part is not the tooling but the discipline of acting on what "
    "the data reveals, since a dashboard nobody reads changes nothing at all. "
    "Engineers describe a quieter confidence: fewer late nights chasing "
    "regressions and more time spent on design and architecture work. The "
    "transition is uneven, and smaller teams often struggle to justify the "
    "upfront investment, yet the direction of travel is clear enough that few "
    "practitioners expect a reversal any time soon in this decade. "
)


def _section(title: str) -> str:
    return f"## {title}\n\n{_PARA}\n\n{_PARA}"


_FULL_ARTICLE = (
    "---\nlayout: post\n"
    'title: "The Quiet Reinvention of Software Quality"\n'
    "image: /assets/images/quiet-reinvention.png\n"
    "---\n\n"
    + _section("The shift to continuous verification")
    + "\n\n"
    + _section("What the numbers reveal")
    + "\n\n"
    "As the chart shows, automated practice adoption now outpaces manual work.\n\n"
    + _section("Where this leaves teams")
    + "\n\n## References\n\n"
    "1. State of Testing Report, PractiTest, 2026, https://practitest.com/state-of-testing/\n"
    "2. World Quality Report, Capgemini, 2025, https://capgemini.com/wqr/\n"
    "3. DevOps Trends, Gartner, 2025, https://gartner.com/devops/\n"
)
_FULL_CHART_JSON = (
    '{"title": "Adoption of automated quality practices", "data": ['
    '{"metric": "Automated", "value": 62, "color": "navy"}, '
    '{"metric": "Manual only", "value": 13, "color": "grey"}]}'
)


def _wire_writer_full(monkeypatch) -> None:
    call_results = iter([(_FULL_ARTICLE, 0.04), (_FULL_CHART_JSON, 0.01)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")


def _wire_writer(monkeypatch) -> None:
    call_results = iter([(_ARTICLE, 0.04), (_CHART_JSON, 0.01)])

    async def fake_collect(*args, **kwargs):
        return next(call_results)

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")


def _unset_all_keys(monkeypatch) -> None:
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_claude_web_mode_routes_to_keyless_researcher(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _unset_all_keys(monkeypatch)
    _wire_writer(monkeypatch)

    det = Mock(return_value="# Brief\n\nseed source")
    deep = AsyncMock(return_value=("# Deep brief", 0.5))
    web = AsyncMock(return_value=("# Research Brief: topic\n\nsourced claim", 0.2))
    monkeypatch.setattr(s3, "build_research_brief", det)
    monkeypatch.setattr(s3, "build_deep_research_brief", deep)
    monkeypatch.setattr(s3, "build_claude_web_brief", web)

    result = asyncio.run(run_stage3("topic", research_mode="claude_web"))

    web.assert_awaited_once_with("topic")
    det.assert_not_called()  # Serper path never touched
    deep.assert_not_called()
    assert result.research_cost_usd == 0.2


def test_env_var_selects_claude_web(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RESEARCH_MODE", "claude_web")
    _unset_all_keys(monkeypatch)
    _wire_writer(monkeypatch)

    det = Mock(return_value="# Brief")
    web = AsyncMock(return_value=("# Research Brief: topic", 0.1))
    monkeypatch.setattr(s3, "build_research_brief", det)
    monkeypatch.setattr(s3, "build_claude_web_brief", web)

    # argument says deterministic, but RESEARCH_MODE=claude_web wins
    result = asyncio.run(run_stage3("topic", research_mode="deterministic"))

    web.assert_awaited_once()
    det.assert_not_called()
    assert result.research_cost_usd == 0.1


def test_checkpoint_a_keyless_chart_only_passes_validator(
    tmp_path: Path, monkeypatch
) -> None:
    """CHECKPOINT A: run_pipeline(chart_only, claude_web) with every paid key
    unset produces a validator-passing article and touches no Serper/anthropic."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _unset_all_keys(monkeypatch)
    _wire_writer_full(monkeypatch)

    web = AsyncMock(return_value=("# Research Brief: topic\n\nsourced claim", 0.2))
    monkeypatch.setattr(s3, "build_claude_web_brief", web)

    # Guard: the deterministic Serper brief must never be constructed on this path.
    def _boom(*_a, **_k):  # pragma: no cover - only fires on regression
        raise AssertionError("Serper build_research_brief called on keyless path")

    monkeypatch.setattr(s3, "build_research_brief", _boom)

    result = asyncio.run(
        run_pipeline(
            "topic",
            image_mode="chart_only",
            research_mode="claude_web",
        )
    )

    web.assert_awaited_once()
    assert result.publication_validator_passed is True
    assert result.publication_validator_issues == []


def test_slug_from_article_uses_title() -> None:
    art = '---\nlayout: post\ntitle: "The Quiet Reinvention of QA"\n---\n\nBody.\n'
    assert _slug_from_article(art, "fallback topic") == "the-quiet-reinvention-of-qa"


def test_slug_from_article_falls_back_to_topic() -> None:
    assert _slug_from_article("no frontmatter here", "My Topic!") == "my-topic"


def test_end_to_end_cli_writes_article_and_exits_zero(
    tmp_path: Path, monkeypatch
) -> None:
    """The chart_only end-to-end CLI path writes the article and exits 0 when the
    validator passes, using run_pipeline with the selected research mode."""
    monkeypatch.chdir(tmp_path)
    _unset_all_keys(monkeypatch)

    from src.agent_sdk.pipeline import PipelineResult

    async def fake_run_pipeline(topic, **kwargs):
        assert kwargs["image_mode"] == "chart_only"
        assert kwargs["research_mode"] == "claude_web"
        return PipelineResult(
            topic=topic,
            article='---\nlayout: post\ntitle: "A Good Title"\n---\n\nBody.\n',
            chart_data={},
            editorial_score=1.0,
            gates_passed=True,
            publication_ready=True,
            publication_validator_passed=True,
            publication_validator_issues=[],
            total_cost_usd=0.1,
            writer_cost_usd=0.05,
            graphics_cost_usd=0.02,
            research_cost_usd=0.03,
            writer_model="w",
            graphics_model="g",
            stage3_seconds=0.1,
            stage4_seconds=0.1,
            article_chars=42,
        )

    monkeypatch.setattr(pipe, "run_pipeline", fake_run_pipeline)

    with pytest.raises(SystemExit) as exc:
        pipe._run_end_to_end(
            "topic",
            writer_budget=0.3,
            graphics_budget=0.1,
            writer_model="w",
            graphics_model="g",
            research_mode="claude_web",
        )
    assert exc.value.code == 0
    written = (tmp_path / "output" / "posts" / "a-good-title.md").read_text()
    assert "A Good Title" in written
