#!/usr/bin/env python3
"""Regression for BUG-061 (found by the B-020 acceptance run): the writer's
budget must be able to FUND the retry policy it advertises.

The writer budget is cumulative across attempts by design — it is the runaway
guard, and each attempt gets the remaining balance (stage3_runner). The defect
was that the shipped default could not pay for a second attempt, so a malformed
first draft — a normal, *handled* condition with ``_WRITER_MAX_ATTEMPTS = 3`` —
aborted the whole run with a generic ``BudgetExceededError`` after real money had
already been spent.

These tests model the Agent SDK's actual budget behaviour: a call whose cap is
below one attempt's cost aborts instead of producing text.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import src.agent_sdk.stage3_runner as s3
from src.agent_sdk.stage3_runner import BudgetExceededError, run_stage3

_GOOD = (
    "---\nlayout: post\ntitle: t\n"
    "image: /assets/images/test-slug.png\n---\n\n"
    "Body paragraph. As the chart shows, things happen.\n"
)
_CHART = '{"title": "T", "data": [{"metric": "A", "value": 1, "color": "navy"}]}'
_EMPTY_BODY = "---\nlayout: post\ntitle: t\n---\n\n"  # frontmatter, no body


def _wire_metered(monkeypatch, writer_outputs: list[str]) -> list[float | None]:
    """Feed the writer drafts through a collector that CHARGES like the real SDK.

    Every writer call costs ``s3._WRITER_ATTEMPT_COST_USD``, and a call whose cap
    is below that aborts with ``BudgetExceededError`` — exactly what the Agent SDK
    does via ``subtype="error_max_budget_usd"``. Returns the list of caps the
    writer was actually given, so a test can assert on the arithmetic.
    """
    caps_seen: list[float | None] = []
    drafts = iter(writer_outputs)

    async def fake_collect(prompt, system_prompt, **kwargs):
        cap = kwargs.get("max_budget_usd")
        if system_prompt is not s3.WRITER_SYSTEM_PROMPT:
            return _CHART, 0.01  # graphics — not under test here
        caps_seen.append(cap)
        cost = s3._WRITER_ATTEMPT_COST_USD
        if cap is not None and cap < cost:
            raise BudgetExceededError(
                f"Agent SDK budget exceeded: cap=${cap:.4f}", budget_usd=cap
            )
        return next(drafts), cost

    monkeypatch.setattr(s3, "_collect_text", fake_collect)
    monkeypatch.setattr(s3, "_fetch_style_context", lambda topic: "")
    monkeypatch.setattr(s3, "build_research_brief", lambda topic: "# Brief")
    return caps_seen


def test_default_budget_funds_a_full_retry_after_a_malformed_draft(
    tmp_path: Path, monkeypatch
) -> None:
    """The shipped default must survive the failure mode it was built to handle."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    _wire_metered(monkeypatch, [_EMPTY_BODY, _GOOD])

    result = asyncio.run(run_stage3("topic"))  # default writer budget

    assert "things happen" in result.article


def test_default_budget_funds_every_advertised_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    """_WRITER_MAX_ATTEMPTS attempts are promised, so all of them must be payable."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    drafts = [_EMPTY_BODY] * (s3._WRITER_MAX_ATTEMPTS - 1) + [_GOOD]
    caps_seen = _wire_metered(monkeypatch, drafts)

    result = asyncio.run(run_stage3("topic"))

    assert "things happen" in result.article
    assert len(caps_seen) == s3._WRITER_MAX_ATTEMPTS


def test_a_budget_too_small_to_retry_says_so_before_spending(
    tmp_path: Path, monkeypatch
) -> None:
    """An unfundable retry must not be started; the error must name the flag."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    # Enough for attempt 1 only. Attempt 1 is malformed, so a retry is needed.
    budget = s3._WRITER_ATTEMPT_COST_USD * 1.5
    caps_seen = _wire_metered(monkeypatch, [_EMPTY_BODY, _GOOD])

    with pytest.raises(BudgetExceededError) as excinfo:
        asyncio.run(run_stage3("topic", writer_budget_usd=budget))

    message = str(excinfo.value)
    assert "--writer-budget" in message, "operator needs to know which knob to turn"
    assert "attempt 2" in message, "operator needs to know which attempt was starved"
    # The doomed attempt must never have been dispatched.
    assert len(caps_seen) == 1


def test_an_unbounded_budget_still_retries(tmp_path: Path, monkeypatch) -> None:
    """writer_budget_usd=None means no cap — the guard must not fire on it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_MODE", raising=False)
    caps_seen = _wire_metered(monkeypatch, [_EMPTY_BODY, _GOOD])

    result = asyncio.run(run_stage3("topic", writer_budget_usd=None))

    assert "things happen" in result.article
    assert caps_seen == [None, None]
