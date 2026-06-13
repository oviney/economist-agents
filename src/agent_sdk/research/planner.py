"""Deep Research planner: decompose a topic into research sub-questions (#390).

One Sonnet call turns a topic into 3-5 specific, independently-searchable
sub-questions. Robust to the model wrapping its JSON in prose or code fences;
returns an empty list on unparseable output so the orchestrator can fall back to
the deterministic brief rather than crash.
"""

from __future__ import annotations

import logging

import orjson

from src.agent_sdk.research._llm import PLANNER_MODEL, research_llm_call

logger = logging.getLogger(__name__)

MAX_SUBQUESTIONS = 5

PLANNER_SYSTEM = (
    "You are a research planner. Given a topic, decompose it into specific, "
    "independently-searchable sub-questions that together cover the topic. "
    "Each sub-question must be answerable from web/academic sources. Do not "
    "answer them. Return ONLY a JSON array of 3-5 strings, nothing else."
)


def _parse_subquestions(text: str) -> list[str]:
    """Extract a JSON array of sub-question strings from raw model output.

    Tolerates code fences and surrounding prose by slicing the first ``[`` to the
    last ``]``. Returns ``[]`` on any failure (the orchestrator then falls back).
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("Planner output had no JSON array; got %r", text[:120])
        return []
    try:
        parsed = orjson.loads(text[start : end + 1])
    except orjson.JSONDecodeError:
        logger.warning(
            "Planner JSON array did not parse: %r", text[start : end + 1][:120]
        )
        return []
    if not isinstance(parsed, list):
        return []
    questions = [str(q).strip() for q in parsed if str(q).strip()]
    return questions[:MAX_SUBQUESTIONS]


async def plan_subquestions(
    topic: str,
    model: str = PLANNER_MODEL,
    max_budget_usd: float | None = None,
) -> tuple[list[str], float]:
    """Return ``(sub_questions, cost_usd)`` for ``topic`` (3-5, possibly empty)."""
    prompt = (
        f"Topic: {topic}\n\n"
        "Decompose this into 3-5 specific research sub-questions as a JSON array "
        "of strings."
    )
    text, cost = await research_llm_call(prompt, PLANNER_SYSTEM, model, max_budget_usd)
    return _parse_subquestions(text), cost
