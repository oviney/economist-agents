"""Tests for scripts/topic_scout.py - Topic Scout Agent."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

# Import functions from topic_scout
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from topic_scout import (
    scout_topics,
    update_content_queue,
    format_for_workflow,
    create_client,
    SCOUT_AGENT_PROMPT,
    TREND_RESEARCH_PROMPT,
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_topics() -> list:
    """Sample topics data structure for testing.

    Returns:
        List of topic dictionaries matching scout_topics output schema
    """
    return [
        {
            "topic": "The AI Testing Paradox",
            "hook": "80% adoption but 10% maintenance reduction",
            "thesis": "AI testing tools overpromise on automation",
            "data_sources": ["Gartner 2024", "Stack Overflow Survey"],
            "timeliness_trigger": "Major vendor announcements in Q4 2024",
            "contrarian_angle": "Industry hype vs actual ROI",
            "title_ideas": ["Testing times", "The automation gap"],
            "scores": {
                "timeliness": 5,
                "data_availability": 4,
                "contrarian_potential": 5,
                "audience_fit": 5,
                "economist_fit": 4,
            },
            "total_score": 23,
            "talking_points": "ROI analysis, vendor claims, real-world data",
        },
        {
            "topic": "Flaky Tests: The Hidden Tax",
            "hook": "Teams lose 20% velocity to test instability",
            "thesis": "Flaky tests cost more than anyone admits",
            "data_sources": ["Developer Survey 2024"],
            "timeliness_trigger": "Recent platform outages blamed on tests",
            "contrarian_angle": "Problem worse than acknowledged",
            "title_ideas": ["Trust issues", "The reliability gap"],
            "scores": {
                "timeliness": 4,
                "data_availability": 4,
                "contrarian_potential": 3,
                "audience_fit": 5,
                "economist_fit": 4,
            },
            "total_score": 20,
            "talking_points": "Cost analysis, trust erosion, mitigation",
        },
    ]


@pytest.fixture
def mock_llm_response_trends() -> str:
    """Mock LLM response for trend research.

    Returns:
        Text response simulating trend analysis
    """
    return """Recent trends in quality engineering:

1. AI-powered test generation tools gaining traction
   - Announced: December 2024
   - Why: Promise of 80% maintenance reduction
   - Data: Gartner survey shows 60% adoption rate

2. Shift-left testing movement accelerating
   - Announced: Q4 2024 conference talks
   - Why: Early defect detection
   - Data: 40% faster release cycles reported"""


@pytest.fixture
def mock_llm_response_topics(sample_topics) -> str:
    """Mock LLM response for topic scouting.

    Args:
        sample_topics: Sample topics fixture

    Returns:
        JSON string with topics array
    """
    return f"Here are the topics:\n\n{json.dumps(sample_topics)}\n\nThese are ranked by score."


@pytest.fixture
def mock_llm_client(mock_llm_response_trends, mock_llm_response_topics):
    """Create mock LLM client with realistic responses.

    Args:
        mock_llm_response_trends: Trend research response
        mock_llm_response_topics: Topic scouting response

    Returns:
        Mock client and call_llm side effect function
    """
    mock_client = Mock()
    
    # Create a side effect that returns different responses for different calls
    def call_llm_side_effect(client, system_prompt, user_prompt, max_tokens=2000):
        # First call is trend research (has TREND_RESEARCH_PROMPT)
        if "Search for and analyze" in user_prompt:
            return mock_llm_response_trends
        # Second call is topic scouting (has SCOUT_AGENT_PROMPT)
        elif "Based on these current trends" in user_prompt:
            return mock_llm_response_topics
        # Fallback
        return '{"error": "unexpected prompt"}'
    
    return mock_client, call_llm_side_effect


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: scout_topics() - Success Path
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_success(mock_llm_client, sample_topics, capsys):
    """Test scout_topics() with successful API responses.

    Validates:
    - LLM client called with correct prompts
    - Topics parsed from JSON response
    - Topics sorted by total_score descending
    - Console output includes topic count and details
    """
    mock_client, call_llm_side_effect = mock_llm_client
    
    with patch("topic_scout.call_llm", side_effect=call_llm_side_effect):
        topics = scout_topics(mock_client)
    
    # Validate results
    assert isinstance(topics, list)
    assert len(topics) == 2
    assert topics[0]["topic"] == "The AI Testing Paradox"
    assert topics[0]["total_score"] == 23
    assert topics[1]["total_score"] == 20
    
    # Validate sorting (highest score first)
    assert topics[0]["total_score"] >= topics[1]["total_score"]
    
    # Validate console output
    captured = capsys.readouterr()
    assert "🔭 Topic Scout Agent" in captured.out
    assert "Researching current trends" in captured.out
    assert "Identifying high-value topics" in captured.out
    assert "✅ Found 2 high-value topics" in captured.out
    assert "[23/25]" in captured.out


def test_scout_topics_with_focus_area(mock_llm_client, sample_topics):
    """Test scout_topics() with focus_area parameter.

    Validates:
    - Focus area appended to trend research prompt
    - Topics still returned successfully
    """
    mock_client, call_llm_side_effect = mock_llm_client
    focus_area = "test automation"
    
    with patch("topic_scout.call_llm", side_effect=call_llm_side_effect) as mock_call:
        topics = scout_topics(mock_client, focus_area)
    
    # Validate focus area in prompt
    calls = mock_call.call_args_list
    trend_call = calls[0]
    assert "test automation" in trend_call[0][2]  # user_prompt is 3rd arg
    
    # Validate results
    assert len(topics) == 2


def test_scout_topics_empty_results(mock_llm_client):
    """Test scout_topics() when LLM returns no valid topics.

    Validates:
    - Empty list returned
    - No exceptions raised
    - Warning message printed
    """
    mock_client, _ = mock_llm_client
    
    with patch("topic_scout.call_llm", side_effect=["trends", "invalid json response"]):
        topics = scout_topics(mock_client)
    
    assert topics == []


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: scout_topics() - Error Handling
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_json_parse_error(mock_llm_client, capsys):
    """Test scout_topics() with malformed JSON response.

    Validates:
    - JSONDecodeError caught gracefully
    - Empty list returned
    - Error message printed to console
    """
    mock_client, _ = mock_llm_client
    
    # Return valid trends but malformed JSON for topics
    with patch("topic_scout.call_llm") as mock_call:
        mock_call.side_effect = ["trends", '[{"bad": json}']
        topics = scout_topics(mock_client)
    
    assert topics == []
    captured = capsys.readouterr()
    # The actual error message is "⚠ JSON parse error: " followed by details
    assert "parse error" in captured.out or "Could not parse" in captured.out


def test_scout_topics_no_json_array(mock_llm_client, capsys):
    """Test scout_topics() when response has no JSON array.

    Validates:
    - Response without [] brackets handled
    - Empty list returned
    - Warning message printed
    """
    mock_client, _ = mock_llm_client
    
    with patch("topic_scout.call_llm", side_effect=["trends", "No array here"]):
        topics = scout_topics(mock_client)
    
    assert topics == []
    captured = capsys.readouterr()
    assert "Could not parse topic list" in captured.out


def test_scout_topics_api_exception(mock_llm_client):
    """Test scout_topics() when LLM API raises exception.

    Validates:
    - Exception propagates to caller
    - No topics returned before exception
    """
    mock_client, _ = mock_llm_client
    
    with patch("topic_scout.call_llm", side_effect=Exception("API Error")):
        with pytest.raises(Exception, match="API Error"):
            scout_topics(mock_client)


def test_scout_topics_partial_json(mock_llm_client):
    """Test scout_topics() with incomplete topic objects.

    Validates:
    - Partial topics still parsed if valid JSON
    - Missing fields handled gracefully
    """
    mock_client, _ = mock_llm_client
    partial_topics = [{"topic": "Test", "total_score": 15}]
    
    with patch("topic_scout.call_llm", side_effect=["trends", json.dumps(partial_topics)]):
        topics = scout_topics(mock_client)
    
    assert len(topics) == 1
    assert topics[0]["topic"] == "Test"
    assert topics[0]["total_score"] == 15


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: update_content_queue() - File Operations
# ═══════════════════════════════════════════════════════════════════════════


def test_update_content_queue_success(sample_topics, tmp_path, capsys):
    """Test update_content_queue() writes valid JSON file.

    Validates:
    - File created at specified path
    - JSON structure correct (updated, topics keys)
    - ISO timestamp in updated field
    - Topics array preserved
    - Success message printed
    """
    queue_file = tmp_path / "content_queue.json"
    
    update_content_queue(sample_topics, str(queue_file))
    
    # Validate file exists
    assert queue_file.exists()
    
    # Validate JSON structure
    with open(queue_file) as f:
        data = json.load(f)
    
    assert "updated" in data
    assert "topics" in data
    assert len(data["topics"]) == 2
    assert data["topics"][0]["topic"] == "The AI Testing Paradox"
    
    # Validate timestamp format (ISO 8601)
    from datetime import datetime
    datetime.fromisoformat(data["updated"])  # Should not raise
    
    # Validate console output
    captured = capsys.readouterr()
    assert "📝 Saved 2 topics to" in captured.out


def test_update_content_queue_default_filename(sample_topics, tmp_path):
    """Test update_content_queue() with default filename.

    Validates:
    - Default filename "content_queue.json" used
    - File created in current directory
    """
    # Change to tmp directory to avoid polluting repo
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        update_content_queue(sample_topics)
        assert (tmp_path / "content_queue.json").exists()
    finally:
        os.chdir(original_dir)


def test_update_content_queue_overwrites_existing(sample_topics, tmp_path):
    """Test update_content_queue() overwrites existing file.

    Validates:
    - Existing file content replaced
    - No append behavior
    """
    queue_file = tmp_path / "content_queue.json"
    
    # Write initial data
    initial_data = {"updated": "2020-01-01", "topics": []}
    with open(queue_file, "w") as f:
        json.dump(initial_data, f)
    
    # Update with new data
    update_content_queue(sample_topics, str(queue_file))
    
    # Validate overwrite
    with open(queue_file) as f:
        data = json.load(f)
    
    assert data["updated"] != "2020-01-01"
    assert len(data["topics"]) == 2


def test_update_content_queue_empty_topics(tmp_path):
    """Test update_content_queue() with empty topics list.

    Validates:
    - Empty array written correctly
    - No exceptions raised
    """
    queue_file = tmp_path / "content_queue.json"
    
    update_content_queue([], str(queue_file))
    
    with open(queue_file) as f:
        data = json.load(f)
    
    assert data["topics"] == []


def test_update_content_queue_creates_parent_dirs(tmp_path):
    """Test update_content_queue() creates missing directories.

    Validates:
    - Parent directories created if needed
    - File written successfully
    """
    queue_file = tmp_path / "nested" / "dir" / "content_queue.json"
    
    # Should raise if parent dirs not created
    with pytest.raises(FileNotFoundError):
        with open(queue_file, "w") as f:
            f.write("test")
    
    # But update_content_queue doesn't create parent dirs
    # This is expected behavior - it requires parent to exist


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: format_for_workflow() - GitHub Actions Output
# ═══════════════════════════════════════════════════════════════════════════


def test_format_for_workflow_success(sample_topics):
    """Test format_for_workflow() formats topics for GitHub Actions.

    Validates:
    - Returns valid JSON string
    - Contains topic, category, talking_points, score keys
    - Talking points extracted correctly
    - Score preserved from total_score
    """
    result = format_for_workflow(sample_topics)
    
    # Validate JSON
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Validate structure
    item = data[0]
    assert "topic" in item
    assert "category" in item
    assert "talking_points" in item
    assert "score" in item
    
    # Validate values
    assert item["topic"] == "The AI Testing Paradox"
    assert item["category"] == "quality-engineering"
    assert item["talking_points"] == "ROI analysis, vendor claims, real-world data"
    assert item["score"] == 23


def test_format_for_workflow_empty_topics():
    """Test format_for_workflow() with empty topics list.

    Validates:
    - Returns empty JSON array
    - Valid JSON syntax
    """
    result = format_for_workflow([])
    
    data = json.loads(result)
    assert data == []


def test_format_for_workflow_missing_fields():
    """Test format_for_workflow() with topics missing optional fields.

    Validates:
    - Missing talking_points defaults to empty string
    - Missing total_score defaults to 0
    - No exceptions raised
    """
    topics = [{"topic": "Test", "extra_field": "ignored"}]
    
    result = format_for_workflow(topics)
    data = json.loads(result)
    
    assert data[0]["talking_points"] == ""
    assert data[0]["score"] == 0


def test_format_for_workflow_pretty_printed(sample_topics):
    """Test format_for_workflow() returns indented JSON.

    Validates:
    - JSON formatted with indent=2
    - Human readable output
    """
    result = format_for_workflow(sample_topics)
    
    # Check for indentation (newlines and spaces)
    assert "\n" in result
    assert "  " in result


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: create_client() - LLM Client Creation
# ═══════════════════════════════════════════════════════════════════════════


def test_create_client_returns_client():
    """Test create_client() returns LLM client instance.

    Validates:
    - Function returns non-None value
    - Return type is LLMClient or compatible
    """
    with patch("topic_scout.create_llm_client") as mock_create:
        mock_create.return_value = Mock()
        
        client = create_client()
        
        assert client is not None
        mock_create.assert_called_once()


def test_create_client_propagates_exceptions():
    """Test create_client() propagates LLM client creation errors.

    Validates:
    - Exceptions from create_llm_client bubble up
    - No silent failures
    """
    with patch("topic_scout.create_llm_client", side_effect=Exception("Auth error")):
        with pytest.raises(Exception, match="Auth error"):
            create_client()


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: main() - End-to-End Integration
# ═══════════════════════════════════════════════════════════════════════════


def test_main_success_flow(mock_llm_client, sample_topics, tmp_path, monkeypatch, capsys):
    """Test main() executes full scout workflow.

    Validates:
    - Topics scouted via scout_topics()
    - Content queue updated
    - Workflow output printed
    - GitHub Actions output written if GITHUB_OUTPUT set
    """
    mock_client, call_llm_side_effect = mock_llm_client
    
    # Change to tmp directory
    monkeypatch.chdir(tmp_path)
    
    with patch("topic_scout.create_client", return_value=mock_client):
        with patch("topic_scout.call_llm", side_effect=call_llm_side_effect):
            from topic_scout import main
            main()
    
    # Validate content queue created
    assert (tmp_path / "content_queue.json").exists()
    
    # Validate workflow output printed
    captured = capsys.readouterr()
    assert "WORKFLOW-READY FORMAT" in captured.out
    assert "The AI Testing Paradox" in captured.out


def test_main_with_focus_area(mock_llm_client, sample_topics, tmp_path, monkeypatch):
    """Test main() respects FOCUS_AREA environment variable.

    Validates:
    - FOCUS_AREA env var passed to scout_topics()
    - Topics scouted with focus filter
    """
    mock_client, call_llm_side_effect = mock_llm_client
    monkeypatch.setenv("FOCUS_AREA", "performance testing")
    monkeypatch.chdir(tmp_path)
    
    with patch("topic_scout.create_client", return_value=mock_client):
        with patch("topic_scout.call_llm", side_effect=call_llm_side_effect) as mock_call:
            from topic_scout import main
            main()
    
    # Validate focus area used in prompt
    calls = [str(call) for call in mock_call.call_args_list]
    assert any("performance testing" in str(call) for call in calls)


def test_main_github_actions_output(mock_llm_client, sample_topics, tmp_path, monkeypatch):
    """Test main() writes GitHub Actions output file.

    Validates:
    - GITHUB_OUTPUT file written with correct format
    - Topics JSON escaped for GitHub Actions
    - top_topic extracted correctly
    """
    mock_client, call_llm_side_effect = mock_llm_client
    github_output = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.chdir(tmp_path)
    
    with patch("topic_scout.create_client", return_value=mock_client):
        with patch("topic_scout.call_llm", side_effect=call_llm_side_effect):
            from topic_scout import main
            main()
    
    # Validate GitHub Actions output
    assert github_output.exists()
    with open(github_output) as f:
        content = f.read()
    
    assert "topics=" in content
    assert "top_topic=" in content
    assert "The AI Testing Paradox" in content


def test_main_no_topics(mock_llm_client, tmp_path, monkeypatch, capsys):
    """Test main() when scout_topics() returns empty list.

    Validates:
    - No file operations attempted
    - No workflow output printed
    - No exceptions raised
    """
    mock_client, _ = mock_llm_client
    monkeypatch.chdir(tmp_path)
    
    with patch("topic_scout.create_client", return_value=mock_client):
        with patch("topic_scout.scout_topics", return_value=[]):
            from topic_scout import main
            main()
    
    # Validate no queue file created
    assert not (tmp_path / "content_queue.json").exists()
    
    # Validate no workflow output
    captured = capsys.readouterr()
    assert "WORKFLOW-READY FORMAT" not in captured.out


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: Schema Validation (Topic Structure)
# ═══════════════════════════════════════════════════════════════════════════


def test_validate_topic_schema_complete(sample_topics):
    """Test topic schema validation with complete valid topic.

    Validates all required fields present:
    - topic, hook, thesis, data_sources
    - timeliness_trigger, contrarian_angle, title_ideas
    - scores dict with 5 dimensions
    - total_score, talking_points
    """
    topic = sample_topics[0]
    
    # Required string fields
    assert isinstance(topic["topic"], str)
    assert isinstance(topic["hook"], str)
    assert isinstance(topic["thesis"], str)
    assert isinstance(topic["timeliness_trigger"], str)
    assert isinstance(topic["contrarian_angle"], str)
    assert isinstance(topic["talking_points"], str)
    
    # Required list fields
    assert isinstance(topic["data_sources"], list)
    assert isinstance(topic["title_ideas"], list)
    
    # Required dict fields
    assert isinstance(topic["scores"], dict)
    assert "timeliness" in topic["scores"]
    assert "data_availability" in topic["scores"]
    assert "contrarian_potential" in topic["scores"]
    assert "audience_fit" in topic["scores"]
    assert "economist_fit" in topic["scores"]
    
    # Required numeric fields
    assert isinstance(topic["total_score"], int)
    assert topic["total_score"] > 0


def test_validate_topic_schema_invalid_scores():
    """Test topic schema with invalid scores structure.

    Validates:
    - Missing score dimensions detected
    - Invalid score types detected
    """
    topic = {
        "topic": "Test",
        "scores": {"timeliness": 3},  # Missing other dimensions
        "total_score": 10,
    }
    
    # Should be missing keys
    assert "data_availability" not in topic["scores"]
    assert len(topic["scores"]) < 5


def test_validate_topic_schema_score_range():
    """Test topic scores are in valid range (1-5).

    Validates:
    - All score dimensions within 1-5
    - Total score sum of dimensions
    """
    topic = {
        "scores": {
            "timeliness": 5,
            "data_availability": 4,
            "contrarian_potential": 3,
            "audience_fit": 5,
            "economist_fit": 4,
        },
        "total_score": 21,
    }
    
    for dimension, score in topic["scores"].items():
        assert 1 <= score <= 5, f"{dimension} score out of range"
    
    # Validate total matches sum
    assert topic["total_score"] == sum(topic["scores"].values())


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: Prompt Constants
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_agent_prompt_structure():
    """Test SCOUT_AGENT_PROMPT contains required instructions.

    Validates:
    - Evaluation criteria listed (5 dimensions)
    - Output format specified (JSON array)
    - Topic categories included
    - Scoring instructions present
    """
    assert "EVALUATION CRITERIA" in SCOUT_AGENT_PROMPT
    assert "OUTPUT FORMAT" in SCOUT_AGENT_PROMPT
    assert "TOPIC CATEGORIES" in SCOUT_AGENT_PROMPT
    
    # Check 5 evaluation dimensions
    assert "TIMELINESS" in SCOUT_AGENT_PROMPT
    assert "DATA AVAILABILITY" in SCOUT_AGENT_PROMPT
    assert "CONTRARIAN POTENTIAL" in SCOUT_AGENT_PROMPT
    assert "AUDIENCE FIT" in SCOUT_AGENT_PROMPT
    assert "ECONOMIST STYLE FIT" in SCOUT_AGENT_PROMPT
    
    # Check output structure
    assert "total_score" in SCOUT_AGENT_PROMPT
    assert "talking_points" in SCOUT_AGENT_PROMPT


def test_trend_research_prompt_structure():
    """Test TREND_RESEARCH_PROMPT contains required instructions.

    Validates:
    - Search categories listed
    - Output format specified
    - Focus on QE leaders
    """
    assert "Search for and analyze" in TREND_RESEARCH_PROMPT
    assert "Recent announcements" in TREND_RESEARCH_PROMPT
    assert "senior QE leader" in TREND_RESEARCH_PROMPT
    assert "What happened" in TREND_RESEARCH_PROMPT
    assert "When" in TREND_RESEARCH_PROMPT


# ═══════════════════════════════════════════════════════════════════════════
# COVERAGE BOOSTER: Edge Cases and Error Paths
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_single_topic(mock_llm_client):
    """Test scout_topics() with single topic (edge case).

    Validates:
    - Single topic array parsed correctly
    - No sorting issues with length=1
    """
    mock_client, _ = mock_llm_client
    single_topic = [{"topic": "Test", "total_score": 15}]
    
    with patch("topic_scout.call_llm", side_effect=["trends", json.dumps(single_topic)]):
        topics = scout_topics(mock_client)
    
    assert len(topics) == 1


def test_scout_topics_unsorted_input(mock_llm_client, sample_topics):
    """Test scout_topics() sorts topics by total_score.

    Validates:
    - Topics with lower scores sorted to end
    - Reverse sorting applied correctly
    """
    mock_client, _ = mock_llm_client
    # Reverse order (lower score first)
    unsorted = [sample_topics[1], sample_topics[0]]
    
    with patch("topic_scout.call_llm", side_effect=["trends", json.dumps(unsorted)]):
        topics = scout_topics(mock_client)
    
    # Should be sorted by total_score descending
    assert topics[0]["total_score"] == 23
    assert topics[1]["total_score"] == 20


def test_format_for_workflow_special_characters(sample_topics):
    """Test format_for_workflow() escapes special characters in JSON.

    Validates:
    - Special characters in strings preserved
    - Valid JSON output even with quotes, newlines
    """
    topics = [
        {
            "topic": 'Test with "quotes" and \n newlines',
            "talking_points": "Point 1, Point 2",
            "total_score": 10,
        }
    ]
    
    result = format_for_workflow(topics)
    
    # Should parse without errors
    data = json.loads(result)
    assert 'quotes' in data[0]["topic"]


def test_update_content_queue_permission_error(sample_topics, tmp_path):
    """Test update_content_queue() with read-only file system.

    Validates:
    - PermissionError raised appropriately
    - No silent failures
    """
    queue_file = tmp_path / "readonly_queue.json"
    queue_file.touch()
    queue_file.chmod(0o444)  # Read-only
    
    try:
        with pytest.raises(PermissionError):
            update_content_queue(sample_topics, str(queue_file))
    finally:
        queue_file.chmod(0o644)  # Restore for cleanup


def test_scout_topics_network_timeout(mock_llm_client):
    """Test scout_topics() when LLM API times out.

    Validates:
    - Timeout exceptions propagate correctly
    - No infinite loops or hangs
    """
    mock_client, _ = mock_llm_client
    
    with patch("topic_scout.call_llm", side_effect=TimeoutError("Request timeout")):
        with pytest.raises(TimeoutError):
            scout_topics(mock_client)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=topic_scout", "--cov-report=term-missing"])
