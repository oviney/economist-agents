#!/usr/bin/env python3
"""
Topic Deduplicator - ChromaDB-backed similarity check for topic candidates.

Prevents publishing articles on topics already covered by querying
the ``published_articles`` ChromaDB collection and comparing
cosine-similarity scores against configurable thresholds.

Similarity tiers (matching issue #157 spec):
- > 0.8  → REJECT   — topic is a near-duplicate of existing content
- 0.6-0.8 → WARN    — related coverage exists; flag for editorial review
- < 0.6  → PASS     — novel topic; proceed normally

After successful publication, callers should invoke ``index_article()``
to keep the archive current.

Usage::

    from src.tools.topic_deduplicator import TopicDeduplicator

    deduplicator = TopicDeduplicator()
    filtered, flagged = deduplicator.filter_topics(topic_list)
    # later…
    deduplicator.index_article("My Published Article Title", article_text)
"""

import logging
import warnings
from typing import Any

logger = logging.getLogger(__name__)

# Similarity thresholds (spec from issue #157)
REJECT_THRESHOLD = 0.8  # cosine similarity above this → reject
WARN_THRESHOLD = 0.6  # cosine similarity above this (but ≤ REJECT) → warn

# Minimum topics to retain after filtering (fallback: lower threshold if all dropped)
MIN_TOPICS_AFTER_FILTER = 1

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    warnings.warn(
        "ChromaDB not installed. TopicDeduplicator running in pass-through mode.",
        stacklevel=2,
    )


class TopicDeduplicator:
    """
    ChromaDB-backed topic deduplication for the Economist content pipeline.

    Queries the ``published_articles`` collection to detect near-duplicate
    topics before they enter the editorial board vote.

    Graceful degradation:
    - If ChromaDB is unavailable: all topics pass through unmodified.
    - If the collection is empty: all topics pass through unmodified.
    - If a query fails: logs a warning and passes the topic through.

    Args:
        collection_name: ChromaDB collection to query/write.
        persist_directory: ChromaDB persistence directory.
        reject_threshold: Cosine similarity above which a topic is rejected.
        warn_threshold: Cosine similarity above which a topic is flagged.

    Example::

        dedup = TopicDeduplicator()
        topics = [{"topic": "AI Testing Trends"}, {"topic": "Unit Testing Basics"}]
        kept, flagged = dedup.filter_topics(topics)
    """

    def __init__(
        self,
        collection_name: str = "published_articles",
        persist_directory: str = ".chromadb",
        reject_threshold: float = REJECT_THRESHOLD,
        warn_threshold: float = WARN_THRESHOLD,
    ) -> None:
        """
        Initialise the deduplicator with ChromaDB connection.

        Args:
            collection_name: Name of the ChromaDB collection.
            persist_directory: Path to ChromaDB persistence storage.
            reject_threshold: Similarity cutoff for rejection (default 0.8).
            warn_threshold: Similarity cutoff for warning (default 0.6).
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.reject_threshold = reject_threshold
        self.warn_threshold = warn_threshold
        self.client: Any = None
        self.collection: Any = None

        if not CHROMADB_AVAILABLE:
            logger.warning(
                "ChromaDB unavailable — TopicDeduplicator in pass-through mode"
            )
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
                metadata={
                    "description": "Published article titles and summaries for deduplication"
                },
            )
            logger.info(
                "TopicDeduplicator ready — %d articles in archive",
                self.collection.count(),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("TopicDeduplicator init failed: %s — pass-through mode", exc)
            self.client = None
            self.collection = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_topics(
        self, topics: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Filter candidate topics against the published-articles archive.

        Each topic dict must contain at least a ``"topic"`` key with the
        topic title/description string.

        Topics above ``reject_threshold`` are removed entirely.
        Topics between ``warn_threshold`` and ``reject_threshold`` are
        returned with a ``"dedup_warning"`` key added.
        Topics below ``warn_threshold`` pass through unchanged.

        When the collection is empty or ChromaDB is unavailable, all
        topics pass through unmodified (safe degradation).

        If *all* topics are filtered (extreme edge-case), the threshold
        is relaxed by 0.1 and the least-similar topic is allowed through
        so that the pipeline always has something to work with.

        Args:
            topics: List of topic dicts from scout_topics().

        Returns:
            Tuple of (kept_topics, rejected_topics).
            kept_topics includes warned topics (with ``"dedup_warning"``).
            rejected_topics lists those silently dropped (>reject_threshold).
        """
        if not topics:
            return [], []

        if self.collection is None or self.collection.count() == 0:
            logger.info("TopicDeduplicator: archive empty — all topics pass through")
            return topics, []

        kept: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        for topic_dict in topics:
            topic_text = topic_dict.get("topic", "")
            if not topic_text:
                kept.append(topic_dict)
                continue

            similarity, matched_title = self._query_similarity(topic_text)

            if similarity is None:
                # Query failed — pass through safely
                kept.append(topic_dict)
                continue

            if similarity > self.reject_threshold:
                logger.warning(
                    "🚫 DEDUP REJECT: '%s' (similarity=%.2f > %.2f with '%s')",
                    topic_text,
                    similarity,
                    self.reject_threshold,
                    matched_title,
                )
                rejected.append(
                    {
                        **topic_dict,
                        "dedup_similarity": similarity,
                        "dedup_matched": matched_title,
                    }
                )
            elif similarity > self.warn_threshold:
                logger.warning(
                    "⚠️  DEDUP WARN: '%s' (similarity=%.2f, related to '%s') — passed to editorial with flag",
                    topic_text,
                    similarity,
                    matched_title,
                )
                kept.append(
                    {
                        **topic_dict,
                        "dedup_warning": (
                            f"Related coverage exists: '{matched_title}' "
                            f"(similarity={similarity:.2f})"
                        ),
                        "dedup_similarity": similarity,
                        "dedup_matched": matched_title,
                    }
                )
            else:
                logger.info(
                    "✅ DEDUP PASS: '%s' (similarity=%.2f — novel topic)",
                    topic_text,
                    similarity,
                )
                kept.append(topic_dict)

        # Fallback: ensure at least MIN_TOPICS_AFTER_FILTER survive
        kept = self._apply_fallback(kept, rejected, topics)

        return kept, rejected

    def index_article(
        self, title: str, content: str, article_id: str | None = None
    ) -> bool:
        """
        Index a newly published article in the archive collection.

        Should be called after successful publication to keep the
        deduplication archive current.

        Args:
            title: Article title (used as primary query text).
            content: Full article text (first 500 chars stored for context).
            article_id: Optional unique ID; defaults to a hash of the title.

        Returns:
            True if indexing succeeded, False on error.
        """
        if self.collection is None:
            logger.warning(
                "TopicDeduplicator: cannot index article — ChromaDB unavailable"
            )
            return False

        try:
            import hashlib

            doc_id = article_id or hashlib.md5(title.encode()).hexdigest()
            # Store title + first 500 chars of body as the searchable document
            document = f"{title}\n\n{content[:500]}"
            self.collection.upsert(
                ids=[doc_id],
                documents=[document],
                metadatas=[{"title": title}],
            )
            logger.info("📚 Indexed article in archive: '%s'", title)
            return True
        except Exception as exc:
            logger.warning("Failed to index article '%s': %s", title, exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query_similarity(self, topic_text: str) -> tuple[float | None, str]:
        """
        Query ChromaDB for the most similar published article.

        Args:
            topic_text: Topic string to check against the archive.

        Returns:
            Tuple of (highest_similarity, matched_title).
            Returns (None, "") if the query fails.
        """
        try:
            results = self.collection.query(
                query_texts=[topic_text],
                n_results=1,
                include=["distances", "metadatas"],
            )
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            if not distances:
                return 0.0, ""

            # ChromaDB cosine distance is in [0, 2]; convert to similarity [0, 1]
            # distance = 0 → identical; distance = 2 → opposite
            # similarity = 1 - (distance / 2)
            raw_distance = distances[0]
            similarity = 1.0 - (raw_distance / 2.0)
            matched_title = metadatas[0].get("title", "") if metadatas else ""
            return similarity, matched_title

        except Exception as exc:
            logger.warning("ChromaDB query failed for topic '%s': %s", topic_text, exc)
            return None, ""

    def _apply_fallback(
        self,
        kept: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        original: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Ensure at least MIN_TOPICS_AFTER_FILTER topics survive filtering.

        If all topics were rejected, rescue the one with the lowest
        similarity (most novel) and log a warning.

        Args:
            kept: Topics that passed the filter.
            rejected: Topics that were rejected.
            original: Original full list (used for rescue selection).

        Returns:
            Possibly augmented kept list.
        """
        if len(kept) >= MIN_TOPICS_AFTER_FILTER:
            return kept

        # All topics were rejected — rescue the least-similar one
        if not rejected:
            return kept

        best = min(rejected, key=lambda t: t.get("dedup_similarity", 1.0))
        logger.warning(
            "⚠️  DEDUP FALLBACK: all topics filtered — rescuing least-similar topic '%s' "
            "(similarity=%.2f). Consider refreshing topic generation.",
            best.get("topic", "unknown"),
            best.get("dedup_similarity", 0.0),
        )
        rescued = {
            k: v
            for k, v in best.items()
            if k not in ("dedup_similarity", "dedup_matched")
        }
        rescued["dedup_warning"] = (
            f"Rescued from rejection (all topics filtered); "
            f"original similarity={best.get('dedup_similarity', 0):.2f}"
        )
        return kept + [rescued]
