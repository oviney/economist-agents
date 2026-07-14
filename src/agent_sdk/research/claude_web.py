"""Keyless web research via the Agent SDK (B-006).

The deterministic research path calls Serper (needs ``SERPER_API_KEY``); the
deep-research path also drives Serper under the hood. This module instead lets
Claude do its own live web research through the Agent SDK's built-in
``WebSearch``/``WebFetch`` tools, so a full pipeline run needs **no paid API
key** — only the Claude subscription the ``claude`` CLI is authenticated with.

``build_claude_web_brief(topic)`` returns ``(brief, cost_usd)`` with the same
string contract as ``build_research_brief``/``build_deep_research_brief`` (the
anti-fabrication guardrail header followed by a sourced text block), so the
Stage 3 writer prompt and the stat audit are unchanged.

Trade-offs (recorded in the B-006 ADR): this puts an LLM in the research path
and is non-deterministic. The downstream ``citation_verifier`` /
``publication_validator`` gates still enforce source quality.
"""

from __future__ import annotations

import logging

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

logger = logging.getLogger(__name__)

RESEARCH_MODEL = "claude-sonnet-4-6"
# Enough turns for a few search→fetch→reason loops without running away.
MAX_TURNS = 12

# Mirror the anti-fabrication guardrails the deterministic/deep briefs prepend
# so the writer and stat audit see an identical contract regardless of mode.
_RESEARCH_BRIEF_GUARDRAILS = (
    "The following sources were found via live web search.",
    "Use ONLY statistics and claims from these sources.",
    "If you need a statistic not listed below, tag it [NEEDS SOURCE].",
    "Do NOT invent statistics, researcher names, or URLs.",
    "Every sentence containing a percentage, multiplier, or quantified claim "
    "must name the source inline (e.g. 'According to Gartner, 2024, …').",
)

_SYSTEM_PROMPT = (
    "You are a meticulous research analyst. Use the WebSearch and WebFetch "
    "tools to find recent, credible, quantified evidence on the given topic. "
    "Prefer primary sources and reports. For every statistic you report, name "
    "the source and include its URL. Never invent statistics, names, or URLs — "
    "if you cannot verify a number, omit it. Return a concise brief of the "
    "strongest sourced findings, grouped under short ## sub-headings, each as "
    "'- <claim with inline source>. Source: <url>'."
)


def _format_brief(topic: str, body: str) -> str:
    """Render the researched ``body`` as a brief string (same contract as
    ``build_research_brief``: guardrail header + sourced text block)."""
    lines = [f"# Research Brief: {topic}", "", *_RESEARCH_BRIEF_GUARDRAILS, ""]
    if body.strip():
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines)


async def build_claude_web_brief(
    topic: str,
    max_budget_usd: float | None = None,
) -> tuple[str, float]:
    """Research ``topic`` with Claude's own web tools; return ``(brief, cost)``.

    Keyless: authenticates via the ``claude`` CLI subscription, uses no Serper
    and no ``anthropic`` client. On any SDK failure the brief still returns with
    its guardrail header (an empty findings block) so the pipeline degrades
    softly rather than crashing.

    Args:
        topic: The article topic to research.
        max_budget_usd: Optional cumulative SDK budget ceiling for this call.

    Returns:
        ``(brief, cost_usd)`` — the brief string and SDK-reported cost.
    """
    options = ClaudeAgentOptions(
        system_prompt=_SYSTEM_PROMPT,
        model=RESEARCH_MODEL,
        max_turns=MAX_TURNS,
        permission_mode="bypassPermissions",
        allowed_tools=["WebSearch", "WebFetch"],
        mcp_servers={},
        stderr=lambda line: logger.warning("claude_web stderr: %s", line),
        max_budget_usd=max_budget_usd,
    )
    prompt = (
        f"Research this topic for an Economist-style article: {topic}\n\n"
        "Find 4-6 strong, recent, quantified findings, each with a named source "
        "and URL. Return only the grouped sourced findings."
    )

    text_parts: list[str] = []
    cost = 0.0
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(message, ResultMessage):
                cost = float(message.total_cost_usd or 0.0)
    except Exception as exc:  # noqa: BLE001 — soft-degrade, never crash Stage 3
        logger.warning(
            "claude_web research failed (%s) — returning empty brief", exc
        )

    body = "".join(text_parts)
    if not body.strip():
        logger.warning("claude_web research produced no findings for %r", topic)
    return _format_brief(topic, body), cost
