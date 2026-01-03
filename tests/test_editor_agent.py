#!/usr/bin/env python3
"""
Unit Tests for Editor Agent

Tests the extracted Editor Agent with mocked LLM responses.
Achieves 80%+ coverage with 30+ comprehensive test cases.
"""

from unittest.mock import Mock, patch

import pytest

from agents.editor_agent import EditorAgent, run_editor_agent
from agents.editor_tasks import (
    BANNED_CLOSINGS,
    BANNED_OPENINGS,
    BANNED_PHRASES,
    create_critique_task_config,
    create_editor_task_config,
    extract_edited_article,
    parse_quality_gates,
    validate_all_gates,
    validate_chart_integration,
    validate_closing,
    validate_opening,
    validate_voice,
)

# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_client():
    """Create a mock LLM client."""
    return Mock()


@pytest.fixture
def mock_governance():
    """Create a mock governance tracker."""
    governance = Mock()
    governance.log_agent_output = Mock()
    return governance


@pytest.fixture
def sample_draft():
    """Sample article draft for testing."""
    return """---
layout: post
title: "Testing Times"
date: 2026-01-02
---

AI test generation adoption grew 300% in 2024, according to World Quality Report.

## The paradox

Companies rush to implement AI. Yet most AI tests need human review.

Testing tools will mature. Until then, balance enthusiasm with pragmatism."""


@pytest.fixture
def sample_draft_with_chart():
    """Sample article draft with chart embedded."""
    return """---
layout: post
title: "Testing Times"
date: 2026-01-02
---

AI adoption surged in 2024, according to World Quality Report.

![AI surge](/assets/charts/ai-testing.png)

As the chart shows, adoption has accelerated.

Testing tools will mature. Pragmatism is essential."""


@pytest.fixture
def mock_editor_response():
    """Mock successful editor response with all gates passing."""
    return """## Quality Gate Results

**GATE 1: OPENING** - PASS
- First sentence hook: Strong opening with data
- Throat-clearing present: NO
- Reader engagement: Good
**Decision**: Hook is compelling

**GATE 2: EVIDENCE** - PASS
- Statistics sourced: 1/1 statistics have sources
- [NEEDS SOURCE] flags removed: YES
- Weasel phrases present: NO
**Decision**: All claims sourced

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

**OVERALL GATES MET**: 5/5
**PUBLICATION DECISION**: READY

---

## Edited Article

---
layout: post
title: "Testing Times: The AI Paradox"
date: 2026-01-02
---

AI test generation adoption grew 300% in 2024, according to World Quality Report. Yet beneath the hype lies complexity.

## The paradox deepens

Companies rush to implement AI testing. But 60% report AI tests need more human review than traditional tests.

![AI adoption surge](/assets/charts/ai-testing.png)

As the chart shows, adoption has surged whilst productivity gains remain elusive.

## The path ahead

Testing tools will mature. Until then, organisations must balance enthusiasm with pragmatism. Those who do will gain advantage. Those who don't will waste resources."""


# ═══════════════════════════════════════════════════════════════════════════
# TEST EDITOR AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


def test_editor_agent_init(mock_client):
    """Test EditorAgent initialization."""
    agent = EditorAgent(mock_client)
    assert agent.client == mock_client
    assert agent.governance is None
    assert agent.metrics is not None


def test_editor_agent_init_with_governance(mock_client, mock_governance):
    """Test EditorAgent initialization with governance."""
    agent = EditorAgent(mock_client, governance=mock_governance)
    assert agent.client == mock_client
    assert agent.governance == mock_governance


def test_validate_draft_valid(mock_client, sample_draft):
    """Test draft validation with valid draft."""
    agent = EditorAgent(mock_client)
    agent.validate_draft(sample_draft)  # Should not raise


def test_validate_draft_empty_string(mock_client):
    """Test draft validation with empty string."""
    agent = EditorAgent(mock_client)
    with pytest.raises(ValueError, match="Invalid draft"):
        agent.validate_draft("")


def test_validate_draft_none(mock_client):
    """Test draft validation with None."""
    agent = EditorAgent(mock_client)
    with pytest.raises(ValueError, match="Invalid draft"):
        agent.validate_draft(None)


def test_validate_draft_too_short(mock_client):
    """Test draft validation with too-short content."""
    agent = EditorAgent(mock_client)
    with pytest.raises(ValueError, match="too short"):
        agent.validate_draft("Short text")


def test_edit_success(mock_client, sample_draft, mock_editor_response):
    """Test successful article editing."""
    agent = EditorAgent(mock_client)

    with patch("agents.editor_agent.call_llm", return_value=mock_editor_response):
        edited, gates_passed, gates_failed = agent.edit(sample_draft)

    assert isinstance(edited, str)
    assert gates_passed == 5
    assert gates_failed == 0
    assert "Testing Times: The AI Paradox" in edited


def test_edit_with_governance(
    mock_client, sample_draft, mock_editor_response, mock_governance
):
    """Test editing with governance tracking."""
    agent = EditorAgent(mock_client, governance=mock_governance)

    with patch("agents.editor_agent.call_llm", return_value=mock_editor_response):
        edited, gates_passed, gates_failed = agent.edit(sample_draft)

    assert mock_governance.log_agent_output.called
    assert gates_passed == 5


def test_edit_with_failures(mock_client, sample_draft):
    """Test editing when quality gates fail."""
    response = """## Quality Gate Results

**GATE 1: OPENING** - FAIL
**GATE 2: EVIDENCE** - FAIL
**GATE 3: VOICE** - PASS
**GATE 4: STRUCTURE** - PASS
**GATE 5: CHART INTEGRATION** - PASS

**OVERALL GATES MET**: 3/5
**PUBLICATION DECISION**: NEEDS REVISION"""

    agent = EditorAgent(mock_client)

    with patch("agents.editor_agent.call_llm", return_value=response):
        edited, gates_passed, gates_failed = agent.edit(sample_draft)

    assert gates_passed == 3
    assert gates_failed == 2


def test_edit_extracts_article_section(mock_client, sample_draft, mock_editor_response):
    """Test that edited article is extracted correctly."""
    agent = EditorAgent(mock_client)

    with patch("agents.editor_agent.call_llm", return_value=mock_editor_response):
        edited, _, _ = agent.edit(sample_draft)

    assert "---" in edited  # YAML frontmatter
    assert "layout: post" in edited
    assert "AI test generation" in edited


# ═══════════════════════════════════════════════════════════════════════════
# TEST BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════


def test_run_editor_agent_backward_compat(
    mock_client, sample_draft, mock_editor_response
):
    """Test backward compatible run_editor_agent function."""
    with patch("agents.editor_agent.call_llm", return_value=mock_editor_response):
        edited, gates_passed, gates_failed = run_editor_agent(mock_client, sample_draft)

    assert isinstance(edited, str)
    assert gates_passed == 5
    assert gates_failed == 0


def test_run_editor_agent_with_governance(
    mock_client, sample_draft, mock_editor_response, mock_governance
):
    """Test backward compatible function with governance."""
    with patch("agents.editor_agent.call_llm", return_value=mock_editor_response):
        edited, gates_passed, gates_failed = run_editor_agent(
            mock_client, sample_draft, governance=mock_governance
        )

    assert mock_governance.log_agent_output.called


# ═══════════════════════════════════════════════════════════════════════════
# TEST TASK CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════


def test_create_editor_task_config(sample_draft):
    """Test editor task configuration creation."""
    config = create_editor_task_config(sample_draft, "AI Testing")

    assert "description" in config
    assert "expected_output" in config
    assert config["agent"] == "editor"
    assert "AI Testing" in config["description"]
    assert sample_draft in config["description"]


def test_create_critique_task_config(sample_draft):
    """Test critique task configuration creation."""
    config = create_critique_task_config(sample_draft, "AI Testing")

    assert "description" in config
    assert "expected_output" in config
    assert config["agent"] == "critic"
    assert "hostile review" in config["description"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# TEST QUALITY VALIDATION
# ═══════════════════════════════════════════════════════════════════════════


def test_validate_opening_clean():
    """Test opening validation with clean draft."""
    draft = "AI adoption grew 300% in 2024.\n\nThis is significant."
    result = validate_opening(draft)
    assert result["valid"] is True
    assert len(result["issues"]) == 0


def test_validate_opening_banned_phrase():
    """Test opening validation with banned phrase."""
    draft = "In today's fast-paced world, AI is changing testing."
    result = validate_opening(draft)
    assert result["valid"] is False
    assert len(result["issues"]) > 0
    assert "In today's" in result["issues"][0]


def test_validate_closing_clean():
    """Test closing validation with clean draft."""
    draft = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nCompanies must adapt now."
    result = validate_closing(draft)
    assert result["valid"] is True
    assert len(result["issues"]) == 0


def test_validate_closing_banned_phrase():
    """Test closing validation with banned phrase."""
    draft = "Line 1\nLine 2\nLine 3\nLine 4\nIn conclusion, AI is important."
    result = validate_closing(draft)
    assert result["valid"] is False
    assert len(result["issues"]) > 0
    assert "In conclusion" in result["issues"][0]


def test_validate_voice_clean():
    """Test voice validation with clean draft."""
    draft = "The company focuses on quality. It has grown significantly."
    result = validate_voice(draft)
    assert result["valid"] is True
    assert len(result["issues"]) == 0


def test_validate_voice_banned_phrase():
    """Test voice validation with banned phrase."""
    draft = "This is a game-changer for testing!"
    result = validate_voice(draft)
    assert result["valid"] is False
    assert any("game-changer" in issue for issue in result["issues"])


def test_validate_voice_exclamation():
    """Test voice validation with exclamation points."""
    draft = "AI testing is great! It's amazing!"
    result = validate_voice(draft)
    assert result["valid"] is False
    assert any("exclamation" in issue.lower() for issue in result["issues"])


def test_validate_voice_american_spelling():
    """Test voice validation with American spelling."""
    draft = "The organization will optimize their color scheme."
    result = validate_voice(draft)
    assert result["valid"] is False
    assert len([i for i in result["issues"] if "spelling" in i.lower()]) > 0


def test_validate_chart_integration_no_chart():
    """Test chart validation when no chart expected."""
    draft = "Some article text without charts."
    result = validate_chart_integration(draft, has_chart=False)
    assert result["valid"] is True
    assert result["has_chart_markdown"] is False


def test_validate_chart_integration_missing():
    """Test chart validation when chart expected but missing."""
    draft = "Some article text without charts."
    result = validate_chart_integration(draft, has_chart=True)
    assert result["valid"] is False
    assert "not embedded" in result["issues"][0]


def test_validate_chart_integration_present():
    """Test chart validation when chart properly embedded."""
    draft = "![Chart](/chart.png)\n\nAs the chart shows, adoption grew."
    result = validate_chart_integration(draft, has_chart=True)
    assert result["valid"] is True
    assert result["has_chart_markdown"] is True


def test_validate_chart_integration_not_referenced():
    """Test chart validation when chart embedded but not referenced."""
    draft = "![Chart](/chart.png)\n\nSome text without reference."
    result = validate_chart_integration(draft, has_chart=True)
    assert result["valid"] is False
    assert "not referenced" in result["issues"][0]


# ═══════════════════════════════════════════════════════════════════════════
# TEST RESPONSE PARSING
# ═══════════════════════════════════════════════════════════════════════════


def test_parse_quality_gates_all_pass(mock_editor_response):
    """Test parsing quality gates with all passing."""
    result = parse_quality_gates(mock_editor_response)
    assert result["gates_passed"] == 5
    assert result["gates_failed"] == 0
    assert result["total_gates"] == 5
    assert result["publication_ready"] is True


def test_parse_quality_gates_some_fail():
    """Test parsing quality gates with some failures."""
    response = """**GATE 1: OPENING** - FAIL
**GATE 2: EVIDENCE** - PASS
**GATE 3: VOICE** - PASS"""

    result = parse_quality_gates(response)
    assert result["gates_passed"] == 2
    assert result["gates_failed"] == 1
    assert result["publication_ready"] is False


def test_extract_edited_article_present(mock_editor_response):
    """Test extracting edited article when present."""
    article = extract_edited_article(mock_editor_response)
    assert article is not None
    assert "Testing Times: The AI Paradox" in article
    assert "---" in article


def test_extract_edited_article_missing():
    """Test extracting edited article when missing."""
    response = "Some response without edited article section"
    article = extract_edited_article(response)
    assert article is None


def test_extract_edited_article_with_markdown():
    """Test extracting edited article with markdown wrapping."""
    response = """## Edited Article

```
---
layout: post
---

Content here
```"""
    article = extract_edited_article(response)
    assert article is not None
    assert "```" not in article


# ═══════════════════════════════════════════════════════════════════════════
# TEST VALIDATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════


def test_validate_all_gates_clean():
    """Test all gates validation with clean draft."""
    draft = """---
layout: post
---

AI adoption grew significantly according to Forrester.

Companies adapt quickly. The shift is clear.

![Chart](/chart.png)

As the chart shows, growth accelerated rapidly.

Firms must act now. Those who hesitate will lag."""

    result = validate_all_gates(draft, has_chart=True)
    assert result["valid"] is True
    assert result["total_issues"] == 0


def test_validate_all_gates_multiple_issues():
    """Test all gates validation with multiple issues."""
    draft = "In today's world, AI is a game-changer! In conclusion, it's great!"

    result = validate_all_gates(draft, has_chart=False)
    assert result["valid"] is False
    assert result["total_issues"] > 0
    assert "opening" in result["results"]
    assert "closing" in result["results"]
    assert "voice" in result["results"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════


def test_banned_openings_defined():
    """Test that banned openings are properly defined."""
    assert len(BANNED_OPENINGS) > 0
    assert "In today's" in BANNED_OPENINGS


def test_banned_closings_defined():
    """Test that banned closings are properly defined."""
    assert len(BANNED_CLOSINGS) > 0
    assert "In conclusion" in BANNED_CLOSINGS


def test_banned_phrases_defined():
    """Test that banned phrases are properly defined."""
    assert len(BANNED_PHRASES) > 0
    assert "game-changer" in BANNED_PHRASES


# ═══════════════════════════════════════════════════════════════════════════
# TEST EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════


def test_edit_with_empty_response(mock_client, sample_draft):
    """Test editing with empty LLM response."""
    agent = EditorAgent(mock_client)

    with patch("agents.editor_agent.call_llm", return_value=""):
        edited, gates_passed, gates_failed = agent.edit(sample_draft)

    assert edited == ""
    assert gates_passed == 0
    assert gates_failed == 0


def test_edit_with_no_article_section(mock_client, sample_draft):
    """Test editing when response has no article section."""
    response = "GATE 1: PASS\nGATE 2: PASS\n\nNo article section here"
    agent = EditorAgent(mock_client)

    with patch("agents.editor_agent.call_llm", return_value=response):
        edited, gates_passed, gates_failed = agent.edit(sample_draft)

    # Should return full response when no section marker found
    assert "GATE 1" in edited


def test_validate_opening_multiline():
    """Test opening validation considers first two lines."""
    draft = "Good first line.\nAmidst the chaos, second line starts bad."
    result = validate_opening(draft)
    assert result["valid"] is False


def test_validate_closing_only_last_paragraphs():
    """Test closing validation only checks last paragraphs."""
    draft = """In conclusion, this is early in the article.

Many paragraphs here.
More content.
More content.
More content.
More content.

Companies must adapt. The time is now."""
    result = validate_closing(draft)
    # Should be valid because "In conclusion" is not in last 6 lines
    assert result["valid"] is True


def test_validate_chart_with_multiple_indicators():
    """Test chart validation recognizes various reference phrases."""
    drafts = [
        "![Chart](/chart.png)\nAs the chart shows, data is clear.",
        "![Chart](/chart.png)\nThe chart reveals important trends.",
        "![Chart](/chart.png)\nData shows significant growth.",
        "![Chart](/chart.png)\nIllustrated above, adoption grew.",
    ]

    for draft in drafts:
        result = validate_chart_integration(draft, has_chart=True)
        assert result["valid"] is True, f"Failed for: {draft}"
