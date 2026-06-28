#!/usr/bin/env python3
"""Web Researcher MCP Server.

Exposes free arXiv academic search and page-fetching as MCP tools so any
agent in the pipeline can retrieve fresh sources without a paid web-search
API.

Transport: stdio (default FastMCP behaviour).

Usage (stdio):
    python -m mcp_servers.web_researcher_server

Tools exposed:
    search_arxiv(query, max_results) — arXiv academic paper search.
    fetch_page(url)                  — Fetch and extract plain text from URL.
"""

from __future__ import annotations

import logging
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

mcp = FastMCP("web-researcher")


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
                },
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
                ),
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
