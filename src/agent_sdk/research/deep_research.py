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
MAX_ITERATIONS_CEILING = 3  # spec: "Ask first to exceed"; clamp as a backstop
DEFAULT_RESEARCH_BUDGET_USD = 2.50
SOURCES_PER_SUBQUESTION = 5

# The same anti-fabrication guardrails the deterministic build_research_brief
# prepends. Duplicated here (not imported) because the source lives in
# _shared.py, which the arch-review gate blocks from editing (ADR-002);
# single-sourcing both briefs is tracked in #420.
_RESEARCH_BRIEF_GUARDRAILS = (
    "The following sources were found via live web search.",
    "Use ONLY statistics and claims from these sources.",
    "If you need a statistic not listed below, tag it [NEEDS SOURCE].",
    "Do NOT invent statistics, researcher names, or URLs.",
    "Every sentence containing a percentage, multiplier, or quantified claim "
    "must name the source inline (e.g. 'According to Gartner, 2024, …').",
)


def _format_brief(topic: str, findings: list[dict[str, Any]]) -> str:
    """Render findings as a research brief (same string contract as the
    deterministic ``build_research_brief``: the anti-fabrication guardrail
    header plus a sourced text block the writer embeds and the stat audit
    greps for cited numbers)."""
    lines = [f"# Research Brief: {topic}", "", *_RESEARCH_BRIEF_GUARDRAILS, ""]
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

    Budget is enforced cumulatively: each call receives the *remaining* budget as
    its per-call ceiling, and the parallel fan-out divides the remainder across
    the in-flight sub-questions so a single iteration cannot overspend.
    """
    max_iterations = max(1, min(max_iterations, MAX_ITERATIONS_CEILING))
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
        remaining = research_budget_usd - spent
        if remaining <= 0:
            logger.warning(
                "Deep research budget $%.2f exhausted before iteration %d; stopping",
                research_budget_usd,
                iteration + 1,
            )
            break
        # Divide the remaining budget across the parallel sub-questions so the
        # fan-out cannot collectively overspend within a single iteration.
        per_call = remaining / len(subquestions)
        results = await asyncio.gather(
            *(_research_one(q, per_call) for q in subquestions)
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
        # Last iteration: skip the synthesizer (a wasted Sonnet call — we won't
        # loop again regardless of its verdict).
        if iteration == max_iterations - 1:
            break

        verdict, call_cost = await assess_completeness(
            topic, findings, max_budget_usd=research_budget_usd - spent
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
