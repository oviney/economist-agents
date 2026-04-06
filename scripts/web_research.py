#!/usr/bin/env python3
"""Web Research Module — Live search for current sources.

Provides the Research Agent with access to current web data via
multiple search backends. Falls back gracefully if APIs are unavailable.

Usage:
    from scripts.web_research import search_for_sources

    sources = search_for_sources(
        topic="AI test automation ROI",
        max_results=10,
        recency_days=365,
    )
"""

import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def search_arxiv(
    query: str, max_results: int = 5, days: int = 365
) -> list[dict[str, str]]:
    """Search arXiv for recent papers.

    Args:
        query: Search query.
        max_results: Maximum results to return.
        days: Only return papers from the last N days.

    Returns:
        List of source dicts with title, authors, date, url, summary.
    """
    try:
        from scripts.arxiv_search import search_arxiv_for_topic

        result = search_arxiv_for_topic(query, max_papers=max_results)
        results = result.get("papers", [])
        sources = []
        cutoff = datetime.now() - timedelta(days=days)

        for paper in results:
            pub_date = paper.get("published", "")
            if pub_date and pub_date > cutoff.isoformat():
                sources.append(
                    {
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", ""),
                        "date": pub_date[:10],
                        "url": paper.get("url", ""),
                        "summary": paper.get("summary", "")[:200],
                        "source_type": "academic",
                    }
                )
        return sources
    except Exception as e:
        logger.warning("arXiv search failed: %s", e)
        return []


def search_google(
    query: str, max_results: int = 5, days: int = 365
) -> list[dict[str, str]]:
    """Search Google via Custom Search API or Serper API.

    Requires one of:
    - GOOGLE_API_KEY + GOOGLE_CSE_ID (Custom Search)
    - SERPER_API_KEY (Serper.dev)

    Args:
        query: Search query.
        max_results: Maximum results.
        days: Recency filter.

    Returns:
        List of source dicts.
    """
    # Try Serper first (simpler API)
    serper_key = os.environ.get("SERPER_API_KEY")
    if serper_key:
        return _search_serper(query, serper_key, max_results, days)

    # Try Google Custom Search
    google_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if google_key and cse_id:
        return _search_google_cse(query, google_key, cse_id, max_results, days)

    logger.warning(
        "No search API configured. Set SERPER_API_KEY or "
        "GOOGLE_API_KEY + GOOGLE_CSE_ID for web search."
    )
    return []


def _search_serper(
    query: str, api_key: str, max_results: int, days: int
) -> list[dict[str, str]]:
    """Search via Serper.dev API."""
    import requests

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={
                "q": f"{query} after:{_date_filter(days)}",
                "num": max_results,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        sources = []
        for item in data.get("organic", [])[:max_results]:
            sources.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "summary": item.get("snippet", ""),
                    "date": item.get("date", ""),
                    "source_type": "web",
                }
            )
        return sources
    except Exception as e:
        logger.warning("Serper search failed: %s", e)
        return []


def _search_google_cse(
    query: str, api_key: str, cse_id: str, max_results: int, days: int
) -> list[dict[str, str]]:
    """Search via Google Custom Search Engine API."""
    import requests

    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cse_id,
                "q": query,
                "num": min(max_results, 10),
                "dateRestrict": f"d{days}",
                "sort": "date",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        sources = []
        for item in data.get("items", []):
            sources.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "summary": item.get("snippet", ""),
                    "date": "",
                    "source_type": "web",
                }
            )
        return sources
    except Exception as e:
        logger.warning("Google CSE search failed: %s", e)
        return []


def _date_filter(days: int) -> str:
    """Generate a date string for N days ago."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def search_for_sources(
    topic: str,
    max_results: int = 10,
    recency_days: int = 365,
) -> list[dict[str, str]]:
    """Search multiple backends for current sources on a topic.

    Combines arXiv (academic) and Google (web) results, deduplicates,
    and sorts by recency.

    Args:
        topic: Research topic.
        max_results: Total results desired.
        recency_days: Only return sources from last N days.

    Returns:
        List of source dicts sorted by recency.
    """
    all_sources: list[dict[str, str]] = []

    # Academic sources
    arxiv_results = search_arxiv(topic, max_results=max_results // 2, days=recency_days)
    all_sources.extend(arxiv_results)

    # Web sources
    web_results = search_google(topic, max_results=max_results // 2, days=recency_days)
    all_sources.extend(web_results)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[dict[str, str]] = []
    for source in all_sources:
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(source)

    # Sort by date (most recent first)
    unique.sort(key=lambda s: s.get("date", ""), reverse=True)

    return unique[:max_results]


if __name__ == "__main__":
    results = search_for_sources("AI software testing automation 2025 2026")
    print(f"Found {len(results)} sources:")
    for r in results:
        print(f"  [{r['source_type']}] {r['title'][:60]}")
        print(f"         {r['url'][:60]}")
        print(f"         {r['date']}")
        print()
