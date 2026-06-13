"""Deep Research orchestrator: recursive planner→search→extract→synthesise (#390).

``build_deep_research_brief(topic)`` ties the layers together into the recursive
loop and returns a research-brief string with the same shape contract as
``build_research_brief`` — so the writer prompt and the stat audit are unchanged.

This is OPT-IN; ``stage3_runner`` only calls it when ``research_mode="deep"``.
The loop is bounded two ways: a hard iteration cap and a cumulative dollar
budget. Every failure mode degrades softly:
- planner yields no sub-questions      → fall back to the deterministic brief
- a sub-question returns no sources     → recorded as "no evidence", not a crash
- malformed LLM output                  → handled in each layer (see their docs)
- budget reached                        → stop and assemble what we have
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.agent_sdk.research.extractor import extract_passages
from src.agent_sdk.research.planner import plan_subquestions
from src.agent_sdk.research.synthesizer import assess_completeness
from src.agent_sdk.tools.research_tools import _run_provider_search

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 2
DEFAULT_RESEARCH_BUDGET_USD = 2.50
SOURCES_PER_SUBQUESTION = 5


def _format_brief(topic: str, findings: list[dict[str, Any]]) -> str:
    """Render findings as a research brief (same string contract as the
    deterministic ``build_research_brief``: a sourced text block the writer
    embeds and the stat audit greps for cited numbers)."""
    lines = [f"# Research Brief: {topic}", ""]
    for finding in findings:
        passages = finding.get("passages") or []
        heading = finding.get("subquestion", "")
        if not passages:
            lines.append(f"## {heading}")
            lines.append("- No evidence found.")
            lines.append("")
            continue
        lines.append(f"## {heading}")
        lines.extend(f"- {p}" for p in passages)
        lines.append("")
    return "\n".join(lines)


async def _research_one(
    subquestion: str, budget: float
) -> tuple[dict[str, Any], float]:
    """Search + extract for a single sub-question (search runs off the loop)."""
    sources = await asyncio.to_thread(
        _run_provider_search, subquestion, SOURCES_PER_SUBQUESTION
    )
    return await extract_passages(subquestion, sources, max_budget_usd=budget)


async def build_deep_research_brief(
    topic: str,
    max_iterations: int = MAX_ITERATIONS,
    research_budget_usd: float = DEFAULT_RESEARCH_BUDGET_USD,
) -> tuple[str, float]:
    """Run the recursive research loop and return ``(brief, cost_usd)``.

    The brief string has the same shape contract as ``build_research_brief`` (so
    the writer + stat audit are unchanged); the cost is surfaced so the pipeline
    can record research spend in the cost log.
    """
    spent = 0.0

    subquestions, cost = await plan_subquestions(
        topic, max_budget_usd=research_budget_usd
    )
    spent += cost
    if not subquestions:
        logger.warning(
            "Deep research planner produced no sub-questions; "
            "falling back to the deterministic brief"
        )
        from src.agent_sdk._shared import build_research_brief

        return build_research_brief(topic), spent

    findings: list[dict[str, Any]] = []
    for iteration in range(max_iterations):
        results = await asyncio.gather(
            *(_research_one(q, research_budget_usd) for q in subquestions)
        )
        for finding, call_cost in results:
            findings.append(finding)
            spent += call_cost

        if spent >= research_budget_usd:
            logger.warning(
                "Deep research budget $%.2f reached after iteration %d; stopping",
                research_budget_usd,
                iteration + 1,
            )
            break
        if iteration == max_iterations - 1:
            break

        verdict, call_cost = await assess_completeness(
            topic, findings, max_budget_usd=research_budget_usd
        )
        spent += call_cost
        if verdict["enough"] or not verdict["gaps"]:
            break
        subquestions = verdict["gaps"]

    logger.info(
        "Deep research complete: %d findings across the topic, $%.4f spent",
        len(findings),
        spent,
    )
    return _format_brief(topic, findings), spent
