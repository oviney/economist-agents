#!/usr/bin/env python3
"""
Article Archive - Published Topics Store

Provides ChromaDB-backed storage and semantic similarity search for published
articles, enabling topic deduplication across interactive (Claude Code) and
automated (pipeline) contexts.

Usage:
    from scripts.article_archive import ArticleArchive

    archive = ArticleArchive()
    archive.index_article("Title", "Thesis text", "2026-01-01", "tech", "posts/file.md")
    results = archive.search("similar topic query", threshold=0.6, n_results=5)
    stats = archive.get_stats()
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not installed. Article Archive in fallback mode.")


class ArticleArchive:
    """
    ChromaDB-backed store for published article metadata.

    Supports semantic similarity search for topic deduplication.

    Graceful Degradation:
    - If ChromaDB unavailable: returns empty results / failure dicts
    - If collection empty: returns empty results without error
    - If operation fails: catches exceptions, returns safe defaults
    """

    def __init__(
        self,
        collection_name: str = "published_articles",
        persist_directory: str = ".chromadb_archive",
        _client: Any = None,
    ) -> None:
        """
        Initialise the article archive with ChromaDB.

        Args:
            collection_name: ChromaDB collection name.
            persist_directory: Path for ChromaDB persistence files.
            _client: Optional pre-built ChromaDB client (used for testing to
                avoid persistent state). When provided, the chromadb package
                does not need to be installed.
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client: Any = None
        self.collection: Any = None

        # Injected client path — used in tests so no real ChromaDB is needed.
        if _client is not None:
            try:
                self.client = _client
                self.collection = _client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": "Published Economist articles for topic dedup"},
                )
                logger.info(
                    "Article Archive initialised (injected client): %d articles indexed",
                    self.collection.count(),
                )
            except Exception as exc:
                logger.error("Article Archive initialisation failed: %s", exc)
                self.client = None
                self.collection = None
            return

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB unavailable - Article Archive disabled")
            return

        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Published Economist articles for topic dedup"},
            )
            logger.info(
                "Article Archive initialised: %d articles indexed",
                self.collection.count(),
            )
        except Exception as exc:
            logger.error("Article Archive initialisation failed: %s", exc)
            self.client = None
            self.collection = None

    def search(
        self,
        query: str,
        threshold: float = 0.6,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search for published articles semantically similar to the query.

        Args:
            query: Topic description or title to search for.
            threshold: Minimum similarity score (0–1). Results below this are
                filtered out. Default 0.6.
            n_results: Maximum number of results to return. Default 5.

        Returns:
            List of matching article dicts, each containing:
            title, thesis, date, categories, file_path, similarity.
        """
        if not self.collection:
            return []
        if not query.strip():
            return []

        try:
            count = self.collection.count()
            if count == 0:
                return []

            actual_n = min(n_results, count)
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_n,
            )

            formatted: list[dict[str, Any]] = []
            if results and results.get("documents") and results["documents"][0]:
                distances = results.get("distances", [[]])[0] or [
                    0.0
                ] * len(results["documents"][0])
                # strict=False: distances list may be a fallback default (line above),
                # so we deliberately allow mismatched lengths rather than raising.
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    distances,
                    strict=False,
                ):
                    score = max(0.0, 1.0 - min(float(dist), 1.0))
                    if score >= threshold:
                        formatted.append(
                            {
                                "title": meta.get("title", ""),
                                "thesis": doc,
                                "date": meta.get("date", ""),
                                "categories": meta.get("categories", ""),
                                "file_path": meta.get("file_path", ""),
                                "similarity": round(score, 3),
                            }
                        )
            return formatted

        except Exception as exc:
            logger.error("Archive search failed: %s", exc)
            return []

    def index_article(
        self,
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
            date: Publication date string (e.g. "2026-01-15").
            categories: Comma-separated category tags.
            file_path: Relative path to the article file (used as unique ID).

        Returns:
            dict with:
            - success (bool): Whether indexing succeeded.
            - id (str): Document ID used in ChromaDB.
            - total_indexed (int): Total articles in archive after operation.
            - error (str): Error message, present only on failure.
        """
        if not self.collection:
            return {"success": False, "error": "ChromaDB unavailable", "id": ""}

        try:
            doc_id = file_path.strip() or f"{title}_{date}"
            self.collection.upsert(
                documents=[thesis],
                metadatas=[
                    {
                        "title": title,
                        "date": date,
                        "categories": categories,
                        "file_path": file_path,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
                ids=[doc_id],
            )
            return {
                "success": True,
                "id": doc_id,
                "total_indexed": self.collection.count(),
            }
        except Exception as exc:
            logger.error("Failed to index article '%s': %s", title, exc)
            return {"success": False, "error": str(exc), "id": ""}

    def get_stats(self) -> dict[str, Any]:
        """
        Return statistics about the published article archive.

        Returns:
            dict with:
            - available (bool): Whether ChromaDB is operational.
            - total_articles (int): Total indexed articles.
            - date_range (dict): earliest and latest publication dates.
            - category_distribution (dict[str, int]): Count per category tag.
        """
        if not self.collection:
            return {
                "available": False,
                "total_articles": 0,
                "date_range": {"earliest": None, "latest": None},
                "category_distribution": {},
            }

        try:
            count = self.collection.count()
            if count == 0:
                return {
                    "available": True,
                    "total_articles": 0,
                    "date_range": {"earliest": None, "latest": None},
                    "category_distribution": {},
                }

            all_items = self.collection.get(include=["metadatas"])
            metadatas: list[dict[str, Any]] = all_items.get("metadatas") or []

            dates: list[str] = sorted(
                m.get("date", "") for m in metadatas if m.get("date")
            )

            cat_dist: dict[str, int] = {}
            for m in metadatas:
                for cat in m.get("categories", "").split(","):
                    cat = cat.strip()
                    if cat:
                        cat_dist[cat] = cat_dist.get(cat, 0) + 1

            return {
                "available": True,
                "total_articles": count,
                "date_range": {
                    "earliest": dates[0] if dates else None,
                    "latest": dates[-1] if dates else None,
                },
                "category_distribution": cat_dist,
            }

        except Exception as exc:
            logger.error("Failed to compute archive stats: %s", exc)
            return {
                "available": True,
                "total_articles": 0,
                "date_range": {"earliest": None, "latest": None},
                "category_distribution": {},
            }
