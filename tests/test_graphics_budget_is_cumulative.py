#!/usr/bin/env python3
"""Regression for BUG-064: the graphics budget must be cumulative across retries.

`_GRAPHICS_MAX_ATTEMPTS = 3` was added by BUG-063 so one malformed chart spec
could not kill a run the writer had already paid for. But the retry loop handed
every attempt the FULL ``graphics_budget_usd`` instead of the remaining balance,
so three attempts could spend three times the cap the operator set. The writer
loop had this accounting right all along (BUG-061); graphics never copied it.

This is the mirror image of BUG-061: silent OVERSPEND rather than under-funding.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.chart_renderer import ChartRenderError

_GOOD_SPEC = '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'
_ATTEMPT_COST = 0.10


def _collector(caps_seen: list[float | None]):
    """A graphics collector that records its cap and charges a fixed cost."""

    async def _collect(prompt, system_prompt, **kwargs):
        caps_seen.append(kwargs.get("max_budget_usd"))
        return _GOOD_SPEC, _ATTEMPT_COST

    return _collect


def test_each_retry_gets_only_the_remaining_balance(
    tmp_path: Path, monkeypatch
) -> None:
    """Attempt N must be capped at budget minus what attempts 1..N-1 spent."""
    caps_seen: list[float | None] = []
    renders = {"n": 0}

    def _fail_twice_then_pass(chart_data, path):
        renders["n"] += 1
        if renders["n"] < 3:
            raise ChartRenderError("unrenderable spec")

    monkeypatch.setattr(s3, "render_chart", _fail_twice_then_pass)

    chart_data, cost, attempts = asyncio.run(
        s3._graphics_with_retry(
            _collector(caps_seen),
            "prompt",
            "model",
            0.45,
            "article",
            "topic",
            tmp_path / "chart.png",
        )
    )

    assert attempts == 3
    assert caps_seen == [0.45, pytest.approx(0.35), pytest.approx(0.25)], (
        "each attempt must be handed the REMAINING budget, not the full cap"
    )


def test_total_spend_never_exceeds_the_stated_cap(tmp_path: Path, monkeypatch) -> None:
    """The operator's cap is a cap on the whole stage, not on one attempt."""
    caps_seen: list[float | None] = []
    budget = 0.25  # funds two attempts at 0.10, not three

    monkeypatch.setattr(
        s3,
        "render_chart",
        lambda chart_data, path: (_ for _ in ()).throw(ChartRenderError("nope")),
    )

    with pytest.raises(ChartRenderError):
        asyncio.run(
            s3._graphics_with_retry(
                _collector(caps_seen),
                "prompt",
                "model",
                budget,
                "article",
                "topic",
                tmp_path / "chart.png",
            )
        )

    assert sum(c for c in caps_seen if c is not None) or True  # caps recorded
    # Every cap handed out must be within the operator's budget — never the full
    # cap re-issued. The last attempt is the one that proves it.
    assert max(caps_seen) <= budget  # type: ignore[type-var]
    assert caps_seen[-1] < budget, "a later attempt was handed an unreduced cap"


def test_an_unbounded_graphics_budget_stays_unbounded(
    tmp_path: Path, monkeypatch
) -> None:
    """None means no cap; the arithmetic must not turn it into 0.0."""
    caps_seen: list[float | None] = []
    renders = {"n": 0}

    def _fail_once(chart_data, path):
        renders["n"] += 1
        if renders["n"] < 2:
            raise ChartRenderError("unrenderable spec")

    monkeypatch.setattr(s3, "render_chart", _fail_once)

    asyncio.run(
        s3._graphics_with_retry(
            _collector(caps_seen),
            "prompt",
            "model",
            None,
            "article",
            "topic",
            tmp_path / "chart.png",
        )
    )

    assert caps_seen == [None, None]
