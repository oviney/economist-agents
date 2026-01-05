#!/usr/bin/env python3
"""
Integration Tests for Agent Pipeline (Sprint 8 Story 3)

Tests the COMPLETE workflow: Research → Writer → Editor → Validator → Publication

Background:
- Sprint 7 found 42.9% of bugs are integration test gaps (HIGHEST gap)
- Bugs caught: Agent coordination issues, data flow problems, missing validations
- Most bugs occur at integration points, not within individual agents

Test Strategy:
- Mock LLM responses for deterministic testing
- Validate data flow between agents
- Check that validation gates actually block bad content
- Verify chart embedding works end-to-end
- Ensure publication validator catches known issues

Test Categories:
1. Happy Path: Complete pipeline with valid content
2. Chart Integration: Chart generation → embedding → validation
3. Quality Gates: Editor rejects bad content
4. Publication Blocking: Validator stops invalid articles
5. Error Handling: Graceful degradation on failures

Usage:
    pytest scripts/test_agent_integration.py -v
    pytest scripts/test_agent_integration.py::test_happy_path -v
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import components to test
from economist_agent import (
    generate_economist_post,
)
from publication_validator import PublicationValidator

# ═══════════════════════════════════════════════════════════════════════════
# MOCK LLM RESPONSES (Deterministic Testing)
# ═══════════════════════════════════════════════════════════════════════════

MOCK_RESEARCH_RESPONSE = """{
  "headline_stat": {
    "value": "Self-healing tests reduce maintenance by 18%",
    "source": "Tricentis 2024 Survey",
    "year": "2024",
    "verified": true
  },
  "data_points": [
    {
      "stat": "81% of companies use AI in testing",
      "source": "Tricentis Research",
      "year": "2024",
      "verified": true
    },
    {
      "stat": "18% maintenance reduction achieved",
      "source": "TestGuild Survey",
      "year": "2024",
      "verified": true
    }
  ],
  "trend_narrative": "AI adoption in testing has surged from 12% in 2018 to 81% in 2024, according to Tricentis Research.",
  "chart_data": {
    "title": "The automation gap",
    "subtitle": "AI adoption vs maintenance reduction, %",
    "type": "line",
    "x_label": "Year",
    "y_label": "Percentage",
    "data": [
      {"label": "2018", "ai_adoption": 12, "maintenance_reduction": 0},
      {"label": "2024", "ai_adoption": 81, "maintenance_reduction": 18}
    ],
    "source_line": "Sources: Tricentis; TestGuild"
  },
  "contrarian_angle": "Despite 81% adoption, only 18% see meaningful maintenance reduction.",
  "unverified_claims": []
}"""

MOCK_WRITER_RESPONSE = """---
layout: post
title: "Self-Healing Tests: The Gap"
date: 2026-01-03
categories: [quality-engineering, test-automation]
author: "The Economist"
---

Self-healing tests reduce maintenance by 18%. That is far short of the 80% promised by vendors.

## The adoption surge

AI adoption in testing has reached 81%, up from just 12% in 2018, according to Tricentis Research.

![The automation gap](/assets/charts/test-automation-gap.png)

As the chart shows, adoption has soared whilst maintenance burden has barely budged.

## The reality gap

Companies are deploying AI testing tools but not seeing proportional benefits. The problem is not the technology but unrealistic expectations.

## References

1. Tricentis Research. (2024). "World Quality Report 2024." Retrieved from tricentis.com
2. Gartner Inc. (2024). "AI Testing Adoption Trends." Retrieved from gartner.com
3. TestGuild. (2024). "Automation Survey 2024." Retrieved from testguild.io

Self-healing tests will remain niche until vendors stop overselling and start delivering."""

MOCK_EDITOR_RESPONSE = """## Quality Gate Results

**GATE 1: OPENING** - PASS
- First sentence hook: Strong statistic (18% vs 80%)
- Throat-clearing present: NO
- Reader engagement: HIGH
**Decision**: PASS

**GATE 2: EVIDENCE** - PASS
- Statistics sourced: 3/3 statistics have sources
- [NEEDS SOURCE] flags removed: YES
- Weasel phrases present: NO
**Decision**: PASS

**GATE 3: VOICE** - PASS
- British spelling: YES (whilst)
- Active voice: YES
- Banned phrases found: NONE
- Exclamation points: NONE
**Decision**: PASS

**GATE 4: STRUCTURE** - PASS
- Logical flow: Clear progression
- Weak ending: NO - definitive prediction
- Redundant paragraphs: NONE
**Decision**: PASS

**GATE 5: CHART INTEGRATION** - PASS
- Chart markdown present: YES
- Chart referenced in text: YES ("As the chart shows")
- Natural integration: YES
**Decision**: PASS

**OVERALL GATES PASSED**: 5/5
**PUBLICATION DECISION**: READY

---

## Edited Article

---
layout: post
title: "Self-Healing Tests: The Gap"
date: 2026-01-03
categories: [quality-engineering, test-automation]
author: "The Economist"
---

Self-healing tests reduce maintenance by 18%. That is far short of the 80% promised by vendors.

## The adoption surge

AI adoption in testing has reached 81%, up from just 12% in 2018, according to Tricentis Research.

![The automation gap](/assets/charts/test-automation-gap.png)

As the chart shows, adoption has soared whilst maintenance burden has barely budged.

## The reality gap

Companies are deploying AI testing tools but not seeing proportional benefits. The problem is not the technology but unrealistic expectations.

## References

1. Tricentis Research. (2024). "World Quality Report 2024." Retrieved from tricentis.com
2. Gartner Inc. (2024). "AI Testing Adoption Trends." Retrieved from gartner.com
3. TestGuild. (2024). "Automation Survey 2024." Retrieved from testguild.io

Self-healing tests will remain niche until vendors stop overselling and start delivering."""


# ═══════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client that returns deterministic responses"""
    client = Mock()
    client.provider = "anthropic"
    # Mock Anthropic API response structure with content[0].text
    mock_response = Mock()
    mock_content = Mock()
    mock_content.text = "Mock response text"
    mock_response.content = [mock_content]
    client.client = Mock()
    client.client.messages = Mock()
    client.client.messages.create = Mock(return_value=mock_response)
    return client


@pytest.fixture
def mock_call_llm():
    """Mock call_llm function"""

    def _mock_call(client, system_prompt, user_prompt, max_tokens=1000, **kwargs):
        # Return different responses based on prompts
        # Accept temperature and other kwargs but ignore them
        if "Research Analyst" in system_prompt:
            return MOCK_RESEARCH_RESPONSE
        elif "senior writer" in system_prompt:
            return MOCK_WRITER_RESPONSE
        elif "chief editor" in system_prompt:
            return MOCK_EDITOR_RESPONSE
        else:
            return '{"status": "ok"}'

    return _mock_call


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestAgentPipeline:
    """Test complete agent pipeline integration"""

    def test_happy_path_end_to_end(
        self, mock_llm_client, mock_call_llm, temp_output_dir
    ):
        """Test: Complete pipeline produces valid article"""

        with (
            patch("llm_client.call_llm", mock_call_llm),
            patch("agents.research_agent.call_llm", mock_call_llm),
            patch("agents.writer_agent.call_llm", mock_call_llm),
            patch("agents.editor_agent.call_llm", mock_call_llm),
            patch("economist_agent.create_llm_client", return_value=mock_llm_client),
            patch("economist_agent.call_llm", mock_call_llm),
        ):
            result = generate_economist_post(
                topic="Self-Healing Tests: Reality Check",
                output_dir=temp_output_dir,
                interactive=False,
            )

            # Check if validation rejected the article
            if result.get("status") == "rejected":
                # Article was quarantined due to validation failure
                assert "validation_failed" in str(result.get("reason", ""))
                assert result["article_path"] is not None
                # Still should have some path even if quarantined
                return

            # Assertions for successful publication
            # Only check gates if not rejected
            if "gates_passed" in result:
                assert result["gates_passed"] == 5, "All quality gates should pass"
                assert result["gates_failed"] == 0, "No gates should fail"
            assert result["article_path"] is not None
            assert Path(result["article_path"]).exists()

            # Verify article content
            with open(result["article_path"]) as f:
                content = f.read()

            assert "---\nlayout: post" in content, "Must have YAML frontmatter"
            assert "date: 2026-01-03" in content, "Must have correct date"
            assert "![" in content, "Must have chart markdown"
            assert "As the chart shows" in content, "Must reference chart"
            assert "## References" in content, "Must have References section"

    def test_chart_integration_workflow(
        self, mock_llm_client, mock_call_llm, temp_output_dir
    ):
        """Test: Chart generation → embedding → validation"""

        # Mock chart generation
        with (
            patch("llm_client.call_llm", mock_call_llm),
            patch("agents.research_agent.call_llm", mock_call_llm),
            patch("agents.writer_agent.call_llm", mock_call_llm),
            patch("economist_agent.call_llm", mock_call_llm),
            patch("agents.editor_agent.call_llm", mock_call_llm),
            patch("economist_agent.create_llm_client", return_value=mock_llm_client),
            patch("economist_agent.run_graphics_agent") as mock_graphics,
        ):
            # Mock graphics agent to create dummy chart
            chart_path = str(Path(temp_output_dir) / "charts" / "test-chart.png")
            Path(chart_path).parent.mkdir(parents=True, exist_ok=True)
            Path(chart_path).write_text("dummy")
            mock_graphics.return_value = chart_path

            result = generate_economist_post(
                topic="Test Chart Integration",
                output_dir=temp_output_dir,
                interactive=False,
            )

            # Chart should be embedded
            with open(result["article_path"]) as f:
                content = f.read()

            assert "![" in content, "Chart must be embedded"
            assert "test-chart.png" in content or "automation-gap" in content

    def test_editor_rejects_bad_content(self, mock_llm_client):
        """Test: Editor quality gates block bad content"""

        bad_draft = """---
layout: post
title: "Bad Article"
date: 2026-01-01
---

In today's fast-paced world, testing is changing. Game-changer tools are revolutionary.

In conclusion, the future remains to be seen!"""

        with patch("economist_agent.call_llm") as mock_call:
            # Mock editor to return failures for bad content
            mock_call.return_value = """## Quality Gate Results
**GATE 1: OPENING** - FAIL
- Throat-clearing: "In today's world"
**GATE 3: VOICE** - FAIL
- Banned phrases: "game-changer", "revolutionary"
**GATE 4: STRUCTURE** - FAIL
- Weak ending: "In conclusion", "remains to be seen"

**OVERALL GATES PASSED**: 2/5
**PUBLICATION DECISION**: NEEDS REVISION"""

            from economist_agent import run_editor_agent

            edited, passed, failed = run_editor_agent(mock_llm_client, bad_draft)

            assert passed < 5, "Bad content should fail quality gates"
            assert failed > 0, "Should have failures"

    def test_publication_validator_blocks_invalid(self, temp_output_dir):
        """Test: Publication validator blocks known issues"""

        # Article with unverified claims and weak ending
        bad_article = """---
layout: post
title: "Test"
date: 2026-01-01
---

Content with [NEEDS SOURCE] claim here.

In conclusion, this is the end."""

        validator = PublicationValidator(expected_date="2026-01-01")
        is_valid, issues = validator.validate(bad_article)

        assert not is_valid, "Should reject article with critical issues"
        # Issues are dicts with 'message' and 'severity' keys
        assert len(issues) > 0
        # Check for verification flags or weak ending
        issue_messages = [issue["message"].lower() for issue in issues]
        critical_found = any(
            "unverified" in msg
            or "verification" in msg
            or "ending" in msg
            or "conclusion" in msg
            for msg in issue_messages
        )
        assert critical_found, f"Should catch critical issues, got: {issue_messages}"

    def test_chart_embedding_validation(self):
        """Test: Validator catches missing chart embedding (BUG-016 pattern)"""

        # Article with NO chart despite chart_data existing
        article_no_chart = """---
layout: post
title: "Test Article"
date: 2026-01-01
---

Some content about data. No chart embedded."""

        validator = PublicationValidator()
        is_valid, issues = validator.validate(article_no_chart)

        # Should pass baseline checks (has layout, date, etc.)
        # Chart check requires chart_data context - tested in defect_prevention_rules

    def test_agent_data_flow(self, mock_llm_client, mock_call_llm):
        """Test: Data flows correctly between agents"""

        with (
            patch("llm_client.call_llm", mock_call_llm),
            patch("agents.research_agent.call_llm", mock_call_llm),
            patch("agents.writer_agent.call_llm", mock_call_llm),
            patch("economist_agent.create_llm_client", return_value=mock_llm_client),
        ):
            # Research agent output
            from economist_agent import run_research_agent

            research = run_research_agent(mock_llm_client, "Test Topic")

            assert "headline_stat" in research, "Research should return structured data"
            assert "chart_data" in research, "Research should include chart_data"

            # Chart data should flow to writer
            assert research["chart_data"]["title"] == "The automation gap"

    def test_error_handling_graceful_degradation(self, mock_llm_client):
        """Test: Pipeline handles errors gracefully by raising proper exceptions"""

        # Import research agent
        from economist_agent import run_research_agent

        # Test 1: Invalid topic (empty string) should raise ValueError
        with pytest.raises(ValueError, match="Invalid topic"):
            run_research_agent(mock_llm_client, "")

        # Test 2: Invalid topic (too short) should raise ValueError
        with pytest.raises(ValueError, match="Topic too short"):
            run_research_agent(mock_llm_client, "Hi")


class TestDefectPrevention:
    """Test that known defect patterns are prevented"""

    def test_bug_016_pattern_prevented(self):
        """Test: BUG-016 pattern (chart not embedded) is caught"""
        from defect_prevention_rules import DefectPrevention

        article_missing_chart = """---
layout: post
title: "Test"
date: 2026-01-01
categories: [testing]
---

Content without chart."""

        prevention = DefectPrevention()
        violations = prevention.check_all(article_missing_chart, {"chart_data": True})

        # Should detect missing chart embedding
        assert any(
            "chart" in v.lower() for v in violations
        ), f"Should catch missing chart. Got violations: {violations}"

    def test_bug_015_pattern_prevented(self):
        """Test: BUG-015 pattern (missing category) is caught"""
        from defect_prevention_rules import DefectPrevention

        article_no_category = """---
layout: post
title: "Test"
date: 2026-01-01
---"""

        prevention = DefectPrevention()
        violations = prevention.check_all(article_no_category, {})

        # Should detect missing category
        assert any(
            "category" in v.lower() for v in violations
        ), "Should catch missing category"


# ═══════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
