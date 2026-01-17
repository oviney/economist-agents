#!/usr/bin/env python3
"""
Integration tests for Writer Agent YAML front matter validation (BUG-031)

These tests verify that Writer Agent:
1. Generates articles with proper YAML front matter
2. Self-validates YAML format before returning output
3. Catches common YAML errors that would cause publication failures

Related Bugs:
- BUG-028: Articles missing opening --- delimiter
- BUG-029: Articles too short (478-543 words vs 800+ required)
- BUG-031: Systematic YAML front matter validation gap
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.writer_agent import WriterAgent, run_writer_agent

# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_client():
    """Mock LLM client for testing"""
    client = MagicMock()
    client.provider = "anthropic"
    return client


@pytest.fixture
def mock_governance():
    """Mock governance tracker"""
    governance = MagicMock()
    governance.log_agent_output = MagicMock()
    return governance


@pytest.fixture
def sample_research():
    """Research brief for testing"""
    return {
        "topic": "Understanding OpenDNS: Cybersecurity Protection",
        "trend_narrative": "OpenDNS provides DNS-level security filtering",
        "key_sources": [
            {
                "claim": "DNS filtering blocks 80% of malware",
                "source": "Cisco Security Report 2024",
                "verified": True,
            }
        ],
        "data_points": [
            {
                "statistic": "80% malware blocked",
                "source": "Cisco Security Report 2024",
                "verified": True,
            }
        ],
        "contrarian_angle": "DNS filtering has blind spots in encrypted traffic",
    }


@pytest.fixture
def valid_yaml_article():
    """Article with CORRECT YAML front matter"""
    return """---
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
categories: [quality-engineering]
---

# The DNS Guardian

Cisco's OpenDNS filters 100 billion DNS requests daily, blocking threats before they reach endpoints. According to the 2024 Cisco Security Report, DNS-level filtering intercepts 80% of malware before traditional antivirus sees it.

The approach is elegantly simple: resolve suspicious domains to nothing. But encrypted DNS (DoH/DoT) creates blind spots. Organizations must balance security visibility with privacy.

Smart enterprises layer DNS filtering with endpoint protection. OpenDNS is the first gate, not the only gate.
"""


@pytest.fixture
def missing_opening_delimiter_article():
    """Article MISSING opening --- (BUG-028 pattern)"""
    return """layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
---

Article content here...
"""


@pytest.fixture
def code_fence_yaml_article():
    """Article with WRONG ```yaml wrapper"""
    return """```yaml
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
```

Article content here...
"""


@pytest.fixture
def missing_closing_delimiter_article():
    """Article MISSING closing ---"""
    return """---
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"

Article content here without closing delimiter...
"""


@pytest.fixture
def missing_layout_field_article():
    """Article MISSING required layout field"""
    return """---
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
---

Article content here...
"""


@pytest.fixture
def wrong_date_article():
    """Article with WRONG date (from research source, not today)"""
    return """---
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2024-03-15
author: "The Economist"
---

Article content here...
"""


# ═══════════════════════════════════════════════════════════════════════════
# YAML FRONT MATTER VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestYAMLFrontMatterValidation:
    """Test Writer Agent catches common YAML errors before publication"""

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_valid_yaml_passes_validation(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        valid_yaml_article,
    ):
        """GIVEN valid YAML front matter
        WHEN Writer Agent validates output
        THEN article passes without regeneration
        """
        # Arrange
        mock_call_llm.return_value = valid_yaml_article
        mock_review.return_value = (True, [])

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert draft.startswith("---\n"), "Article must start with opening ---"
        assert "layout: post" in draft, "Article must have layout field"
        assert "date: 2026-01-05" in draft, "Article must have correct date"
        assert "---\n\n#" in draft or "---\n#" in draft, "Article must have closing ---"
        assert metadata["is_valid"] is True
        assert metadata["regenerated"] is False
        assert mock_call_llm.call_count == 1  # No regeneration needed

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_missing_opening_delimiter_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        missing_opening_delimiter_article,
        valid_yaml_article,
    ):
        """GIVEN article missing opening ---
        WHEN Writer Agent validates
        THEN critical issue flagged AND regeneration attempted
        """
        # Arrange - first call returns invalid, second returns valid
        mock_call_llm.side_effect = [
            missing_opening_delimiter_article,
            valid_yaml_article,
        ]
        mock_review.side_effect = [
            (False, ["CRITICAL: Missing opening --- delimiter"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert draft.startswith("---\n"), "Regenerated article must start with ---"
        assert metadata["regenerated"] is True
        assert mock_call_llm.call_count == 2  # Regeneration happened

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_code_fence_yaml_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        code_fence_yaml_article,
        valid_yaml_article,
    ):
        """GIVEN article with ```yaml wrapper
        WHEN Writer Agent validates
        THEN critical issue flagged (code fence forbidden)
        """
        # Arrange
        mock_call_llm.side_effect = [code_fence_yaml_article, valid_yaml_article]
        mock_review.side_effect = [
            (False, ["CRITICAL: Code fence ```yaml wrapper forbidden"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert not draft.startswith("```yaml"), "Must not use code fences"
        assert draft.startswith("---\n"), "Must use --- delimiters"
        assert metadata["regenerated"] is True

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_missing_closing_delimiter_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        missing_closing_delimiter_article,
        valid_yaml_article,
    ):
        """GIVEN article missing closing ---
        WHEN Writer Agent validates
        THEN critical issue flagged
        """
        # Arrange
        mock_call_llm.side_effect = [
            missing_closing_delimiter_article,
            valid_yaml_article,
        ]
        mock_review.side_effect = [
            (False, ["CRITICAL: Missing closing --- delimiter"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        # Check for closing delimiter after opening YAML block
        yaml_end = draft.find("---", 4)  # Find second ---
        assert yaml_end > 0, "Must have closing --- after front matter"
        assert metadata["regenerated"] is True

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_missing_layout_field_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        missing_layout_field_article,
        valid_yaml_article,
    ):
        """GIVEN article missing required layout field
        WHEN Writer Agent validates
        THEN critical issue flagged (Jekyll requires layout)
        """
        # Arrange
        mock_call_llm.side_effect = [missing_layout_field_article, valid_yaml_article]
        mock_review.side_effect = [
            (False, ["CRITICAL: Missing required layout field"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert "layout: post" in draft, "Must have layout field"
        assert metadata["regenerated"] is True

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_wrong_date_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        wrong_date_article,
        valid_yaml_article,
    ):
        """GIVEN article with wrong date (from research, not today)
        WHEN Writer Agent validates
        THEN critical issue flagged (date must be current_date)
        """
        # Arrange
        mock_call_llm.side_effect = [wrong_date_article, valid_yaml_article]
        mock_review.side_effect = [
            (False, ["CRITICAL: Date is 2024-03-15, should be 2026-01-05"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert "date: 2026-01-05" in draft, "Must use current_date"
        assert "date: 2024-03-15" not in draft, "Must not use research source dates"
        assert metadata["regenerated"] is True

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_missing_categories_field_triggers_regeneration(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        valid_yaml_article,
    ):
        """GIVEN article missing required categories field (BUG-015 pattern)
        WHEN Writer Agent validates
        THEN critical issue flagged (categories required for Jekyll)
        """
        # Arrange - article without categories field
        missing_categories_article = """---
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
---

# Article content here...
"""
        mock_call_llm.side_effect = [missing_categories_article, valid_yaml_article]
        mock_review.side_effect = [
            (False, ["CRITICAL: Missing required field 'categories'"]),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert
        assert "categories:" in draft, "Must have categories field"
        assert metadata["regenerated"] is True


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY WRAPPER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestRunWriterAgentWrapper:
    """Test backward compatibility wrapper validates YAML"""

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_wrapper_returns_valid_yaml(
        self,
        mock_review,
        mock_call_llm,
        mock_client,
        sample_research,
        valid_yaml_article,
    ):
        """GIVEN run_writer_agent() wrapper called
        WHEN article generated
        THEN returns valid YAML front matter
        """
        # Arrange
        mock_call_llm.return_value = valid_yaml_article
        mock_review.return_value = (True, [])

        # Act
        draft, metadata = run_writer_agent(
            mock_client, "Test Topic", sample_research, "2026-01-05"
        )

        # Assert
        assert draft.startswith("---\n"), "Wrapper must return valid YAML"
        assert "layout: post" in draft
        assert metadata["is_valid"] is True


# ═══════════════════════════════════════════════════════════════════════════
# PUBLICATION VALIDATOR INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════


class TestPublicationValidatorIntegration:
    """Test that Writer Agent validation matches publication validator rules"""

    @patch("agents.writer_agent.call_llm")
    @patch("agents.writer_agent.review_agent_output")
    def test_writer_catches_all_publication_validator_yaml_errors(
        self, mock_review, mock_call_llm, mock_client, sample_research
    ):
        """GIVEN article with multiple YAML errors
        WHEN Writer Agent validates
        THEN ALL errors that would cause publication failure are caught
        """
        # Arrange - article with multiple YAML issues
        invalid_article = """```yaml
title: "Generic Title"
date: 2024-01-01
```
Short article content less than 800 words."""

        valid_article = (
            """---
layout: post
title: "Understanding OpenDNS: Cybersecurity Protection"
date: 2026-01-05
author: "The Economist"
categories: [quality-engineering]
---

# The DNS Guardian

[800+ word article content here...]
"""
            * 10
        )  # Make it long enough

        mock_call_llm.side_effect = [invalid_article, valid_article]
        mock_review.side_effect = [
            (
                False,
                [
                    "CRITICAL: Code fence ```yaml wrapper forbidden",
                    "CRITICAL: Missing opening --- delimiter",
                    "CRITICAL: Missing layout field",
                    "CRITICAL: Wrong date (should be 2026-01-05)",
                    "CRITICAL: Generic title",
                    "CRITICAL: Article too short (<800 words)",
                ],
            ),
            (True, []),
        ]

        agent = WriterAgent(mock_client, None)

        # Act
        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=sample_research,
            current_date="2026-01-05",
            chart_filename=None,
        )

        # Assert - verify Writer caught ALL issues before publication validator would
        assert draft.startswith("---\n"), "Must catch opening delimiter issue"
        assert not draft.startswith("```yaml"), "Must catch code fence issue"
        assert "layout: post" in draft, "Must catch missing layout issue"
        assert "date: 2026-01-05" in draft, "Must catch wrong date issue"
        # Word count check: Mock returns placeholder text, so we verify structure instead
        assert len(draft) > 500, "Must generate non-trivial content after regeneration"
        assert metadata["regenerated"] is True
        assert "critical_issues" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
