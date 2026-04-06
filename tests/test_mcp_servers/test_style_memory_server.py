#!/usr/bin/env python3
"""
Tests for mcp_servers/style_memory_server.py

All tests use in-memory ChromaDB so that no state is persisted to disk.

Coverage targets (>80%):
  - query_style_memory tool (results returned, empty-collection path)
  - add_to_style_memory tool (success, empty text, no paragraphs, ChromaDB error)
  - _set_tool_for_testing / _get_tool helpers
  - Graceful degradation when collection is None
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Shared in-memory ChromaDB client (module-level, reused across tests)
# ---------------------------------------------------------------------------

_chroma_client: object | None = None
_fake_ef: object | None = None


def _get_shared_client() -> tuple[object, object]:
    """
    Return (chromadb_client, embedding_function), creating them once per session.

    Skips if ChromaDB is not installed.
    """
    global _chroma_client, _fake_ef  # noqa: PLW0603
    if _chroma_client is None:
        try:
            import hashlib

            import chromadb
            from chromadb.api.types import Documents, Embeddings
            from chromadb.utils.embedding_functions import EmbeddingFunction

            class _FakeEmbedding(EmbeddingFunction):
                """Deterministic, network-free embedding function for tests."""

                def __init__(self) -> None:
                    pass

                def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
                    result: Embeddings = []
                    for text in input:
                        digest = hashlib.sha256(text.encode()).hexdigest()
                        vec = [
                            int(digest[i % 64 : i % 64 + 2], 16) / 255.0
                            for i in range(384)
                        ]
                        result.append(vec)
                    return result

            _chroma_client = chromadb.EphemeralClient()
            _fake_ef = _FakeEmbedding()
        except ImportError:
            pytest.skip("ChromaDB not installed")
    return _chroma_client, _fake_ef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_in_memory_tool(archive_path: Path | None = None) -> object:
    """
    Create a StyleMemoryTool backed by a fresh in-memory ChromaDB collection.

    Each call gets its own uniquely named collection so tests are fully
    isolated even though they share a single in-memory client.  Uses a
    deterministic hash-based embedding function so no network access is needed.

    Returns the tool instance, or skips the test if ChromaDB is unavailable.
    """
    import uuid

    from src.tools.style_memory_tool import StyleMemoryTool

    client, ef = _get_shared_client()
    col_name = f"test_style_{uuid.uuid4().hex[:12]}"
    collection = client.get_or_create_collection(col_name, embedding_function=ef)

    tool = StyleMemoryTool.__new__(StyleMemoryTool)
    tool.archive_path = archive_path or Path("archived")
    tool.collection_name = col_name
    tool.persist_directory = ":memory:"
    tool.client = client
    tool.collection = collection
    tool.indexed_count = 0
    return tool


def _populate_tool(tool: object) -> None:
    """Add a few sample paragraphs so query tests have data to work with."""
    tool.collection.add(
        documents=[
            (
                "Britain's productivity puzzle deepened last quarter. "
                "Output per hour worked fell for the third consecutive period, "
                "confounding economists who had forecast a modest recovery."
            ),
            (
                "The organisation's response was unequivocal. As the chart shows, "
                "capital expenditure climbed sharply after the rate cut, reaching "
                "a five-year high by December."
            ),
            (
                "Economists favour a cautious interpretation. The data, though "
                "striking, reflect only a single quarter and could easily reverse "
                "if global demand softens."
            ),
        ],
        metadatas=[
            {"source": "productivity.md", "paragraph": 0},
            {"source": "capex.md", "paragraph": 0},
            {"source": "caution.md", "paragraph": 0},
        ],
        ids=["doc_0", "doc_1", "doc_2"],
    )
    tool.indexed_count = 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_tool():
    """Ensure each test starts with a fresh server-level tool instance."""
    import mcp_servers.style_memory_server as server

    original = server._tool
    yield
    server._tool = original


# ---------------------------------------------------------------------------
# Tests: _get_tool / _set_tool_for_testing
# ---------------------------------------------------------------------------


class TestToolHelpers:
    """Tests for the internal tool management helpers."""

    def test_set_tool_for_testing_replaces_singleton(self):
        """_set_tool_for_testing stores the provided tool as the singleton."""
        import mcp_servers.style_memory_server as server

        fake_tool = MagicMock()
        server._set_tool_for_testing(fake_tool)
        assert server._get_tool() is fake_tool

    def test_get_tool_creates_default_when_none(self):
        """_get_tool() creates a StyleMemoryTool when no tool is set."""
        import mcp_servers.style_memory_server as server

        server._tool = None
        with patch("mcp_servers.style_memory_server.StyleMemoryTool") as MockTool:
            instance = MagicMock()
            MockTool.return_value = instance
            result = server._get_tool()
            MockTool.assert_called_once_with(persist_directory=".chromadb")
            assert result is instance


# ---------------------------------------------------------------------------
# Tests: query_style_memory
# ---------------------------------------------------------------------------


class TestQueryStyleMemory:
    """Tests for the query_style_memory MCP tool."""

    def test_returns_list(self):
        """query_style_memory always returns a list."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        result = server.query_style_memory("productivity")
        assert isinstance(result, list)

    def test_returns_results_with_expected_keys(self):
        """Results contain text, score, source, paragraph keys."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        _populate_tool(tool)
        server._set_tool_for_testing(tool)

        results = server.query_style_memory("productivity", n_results=2)
        assert len(results) >= 1
        for r in results:
            assert "text" in r
            assert "score" in r
            assert "source" in r
            assert "paragraph" in r

    def test_n_results_respected(self):
        """n_results parameter limits the number of returned excerpts."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        _populate_tool(tool)
        server._set_tool_for_testing(tool)

        results = server.query_style_memory("output chart capital", n_results=1)
        assert len(results) <= 1

    def test_empty_collection_returns_empty_list(self):
        """Empty collection returns [] without error."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        # collection is empty
        server._set_tool_for_testing(tool)

        results = server.query_style_memory("anything")
        assert results == []

    def test_collection_none_returns_empty_list(self):
        """When collection is None, query_style_memory returns []."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        tool.collection = None
        server._set_tool_for_testing(tool)

        results = server.query_style_memory("test")
        assert results == []

    def test_score_values_in_valid_range(self):
        """All returned scores are in [0, 1]."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        _populate_tool(tool)
        server._set_tool_for_testing(tool)

        results = server.query_style_memory("chart shows capital", n_results=3)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0


# ---------------------------------------------------------------------------
# Tests: add_to_style_memory
# ---------------------------------------------------------------------------


class TestAddToStyleMemory:
    """Tests for the add_to_style_memory MCP tool."""

    def test_indexes_valid_article(self):
        """Valid article text is indexed and confirmation returned."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        article = (
            "Britain's factories hummed with renewed purpose last quarter.\n\n"
            "The organisation's capital investment jumped 12% year on year, "
            "a five-year high that surprised even the most optimistic forecasters.\n\n"
            "Economists favour a cautious interpretation nonetheless."
        )
        result = server.add_to_style_memory(article, {"source": "test_article.md"})

        assert result["success"] is True
        assert result["indexed_paragraphs"] >= 2
        assert "test_article.md" in result["message"]

    def test_idempotent_upsert(self):
        """Calling add_to_style_memory twice with the same source is idempotent."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        article = (
            "First paragraph with enough characters to pass the 50-char threshold.\n\n"
            "Second paragraph also meeting the minimum length requirement here."
        )
        server.add_to_style_memory(article, {"source": "idempotent.md"})
        count_before = tool.collection.count()
        server.add_to_style_memory(article, {"source": "idempotent.md"})
        count_after = tool.collection.count()

        # Upsert should not increase count for duplicate IDs
        assert count_after == count_before

    def test_empty_article_returns_failure(self):
        """Empty article_text returns a failure dict."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        result = server.add_to_style_memory("", {"source": "empty.md"})

        assert result["success"] is False
        assert result["indexed_paragraphs"] == 0

    def test_short_paragraphs_only_returns_failure(self):
        """Article with only short paragraphs (<50 chars) returns failure."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        result = server.add_to_style_memory(
            "Short.\n\nAlso short.", {"source": "tiny.md"}
        )

        assert result["success"] is False
        assert result["indexed_paragraphs"] == 0

    def test_collection_none_returns_failure(self):
        """Returns failure dict when ChromaDB collection is unavailable."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        tool.collection = None
        server._set_tool_for_testing(tool)

        long_text = "A" * 60 + "\n\n" + "B" * 60
        result = server.add_to_style_memory(long_text, {"source": "no_db.md"})

        assert result["success"] is False
        assert result["indexed_paragraphs"] == 0

    def test_chromadb_exception_returns_failure(self):
        """ChromaDB upsert error is caught and returned as failure."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        tool.collection = MagicMock()
        tool.collection.upsert.side_effect = RuntimeError("simulated DB error")
        server._set_tool_for_testing(tool)

        long_text = "C" * 60 + "\n\n" + "D" * 60
        result = server.add_to_style_memory(long_text, {"source": "error.md"})

        assert result["success"] is False
        assert "simulated DB error" in result["message"]

    def test_missing_source_returns_failure(self):
        """Metadata without a 'source' key returns a failure dict."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        long_text = "E" * 60 + "\n\n" + "F" * 60
        result = server.add_to_style_memory(long_text, {})

        assert result["success"] is False
        assert result["indexed_paragraphs"] == 0
        assert "source" in result["message"]

    def test_empty_source_returns_failure(self):
        """Metadata with an empty 'source' value returns a failure dict."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        long_text = "G" * 60 + "\n\n" + "H" * 60
        result = server.add_to_style_memory(long_text, {"source": "   "})

        assert result["success"] is False
        assert result["indexed_paragraphs"] == 0

    def test_metadata_attached_to_paragraphs(self):
        """Custom metadata fields are stored alongside each paragraph."""
        import mcp_servers.style_memory_server as server

        tool = _make_in_memory_tool()
        server._set_tool_for_testing(tool)

        article = (
            "The quality of governance matters more than the quantity of rules "
            "in determining long-term economic outcomes.\n\n"
            "Evidence from OECD countries over the past three decades supports "
            "this view; countries with strong institutions consistently outperform."
        )
        server.add_to_style_memory(article, {"source": "gov.md", "author": "editor"})

        # Verify stored metadata via ChromaDB get
        stored = tool.collection.get(ids=["mcp_gov.md_p0"])
        assert stored["metadatas"][0]["author"] == "editor"
        assert stored["metadatas"][0]["source"] == "gov.md"


# ---------------------------------------------------------------------------
# Tests: MCP server object
# ---------------------------------------------------------------------------


class TestMCPServerObject:
    """Smoke tests verifying the FastMCP server is properly configured."""

    def test_server_is_fastmcp_instance(self):
        """mcp is a FastMCP instance."""
        from mcp.server.fastmcp import FastMCP

        import mcp_servers.style_memory_server as server

        assert isinstance(server.mcp, FastMCP)

    def test_tools_registered(self):
        """Both MCP tools are registered on the server."""
        import asyncio

        import mcp_servers.style_memory_server as server

        tools = asyncio.run(server.mcp.list_tools())
        tool_names = {t.name for t in tools}
        assert "query_style_memory" in tool_names
        assert "add_to_style_memory" in tool_names
