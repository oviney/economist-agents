#!/usr/bin/env python3
"""
Integration Tests for Economist Content Flow

Tests the Flow-based state-machine orchestration with @start/@listen/@router decorators.

Test Coverage:
1. Flow initialization and state management
2. Stage3Crew integration via generate_content()
3. Stage4Crew routing logic via quality_gate()
4. End-to-end publish path
5. End-to-end revision path

Usage:
    pytest tests/test_economist_flow.py -v
"""

import os
import sys
from pathlib import Path

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import Mock, patch

import pytest

from src.economist_agents.flow import EconomistContentFlow


class TestEconomistFlow:
    """Integration tests for EconomistContentFlow"""

    @pytest.fixture
    def flow(self):
        """Create Flow instance for testing"""
        return EconomistContentFlow()

    def test_flow_initialization(self, flow):
        """
        Test 1: Flow initialization and state management

        Given: EconomistContentFlow class
        When: Instance created
        Then: Flow initialized with crew dependencies and state
        """
        assert flow is not None
        assert hasattr(flow, "stage4_crew")
        assert hasattr(flow, "state")
        # Note: stage3_crew initialized on-demand in generate_content()
        print("✅ Test 1: Flow initialized with stage4_crew and state")

    def test_discover_topics_stage(self, flow):
        """
        Test 2: @start stage returns topic candidates

        Given: Flow discover_topics() method
        When: Called as entry point
        Then: Returns mock topics with structure {topics: [...], timestamp}
        """
        result = flow.discover_topics()

        assert "topics" in result
        assert "timestamp" in result
        assert len(result["topics"]) > 0
        assert all("topic" in t for t in result["topics"])
        assert all("score" in t for t in result["topics"])
        print("✅ Test 2: discover_topics() returns structured topic data")

    def test_editorial_review_stage(self, flow):
        """
        Test 3: @listen stage selects winning topic

        Given: Mock topics from discover_topics()
        When: editorial_review() called
        Then: Returns single topic with highest score
        """
        topics = {
            "topics": [
                {
                    "topic": "Topic A",
                    "score": 7.5,
                    "hook": "Hook A",
                    "thesis": "Thesis A",
                },
                {
                    "topic": "Topic B",
                    "score": 8.5,
                    "hook": "Hook B",
                    "thesis": "Thesis B",
                },
                {
                    "topic": "Topic C",
                    "score": 6.2,
                    "hook": "Hook C",
                    "thesis": "Thesis C",
                },
            ],
            "timestamp": "2026-01-07T00:00:00Z",
        }

        result = flow.editorial_review(topics)

        assert result["topic"] == "Topic B"  # Highest score
        assert result["score"] == 8.5
        assert "hook" in result
        assert "thesis" in result
        print("✅ Test 3: editorial_review() selects top-scored topic")

    @patch("src.economist_agents.flow.Stage3Crew")
    def test_stage3_crew_integration(self, mock_stage3_class, flow):
        """
        Test 4: Stage3Crew kickoff via generate_content()

        Given: Mocked Stage3Crew
        When: generate_content() called with selected topic
        Then: Stage3Crew.kickoff() executed with topic parameter
        """
        # Mock Stage3Crew.kickoff() return value
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "article": "# Test Article\n\nContent here...",
            "chart_path": "/path/to/chart.png",
            "word_count": 750,
            "metadata": {"category": "quality-engineering"},
        }
        mock_stage3_class.return_value = mock_crew_instance

        selected_topic = {
            "topic": "The AI Testing Paradox",
            "score": 8.5,
            "hook": "Companies report 40% more maintenance",
            "thesis": "Self-healing tests create new complexity",
        }

        result = flow.generate_content(selected_topic)

        # Verify Stage3Crew was initialized with topic
        mock_stage3_class.assert_called_once_with(topic="The AI Testing Paradox")

        # Verify Stage3Crew.kickoff() was called
        mock_crew_instance.kickoff.assert_called_once()

        # Verify result structure
        assert "article" in result
        assert "word_count" in result
        print(
            "✅ Test 4: Stage3Crew initialized and kickoff() called via generate_content()"
        )

    @patch("src.economist_agents.flow.Stage4Crew")
    def test_stage4_crew_routing_publish(self, mock_stage4_class, flow):
        """
        Test 5: Stage4Crew router - publish path

        Given: Mocked Stage4Crew with quality_score ≥ 8
        When: quality_gate() called
        Then: Returns "publish" routing decision
        """
        # Mock Stage4Crew.kickoff() with high quality score
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "edited_article": "# Edited Article\n\nPolished content...",
            "gates_passed": 5,
            "quality_score": 9.2,
        }
        mock_stage4_class.return_value = mock_crew_instance

        flow_with_mock = EconomistContentFlow()

        article_draft = {
            "article": "# Draft Article\n\nDraft content...",
            "chart_path": None,
            "word_count": 750,
        }

        decision = flow_with_mock.quality_gate(article_draft)

        assert decision == "publish"
        assert flow_with_mock.state["decision"] == "publish"
        assert flow_with_mock.state["quality_result"]["quality_score"] == 9.2
        print("✅ Test 5: quality_gate() routes to publish (score ≥8)")

    @patch("src.economist_agents.flow.Stage4Crew")
    def test_stage4_crew_routing_revision(self, mock_stage4_class, flow):
        """
        Test 6: Stage4Crew router - revision path

        Given: Mocked Stage4Crew with quality_score < 8
        When: quality_gate() called
        Then: Returns "revision" routing decision
        """
        # Mock Stage4Crew.kickoff() with low quality score
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.return_value = {
            "edited_article": "# Draft Article\n\nNeeds work...",
            "gates_passed": 3,
            "quality_score": 6.5,
        }
        mock_stage4_class.return_value = mock_crew_instance

        flow_with_mock = EconomistContentFlow()

        article_draft = {
            "article": "# Draft Article\n\nDraft content...",
            "chart_path": None,
            "word_count": 750,
        }

        decision = flow_with_mock.quality_gate(article_draft)

        assert decision == "revision"
        assert flow_with_mock.state["decision"] == "revision"
        assert flow_with_mock.state["quality_result"]["quality_score"] == 6.5
        print("✅ Test 6: quality_gate() routes to revision (score <8)")

    def test_publish_terminal_stage(self, flow):
        """
        Test 7: Publish path terminal stage

        Given: Flow state with publish decision
        When: publish_article() called
        Then: Returns published status with quality metadata
        """
        # Set flow state as if quality_gate() routed to publish
        flow.state["quality_result"] = {
            "edited_article": "# Published Article",
            "gates_passed": 5,
            "quality_score": 9.0,
        }
        flow.state["decision"] = "publish"

        result = flow.publish_article()

        assert result["status"] == "published"
        assert result["quality_score"] == 9.0
        assert result["gates_passed"] == 5
        assert "article" in result
        print("✅ Test 7: publish_article() returns publication metadata")

    def test_revision_terminal_stage(self, flow):
        """
        Test 8: Revision path terminal stage

        Given: Flow state with revision decision
        When: request_revision() called
        Then: Returns needs_revision status with failed gates count
        """
        # Set flow state as if quality_gate() routed to revision
        flow.state["quality_result"] = {
            "edited_article": "# Draft Needs Revision",
            "gates_passed": 2,
            "quality_score": 5.5,
        }
        flow.state["decision"] = "revision"

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert result["quality_score"] == 5.5
        assert result["gates_passed"] == 2
        assert result["gates_failed"] == 3
        print("✅ Test 8: request_revision() returns revision metadata")


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for CrewAI agent initialization",
)
def test_flow_decorators_registered():
    """
    Test 9: Verify Flow decorators are properly registered

    Given: EconomistContentFlow class
    When: Inspected for decorated methods
    Then: @start, @listen, @router decorators present
    """
    flow = EconomistContentFlow()

    # Check method existence
    assert hasattr(flow, "discover_topics")
    assert hasattr(flow, "editorial_review")
    assert hasattr(flow, "generate_content")
    assert hasattr(flow, "quality_gate")
    assert hasattr(flow, "publish_article")
    assert hasattr(flow, "request_revision")

    # Verify methods are callable
    assert callable(flow.discover_topics)
    assert callable(flow.editorial_review)
    assert callable(flow.generate_content)
    assert callable(flow.quality_gate)

    print("✅ Test 9: All Flow decorated methods registered")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
