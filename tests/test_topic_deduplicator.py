#!/usr/bin/env python3
"""
Unit Tests for TopicDeduplicator

Tests cover:
- Pass-through when ChromaDB unavailable (module-level mock)
- Pass-through when collection is empty
- Rejection of near-duplicate topics (similarity > 0.8)
- Warning for related topics (0.6–0.8 similarity)
- Pass-through for novel topics (< 0.6 similarity)
- Fallback when all topics are filtered
- article indexing (upsert)
- filter_topics with empty input
- discover_topics() dedup integration in EconomistContentFlow

Usage::

    pytest tests/test_topic_deduplicator.py -v
"""

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.topic_deduplicator import (
    MIN_TOPICS_AFTER_FILTER,
    REJECT_THRESHOLD,
    WARN_THRESHOLD,
    TopicDeduplicator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deduplicator(distances: list[float] | None = None) -> TopicDeduplicator:
    """Return a TopicDeduplicator whose ChromaDB collection is fully mocked.

    Args:
        distances: List of distance values returned per query.
                   Defaults to [0.0] (identical match) for a single call.
    """
    if distances is None:
        distances = [0.0]

    mock_collection = MagicMock()
    mock_collection.count.return_value = 3  # non-empty archive

    # Each call to query() returns the next distance in the list
    call_index: dict[str, int] = {"i": 0}

    def _query(**kwargs: Any) -> dict[str, Any]:
        idx = call_index["i"] % len(distances)
        call_index["i"] += 1
        dist = distances[idx]
        return {
            "distances": [[dist]],
            "metadatas": [[{"title": "Existing Article"}]],
        }

    mock_collection.query.side_effect = _query

    dedup = TopicDeduplicator.__new__(TopicDeduplicator)
    dedup.collection_name = "published_articles"
    dedup.persist_directory = ".chromadb"
    dedup.reject_threshold = REJECT_THRESHOLD
    dedup.warn_threshold = WARN_THRESHOLD
    dedup.client = MagicMock()
    dedup.collection = mock_collection
    return dedup


def _topics(names: list[str]) -> list[dict[str, Any]]:
    """Build minimal topic dicts from a list of name strings."""
    return [{"topic": name, "score": 7.0} for name in names]


# ---------------------------------------------------------------------------
# Tests: filter_topics — core similarity tiers
# ---------------------------------------------------------------------------


class TestFilterTopicsSimilarityTiers:
    """Test the three similarity tiers: reject, warn, pass."""

    def test_novel_topic_passes_unchanged(self) -> None:
        """Topics with similarity < WARN_THRESHOLD pass without modification."""
        # distance = 1.4 → similarity = 1 - 1.4/2 = 0.3
        dedup = _make_deduplicator(distances=[1.4])
        kept, rejected = dedup.filter_topics(_topics(["Brand New Topic"]))

        assert len(kept) == 1
        assert len(rejected) == 0
        assert "dedup_warning" not in kept[0]

    def test_related_topic_passes_with_warning(self) -> None:
        """Topics with 0.6 < similarity ≤ 0.8 pass with a dedup_warning."""
        # distance = 0.5 → similarity = 1 - 0.5/2 = 0.75
        dedup = _make_deduplicator(distances=[0.5])
        kept, rejected = (
            dedup.filter_topics(_topics(["Related Topic"]))[0],
            dedup.filter_topics(_topics(["Related Topic"]))[1],
        )

        assert len(kept) == 1
        assert len(rejected) == 0
        assert "dedup_warning" in kept[0]
        assert (
            "Related" in kept[0]["dedup_warning"]
            or "Existing" in kept[0]["dedup_warning"]
        )

    def test_duplicate_topic_is_rejected(self) -> None:
        """Topics with similarity > REJECT_THRESHOLD are rejected.

        When all topics are rejected the fallback rescues the least-similar one
        rather than leaving the pipeline with zero candidates, so we verify the
        topic ends up in *rejected* initially (recorded there) and the returned
        kept list carries the rescue warning from the fallback.
        """
        # distance = 0.1 → similarity = 1 - 0.1/2 = 0.95  (above REJECT_THRESHOLD)
        dedup = _make_deduplicator(distances=[0.1])
        kept, rejected = dedup.filter_topics(_topics(["Duplicate Topic"]))

        # The topic was rejected by the threshold check (appears in rejected list)
        assert len(rejected) == 1
        assert rejected[0]["topic"] == "Duplicate Topic"
        assert rejected[0]["dedup_similarity"] > REJECT_THRESHOLD

        # Fallback rescues it because the pipeline needs at least one topic
        assert len(kept) == MIN_TOPICS_AFTER_FILTER
        assert "dedup_warning" in kept[0]

    def test_boundary_at_reject_threshold(self) -> None:
        """Similarity exactly at REJECT_THRESHOLD (0.8) should WARN not reject."""
        # distance such that similarity == REJECT_THRESHOLD exactly
        # similarity = 1 - d/2 = 0.8 → d = 0.4
        dedup = _make_deduplicator(distances=[0.4])
        kept, rejected = dedup.filter_topics(_topics(["Boundary Topic"]))

        # similarity is NOT > 0.8 (it equals 0.8) → warn tier
        assert len(kept) == 1
        assert len(rejected) == 0

    def test_multiple_topics_mixed_result(self) -> None:
        """Mixed-similarity topic lists are categorised correctly."""
        # distances per topic: reject, warn, pass
        dedup = _make_deduplicator(distances=[0.1, 0.5, 1.4])
        topics = _topics(["Dup", "Related", "Novel"])
        kept, rejected = dedup.filter_topics(topics)

        assert len(rejected) == 1
        assert rejected[0]["topic"] == "Dup"
        assert len(kept) == 2

        topic_names = [t["topic"] for t in kept]
        assert "Novel" in topic_names
        assert "Related" in topic_names

        related = next(t for t in kept if t["topic"] == "Related")
        assert "dedup_warning" in related

        novel = next(t for t in kept if t["topic"] == "Novel")
        assert "dedup_warning" not in novel


# ---------------------------------------------------------------------------
# Tests: filter_topics — edge cases
# ---------------------------------------------------------------------------


class TestFilterTopicsEdgeCases:
    """Edge cases: empty input, empty archive, query failure."""

    def test_empty_topic_list_returns_empty(self) -> None:
        """filter_topics([]) returns ([], []) without touching ChromaDB."""
        dedup = _make_deduplicator()
        kept, rejected = dedup.filter_topics([])
        assert kept == []
        assert rejected == []

    def test_empty_archive_passes_all_through(self) -> None:
        """When the collection has 0 docs, all topics pass unmodified."""
        dedup = _make_deduplicator()
        dedup.collection.count.return_value = 0
        topics = _topics(["Topic A", "Topic B"])
        kept, rejected = dedup.filter_topics(topics)
        assert kept == topics
        assert rejected == []

    def test_no_collection_passes_all_through(self) -> None:
        """When collection is None (ChromaDB error), all topics pass."""
        dedup = TopicDeduplicator.__new__(TopicDeduplicator)
        dedup.collection = None
        dedup.reject_threshold = REJECT_THRESHOLD
        dedup.warn_threshold = WARN_THRESHOLD
        kept, rejected = dedup.filter_topics(_topics(["A", "B"]))
        assert len(kept) == 2
        assert rejected == []

    def test_query_failure_passes_topic_through(self) -> None:
        """If ChromaDB raises an exception, the topic passes through safely."""
        dedup = _make_deduplicator()
        dedup.collection.query.side_effect = RuntimeError("DB unavailable")
        dedup.collection.count.return_value = 2
        kept, rejected = dedup.filter_topics(_topics(["Topic X"]))
        assert len(kept) == 1
        assert rejected == []

    def test_topic_with_empty_string_passes_through(self) -> None:
        """Topics with empty topic string are kept without querying."""
        dedup = _make_deduplicator()
        topics = [{"topic": "", "score": 5.0}]
        kept, rejected = dedup.filter_topics(topics)
        assert kept == topics
        assert rejected == []


# ---------------------------------------------------------------------------
# Tests: filter_topics — fallback
# ---------------------------------------------------------------------------


class TestFilterTopicsFallback:
    """When all topics are rejected the fallback rescues the best one."""

    def test_fallback_rescues_least_similar_topic(self) -> None:
        """If all topics are rejected, the one with lowest similarity is rescued."""
        # Two topics both above reject threshold; second is less similar
        dedup = _make_deduplicator(distances=[0.05, 0.2])  # sim=0.975, sim=0.9
        topics = _topics(["Near-identical", "Mostly-duplicate"])
        kept, rejected = dedup.filter_topics(topics)

        # Both were rejected, but the fallback rescues one
        assert len(kept) == MIN_TOPICS_AFTER_FILTER
        assert kept[0]["topic"] == "Mostly-duplicate"  # sim=0.9 < 0.975
        assert "dedup_warning" in kept[0]
        assert "Rescued" in kept[0]["dedup_warning"]


# ---------------------------------------------------------------------------
# Tests: index_article
# ---------------------------------------------------------------------------


class TestIndexArticle:
    """Tests for post-publication article indexing."""

    def test_index_article_calls_upsert(self) -> None:
        """index_article() calls collection.upsert with correct arguments."""
        dedup = _make_deduplicator()
        result = dedup.index_article("My Article", "Full article text here...")
        assert result is True
        dedup.collection.upsert.assert_called_once()
        call_kwargs = dedup.collection.upsert.call_args
        # metadatas should include the title
        metadatas = (
            call_kwargs.kwargs.get("metadatas") or call_kwargs.args[2]
            if call_kwargs.args
            else call_kwargs.kwargs["metadatas"]
        )
        assert metadatas[0]["title"] == "My Article"

    def test_index_article_no_collection_returns_false(self) -> None:
        """index_article() returns False when ChromaDB is unavailable."""
        dedup = TopicDeduplicator.__new__(TopicDeduplicator)
        dedup.collection = None
        result = dedup.index_article("Title", "Body")
        assert result is False

    def test_index_article_upsert_failure_returns_false(self) -> None:
        """index_article() returns False when upsert raises an exception."""
        dedup = _make_deduplicator()
        dedup.collection.upsert.side_effect = RuntimeError("write error")
        result = dedup.index_article("Title", "Body")
        assert result is False

    def test_index_article_custom_id(self) -> None:
        """Custom article_id is passed through to upsert."""
        dedup = _make_deduplicator()
        dedup.index_article("Title", "Body", article_id="custom-123")
        call_kwargs = dedup.collection.upsert.call_args.kwargs
        assert call_kwargs["ids"] == ["custom-123"]


# ---------------------------------------------------------------------------
# Tests: discover_topics() flow integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for CrewAI agent initialization",
)
class TestDiscoverTopicsDeduplication:
    """Integration tests for dedup wiring inside EconomistContentFlow."""

    def _build_flow(self, distances: list[float]) -> Any:
        """Create a flow with a mocked deduplicator.

        After ADR-0006 Phase 2 (epic #308) the flow no longer
        instantiates a CrewAI Stage4Crew at __init__ time — the
        Stage 4 logic runs inline through src.agent_sdk.pipeline.
        Nothing else needs patching at construction.

        Args:
            distances: Cosine distances returned by the mock ChromaDB
                collection.
        """
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()
        flow._deduplicator = _make_deduplicator(distances=distances)
        return flow

    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_novel_topic_reaches_editorial(
        self, mock_client: Mock, mock_scout: Mock
    ) -> None:
        """Novel topics (<0.6 sim) are returned to the editorial board."""
        mock_client.return_value = Mock()
        mock_scout.return_value = [
            {
                "topic": "Novel AI Insight",
                "total_score": 20,
                "hook": "",
                "thesis": "",
                "data_sources": [],
                "contrarian_angle": "",
                "talking_points": "",
            }
        ]
        # distance = 1.4 → similarity = 0.3 (novel)
        flow = self._build_flow(distances=[1.4])
        result = flow.discover_topics()
        assert len(result["topics"]) == 1
        assert "dedup_warning" not in result["topics"][0]

    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_duplicate_topic_filtered_before_editorial(
        self, mock_client: Mock, mock_scout: Mock
    ) -> None:
        """Duplicate topics (>0.8 sim) are removed before editorial board.

        Fallback rescues the topic with a dedup_warning so the pipeline
        always has at least one candidate.
        """
        mock_client.return_value = Mock()
        mock_scout.return_value = [
            {
                "topic": "Duplicate Topic",
                "total_score": 20,
                "hook": "",
                "thesis": "",
                "data_sources": [],
                "contrarian_angle": "",
                "talking_points": "",
            }
        ]
        # distance = 0.1 → similarity = 0.95 (reject)
        flow = self._build_flow(distances=[0.1])
        result = flow.discover_topics()
        # Fallback should rescue it with a warning
        assert len(result["topics"]) == MIN_TOPICS_AFTER_FILTER
        assert "dedup_warning" in result["topics"][0]

    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_related_topic_flagged_for_editorial(
        self, mock_client: Mock, mock_scout: Mock
    ) -> None:
        """Related topics (0.6–0.8 sim) pass but carry a dedup_warning."""
        mock_client.return_value = Mock()
        mock_scout.return_value = [
            {
                "topic": "Related Topic",
                "total_score": 18,
                "hook": "",
                "thesis": "",
                "data_sources": [],
                "contrarian_angle": "",
                "talking_points": "",
            }
        ]
        # distance = 0.5 → similarity = 0.75 (warn tier)
        flow = self._build_flow(distances=[0.5])
        result = flow.discover_topics()
        assert len(result["topics"]) == 1
        assert "dedup_warning" in result["topics"][0]

    def test_publish_article_indexes_in_archive(self) -> None:
        """publish_article() calls deduplicator.index_article after publishing."""
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        flow.state["quality_result"] = {
            "article": "---\ntitle: Published\n---\n\nContent here.",
            "editorial_score": 87,
            "gates_passed": 5,
        }
        flow.state["selected_topic"] = {"topic": "Published Topic"}

        mock_dedup = MagicMock()
        flow._deduplicator = mock_dedup

        result = flow.publish_article()

        assert result["status"] == "published"
        mock_dedup.index_article.assert_called_once_with(
            title="Published Topic",
            content="---\ntitle: Published\n---\n\nContent here.",
        )
