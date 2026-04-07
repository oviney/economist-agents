#!/usr/bin/env python3
"""
Article Archive - Searchable archive of published articles via ChromaDB.

Provides Topic Scout with duplicate-detection capability by indexing published
articles into a ChromaDB vector store and exposing similarity search.

Features:
- Persistent ChromaDB collection ``published_articles`` (cosine distance)
- Index individual articles with structured metadata
- Similarity search with configurable threshold
- Backfill from a directory of Jekyll-style markdown posts

Usage:
    from scripts.article_archive import ArticleArchive

    archive = ArticleArchive()
    archive.index_article(
        title="Why AI Testing is Broken",
        thesis="Automated test generation raises quality illusions.",
        categories="testing,ai",
        date="2026-04-05",
        file_path="_posts/2026-04-05-why-ai-testing-is-broken.md",
    )

    results = archive.find_similar_topics("AI test generation quality", threshold=0.8)
    for r in results:
        print(r["title"], r["similarity"])
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not installed. ArticleArchive in fallback mode.")

# Sentinel so callers can distinguish "use the ChromaDB default" from None
_USE_DEFAULT_EF = object()

# ChromaDB collection name for published articles
COLLECTION_NAME = "published_articles"

# Frontmatter delimiter pattern
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and return (frontmatter_dict, body_text).

    Args:
        content: Full markdown file content.

    Returns:
        Tuple of (frontmatter dict, body string).  If no frontmatter is
        found the dict is empty and body is the full content.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse frontmatter YAML: %s", exc)
        frontmatter = {}

    body = content[match.end():]
    return frontmatter, body


def _extract_thesis(body: str) -> str:
    """Extract thesis from the first two non-empty paragraphs of the body.

    Args:
        body: Article body text (after frontmatter).

    Returns:
        Concatenated first two paragraphs, stripped of markdown headings and
        blank lines.
    """
    paragraphs = [
        p.strip()
        for p in body.split("\n\n")
        if p.strip() and not p.strip().startswith("#")
    ]
    thesis_parts = paragraphs[:2]
    return " ".join(thesis_parts)


def _categories_to_str(categories: Any) -> str:
    """Normalise a categories value to a comma-separated string.

    Args:
        categories: A string, list, or other value from frontmatter.

    Returns:
        Comma-separated string of categories.
    """
    if isinstance(categories, list):
        return ",".join(str(c) for c in categories)
    return str(categories) if categories is not None else ""


class ArticleArchive:
    """Searchable archive of published articles backed by ChromaDB.

    The archive stores each article as a single document whose text is the
    concatenation of ``title``, ``thesis`` and ``summary``.  Metadata fields
    (title, thesis, date, categories, file_path) are stored alongside the
    document for retrieval.

    Graceful Degradation:
    - If ChromaDB is unavailable: all mutating methods are no-ops; search
      returns an empty list with a logged warning.
    - If the collection is empty: search returns an empty list.
    """

    def __init__(
        self,
        persist_directory: str = ".chromadb",
        *,
        _client: Any = None,
        _embedding_function: Any = _USE_DEFAULT_EF,
    ) -> None:
        """Initialise the ArticleArchive.

        Args:
            persist_directory: Path to the ChromaDB persistence directory.
                Ignored when ``_client`` is provided (used in tests).
            _client: Optional pre-built ChromaDB client (e.g. EphemeralClient
                for tests).  When supplied ``persist_directory`` is ignored.
            _embedding_function: Optional embedding function to pass to the
                ChromaDB collection.  Pass ``None`` to let ChromaDB use its
                default.  Primarily used in tests to inject an offline-capable
                embedding function so tests do not require network access.
        """
        self.persist_directory = persist_directory
        self.client: Any = None
        self.collection: Any = None

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB unavailable — ArticleArchive disabled.")
            return

        try:
            if _client is not None:
                self.client = _client
            else:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                    ),
                )

            collection_kwargs: dict[str, Any] = {
                "name": COLLECTION_NAME,
                "metadata": {
                    "description": "Published Economist-style articles for duplicate detection",
                    "hnsw:space": "cosine",
                },
            }
            if _embedding_function is not _USE_DEFAULT_EF:
                collection_kwargs["embedding_function"] = _embedding_function

            self.collection = self.client.get_or_create_collection(**collection_kwargs)
            logger.info(
                "ArticleArchive ready — %d articles indexed.",
                self.collection.count(),
            )
        except Exception as exc:
            logger.error("ArticleArchive initialisation failed: %s", exc)
            self.client = None
            self.collection = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_article(
        self,
        title: str,
        thesis: str,
        date: str,
        categories: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Index a single article into the archive.

        The document text stored in ChromaDB is the ``thesis``.
        If an article with the same ``file_path`` already exists it is replaced.

        Args:
            title: Article headline.
            thesis: Core argument extracted from the first two body paragraphs.
            date: Publication date in ``YYYY-MM-DD`` format.
            categories: Comma-separated category tags.
            file_path: Relative or absolute path to the source ``.md`` file.
                When empty, the doc ID falls back to ``"{title}_{date}"``.

        Returns:
            dict with ``success`` (bool), ``id`` (str), and ``total_indexed``
            (int) on success, or ``success`` (bool) and ``error`` (str) on
            failure.  The stored metadata includes an ``indexed_at`` ISO-8601
            UTC timestamp added automatically on each upsert.
        """
        if self.collection is None:
            return {
                "success": False,
                "error": "ArticleArchive is not available (ChromaDB missing).",
                "id": "",
            }

        doc_id = file_path if file_path else f"{title}_{date}"

        metadata: dict[str, str] = {
            "title": title,
            "thesis": thesis,
            "date": date,
            "categories": categories,
            "file_path": file_path,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # upsert so re-indexing the same article is idempotent
            self.collection.upsert(
                documents=[thesis],
                metadatas=[metadata],
                ids=[doc_id],
            )
            logger.debug("Indexed article '%s' (id=%s).", title, doc_id)
        except Exception as exc:
            logger.error("Failed to index article '%s': %s", title, exc)
            return {"success": False, "error": str(exc), "id": doc_id}

        return {"success": True, "id": doc_id, "total_indexed": self.collection.count()}

    def find_similar_topics(
        self,
        query: str,
        threshold: float = 0.6,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search the archive for articles similar to *query*.

        Args:
            query: Free-text topic or thesis to search for.
            threshold: Minimum cosine similarity score (0–1).  Only articles
                with ``similarity >= threshold`` are returned.
            n_results: Maximum number of results to return before threshold
                filtering.

        Returns:
            List of dicts, each containing the article schema fields plus a
            ``"similarity"`` key (float in [0, 1]).  Sorted by similarity
            descending.  Returns ``[]`` if the archive is unavailable or empty.
        """
        if self.collection is None:
            logger.warning("ArticleArchive unavailable — returning empty results.")
            return []

        if not query.strip():
            return []

        count = self.collection.count()
        if count == 0:
            return []

        # Clamp n_results to what the collection actually holds
        effective_n = min(n_results, count)

        try:
            raw = self.collection.query(
                query_texts=[query],
                n_results=effective_n,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ArticleArchive query failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        if not (raw.get("documents") and raw["documents"][0]):
            return results

        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0]
        raw_distances = raw.get("distances", [[]])[0]
        # Pad missing distances with 0.0 (→ similarity 1.0) so every document
        # in the response has a corresponding distance value.  ChromaDB
        # guarantees a distances list when include=["distances"] is requested,
        # but guard defensively; the calling test documents this expectation.
        distances: list[float] = list(raw_distances) + [0.0] * max(
            0, len(documents) - len(raw_distances)
        )

        for doc, meta, distance in zip(documents, metadatas, distances, strict=False):
            # _doc is the stored document text; we return metadata fields instead
            # ChromaDB cosine distance is in [0, 2]; similarity = 1 - distance
            similarity = round(1.0 - float(distance), 4)
            if similarity < threshold:
                continue
            results.append(
                {
                    "title": meta.get("title", ""),
                    "thesis": doc,
                    "date": meta.get("date", ""),
                    "categories": meta.get("categories", ""),
                    "file_path": meta.get("file_path", ""),
                    "similarity": similarity,
                }
            )

        results.sort(key=lambda r: r["similarity"], reverse=True)
        return results

    def backfill_from_directory(self, posts_dir: str | Path) -> int:
        """Index all ``.md`` files found in *posts_dir*.

        Reads each file, extracts YAML frontmatter, derives the thesis from
        the first two body paragraphs, and calls :meth:`index_article`.

        Args:
            posts_dir: Directory containing Jekyll-style markdown posts.

        Returns:
            Number of articles successfully indexed.

        Raises:
            FileNotFoundError: If *posts_dir* does not exist.
        """
        posts_path = Path(posts_dir)
        if not posts_path.exists():
            raise FileNotFoundError(f"Posts directory not found: {posts_path}")

        md_files = sorted(posts_path.glob("**/*.md"))
        indexed = 0

        for md_file in md_files:
            if md_file.name.lower() == "readme.md":
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
                frontmatter, body = _parse_frontmatter(content)

                title = str(frontmatter.get("title", md_file.stem))
                date = str(frontmatter.get("date", ""))
                raw_categories = frontmatter.get("categories", "")
                categories = _categories_to_str(raw_categories)

                thesis = _extract_thesis(body)

                self.index_article(
                    title=title,
                    thesis=thesis,
                    categories=categories,
                    date=date,
                    file_path=str(md_file),
                )
                indexed += 1
            except Exception as exc:
                logger.warning("Skipping %s: %s", md_file.name, exc)
                continue

        logger.info("Backfill complete — %d/%d articles indexed.", indexed, len(md_files))
        return indexed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the number of articles currently in the archive.

        Returns:
            Integer count, or 0 if ChromaDB is unavailable.
        """
        if self.collection is None:
            return 0
        return self.collection.count()

    def search(
        self,
        query: str,
        threshold: float = 0.6,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Alias for :meth:`find_similar_topics` — used by the MCP server.

        Args:
            query: Free-text topic or thesis to search for.
            threshold: Minimum cosine similarity score (0–1).
            n_results: Maximum number of results to return.

        Returns:
            List of matching article dicts with a ``similarity`` key.
        """
        return self.find_similar_topics(query, threshold=threshold, n_results=n_results)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the archive.

        Returns:
            dict with ``available`` (bool), ``total_articles`` (int),
            ``date_range`` (dict with ``earliest``/``latest`` str),
            and ``category_distribution`` (dict mapping category to count).
        """
        if self.collection is None:
            return {"available": False, "total_articles": 0}

        total = self.collection.count()
        stats: dict[str, Any] = {
            "available": True,
            "total_articles": total,
            "date_range": {"earliest": None, "latest": None},
            "category_distribution": {},
        }

        if total == 0:
            return stats

        try:
            all_items = self.collection.get(include=["metadatas"])
            dates: list[str] = []
            categories: dict[str, int] = {}
            for meta in all_items.get("metadatas", []):
                if meta.get("date"):
                    dates.append(meta["date"])
                for cat in (meta.get("categories") or "").split(","):
                    cat = cat.strip()
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 1
            if dates:
                dates_sorted = sorted(dates)
                stats["date_range"] = {
                    "earliest": dates_sorted[0],
                    "latest": dates_sorted[-1],
                }
            stats["category_distribution"] = categories
        except Exception as exc:
            logger.warning("get_stats metadata fetch failed: %s", exc)
            stats["total_articles"] = 0

        return stats


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _make_doc_id(file_path: str) -> str:
    """Derive a stable document ID from a file path.

    Args:
        file_path: Relative or absolute path to the article file.

    Returns:
        A URL-safe string suitable for use as a ChromaDB document ID.
    """
    stem = Path(file_path).stem
    # Replace characters that may cause issues with some ChromaDB backends
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║ ARTICLE ARCHIVE — Published article similarity search          ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    archive = ArticleArchive()
    print(f"Articles indexed: {archive.count()}")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nSearching for: '{query}'\n")
        results = archive.find_similar_topics(query, threshold=0.5, n_results=5)
        if results:
            for i, r in enumerate(results, 1):
                print(
                    f"{i}. [{r['similarity']:.2f}] {r['title']} ({r['date']})"
                )
        else:
            print("No similar articles found.")
