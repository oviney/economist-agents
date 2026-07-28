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

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    query,
)

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


class ModelCallTimeoutError(RuntimeError):
    """Raised when a model call exceeds its wall-clock bound (BUG-059).

    ``max_budget_usd`` bounds what a call may SPEND; it says nothing about how
    long it may WAIT. An Agent SDK ``query()`` that stalls therefore blocked
    Stage 3 indefinitely, with no output and no way to distinguish a slow call
    from a dead one. Every collector now runs under a bound and converts the
    expiry into this typed error, which names the call so a log line is
    actionable rather than "the pipeline is stuck".
    """

    def __init__(self, label: str, timeout_s: float) -> None:
        self.label = label
        self.timeout_s = timeout_s
        super().__init__(
            f"{label} model call exceeded its {timeout_s:g}s wall-clock bound. "
            "The call produced no result and was abandoned; nothing was "
            "committed. Retry, or raise the bound if this call is legitimately "
            "this slow."
        )


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

CRITICAL — one axis, one measure (a chart is a horizontal bar chart on ONE
linear axis):
- Every bar MUST be the same kind of measure on the same scale. NEVER mix a
  percentage (e.g. 84) with a raw count (e.g. 150000) in the same chart — the
  large value swallows the axis and the small bars vanish. If the article has
  both, pick ONE coherent measure and drop the rest.
- Choose the single measure that best advances the article's thesis (the point
  the prose already makes), not a grab-bag of every number in the piece.
- Keep the largest and smallest values within ~1 order of magnitude of each
  other. If they aren't, they don't belong on the same chart.
- Set each item's `unit` correctly: a count is not a percentage. Do not label a
  raw number "%".

Economist style:
- Clean, minimalist design; inline labels instead of legends.
- Proper zone boundaries (red bar, title, chart, x-axis, source).
- High-quality export (PNG, 300 DPI).
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
    """Combine free, keyless search results for ``topic``.

    Fans out to two no-cost academic providers only — arXiv and Semantic
    Scholar (no API keys required). The pay-per-use providers (Serper/Google,
    Brave, Tavily) were removed; research must never depend on a metered
    third-party API. Each provider is isolated in its own try/except so a
    single outage cannot poison the other. Diagnostics shape:

        {
            "source_counts": {"arxiv": int, "semantic_scholar": int},
            "provider_failed": {"arxiv": bool, "semantic_scholar": bool},
        }

    A provider is ``failed`` if it raised or returned ``success=False``. A
    provider that ran cleanly but returned zero results is **not** marked
    failed (lets the gate distinguish topic-too-narrow from provider-outage).
    """
    results: list[str] = []
    source_counts: dict[str, int] = {
        "arxiv": 0,
        "semantic_scholar": 0,
    }
    provider_failed: dict[str, bool] = {
        "arxiv": False,
        "semantic_scholar": False,
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


#: Fallback tags so the >= 2 floor holds even for a single-category article.
_FALLBACK_TAGS: tuple[str, ...] = ("software-quality", "engineering")


def _derive_tags(frontmatter: str) -> str:
    """Inline-bracket ``tags:`` line satisfying the blog's post contract (BUG-057).

    ``oviney/blog``'s ``scripts/validate-posts.sh`` requires **>= 2** tags, in
    inline bracket form, **all lowercase-hyphen** (an uppercase character is a
    hard error). The pipeline never emitted the field, so the first real article
    published failed the blog's ``validate-editorial`` gate. Derive them from
    ``categories`` — already the article's own topic labels — kebab-cased, topped
    up from ``_FALLBACK_TAGS`` when a single category would leave us under the
    floor.
    """
    match = re.search(r"^categories:\s*(.+)$", frontmatter, re.MULTILINE)
    raw = match.group(1) if match else ""
    tags: list[str] = []
    for part in raw.strip().strip("[]").split(","):
        slug = re.sub(r"[^a-z0-9]+", "-", part.strip().strip("\"'").lower()).strip("-")
        if slug and slug not in tags:
            tags.append(slug)
    for fallback in _FALLBACK_TAGS:
        if len(tags) >= 2:
            break
        if fallback not in tags:
            tags.append(fallback)
    return f"tags: [{', '.join(tags)}]"


#: The only category values ``oviney/blog``'s validate-post-quality.sh accepts.
#: Anything else is a hard error there, so an off-list value is dropped rather
#: than guessed at.
_DEFAULT_CATEGORY = "Quality Engineering"

_BLOCK_LIST_ITEM = re.compile(r"^\s*-\s+(.+?)\s*$")


#: The blog hard-fails a subtitle over 60 words and warns over 40; target the
#: soft cap so a generated article lands clean rather than merely passing.
_SUBTITLE_MAX_WORDS = 40


def _derive_subtitle(frontmatter: str, body: str) -> str:
    """A ``subtitle`` value for an article whose writer omitted the field.

    ``oviney/blog`` requires ``subtitle`` — its absence is a hard ERROR, so a
    missing one must never be allowed to block an otherwise publishable article
    (the same reasoning as the description/tags guarantees above). Prefers the
    ``description``, which is already a one-line editorial summary, and falls
    back to the body's opening sentence.

    This duplicates the description on the rendered page. That is deliberate and
    is the *fallback*: the writer is prompted for a distinct subtitle, and a mild
    repetition is a far better failure mode than a rejected deploy.
    """
    match = re.search(r'^description:\s*(["\']?)(.+?)\1\s*$', frontmatter, re.MULTILINE)
    source = match.group(2) if match else _derive_description(body)
    words = source.replace('"', "").split()
    if len(words) > _SUBTITLE_MAX_WORDS:
        source = " ".join(words[:_SUBTITLE_MAX_WORDS])
    return source.strip().rstrip(".,;:")


def _normalize_category_casing(frontmatter: str) -> str:
    """Rewrite ``categories:`` into the blog's exact expected form (B-019).

    ``oviney/blog``'s ``validate-post-quality.sh`` parses the line by splitting
    on ``", "``, so the value must be an **inline, double-quoted** list —
    ``categories: ["Quality Engineering", "Test Automation"]``. An unquoted list
    reads as a single invalid category and hard-fails the gate; a block-style
    YAML list is not detected at all.

    Values are mapped through :data:`_CATEGORY_NORMALIZATION`; anything outside
    the blog's four accepted values is dropped, falling back to
    :data:`_DEFAULT_CATEGORY` when nothing survives.
    """
    lines = frontmatter.split("\n")
    for i, line in enumerate(lines):
        if not line.strip().startswith("categories:"):
            continue

        raw = line.split(":", 1)[1].strip()
        end = i + 1
        if not raw:
            # Block-style list: consume the "- item" lines that follow.
            items = []
            while end < len(lines) and (m := _BLOCK_LIST_ITEM.match(lines[end])):
                items.append(m.group(1))
                end += 1
        else:
            items = raw.strip("[]").split(",")

        canonical: list[str] = []
        for item in items:
            value = _CATEGORY_NORMALIZATION.get(item.strip().strip("\"'").lower())
            if value and value not in canonical:
                canonical.append(value)
        if not canonical:
            canonical = [_DEFAULT_CATEGORY]

        quoted = ", ".join(f'"{value}"' for value in canonical)
        return "\n".join(lines[:i] + [f"categories: [{quoted}]"] + lines[end:])
    return frontmatter


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


#: Stop words dropped from a derived slug. Deliberately a short closed list —
#: the blog's policy says omit filler "where the slug still reads clearly", so
#: this covers articles/conjunctions/prepositions and nothing content-bearing.
_SLUG_STOP_WORDS: frozenset[str] = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "that",
        "this",
        "with",
        "as",
        "at",
        "by",
        "from",
        "it",
        "its",
        "but",
        "not",
    ]
)

#: The blog targets <=50 chars, warns from 55, and hard-fails over 60
#: (``oviney/blog`` ``docs/URL_SLUG_POLICY.md``). Deriving to the *target* keeps
#: us clear of the warning band too.
_SLUG_TARGET_CHARS = 50

#: A writer-proposed ``slug:`` is accepted only in the exact shape the blog
#: wants: lowercase alphanumerics, single hyphens, no leading/trailing hyphen.
_VALID_SLUG_FIELD = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_FIELD_PATTERN = re.compile(r'^slug:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)

#: ``Engineering's`` must slugify to ``engineering``, not ``engineering-s``.
_POSSESSIVE = re.compile(r"['’]s\b")


def _shorten_to_slug(source: str) -> str:
    """Kebab-case ``source`` and shorten it to the blog's slug policy.

    Complete words only — the policy exists because an upstream tool once cut
    slugs mid-word (``…-and-sustai``), and those URLs are permanently indexed.
    So we drop whole trailing words rather than characters.
    """
    text = _POSSESSIVE.sub("", source)
    words = [
        w
        for w in re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-").split("-")
        if w and w not in _SLUG_STOP_WORDS
    ]
    while words and len("-".join(words)) > _SLUG_TARGET_CHARS:
        words.pop()
    if words:
        return "-".join(words)
    # A title of nothing but stop words: keep them rather than return nothing,
    # still bounded by the target.
    bare = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return bare[:_SLUG_TARGET_CHARS].rstrip("-")


def canonical_slug(article: str, fallback: str) -> str:
    """The single slug shared by the article file, the chart PNG, the chart
    embed, and the image-prompt sidecar (B-008).

    Sources, in order:

    1. An explicit ``slug:`` frontmatter field, when it already matches the
       blog's shape and length. The writer proposes it (B-019) because a
       mechanically-shortened title tends to end on a dangling word, and the URL
       is permanent — ``oviney/blog`` has no ``jekyll-redirect-from``.
    2. The article's ``title``, shortened per the blog's slug policy.
    3. A kebab-cased ``fallback`` (the topic) when there is no title.

    Using one derivation everywhere prevents a chart embed from pointing at a
    PNG named from a different source (which broke in ``chart_only`` runs where
    the hero ``image:`` field is empty), and means the B-019 shortening moves
    every consumer together rather than desynchronising them.
    """
    field = _SLUG_FIELD_PATTERN.search(article)
    if field:
        proposed = field.group(1).strip()
        if _VALID_SLUG_FIELD.match(proposed) and len(proposed) <= 60:
            return proposed

    match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', article, re.MULTILINE)
    source = match.group(1) if match else fallback
    return _shorten_to_slug(source) or "article"


def describe_slug(article: str, fallback: str) -> str:
    """One-line, reviewable summary of the slug the article will publish under.

    The URL is permanent (no ``jekyll-redirect-from`` on the blog), so the
    operator needs to see it *before* publishing rather than infer it from an
    output filename.
    """
    slug = canonical_slug(article, fallback)
    field = _SLUG_FIELD_PATTERN.search(article)
    proposed = field.group(1).strip() if field else ""
    if proposed and proposed == slug:
        source = "writer-supplied"
    elif proposed:
        source = "derived from title (writer's slug rejected)"
    elif re.search(r"^title:", article, re.MULTILINE):
        source = "derived from title"
    else:
        source = "derived from topic"
    return f"slug: {slug}  ({len(slug)} chars, {source})"


def _auto_embed_chart(article: str) -> str:
    """Insert a chart embed before References if one is missing."""
    if "![" in article and "/assets/charts/" in article:
        return article

    if not re.search(r"^title:", article, re.MULTILINE):
        # No title to derive a slug from — cannot name the chart; leave as-is
        # (the mandatory-chart validator will flag it).
        return article
    slug = canonical_slug(article, "untitled")

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


#: Matches an ``image:`` frontmatter line whose value is empty or an empty
#: quoted string.
#:
#: BUG-055: a chart-only article must OMIT ``image:`` entirely rather than stamp
#: ``image: ""``. Our validator reads empty and absent identically ("no hero",
#: chart-only mode), but **Jekyll does not**: in Liquid only ``nil`` and
#: ``false`` are falsy, so an empty string satisfies the blog's
#: ``{% if page.image %}`` hero guard, ``responsive-image.html`` renders an
#: ``<img>`` with no usable ``src``, and html-proofer fails the blog's REQUIRED
#: ``build`` check with "image has no src or srcset attribute". The frontmatter
#: schema requires only layout/title/date/categories, so dropping the key is
#: safe. Hero images stay human-supplied per CLAUDE.md constraint #4.
_EMPTY_IMAGE_LINE = re.compile(r"^image:\s*(?:\"\"|''|)\s*$\n?", re.MULTILINE)

#: An ``image:`` value the writer never filled in. The Stage-3 prompt used to ask
#: for a literal ``/assets/images/SLUG.png`` — the writer cannot know the slug, so
#: the path could never resolve and hard-failed the blog's gate (B-019).
_PLACEHOLDER_IMAGE_LINE = re.compile(
    r"^image:[ \t]*[\"']?[^\n\"']*"
    r"(?:\bSLUG\b|<[^>\n]+>|\bYOUR[-_]|\bPLACEHOLDER\b|\bTODO\b)"
    r"[^\n\"']*[\"']?[ \t]*$\n?",
    re.MULTILINE,
)


def _yaml_safe(value: str, max_chars: int = 120) -> str:
    """Sanitise a string for use as a double-quoted YAML scalar."""
    cleaned = value.replace('"', "'").replace("\n", " ").strip()
    return cleaned[:max_chars]


def _derive_title(body: str) -> str:
    """Best-effort title for an article that lost its frontmatter."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return _yaml_safe(stripped[2:]) or "Quality Engineering Update"
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return _yaml_safe(stripped)
    return "Quality Engineering Update"


def _derive_description(body: str, max_chars: int = 160) -> str:
    """First sentence of the body, for a fallback SEO description."""
    prose = " ".join(
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith(("#", "!", "|", "-"))
    )
    if not prose:
        return "An Economist-style analysis."
    sentence = re.split(r"(?<=[.?])\s", prose, maxsplit=1)[0]
    return _yaml_safe(sentence, max_chars) or "An Economist-style analysis."


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
            # Strip exclamation marks (Economist style) but preserve the
            # Markdown image token "![" — otherwise "![alt](chart.png)" becomes
            # ".[alt](chart.png)" and the chart/hero embed is silently broken
            # (BUG-039). Replace "!" with "." only when not immediately
            # followed by "[".
            lines[i] = re.sub(r"!(?!\[)", ".", line)
    text = "\n".join(lines)
    text = text.replace("..", ".")

    # Strip leading whitespace once, up front, so every frontmatter check below
    # (date rewrite, reconstruction) sees a draft that starts with ``---`` when
    # it has a block. Otherwise a draft beginning with a blank line before
    # ``---`` skips the date rewrite AND gets a second block injected — a
    # double-frontmatter corruption. Only when finalizing (current_date given).
    if current_date:
        text = text.lstrip()

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

    # Deterministic frontmatter guarantee. A finalize date (``current_date``)
    # signals real pipeline usage: the article MUST leave here with a valid,
    # complete frontmatter block. A missing block or missing date is purely
    # mechanical and must never quarantine an otherwise-publishable article —
    # so we rebuild it rather than letting the validator reject it. (Leading
    # whitespace was already stripped above, so this check is robust.)
    if current_date and not text.startswith("---"):
        title = _derive_title(text)
        text = (
            f'---\nlayout: post\ntitle: "{title}"\ndate: {current_date}\n---\n\n'
        ) + text

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
                fm = fm.rstrip() + f'\ncategories: ["{_DEFAULT_CATEGORY}"]\n'
            # Canonicalise categories BEFORE deriving tags: tags are kebab-cased
            # categories, so a block-style or off-list value would otherwise leak
            # into the tags (or leave only the fallbacks). B-019.
            fm = _normalize_category_casing(fm)
            # The blog requires >=2 lowercase-hyphen tags (BUG-057). Derive them
            # after categories are guaranteed so there is always a source.
            if not re.search(r"^tags:", fm, re.MULTILINE):
                fm = fm.rstrip() + "\n" + _derive_tags(fm) + "\n"
            if current_date and "date:" not in fm:
                fm = fm.rstrip() + f"\ndate: {current_date}\n"
            # No `image:` injection: a chart-only article omits the key rather
            # than stamping an empty value that breaks the blog build (BUG-055).
            # Strip an empty one the writer may have emitted — and likewise a
            # placeholder path, which cannot resolve and fails the blog's gate
            # (B-019). Absent is safe; broken is not.
            fm = _EMPTY_IMAGE_LINE.sub("", fm)
            fm = _PLACEHOLDER_IMAGE_LINE.sub("", fm)
            if current_date and "description:" not in fm:
                fm = fm.rstrip() + f'\ndescription: "{_derive_description(parts[2])}"\n'
            # ``subtitle`` is required by the blog and was never emitted (B-019).
            # Derived after description so there is always a source; the writer
            # is asked for a distinct one, this only guarantees the gate passes.
            if current_date and not re.search(r"^subtitle:", fm, re.MULTILINE):
                fm = fm.rstrip() + f'\nsubtitle: "{_derive_subtitle(fm, parts[2])}"\n'
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
    exists.  Once the hero image exists this function has Claude inspect it (via
    the Agent SDK's ``Read`` tool, which renders images) and refine the text
    against what is actually visible, returning more accurate alt text and a
    tighter editorial caption.

    Keyless (B-006): runs through ``claude_agent_sdk.query()`` on the Claude
    subscription — no ``ANTHROPIC_API_KEY`` and no ``anthropic`` client. Fails
    gracefully (returns writer drafts) when:
    - the image file is missing or exceeds 4 MB
    - the SDK call raises, returns no text, or returns non-JSON

    Args:
        image_path: Path to the generated image file.
        draft_alt: ``image_alt`` draft from the writer agent.
        draft_caption: ``image_caption`` draft from the writer agent.

    Returns:
        Dict with ``image_alt`` and ``image_caption`` keys.
    """
    import json as _stdlib_json
    import os
    import re as _re
    from pathlib import Path as _Path

    fallback = {"image_alt": draft_alt, "image_caption": draft_caption}

    path = _Path(image_path)
    if not path.exists():
        logger.warning("Image not found at %s — skipping vision refinement", image_path)
        return fallback

    if path.stat().st_size > _MAX_IMAGE_BYTES:
        logger.warning(
            "Image %s is %.1f MB — exceeds 4 MB limit, skipping vision refinement",
            image_path,
            path.stat().st_size / 1_000_000,
        )
        return fallback

    vision_model = os.environ.get("VISION_MODEL", _DEFAULT_VISION_MODEL)
    if vision_model not in _ALLOWED_MODELS:
        logger.warning(
            "VISION_MODEL=%r is not in the allowlist — falling back to default",
            vision_model,
        )
        vision_model = _DEFAULT_VISION_MODEL

    try:
        options = ClaudeAgentOptions(
            model=vision_model,
            max_turns=2,
            permission_mode="bypassPermissions",
            allowed_tools=["Read"],
            mcp_servers={},
            stderr=lambda line: logger.warning("vision stderr: %s", line),
        )
        prompt = (
            "Use the Read tool to inspect the hero image for an Economist-style "
            f"article at this path: {path}\n\n"
            f"Writer's draft alt text: {draft_alt}\n"
            f"Writer's draft caption: {draft_caption}\n\n"
            "Refine both to match what is *actually visible* in the image. "
            "Return JSON only:\n"
            '{"image_alt": "<one sentence for screen readers>", '
            '"image_caption": "<one punchy editorial sentence>"}'
        )

        text_parts: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
        raw = "".join(text_parts).strip()
        # The model may wrap the JSON in prose or a code fence; extract the object.
        match = _re.search(r"\{.*\}", raw, _re.DOTALL)
        refined = _stdlib_json.loads(match.group(0) if match else raw)
        return {
            "image_alt": refined.get("image_alt", draft_alt),
            "image_caption": refined.get("image_caption", draft_caption),
        }
    except Exception as exc:
        logger.warning("Vision refinement failed (%s) — using writer drafts", exc)
        return fallback
