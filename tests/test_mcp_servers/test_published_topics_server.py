#!/usr/bin/env python3
"""
Tests for Published Topics MCP Server (Story 19.3)

Coverage targets:
- scripts/article_archive.py  : ArticleArchive class (all public methods)
- mcp_servers/published_topics_server.py : MCP tool functions and archive lifecycle

All ChromaDB interactions are mocked — no persistent state is created.
ChromaDB does not need to be installed for these tests to run.

Usage:
    pytest tests/test_mcp_servers/test_published_topics_server.py -v
"""

import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is on path so that 'scripts' and 'mcp_servers' are importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.article_archive import ArticleArchive
from mcp_servers.published_topics_server import (
    _get_archive,
    get_archive_stats,
    index_published_article,
    is_topic_duplicate,
    query_published_topics,
    search_published_topics,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_collection(count: int = 0) -> MagicMock:
    """Return a minimal mock ChromaDB collection."""
    coll = MagicMock()
    coll.count.return_value = count
    return coll


def _make_mock_client(collection: MagicMock) -> MagicMock:
    """Return a mock ChromaDB client that returns *collection*."""
    client = MagicMock()
    client.get_or_create_collection.return_value = collection
    return client


def _make_archive(collection: MagicMock) -> ArticleArchive:
    """Create an ArticleArchive with the given mock collection injected."""
    return ArticleArchive(_client=_make_mock_client(collection))


# ---------------------------------------------------------------------------
# ArticleArchive — initialisation
# ---------------------------------------------------------------------------


class TestArticleArchiveInit:
    """Tests for ArticleArchive.__init__."""

    def test_init_success_with_injected_client(self) -> None:
        """Archive initialises correctly when a mock client is injected."""
        mock_coll = _make_mock_collection(count=3)
        mock_client = _make_mock_client(mock_coll)

        archive = ArticleArchive(_client=mock_client)

        assert archive.client is mock_client
        assert archive.collection is mock_coll

    def test_init_chromadb_unavailable(self) -> None:
        """Archive degrades gracefully when ChromaDB is not installed."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            archive = ArticleArchive()

        assert archive.client is None
        assert archive.collection is None

    def test_init_injected_client_exception(self) -> None:
        """Archive degrades gracefully when injected client raises."""
        bad_client = MagicMock()
        bad_client.get_or_create_collection.side_effect = RuntimeError("db error")

        archive = ArticleArchive(_client=bad_client)

        assert archive.client is None
        assert archive.collection is None

    def test_init_no_client_no_chromadb(self) -> None:
        """Archive with no client and CHROMADB_AVAILABLE=False is a no-op."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            archive = ArticleArchive()

        assert archive.client is None
        assert archive.collection is None


# ---------------------------------------------------------------------------
# ArticleArchive.search
# ---------------------------------------------------------------------------


class TestArticleArchiveSearch:
    """Tests for ArticleArchive.search."""

    def test_search_returns_results_above_threshold(self) -> None:
        """Matching articles above the similarity threshold are returned."""
        mock_coll = _make_mock_collection(count=2)
        mock_coll.query.return_value = {
            "documents": [["Central bank policy shapes inflation"]],
            "metadatas": [
                [
                    {
                        "title": "Inflation Outlook",
                        "date": "2026-01-10",
                        "categories": "economics",
                        "file_path": "posts/inflation.md",
                    }
                ]
            ],
            "distances": [[0.2]],  # similarity = 1 - 0.2 = 0.8 > 0.6
        }

        archive = _make_archive(mock_coll)
        results = archive.search("inflation central bank", threshold=0.6, n_results=5)

        assert len(results) == 1
        result = results[0]
        assert result["title"] == "Inflation Outlook"
        assert result["similarity"] == pytest.approx(0.8, abs=0.001)
        assert result["thesis"] == "Central bank policy shapes inflation"
        assert result["date"] == "2026-01-10"
        assert result["categories"] == "economics"
        assert result["file_path"] == "posts/inflation.md"

    def test_search_filters_results_below_threshold(self) -> None:
        """Articles with similarity below threshold are excluded."""
        mock_coll = _make_mock_collection(count=1)
        mock_coll.query.return_value = {
            "documents": [["Unrelated article text"]],
            "metadatas": [[{"title": "Unrelated", "date": "", "categories": "", "file_path": ""}]],
            "distances": [[0.9]],  # similarity = 0.1 < 0.6
        }

        archive = _make_archive(mock_coll)
        results = archive.search("inflation", threshold=0.6)

        assert results == []

    def test_search_empty_collection(self) -> None:
        """Search on an empty archive returns an empty list."""
        mock_coll = _make_mock_collection(count=0)

        archive = _make_archive(mock_coll)
        results = archive.search("any query")

        assert results == []
        mock_coll.query.assert_not_called()

    def test_search_no_collection(self) -> None:
        """Search without a collection returns an empty list."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            archive = ArticleArchive()
        assert archive.search("test") == []

    def test_search_empty_query(self) -> None:
        """Blank query string returns an empty list without hitting ChromaDB."""
        mock_coll = _make_mock_collection(count=5)
        archive = _make_archive(mock_coll)

        assert archive.search("   ") == []
        mock_coll.query.assert_not_called()

    def test_search_limits_n_results_to_collection_count(self) -> None:
        """n_results is capped at the actual collection size."""
        mock_coll = _make_mock_collection(count=2)
        mock_coll.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        archive = _make_archive(mock_coll)
        archive.search("query", n_results=100)

        call_kwargs = mock_coll.query.call_args.kwargs
        assert call_kwargs["n_results"] == 2

    def test_search_handles_exception(self) -> None:
        """If ChromaDB query raises, search returns an empty list."""
        mock_coll = _make_mock_collection(count=1)
        mock_coll.query.side_effect = RuntimeError("query failed")

        archive = _make_archive(mock_coll)
        results = archive.search("query")

        assert results == []

    def test_search_missing_distances_key(self) -> None:
        """Search handles responses without a 'distances' key gracefully."""
        mock_coll = _make_mock_collection(count=1)
        mock_coll.query.return_value = {
            "documents": [["Some article"]],
            "metadatas": [[{"title": "X", "date": "", "categories": "", "file_path": ""}]],
            # no 'distances' key
        }

        archive = _make_archive(mock_coll)
        results = archive.search("query", threshold=0.0)

        # With no distance key, distance defaults to 0.0, so similarity=1.0
        assert len(results) == 1
        assert results[0]["similarity"] == 1.0

    def test_search_multiple_results(self) -> None:
        """Multiple above-threshold results are all returned."""
        mock_coll = _make_mock_collection(count=3)
        mock_coll.query.return_value = {
            "documents": [["Doc A", "Doc B"]],
            "metadatas": [
                [
                    {"title": "A", "date": "2026-01-01", "categories": "cat", "file_path": "a.md"},
                    {"title": "B", "date": "2026-02-01", "categories": "cat", "file_path": "b.md"},
                ]
            ],
            "distances": [[0.1, 0.3]],
        }

        archive = _make_archive(mock_coll)
        results = archive.search("query", threshold=0.5)

        assert len(results) == 2
        assert results[0]["title"] == "A"
        assert results[1]["title"] == "B"


# ---------------------------------------------------------------------------
# ArticleArchive.index_article
# ---------------------------------------------------------------------------


class TestArticleArchiveIndexArticle:
    """Tests for ArticleArchive.index_article."""

    def test_index_article_success(self) -> None:
        """Successful indexing returns success=True with id and total_indexed."""
        mock_coll = _make_mock_collection(count=0)
        mock_coll.count.side_effect = [0, 1]  # before (init) and after upsert

        archive = _make_archive(mock_coll)
        result = archive.index_article(
            title="The AI Revolution",
            thesis="Artificial intelligence is reshaping labour markets",
            date="2026-03-01",
            categories="technology,economics",
            file_path="posts/ai-revolution.md",
        )

        assert result["success"] is True
        assert result["id"] == "posts/ai-revolution.md"
        assert "total_indexed" in result
        mock_coll.upsert.assert_called_once()

    def test_index_article_uses_title_date_as_fallback_id(self) -> None:
        """When file_path is empty, title+date is used as the document ID."""
        mock_coll = _make_mock_collection(count=0)
        archive = _make_archive(mock_coll)

        result = archive.index_article(
            title="Climate Crisis",
            thesis="Rising temperatures threaten ecosystems",
            date="2026-02-15",
            categories="environment",
            file_path="",
        )

        assert result["success"] is True
        assert result["id"] == "Climate Crisis_2026-02-15"

    def test_index_article_no_chromadb(self) -> None:
        """Indexing without a collection returns success=False with error."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            archive = ArticleArchive()
        result = archive.index_article("T", "thesis", "2026-01-01", "cat", "path.md")

        assert result["success"] is False
        assert "error" in result

    def test_index_article_upsert_exception(self) -> None:
        """If upsert raises, index_article returns success=False."""
        mock_coll = _make_mock_collection(count=0)
        mock_coll.upsert.side_effect = RuntimeError("write error")

        archive = _make_archive(mock_coll)
        result = archive.index_article("T", "thesis", "2026-01-01", "cat", "path.md")

        assert result["success"] is False
        assert "error" in result

    def test_index_article_metadata_contains_indexed_at(self) -> None:
        """Upserted metadata includes an indexed_at timestamp."""
        mock_coll = _make_mock_collection(count=0)
        archive = _make_archive(mock_coll)

        archive.index_article("T", "thesis", "2026-01-01", "cat", "path.md")

        call_kwargs = mock_coll.upsert.call_args.kwargs
        metadata = call_kwargs["metadatas"][0]
        assert "indexed_at" in metadata

    def test_index_article_upsert_called_with_correct_args(self) -> None:
        """upsert is called with thesis as document and correct metadata fields."""
        mock_coll = _make_mock_collection(count=0)
        archive = _make_archive(mock_coll)

        archive.index_article(
            title="Economic Growth",
            thesis="GDP growth slows amid trade tensions",
            date="2026-04-01",
            categories="economics",
            file_path="posts/growth.md",
        )

        call_kwargs = mock_coll.upsert.call_args.kwargs
        assert call_kwargs["documents"] == ["GDP growth slows amid trade tensions"]
        assert call_kwargs["ids"] == ["posts/growth.md"]
        meta = call_kwargs["metadatas"][0]
        assert meta["title"] == "Economic Growth"
        assert meta["date"] == "2026-04-01"
        assert meta["categories"] == "economics"


# ---------------------------------------------------------------------------
# ArticleArchive.get_stats
# ---------------------------------------------------------------------------


class TestArticleArchiveGetStats:
    """Tests for ArticleArchive.get_stats."""

    def test_stats_no_chromadb(self) -> None:
        """get_stats returns available=False when ChromaDB is unavailable."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            archive = ArticleArchive()
        stats = archive.get_stats()

        assert stats["available"] is False
        assert stats["total_articles"] == 0

    def test_stats_empty_collection(self) -> None:
        """get_stats on an empty collection returns total_articles=0."""
        mock_coll = _make_mock_collection(count=0)
        archive = _make_archive(mock_coll)
        stats = archive.get_stats()

        assert stats["available"] is True
        assert stats["total_articles"] == 0
        assert stats["date_range"] == {"earliest": None, "latest": None}
        assert stats["category_distribution"] == {}

    def test_stats_with_articles(self) -> None:
        """get_stats returns correct totals, date_range, and category counts."""
        mock_coll = _make_mock_collection(count=2)
        mock_coll.get.return_value = {
            "metadatas": [
                {"title": "A", "date": "2026-01-10", "categories": "tech,economics"},
                {"title": "B", "date": "2026-03-05", "categories": "tech"},
            ]
        }

        archive = _make_archive(mock_coll)
        stats = archive.get_stats()

        assert stats["available"] is True
        assert stats["total_articles"] == 2
        assert stats["date_range"]["earliest"] == "2026-01-10"
        assert stats["date_range"]["latest"] == "2026-03-05"
        assert stats["category_distribution"]["tech"] == 2
        assert stats["category_distribution"]["economics"] == 1

    def test_stats_articles_with_missing_dates(self) -> None:
        """Articles without dates are excluded from date_range computation."""
        mock_coll = _make_mock_collection(count=1)
        mock_coll.get.return_value = {
            "metadatas": [{"title": "A", "date": "", "categories": ""}]
        }

        archive = _make_archive(mock_coll)
        stats = archive.get_stats()

        assert stats["date_range"]["earliest"] is None
        assert stats["date_range"]["latest"] is None

    def test_stats_exception_returns_safe_default(self) -> None:
        """Exceptions in get_stats are caught and a safe dict is returned."""
        mock_coll = _make_mock_collection(count=3)
        mock_coll.get.side_effect = RuntimeError("db error")

        archive = _make_archive(mock_coll)
        stats = archive.get_stats()

        assert stats["available"] is True
        assert stats["total_articles"] == 0

    def test_stats_categories_with_whitespace(self) -> None:
        """Category strings with extra whitespace are trimmed correctly."""
        mock_coll = _make_mock_collection(count=1)
        mock_coll.get.return_value = {
            "metadatas": [{"title": "A", "date": "2026-01-01", "categories": " tech , economics "}]
        }

        archive = _make_archive(mock_coll)
        stats = archive.get_stats()

        assert "tech" in stats["category_distribution"]
        assert "economics" in stats["category_distribution"]


# ---------------------------------------------------------------------------
# MCP server tool functions
# ---------------------------------------------------------------------------


class TestMCPServerTools:
    """Tests for the three MCP tool functions in published_topics_server.py."""

    @pytest.fixture(autouse=True)
    def reset_archive(self) -> Iterator[None]:
        """Reset the module-level _archive singleton between tests."""
        import mcp_servers.published_topics_server as srv

        original = srv._archive
        srv._archive = None
        yield
        srv._archive = original

    def _mock_archive(self) -> MagicMock:
        return MagicMock(spec=ArticleArchive)

    def test_search_published_topics_delegates_to_archive(self) -> None:
        """search_published_topics forwards call to archive.search."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [{"title": "Inflation", "similarity": 0.85}]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            results = search_published_topics("inflation", threshold=0.5, n_results=3)

        mock_arc.search.assert_called_once_with("inflation", threshold=0.5, n_results=3)
        assert results[0]["title"] == "Inflation"

    def test_index_published_article_delegates_to_archive(self) -> None:
        """index_published_article forwards call to archive.index_article."""
        mock_arc = self._mock_archive()
        mock_arc.index_article.return_value = {
            "success": True,
            "id": "posts/test.md",
            "total_indexed": 1,
        }

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = index_published_article(
                title="Test",
                thesis="A test article",
                date="2026-04-01",
                categories="testing",
                file_path="posts/test.md",
            )

        mock_arc.index_article.assert_called_once_with(
            "Test", "A test article", "2026-04-01", "testing", "posts/test.md"
        )
        assert result["success"] is True

    def test_get_archive_stats_delegates_to_archive(self) -> None:
        """get_archive_stats forwards call to archive.get_stats."""
        mock_arc = self._mock_archive()
        mock_arc.get_stats.return_value = {
            "available": True,
            "total_articles": 5,
            "date_range": {"earliest": "2025-01-01", "latest": "2026-03-01"},
            "category_distribution": {"tech": 3, "economics": 2},
        }

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            stats = get_archive_stats()

        mock_arc.get_stats.assert_called_once()
        assert stats["total_articles"] == 5

    def test_get_archive_lazy_initialises_singleton(self) -> None:
        """_get_archive() creates ArticleArchive on first call and caches it."""
        import mcp_servers.published_topics_server as srv

        assert srv._archive is None

        mock_coll = _make_mock_collection(count=0)
        mock_archive = _make_archive(mock_coll)

        with patch(
            "mcp_servers.published_topics_server.ArticleArchive",
            return_value=mock_archive,
        ):
            arc1 = _get_archive()
            arc2 = _get_archive()

        assert arc1 is arc2
        assert srv._archive is arc1

    def test_search_published_topics_default_params(self) -> None:
        """search_published_topics uses correct default threshold and n_results."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            search_published_topics("some query")

        mock_arc.search.assert_called_once_with("some query", threshold=0.6, n_results=5)

    def test_search_returns_empty_list_when_no_results(self) -> None:
        """search_published_topics returns [] when archive finds nothing."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            results = search_published_topics("obscure topic")

        assert results == []

    def test_index_article_returns_failure_dict_on_error(self) -> None:
        """index_published_article propagates failure dict from archive."""
        mock_arc = self._mock_archive()
        mock_arc.index_article.return_value = {
            "success": False,
            "error": "ChromaDB unavailable",
            "id": "",
        }

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = index_published_article("T", "thesis", "2026-01-01", "cat", "")

        assert result["success"] is False
        assert result["error"] == "ChromaDB unavailable"


# ---------------------------------------------------------------------------
# MCP tool: query_published_topics
# ---------------------------------------------------------------------------


class TestQueryPublishedTopics:
    """Tests for the query_published_topics MCP tool."""

    @pytest.fixture(autouse=True)
    def reset_archive(self) -> Iterator[None]:
        """Reset the module-level _archive singleton between tests."""
        import mcp_servers.published_topics_server as srv

        original = srv._archive
        srv._archive = None
        yield
        srv._archive = original

    def _mock_archive(self) -> MagicMock:
        return MagicMock(spec=ArticleArchive)

    def test_query_returns_results(self) -> None:
        """query_published_topics returns results from archive.search."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [
            {"title": "Inflation", "similarity": 0.75},
            {"title": "Trade War", "similarity": 0.62},
        ]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            results = query_published_topics("monetary policy")

        mock_arc.search.assert_called_once_with("monetary policy", threshold=0.0, n_results=5)
        assert len(results) == 2
        assert results[0]["title"] == "Inflation"

    def test_query_default_n_results(self) -> None:
        """query_published_topics defaults to n_results=5."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            query_published_topics("some topic")

        mock_arc.search.assert_called_once_with("some topic", threshold=0.0, n_results=5)

    def test_query_custom_n_results(self) -> None:
        """query_published_topics passes custom n_results to archive.search."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            query_published_topics("AI automation", n_results=10)

        mock_arc.search.assert_called_once_with("AI automation", threshold=0.0, n_results=10)

    def test_query_uses_zero_threshold(self) -> None:
        """query_published_topics uses threshold=0.0 (returns all results)."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [{"title": "Low sim", "similarity": 0.1}]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            results = query_published_topics("obscure niche")

        # threshold=0.0 means even low-similarity results come through
        assert results[0]["similarity"] == 0.1

    def test_query_empty_archive_returns_empty_list(self) -> None:
        """query_published_topics returns [] when no articles are indexed."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            results = query_published_topics("anything")

        assert results == []


# ---------------------------------------------------------------------------
# MCP tool: is_topic_duplicate
# ---------------------------------------------------------------------------


class TestIsTopicDuplicate:
    """Tests for the is_topic_duplicate MCP tool."""

    @pytest.fixture(autouse=True)
    def reset_archive(self) -> Iterator[None]:
        """Reset the module-level _archive singleton between tests."""
        import mcp_servers.published_topics_server as srv

        original = srv._archive
        srv._archive = None
        yield
        srv._archive = original

    def _mock_archive(self) -> MagicMock:
        return MagicMock(spec=ArticleArchive)

    def test_duplicate_when_similarity_above_0_8(self) -> None:
        """is_duplicate=True when best match similarity exceeds 0.8."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [
            {"title": "Inflation Outlook", "similarity": 0.9},
        ]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = is_topic_duplicate("Central bank inflation forecast")

        assert result["is_duplicate"] is True
        assert result["confidence"] == pytest.approx(0.9)
        assert result["warning"] is False
        assert len(result["similar_articles"]) == 1

    def test_warning_when_similarity_between_0_6_and_0_8(self) -> None:
        """warning=True when best match is in the 0.6-0.8 zone."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [
            {"title": "Trade Policy", "similarity": 0.7},
        ]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = is_topic_duplicate("Trade tariffs impact")

        assert result["is_duplicate"] is False
        assert result["warning"] is True
        assert result["confidence"] == pytest.approx(0.7)

    def test_safe_when_no_similar_articles(self) -> None:
        """is_duplicate=False and warning=False when archive is empty."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = is_topic_duplicate("Completely new topic")

        assert result["is_duplicate"] is False
        assert result["warning"] is False
        assert result["confidence"] == 0.0
        assert result["similar_articles"] == []

    def test_boundary_exactly_0_8_is_not_duplicate(self) -> None:
        """similarity == 0.8 is in the warning zone, not a duplicate."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = [
            {"title": "Edge Case", "similarity": 0.8},
        ]

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = is_topic_duplicate("Edge case topic")

        assert result["is_duplicate"] is False
        assert result["warning"] is True

    def test_uses_threshold_0_6_for_search(self) -> None:
        """is_topic_duplicate searches with threshold=0.6."""
        mock_arc = self._mock_archive()
        mock_arc.search.return_value = []

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            is_topic_duplicate("some topic")

        mock_arc.search.assert_called_once_with("some topic", threshold=0.6, n_results=5)

    def test_returns_all_similar_articles_in_result(self) -> None:
        """similar_articles in result includes all returned matches."""
        mock_arc = self._mock_archive()
        articles = [
            {"title": "A", "similarity": 0.85},
            {"title": "B", "similarity": 0.72},
            {"title": "C", "similarity": 0.65},
        ]
        mock_arc.search.return_value = articles

        with patch("mcp_servers.published_topics_server._get_archive", return_value=mock_arc):
            result = is_topic_duplicate("broad topic")

        assert result["similar_articles"] == articles
        assert result["is_duplicate"] is True  # best match 0.85 > 0.8
