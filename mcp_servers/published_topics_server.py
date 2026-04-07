#!/usr/bin/env python3
"""
Published Topics MCP Server

Exposes the published article archive as MCP tools so that topic
deduplication works from both interactive (Claude Code) and automated
(pipeline) contexts.

Transport: stdio (FastMCP)

Tools:
    query_published_topics    — semantic similarity search over the archive
    is_topic_duplicate        — check whether a topic has already been published
    search_published_topics   — semantic similarity search with threshold filter
    index_published_article   — add / update an article in the archive
    get_archive_stats         — summary statistics about the archive

Usage:
    python -m mcp_servers.published_topics_server
    # or
    python mcp_servers/published_topics_server.py
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from scripts.article_archive import ArticleArchive

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "published-topics",
    instructions=(
        "Query the published article archive to detect duplicate topics before "
        "commissioning new content. Use query_published_topics for similarity "
        "search and is_topic_duplicate for a structured duplicate verdict."
    ),
)

# Module-level archive instance (lazy-initialised on first use)
_archive: ArticleArchive | None = None


def _get_archive() -> ArticleArchive:
    """Return the shared :class:`ArticleArchive`, creating it on first call."""
    global _archive  # noqa: PLW0603
    if _archive is None:
        _archive = ArticleArchive()
    return _archive


def _set_archive_for_testing(archive: ArticleArchive) -> None:
    """Replace the shared archive instance (for tests only).

    Allows tests to inject an in-memory ChromaDB-backed archive so that no
    persistent state is written to disk.
    """
    global _archive  # noqa: PLW0603
    _archive = archive


@mcp.tool()
def query_published_topics(
    query: str,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Return the *n_results* most similar published articles for a topic query.

    Unlike ``search_published_topics``, this tool applies no similarity
    threshold — it always returns the closest matches sorted by descending
    cosine similarity.

    Args:
        query: Topic description or title to search for.
        n_results: Maximum number of results to return. Default 5.

    Returns:
        List of matching articles, each with title, thesis, date,
        categories, file_path, and similarity score.
        On failure returns an empty list.
    """
    try:
        return _get_archive().search(query, threshold=0.0, n_results=n_results)
    except Exception as exc:
        logger.error("query_published_topics failed: %s", exc)
        return []


@mcp.tool()
def is_topic_duplicate(topic: str) -> dict[str, Any]:
    """
    Check whether a proposed topic has already been covered.

    Thresholds:
      - similarity > 0.8  -> duplicate (is_duplicate=True)
      - 0.6 <= similarity <= 0.8 -> warning zone
      - similarity < 0.6  -> safe to publish

    Args:
        topic: Proposed article topic or title to check for duplication.

    Returns:
        dict with:
          - is_duplicate (bool): True when the best match exceeds 0.8.
          - confidence (float): Similarity score of the closest match (0-1).
          - similar_articles (list): Up to 5 similar articles with metadata.
          - warning (bool): True when 0.6 <= confidence <= 0.8.
        On failure, returns is_duplicate=False, confidence=0.0 with an error key.
    """
    try:
        similar = _get_archive().search(topic, threshold=0.6, n_results=5)
        confidence = similar[0]["similarity"] if similar else 0.0
        return {
            "is_duplicate": confidence > 0.8,
            "confidence": confidence,
            "similar_articles": similar,
            "warning": 0.6 <= confidence <= 0.8,
        }
    except Exception as exc:
        logger.error("is_topic_duplicate failed: %s", exc)
        return {
            "is_duplicate": False,
            "confidence": 0.0,
            "similar_articles": [],
            "warning": False,
            "error": str(exc),
        }


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
        threshold: Minimum similarity score (0-1). Default 0.6.
        n_results: Maximum number of results to return. Default 5.

    Returns:
        List of matching articles, each with title, thesis, date,
        categories, file_path, and similarity score.
        On failure returns an empty list.
    """
    try:
        return _get_archive().search(query, threshold=threshold, n_results=n_results)
    except Exception as exc:
        logger.error("search_published_topics failed: %s", exc)
        return []


@mcp.tool()
def index_published_article(
    title: str,
    thesis: str,
    date: str,
    categories: str,
    file_path: str,
) -> dict[str, Any]:
    """
    Index a published article in the archive.

    Args:
        title: Article title.
        thesis: Central argument or summary (used as embedding text).
        date: Publication date (YYYY-MM-DD).
        categories: Comma-separated category tags.
        file_path: Relative path to the article file.

    Returns:
        dict with success (bool), id (str), and total_indexed (int).
        On failure, includes an error (str) field instead of total_indexed.
    """
    try:
        # index_article returns a success/error dict rather than raising, so
        # this try/except specifically guards _get_archive() initialisation
        # failures (e.g. import errors) that would otherwise propagate.
        return _get_archive().index_article(title, thesis, date, categories, file_path)
    except Exception as exc:
        logger.error("index_published_article failed: %s", exc)
        return {"success": False, "error": str(exc), "id": ""}


@mcp.tool()
def get_archive_stats() -> dict[str, Any]:
    """
    Return statistics about the published article archive.

    Returns:
        dict with available (bool), total_articles (int),
        date_range (dict with earliest/latest), and
        category_distribution (dict mapping category to count).
        On failure, returns available=False with an error key.
    """
    try:
        return _get_archive().get_stats()
    except Exception as exc:
        logger.error("get_archive_stats failed: %s", exc)
        return {"available": False, "total_articles": 0, "error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
