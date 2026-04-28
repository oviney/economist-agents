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
    """
    raw = _run_web_searches(topic)
    if not raw:
        return (
            f"No web search results found for '{topic}'. "
            f"Write the article using general knowledge but tag every "
            f"statistic with [NEEDS SOURCE]."
        )
    return "\n".join(
        [
            f"# Research Brief: {topic}",
            "",
            "The following sources were found via live web search.",
            "Use ONLY statistics and claims from these sources.",
            "If you need a statistic not listed below, tag it [NEEDS SOURCE].",
            "Do NOT invent statistics, researcher names, or URLs.",
            "",
            raw,
        ]
    )


def _run_web_searches(topic: str) -> str:
    """Combine arXiv and Google search results for ``topic``."""
    results: list[str] = []
    try:
        from arxiv_search import search_arxiv_for_topic

        arxiv = search_arxiv_for_topic(topic, max_papers=5)
        if arxiv.get("success"):
            papers = arxiv.get("insights", {}).get("papers_analyzed", [])
            if papers:
                results.append("## arXiv Papers")
                for p in papers[:5]:
                    results.append(
                        f"- [{p.get('title', 'Unknown')}]({p.get('url', '')})\n"
                        f"  Authors: {p.get('authors', 'Unknown')}\n"
                        f"  Published: {p.get('published', 'N/A')}\n"
                        f"  Key finding: {p.get('key_insight', 'N/A')}"
                    )
    except Exception as exc:
        logger.warning("arXiv search failed: %s", exc)

    try:
        from google_search import search_google_for_topic

        google = search_google_for_topic(topic, max_results=5)
        if google.get("success"):
            web = google.get("web_results", [])
            if web:
                results.append("\n## Web Sources")
                for r in web[:5]:
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('link', '')})\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}\n"
                        f"  Date: {r.get('date', 'N/A')}"
                    )
            scholar = google.get("scholar_results", [])
            if scholar:
                results.append("\n## Google Scholar")
                for r in scholar[:5]:
                    results.append(
                        f"- [{r.get('title', 'Unknown')}]({r.get('link', '')})\n"
                        f"  Year: {r.get('year', 'N/A')}\n"
                        f"  Cited by: {r.get('cited_by', 'N/A')}"
                    )
    except Exception as exc:
        logger.warning("Google search failed: %s", exc)

    return "\n".join(results)


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
        logger.warning(
            "Stat audit: removed %d sentence(s) with fabricated stats",
            removed_count,
        )
        print(
            f"   🔪 Stat audit: removed {removed_count} sentence(s) with "
            f"unverified stats"
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
                    re.escape(raw_value), canonical, lines[i], flags=re.IGNORECASE
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
                fm = fm.rstrip() + '\nauthor: "Ouray Viney"\n'
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
            }
        )
    return {"data_points": data_points}
