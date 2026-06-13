"""Deep Research extractor: pull source-grounded passages for a sub-question (#390).

One Haiku call per sub-question reduces the retrieved sources to the passages
that actually answer it, plus a confidence score. This is where most research
calls happen, so it runs on the cheap model. v1 extracts from search-result
snippets (title/url/snippet); full-page fetch is a deferred v2 extension.

Failure is soft: if the model output does not parse, fall back to the raw source
snippets at low confidence so retrieved evidence is never lost, and the run
never crashes.
"""

from __future__ import annotations

import logging
from typing import Any

import orjson

from src.agent_sdk.research._llm import EXTRACTOR_MODEL, research_llm_call

logger = logging.getLogger(__name__)

_FALLBACK_CONFIDENCE = 0.3

EXTRACTOR_SYSTEM = (
    "You extract evidence for a specific research sub-question from a list of "
    "sources. Use ONLY the provided source text — never invent facts, numbers, "
    "or citations. Return ONLY a JSON object: "
    '{"passages": ["<verbatim or lightly-edited relevant passage>", ...], '
    '"confidence": <0.0-1.0 how well the sources answer the sub-question>}.'
)

# A reusable type for a normalised source dict.
Source = dict[str, str]


def _format_sources(sources: list[Source]) -> str:
    lines = []
    for i, src in enumerate(sources, 1):
        lines.append(
            f"[{i}] {src.get('title', '')} ({src.get('url', '')})\n"
            f"    {src.get('snippet', '')}"
        )
    return "\n".join(lines)


def _parse_extraction(text: str, sources: list[Source]) -> dict[str, Any]:
    """Parse ``{passages, confidence}`` from model output.

    On any failure, fall back to the source snippets at low confidence so the
    retrieved evidence survives and the run continues.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = orjson.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                passages = [
                    str(p).strip() for p in parsed.get("passages", []) if str(p).strip()
                ]
                confidence = float(parsed.get("confidence", 0.0) or 0.0)
                return {
                    "passages": passages,
                    "confidence": max(0.0, min(1.0, confidence)),
                }
        except (orjson.JSONDecodeError, TypeError, ValueError):
            pass

    logger.warning("Extractor output unparseable; falling back to snippets")
    snippets = [s.get("snippet", "").strip() for s in sources if s.get("snippet")]
    return {
        "passages": snippets,
        "confidence": _FALLBACK_CONFIDENCE if snippets else 0.0,
    }


async def extract_passages(
    subquestion: str,
    sources: list[Source],
    model: str = EXTRACTOR_MODEL,
    max_budget_usd: float | None = None,
) -> tuple[dict[str, Any], float]:
    """Return ``({subquestion, passages, confidence}, cost_usd)``.

    A sub-question with no sources yields empty passages at zero confidence and
    makes no LLM call (zero cost) — the orchestrator records this as
    "no evidence found" rather than failing.
    """
    if not sources:
        return (
            {"subquestion": subquestion, "passages": [], "confidence": 0.0},
            0.0,
        )

    prompt = (
        f"Sub-question: {subquestion}\n\n"
        f"Sources:\n{_format_sources(sources)}\n\n"
        "Extract the passages that answer the sub-question as the JSON object."
    )
    text, cost = await research_llm_call(
        prompt, EXTRACTOR_SYSTEM, model, max_budget_usd
    )
    parsed = _parse_extraction(text, sources)
    return (
        {
            "subquestion": subquestion,
            "passages": parsed["passages"],
            "confidence": parsed["confidence"],
        },
        cost,
    )
