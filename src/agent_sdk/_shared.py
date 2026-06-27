"""Shared helpers used by both Stage 3 and Stage 4 Agent SDK runners.

These functions used to live in ``src/crews/stage3_crew.py`` and
``src/crews/stage4_crew.py``. They are pure Python (no CrewAI, no LLM)
and were moved here so the Agent SDK runners can be used after CrewAI
is deleted (epic #308, story #313).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class EmptyResearchBriefError(RuntimeError):
    """Base error for any condition that produces a research brief with zero usable sources.

    Concrete cause is conveyed by subclass. CLI catches all three and prints
    a tailored, traceback-free message before exiting non-zero.
    """


class SearchProvidersFailedError(EmptyResearchBriefError):
    """Both research providers errored (HTTP error, network failure, or library exception).

    Likely transient (provider outage) or environmental (bad/missing API key,
    misformatted query rejected at provider). Retry or rephrase the topic.
    """


class SearchProvidersEmptyError(EmptyResearchBriefError):
    """Providers responded successfully but returned zero usable sources for the topic.

    The topic is likely too narrow, too recent, or phrased in a way that
    matches nothing in arXiv/Google Scholar/Google Web. Try broadening or
    rephrasing it as a noun-phrase rather than a question.
    """


class BudgetExceededError(RuntimeError):
    """Raised when an Agent SDK call hits its ``max_budget_usd`` cap.

    The SDK signals budget exhaustion by emitting a ``ResultMessage`` with
    ``subtype="error_max_budget_usd"`` and ``is_error=True`` (see
    ``claude_agent_sdk.types.ClaudeAgentOptions.max_budget_usd`` docstring).
    The Stage 3 runner inspects that signal and re-raises this typed error so
    callers (notably ``flow.py:generate_content``) can route a clean abort
    instead of crashing with an unhandled exception.
    """

    def __init__(self, message: str, *, budget_usd: float | None = None) -> None:
        self.budget_usd = budget_usd
        super().__init__(message)


_DEFAULT_VISION_MODEL = "claude-sonnet-4-6"
_ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "claude-haiku-4-5",
        "claude-sonnet-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-7",
    }
)


# ─── Stage 3: research brief + stat audit ──────────────────────────────

GRAPHICS_AGENT_PROMPT = """
You are a Data Visualization Specialist.
Your goal is to take complex data and describe how it should be visualized.

Create clear, accurate charts that follow Economist style guidelines:
- Clean, minimalist design
- Proper zone boundaries (red bar, title, chart, x-axis, source)
- Inline labels instead of legends
- High-quality export (PNG, 300 DPI)
"""


_STAT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(%|per\s*cent|billion|million|thousand|trillion|fold|times\b|x\b)",
    re.IGNORECASE,
)


def _extract_stats(text: str) -> list[str]:
    """Return numeric claims with surrounding context for fuzzy matching."""
    stats: list[str] = []
    for match in _STAT_PATTERN.finditer(text):
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)
        context = text[start:end].strip()
        context = re.sub(r"\s+", " ", context)
        stats.append(context)
    return stats


def build_research_brief(topic: str) -> str:
    """Run arXiv + Google searches and format the result for the Writer.

    No LLM is involved; this is the deterministic research path that
    replaces the original CrewAI Research Agent (which hallucinated
    sources from training data instead of using injected tool results).

    Raises one of the typed ``EmptyResearchBriefError`` subclasses if the
    combined source count across all providers is zero — preventing an
    unsourced LLM call.
    """
    raw, diagnostics = _run_web_searches(topic)
    total_sources = sum(diagnostics["source_counts"].values())
    if total_sources == 0:
        any_failed = any(diagnostics["provider_failed"].values())
        msg = (
            f"No usable sources returned for topic {topic!r}. "
            f"provider_failed={diagnostics['provider_failed']}, "
            f"source_counts={diagnostics['source_counts']}."
        )
        logger.debug("EmptyResearchBriefError: %s", msg)
        if any_failed:
            raise SearchProvidersFailedError(msg)
        raise SearchProvidersEmptyError(msg)
    return "\n".join(
        [
            f"# Research Brief: {topic}",
            "",
            "The following sources were found via live web search.",
            "Use ONLY statistics and claims from these sources.",
            "If you need a statistic not listed below, tag it [NEEDS SOURCE].",
            "Do NOT invent statistics, researcher names, or URLs.",
            "Every sentence containing a percentage, multiplier, or quantified claim must name the source inline (e.g. 'According to Gartner, 2024, …' or '…, per the ASQ report (2023)').",
            "",
            raw,
        ],
    )


def _run_web_searches(topic: str) -> tuple[str, dict[str, Any]]:
    """Combine multi-provider search results for ``topic`` (#388).

    Fans out to arXiv, Google (via Serper, when ``SERPER_API_KEY`` is set),
    Semantic Scholar (no key required), Brave (when ``BRAVE_API_KEY`` is
    set), and Tavily (when ``TAVILY_API_KEY`` is set). Each provider is
    isolated in its own try/except so a single outage / missing key
    cannot poison the others. Diagnostics shape:

        {
            "source_counts": {
                "arxiv": int, "google_web": int, "google_scholar": int,
                "semantic_scholar": int, "brave": int, "tavily": int,
            },
            "provider_failed": {
                "arxiv": bool, "google": bool, "semantic_scholar": bool,
                "brave": bool, "tavily": bool,
            },
        }

    A provider is ``failed`` if it raised, returned ``success=False``,
    or returned only error-stub results. A provider that ran cleanly
    but returned zero results is **not** marked failed (lets the gate
    distinguish topic-too-narrow from provider-outage).
    """
    results: list[str] = []
    source_counts: dict[str, int] = {
        "arxiv": 0,
        "google_web": 0,
        "google_scholar": 0,
        "semantic_scholar": 0,
        "brave": 0,
        "tavily": 0,
    }
    provider_failed: dict[str, bool] = {
        "arxiv": False,
        "google": False,
        "semantic_scholar": False,
        "brave": False,
        "tavily": False,
    }

    # ── arXiv ────────────────────────────────────────────────────────
    try:
        from scripts.arxiv_search import search_arxiv_for_topic

        arxiv = search_arxiv_for_topic(topic, max_papers=5)
        if not arxiv.get("success", False):
            provider_failed["arxiv"] = True
        else:
            papers = arxiv.get("insights", {}).get("papers_analyzed", [])
            if papers:
                source_counts["arxiv"] = len(papers[:5])
                results.append("## arXiv Papers")
                for p in papers[:5]:
                    results.append(
                        f"- [{p.get('title', 'Unknown')}]({p.get('url', '')})\n"
                        f"  Authors: {p.get('authors', 'Unknown')}\n"
                        f"  Published: {p.get('published', 'N/A')}\n"
                        f"  Key finding: {p.get('key_insight', 'N/A')}",
                    )
    except Exception as exc:
        logger.warning("arXiv search failed: %s", exc)
        provider_failed["arxiv"] = True

    # ── Google (Serper) ──────────────────────────────────────────────
    try:
        from scripts.google_search import search_google_for_topic

        google = search_google_for_topic(topic, max_results=5)
        if not google.get("success", False):
            provider_failed["google"] = True
        else:
            # search_web and search_scholar in scripts/google_search.py catch
            # requests.HTTPError internally and return [{"error": "..."}] as
            # the result list. search_google_for_topic does NOT filter those
            # out, so success=True can coexist with error-stub results. Filter
            # them here so they don't get counted as real sources or rendered
            # as fake bullets with "Unknown" titles.
            web = [r for r in google.get("web_results", []) if "error" not in r]
            if web:
                source_counts["google_web"] = len(web[:5])
                results.append("\n## Web Sources (Google)")
                for r in web[:5]:
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('link', '')})\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}\n"
                        f"  Date: {r.get('date', 'N/A')}",
                    )
            scholar = [r for r in google.get("scholar_results", []) if "error" not in r]
            if scholar:
                source_counts["google_scholar"] = len(scholar[:5])
                results.append("\n## Google Scholar")
                for r in scholar[:5]:
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('link', '')})\n"
                        f"  Year: {r.get('year', 'N/A')}\n"
                        f"  Cited by: {r.get('cited_by', 'N/A')}",
                    )
            # If google reported success but ALL results were error stubs that
            # we just filtered out, the provider effectively failed. Mark it
            # so the gate categorises this as SearchProvidersFailedError
            # (transient/environmental) rather than SearchProvidersEmptyError
            # (topic too narrow).
            if (
                not web
                and not scholar
                and (google.get("web_results") or google.get("scholar_results"))
            ):
                provider_failed["google"] = True
    except Exception as exc:
        logger.warning("Google search failed: %s", exc)
        provider_failed["google"] = True

    # ── Semantic Scholar ─────────────────────────────────────────────
    try:
        from scripts.semantic_scholar_search import search_semantic_scholar_for_topic

        ss = search_semantic_scholar_for_topic(topic, max_papers=5)
        if not ss.get("success", False):
            provider_failed["semantic_scholar"] = True
        else:
            papers = ss.get("papers", [])
            if papers:
                source_counts["semantic_scholar"] = len(papers[:5])
                results.append("\n## Semantic Scholar")
                for p in papers[:5]:
                    citation_str = (
                        f" — cited {p['citation_count']}x"
                        if p.get("citation_count")
                        else ""
                    )
                    results.append(
                        f"- [{p.get('title', 'Unknown')}]({p.get('url', '')})\n"
                        f"  Authors: {p.get('authors', 'Unknown')} "
                        f"({p.get('year', 'N/A')}){citation_str}\n"
                        f"  DOI: {p.get('doi', '')}\n"
                        f"  Abstract: {p.get('abstract', '')}",
                    )
    except Exception as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)
        provider_failed["semantic_scholar"] = True

    # ── Brave ────────────────────────────────────────────────────────
    try:
        from scripts.brave_search import search_brave_for_topic

        brave = search_brave_for_topic(topic, max_results=5)
        if not brave.get("success", False):
            provider_failed["brave"] = True
        else:
            br = brave.get("results", [])
            if br:
                source_counts["brave"] = len(br[:5])
                results.append("\n## Web Sources (Brave)")
                for r in br[:5]:
                    age_str = f" ({r['age']})" if r.get("age") else ""
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('url', '')})"
                        f"{age_str}\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}",
                    )
    except Exception as exc:
        logger.warning("Brave search failed: %s", exc)
        provider_failed["brave"] = True

    # ── Tavily ───────────────────────────────────────────────────────
    try:
        from scripts.tavily_search import search_tavily_for_topic

        tavily = search_tavily_for_topic(topic, max_results=5)
        if not tavily.get("success", False):
            provider_failed["tavily"] = True
        else:
            tv = tavily.get("results", [])
            if tv:
                source_counts["tavily"] = len(tv[:5])
                results.append("\n## Web Sources (Tavily, AI-ranked)")
                answer = tavily.get("answer", "")
                if answer:
                    results.append(f"_Synthesis:_ {answer}\n")
                for r in tv[:5]:
                    score_str = f" (score {r['score']:.2f})" if r.get("score") else ""
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('url', '')})"
                        f"{score_str}\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}",
                    )
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        provider_failed["tavily"] = True

    diagnostics: dict[str, Any] = {
        "source_counts": source_counts,
        "provider_failed": provider_failed,
    }
    return "\n".join(results), diagnostics


def audit_article_stats(article: str, research_brief: str) -> str:
    """Strip sentences whose numeric claims are not in the research brief."""
    if article.strip().startswith("---"):
        parts = article.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]
        else:
            return article
    else:
        frontmatter = ""
        body = article

    ref_match = re.search(r"\n## References", body)
    if ref_match:
        pre_refs = body[: ref_match.start()]
        refs_section = body[ref_match.start() :]
    else:
        pre_refs = body
        refs_section = ""

    norm_research = research_brief.lower()
    sentences = re.split(r"(?<=[.!?])\s+", pre_refs)
    kept: list[str] = []
    removed_count = 0

    for sentence in sentences:
        stats_in_sentence = list(_STAT_PATTERN.finditer(sentence))
        if not stats_in_sentence:
            kept.append(sentence)
            continue

        has_fabricated = False
        for match in stats_in_sentence:
            num_with_unit = match.group(0).strip().lower()
            raw_num = match.group(1)
            if num_with_unit not in norm_research and raw_num not in norm_research:
                has_fabricated = True
                break

        if has_fabricated:
            removed_count += 1
        else:
            kept.append(sentence)

    if removed_count > 0:
        logger.info(
            "Stat audit: removed %d sentence(s) with unverified stats",
            removed_count,
        )

    cleaned_body = " ".join(kept) + refs_section
    return frontmatter + cleaned_body


# ─── Stage 4: deterministic editorial fixes ────────────────────────────

_BRITISH_SPELLING: dict[str, str] = {
    "organization": "organisation",
    "Organization": "Organisation",
    "optimize": "optimise",
    "Optimize": "Optimise",
    "optimization": "optimisation",
    "analyze": "analyse",
    "Analyze": "Analyse",
    "analyzing": "analysing",
    "utilize": "utilise",
    "utilizing": "utilising",
    "recognize": "recognise",
    "customize": "customise",
    "prioritize": "prioritise",
    "standardize": "standardise",
    "modernize": "modernise",
    "behavior": "behaviour",
    "favor": "favour",
    "favorable": "favourable",
    "color": "colour",
    "labor": "labour",
}

_BANNED_PHRASES: list[str] = [
    "game-changer",
    "game changer",
    "paradigm shift",
    "at the end of the day",
]

_HEDGING_PHRASES: list[str] = [
    "it would be misguided",
    "one might",
    "it is worth noting",
    "it should be noted",
    "it is important to",
    "it is not a minor footnote",
    "further complicating matters",
    "invites closer scrutiny",
    "in practical terms",
    "One suspects",
    "if you find yourself",
    "it is clear that",
    "it remains to be seen",
]

_VERBOSE_PADDING: list[str] = [
    "it goes without saying",
    "needless to say",
    "as mentioned earlier",
    "as noted above",
    "as stated above",
]

_BANNED_CLOSINGS: list[str] = [
    "In conclusion",
    "To conclude",
    "In summary",
    "remains to be seen",
    "only time will tell",
    "The journey ahead",
    "will rest on",
    "depends on",
    "the key is",
    "to summarise",
    "One suspects",
]

_BANNED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bleverage\b(?=\s+(?:the|our|their|its|this|that|these|those))",
            re.IGNORECASE,
        ),
        "use",
    ),
]

_CATEGORY_NORMALIZATION: dict[str, str] = {
    "quality engineering": "Quality Engineering",
    "quality-engineering": "Quality Engineering",
    "software engineering": "Software Engineering",
    "software-engineering": "Software Engineering",
    "test automation": "Test Automation",
    "test-automation": "Test Automation",
    "security": "Security",
}


def _normalize_category_casing(frontmatter: str) -> str:
    """Normalize category values to the blog's title-case contract."""
    lines = frontmatter.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("categories:"):
            for raw_value, canonical in _CATEGORY_NORMALIZATION.items():
                lines[i] = re.sub(
                    re.escape(raw_value),
                    canonical,
                    lines[i],
                    flags=re.IGNORECASE,
                )
            break
    return "\n".join(lines)


def _truncate_description(frontmatter: str, max_chars: int = 160) -> str:
    """Truncate description/summary to ``max_chars`` at a word boundary."""
    match = re.search(
        r'^((?:description|summary):\s*)(["\']?)(.+?)(\2\s*)$',
        frontmatter,
        re.MULTILINE,
    )
    if not match:
        return frontmatter
    prefix, quote, value, _suffix = (
        match.group(1),
        match.group(2),
        match.group(3),
        match.group(4),
    )
    if len(value) <= max_chars:
        return frontmatter
    truncated = value[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return frontmatter.replace(match.group(0), f"{prefix}{quote}{truncated}{quote}")


def _auto_embed_chart(article: str) -> str:
    """Insert a chart embed before References if one is missing."""
    if "![" in article and "/assets/charts/" in article:
        return article

    slug_match = re.search(r"image:\s*/assets/images/([^.\s]+)", article)
    if not slug_match:
        return article

    slug = slug_match.group(1)
    chart_embed = f"\n![Chart](/assets/charts/{slug}.png)\n"

    ref_match = re.search(r"\n## References", article)
    if ref_match:
        pos = ref_match.start()
        return article[:pos] + chart_embed + article[pos:]
    return article.rstrip() + "\n" + chart_embed


def _enforce_heading_limit(article: str, max_headings: int = 4) -> str:
    """Merge the shortest section when body heading count exceeds the limit."""
    if article.startswith("---"):
        parts = article.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]
        else:
            frontmatter = ""
            body = article
    else:
        frontmatter = ""
        body = article

    while True:
        lines = body.split("\n")
        heading_indices: list[int] = [
            i
            for i, line in enumerate(lines)
            if line.startswith("## ") and line.strip() != "## References"
        ]

        if len(heading_indices) <= max_headings:
            break

        section_lengths: list[tuple[int, int]] = []
        for idx, h_idx in enumerate(heading_indices):
            next_h = (
                heading_indices[idx + 1]
                if idx + 1 < len(heading_indices)
                else len(lines)
            )
            section_lengths.append((next_h - h_idx, h_idx))

        mergeable = section_lengths[1:]
        if not mergeable:
            break

        shortest = min(mergeable, key=lambda x: x[0])
        del lines[shortest[1]]
        body = "\n".join(lines)

    return frontmatter + body


def apply_editorial_fixes(article: str, current_date: str | None = None) -> str:
    """Apply British spelling, banned-phrase removal, and frontmatter cleanup.

    When ``current_date`` is ``None`` the article's date frontmatter is
    left untouched. Pass an explicit YYYY-MM-DD string to overwrite it.
    """
    text = article
    for american, british in _BRITISH_SPELLING.items():
        text = text.replace(american, british)
    for phrase in _BANNED_PHRASES:
        text = re.compile(re.escape(phrase), re.IGNORECASE).sub("", text)
    for pattern, replacement in _BANNED_PATTERNS:
        text = pattern.sub(replacement, text)

    lines = text.split("\n")
    in_code_block = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block:
            lines[i] = line.replace("!", ".")
    text = "\n".join(lines)
    text = text.replace("..", ".")

    if current_date and text.startswith("---"):
        text = re.sub(
            r"^(---\n.*?date:\s*)\S+(.*?\n---)",
            rf"\g<1>{current_date}\g<2>",
            text,
            count=1,
            flags=re.DOTALL,
        )

    text = re.sub(r"\s*\[NEEDS SOURCE\]", "", text)
    text = re.sub(r"\s*\[UNVERIFIED\]", "", text)
    text = re.sub(r"\s*\[REPLACE[-_]?ME\]", "", text, flags=re.IGNORECASE)

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            if "layout:" not in fm:
                fm = "\nlayout: post" + fm
            if "author:" not in fm:
                from scripts.publication_validator import BLOG_AUTHOR

                fm = fm.rstrip() + f'\nauthor: "{BLOG_AUTHOR}"\n'
            if "categories:" not in fm:
                fm = fm.rstrip() + '\ncategories: ["Quality Engineering"]\n'
            fm = _normalize_category_casing(fm)
            fm = _truncate_description(fm)
            text = "---" + fm + "---" + parts[2]

    text = _auto_embed_chart(text)
    text = _enforce_heading_limit(text)
    text = re.sub(r"  +", " ", text)

    for phrase in _HEDGING_PHRASES:
        text = re.compile(re.escape(phrase), re.IGNORECASE).sub("", text)
    for phrase in _VERBOSE_PADDING:
        text = re.compile(re.escape(phrase), re.IGNORECASE).sub("", text)
    text = re.sub(r"  +", " ", text)

    return text


# ─── Other shared bits the runners reach into ──────────────────────────


def parse_research_for_verification(research_text: str) -> dict[str, Any]:
    """Parse research output into the citation_verifier input shape."""
    data_points: list[dict[str, Any]] = []
    links = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", research_text)
    for text_label, url in links:
        idx = research_text.find(url)
        if idx == -1:
            continue
        window = research_text[max(0, idx - 200) : idx + 200]
        stats = re.findall(r"\d+(?:\.\d+)?%", window)
        stat_text = ", ".join(stats) if stats else text_label
        data_points.append(
            {
                "url": url,
                "stat": stat_text,
                "source": text_label,
                "verified": True,
            },
        )
    return {"data_points": data_points}


# ─── Vision refinement: Claude grounds image_alt / image_caption ────────

_MAX_IMAGE_BYTES = 4_000_000  # ~4 MB — Anthropic API hard limit for base64


async def refine_image_metadata(
    image_path: str,
    draft_alt: str,
    draft_caption: str,
) -> dict[str, str]:
    """Ground image_alt and image_caption against the actual generated image.

    The writer drafts both fields from the article thesis before the image
    exists.  Once DALL-E produces the image this function passes it to Claude
    vision to refine the text against what is actually visible, returning more
    accurate alt text and a tighter editorial caption.

    Uses ``anthropic.AsyncAnthropic`` so the call is non-blocking inside the
    async pipeline.  Fails gracefully (returns writer drafts) when:
    - ``ANTHROPIC_API_KEY`` is absent
    - The image file is missing or exceeds 4 MB
    - The API call raises any exception (including JSON parse failure)

    Args:
        image_path: Path to the generated image file.
        draft_alt: ``image_alt`` draft from the writer agent.
        draft_caption: ``image_caption`` draft from the writer agent.

    Returns:
        Dict with ``image_alt`` and ``image_caption`` keys.
    """
    import base64
    import json as _stdlib_json
    import os
    from pathlib import Path as _Path

    fallback = {"image_alt": draft_alt, "image_caption": draft_caption}

    from scripts.llm_client import resolve_anthropic_auth

    if not resolve_anthropic_auth():
        logger.warning(
            "No Anthropic credentials (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / "
            "ant profile) — skipping vision refinement",
        )
        return fallback

    path = _Path(image_path)
    if not path.exists():
        logger.warning("Image not found at %s — skipping vision refinement", image_path)
        return fallback

    if path.stat().st_size > _MAX_IMAGE_BYTES:
        logger.warning(
            "Image %s is %.1f MB — exceeds 4 MB API limit, skipping vision refinement",
            image_path,
            path.stat().st_size / 1_000_000,
        )
        return fallback

    try:
        from scripts.llm_client import create_async_anthropic_client

        suffix = path.suffix.lower().lstrip(".")
        media_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(suffix, "image/png")
        image_data = base64.standard_b64encode(path.read_bytes()).decode()

        vision_model = os.environ.get("VISION_MODEL", _DEFAULT_VISION_MODEL)
        if vision_model not in _ALLOWED_MODELS:
            logger.warning(
                "VISION_MODEL=%r is not in the allowlist — falling back to default",
                vision_model,
            )
            vision_model = _DEFAULT_VISION_MODEL
        client = create_async_anthropic_client()
        response = await client.messages.create(
            model=vision_model,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "This is the hero image for an Economist-style article.\n\n"
                                f"Writer's draft alt text: {draft_alt}\n"
                                f"Writer's draft caption: {draft_caption}\n\n"
                                "Refine both to match what is *actually visible* in the image. "
                                "Return JSON only:\n"
                                '{"image_alt": "<one sentence for screen readers>", '
                                '"image_caption": "<one punchy editorial sentence>"}'
                            ),
                        },
                    ],
                }
            ],
        )
        raw = response.content[0].text.strip()
        refined = _stdlib_json.loads(raw)
        return {
            "image_alt": refined.get("image_alt", draft_alt),
            "image_caption": refined.get("image_caption", draft_caption),
        }
    except Exception as exc:
        logger.warning("Vision refinement failed (%s) — using writer drafts", exc)
        return fallback
