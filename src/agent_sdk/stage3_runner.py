"""Stage 3 production runtime — Writer + Graphics on the Anthropic Agent SDK.

This is the sole production runtime for Stage 3 (article + chart
generation). It originated as the Phase 2 spike that replaced
``src/crews/stage3_crew.py`` (ADR-0006, epic #308, story #309); the
CrewAI path has since been removed.

Design:
- Research stays deterministic — calls ``build_research_brief`` from
  ``_shared`` so the LLM never participates in the research path.
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
from typing import Any

import orjson
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
)

from scripts.publication_validator import (
    BLOG_AUTHOR,
    WORD_COUNT_MIN,
    WORD_COUNT_TARGET,
)
from src.agent_sdk._shared import (
    _ALLOWED_MODELS as _ALLOWED_MODELS,
)
from src.agent_sdk._shared import (
    GRAPHICS_AGENT_PROMPT,
    BudgetExceededError,
    build_research_brief,
    canonical_slug,
)
from src.agent_sdk._shared import (
    audit_article_stats as _audit_article_stats,
)
from src.agent_sdk.chart_renderer import ChartRenderError, render_chart
from src.agent_sdk.hero_svg import HERO_IMAGES_DIR
from src.agent_sdk.image_prompt_synth import PromptSynthError, compose_prompt
from src.agent_sdk.research.claude_web import build_claude_web_brief
from src.agent_sdk.research.deep_research import build_deep_research_brief
from src.agent_sdk.tools.research_tools import SourceFetchSession, build_search_tool

logger = logging.getLogger(__name__)


def _fetch_style_context(topic: str) -> str:
    """Fetch a style-memory exemplar block for the writer prompt.

    Isolated from ``run_stage3`` so the StyleMemoryTool import (which
    transitively pulls in ChromaDB) is paid only when the runtime needs
    it, and so tests can monkeypatch this function without touching the
    tool itself.

    Returns an empty string when the tool is unavailable, errors out, or
    returns no exemplars above the relevance threshold — callers must
    omit the ``## Style Memory`` section entirely in that case.
    """
    try:
        from src.tools.style_memory_tool import StyleMemoryTool
    except ImportError as exc:
        logger.info("StyleMemoryTool unavailable (%s); skipping style context", exc)
        return ""

    try:
        tool = StyleMemoryTool()
        return tool.get_style_context(topic)
    except Exception as exc:  # noqa: BLE001 — style memory is best-effort
        logger.warning("StyleMemoryTool.get_style_context failed: %s", exc)
        return ""


class MalformedArticleError(ValueError):
    """Raised when the writer agent returns output that is not a well-formed article."""


def _validated_model(env_var: str, default: str) -> str:
    value = os.environ.get(env_var, default)
    if value not in _ALLOWED_MODELS:
        logger.warning(
            "%s=%r is not in the allowlist — falling back to default", env_var, value
        )
        return default
    return value


DEFAULT_WRITER_MODEL = _validated_model("WRITER_MODEL", "claude-sonnet-4-6")
DEFAULT_GRAPHICS_MODEL = _validated_model("GRAPHICS_MODEL", "claude-sonnet-4-6")

# Bounded writer regeneration on malformed output (non-deterministic drafts).
_WRITER_MAX_ATTEMPTS = 3

#: Measured cost of ONE Sonnet writer attempt including its tool turns (~$0.42 on
#: the B-020 acceptance runs), rounded up for headroom.
_WRITER_ATTEMPT_COST_USD = 0.45

#: The writer budget is cumulative across attempts, so the default must be able to
#: pay for every attempt the retry policy promises — otherwise a malformed first
#: draft (a normal, handled condition) starves the retry and aborts the run after
#: real money is spent (BUG-061). Derived, never hand-picked, so the two cannot
#: drift apart again.
DEFAULT_WRITER_BUDGET_USD = _WRITER_ATTEMPT_COST_USD * _WRITER_MAX_ATTEMPTS

WRITER_SYSTEM_PROMPT = """You are an Economist-style Writer renowned for sharp, witty prose with British flair.
Every article must satisfy the 10 rules below before submission. Do not read files. Write primarily
from the brief. You MAY call the `search_for_source` tool sparingly (at most 3 times per article)
to find a source for a specific claim the brief does not cover — for example to strengthen a weak
claim, anchor the opening with a recent statistic, or cite counter-evidence. Prefer the brief's
pre-vetted sources; only search when a claim genuinely needs support the brief lacks.

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


def _build_writer_prompt(topic: str, research_brief: str, style_section: str) -> str:
    """Build the Stage 3 writer user-prompt.

    The author is pinned to ``BLOG_AUTHOR`` (the single source of truth shared
    with the publication validator) so the model does not invent an author name
    that Stage 4's author contract would then reject (issue #401).
    """
    return (
        f"Write the complete Economist-style article on this topic: {topic}\n\n"
        f"Output the entire article text with YAML frontmatter at the top. "
        f"Start directly with `---` — no preamble, no commentary.\n\n"
        f"Frontmatter must include: layout, title, date, author (set exactly "
        f'to "{BLOG_AUTHOR}" — do not invent an author name), categories '
        f"(Title Case from: Quality Engineering, Software Engineering, "
        f"Test Automation, Security), "
        f"description (160 chars max), "
        f"subtitle (one line, 40 words max, that sharpens the title — a "
        f"distinct editorial angle, NOT a restatement of the description, e.g. "
        f"'What a green build hides: the payroll cost of tests that lie'), "
        f"slug (the article's URL: 4-6 lowercase hyphenated keywords, 50 "
        f"characters max, complete words only, no filler like 'the' or 'of' — "
        f"the terms a reader would actually search, e.g. "
        f"'flaky-tests-invisible-tax'. This URL is permanent and cannot be "
        f"changed after publication, so make it read as a finished phrase), "
        f"image_alt (one sentence describing the ideal editorial illustration "
        f"for accessibility — written from the article thesis, e.g. "
        f"'An Economist-style editorial illustration of a developer staring at "
        f"a dashboard filled with green checkmarks while a production server burns'), "
        f"and image_caption (40 characters max — a terse credit line, not a "
        f"sentence, e.g. 'The build is green; the budget drains').\n\n"
        f"Do NOT emit an `image:` path — the pipeline sets it from the slug.\n\n"
        f"Body length is a hard requirement. Target ~{WORD_COUNT_TARGET} words "
        f"across 3-4 body sections of roughly 220-280 words each (matching the "
        f"3-4 heading maximum above) — enough for a thesis, two or three "
        f"evidenced arguments, a counterpoint, and a decisive close. The "
        f"publication validator rejects anything under {WORD_COUNT_MIN} words, "
        f"so never come in short; if a section feels thin, deepen it with a "
        f"concrete example or data point from the brief rather than adding "
        f"another heading or filler. End with a `## References` section "
        f"containing 3+ numbered citations.\n\n"
        f"At least one paragraph in the body must reference the chart "
        f"explicitly — write something like 'as the chart shows', "
        f"'the chart makes clear', or 'the chart below illustrates'. "
        f"This is required by the publication validator.\n\n"
        f"RESEARCH BRIEF (use ONLY these sources and statistics — do NOT "
        f"invent any statistics, researcher names, or URLs):\n\n"
        f"{research_brief}"
        f"{style_section}"
    )


@dataclass
class Stage3Result:
    """Captured metrics from a Stage 3 run."""

    topic: str
    article: str
    chart_data: dict
    total_cost_usd: float
    writer_cost_usd: float
    graphics_cost_usd: float
    research_cost_usd: float
    writer_model: str
    graphics_model: str
    wall_seconds: float
    research_brief_chars: int
    article_chars: int
    stat_audit_removed: int
    writer_search_calls: int = 0  # #389: on-demand source searches the writer made
    chart_path: Path | None = None  # #403 slice 1: rendered chart PNG
    prompt_path: Path | None = None  # #403 slice 3: image-prompt artefact
    slug: str = ""  # #403 slice 3: canonical slug for downstream resume
    image_prompt: str = ""  # #403 slice 3: the prompt text itself
    hero_path: Path | None = None  # B-016b: Claude-drawn hero SVG
    hero_critique: str = (
        ""  # B-016b: unresolved composition defects (CLI exits non-zero)
    )
    hero_error: str = ""  # B-016b: why no hero exists (empty when hero_path is set)


_TITLE_FIELD_PATTERN = re.compile(r'^title:\s*["\']?(.*?)["\']?\s*$', re.MULTILINE)
_IMAGE_ALT_PATTERN = re.compile(r'^image_alt:\s*["\']?(.*?)["\']?\s*$', re.MULTILINE)
_IMAGE_CAPTION_PATTERN = re.compile(
    r'^image_caption:\s*["\']?(.*?)["\']?\s*$', re.MULTILINE
)


def _extract_frontmatter_field(article: str, pattern: re.Pattern[str]) -> str:
    """Return the first capture from ``pattern`` in the article's
    frontmatter, or ``''`` if not found. Frontmatter is the block
    between the first two ``---`` lines."""
    if not article.startswith("---"):
        return ""
    parts = article.split("---", 2)
    if len(parts) < 3:
        return ""
    match = pattern.search(parts[1])
    return match.group(1).strip() if match else ""


def _slug_for_chart(article: str, topic: str) -> str:
    """Slug for the chart PNG + image-prompt sidecar — the single canonical slug
    (B-008), shared with the article file and the in-article chart embed so they
    can never point at different filenames. Derived from the article title,
    falling back to the topic."""
    return canonical_slug(article, topic)


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


def _strip_enclosing_code_fence(text: str) -> str:
    """Unwrap an article the writer wrapped in a Markdown code fence.

    Some models emit ```` ```markdown\\n---\\n…\\n``` ```` despite the prompt
    asking for a bare article. The leading fence stops the article starting with
    ``---`` and makes ``_strip_duplicate_article`` mistake the real frontmatter
    (now at a non-zero offset) for a duplicate emission — deleting the whole body
    (BUG-041). Strip a single enclosing fence when the text opens with one.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return text
    body = stripped[first_newline + 1 :].rstrip()
    fence_close = body.rfind("```")
    if fence_close != -1:
        body = body[:fence_close].rstrip()
    return body + "\n"


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
            "Stripping duplicate article emission at offset %d",
            match.start(),
        )
        return text[: match.start()].rstrip() + "\n"
    return text


# Start of a genuine article: a ``---`` fence line immediately followed by a
# known frontmatter key. Distinguishes real frontmatter from a stray ``---``
# markdown rule the writer may drop in its preamble.
_FRONTMATTER_START = re.compile(
    r"(?m)^---[ \t]*\r?\n"
    r"(?=(?:layout|title|date|author|categories|description|image)\s*:)"
)


def _extract_article(text: str) -> str:
    """Recover the article from noisy writer output (BUG-047).

    Handles three observed writer quirks, in order:
    1. The whole article wrapped in a code fence (``_strip_enclosing_code_fence``).
    2. Conversational preamble (and/or a stray ``---`` markdown rule) before the
       real frontmatter — everything before the first genuine ``---\\n<key>:``
       block is discarded, so a preambled draft passes the well-formed check on
       the first attempt instead of forcing a budget-burning retry.
    3. A dangling trailing code fence left once a between-preamble fence opener
       is removed.

    Prose with no frontmatter at all is returned (near) unchanged so the
    downstream well-formed check still rejects it.
    """
    text = _strip_enclosing_code_fence(text)
    match = _FRONTMATTER_START.search(text)
    if match and match.start() > 0:
        text = text[match.start() :]
    text = re.sub(r"\r?\n[ \t]*```[a-zA-Z]*[ \t]*$", "", text.rstrip())
    return text.rstrip() + "\n"


def _raise_if_budget_exceeded(
    msg: ResultMessage, cost: float, max_budget_usd: float | None
) -> None:
    """The Agent SDK signals budget exhaustion by returning a ResultMessage with
    subtype="error_max_budget_usd" rather than raising. Surface it as a typed
    BudgetExceededError so callers can route a clean abort."""
    if msg.subtype != "error_max_budget_usd":
        return
    cap_str = f"${max_budget_usd:.4f}" if max_budget_usd is not None else "<unset>"
    logger.warning(
        "Agent SDK budget exceeded: cap=%s, cost_at_abort=$%.4f", cap_str, cost
    )
    raise BudgetExceededError(
        f"Agent SDK budget exceeded: cap={cap_str}, cost_at_abort=${cost:.4f}",
        budget_usd=max_budget_usd,
    )


async def _collect_text(
    prompt: str,
    system_prompt: str,
    model: str = DEFAULT_WRITER_MODEL,
    max_budget_usd: float | None = None,
    mcp_servers: dict[str, Any] | None = None,
    allowed_tools: list[str] | None = None,
    max_turns: int = 1,
) -> tuple[str, float]:
    """Run an Agent SDK query and return ``(text, cost_usd)``.

    Streaming text chunks are joined with a space when the boundary
    between two chunks looks like an unintended word concatenation
    (lowercase letter followed by uppercase letter), to avoid artefacts
    such as "OrganisationsDoubleDown" seen in the Story 1 spike output.

    By default no tools are exposed and the query runs in a single turn. Pass
    ``mcp_servers``/``allowed_tools`` with ``max_turns > 1`` to enable a tool-use
    loop (e.g. the writer's on-demand source search, #389).
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        max_turns=max_turns,
        permission_mode="bypassPermissions",
        allowed_tools=allowed_tools or [],
        mcp_servers=mcp_servers or {},
        stderr=lambda line: logger.warning("agent-sdk stderr: %s", line),
        max_budget_usd=max_budget_usd,
    )
    text_chunks: list[str] = []
    cost = 0.0
    budget_msg: ResultMessage | None = None
    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_chunks.append(block.text)
            elif isinstance(msg, ResultMessage):
                cost = float(msg.total_cost_usd or 0.0)
                if msg.subtype == "error_max_budget_usd":
                    # Break out and raise AFTER the loop (below). Raising here,
                    # mid-iteration, makes the async-for finalise the query()
                    # generator while it is still running its subprocess pump —
                    # 'aclose(): asynchronous generator is already running'
                    # then masks the real BudgetExceededError (BUG-048).
                    budget_msg = msg
                    break
    except Exception as exc:  # noqa: BLE001
        # The subscription CLI raises (rather than returning a ResultMessage)
        # when it hits the turn cap. If the agent already emitted text, proceed
        # with what we have rather than crashing the whole pipeline (BUG-042);
        # otherwise re-raise so a genuine failure still surfaces.
        if "maximum number of turns" in str(exc).lower() and text_chunks:
            logger.warning(
                "Agent SDK hit the turn cap; proceeding with %d collected chunk(s)",
                len(text_chunks),
            )
        else:
            raise

    # Raise the budget error here — after the async generator has closed cleanly
    # on ``break`` — so it surfaces as a typed BudgetExceededError (BUG-048).
    if budget_msg is not None:
        _raise_if_budget_exceeded(budget_msg, cost, max_budget_usd)

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
        cleaned = cleaned.removesuffix("```")
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {"specification": text}


def _ensure_chart_title(chart_data: dict, article: str, topic: str) -> dict:
    """Backfill a chart title when the graphics model omits one (BUG-043).

    The chart is required downstream, so a missing/empty ``title`` must not crash
    the render. The backfill is **data-descriptive and never the article
    headline** (per B-007): prefer the chart's own ``subtitle`` (which describes
    the data), else a neutral generic label. ``article``/``topic`` are accepted
    for signature stability but deliberately not used as the title.
    """
    title = chart_data.get("title")
    if isinstance(title, str) and title.strip():
        return chart_data
    subtitle = chart_data.get("subtitle")
    derived = (
        subtitle.strip()
        if isinstance(subtitle, str) and subtitle.strip()
        else "Key figures"
    )[:80]
    logger.warning("Graphics output had no chart title; backfilled %r", derived)
    return {**chart_data, "title": derived}


#: The graphics agent is as prone to malformed output as the writer, which gets
#: _WRITER_MAX_ATTEMPTS. It had none, so one bad JSON spec killed the pipeline
#: AFTER the writer had already succeeded and cost ~$0.85 (BUG-063, found by the
#: B-020 acceptance run).
_GRAPHICS_MAX_ATTEMPTS = 3


async def _graphics_with_retry(
    collect: Any,
    graphics_prompt: str,
    graphics_model: str,
    graphics_budget_usd: float | None,
    article: str,
    topic: str,
    chart_path: Path,
) -> tuple[dict, float, int]:
    """Generate a chart spec and render it, retrying a spec the renderer rejects.

    Chart failures stay fatal — a missing chart leaves a broken body embed — but
    "fatal" should mean "the agent could not produce a valid spec in N tries",
    not "the first try was malformed".

    Returns ``(chart_data, cost, attempts)``. Raises the last
    :class:`ChartRenderError` when every attempt fails.
    """
    cost = 0.0
    last_error: ChartRenderError | None = None
    prompt = graphics_prompt

    for attempt in range(1, _GRAPHICS_MAX_ATTEMPTS + 1):
        text, call_cost = await collect(
            prompt,
            GRAPHICS_AGENT_PROMPT,
            model=graphics_model,
            max_budget_usd=graphics_budget_usd,
            # Turn headroom: the subscription CLI can need >1 turn for the JSON
            # (BUG-042). Kept small — no tools are exposed for graphics.
            max_turns=4,
        )
        cost += call_cost
        chart_data = _ensure_chart_title(_parse_chart_json(text), article, topic)
        try:
            render_chart(chart_data, chart_path)
        except ChartRenderError as exc:
            last_error = exc
            logger.warning(
                "Graphics attempt %s/%s produced an unrenderable spec: %s; retrying",
                attempt,
                _GRAPHICS_MAX_ATTEMPTS,
                exc,
            )
            # Feed the renderer's own message back — without it the agent has no
            # idea what to change and simply repeats itself.
            prompt = (
                f"{graphics_prompt}\n\nYour previous chart JSON was rejected by "
                f"the renderer: {exc}\nReturn corrected JSON only."
            )
            continue
        return chart_data, cost, attempt

    assert last_error is not None
    raise last_error


async def run_stage3(
    topic: str,
    writer_budget_usd: float | None = DEFAULT_WRITER_BUDGET_USD,
    graphics_budget_usd: float | None = 0.10,
    writer_model: str = DEFAULT_WRITER_MODEL,
    graphics_model: str = DEFAULT_GRAPHICS_MODEL,
    research_mode: str = "deterministic",
    brief_override: str | None = None,
) -> Stage3Result:
    """Generate one article via the Agent SDK and return captured metrics.

    Mirrors ``Stage3Crew.kickoff`` so output is comparable.

    Args:
        topic: Article topic.
        writer_budget_usd: Hard cap on TOTAL writer cost across all attempts.
            Defaults to ``DEFAULT_WRITER_BUDGET_USD`` — one measured attempt
            (~$0.45) × ``_WRITER_MAX_ATTEMPTS`` — so the retry policy is always
            funded (BUG-061). ``None`` disables the cap.
        graphics_budget_usd: Hard cap for the graphics call. Default
            0.10 (~3× headroom over ~$0.03).
        writer_model: Model id for the Writer call. Default Sonnet 4.6
            because the Story 4 verification run showed Opus 4.7 cost
            3.4× more for a marginally LOWER score on this task. Override
            with WRITER_MODEL env var if your topic needs deeper reasoning.
        graphics_model: Model id for the Graphics call. Default Sonnet
            4.6; override with GRAPHICS_MODEL env var.

    Returns:
        Stage3Result with article text, chart dict, cost, and timing.

    """
    start = time.perf_counter()

    # Research path is deterministic by default; "deep" (#390) opts into the
    # recursive multi-hop loop; "claude_web" (B-006) is the keyless path — Claude
    # does its own web research via the Agent SDK (no Serper key). RESEARCH_MODE
    # env overrides the argument. An unrecognised value fails closed to
    # deterministic (a typo must not silently disable the expensive deep path or
    # the keyless path) and is logged so operators can confirm.
    if brief_override is not None:
        # B-012: opt-in --brief — a pre-built deep-research brief (refuted claims
        # already stripped by pipeline.load_brief_file) is used verbatim; the
        # research step is skipped entirely (no cost).
        research_brief, research_cost = brief_override, 0.0
        logger.info("Research: using supplied --brief (%d chars)", len(research_brief))
    else:
        resolved_research_mode = os.environ.get("RESEARCH_MODE", research_mode)
        if resolved_research_mode not in ("deterministic", "deep", "claude_web"):
            logger.warning(
                "Unrecognised research mode %r; using deterministic",
                resolved_research_mode,
            )
            resolved_research_mode = "deterministic"
        logger.info("Research mode: %s", resolved_research_mode)
        if resolved_research_mode == "deep":
            research_brief, research_cost = await build_deep_research_brief(topic)
        elif resolved_research_mode == "claude_web":
            research_brief, research_cost = await build_claude_web_brief(topic)
        else:
            research_brief, research_cost = build_research_brief(topic), 0.0
    logger.info("Research brief: %d chars", len(research_brief))

    style_context = _fetch_style_context(topic)
    if style_context:
        logger.info("Style memory: %d chars of exemplars", len(style_context))
        style_section = f"\n\n## Style Memory\n\n{style_context}"
    else:
        style_section = ""

    writer_prompt = _build_writer_prompt(topic, research_brief, style_section)
    # #389 hybrid research: expose a budget-capped source-search tool the writer
    # can call mid-draft. A fresh session per article isolates budget/dedupe.
    # max_turns must exceed 1 so the SDK can drive the tool-use loop.
    #
    # Bounded retry (BUG-044): the writer (esp. via the subscription CLI)
    # is non-deterministic and occasionally emits malformed output — a bare code
    # fence, or frontmatter with an empty body. Regenerate a few times before
    # giving up rather than aborting the whole run on a single bad draft. Only
    # the writer re-runs; the research brief is reused, so retries are cheap.
    #
    # The budget cap is CUMULATIVE across attempts: each attempt gets the
    # remaining budget, so total writer spend never exceeds ``writer_budget_usd``
    # even when retries happen (a spent budget makes the next attempt abort via
    # BudgetExceededError rather than overspend).
    pre_audit_article = ""
    writer_cost = 0.0
    search_session = SourceFetchSession()
    last_diagnostic = ""
    for attempt in range(1, _WRITER_MAX_ATTEMPTS + 1):
        search_session = SourceFetchSession()
        research_server = create_sdk_mcp_server(
            "research", tools=[build_search_tool(search_session)]
        )
        remaining_budget = (
            None
            if writer_budget_usd is None
            else max(0.0, writer_budget_usd - writer_cost)
        )
        # Never dispatch a retry the budget cannot pay for (BUG-061). The SDK
        # would abort it anyway, but generically — the operator needs the
        # arithmetic and the name of the knob, not "budget exceeded".
        if (
            attempt > 1
            and remaining_budget is not None
            and remaining_budget < _WRITER_ATTEMPT_COST_USD
        ):
            raise BudgetExceededError(
                f"Writer attempt {attempt} of {_WRITER_MAX_ATTEMPTS} needs "
                f"~${_WRITER_ATTEMPT_COST_USD:.2f} but only "
                f"${remaining_budget:.2f} is left of --writer-budget "
                f"${writer_budget_usd:.2f} (spent ${writer_cost:.2f}). Raise "
                f"--writer-budget to at least "
                f"${DEFAULT_WRITER_BUDGET_USD:.2f} to fund every attempt.",
                budget_usd=writer_budget_usd,
            )
        raw_writer_output, attempt_cost = await _collect_text(
            writer_prompt,
            WRITER_SYSTEM_PROMPT,
            model=writer_model,
            max_budget_usd=remaining_budget,
            mcp_servers={"research": research_server},
            allowed_tools=["mcp__research__search_for_source"],
            # Each search costs 2 turns (the tool_use, then consuming the
            # tool_result); plus the initial draft and 1 turn of headroom.
            max_turns=2 * search_session.max_calls + 2,
        )
        writer_cost += attempt_cost
        # _extract_article (BUG-047) unwraps a fence AND strips conversational
        # preamble / stray rules before the frontmatter, so a preambled draft
        # passes the well-formed check on this attempt instead of retrying.
        candidate = _strip_duplicate_article(_extract_article(raw_writer_output))
        # Require opening ---, a closing --- on its own line, and a non-empty
        # body. re.DOTALL so the frontmatter block can contain newlines.
        _fm_match = re.match(r"^---\r?\n.*?\r?\n---\r?\n(.+)", candidate, re.DOTALL)
        body_is_empty = _fm_match is None or not _fm_match.group(1).strip()
        if candidate.startswith("---") and not body_is_empty:
            pre_audit_article = candidate
            break
        last_diagnostic = (
            f"(starts_with_dash={candidate.startswith('---')!r}, "
            f"body_empty={body_is_empty!r}). First 120 chars: {candidate[:120]!r}"
        )
        logger.warning(
            "Writer attempt %d/%d produced malformed output %s; retrying",
            attempt,
            _WRITER_MAX_ATTEMPTS,
            last_diagnostic,
        )
    else:
        raise MalformedArticleError(
            f"Writer output is not a well-formed article after "
            f"{_WRITER_MAX_ATTEMPTS} attempts {last_diagnostic}"
        )

    if search_session.calls_made:
        logger.info(
            "Writer made %d on-demand source search(es)", search_session.calls_made
        )
    # Append writer-fetched sources to the brief so the stat audit does not
    # strip statistics the writer legitimately cited from them (#389).
    research_brief = research_brief + search_session.brief_supplement()

    audited = _audit_article_stats(pre_audit_article, research_brief)
    stat_audit_removed = pre_audit_article.count(".") - audited.count(".")
    article = _normalize_paragraphs(audited)

    graphics_prompt = (
        "Generate the chart JSON for this article. Output a single valid "
        "JSON object with keys: title, subtitle, data (list of "
        "{metric, value, unit, color}), colors (navy/burgundy hex map), "
        "dimensions (width/height). No commentary, no markdown fences.\n\n"
        "One axis, one measure: every data item must be the same kind of measure "
        "on the same scale (all percentages, OR all counts — never mixed), within "
        "~1 order of magnitude, with correct units. Pick the single measure that "
        "best carries the article's argument.\n\n"
        f"Article excerpt:\n{article[:2500]}"
    )
    # #403 slice 1: render the chart spec to a real PNG. Render failures stay
    # fatal (a missing chart leaves a broken body embed) but are now retried
    # first — one malformed spec used to kill the run after the writer had
    # already succeeded (BUG-063).
    slug = _slug_for_chart(article, topic)
    chart_path = Path("output/charts") / f"{slug}.png"
    chart_data, graphics_cost, graphics_attempts = await _graphics_with_retry(
        _collect_text,
        graphics_prompt,
        graphics_model,
        graphics_budget_usd,
        article,
        topic,
        chart_path,
    )
    logger.info("Rendered chart: %s (attempt %s)", chart_path, graphics_attempts)

    # #403 slice 3: synthesise the ChatGPT-handoff prompt and persist it
    # as a sibling artefact. The prompt is built from the article's own
    # image_alt + image_caption fields (already LLM-generated visual
    # concepts) wrapped in the Economist hard constraints. Failure is
    # non-fatal — the operator can still ship chart-only via --no-image.
    image_prompt = ""
    prompt_path: Path | None = None
    try:
        title = _extract_frontmatter_field(article, _TITLE_FIELD_PATTERN) or topic
        image_alt = _extract_frontmatter_field(article, _IMAGE_ALT_PATTERN)
        image_caption = _extract_frontmatter_field(article, _IMAGE_CAPTION_PATTERN)
        if image_alt:
            image_prompt = compose_prompt(
                title=title, image_alt=image_alt, image_caption=image_caption
            )
            prompt_path = Path("output/posts") / f"{slug}.image_prompt.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(image_prompt)
            logger.info("Wrote image prompt artefact: %s", prompt_path)
        else:
            logger.info(
                "No image_alt in frontmatter — skipping prompt artefact "
                "(article will need --no-image at resume time)"
            )
    except PromptSynthError as exc:
        logger.warning("Image prompt synthesis skipped (%s)", exc)

    # B-016b: Claude draws the hero from that same brief. The blog REQUIRES a
    # resolvable `image:` (both its validators error without one), so an article
    # with no hero is unpublishable — but a hero problem must never corrupt or
    # abort an otherwise good article. So this never raises: the outcome is
    # reported on Stage3Result and the CLI owns the exit code.
    hero_path: Path | None = None
    hero_critique = ""
    hero_error = ""
    if image_prompt:
        # Imported at call time: hero_author needs _collect_text from this module,
        # so a module-level import here would be a cycle.
        from src.agent_sdk.hero_author import author_hero_svg_async

        # Async entry point: run_stage3 is already inside an event loop, so the
        # sync wrapper would raise and silently lose the hero.
        hero = await author_hero_svg_async(
            brief=image_prompt,
            slug=slug,
            images_dir=HERO_IMAGES_DIR,
            model=graphics_model,
        )
        hero_path, hero_critique, hero_error = hero.path, hero.critique, hero.error
        if hero_path:
            logger.info("Drew hero: %s", hero_path)
        else:
            logger.warning("No hero drawn (%s)", hero_error or "unknown reason")
    else:
        hero_error = "no image_alt in frontmatter, so there was no brief to draw from"
        logger.warning("Skipping hero: %s", hero_error)

    elapsed = time.perf_counter() - start

    return Stage3Result(
        topic=topic,
        article=article,
        chart_data=chart_data,
        total_cost_usd=writer_cost + graphics_cost + research_cost,
        writer_cost_usd=writer_cost,
        graphics_cost_usd=graphics_cost,
        research_cost_usd=research_cost,
        writer_model=writer_model,
        graphics_model=graphics_model,
        wall_seconds=elapsed,
        research_brief_chars=len(research_brief),
        article_chars=len(article),
        stat_audit_removed=max(stat_audit_removed, 0),
        writer_search_calls=search_session.calls_made,
        chart_path=chart_path,
        prompt_path=prompt_path,
        slug=slug,
        image_prompt=image_prompt,
        hero_path=hero_path,
        hero_critique=hero_critique,
        hero_error=hero_error,
    )


def main() -> None:
    """CLI entrypoint — write Stage 3 artefacts to ``logs/spike/``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    topic = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "developer productivity in the age of AI coding agents"
    )
    print(f"Running Stage 3 on topic: {topic}")
    result = asyncio.run(run_stage3(topic))

    out_dir = Path("logs/spike")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agent_sdk_article.md").write_text(result.article)
    (out_dir / "agent_sdk_chart.json").write_bytes(
        orjson.dumps(result.chart_data, option=orjson.OPT_INDENT_2),
    )
    metrics = {
        k: v for k, v in asdict(result).items() if k not in ("article", "chart_data")
    }
    (out_dir / "agent_sdk_metrics.json").write_bytes(
        orjson.dumps(metrics, option=orjson.OPT_INDENT_2),
    )

    print(
        f"Stage 3 complete: ${result.total_cost_usd:.4f} "
        f"(writer ${result.writer_cost_usd:.4f}, "
        f"graphics ${result.graphics_cost_usd:.4f}), "
        f"{result.wall_seconds:.1f}s, "
        f"{result.article_chars} chars.",
    )
    print("Artefacts: logs/spike/agent_sdk_{article.md,chart.json,metrics.json}")


if __name__ == "__main__":
    main()
