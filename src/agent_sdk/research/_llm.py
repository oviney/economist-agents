"""Thin Agent SDK query helper for Deep Research orchestration (#390).

Research has historically had no LLM in the path. Deep Research adds a few
orchestration calls (planner, extractor, synthesizer); this module isolates the
single-turn Agent SDK boilerplate so each layer can stay focused on prompts and
parsing. Returns ``(text, cost_usd)`` like ``stage3_runner._collect_text`` but
without the writer-specific chunk-joining.
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

PLANNER_MODEL = "claude-sonnet-4-6"
EXTRACTOR_MODEL = "claude-haiku-4-5"
SYNTHESIZER_MODEL = "claude-sonnet-4-6"


async def research_llm_call(
    prompt: str,
    system_prompt: str,
    model: str,
    max_budget_usd: float | None = None,
) -> tuple[str, float]:
    """Run one single-turn Agent SDK query and return ``(text, cost_usd)``.

    No tools are exposed and no budget exception is raised here — the
    orchestrator enforces the overall research budget across calls and treats a
    zero-cost empty response as a soft failure.
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        max_turns=1,
        permission_mode="bypassPermissions",
        allowed_tools=[],
        mcp_servers={},
        stderr=lambda line: logger.warning("research agent-sdk stderr: %s", line),
        max_budget_usd=max_budget_usd,
    )
    text_parts: list[str] = []
    cost = 0.0
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            cost = float(message.total_cost_usd or 0.0)
    return "".join(text_parts), cost
