#!/usr/bin/env python3
"""
Tests for scripts/article_archive.py

Tests the published-article archive backed by ChromaDB for:
1. index_article — stores articles with correct metadata
2. find_similar_topics — returns results above similarity threshold
3. backfill_from_directory — indexes all .md files in a directory
4. Graceful degradation when ChromaDB is unavailable
5. Edge-cases: empty collection, empty query, missing frontmatter, etc.

All tests that need a real vector store use ChromaDB's EphemeralClient so
no state persists between runs (no .chromadb directory is created).

Usage:
    pytest tests/test_article_archive.py -v
"""

import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Make sure the repo root is on sys.path so we can import scripts/
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.article_archive import (
    ArticleArchive,
    _categories_to_str,
    _extract_thesis,
    _make_doc_id,
    _parse_frontmatter,
)

# ---------------------------------------------------------------------------
# Offline embedding function for tests (no network / model download required)
# ---------------------------------------------------------------------------

try:
    from chromadb import Documents, EmbeddingFunction, Embeddings

    class _HashEmbedding(EmbeddingFunction):  # type: ignore[misc]
        """Deterministic bag-of-words embedding — works fully offline (no network/model download).

        Uses MD5 for word-to-bucket mapping. This is NOT a cryptographic use;
        MD5 is chosen for its fast, uniform distribution over hash buckets.
        """

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
# Helper: create an EphemeralClient for isolated in-memory testing
# ---------------------------------------------------------------------------

def _ephemeral_archive() -> ArticleArchive:
    """Return an ArticleArchive backed by an in-memory EphemeralClient."""
    try:
        import chromadb
        from chromadb.config import Settings

        # allow_reset=True so each call can start from a clean state
        client = chromadb.EphemeralClient(settings=Settings(allow_reset=True))
        client.reset()  # wipe any state from previous tests (shared in-process store)
        return ArticleArchive(_client=client, _embedding_function=_HASH_EF)
    except ImportError:
        pytest.skip("ChromaDB not installed — skipping test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def archive() -> ArticleArchive:
    """Fresh in-memory ArticleArchive for each test."""
    return _ephemeral_archive()


@pytest.fixture()
def posts_dir(tmp_path: Path) -> Path:
    """Temporary directory with sample markdown posts."""
    posts = tmp_path / "_posts"
    posts.mkdir()

    (posts / "2026-01-01-ai-testing.md").write_text(
        """\
---
layout: post
title: "Why AI Testing Fails Teams"
date: 2026-01-01
categories: [testing, ai]
image: /assets/charts/ai-testing.png
---

AI-generated tests create a quality illusion.  Survey data from 500 teams
reveals that higher coverage numbers correlate with *fewer* defect detections.

The root cause is mode collapse: language models optimise for passing existing
assertions rather than exposing edge-cases.
""",
        encoding="utf-8",
    )

    (posts / "2026-02-10-platform-engineering.md").write_text(
        """\
---
layout: post
title: "Platform Engineering Reduces Cognitive Load"
date: 2026-02-10
categories: platform-engineering
image: /assets/charts/platform.png
---

Platform teams abstract infrastructure complexity, freeing engineers to focus
on business logic.  A study of 200 organisations found a 40 % reduction in
time spent on undifferentiated heavy-lifting.

The gains are largest when the internal developer platform exposes a curated
set of golden-path workflows.
""",
        encoding="utf-8",
    )

    (posts / "README.md").write_text("# Posts\n\nThis directory holds blog posts.")

    return posts


# ---------------------------------------------------------------------------
# Unit tests for module-level helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Unit tests for private helper functions."""

    def test_make_doc_id_simple(self) -> None:
        doc_id = _make_doc_id("_posts/2026-01-01-ai-testing.md")
        assert doc_id == "2026-01-01-ai-testing"

    def test_make_doc_id_replaces_special_chars(self) -> None:
        doc_id = _make_doc_id("some/path/hello world.md")
        assert " " not in doc_id

    def test_parse_frontmatter_valid(self) -> None:
        content = "---\ntitle: Hello\ndate: 2026-01-01\n---\n\nBody text."
        fm, body = _parse_frontmatter(content)
        assert fm["title"] == "Hello"
        assert "Body text." in body

    def test_parse_frontmatter_missing(self) -> None:
        content = "No frontmatter here."
        fm, body = _parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_frontmatter_invalid_yaml(self) -> None:
        content = "---\n: bad: yaml: : :\n---\nBody."
        fm, body = _parse_frontmatter(content)
        # Should not raise; frontmatter may be empty or partially parsed
        assert isinstance(fm, dict)

    def test_extract_thesis_two_paragraphs(self) -> None:
        body = "\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        thesis = _extract_thesis(body)
        assert "First paragraph." in thesis
        assert "Second paragraph." in thesis
        assert "Third paragraph." not in thesis

    def test_extract_thesis_skips_headings(self) -> None:
        body = "# Heading\n\nFirst real paragraph.\n\nSecond paragraph."
        thesis = _extract_thesis(body)
        assert "Heading" not in thesis
        assert "First real paragraph." in thesis

    def test_extract_thesis_empty_body(self) -> None:
        assert _extract_thesis("") == ""

    def test_categories_to_str_list(self) -> None:
        assert _categories_to_str(["testing", "ai"]) == "testing,ai"

    def test_categories_to_str_string(self) -> None:
        assert _categories_to_str("testing") == "testing"

    def test_categories_to_str_none(self) -> None:
        assert _categories_to_str(None) == ""


# ---------------------------------------------------------------------------
# Tests for ArticleArchive.index_article
# ---------------------------------------------------------------------------


class TestIndexArticle:
    """Tests for the index_article method."""

    def test_index_returns_doc_id(self, archive: ArticleArchive) -> None:
        """index_article returns a non-empty document ID."""
        doc_id = archive.index_article(
            title="Test Article",
            thesis="This is the thesis.",
            summary="Short summary.",
            categories="testing",
            date="2026-01-01",
            file_path="_posts/2026-01-01-test.md",
        )
        assert doc_id
        assert isinstance(doc_id, str)

    def test_index_increments_count(self, archive: ArticleArchive) -> None:
        """Indexing an article increases the collection count."""
        assert archive.count() == 0
        archive.index_article(
            title="Article A",
            thesis="Thesis A.",
            summary="Summary A.",
            categories="a",
            date="2026-01-01",
            file_path="_posts/a.md",
        )
        assert archive.count() == 1

    def test_index_multiple_articles(self, archive: ArticleArchive) -> None:
        """Multiple articles are all stored independently."""
        for i in range(3):
            archive.index_article(
                title=f"Article {i}",
                thesis=f"Thesis {i}.",
                summary=f"Summary {i}.",
                categories="testing",
                date=f"2026-01-0{i + 1}",
                file_path=f"_posts/article-{i}.md",
            )
        assert archive.count() == 3

    def test_index_is_idempotent(self, archive: ArticleArchive) -> None:
        """Re-indexing the same file_path does not create duplicate entries."""
        kwargs = {
            "title": "Same Article",
            "thesis": "Same thesis.",
            "summary": "Same summary.",
            "categories": "testing",
            "date": "2026-01-01",
            "file_path": "_posts/same.md",
        }
        archive.index_article(**kwargs)
        archive.index_article(**kwargs)
        assert archive.count() == 1

    def test_index_raises_when_unavailable(self) -> None:
        """index_article raises RuntimeError when ChromaDB is not available."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            arc = ArticleArchive()
        with pytest.raises(RuntimeError):
            arc.index_article(
                title="X",
                thesis="T",
                summary="S",
                categories="c",
                date="2026-01-01",
                file_path="x.md",
            )


# ---------------------------------------------------------------------------
# Tests for ArticleArchive.find_similar_topics
# ---------------------------------------------------------------------------


class TestFindSimilarTopics:
    """Tests for the find_similar_topics search method."""

    @pytest.fixture()
    def populated_archive(self, archive: ArticleArchive) -> ArticleArchive:
        """Archive pre-populated with two distinct articles."""
        archive.index_article(
            title="AI Testing Quality Illusion",
            thesis="AI test generation creates coverage without catching defects.",
            summary="500-team survey shows divergence between coverage and bug detection.",
            categories="testing,ai",
            date="2026-01-01",
            file_path="_posts/2026-01-01-ai-testing.md",
        )
        archive.index_article(
            title="Platform Engineering Cognitive Load",
            thesis="Internal developer platforms reduce cognitive overhead by 40 %.",
            summary="Research across 200 organisations demonstrates productivity gains.",
            categories="platform-engineering",
            date="2026-02-10",
            file_path="_posts/2026-02-10-platform.md",
        )
        return archive

    def test_returns_list(self, populated_archive: ArticleArchive) -> None:
        results = populated_archive.find_similar_topics("AI testing")
        assert isinstance(results, list)

    def test_result_has_required_keys(self, populated_archive: ArticleArchive) -> None:
        """Each result dict contains the required schema keys."""
        results = populated_archive.find_similar_topics("AI test quality", threshold=0.0)
        assert results  # at least one result
        required_keys = {"title", "thesis", "date", "categories", "file_path", "similarity"}
        for result in results:
            assert required_keys.issubset(result.keys())

    def test_threshold_filters_low_similarity(
        self, populated_archive: ArticleArchive
    ) -> None:
        """Results respect the similarity threshold."""
        results = populated_archive.find_similar_topics(
            "AI testing defects", threshold=0.8
        )
        for result in results:
            assert result["similarity"] >= 0.8

    def test_threshold_zero_returns_all(
        self, populated_archive: ArticleArchive
    ) -> None:
        """threshold=0 returns all documents (up to n_results)."""
        results = populated_archive.find_similar_topics("x", threshold=0.0, n_results=10)
        assert len(results) == 2

    def test_n_results_limits_output(self, populated_archive: ArticleArchive) -> None:
        """n_results caps results before threshold filtering."""
        results = populated_archive.find_similar_topics(
            "testing", threshold=0.0, n_results=1
        )
        assert len(results) <= 1

    def test_sorted_by_similarity_descending(
        self, populated_archive: ArticleArchive
    ) -> None:
        """Results are returned in descending similarity order."""
        results = populated_archive.find_similar_topics("testing", threshold=0.0)
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)

    def test_empty_query_returns_empty(
        self, populated_archive: ArticleArchive
    ) -> None:
        results = populated_archive.find_similar_topics("   ")
        assert results == []

    def test_empty_collection_returns_empty(self, archive: ArticleArchive) -> None:
        """An empty archive always returns an empty list."""
        results = archive.find_similar_topics("any query")
        assert results == []

    def test_unavailable_returns_empty(self) -> None:
        """find_similar_topics returns [] when ChromaDB is unavailable."""
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            arc = ArticleArchive()
        assert arc.find_similar_topics("any") == []


# ---------------------------------------------------------------------------
# Tests for ArticleArchive.backfill_from_directory
# ---------------------------------------------------------------------------


class TestBackfillFromDirectory:
    """Tests for the backfill_from_directory method."""

    def test_backfill_indexes_all_md_files(
        self, archive: ArticleArchive, posts_dir: Path
    ) -> None:
        """All .md files (except README) are indexed."""
        count = archive.backfill_from_directory(posts_dir)
        # 2 article files (README excluded)
        assert count == 2
        assert archive.count() == 2

    def test_backfill_skips_readme(
        self, archive: ArticleArchive, posts_dir: Path
    ) -> None:
        """README.md is excluded from indexing."""
        archive.backfill_from_directory(posts_dir)
        results = archive.find_similar_topics("README", threshold=0.0, n_results=10)
        titles = [r["title"] for r in results]
        assert all("README" not in t for t in titles)

    def test_backfill_extracts_frontmatter_title(
        self, archive: ArticleArchive, posts_dir: Path
    ) -> None:
        """Frontmatter title is stored in metadata."""
        archive.backfill_from_directory(posts_dir)
        results = archive.find_similar_topics(
            "AI testing fails", threshold=0.0, n_results=10
        )
        titles = [r["title"] for r in results]
        assert any("AI Testing Fails Teams" in t for t in titles)

    def test_backfill_extracts_categories_list(
        self, archive: ArticleArchive, posts_dir: Path
    ) -> None:
        """List-type categories are stored as comma-separated string."""
        archive.backfill_from_directory(posts_dir)
        results = archive.find_similar_topics(
            "AI testing fails", threshold=0.0, n_results=10
        )
        ai_article = next(
            (r for r in results if "AI Testing Fails Teams" in r["title"]), None
        )
        assert ai_article is not None
        assert "testing" in ai_article["categories"]
        assert "ai" in ai_article["categories"]

    def test_backfill_is_idempotent(
        self, archive: ArticleArchive, posts_dir: Path
    ) -> None:
        """Running backfill twice does not create duplicates."""
        archive.backfill_from_directory(posts_dir)
        archive.backfill_from_directory(posts_dir)
        assert archive.count() == 2  # same 2 articles, no duplicates

    def test_backfill_raises_on_missing_directory(
        self, archive: ArticleArchive, tmp_path: Path
    ) -> None:
        """FileNotFoundError is raised when the directory does not exist."""
        with pytest.raises(FileNotFoundError):
            archive.backfill_from_directory(tmp_path / "nonexistent")

    def test_backfill_handles_missing_frontmatter(
        self, archive: ArticleArchive, tmp_path: Path
    ) -> None:
        """Articles without frontmatter are indexed using the filename as title."""
        posts = tmp_path / "_posts"
        posts.mkdir()
        (posts / "2026-03-01-no-frontmatter.md").write_text(
            "This article has no YAML frontmatter at all.\n\nSecond paragraph here.",
            encoding="utf-8",
        )
        count = archive.backfill_from_directory(posts)
        assert count == 1

    def test_backfill_returns_zero_for_empty_directory(
        self, archive: ArticleArchive, tmp_path: Path
    ) -> None:
        """An empty directory returns 0 indexed articles."""
        posts = tmp_path / "empty_posts"
        posts.mkdir()
        assert archive.backfill_from_directory(posts) == 0


# ---------------------------------------------------------------------------
# Tests for ArticleArchive.count
# ---------------------------------------------------------------------------


class TestCount:
    """Tests for the count helper method."""

    def test_count_empty_archive(self, archive: ArticleArchive) -> None:
        assert archive.count() == 0

    def test_count_after_indexing(self, archive: ArticleArchive) -> None:
        archive.index_article("T", "Th", "S", "c", "2026-01-01", "f.md")
        assert archive.count() == 1

    def test_count_returns_zero_when_unavailable(self) -> None:
        with patch("scripts.article_archive.CHROMADB_AVAILABLE", False):
            arc = ArticleArchive()
        assert arc.count() == 0


# ---------------------------------------------------------------------------
# Import smoke test
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """The module and its public symbols import without errors."""
    from scripts.article_archive import (  # noqa: F401
        COLLECTION_NAME,
        ArticleArchive,
        _categories_to_str,
        _extract_thesis,
        _make_doc_id,
        _parse_frontmatter,
    )

    assert ArticleArchive is not None
    assert COLLECTION_NAME == "published_articles"
