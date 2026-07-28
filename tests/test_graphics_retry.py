#!/usr/bin/env python3
"""BUG-063: the graphics agent must retry a malformed chart spec.

Chart render failures are fatal by design (a missing chart leaves a broken body
embed), and the graphics call had **no retry** — so one bad JSON response killed
the pipeline *after* the writer had already succeeded and cost ~$0.85.

The writer gets ``_WRITER_MAX_ATTEMPTS`` for exactly the same class of problem.
Found by the B-020 acceptance run: ``ChartRenderError: spec.data is required and
must be a non-empty list``.
"""

from __future__ import annotations

import asyncio

import pytest

from src.agent_sdk import stage3_runner
from src.agent_sdk.chart_renderer import ChartRenderError

_GOOD_SPEC = (
    '{"title": "Review queue cost", "data": ['
    '{"metric": "Waiting", "value": 62, "unit": "%"},'
    '{"metric": "Reviewing", "value": 21, "unit": "%"}]}'
)
_EMPTY_SPEC = '{"title": "Review queue cost", "data": []}'


class _Graphics:
    """Returns queued graphics replies and records the prompts it saw."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def __call__(self, prompt: str, *a: object, **k: object) -> tuple[str, float]:
        self.prompts.append(prompt)
        return (self.replies.pop(0) if self.replies else ""), 0.0


def test_a_malformed_spec_is_retried_with_the_error_fed_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    graphics = _Graphics([_EMPTY_SPEC, _GOOD_SPEC])
    rendered: list[dict] = []

    def fake_render(spec, path):  # type: ignore[no-untyped-def]
        if not spec.get("data"):
            raise ChartRenderError("spec.data is required and must be a non-empty list")
        rendered.append(spec)
        return path

    monkeypatch.setattr(stage3_runner, "render_chart", fake_render)

    # Async: run_stage3 is already in an event loop, and a sync helper there
    # would repeat the asyncio.run-inside-a-loop bug this codebase just fixed.
    data, cost, attempts = asyncio.run(
        stage3_runner._graphics_with_retry(
            graphics, "prompt", "model", None, "article", "topic", tmp_path / "c.png"
        )
    )
    assert rendered, "a retry should have produced a renderable spec"
    assert attempts == 2
    # The retry must say what was wrong, or the agent repeats itself.
    assert "spec.data is required" in graphics.prompts[1]


def test_the_first_good_spec_short_circuits(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    graphics = _Graphics([_GOOD_SPEC, _GOOD_SPEC])
    monkeypatch.setattr(stage3_runner, "render_chart", lambda spec, path: path)
    _, _, attempts = asyncio.run(
        stage3_runner._graphics_with_retry(
            graphics, "prompt", "model", None, "article", "topic", tmp_path / "c.png"
        )
    )
    assert attempts == 1


def test_exhausting_attempts_still_raises_so_the_chart_is_never_silently_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    graphics = _Graphics([_EMPTY_SPEC] * 6)

    def always_fail(spec, path):  # type: ignore[no-untyped-def]
        raise ChartRenderError("spec.data is required and must be a non-empty list")

    monkeypatch.setattr(stage3_runner, "render_chart", always_fail)
    with pytest.raises(ChartRenderError):
        asyncio.run(
            stage3_runner._graphics_with_retry(
                graphics,
                "prompt",
                "model",
                None,
                "article",
                "topic",
                tmp_path / "c.png",
            )
        )
    assert len(graphics.prompts) == stage3_runner._GRAPHICS_MAX_ATTEMPTS
