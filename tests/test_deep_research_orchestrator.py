#!/usr/bin/env python3
"""Tests for the Deep Research orchestrator loop (#390).

All layers (planner / search / extractor / synthesizer) are mocked at the
deep_research module boundary — no LLM or network calls.
"""

from __future__ import annotations

import asyncio

import pytest

from src.agent_sdk.research import deep_research
from src.agent_sdk.research.deep_research import build_deep_research_brief


def _finding(q: str, passages: list[str], confidence: float = 0.7) -> dict:
    return {"subquestion": q, "passages": passages, "confidence": confidence}


def _wire(
    monkeypatch,
    *,
    subquestions: list[str],
    sources_per_q: list[dict] | None = None,
    extract_cost: float = 0.01,
    verdicts: list[dict] | None = None,
) -> dict:
    """Patch the four layer functions; return counters."""
    counters = {"plan": 0, "search": 0, "extract": [], "assess": 0, "budgets": []}
    sources_per_q = (
        [{"title": "S", "url": "https://s", "snippet": f"stat for {0}"}]
        if sources_per_q is None
        else sources_per_q
    )
    verdict_iter = iter(verdicts or [])

    async def fake_plan(topic, model=None, max_budget_usd=None):
        counters["plan"] += 1
        return subquestions, 0.02

    def fake_search(query, n):
        counters["search"] += 1
        return list(sources_per_q)

    async def fake_extract(subquestion, sources, model=None, max_budget_usd=None):
        counters["extract"].append(subquestion)
        counters["budgets"].append(max_budget_usd)
        passages = [f"passage for {subquestion}"] if sources else []
        return _finding(subquestion, passages), extract_cost

    async def fake_assess(topic, findings, model=None, max_budget_usd=None):
        counters["assess"] += 1
        try:
            return next(verdict_iter), 0.02
        except StopIteration:
            return {"enough": True, "gaps": []}, 0.02

    monkeypatch.setattr(deep_research, "plan_subquestions", fake_plan)
    monkeypatch.setattr(deep_research, "_run_provider_search", fake_search)
    monkeypatch.setattr(deep_research, "extract_passages", fake_extract)
    monkeypatch.setattr(deep_research, "assess_completeness", fake_assess)
    return counters


def test_happy_path_assembles_brief(monkeypatch) -> None:
    counters = _wire(monkeypatch, subquestions=["q1?", "q2?"])

    brief, _cost = asyncio.run(build_deep_research_brief("Topic", max_iterations=1))

    assert brief.startswith("# Research Brief: Topic")
    assert "passage for q1?" in brief
    assert "passage for q2?" in brief
    # single iteration → no synthesizer call, both sub-questions extracted
    # (order within an iteration is nondeterministic — they run in parallel).
    assert counters["assess"] == 0
    assert set(counters["extract"]) == {"q1?", "q2?"}


def test_loop_continues_on_gaps_until_cap(monkeypatch) -> None:
    counters = _wire(
        monkeypatch,
        subquestions=["q1?"],
        verdicts=[{"enough": False, "gaps": ["gap1?", "gap2?"]}],
    )

    asyncio.run(build_deep_research_brief("Topic", max_iterations=2))

    # iter0 extracts q1?; synthesizer asks for gaps; iter1 extracts the gaps;
    # iter1 is the cap so no second synthesizer call. Order within an iteration
    # is nondeterministic (parallel), but iterations are ordered.
    assert counters["extract"][0] == "q1?"
    assert set(counters["extract"][1:]) == {"gap1?", "gap2?"}
    assert len(counters["extract"]) == 3
    assert counters["assess"] == 1


def test_stops_when_synthesizer_says_enough(monkeypatch) -> None:
    counters = _wire(
        monkeypatch,
        subquestions=["q1?"],
        verdicts=[{"enough": True, "gaps": []}],
    )

    asyncio.run(build_deep_research_brief("Topic", max_iterations=3))

    assert counters["extract"] == ["q1?"]
    assert counters["assess"] == 1


def test_empty_planner_falls_back_to_deterministic(monkeypatch) -> None:
    _wire(monkeypatch, subquestions=[])
    monkeypatch.setattr(
        "src.agent_sdk._shared.build_research_brief",
        lambda topic: f"DETERMINISTIC BRIEF for {topic}",
    )

    brief, _cost = asyncio.run(build_deep_research_brief("Topic"))

    assert brief == "DETERMINISTIC BRIEF for Topic"


def test_budget_cap_stops_after_first_iteration(monkeypatch) -> None:
    counters = _wire(
        monkeypatch,
        subquestions=["q1?", "q2?"],
        extract_cost=5.0,  # one iteration blows the budget
        verdicts=[{"enough": False, "gaps": ["should-not-run?"]}],
    )

    asyncio.run(
        build_deep_research_brief("Topic", max_iterations=3, research_budget_usd=1.0)
    )

    # budget exceeded after iter0 → no synthesizer, no further iterations
    assert set(counters["extract"]) == {"q1?", "q2?"}
    assert counters["assess"] == 0


def test_budget_divided_across_parallel_subquestions(monkeypatch) -> None:
    """Each parallel sub-question gets the REMAINING budget divided by the
    fan-out width, so one iteration cannot collectively overspend (#429 review)."""
    counters = _wire(monkeypatch, subquestions=["a?", "b?", "c?"])

    asyncio.run(
        build_deep_research_brief("Topic", max_iterations=1, research_budget_usd=3.0)
    )

    # remaining after the planner's 0.02 is 2.98, split three ways
    assert len(counters["budgets"]) == 3
    for budget in counters["budgets"]:
        assert budget == pytest.approx((3.0 - 0.02) / 3)


def test_budget_exhausted_before_iteration_breaks(monkeypatch) -> None:
    """If the planner alone exhausts the budget, no extraction runs."""
    counters = _wire(monkeypatch, subquestions=["a?"])

    # planner costs 0.02 > 0.01 budget → remaining negative before iteration 0
    asyncio.run(
        build_deep_research_brief("Topic", max_iterations=2, research_budget_usd=0.01)
    )

    assert counters["extract"] == []


def test_zero_source_subquestion_records_no_evidence(monkeypatch) -> None:
    _wire(monkeypatch, subquestions=["q1?"], sources_per_q=[])

    brief, _cost = asyncio.run(build_deep_research_brief("Topic", max_iterations=1))

    assert "## q1?" in brief
    assert "No evidence found." in brief
