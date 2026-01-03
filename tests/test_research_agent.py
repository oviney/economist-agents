#!/usr/bin/env python3
"""
Unit Tests for Research Agent

Tests the extracted Research Agent with mocked LLM responses.
"""

import json
from unittest.mock import Mock, patch

import pytest

from agents.research_agent import (
    RESEARCH_AGENT_PROMPT,
    ResearchAgent,
    run_research_agent,
)

# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_client():
    """Create a mock LLM client."""
    client = Mock()
    client.provider = "anthropic"  # Required by call_llm
    client.model = "claude-3-opus-20240229"

    # Mock the Anthropic response structure: response.content[0].text
    mock_text_obj = Mock()
    mock_text_obj.text = "test response"

    mock_response = Mock()
    mock_response.content = [mock_text_obj]  # Make it a list so [0] works

    # Mock the client.messages.create call
    client.client = Mock()
    client.client.messages = Mock()
    client.client.messages.create = Mock(return_value=mock_response)

    return client


@pytest.fixture
def mock_governance():
    """Create a mock governance tracker."""
    governance = Mock()
    governance.log_agent_output = Mock()
    return governance


@pytest.fixture
def sample_research_response():
    """Sample valid research response from LLM."""
    return json.dumps(
        {
            "headline_stat": {
                "value": "AI test generation adoption grew 300% in 2024",
                "source": "World Quality Report 2024",
                "year": "2024",
                "verified": True,
            },
            "data_points": [
                {
                    "stat": "45% of companies use AI for test generation",
                    "source": "Forrester Research",
                    "year": "2024",
                    "url": "https://example.com/report",
                    "verified": True,
                },
                {
                    "stat": "80% report reduced test maintenance costs",
                    "source": "Gartner Survey",
                    "year": "2024",
                    "verified": True,
                },
            ],
            "trend_narrative": "AI adoption in testing accelerated dramatically in 2024, driven by cost pressures and developer productivity initiatives.",
            "chart_data": {
                "title": "AI adoption in testing",
                "subtitle": "Percentage of companies using AI for test generation, 2020-2024",
                "type": "line",
                "x_label": "Year",
                "y_label": "Adoption rate, %",
                "data": [
                    {"label": "2020", "adoption": 12},
                    {"label": "2021", "adoption": 18},
                    {"label": "2022", "adoption": 28},
                    {"label": "2023", "adoption": 35},
                    {"label": "2024", "adoption": 45},
                ],
                "source_line": "Sources: Forrester Research; Gartner",
            },
            "contrarian_angle": "Despite high adoption, 60% of teams report AI tests require more human review than traditional tests",
            "unverified_claims": [],
        }
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEST RESEARCH AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class TestResearchAgent:
    """Test suite for ResearchAgent class."""

    def test_init(self, mock_client):
        """Test agent initialization."""
        agent = ResearchAgent(mock_client)
        assert agent.client == mock_client
        assert agent.governance is None

    def test_init_with_governance(self, mock_client, mock_governance):
        """Test agent initialization with governance."""
        agent = ResearchAgent(mock_client, mock_governance)
        assert agent.client == mock_client
        assert agent.governance == mock_governance

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_research_success(
        self, mock_review, mock_call_llm, mock_client, sample_research_response
    ):
        """Test successful research execution."""
        # Setup mocks
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (True, [])

        # Execute
        agent = ResearchAgent(mock_client)
        result = agent.research("AI Testing Trends", "adoption rates")

        # Verify call_llm was called with correct arguments
        mock_call_llm.assert_called_once()
        args = mock_call_llm.call_args
        assert args[0][0] == mock_client
        assert args[0][1] == RESEARCH_AGENT_PROMPT
        assert "AI Testing Trends" in args[0][2]
        assert "adoption rates" in args[0][2]
        assert args[1]["max_tokens"] == 2500

        # Verify result structure
        assert "headline_stat" in result
        assert "data_points" in result
        assert len(result["data_points"]) == 2
        assert result["data_points"][0]["verified"] is True

        # Verify self-validation was called
        mock_review.assert_called_once_with("research_agent", result)

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_research_with_governance_logging(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        mock_governance,
        sample_research_response,
    ):
        """Test that governance logging is called when enabled."""
        # Setup mocks
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (True, [])

        # Execute
        agent = ResearchAgent(mock_client, mock_governance)
        result = agent.research("AI Testing Trends")

        # Verify governance logging
        mock_governance.log_agent_output.assert_called_once()
        call_args = mock_governance.log_agent_output.call_args
        assert call_args[0][0] == "research_agent"
        assert call_args[0][1] == result
        assert "topic" in call_args[1]["metadata"]
        assert call_args[1]["metadata"]["topic"] == "AI Testing Trends"

    def test_research_invalid_topic_empty(self, mock_client):
        """Test that empty topic raises ValueError."""
        agent = ResearchAgent(mock_client)

        with pytest.raises(ValueError, match="Invalid topic"):
            agent.research("")

    def test_research_invalid_topic_none(self, mock_client):
        """Test that None topic raises ValueError."""
        agent = ResearchAgent(mock_client)

        with pytest.raises(ValueError, match="Invalid topic"):
            agent.research(None)

    def test_research_invalid_topic_too_short(self, mock_client):
        """Test that too-short topic raises ValueError."""
        agent = ResearchAgent(mock_client)

        with pytest.raises(ValueError, match="Topic too short"):
            agent.research("AI")

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_research_handles_malformed_json(
        self, mock_review, mock_call_llm, mock_client
    ):
        """Test that malformed JSON is handled gracefully."""
        # Setup mocks with invalid JSON
        mock_call_llm.return_value = "This is not JSON at all"
        mock_review.return_value = (False, ["Invalid JSON format"])

        # Execute
        agent = ResearchAgent(mock_client)
        result = agent.research("Testing Topic")

        # Verify fallback structure
        assert "raw_research" in result
        assert result["raw_research"] == "This is not JSON at all"
        assert result["chart_data"] is None

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_research_with_unverified_claims(
        self, mock_review, mock_call_llm, mock_client, capsys
    ):
        """Test that unverified claims are properly logged."""
        # Setup response with unverified claims
        response = json.dumps(
            {
                "headline_stat": {
                    "value": "Test stat",
                    "source": "Test",
                    "year": "2024",
                    "verified": True,
                },
                "data_points": [],
                "trend_narrative": "Test",
                "chart_data": None,
                "contrarian_angle": "Test",
                "unverified_claims": ["Claim 1", "Claim 2", "Claim 3"],
            }
        )
        mock_call_llm.return_value = response
        mock_review.return_value = (True, [])

        # Execute
        agent = ResearchAgent(mock_client)
        agent.research("Test Topic")

        # Verify console output mentions unverified claims
        captured = capsys.readouterr()
        assert "3 unverified claims flagged" in captured.out

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_research_validation_failure_logged(
        self, mock_review, mock_call_llm, mock_client, sample_research_response, capsys
    ):
        """Test that validation failures are properly logged."""
        # Setup mocks with validation failure
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (
            False,
            [
                "Issue 1: Missing source",
                "Issue 2: Unverified claim",
                "Issue 3: Format error",
            ],
        )

        # Execute
        agent = ResearchAgent(mock_client)
        agent.research("Test Topic")

        # Verify console output shows validation issues
        captured = capsys.readouterr()
        assert "3 quality issues" in captured.out
        assert "Issue 1: Missing source" in captured.out


# ═══════════════════════════════════════════════════════════════════════════
# TEST BACKWARD COMPATIBILITY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """Test backward compatibility with original function."""

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_run_research_agent_function(
        self, mock_review, mock_call_llm, mock_client, sample_research_response
    ):
        """Test that run_research_agent() function works identically."""
        # Setup mocks
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (True, [])

        # Execute
        result = run_research_agent(mock_client, "AI Testing")

        # Verify result structure (same as class-based approach)
        assert "headline_stat" in result
        assert "data_points" in result
        assert len(result["data_points"]) == 2

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_run_research_agent_with_all_params(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        mock_governance,
        sample_research_response,
    ):
        """Test run_research_agent() with all parameters."""
        # Setup mocks
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (True, [])

        # Execute with all parameters
        result = run_research_agent(
            mock_client, "AI Testing Trends", "adoption rates, ROI", mock_governance
        )

        # Verify governance was used
        mock_governance.log_agent_output.assert_called_once()

        # Verify result
        assert "headline_stat" in result


# ═══════════════════════════════════════════════════════════════════════════
# TEST HELPER METHODS
# ═══════════════════════════════════════════════════════════════════════════


class TestHelperMethods:
    """Test private helper methods."""

    def test_build_user_prompt(self, mock_client):
        """Test user prompt building."""
        agent = ResearchAgent(mock_client)
        prompt = agent._build_user_prompt("Test Topic", "focus1, focus2")

        assert "Test Topic" in prompt
        assert "focus1, focus2" in prompt
        assert "VERIFIABLE" in prompt

    def test_build_user_prompt_no_talking_points(self, mock_client):
        """Test user prompt building without talking points."""
        agent = ResearchAgent(mock_client)
        prompt = agent._build_user_prompt("Test Topic", "")

        assert "Test Topic" in prompt
        assert "General coverage" in prompt

    def test_parse_response_valid_json(self, mock_client, sample_research_response):
        """Test parsing valid JSON response."""
        agent = ResearchAgent(mock_client)
        result = agent._parse_response(sample_research_response)

        assert "headline_stat" in result
        assert "data_points" in result

    def test_parse_response_json_with_markdown(self, mock_client):
        """Test parsing JSON wrapped in markdown."""
        agent = ResearchAgent(mock_client)
        response = """Here's the research data:

```json
{"headline_stat": {"value": "Test", "source": "Test", "year": "2024", "verified": true}, "data_points": []}
```

Hope this helps!"""

        result = agent._parse_response(response)
        assert "headline_stat" in result

    def test_parse_response_invalid_json(self, mock_client):
        """Test parsing invalid JSON falls back gracefully."""
        agent = ResearchAgent(mock_client)
        result = agent._parse_response("Not JSON")

        assert "raw_research" in result
        assert result["raw_research"] == "Not JSON"
        assert result["chart_data"] is None


# ═══════════════════════════════════════════════════════════════════════════
# TEST INTEGRATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""

    @patch("scripts.llm_client.call_llm")
    @patch("agents.research_agent.review_agent_output")
    def test_full_research_pipeline(
        self, mock_review, mock_call_llm, mock_client, sample_research_response, capsys
    ):
        """Test complete research pipeline from input to output."""
        # Setup
        mock_call_llm.return_value = sample_research_response
        mock_review.return_value = (True, [])

        # Execute
        agent = ResearchAgent(mock_client)
        result = agent.research(
            "AI Testing Trends", "adoption rates, maintenance costs"
        )

        # Verify complete flow
        captured = capsys.readouterr()
        assert "📊 Research Agent" in captured.out
        assert "✓ Found 2 data points" in captured.out
        assert "✅ Research passed self-validation" in captured.out

        # Verify result quality
        assert result["headline_stat"]["verified"] is True
        assert len(result["data_points"]) == 2
        assert all(dp["verified"] for dp in result["data_points"])
        assert result["chart_data"] is not None
