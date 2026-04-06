#!/usr/bin/env python3
"""
Published Topics MCP Server

Exposes the published article archive as MCP tools so that topic
deduplication works from both interactive (Claude Code) and automated
(pipeline) contexts.

Transport: stdio (FastMCP)

Tools:
    search_published_topics   — semantic similarity search over the archive
    index_published_article   — add / update an article in the archive
    get_archive_stats         — summary statistics about the archive

Usage:
    python -m mcp_servers.published_topics_server
    # or
    python mcp_servers/published_topics_server.py
"""

import logging
from typing import Any

from fastmcp import FastMCP

from scripts.article_archive import ArticleArchive

logger = logging.getLogger(__name__)

mcp = FastMCP("published-topics")

# Module-level archive instance (lazy-initialised on first use)
_archive: ArticleArchive | None = None


def _get_archive() -> ArticleArchive:
    """Return the shared :class:`ArticleArchive`, creating it on first call."""
    global _archive
    if _archive is None:
        _archive = ArticleArchive()
    return _archive


@mcp.tool()
def search_published_topics(
    query: str,
    threshold: float = 0.6,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Search for published articles similar to the given topic query.

    Args:
        query: Topic description or title to search for.
        threshold: Minimum similarity score (0–1). Default 0.6.
        n_results: Maximum number of results to return. Default 5.

    Returns:
        List of matching articles, each with title, thesis, date,
        categories, file_path, and similarity score.
    """
    return _get_archive().search(query, threshold=threshold, n_results=n_results)


@mcp.tool()
def index_published_article(
    title: str,
    thesis: str,
    date: str,
    categories: str,
    file_path: str,
    summary: str = "",
) -> dict[str, Any]:
    """
    Index a published article in the archive.

    Args:
        title: Article title.
        thesis: Central argument or summary (used as embedding text).
        date: Publication date (YYYY-MM-DD).
        categories: Comma-separated category tags.
        file_path: Relative path to the article file.
        summary: Optional brief human-readable summary (one or two sentences).

    Returns:
        dict with success (bool), id (str), and total_indexed (int).
        On failure, includes an error (str) field instead of total_indexed.
    """
    try:
        doc_id = _get_archive().index_article(
            title=title,
            thesis=thesis,
            summary=summary,
            categories=categories,
            date=date,
            file_path=file_path,
        )
        return {
            "success": True,
            "id": doc_id,
            "total_indexed": _get_archive().count(),
        }
    except Exception as exc:
        logger.error("index_published_article failed: %s", exc)
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_archive_stats() -> dict[str, Any]:
    """
    Return statistics about the published article archive.

    Returns:
        dict with available (bool), total_articles (int),
        date_range (dict with earliest/latest), and
        category_distribution (dict mapping category to count).
    """
    return _get_archive().get_stats()


if __name__ == "__main__":
    mcp.run()
