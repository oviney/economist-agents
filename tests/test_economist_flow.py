#!/usr/bin/env python3
"""
Integration Tests for Economist Content Flow

Tests the Flow-based state-machine orchestration with @start/@listen/@router decorators.

Test Coverage:
1. Flow initialization and state management
2. Topic discovery via scout_topics adapter
3. Editorial review via run_editorial_board adapter
4. Stage3Crew integration via generate_content()
5. Stage4Crew + PublicationValidator routing (publish/revision)
6. Revision loop with feedback (1 retry)
7. Revision exhaustion

Usage:
    pytest tests/test_economist_flow.py -v
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

pytest.importorskip("crewai")

from src.economist_agents.flow import EconomistContentFlow

# Valid article stub for tests that need to pass schema validation
_VALID_ARTICLE = '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-04\nauthor: "Ouray Viney"\ndescription: "Test article for quality gate validation"\ncategories: ["quality-engineering"]\nimage: /assets/images/test.png\n---\n\nBody'


@pytest.mark.skip(
    reason=(
        "Obsolete after ADR-0006 Phase 2 (epic #308). These tests patch "
        "src.economist_agents.flow.Stage3Crew / Stage4Crew which no "
        "longer exist; flow.py now calls src.agent_sdk.pipeline."
        "run_pipeline directly. Filed #314 to add new flow tests."
    )
)
class TestEconomistFlow:
    """Integration tests for EconomistContentFlow."""

    @pytest.fixture
    def flow(self) -> EconomistContentFlow:
        """Create Flow instance for testing."""
        return EconomistContentFlow()

    def test_flow_initialization(self, flow: EconomistContentFlow) -> None:
        """Flow initializes with stage4_crew and state."""
        assert flow is not None
        assert hasattr(flow, "stage4_crew")
        assert hasattr(flow, "state")

    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_discover_topics_stage(
        self,
        mock_create_client: Mock,
        mock_scout: Mock,
        flow: EconomistContentFlow,
    ) -> None:
        """discover_topics() calls scout_topics and normalises scores."""
        mock_create_client.return_value = Mock()
        mock_scout.return_value = [
            {
                "topic": "AI Testing Paradox",
                "total_score": 20,
                "hook": "Hook A",
                "thesis": "Thesis A",
                "data_sources": [],
                "contrarian_angle": "Angle A",
                "talking_points": "Points A",
            },
            {
                "topic": "Quality Tax",
                "total_score": 15,
                "hook": "Hook B",
                "thesis": "Thesis B",
                "data_sources": [],
                "contrarian_angle": "Angle B",
                "talking_points": "Points B",
            },
        ]

        result = flow.discover_topics()

        assert "topics" in result
        assert "timestamp" in result
        assert len(result["topics"]) == 2
        # 20/25 * 10 = 8.0
        assert result["topics"][0]["score"] == 8.0
        # 15/25 * 10 = 6.0
        assert result["topics"][1]["score"] == 6.0
        assert result["topics"][0]["topic"] == "AI Testing Paradox"
        mock_scout.assert_called_once()

    @patch("src.economist_agents.flow.run_editorial_board")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_editorial_review_stage(
        self,
        mock_create_client: Mock,
        mock_board: Mock,
        flow: EconomistContentFlow,
    ) -> None:
        """editorial_review() calls run_editorial_board and selects top pick."""
        mock_create_client.return_value = Mock()
        mock_board.return_value = {
            "top_pick": {
                "topic": "AI Testing Paradox",
                "weighted_score": 8.5,
                "original_topic": {
                    "hook": "Hook A",
                    "thesis": "Thesis A",
                },
            },
            "consensus": True,
            "dissenting_views": [],
        }

        topics = {
            "topics": [
                {
                    "topic": "AI Testing Paradox",
                    "score": 8.0,
                    "hook": "Hook A",
                    "thesis": "Thesis A",
                    "raw": {"topic": "AI Testing Paradox"},
                },
            ],
            "timestamp": "2026-01-07T00:00:00Z",
        }

        result = flow.editorial_review(topics)

        assert result["topic"] == "AI Testing Paradox"
        assert result["score"] == 8.5
        assert result["consensus"] is True
        mock_board.assert_called_once()

    def test_editorial_review_fallback_no_top_pick(
        self, flow: EconomistContentFlow
    ) -> None:
        """editorial_review() falls back to highest score if board returns no top_pick."""
        with (
            patch("src.economist_agents.flow.create_llm_client") as mock_client,
            patch("src.economist_agents.flow.run_editorial_board") as mock_board,
        ):
            mock_client.return_value = Mock()
            mock_board.return_value = {
                "top_pick": None,
                "consensus": False,
                "dissenting_views": [],
            }

            topics = {
                "topics": [
                    {"topic": "Topic A", "score": 6.0, "hook": "", "thesis": ""},
                    {"topic": "Topic B", "score": 9.0, "hook": "", "thesis": ""},
                ],
            }

            result = flow.editorial_review(topics)
            assert result["topic"] == "Topic B"

    def test_editorial_review_empty_topics_raises(
        self, flow: EconomistContentFlow
    ) -> None:
        """editorial_review() raises ValueError on empty topic list."""
        with pytest.raises(ValueError, match="No topics"):
            flow.editorial_review({"topics": []})

    @patch("src.economist_agents.flow.Stage3Crew")
    def test_generate_content(
        self, mock_stage3_class: Mock, flow: EconomistContentFlow
    ) -> None:
        """generate_content() initializes Stage3Crew and preserves topic in state."""
        mock_instance = Mock()
        mock_instance.kickoff.return_value = {
            "article": "---\ntitle: Test\n---\n\nContent here",
            "chart_data": {"title": "Chart"},
        }
        mock_stage3_class.return_value = mock_instance

        selected = {"topic": "AI Testing", "score": 8.5, "hook": "", "thesis": ""}
        result = flow.generate_content(selected)

        mock_stage3_class.assert_called_once_with(topic="AI Testing")
        mock_instance.kickoff.assert_called_once()
        assert "article" in result
        assert flow.state["selected_topic"] == selected

    @patch("src.economist_agents.flow.PublicationValidator")
    @patch("src.economist_agents.flow.Stage4Crew")
    def test_quality_gate_publish(
        self, mock_stage4_class: Mock, mock_validator_class: Mock
    ) -> None:
        """quality_gate() routes to 'publish' when editorial score >= 80 and validation passes."""
        mock_s4 = Mock()
        mock_s4.kickoff.return_value = {
            "article": "Polished article",
            "editorial_score": 92,
            "gates_passed": 5,
        }
        mock_stage4_class.return_value = mock_s4

        mock_validator = Mock()
        mock_validator.validate.return_value = (True, [])
        mock_validator_class.return_value = mock_validator

        flow = EconomistContentFlow()
        draft = {"article": _VALID_ARTICLE, "chart_data": {"title": "Chart"}}
        decision = flow.quality_gate(draft)

        assert decision == "publish"
        assert flow.state["decision"] == "publish"
        # Verify Stage4Crew was called
        mock_s4.kickoff.assert_called_once()

    @patch("src.economist_agents.flow.Stage4Crew")
    def test_quality_gate_revision_failed_gates(self, mock_stage4_class: Mock) -> None:
        """quality_gate() routes to 'revision' when any editorial gate fails."""
        mock_s4 = Mock()
        mock_s4.kickoff.return_value = {
            "article": "Weak article",
            "editorial_score": 65,
            "gates_passed": 3,
            "specific_edits": ["Fix opening", "Add sources"],
        }
        mock_stage4_class.return_value = mock_s4

        flow = EconomistContentFlow()
        draft = {"article": _VALID_ARTICLE, "chart_data": {}}
        decision = flow.quality_gate(draft)

        assert decision == "revision"
        assert "3/5" in flow.state["revision_reason"]
        assert flow.state["revision_feedback"] == ["Fix opening", "Add sources"]

    @patch("src.economist_agents.flow.PublicationValidator")
    @patch("src.economist_agents.flow.Stage4Crew")
    def test_quality_gate_revision_validation_fails(
        self, mock_stage4_class: Mock, mock_validator_class: Mock
    ) -> None:
        """quality_gate() routes to 'revision' when validation fails despite good score."""
        mock_s4 = Mock()
        mock_s4.kickoff.return_value = {
            "article": "Good score but bad format",
            "editorial_score": 90,
            "gates_passed": 5,
        }
        mock_stage4_class.return_value = mock_s4

        mock_validator = Mock()
        mock_validator.validate.return_value = (
            False,
            [{"severity": "CRITICAL", "message": "Missing YAML frontmatter"}],
        )
        mock_validator_class.return_value = mock_validator

        flow = EconomistContentFlow()
        draft = {"article": _VALID_ARTICLE, "chart_data": {}}
        decision = flow.quality_gate(draft)

        assert decision == "revision"
        assert "validation failed" in flow.state["revision_reason"]
        assert "Missing YAML frontmatter" in flow.state["revision_feedback"]

    def test_publish_article(self, flow: EconomistContentFlow) -> None:
        """publish_article() returns publication metadata from state."""
        flow.state["quality_result"] = {
            "article": "# Published Article",
            "editorial_score": 92,
            "gates_passed": 5,
        }

        result = flow.publish_article()

        assert result["status"] == "published"
        assert result["editorial_score"] == 92
        assert result["gates_passed"] == 5
        assert result["article"] == "# Published Article"

    @patch("src.economist_agents.flow.PublicationValidator")
    @patch("src.economist_agents.flow.Stage3Crew")
    def test_revision_loop_succeeds(
        self,
        mock_stage3_class: Mock,
        mock_validator_class: Mock,
        flow: EconomistContentFlow,
    ) -> None:
        """request_revision() retries and succeeds on second attempt."""
        # Setup state as if quality_gate routed to revision
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_reason"] = "Editorial score 65/100"
        flow.state["revision_feedback"] = ["Fix opening"]
        flow.state["quality_result"] = {"editorial_score": 65, "gates_passed": 3}
        flow.state["retry_count"] = 0

        # Mock Stage3Crew for revision
        mock_s3 = Mock()
        mock_s3.kickoff.return_value = {
            "article": "Improved article",
            "chart_data": {},
        }
        mock_stage3_class.return_value = mock_s3

        # Mock Stage4Crew (already on flow instance)
        flow.stage4_crew = Mock()
        flow.stage4_crew.kickoff.return_value = {
            "article": "Polished improved article",
            "editorial_score": 88,
            "gates_passed": 5,
        }

        # Mock PublicationValidator
        mock_validator = Mock()
        mock_validator.validate.return_value = (True, [])
        mock_validator_class.return_value = mock_validator

        result = flow.request_revision()

        assert result["status"] == "published"
        assert result["editorial_score"] == 88
        assert result["retry_count"] == 1
        # Verify Stage3Crew was called with revision instructions
        topic_arg = mock_stage3_class.call_args[1]["topic"]
        assert "REVISION INSTRUCTIONS" in topic_arg
        assert "Fix opening" in topic_arg

    def test_revision_exhausted(self, flow: EconomistContentFlow) -> None:
        """request_revision() gives up after max retries."""
        flow.state["retry_count"] = 2  # Already used 2 retries (MAX_REVISIONS)
        flow.state["quality_result"] = {"editorial_score": 50, "gates_passed": 2}
        flow.state["revision_reason"] = "Still failing"

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert result["retry_count"] == 2
        assert result["revision_reason"] == "Still failing"


@pytest.mark.skip(
    reason=(
        "Obsolete after ADR-0006 Phase 2 (epic #308). These tests patch "
        "src.economist_agents.flow.Stage3Crew / Stage4Crew which no "
        "longer exist; flow.py now calls src.agent_sdk.pipeline."
        "run_pipeline directly. Filed #314 to add new flow tests."
    )
)
class TestResearchBackedRevision:
    """Tests for research-backed revision when sourcing issues detected."""

    @pytest.fixture
    def flow(self) -> EconomistContentFlow:
        return EconomistContentFlow()

    @patch("src.economist_agents.flow.PublicationValidator")
    @patch("src.economist_agents.flow.Stage3Crew")
    def test_sourcing_failure_triggers_research_rerun(
        self,
        mock_stage3_class: Mock,
        mock_validator_class: Mock,
        flow: EconomistContentFlow,
    ) -> None:
        """Revision with placeholder feedback re-runs Research Agent."""
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_reason"] = "Publication validation failed"
        flow.state["revision_feedback"] = ["Found 2 placeholder(s)"]
        flow.state["quality_result"] = {
            "editorial_score": 98,
            "gates_passed": 5,
            "article": (
                "Half of teams report improved outcomes [NEEDS SOURCE]. "
                "The market grew by 40% last year [NEEDS SOURCE]."
            ),
        }
        flow.state["retry_count"] = 0

        mock_s3 = Mock()
        mock_s3.kickoff.return_value = {
            "article": "Fixed article with real sources",
            "chart_data": {},
        }
        mock_stage3_class.return_value = mock_s3

        flow.stage4_crew = Mock()
        flow.stage4_crew.kickoff.return_value = {
            "article": "Polished article",
            "editorial_score": 95,
            "gates_passed": 5,
        }

        mock_validator = Mock()
        mock_validator.validate.return_value = (True, [])
        mock_validator_class.return_value = mock_validator

        with patch("crewai.Crew") as mock_crew_cls:
            mock_crew = Mock()
            mock_result = Mock()
            mock_result.raw = "McKinsey 2025 found 48% of teams improved."
            mock_crew.kickoff.return_value = mock_result
            mock_crew_cls.return_value = mock_crew

            result = flow.request_revision()

        assert result["status"] == "published"
        # Verify Stage3Crew received research supplement
        topic_arg = mock_stage3_class.call_args[1]["topic"]
        assert "ADDITIONAL VERIFIED SOURCES" in topic_arg

    @patch("src.economist_agents.flow.PublicationValidator")
    @patch("src.economist_agents.flow.Stage3Crew")
    def test_non_sourcing_failure_skips_research_rerun(
        self,
        mock_stage3_class: Mock,
        mock_validator_class: Mock,
        flow: EconomistContentFlow,
    ) -> None:
        """Revision for non-sourcing issues does NOT re-run Research Agent."""
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_reason"] = "Editorial score 65/100"
        flow.state["revision_feedback"] = ["Fix weak opening paragraph"]
        flow.state["quality_result"] = {
            "editorial_score": 65,
            "gates_passed": 3,
            "article": "In today's world, AI is changing everything.",
        }
        flow.state["retry_count"] = 0

        mock_s3 = Mock()
        mock_s3.kickoff.return_value = {"article": "Better opening", "chart_data": {}}
        mock_stage3_class.return_value = mock_s3

        flow.stage4_crew = Mock()
        flow.stage4_crew.kickoff.return_value = {
            "article": "Polished article",
            "editorial_score": 88,
            "gates_passed": 5,
        }

        mock_validator = Mock()
        mock_validator.validate.return_value = (True, [])
        mock_validator_class.return_value = mock_validator

        result = flow.request_revision()

        assert result["status"] == "published"
        # Verify no research supplement injected
        topic_arg = mock_stage3_class.call_args[1]["topic"]
        assert "ADDITIONAL VERIFIED SOURCES" not in topic_arg

    def test_research_unsourced_claims_extracts_placeholders(
        self,
        flow: EconomistContentFlow,
    ) -> None:
        """_research_unsourced_claims extracts [NEEDS SOURCE] sentences."""
        flow.state["quality_result"] = {
            "article": (
                "Teams report 50% gains [NEEDS SOURCE]. "
                "This is well known. "
                "Market grew 40% [NEEDS SOURCE]."
            ),
        }

        with patch("crewai.Crew") as mock_crew_cls:
            mock_crew = Mock()
            mock_result = Mock()
            mock_result.raw = "Gartner 2025: 48% of teams improved."
            mock_crew.kickoff.return_value = mock_result
            mock_crew_cls.return_value = mock_crew

            result = flow._research_unsourced_claims("AI Testing", "placeholder issues")

        assert "Gartner 2025" in result
        mock_crew_cls.assert_called_once()


@pytest.mark.skip(
    reason=(
        "Obsolete after ADR-0006 Phase 2 (epic #308). These tests patch "
        "src.economist_agents.flow.Stage3Crew / Stage4Crew which no "
        "longer exist; flow.py now calls src.agent_sdk.pipeline."
        "run_pipeline directly. Filed #314 to add new flow tests."
    )
)
def test_flow_decorators_registered() -> None:
    """All Flow decorated methods are registered and callable."""
    flow = EconomistContentFlow()

    for method_name in [
        "discover_topics",
        "editorial_review",
        "generate_content",
        "quality_gate",
        "publish_article",
        "request_revision",
    ]:
        assert hasattr(flow, method_name)
        assert callable(getattr(flow, method_name))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
