#!/usr/bin/env python3
"""Ground Topic Scout trend research in free, keyless evidence.

Collects dated trend evidence from the Hacker News front page (official HN
Firebase API — no key, no cost). The previous Google Web Search path (via
``scripts/google_search.py`` / Serper) was removed: research must never depend
on a pay-per-use API.

Exports
-------
build_grounded_trend_context(focus_area=None) -> str
    Collects HN front-page evidence and returns a prompt-ready text block that
    includes titles, URLs, and dates.

TrendEvidence
    TypedDict describing the shape of collected evidence.

Usage::

    from scripts.topic_trend_grounding import build_grounded_trend_context

    context = build_grounded_trend_context(focus_area="test automation")
    # Pass *context* into the scout prompt in place of the old LLM trends.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TypedDict

import orjson
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
# Constants
# ---------------------------------------------------------------------------


_HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
_HN_MAX_ITEMS = 5
_HN_TIMEOUT = 5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
        story_ids: list[int] = orjson.loads(resp.content)[:max_items]

        items: list[EvidenceItem] = []
        for sid in story_ids:
            item_resp = requests.get(
                _HN_ITEM_URL.format(item_id=sid),
                timeout=_HN_TIMEOUT,
            )
            item_resp.raise_for_status()
            story = orjson.loads(item_resp.content)
            if not story:
                continue
            # Skip items with missing or zero timestamps (would format as
            # 1970-01-01 and pollute evidence with incorrect dates).
            ts = story.get("time", 0)
            if not ts:
                continue
            items.append(
                EvidenceItem(
                    title=story.get("title", ""),
                    url=story.get("url", ""),
                    snippet="",
                    date=datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d"),
                    source="hacker_news",
                ),
            )
        logger.info("Fetched %d HN front-page stories", len(items))
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch HN stories: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def gather_trend_evidence(include_hn: bool = True) -> list[TrendEvidence]:
    """Collect structured trend evidence from free sources.

    Currently the Hacker News front page is the only no-cost trend signal (the
    pay-per-use Google/Serper search was removed). ``include_hn=False`` yields
    an empty list.

    Args:
        include_hn: When ``True``, fetch Hacker News front-page stories.

    Returns:
        A list with at most one :class:`TrendEvidence` entry (the HN front
        page), each containing a ``query`` key and a ``results`` list of
        :class:`EvidenceItem`.

    """
    evidence: list[TrendEvidence] = []

    if include_hn:
        hn_stories = _fetch_hn_top_stories()
        if hn_stories:
            evidence.append(
                TrendEvidence(query="Hacker News front page", results=hn_stories),
            )

    return evidence


def build_grounded_trend_context(
    focus_area: str | None = None,
    include_hn: bool = True,
) -> str:
    """Build a prompt-ready text block with dated trend evidence.

    Primary entry point for ``topic_scout.py``. Collects free trend evidence
    (Hacker News front page) and formats it for the scout prompt.

    Args:
        focus_area: Retained for API compatibility. No longer drives queries —
            the free HN front-page signal is not query-scoped.
        include_hn: Include Hacker News front-page stories.

    Returns:
        Formatted string containing dated evidence with URLs, suitable for
        injection into an LLM prompt. Returns a fallback message when no
        evidence could be collected.

    """
    evidence = gather_trend_evidence(include_hn=include_hn)
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
            "_No live evidence could be collected (Hacker News may be "
            "unreachable). Rely on your training knowledge but flag any claims "
            "as [UNVERIFIED]._\n"
        )

    # Determine which sources contributed evidence.
    sources = {item["source"] for e in evidence for item in e["results"]}
    source_label = ", ".join(sorted(sources)) if sources else "live search"

    lines: list[str] = [
        f"## Live Trend Evidence ({source_label})\n",
        f"_Collected {total_items} items on "
        f"{datetime.now(tz=UTC).strftime('%Y-%m-%d')}.  "
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
