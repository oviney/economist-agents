#!/usr/bin/env python3
"""Unit tests for scripts/index_published_articles.py.

All ChromaDB interactions use an in-memory ``EphemeralClient`` so no state
is persisted to disk between runs.  HTTP calls are intercepted with
``unittest.mock`` so the tests run fully offline.

Coverage targets:
- ``_make_doc_id`` — URL normalisation
- ``_categories_to_str`` — list / string / None handling
- ``fetch_search_json`` — HTTP fetch, local file, error paths
- ``index_articles`` — upsert, idempotency, metadata, skip logic
- ``run`` — end-to-end with injected client
- Module-level import smoke test

Usage::

    pytest tests/test_index_published_articles.py -v
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import orjson
import pytest

# ---------------------------------------------------------------------------
# Make repo root importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.index_published_articles import (
    COLLECTION_NAME,
    DEFAULT_SOURCE,
    _categories_to_str,
    _make_doc_id,
    fetch_search_json,
    index_articles,
    run,
)

# ---------------------------------------------------------------------------
# Offline embedding function (no network / model download required)
# ---------------------------------------------------------------------------

try:
    from chromadb import Documents, EmbeddingFunction, Embeddings

    class _HashEmbedding(EmbeddingFunction):  # type: ignore[misc]
        """Deterministic bag-of-words embedding — works fully offline."""

        DIM = 128

        def __init__(self) -> None:
            pass  # required by ChromaDB 1.5.5+

        def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
            embeddings = []
            for text in input:
                vec = [0.0] * self.DIM
                for word in text.lower().split():
                    idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM
                    vec[idx] += 1.0
                norm = sum(x * x for x in vec) ** 0.5
                if norm > 0:
                    vec = [x / norm for x in vec]
                embeddings.append(vec)
            return embeddings

    _HASH_EF: _HashEmbedding | None = _HashEmbedding()
except ImportError:
    _HASH_EF = None

# ---------------------------------------------------------------------------
# Sample search.json data
# ---------------------------------------------------------------------------

SAMPLE_ARTICLES: list[dict[str, Any]] = [
    {
        "title": "Why AI Testing is Broken",
        "url": "/2026-04-01-why-ai-testing-is-broken/",
        "date": "2026-04-01",
        "categories": ["quality-engineering"],
        "excerpt": "Automated test generation raises quality illusions.",
        "content": "Full article content here for testing purposes.",
    },
    {
        "title": "The Productivity Puzzle",
        "url": "/2026-03-15-productivity-puzzle/",
        "date": "2026-03-15",
        "categories": ["economics", "labour"],
        "excerpt": "Britain's output per hour worked continues to confound economists.",
    },
    {
        "title": "Capital Markets in 2026",
        "url": "/2026-02-01-capital-markets-2026/",
        "date": "2026-02-01",
        "categories": ["finance"],
        "description": "A survey of global capital markets and emerging trends.",
    },
]

# ---------------------------------------------------------------------------
# Helper: in-memory ChromaDB collection
# ---------------------------------------------------------------------------


def _ephemeral_collection(name: str = COLLECTION_NAME) -> Any:
    """Return an in-memory ChromaDB collection, or skip if not installed."""
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.EphemeralClient(settings=Settings(allow_reset=True))
        client.reset()
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=_HASH_EF,
        )
    except ImportError:
        pytest.skip("ChromaDB not installed — skipping test")


def _ephemeral_client() -> Any:
    """Return a fresh EphemeralClient, or skip if ChromaDB not installed."""
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.EphemeralClient(settings=Settings(allow_reset=True))
        client.reset()
        return client
    except ImportError:
        pytest.skip("ChromaDB not installed — skipping test")


# ---------------------------------------------------------------------------
# Tests: _make_doc_id
# ---------------------------------------------------------------------------


class TestMakeDocId:
    """Unit tests for the document-ID derivation helper."""

    def test_strips_protocol_and_host(self) -> None:
        doc_id = _make_doc_id("https://viney.ca/2026-01-01-my-post/")
        assert "viney" not in doc_id
        assert "https" not in doc_id

    def test_root_relative_url(self) -> None:
        doc_id = _make_doc_id("/2026-04-01-why-ai-testing-is-broken/")
        assert "2026" in doc_id
        assert "/" not in doc_id

    def test_replaces_special_chars(self) -> None:
        doc_id = _make_doc_id("/2026-04-01-article title/?q=1")
        assert " " not in doc_id
        assert "?" not in doc_id
        assert "=" not in doc_id

    def test_empty_url_returns_unknown(self) -> None:
        assert _make_doc_id("") == "unknown"

    def test_same_url_produces_same_id(self) -> None:
        url = "https://viney.ca/2026-01-01-article/"
        assert _make_doc_id(url) == _make_doc_id(url)

    def test_different_urls_produce_different_ids(self) -> None:
        id1 = _make_doc_id("/2026-01-01-article-a/")
        id2 = _make_doc_id("/2026-02-01-article-b/")
        assert id1 != id2


# ---------------------------------------------------------------------------
# Tests: _categories_to_str
# ---------------------------------------------------------------------------


class TestCategoriesToStr:
    """Unit tests for the categories normalisation helper."""

    def test_list_joined_by_comma(self) -> None:
        assert _categories_to_str(["testing", "ai"]) == "testing,ai"

    def test_string_passthrough(self) -> None:
        assert _categories_to_str("quality-engineering") == "quality-engineering"

    def test_none_returns_empty_string(self) -> None:
        assert _categories_to_str(None) == ""

    def test_empty_list_returns_empty_string(self) -> None:
        assert _categories_to_str([]) == ""

    def test_single_item_list(self) -> None:
        assert _categories_to_str(["finance"]) == "finance"


# ---------------------------------------------------------------------------
# Tests: fetch_search_json
# ---------------------------------------------------------------------------


class TestFetchSearchJson:
    """Tests for the HTTP / local-file fetch function."""

    def test_fetches_from_url(self) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ARTICLES
        mock_resp.raise_for_status.return_value = None

        with patch(
            "scripts.index_published_articles.requests.get",
            return_value=mock_resp,
        ) as mock_get:
            result = fetch_search_json("https://viney.ca/search.json")

        mock_get.assert_called_once_with("https://viney.ca/search.json", timeout=30)
        assert result == SAMPLE_ARTICLES

    def test_reads_from_local_file(self, tmp_path: Path) -> None:
        search_json = tmp_path / "search.json"
        search_json.write_bytes(orjson.dumps(SAMPLE_ARTICLES))

        result = fetch_search_json(str(search_json))

        assert len(result) == len(SAMPLE_ARTICLES)
        assert result[0]["title"] == SAMPLE_ARTICLES[0]["title"]

    def test_http_raises_on_error_status(self) -> None:
        import requests as req_lib

        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("404")

        with (
            patch(
                "scripts.index_published_articles.requests.get",
                return_value=mock_resp,
            ),
            pytest.raises(req_lib.HTTPError),
        ):
            fetch_search_json("https://viney.ca/search.json")

    def test_raises_value_error_for_non_list_json(self, tmp_path: Path) -> None:
        bad_json = tmp_path / "search.json"
        bad_json.write_bytes(orjson.dumps({"articles": []}))

        with pytest.raises(ValueError, match="Expected a JSON array"):
            fetch_search_json(str(bad_json))

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        bad_json = tmp_path / "search.json"
        bad_json.write_bytes(b"not-valid-json{{{")

        with pytest.raises(orjson.JSONDecodeError):
            fetch_search_json(str(bad_json))

    def test_empty_array_is_accepted(self, tmp_path: Path) -> None:
        empty_json = tmp_path / "search.json"
        empty_json.write_bytes(b"[]")

        result = fetch_search_json(str(empty_json))
        assert result == []


# ---------------------------------------------------------------------------
# Tests: index_articles
# ---------------------------------------------------------------------------


class TestIndexArticles:
    """Tests for the core upsert logic."""

    def test_upserts_all_articles(self) -> None:
        collection = _ephemeral_collection()
        result = index_articles(SAMPLE_ARTICLES, collection)

        assert result["indexed"] == 3
        assert result["skipped"] == 0
        assert collection.count() == 3

    def test_idempotent_upsert(self) -> None:
        """Re-indexing the same articles must not create duplicates."""
        collection = _ephemeral_collection()

        index_articles(SAMPLE_ARTICLES, collection)
        count_after_first = collection.count()

        index_articles(SAMPLE_ARTICLES, collection)
        count_after_second = collection.count()

        assert count_after_first == count_after_second == 3

    def test_stores_required_metadata_fields(self) -> None:
        collection = _ephemeral_collection()
        index_articles([SAMPLE_ARTICLES[0]], collection)

        stored = collection.get(include=["metadatas"])
        meta = stored["metadatas"][0]

        assert meta["title"] == SAMPLE_ARTICLES[0]["title"]
        assert meta["url"] == SAMPLE_ARTICLES[0]["url"]
        assert meta["date"] == SAMPLE_ARTICLES[0]["date"]
        assert "quality-engineering" in meta["categories"]
        assert "summary" in meta

    def test_excerpt_used_as_summary(self) -> None:
        collection = _ephemeral_collection()
        index_articles([SAMPLE_ARTICLES[0]], collection)

        stored = collection.get(include=["metadatas"])
        assert stored["metadatas"][0]["summary"] == SAMPLE_ARTICLES[0]["excerpt"]

    def test_description_used_as_fallback_summary(self) -> None:
        """When only 'description' is present it becomes the summary."""
        collection = _ephemeral_collection()
        article = SAMPLE_ARTICLES[2]  # has 'description', no 'excerpt'
        index_articles([article], collection)

        stored = collection.get(include=["metadatas"])
        assert stored["metadatas"][0]["summary"] == article["description"]

    def test_content_truncated_when_no_excerpt(self) -> None:
        """When no excerpt or description, content is truncated to 200 chars."""
        collection = _ephemeral_collection()
        long_content = "X" * 500
        article = {
            "title": "Long Content Article",
            "url": "/long-content/",
            "date": "2026-01-01",
            "categories": [],
            "content": long_content,
        }
        index_articles([article], collection)

        stored = collection.get(include=["metadatas"])
        assert len(stored["metadatas"][0]["summary"]) <= 200

    def test_categories_list_normalised_to_comma_string(self) -> None:
        collection = _ephemeral_collection()
        index_articles([SAMPLE_ARTICLES[1]], collection)  # categories is a list

        stored = collection.get(include=["metadatas"])
        cats = stored["metadatas"][0]["categories"]
        assert "economics" in cats
        assert "labour" in cats

    def test_skips_articles_with_no_title_or_url(self) -> None:
        collection = _ephemeral_collection()
        empty_article: dict[str, Any] = {"title": "", "url": ""}

        result = index_articles([empty_article], collection)

        assert result["skipped"] == 1
        assert result["indexed"] == 0
        assert collection.count() == 0

    def test_handles_upsert_failure_gracefully(self) -> None:
        """A ChromaDB write error is logged and counted as skipped."""
        from unittest.mock import MagicMock

        mock_col = MagicMock()
        mock_col.upsert.side_effect = RuntimeError("simulated write error")

        result = index_articles([SAMPLE_ARTICLES[0]], mock_col)

        assert result["skipped"] == 1
        assert result["indexed"] == 0

    def test_partial_failure_counts_correctly(self) -> None:
        """Failures on some articles do not block others."""
        from unittest.mock import MagicMock

        call_count = {"n": 0}
        mock_col = MagicMock()

        def _upsert_side_effect(**_kwargs: Any) -> None:
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("second article fails")

        mock_col.upsert.side_effect = _upsert_side_effect

        result = index_articles(SAMPLE_ARTICLES, mock_col)

        assert result["indexed"] == 2
        assert result["skipped"] == 1

    def test_empty_feed_returns_zero_counts(self) -> None:
        collection = _ephemeral_collection()
        result = index_articles([], collection)

        assert result["indexed"] == 0
        assert result["skipped"] == 0
        assert collection.count() == 0


# ---------------------------------------------------------------------------
# Tests: run()
# ---------------------------------------------------------------------------


class TestRun:
    """End-to-end tests for the run() orchestrator."""

    def test_run_indexes_articles_from_url(self) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ARTICLES
        mock_resp.raise_for_status.return_value = None

        client = _ephemeral_client()

        with patch(
            "scripts.index_published_articles.requests.get",
            return_value=mock_resp,
        ):
            result = run(
                source="https://viney.ca/search.json",
                _client=client,
                _embedding_function=_HASH_EF,
            )

        assert result["indexed"] == 3
        assert result["skipped"] == 0

    def test_run_is_idempotent(self) -> None:
        """Calling run() twice with the same feed must not create duplicates."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ARTICLES
        mock_resp.raise_for_status.return_value = None

        client = _ephemeral_client()

        with patch(
            "scripts.index_published_articles.requests.get",
            return_value=mock_resp,
        ):
            run(
                source="https://viney.ca/search.json",
                _client=client,
                _embedding_function=_HASH_EF,
            )
            result2 = run(
                source="https://viney.ca/search.json",
                _client=client,
                _embedding_function=_HASH_EF,
            )

        # Second run upserts the same IDs — count must not grow
        assert result2["indexed"] == 3

    def test_run_reads_from_local_file(self, tmp_path: Path) -> None:
        search_file = tmp_path / "search.json"
        search_file.write_bytes(orjson.dumps(SAMPLE_ARTICLES))

        client = _ephemeral_client()
        result = run(
            source=str(search_file),
            _client=client,
            _embedding_function=_HASH_EF,
        )

        assert result["indexed"] == 3

    def test_run_propagates_http_error(self) -> None:
        import requests as req_lib

        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_lib.HTTPError("503")

        with (
            patch(
                "scripts.index_published_articles.requests.get",
                return_value=mock_resp,
            ),
            pytest.raises(req_lib.HTTPError),
        ):
            run(source="https://viney.ca/search.json")

    def test_run_uses_correct_collection_name(self) -> None:
        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None

        client = _ephemeral_client()

        with patch(
            "scripts.index_published_articles.requests.get",
            return_value=mock_resp,
        ):
            run(
                source="https://viney.ca/search.json",
                _client=client,
                _embedding_function=_HASH_EF,
            )

        collection_names = [c.name for c in client.list_collections()]
        assert COLLECTION_NAME in collection_names


# ---------------------------------------------------------------------------
# Import smoke test
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """All public symbols import without errors."""
    from scripts.index_published_articles import (  # noqa: F401
        COLLECTION_NAME,
        _categories_to_str,
        _make_doc_id,
        fetch_search_json,
        index_articles,
        run,
    )

    assert COLLECTION_NAME == "published_articles"
    assert DEFAULT_SOURCE == "https://viney.ca/search.json"
    assert callable(_make_doc_id)
    assert callable(_categories_to_str)
    assert callable(fetch_search_json)
    assert callable(index_articles)
    assert callable(run)
