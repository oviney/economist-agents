#!/usr/bin/env python3
"""Google Search integration for the Research Agent.

Provides programmatic Google Web Search and Google Scholar search via the
Serper API, targeting the current and previous year so that research sources
are always fresh.

Required environment variable:
    SERPER_API_KEY — API key for Serper.dev (https://serper.dev)

Usage:
    from scripts.google_search import GoogleSearcher, search_google_for_topic

    # Convenience function (returns web + scholar results for a topic)
    results = search_google_for_topic("AI testing trends")

    # Direct class usage
    searcher = GoogleSearcher()
    web     = searcher.search_web("quality engineering 2026", num_results=5)
    scholar = searcher.search_scholar("test automation", num_results=5)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERPER_API_BASE = "https://google.serper.dev"
_DEFAULT_NUM_RESULTS = 5
_DEFAULT_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class GoogleSearchError(Exception):
    """Raised when a Google search call fails unrecoverably."""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class GoogleSearcher:
    """Google Web Search and Google Scholar search via the Serper API.

    Queries are automatically year-scoped to the current and previous year
    to ensure that research sources are recent.

    Args:
        api_key: Serper API key.  Defaults to the ``SERPER_API_KEY``
            environment variable.
        current_year: Override the reference year used for freshness
            filtering (defaults to the current calendar year).

    Example:
        >>> searcher = GoogleSearcher()
        >>> web_results = searcher.search_web("AI test automation 2026")
        >>> scholar_results = searcher.search_scholar("software testing automation")
    """

    def __init__(
        self,
        api_key: str | None = None,
        current_year: int | None = None,
    ) -> None:
        """Initialise GoogleSearcher.

        Args:
            api_key: Serper API key (falls back to SERPER_API_KEY env var).
            current_year: Reference year for freshness filtering (defaults to
                today's year).
        """
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "")
        self.current_year = current_year or datetime.now().year
        logger.info(
            "GoogleSearcher initialised (current_year=%d)", self.current_year
        )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def search_web(
        self,
        query: str,
        num_results: int = _DEFAULT_NUM_RESULTS,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> list[dict[str, str]]:
        """Search Google web for recent content via Serper.

        Args:
            query: Search query string.
            num_results: Maximum number of results to return (default 5).
            year_start: Include only results from this year onward.  When
                provided the year is appended to the query.
            year_end: Include only results up to this year.

        Returns:
            List of dicts with keys ``title``, ``url``, ``snippet``, ``date``,
            ``source``.  Returns a single-element list with an ``error`` key
            on failure.
        """
        if not self.api_key:
            logger.error("SERPER_API_KEY is not set")
            return [{"error": "SERPER_API_KEY environment variable is not set"}]

        search_query = self._build_query_with_years(query, year_start, year_end)

        try:
            response = requests.post(
                f"{SERPER_API_BASE}/search",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"q": search_query, "num": num_results},
                timeout=_DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            results: list[dict[str, str]] = []
            for item in data.get("organic", [])[:num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "date": item.get("date", ""),
                        "source": "google_search",
                    }
                )
            logger.info(
                "Google web search '%s' returned %d results",
                search_query,
                len(results),
            )
            return results

        except requests.HTTPError as exc:
            logger.error("Serper web search HTTP error: %s", exc)
            return [{"error": f"HTTP error from Serper API: {exc}"}]
        except requests.RequestException as exc:
            logger.error("Serper web search request failed: %s", exc)
            return [{"error": f"Request failed: {exc}"}]
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in search_web: %s", exc)
            return [{"error": f"Unexpected error: {exc}"}]

    def search_scholar(
        self,
        query: str,
        num_results: int = _DEFAULT_NUM_RESULTS,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search Google Scholar for academic papers via Serper.

        Args:
            query: Search query string (academic terms work best).
            num_results: Maximum number of results to return (default 5).
            year_start: Filter papers published from this year onward
                (``yearLow`` parameter sent to Serper).
            year_end: Filter papers published up to this year
                (``yearHigh`` parameter sent to Serper).

        Returns:
            List of dicts with keys ``title``, ``url``, ``snippet``, ``year``,
            ``authors``, ``cited_by``, ``source``.  Returns a single-element
            list with an ``error`` key on failure.
        """
        if not self.api_key:
            logger.error("SERPER_API_KEY is not set")
            return [{"error": "SERPER_API_KEY environment variable is not set"}]

        payload: dict[str, Any] = {"q": query, "num": num_results}
        if year_start is not None:
            payload["yearLow"] = year_start
        if year_end is not None:
            payload["yearHigh"] = year_end

        try:
            response = requests.post(
                f"{SERPER_API_BASE}/scholar",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=_DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            results: list[dict[str, Any]] = []
            for item in data.get("organic", [])[:num_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "year": str(item.get("year", "")),
                        "authors": item.get("authors", ""),
                        "cited_by": item.get("citedBy", 0),
                        "source": "google_scholar",
                    }
                )
            logger.info(
                "Google Scholar search '%s' returned %d results",
                query,
                len(results),
            )
            return results

        except requests.HTTPError as exc:
            logger.error("Serper Scholar HTTP error: %s", exc)
            return [{"error": f"HTTP error from Serper API: {exc}"}]
        except requests.RequestException as exc:
            logger.error("Serper Scholar request failed: %s", exc)
            return [{"error": f"Request failed: {exc}"}]
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in search_scholar: %s", exc)
            return [{"error": f"Unexpected error: {exc}"}]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_query_with_years(
        self,
        query: str,
        year_start: int | None,
        year_end: int | None,
    ) -> str:
        """Append year constraints to a query string for freshness.

        Args:
            query: Original query.
            year_start: Earliest year to include.
            year_end: Latest year to include (unused in query text when equal
                to current year — the ``after:`` operator is sufficient).

        Returns:
            Augmented query string.
        """
        if year_start is not None and year_end is not None and year_start == year_end:
            return f"{query} {year_start}"
        if year_start is not None:
            return f"{query} after:{year_start - 1}"
        return query


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def search_google_for_topic(
    topic: str,
    max_results: int = _DEFAULT_NUM_RESULTS,
    include_scholar: bool = True,
) -> dict[str, Any]:
    """Search Google Web and optionally Google Scholar for a research topic.

    Queries are automatically scoped to the current year and the previous
    year to maximise source freshness in line with
    ``skills/research-sourcing/SKILL.md``.

    Args:
        topic: Research topic (e.g., ``"AI test automation"``)
        max_results: Maximum results per source (default 5).
        include_scholar: Also search Google Scholar (default ``True``).

    Returns:
        Dictionary with keys:

        - ``success`` (bool)
        - ``topic`` (str)
        - ``web_results`` (list[dict])
        - ``scholar_results`` (list[dict])
        - ``current_year`` (int)
        - ``year_start`` (int)
        - ``error`` (str | None)

    Example:
        >>> results = search_google_for_topic("quality engineering")
        >>> print(results["web_results"][0]["title"])
    """
    current_year = datetime.now().year
    year_start = current_year - 1  # Previous year

    try:
        searcher = GoogleSearcher()

        # Web search: include year range in query for freshness
        web_results = searcher.search_web(
            query=f"{topic} {current_year} OR {current_year - 1}",
            num_results=max_results,
            year_start=year_start,
        )

        scholar_results: list[dict[str, Any]] = []
        if include_scholar:
            scholar_results = searcher.search_scholar(
                query=topic,
                num_results=max_results,
                year_start=year_start,
                year_end=current_year,
            )

        return {
            "success": True,
            "topic": topic,
            "web_results": web_results,
            "scholar_results": scholar_results,
            "current_year": current_year,
            "year_start": year_start,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Google search failed for topic '%s': %s", topic, exc
        )
        return {
            "success": False,
            "topic": topic,
            "web_results": [],
            "scholar_results": [],
            "current_year": current_year,
            "year_start": year_start,
            "error": str(exc),
        }


if __name__ == "__main__":  # pragma: no cover
    print("🔍 Google Search Integration Demo")
    print("=" * 50)

    demo_topic = "AI test automation quality engineering"
    result = search_google_for_topic(demo_topic, max_results=3)

    if result["success"]:
        print(f"📌 Topic: {demo_topic}")
        print(f"📅 Year range: {result['year_start']}–{result['current_year']}")

        print("\n🌐 Web Results:")
        for item in result["web_results"][:3]:
            if "error" not in item:
                print(f"  • {item['title']}")
                print(f"    {item['url']}")

        print("\n📚 Google Scholar Results:")
        for item in result["scholar_results"][:3]:
            if "error" not in item:
                print(f"  • {item['title']} ({item.get('year', 'n/a')})")
                print(f"    Authors: {item.get('authors', 'N/A')}")
    else:
        print(f"❌ Search failed: {result['error']}")
