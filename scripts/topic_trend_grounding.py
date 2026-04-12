#!/usr/bin/env python3
"""Ground Topic Scout trend research in live web search.

Replaces the plain ``call_llm()`` trend-research step in ``topic_scout.py``
with dated evidence from Google Web Search (via ``scripts/google_search.py``)
and optional Hacker News front-page scraping.

Exports
-------
build_grounded_trend_context(focus_area=None) -> str
    Runs dated search queries, collects evidence, and returns a prompt-ready
    text block that includes titles, URLs, dates, and snippets.

TrendEvidence
    TypedDict describing the shape of evidence returned per query.

Usage::

    from scripts.topic_trend_grounding import build_grounded_trend_context

    context = build_grounded_trend_context(focus_area="test automation")
    # Pass *context* into the scout prompt in place of the old LLM trends.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, TypedDict

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class EvidenceItem(TypedDict):
    """A single piece of trend evidence from a web search result."""

    title: str
    url: str
    snippet: str
    date: str
    source: str


class TrendEvidence(TypedDict):
    """Evidence dict returned by :func:`gather_trend_evidence`."""

    query: str
    results: list[EvidenceItem]


# ---------------------------------------------------------------------------
# Constants – default search queries
# ---------------------------------------------------------------------------

_CURRENT_YEAR: int = datetime.now().year

_DEFAULT_QUERIES: list[str] = [
    f"quality engineering {_CURRENT_YEAR} announcements",
    f"AI testing tool release {_CURRENT_YEAR}",
    f"DevSecOps survey {_CURRENT_YEAR}",
    f"platform engineering Backstage release {_CURRENT_YEAR}",
    f"SRE conference {_CURRENT_YEAR}",
    f"software testing trends {_CURRENT_YEAR}",
    f"observability OpenTelemetry {_CURRENT_YEAR}",
]

_HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
_HN_MAX_ITEMS = 10
_HN_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_searcher() -> Any:
    """Create a ``GoogleSearcher`` instance.

    Returns ``None`` when the ``SERPER_API_KEY`` environment variable is not
    set (the caller should log a warning and skip web search).
    """
    if not os.environ.get("SERPER_API_KEY"):
        return None

    # Import lazily to keep module importable even when google_search has
    # heavy optional deps.
    from google_search import GoogleSearcher  # noqa: E402

    return GoogleSearcher()


def _run_query(searcher: Any, query: str, num_results: int = 5) -> list[EvidenceItem]:
    """Execute a single web-search query and normalise results.

    Args:
        searcher: ``GoogleSearcher`` instance.
        query: Search query string.
        num_results: Maximum results to return.

    Returns:
        List of :class:`EvidenceItem` dicts (may be empty on error).
    """
    raw = searcher.search_web(
        query=query,
        num_results=num_results,
        year_start=_CURRENT_YEAR,
    )

    items: list[EvidenceItem] = []
    for r in raw:
        if "error" in r:
            logger.warning("Search error for '%s': %s", query, r["error"])
            continue
        items.append(
            EvidenceItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                date=r.get("date", ""),
                source=r.get("source", "google_search"),
            )
        )
    return items


def _fetch_hn_top_stories(max_items: int = _HN_MAX_ITEMS) -> list[EvidenceItem]:
    """Fetch current Hacker News front-page stories.

    Uses the official HN Firebase API (no auth required).  Returns an empty
    list on any failure so the caller can degrade gracefully.

    Args:
        max_items: Maximum number of stories to return.

    Returns:
        List of :class:`EvidenceItem` dicts.
    """
    try:
        resp = requests.get(_HN_TOP_STORIES_URL, timeout=_HN_TIMEOUT)
        resp.raise_for_status()
        story_ids: list[int] = resp.json()[:max_items]

        items: list[EvidenceItem] = []
        for sid in story_ids:
            item_resp = requests.get(
                _HN_ITEM_URL.format(item_id=sid), timeout=_HN_TIMEOUT
            )
            item_resp.raise_for_status()
            story = item_resp.json()
            if not story:
                continue
            items.append(
                EvidenceItem(
                    title=story.get("title", ""),
                    url=story.get("url", ""),
                    snippet="",
                    date=datetime.fromtimestamp(
                        story.get("time", 0)
                    ).strftime("%Y-%m-%d"),
                    source="hacker_news",
                )
            )
        logger.info("Fetched %d HN front-page stories", len(items))
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch HN stories: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def gather_trend_evidence(
    queries: list[str] | None = None,
    include_hn: bool = True,
    num_results_per_query: int = 5,
) -> list[TrendEvidence]:
    """Run web searches and return structured trend evidence.

    Args:
        queries: Search queries to run.  Defaults to :data:`_DEFAULT_QUERIES`.
        include_hn: When ``True``, also fetch Hacker News front-page stories.
        num_results_per_query: Maximum results per query.

    Returns:
        List of :class:`TrendEvidence` dicts, one per query (plus one for HN
        if *include_hn* is ``True``).  Each element contains a ``query`` key
        and a ``results`` list of :class:`EvidenceItem`.
    """
    if queries is None:
        queries = list(_DEFAULT_QUERIES)

    evidence: list[TrendEvidence] = []

    searcher = _get_searcher()
    if searcher is None:
        logger.warning(
            "SERPER_API_KEY not set — web search disabled; "
            "trend grounding will be limited to HN stories (if enabled)"
        )
    else:
        for q in queries:
            results = _run_query(searcher, q, num_results=num_results_per_query)
            evidence.append(TrendEvidence(query=q, results=results))
            logger.info(
                "Query '%s' returned %d evidence items", q, len(results)
            )

    if include_hn:
        hn_stories = _fetch_hn_top_stories()
        if hn_stories:
            evidence.append(
                TrendEvidence(query="Hacker News front page", results=hn_stories)
            )

    return evidence


def build_grounded_trend_context(
    focus_area: str | None = None,
    include_hn: bool = True,
    num_results_per_query: int = 5,
) -> str:
    """Build a prompt-ready text block with dated trend evidence.

    This is the primary entry point for ``topic_scout.py``.  It runs web
    searches, collects evidence, and formats everything into a structured
    text block that the scout prompt can consume directly.

    Args:
        focus_area: Optional focus area to add extra targeted queries.
        include_hn: Include Hacker News front-page stories.
        num_results_per_query: Maximum results per query.

    Returns:
        Formatted string containing dated evidence with URLs, suitable for
        injection into an LLM prompt.  Returns a fallback message when no
        evidence could be collected.
    """
    queries = list(_DEFAULT_QUERIES)

    # Add focus-specific queries when a focus area is provided.
    if focus_area:
        queries.extend(
            [
                f"{focus_area} {_CURRENT_YEAR} trends",
                f"{focus_area} {_CURRENT_YEAR} announcements",
            ]
        )

    evidence = gather_trend_evidence(
        queries=queries,
        include_hn=include_hn,
        num_results_per_query=num_results_per_query,
    )

    return format_evidence_as_prompt(evidence)


def format_evidence_as_prompt(evidence: list[TrendEvidence]) -> str:
    """Format collected evidence into a prompt-ready text block.

    Args:
        evidence: List of :class:`TrendEvidence` dicts as returned by
            :func:`gather_trend_evidence`.

    Returns:
        Formatted string.  Returns a fallback note when *evidence* contains
        no items.
    """
    total_items = sum(len(e["results"]) for e in evidence)
    if total_items == 0:
        return (
            "## Live Trend Evidence\n\n"
            "_No live evidence could be collected (API keys may be missing). "
            "Rely on your training knowledge but flag any claims as "
            "[UNVERIFIED]._\n"
        )

    lines: list[str] = [
        "## Live Trend Evidence (Web Search Results)\n",
        f"_Collected {total_items} items on "
        f"{datetime.now().strftime('%Y-%m-%d')}.  "
        "Use these DATED sources to ground your topic recommendations. "
        "Cite specific titles, dates, and URLs when proposing topics._\n",
    ]

    for entry in evidence:
        if not entry["results"]:
            continue
        lines.append(f"### Query: {entry['query']}\n")
        for item in entry["results"]:
            date_str = f" ({item['date']})" if item["date"] else ""
            lines.append(f"- **{item['title']}**{date_str}")
            if item["url"]:
                lines.append(f"  URL: {item['url']}")
            if item["snippet"]:
                lines.append(f"  > {item['snippet']}")
            lines.append("")  # blank line between items

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)
    focus = sys.argv[1] if len(sys.argv) > 1 else None
    context = build_grounded_trend_context(focus_area=focus)
    print(context)
