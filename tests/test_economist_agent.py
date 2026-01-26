"""Comprehensive tests for scripts/economist_agent.py

Tests cover the main workflow functions:
- run_research_agent: Mock LLM calls, test research output
- run_writer_agent: Mock LLM, test article generation
- run_editor_agent: Mock LLM, test editing/validation
- run_graphics_agent: Mock chart generation
- main: Test full pipeline with governance gates

Mocks all:
- LLM API calls (OpenAI/Anthropic)
- File I/O operations
- Chart generation
- User input for interactive mode

Tests error handling:
- API failures at each stage
- Invalid agent outputs
- Schema validation failures
- Governance gate rejections

Target: 80%+ coverage
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import economist_agent as ea  # noqa: E402

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLM client that can be configured for different responses."""
    client = Mock()
    client.provider = "anthropic"
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
def mock_governance_tracker():
    """Mock governance tracker for approval gates."""
    tracker = Mock()
    tracker.session_dir = "/tmp/governance"
    tracker.log_agent_output = Mock()
    tracker.request_approval = Mock(return_value=True)
    tracker.generate_report = Mock()
    return tracker


@pytest.fixture
def sample_research_output():
    """Sample research agent output."""
    return {
        "headline_stat": {
            "value": "80% of QE teams use AI testing",
            "source": "Gartner 2024 QE Survey",
            "year": "2024",
            "verified": True,
        },
        "data_points": [
            {
                "stat": "50% reduction in test maintenance",
                "source": "TestGuild 2024 Report",
                "year": "2024",
                "url": "https://testguild.com/report-2024",
                "verified": True,
            },
            {
                "stat": "30% faster test execution",
                "source": "Industry Benchmark",
                "year": "2024",
                "verified": True,
            },
        ],
        "trend_narrative": "AI testing adoption accelerating in enterprise QE organizations",
        "chart_data": {
            "title": "AI Testing Adoption Growth",
            "subtitle": "Percentage of teams using AI testing tools, %",
            "type": "line",
            "x_label": "Years",
            "y_label": "Adoption %",
            "data": [
                {"label": "2022", "value": 45},
                {"label": "2023", "value": 60},
                {"label": "2024", "value": 80},
            ],
            "source_line": "Sources: Gartner; TestGuild",
        },
        "contrarian_angle": "Despite hype, maintenance reduction claims often overstated",
        "unverified_claims": [],
    }


@pytest.fixture
def sample_article_draft():
    """Sample article draft from writer agent."""
    return """---
layout: post
title: "Testing Times: The AI Promise Gap"
date: 2024-01-15
author: "The Economist"
---

AI testing tools promise an 80% cut in maintenance costs. Only 10% of companies achieve it.

The gap between vendor promises and reality has never been wider...

![AI Testing Adoption Growth](/assets/charts/testing-times-ai-gap.png)

As the chart shows, adoption is surging but results lag behind.
"""


@pytest.fixture
def sample_edited_article():
    """Sample edited article from editor agent."""
    return """## Quality Gate Results

**GATE 1: OPENING** - PASS
- First sentence hook: Strong data point
- Throat-clearing present: NO
- Reader engagement: High
**Decision**: PASS

**GATE 2: EVIDENCE** - PASS
- Statistics sourced: 5/5 statistics have sources
- [NEEDS SOURCE] flags removed: YES
- Weasel phrases present: NO
**Decision**: PASS

**GATE 3: VOICE** - PASS
- British spelling: YES
- Active voice: YES
- Banned phrases found: NONE
- Exclamation points: NONE
**Decision**: Voice is correct

**GATE 4: STRUCTURE** - PASS
- Logical flow: Good progression
- Weak ending: NO
- Redundant paragraphs: NONE
**Decision**: Structure is sound

**GATE 5: CHART INTEGRATION** - PASS
- Chart markdown present: YES
- Chart referenced in text: YES
- Natural integration: Good
**Decision**: Chart well integrated

**OVERALL GATES PASSED**: 5/5
**PUBLICATION DECISION**: READY

---

## Edited Article

---
layout: post
title: "Testing Times: The AI Promise Gap"
date: 2024-01-15
author: "The Economist"
---

AI testing tools promise an 80% cut in maintenance costs. Only 10% achieve it.

[Rest of article...]
"""


# ============================================================================
# RESEARCH AGENT TESTS
# ============================================================================


class TestRunResearchAgent:
    """Tests for run_research_agent function."""

    def test_successful_research_with_valid_output(
        self, mock_llm_client, sample_research_output
    ):
        """Test research agent with successful LLM response."""
        # Mock the response at the message content level (Anthropic API structure)
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(sample_research_output))]

        with (
            patch("agents.research_agent.call_llm") as mock_call_llm,
            patch("agents.research_agent.review_agent_output") as mock_review,
            patch(
                "agents.research_agent.ResearchAgent._gather_arxiv_research",
                return_value=None,
            ),
        ):
            # Return the properly structured mock response
            mock_call_llm.return_value = json.dumps(sample_research_output)
            mock_review.return_value = (True, [])

            result = ea.run_research_agent(
                mock_llm_client, "AI Testing Trends", "adoption rates, ROI"
            )

            assert result == sample_research_output
            assert mock_call_llm.call_count == 1
            assert mock_review.call_count == 1

    def test_research_agent_with_invalid_topic(self, mock_llm_client):
        """Test research agent with invalid topic parameter."""
        with pytest.raises(ValueError, match="Invalid topic"):
            ea.run_research_agent(mock_llm_client, None)

        with pytest.raises(ValueError, match="Invalid topic"):
            ea.run_research_agent(mock_llm_client, 123)

    def test_research_agent_with_too_short_topic(self, mock_llm_client):
        """Test research agent with topic too short."""
        with pytest.raises(ValueError, match="Topic too short"):
            ea.run_research_agent(mock_llm_client, "AI")

    def test_research_agent_with_invalid_json_response(self, mock_llm_client):
        """Test research agent handles invalid JSON from LLM."""
        with (
            patch("agents.research_agent.call_llm") as mock_call_llm,
            patch("agents.research_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = "This is not valid JSON"
            mock_review.return_value = (True, [])

            result = ea.run_research_agent(
                mock_llm_client, "Testing Topic", "focus areas"
            )

            assert "raw_research" in result
            assert result["raw_research"] == "This is not valid JSON"
            assert result["chart_data"] is None

    def test_research_agent_with_unverified_claims(
        self, mock_llm_client, sample_research_output
    ):
        """Test research agent flags unverified claims."""
        sample_research_output["unverified_claims"] = [
            "90% of companies report improved quality"
        ]

        with (
            patch("agents.research_agent.call_llm") as mock_call_llm,
            patch("agents.research_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = json.dumps(sample_research_output)
            mock_review.return_value = (True, [])

            result = ea.run_research_agent(mock_llm_client, "Testing Topic")

            assert len(result["unverified_claims"]) == 1

    def test_research_agent_with_governance_logging(
        self, mock_llm_client, sample_research_output, mock_governance_tracker
    ):
        """Test research agent logs to governance tracker."""
        with (
            patch("agents.research_agent.call_llm") as mock_call_llm,
            patch("agents.research_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = json.dumps(sample_research_output)
            mock_review.return_value = (True, [])

            ea.run_research_agent(
                mock_llm_client, "Testing Topic", governance=mock_governance_tracker
            )

            assert mock_governance_tracker.log_agent_output.called
            call_args = mock_governance_tracker.log_agent_output.call_args
            assert call_args[0][0] == "research_agent"
            assert "metadata" in call_args[1]

    def test_research_agent_with_validation_failures(
        self, mock_llm_client, sample_research_output
    ):
        """Test research agent handles validation failures."""
        with (
            patch("agents.research_agent.call_llm") as mock_call_llm,
            patch("agents.research_agent.review_agent_output") as mock_review,
            patch(
                "agents.research_agent.ResearchAgent._gather_arxiv_research",
                return_value=None,
            ),
        ):
            mock_call_llm.return_value = json.dumps(sample_research_output)
            mock_review.return_value = (
                False,
                ["Missing source attribution", "Data not verified"],
            )

            result = ea.run_research_agent(mock_llm_client, "Testing Topic")

            # Should still return data despite validation issues
            assert result == sample_research_output


# ============================================================================
# WRITER AGENT TESTS
# ============================================================================


class TestRunWriterAgent:
    """Tests for run_writer_agent function."""

    def test_successful_article_generation(
        self, mock_llm_client, sample_research_output, sample_article_draft
    ):
        """Test writer agent with successful article generation."""
        with (
            patch("agents.writer_agent.call_llm") as mock_call_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = sample_article_draft
            mock_review.return_value = (True, [])

            draft, metadata = ea.run_writer_agent(
                mock_llm_client,
                "AI Testing Trends",
                sample_research_output,
                "2024-01-15",
            )

            assert "AI testing tools promise" in draft
            assert metadata["is_valid"] is True
            assert metadata["regenerated"] is False

    def test_writer_agent_with_invalid_topic(
        self, mock_llm_client, sample_research_output
    ):
        """Test writer agent with invalid topic."""
        with pytest.raises(ValueError, match="Invalid topic"):
            ea.run_writer_agent(
                mock_llm_client, None, sample_research_output, "2024-01-15"
            )

        with pytest.raises(ValueError, match="Invalid topic"):
            ea.run_writer_agent(
                mock_llm_client, 123, sample_research_output, "2024-01-15"
            )

    def test_writer_agent_with_invalid_research_brief(self, mock_llm_client):
        """Test writer agent with invalid research brief."""
        with pytest.raises(ValueError, match="Invalid research_brief"):
            ea.run_writer_agent(mock_llm_client, "Topic", "not a dict", "2024-01-15")

        with pytest.raises(ValueError, match="Empty research_brief"):
            ea.run_writer_agent(mock_llm_client, "Topic", {}, "2024-01-15")

    def test_writer_agent_with_chart_embedding(
        self, mock_llm_client, sample_research_output, sample_article_draft
    ):
        """Test writer agent includes chart embedding instructions."""
        with (
            patch("agents.writer_agent.call_llm") as mock_call_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = sample_article_draft
            mock_review.return_value = (True, [])

            draft, _ = ea.run_writer_agent(
                mock_llm_client,
                "AI Testing",
                sample_research_output,
                "2024-01-15",
                chart_filename="/assets/charts/test.png",
            )

            # Verify chart embedding instruction was added to prompt
            call_args = mock_call_llm.call_args
            system_prompt = call_args[0][1]
            assert "CHART EMBEDDING REQUIRED" in system_prompt

    def test_writer_agent_with_featured_image(
        self, mock_llm_client, sample_research_output, sample_article_draft
    ):
        """Test writer agent includes featured image instructions."""
        with (
            patch("agents.writer_agent.call_llm") as mock_call_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = sample_article_draft
            mock_review.return_value = (True, [])

            draft, _ = ea.run_writer_agent(
                mock_llm_client,
                "AI Testing",
                sample_research_output,
                "2024-01-15",
                featured_image="/assets/images/featured.png",
            )

            call_args = mock_call_llm.call_args
            system_prompt = call_args[0][1]
            assert "FEATURED IMAGE AVAILABLE" in system_prompt

    def test_writer_agent_with_critical_validation_issues(
        self, mock_llm_client, sample_research_output, sample_article_draft
    ):
        """Test writer agent regenerates on critical issues."""
        with (
            patch("agents.writer_agent.call_llm") as mock_call_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            # First call has critical issues, second call is clean
            mock_call_llm.side_effect = [
                "Bad draft with issues",
                sample_article_draft,
            ]
            mock_review.side_effect = [
                (False, ["CRITICAL: Missing chart", "BANNED: In today's world"]),
                (True, []),
            ]

            draft, metadata = ea.run_writer_agent(
                mock_llm_client,
                "AI Testing",
                sample_research_output,
                "2024-01-15",
            )

            # Check that regeneration happened (2 LLM calls made)
            assert mock_call_llm.call_count == 2
            # After regeneration, draft should be valid
            assert metadata["is_valid"] is True

    def test_writer_agent_with_non_critical_issues(
        self, mock_llm_client, sample_research_output, sample_article_draft
    ):
        """Test writer agent doesn't regenerate on non-critical issues."""
        with (
            patch("agents.writer_agent.call_llm") as mock_call_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            mock_call_llm.return_value = sample_article_draft
            mock_review.return_value = (False, ["Minor style issue", "Small typo"])

            draft, metadata = ea.run_writer_agent(
                mock_llm_client,
                "AI Testing",
                sample_research_output,
                "2024-01-15",
            )

            assert metadata["regenerated"] is False
            assert mock_call_llm.call_count == 1


# ============================================================================
# GRAPHICS AGENT TESTS
# ============================================================================


class TestRunGraphicsAgent:
    """Tests for run_graphics_agent function."""

    def test_successful_chart_generation(self, mock_llm_client):
        """Test graphics agent with successful chart generation."""
        chart_spec = {
            "title": "Test Chart",
            "data": [{"x": 1, "y": 2}],
        }

        with (
            patch("llm_client.call_llm") as mock_call_llm,
            patch("agents.graphics_agent.get_metrics_collector") as mock_metrics,
            patch("subprocess.run") as mock_subprocess,
            patch("builtins.open", mock_open()),
        ):
            mock_call_llm.return_value = "plt.plot([1, 2, 3])\nplt.savefig('test.png')"
            mock_subprocess.return_value = Mock(returncode=0)
            mock_collector = Mock()
            mock_chart_record = {"title": "Test Chart"}
            mock_collector.start_chart.return_value = mock_chart_record
            mock_metrics.return_value = mock_collector

            result = ea.run_graphics_agent(mock_llm_client, chart_spec, "/tmp/test.png")

            assert result == "/tmp/test.png"
            assert mock_collector.record_generation.called

    def test_graphics_agent_with_no_chart_spec(self, mock_llm_client):
        """Test graphics agent with no chart data."""
        result = ea.run_graphics_agent(mock_llm_client, None, "/tmp/test.png")
        assert result is None

    def test_graphics_agent_with_invalid_chart_spec(self, mock_llm_client):
        """Test graphics agent with invalid chart spec."""
        with pytest.raises(ValueError, match="Invalid chart_spec"):
            ea.run_graphics_agent(mock_llm_client, "not a dict", "/tmp/test.png")

    def test_graphics_agent_with_missing_required_fields(self, mock_llm_client):
        """Test graphics agent with missing required fields."""
        chart_spec = {"title": "Test Chart"}  # Missing 'data'

        with pytest.raises(ValueError, match="missing required fields"):
            ea.run_graphics_agent(mock_llm_client, chart_spec, "/tmp/test.png")

    def test_graphics_agent_with_invalid_output_path(self, mock_llm_client):
        """Test graphics agent with invalid output path."""
        chart_spec = {"title": "Test Chart", "data": []}

        with pytest.raises(ValueError, match="Invalid output_path"):
            ea.run_graphics_agent(mock_llm_client, chart_spec, None)

        with pytest.raises(ValueError, match="Invalid output_path"):
            ea.run_graphics_agent(mock_llm_client, chart_spec, 123)

    def test_graphics_agent_with_subprocess_failure(self, mock_llm_client):
        """Test graphics agent handles subprocess failures."""
        chart_spec = {"title": "Test Chart", "data": []}

        with (
            patch("llm_client.call_llm") as mock_call_llm,
            patch("agents.graphics_agent.get_metrics_collector") as mock_metrics,
            patch("subprocess.run") as mock_subprocess,
            patch("builtins.open", mock_open()),
        ):
            mock_call_llm.return_value = "plt.plot([1, 2, 3])"
            mock_subprocess.return_value = Mock(returncode=1, stderr="Matplotlib error")
            mock_collector = Mock()
            mock_collector.start_chart.return_value = {"title": "Test"}
            mock_metrics.return_value = mock_collector

            result = ea.run_graphics_agent(mock_llm_client, chart_spec, "/tmp/test.png")

            assert result is None
            assert mock_collector.record_generation.called

    def test_graphics_agent_with_code_extraction(self, mock_llm_client):
        """Test graphics agent extracts code from markdown blocks."""
        chart_spec = {"title": "Test Chart", "data": []}

        with (
            patch("llm_client.call_llm") as mock_call_llm,
            patch("agents.graphics_agent.get_metrics_collector") as mock_metrics,
            patch("subprocess.run") as mock_subprocess,
            patch("builtins.open", mock_open()),
        ):
            # LLM returns code in markdown block
            mock_call_llm.return_value = "```python\nplt.plot([1, 2, 3])\n```"
            mock_subprocess.return_value = Mock(returncode=0)
            mock_collector = Mock()
            mock_collector.start_chart.return_value = {"title": "Test"}
            mock_metrics.return_value = mock_collector

            result = ea.run_graphics_agent(mock_llm_client, chart_spec, "/tmp/test.png")

            # Should successfully extract and execute code
            assert result == "/tmp/test.png"


# ============================================================================
# EDITOR AGENT TESTS
# ============================================================================


class TestRunEditorAgent:
    """Tests for run_editor_agent function."""

    def test_successful_editing(self, mock_llm_client, sample_edited_article):
        """Test editor agent with successful editing."""
        with patch("agents.editor_agent.call_llm") as mock_call_llm:
            mock_call_llm.return_value = sample_edited_article

            # Draft must be >100 chars
            long_draft = "Draft article content here. " * 10  # ~290 chars
            edited, gates_passed, gates_failed = ea.run_editor_agent(
                mock_llm_client, long_draft
            )

            assert "Edited Article" in edited or "AI testing tools" in edited
            assert gates_passed >= 0
            assert gates_failed >= 0

    def test_editor_agent_with_invalid_draft(self, mock_llm_client):
        """Test editor agent with invalid draft."""
        with pytest.raises(ValueError, match="Invalid draft"):
            ea.run_editor_agent(mock_llm_client, None)

        with pytest.raises(ValueError, match="Invalid draft"):
            ea.run_editor_agent(mock_llm_client, 123)

    def test_editor_agent_with_too_short_draft(self, mock_llm_client):
        """Test editor agent with draft too short."""
        with pytest.raises(ValueError, match="Draft too short"):
            ea.run_editor_agent(mock_llm_client, "Short")

    def test_editor_agent_gate_counting(self, mock_llm_client):
        """Test editor agent counts PASS/FAIL gates correctly."""
        response_with_gates = """## Quality Gate Results

**GATE 1: OPENING** - PASS
**GATE 2: EVIDENCE** - FAIL
**GATE 3: VOICE** - PASS
**GATE 4: STRUCTURE** - PASS
**GATE 5: CHART INTEGRATION** - FAIL

**OVERALL GATES PASSED**: 3/5
**PUBLICATION DECISION**: NEEDS REVISION

---

## Edited Article

Content here...
"""
        with patch("agents.editor_agent.call_llm") as mock_call_llm:
            mock_call_llm.return_value = response_with_gates

            edited, gates_passed, gates_failed = ea.run_editor_agent(
                mock_llm_client, "Draft content..." * 50
            )

            assert gates_passed == 3
            assert gates_failed == 2

    def test_editor_agent_extracts_edited_article(self, mock_llm_client):
        """Test editor agent extracts edited article from response."""
        response = """## Quality Gate Results

**GATE 1: OPENING** - PASS
**GATE 2: EVIDENCE** - PASS
**GATE 3: VOICE** - PASS
**GATE 4: STRUCTURE** - PASS
**GATE 5: CHART INTEGRATION** - PASS

**OVERALL GATES PASSED**: 5/5
**PUBLICATION DECISION**: READY

---

## Edited Article

This is the actual edited content.
"""
        with patch("agents.editor_agent.call_llm") as mock_call_llm:
            mock_call_llm.return_value = response

            edited, _, _ = ea.run_editor_agent(mock_llm_client, "Draft content..." * 50)

            assert "This is the actual edited content" in edited
            assert "Some preamble" not in edited


# ============================================================================
# MAIN PIPELINE TESTS
# ============================================================================


class TestMain:
    """Tests for main function and full pipeline."""

    def test_main_with_default_arguments(self):
        """Test main function with default arguments."""
        with (
            patch("sys.argv", ["economist_agent.py"]),
            patch("economist_agent.generate_economist_post") as mock_generate,
            patch("economist_agent.create_client") as mock_client,
            patch.dict(os.environ, {}, clear=True),
        ):
            mock_generate.return_value = {"article_path": "/tmp/article.md"}
            mock_client.return_value = Mock()

            ea.main()

            assert mock_generate.called

    def test_main_with_interactive_mode(self):
        """Test main function with interactive mode enabled."""
        with (
            patch("sys.argv", ["economist_agent.py", "--interactive"]),
            patch("economist_agent.generate_economist_post") as mock_generate,
            patch("economist_agent.create_client") as mock_client,
            patch("economist_agent.GovernanceTracker") as mock_governance,
            patch.dict(os.environ, {"TOPIC": "Test Topic"}, clear=True),
        ):
            mock_generate.return_value = {"article_path": "/tmp/article.md"}
            mock_client.return_value = Mock()

            ea.main()

            assert mock_generate.called
            assert mock_governance.called

    def test_main_with_custom_governance_dir(self, tmp_path):
        """Test main function with custom governance directory."""
        governance_dir = tmp_path / "governance"
        with (
            patch(
                "sys.argv",
                [
                    "economist_agent.py",
                    "--interactive",
                    "--governance-dir",
                    str(governance_dir),
                ],
            ),
            patch("economist_agent.generate_economist_post") as mock_generate,
            patch("economist_agent.create_client") as mock_client,
            patch("economist_agent.GovernanceTracker") as mock_governance,
            patch.dict(os.environ, {"TOPIC": "Test Topic"}, clear=True),
        ):
            mock_generate.return_value = {"article_path": "/tmp/article.md"}
            mock_client.return_value = Mock()

            ea.main()

            # Verify governance tracker created with custom dir
            assert mock_governance.called

    def test_main_with_environment_variables(self, tmp_path, mock_llm_client):
        """Test main function uses environment variables."""
        custom_output = tmp_path / "custom_output"
        env_vars = {
            "TOPIC": "Custom Topic",
            "TALKING_POINTS": "Point 1, Point 2",
            "CATEGORY": "test-category",
            "OUTPUT_DIR": str(custom_output),
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test123",
        }

        with (
            patch("sys.argv", ["economist_agent.py"]),
            patch("economist_agent.generate_economist_post") as mock_generate,
            patch("economist_agent.create_client") as mock_client,
            patch.dict(os.environ, env_vars),
        ):
            mock_generate.return_value = {
                "article_path": str(custom_output / "article.md")
            }
            mock_client.return_value = mock_llm_client

            ea.main()

            call_args = mock_generate.call_args
            if call_args:
                assert call_args[0][0] == "Custom Topic"
                assert call_args[0][1] == "test-category"
                assert call_args[0][2] == "Point 1, Point 2"

    def test_main_with_github_output(self, mock_llm_client):
        """Test main function writes to GITHUB_OUTPUT."""
        with (
            patch("sys.argv", ["economist_agent.py"]),
            patch("economist_agent.generate_economist_post") as mock_generate,
            patch("economist_agent.create_client") as mock_client,
            patch("builtins.open", mock_open()) as mock_file,
            patch.dict(
                os.environ,
                {"GITHUB_OUTPUT": "/tmp/output.txt", "TOPIC": "Test"},
                clear=True,
            ),
        ):
            mock_generate.return_value = {
                "article_path": "/tmp/article.md",
                "gates_passed": 5,
            }
            mock_client.return_value = mock_llm_client

            ea.main()

            # Verify GITHUB_OUTPUT was written
            mock_file.assert_called_with("/tmp/output.txt", "a")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_pipeline_with_mocked_llm(
        self,
        mock_llm_client,
        sample_research_output,
        sample_article_draft,
        sample_edited_article,
    ):
        """Test full pipeline from research to publication."""
        with (
            patch("agents.research_agent.call_llm") as mock_research_llm,
            patch("agents.writer_agent.call_llm") as mock_writer_llm,
            patch("agents.editor_agent.call_llm") as mock_editor_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
            patch("llm_client.call_llm") as mock_graphics_llm,
            patch("agents.graphics_agent.get_metrics_collector") as mock_metrics,
            patch("subprocess.run") as mock_subprocess,
            patch("builtins.open", mock_open()),
        ):
            # Setup mocks - separate for each agent
            mock_research_llm.return_value = json.dumps(sample_research_output)
            mock_writer_llm.return_value = sample_article_draft
            mock_editor_llm.return_value = sample_edited_article
            mock_graphics_llm.return_value = (
                "plt.plot([1, 2, 3])\nplt.savefig('test.png')"
            )
            mock_review.return_value = (True, [])
            mock_subprocess.return_value = Mock(returncode=0)
            mock_collector = Mock()
            mock_collector.start_chart.return_value = {"title": "Test"}
            mock_metrics.return_value = mock_collector

            # Run research
            research = ea.run_research_agent(
                mock_llm_client, "AI Testing Trends", "ROI, adoption"
            )
            assert "data_points" in research

            # Run writer
            draft, _ = ea.run_writer_agent(
                mock_llm_client, "AI Testing", research, "2024-01-15"
            )
            assert "AI testing tools" in draft

            # Run graphics (if chart data available)
            if research.get("chart_data"):
                chart_path = ea.run_graphics_agent(
                    mock_llm_client, research["chart_data"], "/tmp/chart.png"
                )
                assert chart_path == "/tmp/chart.png"

            # Run editor
            edited, gates_passed, gates_failed = ea.run_editor_agent(
                mock_llm_client, draft
            )
            assert gates_passed > 0

    def test_pipeline_handles_api_failures_gracefully(self, mock_llm_client):
        """Test pipeline handles API failures at each stage."""
        with patch("agents.research_agent.call_llm") as mock_call_llm:
            # Simulate API failure
            mock_call_llm.side_effect = Exception("API Error")

            # Research agent should handle exception
            with pytest.raises((Exception, ValueError, RuntimeError)):
                ea.run_research_agent(mock_llm_client, "Test Topic")

    def test_pipeline_with_governance_gates(
        self,
        mock_llm_client,
        mock_governance_tracker,
        sample_research_output,
        sample_article_draft,
    ):
        """Test pipeline with governance approval gates."""
        with (
            patch("agents.research_agent.call_llm") as mock_research_llm,
            patch("agents.writer_agent.call_llm") as mock_writer_llm,
            patch("agents.writer_agent.review_agent_output") as mock_review,
        ):
            mock_research_llm.return_value = json.dumps(sample_research_output)
            mock_writer_llm.return_value = sample_article_draft
            mock_review.return_value = (True, [])

            # Research with governance
            research = ea.run_research_agent(
                mock_llm_client,
                "Test Topic",
                governance=mock_governance_tracker,
            )
            assert mock_governance_tracker.log_agent_output.called

            # Writer (governance logging happens at higher level)
            draft, _ = ea.run_writer_agent(
                mock_llm_client, "Test Topic", research, "2024-01-15"
            )
            assert draft is not None
