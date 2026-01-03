#!/usr/bin/env python3
"""
Test Suite for FEATURE-001: References Section

Tests Writer Agent and Publication Validator enhancements
for references section functionality.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add agents directory to path
_agents_dir = Path(__file__).parent.parent / "agents"
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

# Add scripts directory to path
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from writer_agent import WriterAgent
from publication_validator import PublicationValidator


class TestWriterAgentReferences:
    """Test Writer Agent references section generation"""

    def test_format_references_guidance_with_sources(self):
        """Should format references guidance from research data"""
        client = MagicMock()
        agent = WriterAgent(client)

        research_brief = {
            "headline_stat": {
                "value": "80%",
                "source": "Gartner",
                "year": "2024",
                "verified": True,
            },
            "data_points": [
                {
                    "stat": "50% adoption",
                    "source": "Forrester Research",
                    "year": "2024",
                    "url": "https://forrester.com/report",
                    "verified": True,
                },
                {
                    "stat": "30% ROI",
                    "source": "IEEE",
                    "year": "2023",
                    "verified": True,
                },
            ],
        }

        guidance = agent._format_references_guidance(research_brief)

        # Should include references header
        assert "REFERENCES SOURCES AVAILABLE" in guidance

        # Should list sources
        assert "Gartner" in guidance
        assert "Forrester Research" in guidance
        assert "IEEE" in guidance

        # Should include URLs when available
        assert "https://forrester.com/report" in guidance

        # Should include years
        assert "2024" in guidance
        assert "2023" in guidance

        # Should provide formatting instructions
        assert "Format these as proper references" in guidance
        assert "descriptive link text" in guidance

    def test_format_references_guidance_no_sources(self):
        """Should return empty string when no verified sources"""
        client = MagicMock()
        agent = WriterAgent(client)

        research_brief = {
            "data_points": [
                {
                    "stat": "Unverified claim",
                    "source": "Unknown",
                    "verified": False,  # Not verified
                }
            ]
        }

        guidance = agent._format_references_guidance(research_brief)

        # Should return empty string
        assert guidance == ""

    def test_format_references_guidance_deduplicates(self):
        """Should deduplicate identical sources"""
        client = MagicMock()
        agent = WriterAgent(client)

        research_brief = {
            "data_points": [
                {
                    "stat": "50%",
                    "source": "Gartner",
                    "year": "2024",
                    "verified": True,
                },
                {
                    "stat": "60%",
                    "source": "Gartner",
                    "year": "2024",
                    "verified": True,
                },
            ]
        }

        guidance = agent._format_references_guidance(research_brief)

        # Should only mention Gartner once
        assert guidance.count("Gartner") == 1

    def test_format_references_guidance_max_five(self):
        """Should limit to 5 sources max"""
        client = MagicMock()
        agent = WriterAgent(client)

        research_brief = {
            "data_points": [
                {"source": f"Source {i}", "year": "2024", "verified": True}
                for i in range(10)
            ]
        }

        guidance = agent._format_references_guidance(research_brief)

        # Should have max 5 numbered items
        numbered_items = [line for line in guidance.split("\n") if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))]
        assert len(numbered_items) <= 5


class TestPublicationValidatorReferences:
    """Test Publication Validator references checks"""

    def test_missing_references_section_critical(self):
        """Should flag missing References section as CRITICAL"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article"
date: 2026-01-02
---

# Article content

This is an article without a references section.

## Conclusion

The end.
"""

        is_valid, issues = validator.validate(article)

        # Should fail validation
        assert not is_valid

        # Should have CRITICAL issue about missing references
        critical_refs = [
            i
            for i in issues
            if i["check"] == "missing_references" and i["severity"] == "CRITICAL"
        ]
        assert len(critical_refs) == 1
        assert "References section" in critical_refs[0]["message"]

    def test_empty_references_section_critical(self):
        """Should flag empty References section as CRITICAL"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article"
date: 2026-01-02
---

# Article content

This is an article.

## References

## Conclusion
"""

        is_valid, issues = validator.validate(article)

        # Should fail validation
        assert not is_valid

        # Should have CRITICAL issue about empty references
        empty_refs = [
            i
            for i in issues
            if i["check"] == "empty_references" and i["severity"] == "CRITICAL"
        ]
        assert len(empty_refs) == 1

    def test_insufficient_references_critical(self):
        """Should require minimum 3 references"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article"
date: 2026-01-02
---

# Article content

This is an article.

## References

1. Source One, "Report", *Publication*, 2024
2. Source Two, "Study", *Journal*, 2024
"""

        is_valid, issues = validator.validate(article)

        # Should fail validation (only 2 references)
        assert not is_valid

        # Should have CRITICAL issue about insufficient references
        insufficient_refs = [
            i
            for i in issues
            if i["check"] == "insufficient_references" and i["severity"] == "CRITICAL"
        ]
        assert len(insufficient_refs) == 1
        assert "Only 2 reference(s) found" in insufficient_refs[0]["message"]

    def test_references_with_three_sources_passes(self):
        """Should pass with 3+ properly formatted references"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article: Proper References"
date: 2026-01-02
---

# Article content

This is a proper article with citations.

## References

1. Gartner, ["World Quality Report 2024"](https://gartner.com/report), *Gartner Research*, November 2024
2. Forrester, ["Testing Automation Trends"](https://forrester.com/study), *Forrester Research*, October 2024
3. IEEE, ["Software Testing Standards"](https://ieee.org/standards), *IEEE Computer Society*, September 2024
"""

        is_valid, issues = validator.validate(article)

        # Should pass validation
        assert is_valid

        # Should have no CRITICAL reference issues
        critical_ref_issues = [
            i
            for i in issues
            if "reference" in i["check"] and i["severity"] == "CRITICAL"
        ]
        assert len(critical_ref_issues) == 0

    def test_bad_link_text_patterns_detected(self):
        """Should detect poor link text patterns"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article: Bad Links"
date: 2026-01-02
---

# Article content

This article has bad link text.

## References

1. Source One, [click here](https://example.com), *Publication*, 2024
2. Source Two, [here](https://example.com), *Journal*, 2024
3. Source Three, [https://example.com/report](https://example.com/report), *Report*, 2024
"""

        is_valid, issues = validator.validate(article)

        # Should have HIGH severity issue about bad links
        bad_links = [
            i
            for i in issues
            if i["check"] == "bad_reference_links" and i["severity"] == "HIGH"
        ]
        assert len(bad_links) == 1
        assert "poor link text" in bad_links[0]["message"]

        # Should detect "click here", "here", and bare URL
        details = bad_links[0]["details"]
        assert "[click here]" in details or "click here" in details.lower()
        assert "[here]" in details or "Generic" in details
        assert "https://" in details or "Bare URL" in details

    def test_references_section_format_validation(self):
        """Should validate references are in numbered list format"""
        validator = PublicationValidator(expected_date="2026-01-02")

        article = """---
layout: post
title: "Test Article: Bad Format"
date: 2026-01-02
---

# Article content

Content.

## References

- Source One (bullet instead of number)
- Source Two
- Source Three
"""

        is_valid, issues = validator.validate(article)

        # Should fail - bullets won't be counted as references
        assert not is_valid

        # Should flag insufficient references (0 found since no numbered items)
        insufficient = [
            i
            for i in issues
            if i["check"] == "insufficient_references" and i["severity"] == "CRITICAL"
        ]
        assert len(insufficient) == 1


class TestReferencesIntegration:
    """Integration tests for references feature"""

    @patch("writer_agent.call_llm")
    def test_writer_agent_includes_references_guidance(self, mock_llm):
        """Should include references guidance in system prompt"""
        mock_llm.return_value = """---
layout: post
title: "Test Article"
date: 2026-01-02
---

Content with data.

## References

1. Gartner, ["Report"](https://gartner.com), *Research*, 2024
2. Forrester, ["Study"](https://forrester.com), *Research*, 2024
3. IEEE, ["Standards"](https://ieee.org), *Society*, 2024
"""

        client = MagicMock()
        agent = WriterAgent(client)

        research_brief = {
            "headline_stat": {
                "value": "80%",
                "source": "Gartner",
                "year": "2024",
                "verified": True,
            },
            "data_points": [
                {
                    "stat": "50%",
                    "source": "Forrester",
                    "year": "2024",
                    "url": "https://forrester.com",
                    "verified": True,
                }
            ],
        }

        draft, metadata = agent.write(
            topic="Test Topic",
            research_brief=research_brief,
            current_date="2026-01-02",
        )

        # Verify LLM was called with references guidance
        call_args = mock_llm.call_args
        system_prompt = call_args[0][1]  # Second positional arg

        # Should include references section requirement
        assert "## References" in system_prompt
        assert "REFERENCES SECTION - MANDATORY" in system_prompt

        # Should include sources from research
        assert "Gartner" in system_prompt
        assert "Forrester" in system_prompt

    def test_end_to_end_references_validation(self):
        """Should validate complete article with references"""
        # Create a complete article with proper references
        article = """---
layout: post
title: "Self-Healing Tests: Myth vs Reality"
date: 2026-01-02
author: "The Economist"
---

# The automation paradox

Self-healing tests promise an 80% reduction in maintenance costs. According to Gartner, only 10% of companies achieve it.

The gap between promise and reality reveals something important about automation. It's not the technology that fails—it's the expectations.

## The reality check

Forrester's 2024 study shows that self-healing tests reduce maintenance time by 18%, not 80%. The discrepancy comes from vendor marketing overselling capabilities.

IEEE research confirms these findings. Their September 2024 standards document shows that most "self-healing" features are simple retry logic.

## References

1. Gartner, ["World Quality Report 2024"](https://www.gartner.com/report), *Gartner Research*, November 2024
2. Forrester, ["State of Test Automation 2024"](https://www.forrester.com/automation), *Forrester Research*, September 2024
3. IEEE, ["Software Testing Standards Update"](https://www.ieee.org/testing), *IEEE Computer Society*, August 2024
"""

        validator = PublicationValidator(expected_date="2026-01-02")
        is_valid, issues = validator.validate(article)

        # Should pass all checks including references
        assert is_valid

        # Should have no CRITICAL issues
        critical = [i for i in issues if i["severity"] == "CRITICAL"]
        assert len(critical) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
