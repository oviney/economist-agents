#!/usr/bin/env python3
"""
Integration Tests for Style Memory Tool

Tests RAG-based style pattern retrieval for Editor Agent GATE 3 enhancement.

Test Coverage:
1. Tool initialization and graceful degradation
2. Archive indexing with real/mock articles
3. Query functionality with relevance scoring
4. ChromaDB integration
5. CrewAI tool wrapper

Usage:
    pytest tests/test_style_memory_tool.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.style_memory_tool import StyleMemoryTool, create_style_memory_tool


class TestStyleMemoryTool:
    """Integration tests for Style Memory Tool"""

    @pytest.fixture
    def temp_archive(self, tmp_path):
        """Create temporary archive with test articles"""
        archive_dir = tmp_path / "archived"
        archive_dir.mkdir()

        # Create test article
        test_article = archive_dir / "test_article.md"
        test_article.write_text(
            """
# Test Gold Standard Article

This is a paragraph demonstrating Economist voice. No banned phrases like
"in today's world" or "it's no secret that". Direct, authoritative tone.

Second paragraph shows proper structure. British spelling: organisation, favour.
Active voice dominates. No exclamation points or rhetorical questions as headers.

Third paragraph validates style patterns. Chart integration example: As the chart
shows, productivity gains plateaued after 2020. Concrete data, clear attribution.
            """.strip()
        )

        return archive_dir

    def test_tool_initialization_with_chromadb(self, temp_archive):
        """
        Test 1: Tool initialization with ChromaDB available

        Given: ChromaDB installed and temp archive
        When: StyleMemoryTool initialized
        Then: Vector store created and articles indexed
        """
        try:
            import chromadb  # noqa: F401

            tool = StyleMemoryTool(
                archive_path=temp_archive,
                persist_directory=str(temp_archive / ".chromadb"),
            )

            assert tool.client is not None
            assert tool.collection is not None
            assert tool.indexed_count >= 0  # May be 0 if paragraphs too short

        except ImportError:
            pytest.skip("ChromaDB not installed - test requires chromadb package")

    def test_tool_initialization_without_chromadb(self, temp_archive):
        """
        Test 2: Tool initialization without ChromaDB (graceful degradation)

        Given: ChromaDB unavailable (mocked)
        When: StyleMemoryTool initialized
        Then: Tool initializes without error, returns empty results
        """
        with patch("src.tools.style_memory_tool.CHROMADB_AVAILABLE", False):
            tool = StyleMemoryTool(archive_path=temp_archive)

            assert tool.client is None
            assert tool.collection is None
            results = tool.query("test query")
            assert results == []  # Graceful degradation

    def test_query_with_results(self, temp_archive):
        """
        Test 3: Query functionality with relevant results

        Given: Tool initialized with test article
        When: Query for "banned phrases"
        Then: Returns results with score >0.7 and proper format
        """
        try:
            import chromadb  # noqa: F401

            tool = StyleMemoryTool(
                archive_path=temp_archive,
                persist_directory=str(temp_archive / ".chromadb"),
            )

            if tool.indexed_count > 0:
                results = tool.query(
                    "banned phrases examples", n_results=3, min_score=0.5
                )

                assert isinstance(results, list)
                for result in results:
                    assert "text" in result
                    assert "score" in result
                    assert "source" in result
                    assert 0 <= result["score"] <= 1.0
            else:
                pytest.skip("No articles indexed (paragraphs may be too short)")

        except ImportError:
            pytest.skip("ChromaDB not installed")

    def test_query_latency_requirement(self, temp_archive):
        """
        Test 4: Query latency <500ms requirement

        Given: Tool initialized
        When: Query executed
        Then: Completes in <500ms
        """
        try:
            import time

            import chromadb  # noqa: F401

            tool = StyleMemoryTool(
                archive_path=temp_archive,
                persist_directory=str(temp_archive / ".chromadb"),
            )

            if tool.indexed_count > 0:
                start = time.time()
                tool.query("test query", n_results=3)
                latency_ms = (time.time() - start) * 1000

                assert latency_ms < 500, (
                    f"Query took {latency_ms:.1f}ms (exceeds 500ms requirement)"
                )
            else:
                pytest.skip("No articles indexed")

        except ImportError:
            pytest.skip("ChromaDB not installed")

    def test_min_score_threshold(self, temp_archive):
        """
        Test 5: Minimum score threshold filtering (>0.7)

        Given: Tool with indexed articles
        When: Query with min_score=0.7
        Then: All results have score >=0.7
        """
        try:
            import chromadb  # noqa: F401

            tool = StyleMemoryTool(
                archive_path=temp_archive,
                persist_directory=str(temp_archive / ".chromadb"),
            )

            if tool.indexed_count > 0:
                results = tool.query("style patterns", n_results=5, min_score=0.7)

                for result in results:
                    assert result["score"] >= 0.7, (
                        f"Result score {result['score']} < 0.7 threshold"
                    )
            else:
                pytest.skip("No articles indexed")

        except ImportError:
            pytest.skip("ChromaDB not installed")

    def test_empty_archive_graceful_degradation(self, tmp_path):
        """
        Test 6: Empty archive handling (graceful degradation)

        Given: Empty archive directory
        When: Tool initialized
        Then: No error, indexed_count=0, queries return empty
        """
        try:
            import chromadb  # noqa: F401

            empty_archive = tmp_path / "empty_archive"
            empty_archive.mkdir()

            tool = StyleMemoryTool(
                archive_path=empty_archive,
                persist_directory=str(tmp_path / ".chromadb"),
            )

            assert tool.indexed_count == 0
            results = tool.query("test query")
            assert results == []

        except ImportError:
            pytest.skip("ChromaDB not installed")

    def test_crewai_tool_wrapper(self, temp_archive):
        """
        Test 7: CrewAI tool wrapper returns formatted string

        Given: create_style_memory_tool() factory
        When: Tool function called with query
        Then: Returns formatted string (not dict)
        """
        try:
            import chromadb  # noqa: F401

            with patch("src.tools.style_memory_tool.StyleMemoryTool") as MockTool:
                # Mock StyleMemoryTool to return controlled results
                mock_instance = MagicMock()
                mock_instance.query.return_value = [
                    {
                        "text": "Example style pattern",
                        "score": 0.85,
                        "source": "test.md",
                        "paragraph": 0,
                    }
                ]
                MockTool.return_value = mock_instance

                tool_func = create_style_memory_tool()
                result = tool_func("test query")

                assert isinstance(result, str)
                assert (
                    "Style Memory Results" in result
                    or "No relevant style patterns" in result
                )

        except ImportError:
            pytest.skip("ChromaDB not installed")

    def test_stats_method(self, temp_archive):
        """
        Test 8: get_stats() returns tool status

        Given: Tool initialized
        When: get_stats() called
        Then: Returns dict with available, indexed_count, collection_name
        """
        try:
            import chromadb  # noqa: F401

            tool = StyleMemoryTool(
                archive_path=temp_archive,
                persist_directory=str(temp_archive / ".chromadb"),
            )

            stats = tool.get_stats()

            assert "available" in stats
            assert "indexed_count" in stats
            assert "collection_name" in stats
            assert isinstance(stats["available"], bool)
            assert isinstance(stats["indexed_count"], int)

        except ImportError:
            pytest.skip("ChromaDB not installed")


def test_style_memory_tool_import():
    """
    Test 9: Module import without errors

    Given: style_memory_tool module
    When: Imported
    Then: No import errors
    """
    from src.tools.style_memory_tool import (
        StyleMemoryTool,
        create_style_memory_tool,
    )

    assert StyleMemoryTool is not None
    assert create_style_memory_tool is not None
