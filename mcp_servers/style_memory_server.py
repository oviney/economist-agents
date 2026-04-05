#!/usr/bin/env python3
"""
Style Memory MCP Server

Exposes ChromaDB-backed style pattern retrieval as MCP tools so that any agent
can query past article patterns for voice consistency.

Tools:
    query_style_memory  – returns similar past article excerpts
    add_to_style_memory – indexes a new article into the vector store

Transport: stdio (FastMCP)
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import chromadb
    import chromadb.errors

    _UPSERT_ERRORS: tuple[type[Exception], ...] = (
        chromadb.errors.ChromaError,
        ValueError,
        RuntimeError,
        OSError,
    )
except ImportError:
    _UPSERT_ERRORS = (ValueError, RuntimeError, OSError)

from mcp.server.fastmcp import FastMCP

from src.tools.style_memory_tool import StyleMemoryTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server & shared tool instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "style-memory",
    instructions=(
        "Query and update the ChromaDB-backed style memory store that holds "
        "excerpts from Gold Standard Economist articles. Use query_style_memory "
        "to retrieve relevant past patterns and add_to_style_memory to index "
        "new articles."
    ),
)

# Lazy singleton – created on first use so that tests can inject their own
# StyleMemoryTool instance via _set_tool_for_testing().
_tool: StyleMemoryTool | None = None


def _get_tool() -> StyleMemoryTool:
    """Return the shared StyleMemoryTool instance (creates it on first call)."""
    global _tool  # noqa: PLW0603
    if _tool is None:
        _tool = StyleMemoryTool(persist_directory=".chromadb")
    return _tool


def _set_tool_for_testing(tool: StyleMemoryTool) -> None:
    """
    Replace the shared tool instance.

    This is intended for tests only – it allows injecting an in-memory
    ChromaDB instance so that tests leave no persistent state on disk.
    """
    global _tool  # noqa: PLW0603
    _tool = tool


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def query_style_memory(query: str, n_results: int = 3) -> list[dict[str, Any]]:
    """
    Query the style memory store for relevant past article excerpts.

    Args:
        query: Natural language query describing the style pattern of interest,
               e.g. "how to handle banned phrases" or "Economist voice examples".
        n_results: Maximum number of results to return (default: 3).

    Returns:
        A list of dicts, each containing:
          - text (str): the matched excerpt
          - score (float): distance-derived relevance score in [0, 1],
            computed as ``1 - min(L2_distance, 1.0)``; higher values indicate
            closer (more relevant) matches
          - source (str): source article filename
          - paragraph (int): paragraph index within the source article
    """
    tool = _get_tool()
    results = tool.query(query_text=query, n_results=n_results, min_score=0.0)
    logger.info(
        "query_style_memory: query=%r returned %d result(s)", query, len(results)
    )
    return results


@mcp.tool()
def add_to_style_memory(article_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Index a new article into the style memory store.

    The article is split into paragraphs (≥50 characters) and each paragraph is
    embedded and stored individually for fine-grained retrieval.

    Args:
        article_text: Full text of the article to index.
        metadata: Arbitrary key/value pairs attached to every paragraph, e.g.
                  ``{"source": "2024-01-15-ai-post.md", "author": "editor"}``.
                  Must be a flat dict of string keys and string/int/float/bool values
                  (ChromaDB restriction).

    Returns:
        A confirmation dict with keys:
          - success (bool): True when indexing succeeded
          - indexed_paragraphs (int): number of paragraphs added
          - message (str): human-readable summary
    """
    tool = _get_tool()

    if not tool.collection:
        return {
            "success": False,
            "indexed_paragraphs": 0,
            "message": "ChromaDB collection is unavailable.",
        }

    if not article_text.strip():
        return {
            "success": False,
            "indexed_paragraphs": 0,
            "message": "article_text is empty.",
        }

    paragraphs = [p.strip() for p in article_text.split("\n\n") if len(p.strip()) >= 50]

    if not paragraphs:
        return {
            "success": False,
            "indexed_paragraphs": 0,
            "message": "No paragraphs with ≥50 characters found in article_text.",
        }

    source_label = str(metadata.get("source", "")).strip()
    if not source_label:
        return {
            "success": False,
            "indexed_paragraphs": 0,
            "message": 'metadata must include a non-empty "source" key to prevent ID collisions.',
        }
    # Build unique IDs based on source + paragraph index so repeated indexing
    # of the same article is idempotent (ChromaDB upsert behaviour).
    ids = [f"mcp_{source_label}_p{i}" for i in range(len(paragraphs))]
    meta_list: list[dict[str, Any]] = [
        {**metadata, "paragraph": i} for i in range(len(paragraphs))
    ]

    try:
        tool.collection.upsert(documents=paragraphs, metadatas=meta_list, ids=ids)
        # Keep indexed_count in sync
        tool.indexed_count = tool.collection.count()
        logger.info(
            "add_to_style_memory: indexed %d paragraph(s) from source=%r",
            len(paragraphs),
            source_label,
        )
        return {
            "success": True,
            "indexed_paragraphs": len(paragraphs),
            "message": (
                f"Successfully indexed {len(paragraphs)} paragraph(s) "
                f"from source '{source_label}'."
            ),
        }
    except _UPSERT_ERRORS as exc:
        logger.error("add_to_style_memory failed: %s", exc)
        return {
            "success": False,
            "indexed_paragraphs": 0,
            "message": f"Indexing failed: {exc}",
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
