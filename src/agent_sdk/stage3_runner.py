"""Stage 3 spike — Writer + Graphics on the Anthropic Agent SDK.

Replaces ``src/crews/stage3_crew.py`` for the Phase 2 spike (ADR-0006,
epic #308, story #309). The CrewAI path remains the production code
path; this module runs side-by-side so the comparison report has data
from both runtimes on the same topic.

Design:
- Research stays deterministic — calls ``Stage3Crew._build_research_brief``
  so the LLM never participates in the research path.
- Writer and Graphics each run as a single ``query()`` against the Agent
  SDK with the existing role prompts.
- Stat audit runs after the writer via ``_audit_article_stats``.
- ``total_cost_usd`` is captured from the ``ResultMessage`` of every
  query and summed for the run.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import orjson
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from src.crews.stage3_crew import (
    GRAPHICS_AGENT_PROMPT,
    Stage3Crew,
    _audit_article_stats,
)

logger = logging.getLogger(__name__)

DEFAULT_WRITER_MODEL = os.environ.get("WRITER_MODEL", "claude-sonnet-4-6")
DEFAULT_GRAPHICS_MODEL = os.environ.get("GRAPHICS_MODEL", "claude-sonnet-4-6")

WRITER_SYSTEM_PROMPT = """You are an Economist-style Writer renowned for sharp, witty prose with British flair.
Every article must satisfy the 10 rules below before submission. Do not attempt to read any files
or use any tools — write the article directly from this brief.

STRUCTURE RULES:
- State a specific, debatable THESIS in the first two paragraphs — not a topic, an argument
- Use 3-4 headings maximum (one per 250-350 words); headings must be noun phrases that advance the argument
- End with a vivid prediction, metaphor, or provocation — never a summary

TITLE RULES:
- Provocative and memorable; use a colon for a surprising twist
- BANNED title patterns: starting with "Why" or "How", "The Impact of", "The Role of", purely descriptive titles

BANNED OPENINGS:
- "In today's world", "It's no secret", "The arrival/emergence/rise of", "When it comes to", "Amidst"
- Any sentence starting with "The" followed by an abstract noun

BANNED IN BODY — NO LISTS:
- Numbered lists (1., 2., 3.), bulleted lists (-, *), "The following steps", "Here are N ways"

BANNED HEDGING PHRASES:
- "it would be misguided", "one might", "it is worth noting", "it is not a minor footnote"
- "it should be noted", "it is important to", "further complicating matters"
- "invites closer scrutiny", "in practical terms"
- "game-changer", "paradigm shift", "leverage" (as verb)

BANNED GENERIC ATTRIBUTION — NAME NAMES:
- "organisations" (use the company name), "professionals" (use the role: "engineers at Google")
- "studies show" (name the study), "experts say" (name the expert), "research indicates" (cite the paper)
- Every article must include at least 2 named companies or individuals with specific anecdotes

BANNED CLOSINGS:
- "will rest on", "depends on", "the key is", "In conclusion", "To summarise"
- "Only time will tell", "remains to be seen"
- Any sentence that restates the thesis without adding new insight

VOICE (British, confident, witty):
- British spelling throughout: organisation, analyse, colour, favour
- Active voice: "Companies are racing" not "it is being observed that"
- Reads like a brilliant dinner companion, not a textbook

FORMATTING:
- Separate paragraphs with a blank line
- Place a blank line before and after every `## ` heading
- Do not emit the article more than once; output exactly one article per response"""


@dataclass
class SpikeResult:
    """Captured metrics from a Stage 3 spike run."""

    topic: str
    article: str
    chart_data: dict
    total_cost_usd: float
    writer_cost_usd: float
    graphics_cost_usd: float
    writer_model: str
    graphics_model: str
    wall_seconds: float
    research_brief_chars: int
    article_chars: int
    stat_audit_removed: int


_INLINE_HEADING_PATTERN = re.compile(r"[ \t]+(##+ +[A-Z][^\n]*)")
_HEADING_LINE_PATTERN = re.compile(r"(?<!\n\n)(^|\n)(##+ +[^\n]+)\n(?!\n)")
_DUPLICATE_FRONTMATTER_PATTERN = re.compile(r"\n---\nlayout:.*", re.DOTALL)


def _normalize_paragraphs(text: str) -> str:
    """Restore blank lines around `##` headings.

    The model frequently emits headings glued to the preceding sentence
    on the same line (``"...the easy part. ## The Perception Gap"``).
    Lift any inline heading onto its own line, then ensure every heading
    has a blank line before and after it.
    """
    text = _INLINE_HEADING_PATTERN.sub(r"\n\n\1", text)
    text = _HEADING_LINE_PATTERN.sub(r"\1\2\n\n", text)
    return text


def _strip_duplicate_article(text: str) -> str:
    """If the model emitted two complete articles, keep only the first.

    The pattern looks for a ``\\n---\\nlayout:`` block, which can only
    appear after the original frontmatter (the original starts at offset
    zero with ``---``, no leading newline). When found, the second
    article is dropped.
    """
    match = _DUPLICATE_FRONTMATTER_PATTERN.search(text)
    if match:
        logger.warning(
            "Stripping duplicate article emission at offset %d", match.start()
        )
        return text[: match.start()].rstrip() + "\n"
    return text


async def _collect_text(
    prompt: str,
    system_prompt: str,
    model: str = DEFAULT_WRITER_MODEL,
    max_budget_usd: float | None = None,
) -> tuple[str, float]:
    """Run a single Agent SDK query and return ``(text, cost_usd)``.

    Streaming text chunks are joined with a space when the boundary
    between two chunks looks like an unintended word concatenation
    (lowercase letter followed by uppercase letter), to avoid artefacts
    such as "OrganisationsDoubleDown" seen in the Story 1 spike output.
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        max_turns=1,
        permission_mode="bypassPermissions",
        allowed_tools=[],
        stderr=lambda line: logger.warning("agent-sdk stderr: %s", line),
        max_budget_usd=max_budget_usd,
    )
    text_chunks: list[str] = []
    cost = 0.0
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text_chunks.append(block.text)
        elif isinstance(msg, ResultMessage):
            cost = float(msg.total_cost_usd or 0.0)

    pieces: list[str] = []
    for chunk in text_chunks:
        if pieces and pieces[-1] and chunk:
            prev_last = pieces[-1][-1]
            curr_first = chunk[0]
            if prev_last.islower() and curr_first.isupper():
                pieces.append(" ")
        pieces.append(chunk)
    return "".join(pieces), cost


def _parse_chart_json(text: str) -> dict:
    """Extract the chart dict from raw model output.

    The model frequently wraps JSON in ```json fences``` — strip those,
    then parse. On failure, fall back to embedding the raw text under
    ``specification`` so downstream code does not crash.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        cleaned = cleaned[first_nl + 1 :] if first_nl != -1 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {"specification": text}


async def run_stage3_spike(
    topic: str,
    writer_budget_usd: float | None = 0.30,
    graphics_budget_usd: float | None = 0.10,
    writer_model: str = DEFAULT_WRITER_MODEL,
    graphics_model: str = DEFAULT_GRAPHICS_MODEL,
) -> SpikeResult:
    """Generate one article via the Agent SDK and return captured metrics.

    Mirrors ``Stage3Crew.kickoff`` so output is comparable.

    Args:
        topic: Article topic.
        writer_budget_usd: Hard cap for the writer call. Default 0.30
            (~3× headroom over observed Sonnet 4.6 runs ~$0.11). Bump
            to 0.60 for Opus runs.
        graphics_budget_usd: Hard cap for the graphics call. Default
            0.10 (~3× headroom over ~$0.03).
        writer_model: Model id for the Writer call. Default Sonnet 4.6
            because the Story 4 verification run showed Opus 4.7 cost
            3.4× more for a marginally LOWER score on this task. Override
            with WRITER_MODEL env var if your topic needs deeper reasoning.
        graphics_model: Model id for the Graphics call. Default Sonnet
            4.6; override with GRAPHICS_MODEL env var.

    Returns:
        SpikeResult with article text, chart dict, cost, and timing.
    """
    start = time.perf_counter()

    research_brief = Stage3Crew._build_research_brief(topic)
    logger.info("Research brief: %d chars", len(research_brief))

    writer_prompt = (
        f"Write the complete Economist-style article on this topic: {topic}\n\n"
        f"Output the entire article text with YAML frontmatter at the top. "
        f"Start directly with `---` — no preamble, no commentary.\n\n"
        f"Frontmatter must include: layout, title, date, author, categories "
        f"(kebab-case from quality-engineering, software-engineering, "
        f"test-automation, security), image (/assets/images/SLUG.png), "
        f"and description (160 chars max).\n\n"
        f"Body must be at least 850 words (the publication validator "
        f"rejects anything under 700, so leave a margin). End with a "
        f"`## References` section containing 3+ numbered citations.\n\n"
        f"At least one paragraph in the body must reference the chart "
        f"explicitly — write something like 'as the chart shows', "
        f"'the chart makes clear', or 'the chart below illustrates'. "
        f"This is required by the publication validator.\n\n"
        f"RESEARCH BRIEF (use ONLY these sources and statistics — do NOT "
        f"invent any statistics, researcher names, or URLs):\n\n"
        f"{research_brief}"
    )
    raw_writer_output, writer_cost = await _collect_text(
        writer_prompt,
        WRITER_SYSTEM_PROMPT,
        model=writer_model,
        max_budget_usd=writer_budget_usd,
    )
    pre_audit_article = _strip_duplicate_article(raw_writer_output)

    audited = _audit_article_stats(pre_audit_article, research_brief)
    stat_audit_removed = pre_audit_article.count(".") - audited.count(".")
    article = _normalize_paragraphs(audited)

    graphics_prompt = (
        "Generate the chart JSON for this article. Output a single valid "
        "JSON object with keys: title, subtitle, data (list of "
        "{metric, value, unit, color}), colors (navy/burgundy hex map), "
        "dimensions (width/height). No commentary, no markdown fences.\n\n"
        f"Article excerpt:\n{article[:2500]}"
    )
    graphics_text, graphics_cost = await _collect_text(
        graphics_prompt,
        GRAPHICS_AGENT_PROMPT,
        model=graphics_model,
        max_budget_usd=graphics_budget_usd,
    )
    chart_data = _parse_chart_json(graphics_text)

    elapsed = time.perf_counter() - start

    return SpikeResult(
        topic=topic,
        article=article,
        chart_data=chart_data,
        total_cost_usd=writer_cost + graphics_cost,
        writer_cost_usd=writer_cost,
        graphics_cost_usd=graphics_cost,
        writer_model=writer_model,
        graphics_model=graphics_model,
        wall_seconds=elapsed,
        research_brief_chars=len(research_brief),
        article_chars=len(article),
        stat_audit_removed=max(stat_audit_removed, 0),
    )


def main() -> None:
    """CLI entrypoint — write spike artefacts to ``logs/spike/``."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    topic = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "developer productivity in the age of AI coding agents"
    )
    print(f"Running Stage 3 spike on topic: {topic}")
    result = asyncio.run(run_stage3_spike(topic))

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agent_sdk_article.md").write_text(result.article)
    (out_dir / "agent_sdk_chart.json").write_bytes(
        orjson.dumps(result.chart_data, option=orjson.OPT_INDENT_2)
    )
    metrics = {
        k: v for k, v in asdict(result).items() if k not in ("article", "chart_data")
    }
    (out_dir / "agent_sdk_metrics.json").write_bytes(
        orjson.dumps(metrics, option=orjson.OPT_INDENT_2)
    )

    print(
        f"Spike complete: ${result.total_cost_usd:.4f} "
        f"(writer ${result.writer_cost_usd:.4f}, "
        f"graphics ${result.graphics_cost_usd:.4f}), "
        f"{result.wall_seconds:.1f}s, "
        f"{result.article_chars} chars."
    )
    print("Artefacts: logs/spike/agent_sdk_{article.md,chart.json,metrics.json}")


if __name__ == "__main__":
    main()
