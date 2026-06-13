"""Deep Research synthesizer: decide whether the evidence is sufficient (#390).

One Sonnet call reviews the findings collected so far and decides whether they
cover the topic well enough to write, or which gaps still need researching. The
orchestrator loops on the returned gaps (bounded by a hard iteration cap).

Safe default: on unparseable output, return ``enough=True`` so the loop stops
rather than spinning — bounding cost is more important than one more hop.
"""

from __future__ import annotations

import logging
from typing import Any

import orjson

from src.agent_sdk.research._llm import SYNTHESIZER_MODEL, research_llm_call

logger = logging.getLogger(__name__)

MAX_GAP_QUESTIONS = 5

SYNTHESIZER_SYSTEM = (
    "You assess research completeness for an article. Given a topic and the "
    "findings gathered so far (sub-questions with their evidence and confidence), "
    "decide whether there is enough well-sourced material to write a strong, "
    "well-triangulated article. Return ONLY a JSON object: "
    '{"enough": <bool>, "gaps": ["<new sub-question to research>", ...]}. '
    "If enough is true, gaps must be empty."
)


def _summarise_findings(findings: list[dict[str, Any]]) -> str:
    lines = []
    for f in findings:
        passages = f.get("passages", [])
        lines.append(
            f"- {f.get('subquestion', '')} "
            f"(confidence {f.get('confidence', 0.0):.2f}, "
            f"{len(passages)} passage(s))"
        )
    return "\n".join(lines)


def _parse_verdict(text: str) -> dict[str, Any]:
    """Parse ``{enough, gaps}``; default to stopping on any failure."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = orjson.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                enough = bool(parsed.get("enough", True))
                gaps = [
                    str(g).strip() for g in parsed.get("gaps", []) if str(g).strip()
                ]
                gaps = gaps[:MAX_GAP_QUESTIONS]
                # A coherent verdict: if we are stopping there are no gaps.
                if enough:
                    gaps = []
                return {"enough": enough, "gaps": gaps}
        except (orjson.JSONDecodeError, TypeError, ValueError):
            pass

    logger.warning("Synthesizer output unparseable; stopping the research loop")
    return {"enough": True, "gaps": []}


async def assess_completeness(
    topic: str,
    findings: list[dict[str, Any]],
    model: str = SYNTHESIZER_MODEL,
    max_budget_usd: float | None = None,
) -> tuple[dict[str, Any], float]:
    """Return ``({enough, gaps}, cost_usd)`` for the findings gathered so far."""
    prompt = (
        f"Topic: {topic}\n\n"
        f"Findings so far:\n{_summarise_findings(findings)}\n\n"
        "Is this enough to write a strong, well-sourced article? Return the JSON "
        "object."
    )
    text, cost = await research_llm_call(
        prompt, SYNTHESIZER_SYSTEM, model, max_budget_usd
    )
    return _parse_verdict(text), cost
