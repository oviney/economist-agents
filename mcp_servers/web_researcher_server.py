#!/usr/bin/env python3
"""Web Researcher MCP Server.

Exposes web search (Serper API), Google Scholar search, arXiv academic
search, and page-fetching as MCP tools so any agent in the pipeline can
retrieve fresh sources.

Transport: stdio (default FastMCP behaviour).

Required environment variable:
    SERPER_API_KEY — API key for Serper.dev web search and Scholar search.

Usage (stdio):
    python -m mcp_servers.web_researcher_server

Tools exposed:
    search_web(query, num_results)            — Serper-powered Google web search.
    search_google_scholar(query, max_results) — Google Scholar via Serper API.
    search_arxiv(query, max_results)          — arXiv academic paper search.
    fetch_page(url)                           — Fetch and extract plain text from URL.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Module-level imports from scripts — kept here so tests can patch them.
try:
    from scripts.arxiv_search import ArxivSearcher, search_arxiv_for_topic
except ImportError:  # pragma: no cover
    ArxivSearcher = None  # type: ignore[assignment,misc]
    search_arxiv_for_topic = None  # type: ignore[assignment]

try:
    from scripts.google_search import GoogleSearcher as _GoogleSearcher
except ImportError:  # pragma: no cover
    _GoogleSearcher = None  # type: ignore[assignment]

mcp = FastMCP("web-researcher")


# ---------------------------------------------------------------------------
# Tool: search_web
# ---------------------------------------------------------------------------


@mcp.tool()
def search_web(query: str, num_results: int = 5) -> list[dict[str, str]]:
    """Search the web via Serper API and return structured results.

    Args:
        query: Search query string.
        num_results: Maximum number of results to return (default 5).

    Returns:
        List of dicts with keys ``title``, ``url``, ``snippet``.
        Returns a single-element list with an ``error`` key on failure.
    """
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        logger.error("SERPER_API_KEY environment variable is not set")
        return [{"error": "SERPER_API_KEY environment variable is not set"}]

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10,
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
                }
            )
        return results

    except requests.HTTPError as exc:
        logger.error("Serper API HTTP error: %s", exc)
        return [{"error": f"HTTP error from Serper API: {exc}"}]
    except requests.RequestException as exc:
        logger.error("Serper API request failed: %s", exc)
        return [{"error": f"Request failed: {exc}"}]
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error in search_web: %s", exc)
        return [{"error": f"Unexpected error: {exc}"}]


# ---------------------------------------------------------------------------
# Tool: search_google_scholar
# ---------------------------------------------------------------------------


@mcp.tool()
def search_google_scholar(
    query: str,
    max_results: int = 5,
    year_start: int | None = None,
    year_end: int | None = None,
) -> list[dict[str, Any]]:
    """Search Google Scholar for academic papers via Serper API.

    Targets recent publications so that research sources are fresh.
    When ``year_start`` and ``year_end`` are both ``None`` the current and
    previous calendar year are used automatically.

    Args:
        query: Search query string (academic terms work best).
        max_results: Maximum number of results to return (default 5).
        year_start: Filter papers published from this year onward.
        year_end: Filter papers published up to this year.

    Returns:
        List of dicts with keys ``title``, ``url``, ``snippet``, ``year``,
        ``authors``, ``cited_by``, ``source``.
        Returns a single-element list with an ``error`` key on failure.
    """
    if _GoogleSearcher is None:
        return [{"error": "google_search module is not available"}]

    from datetime import datetime as _dt

    current_year = _dt.now().year
    effective_year_start = year_start if year_start is not None else current_year - 1
    effective_year_end = year_end if year_end is not None else current_year

    try:
        searcher = _GoogleSearcher()
        return searcher.search_scholar(
            query=query,
            num_results=max_results,
            year_start=effective_year_start,
            year_end=effective_year_end,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Google Scholar search failed: %s", exc)
        return [{"error": f"Google Scholar search failed: {exc}"}]


# ---------------------------------------------------------------------------
# Tool: search_arxiv
# ---------------------------------------------------------------------------


@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search arXiv for academic papers.

    Args:
        query: Search query string.
        max_results: Maximum number of papers to return (default 5).

    Returns:
        List of dicts with keys ``title``, ``authors``, ``abstract``,
        ``url``, ``published``.
        Returns a single-element list with an ``error`` key on failure.
    """
    if search_arxiv_for_topic is None or ArxivSearcher is None:
        return [{"error": "arxiv package is not installed"}]

    try:
        raw: dict[str, Any] = search_arxiv_for_topic(query, max_papers=max_results)
    except Exception as exc:  # noqa: BLE001
        logger.error("arXiv search failed: %s", exc)
        return [{"error": f"arXiv search failed: {exc}"}]

    if not raw.get("success"):
        error_msg = raw.get("error") or "arXiv search returned no results"
        logger.error("arXiv search unsuccessful: %s", error_msg)
        return [{"error": error_msg}]

    # Try to get full paper metadata via ArxivSearcher
    try:
        searcher = ArxivSearcher(max_results=max_results, days_back=365)
        paper_list = searcher.search_recent_papers(query)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch detailed paper list: %s", exc)
        paper_list = []

    if paper_list:
        results: list[dict[str, Any]] = []
        for paper in paper_list[:max_results]:
            results.append(
                {
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "abstract": paper.get("abstract", ""),
                    "url": paper.get("url", ""),
                    "published": paper.get("published", ""),
                }
            )
        return results

    # Fallback: return citation strings as minimal records
    citations: list[str] = raw.get("insights", {}).get("citations", [])
    if citations:
        return [
            {"title": c, "authors": [], "abstract": "", "url": "", "published": ""}
            for c in citations
        ]

    return []


# ---------------------------------------------------------------------------
# Tool: fetch_page
# ---------------------------------------------------------------------------


@mcp.tool()
def fetch_page(url: str) -> str:
    """Fetch a URL and return its plain-text content.

    Strips HTML tags via a simple regex approach so that agents receive
    readable text rather than raw markup.

    Args:
        url: The URL to fetch.

    Returns:
        Plain-text representation of the page, or an error message string.
    """
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; EconomistAgentsBot/1.0; "
                    "+https://github.com/oviney/economist-agents)"
                )
            },
            timeout=15,
        )
        response.raise_for_status()
        html = response.text

        # Strip script / style blocks (handles optional whitespace before closing >)
        html = re.sub(
            r"<(script|style)[^>]*>.*?<\s*/\s*(script|style)\s*>",
            " ",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    except requests.HTTPError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
        return f"Error: HTTP error fetching page: {exc}"
    except requests.RequestException as exc:
        logger.error("Request error fetching %s: %s", url, exc)
        return f"Error: Failed to fetch page: {exc}"
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching %s: %s", url, exc)
        return f"Error: Unexpected error: {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
