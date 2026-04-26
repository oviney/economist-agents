"""Integration tests for the rewritten EconomistContentFlow.

After ADR-0006 Phase 2 (epic #308) the flow no longer wraps CrewAI
crews; ``generate_content`` now calls ``src.agent_sdk.pipeline.run_pipeline``
directly. These tests mock the pipeline and the per-stage adapters so
each method can be exercised in isolation without spending API budget.

Replaces the now-skipped ``tests/test_economist_flow.py`` and the
``TestFlowOrchestration`` block in ``tests/test_production_integration.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.economist_agents.flow import (
    MAX_REVISIONS,
    PUBLISH_THRESHOLD,
    EconomistContentFlow,
)


@dataclass
class _FakePipelineResult:
    """Stand-in for the real PipelineResult used by run_pipeline."""

    article: str
    chart_data: dict
    editorial_score: int
    gates_passed: int
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    total_cost_usd: float = 0.05
    writer_cost_usd: float = 0.04
    graphics_cost_usd: float = 0.01
    writer_model: str = "claude-sonnet-4-6"
    graphics_model: str = "claude-sonnet-4-6"
    stage3_seconds: float = 1.0
    stage4_seconds: float = 0.01
    article_chars: int = 500


_VALID_FRONTMATTER = (
    '---\nlayout: post\ntitle: "Specific Test Title"\n'
    'date: 2026-04-26\nauthor: "Test"\n'
    'description: "A concise SEO-friendly test article description here"\n'
    'categories: ["quality-engineering"]\n'
    "image: /assets/images/test.png\n---\n\nBody paragraph here.\n"
)


def _passing_pipeline_result() -> _FakePipelineResult:
    return _FakePipelineResult(
        article=_VALID_FRONTMATTER,
        chart_data={"title": "Chart"},
        editorial_score=88,
        gates_passed=5,
        publication_ready=True,
        publication_validator_passed=True,
        publication_validator_issues=[],
    )


# ─── stage 1 ────────────────────────────────────────────────────────────


class TestDiscoverTopics:
    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_normalises_scout_scores(self, mock_client: Mock, mock_scout: Mock) -> None:
        mock_client.return_value = Mock()
        mock_scout.return_value = [
            {"topic": "Topic A", "total_score": 25},
            {"topic": "Topic B", "total_score": 15},
        ]
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        # Echo whatever topics get passed in so we can read the
        # post-normalisation scores back.
        flow._deduplicator.filter_topics.side_effect = lambda topics: (topics, [])

        result = flow.discover_topics()

        assert "topics" in result
        assert "timestamp" in result
        # 25/25 * 10 == 10.0; 15/25 * 10 == 6.0
        scores = [t["score"] for t in result["topics"]]
        assert scores == [10.0, 6.0]

    @patch("src.economist_agents.flow.scout_topics", return_value=[])
    @patch("src.economist_agents.flow.create_llm_client")
    def test_raises_when_scout_empty_after_retry(
        self, mock_client: Mock, mock_scout: Mock
    ) -> None:
        mock_client.return_value = Mock()
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        flow._deduplicator.filter_topics.return_value = ([], [])
        with pytest.raises(ValueError, match="no topics"):
            flow.discover_topics()


# ─── stage 2 ────────────────────────────────────────────────────────────


class TestEditorialReview:
    @patch("src.economist_agents.flow.run_editorial_board")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_picks_board_top_pick(self, mock_client: Mock, mock_board: Mock) -> None:
        mock_client.return_value = Mock()
        mock_board.return_value = {
            "top_pick": {
                "topic": "Winner",
                "weighted_score": 8.5,
                "original_topic": {"hook": "h", "thesis": "t"},
            },
            "consensus": True,
            "dissenting_views": [],
        }
        flow = EconomistContentFlow()
        topics = {"topics": [{"topic": "Winner", "raw": {}, "score": 8.0}]}

        result = flow.editorial_review(topics)

        assert result["topic"] == "Winner"
        assert result["score"] == 8.5
        assert result["consensus"] is True

    @patch("src.economist_agents.flow.run_editorial_board")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_falls_back_to_highest_scored(
        self, mock_client: Mock, mock_board: Mock
    ) -> None:
        mock_client.return_value = Mock()
        mock_board.return_value = {"top_pick": None}
        flow = EconomistContentFlow()
        topics = {
            "topics": [
                {"topic": "Low", "score": 3.0},
                {"topic": "High", "score": 9.0},
            ]
        }

        result = flow.editorial_review(topics)

        assert result["topic"] == "High"

    def test_empty_topics_raises(self) -> None:
        flow = EconomistContentFlow()
        with pytest.raises(ValueError, match="No topics"):
            flow.editorial_review({"topics": []})


# ─── stage 3 ────────────────────────────────────────────────────────────


class TestGenerateContent:
    @patch("src.economist_agents.flow.generate_featured_image", return_value=False)
    @patch("src.economist_agents.flow.asyncio.run")
    def test_calls_pipeline_and_returns_article(
        self, mock_asyncio_run: Mock, mock_image: Mock
    ) -> None:
        mock_asyncio_run.return_value = _passing_pipeline_result()
        flow = EconomistContentFlow()

        result = flow.generate_content({"topic": "AI Testing"})

        # state preserved
        assert flow.state["selected_topic"]["topic"] == "AI Testing"
        # pipeline outputs propagated
        assert result["article"].startswith("---")
        assert result["chart_data"] == {"title": "Chart"}
        assert result["publication_validator_passed"] is True
        assert result["editorial_score"] == 88
        assert result["gates_passed"] == 5
        # image generation attempted; default returned
        assert result["featured_image"] == "/assets/images/blog-default.svg"

    @patch("src.economist_agents.flow.generate_featured_image", return_value=True)
    @patch("src.economist_agents.flow.asyncio.run")
    def test_uses_dalle_image_when_generated(
        self, mock_asyncio_run: Mock, mock_image: Mock
    ) -> None:
        mock_asyncio_run.return_value = _passing_pipeline_result()
        flow = EconomistContentFlow()

        result = flow.generate_content({"topic": "AI Coding Assistants"})

        assert result["featured_image"] == "/assets/images/ai-coding-assistants.png"


# ─── stage 4 routing ────────────────────────────────────────────────────


class TestQualityGate:
    def _draft(self, **overrides: Any) -> dict[str, Any]:
        draft = {
            "article": _VALID_FRONTMATTER,
            "featured_image": "/assets/images/test.png",
            "editorial_score": 88,
            "gates_passed": 5,
            "publication_validator_passed": True,
            "publication_validator_issues": [],
        }
        draft.update(overrides)
        return draft

    def test_publish_when_score_and_validator_pass(self) -> None:
        flow = EconomistContentFlow()
        decision = flow.quality_gate(self._draft())
        assert decision == "publish"
        assert flow.state["decision"] == "publish"

    def test_revision_when_score_below_threshold(self) -> None:
        flow = EconomistContentFlow()
        decision = flow.quality_gate(self._draft(editorial_score=PUBLISH_THRESHOLD - 1))
        assert decision == "revision"
        assert "below" in flow.state["revision_reason"]

    def test_revision_when_validator_fails(self) -> None:
        flow = EconomistContentFlow()
        draft = self._draft(
            publication_validator_passed=False,
            publication_validator_issues=[
                {
                    "check": "word_count",
                    "severity": "CRITICAL",
                    "message": "too short",
                }
            ],
        )
        decision = flow.quality_gate(draft)
        assert decision == "revision"
        # Feedback contains the issue message; the check name is in the
        # log line but not in the feedback payload.
        assert any("too short" in m for m in flow.state["revision_feedback"])

    def test_frontmatter_schema_failure_routes_to_revision(self) -> None:
        flow = EconomistContentFlow()
        # Strip required frontmatter to trigger schema rejection
        bad = self._draft(article="No frontmatter here at all.\n")
        decision = flow.quality_gate(bad)
        assert decision == "revision"
        assert "schema" in flow.state["revision_reason"].lower()


# ─── publish + revise terminal paths ────────────────────────────────────


class TestPublishArticle:
    def test_publishes_and_indexes(self) -> None:
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        flow.state["selected_topic"] = {"topic": "Indexed Topic"}
        flow.state["quality_result"] = {
            "article": _VALID_FRONTMATTER,
            "editorial_score": 90,
            "gates_passed": 5,
        }

        result = flow.publish_article()

        assert result["status"] == "published"
        flow._deduplicator.index_article.assert_called_once()
        kwargs = flow._deduplicator.index_article.call_args.kwargs
        assert kwargs["title"] == "Indexed Topic"


class TestRequestRevision:
    @patch("src.economist_agents.flow.asyncio.run")
    def test_succeeds_on_retry(self, mock_asyncio_run: Mock) -> None:
        mock_asyncio_run.return_value = _passing_pipeline_result()
        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "Retry Me"}
        flow.state["revision_feedback"] = ["fix the ending"]
        flow.state["article_draft"] = {"featured_image": "/assets/images/test.png"}

        result = flow.request_revision()

        assert result["status"] == "published"
        assert result["retry_count"] == 1

    @patch("src.economist_agents.flow.asyncio.run")
    def test_quarantines_when_retry_still_fails(
        self, mock_asyncio_run: Mock, tmp_path
    ) -> None:
        failing = _passing_pipeline_result()
        failing.publication_validator_passed = False
        failing.publication_validator_issues = [
            {
                "check": "word_count",
                "severity": "CRITICAL",
                "message": "still too short",
            }
        ]
        failing.editorial_score = 40
        mock_asyncio_run.return_value = failing

        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "Stuck Topic"}
        flow.state["revision_feedback"] = ["fix"]
        flow.state["article_draft"] = {"featured_image": "/assets/images/test.png"}

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert "quarantine_path" in result

    def test_exhausted_retry_returns_needs_revision(self) -> None:
        flow = EconomistContentFlow()
        flow.state["retry_count"] = MAX_REVISIONS
        flow.state["quality_result"] = {"editorial_score": 50, "gates_passed": 2}
        flow.state["revision_reason"] = "out of retries"

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert result["retry_count"] == MAX_REVISIONS


# ─── helper ─────────────────────────────────────────────────────────────


class TestPatchFrontmatter:
    def test_overrides_image_path(self) -> None:
        article = "---\nlayout: post\ntitle: T\nimage: /old.png\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(
            article, "/assets/images/new.png"
        )
        assert "image: /assets/images/new.png" in patched
        assert "/old.png" not in patched

    def test_renames_summary_to_description(self) -> None:
        article = "---\nlayout: post\ntitle: T\nsummary: Hello\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(article, "")
        assert "description: Hello" in patched
        assert "summary:" not in patched

    def test_no_op_when_not_frontmatter(self) -> None:
        article = "Plain text without delimiters."
        assert EconomistContentFlow._patch_frontmatter(article, "/x.png") == article
