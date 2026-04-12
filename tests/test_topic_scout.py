"""Tests for scripts/topic_scout.py - Topic Scout Agent."""

import json
import os

# Import functions from topic_scout
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from topic_scout import (
    SCOUT_AGENT_PROMPT,
    THEME_KEYWORDS,
    TREND_RESEARCH_PROMPT,
    check_topic_diversity,
    classify_topic_theme,
    create_client,
    format_for_workflow,
    scout_topics,
    update_content_queue,
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
def mock_dedup_passthrough():
    """Mock TopicDeduplicator that passes all topics through.

    Simulates a non-empty published_articles archive (count=19) and
    returns the input topics unchanged from filter_topics(). Use this
    in tests that don't care about dedup logic — it satisfies the
    fail-closed check added for issue #237 without rejecting anything.
    """
    with patch("topic_scout.TopicDeduplicator") as MockDedup:
        instance = MockDedup.return_value
        instance.collection = Mock()
        instance.collection.count = Mock(return_value=19)
        instance.filter_topics = Mock(side_effect=lambda topics: (topics, []))
        yield instance


@pytest.fixture
def mock_llm_client(mock_llm_response_trends, mock_llm_response_topics):
    """Create mock LLM client with realistic responses.

    Args:
        mock_llm_response_trends: Trend research response (unused after grounding)
        mock_llm_response_topics: Topic scouting response

    Returns:
        Mock client and call_llm side effect function
    """
    mock_client = Mock()

    # call_llm is now only used for the topic-scouting step (and optional
    # diversity retry).  Trend research is handled by
    # build_grounded_trend_context().
    def call_llm_side_effect(client, system_prompt, user_prompt, max_tokens=2000):
        # Topic scouting: detect by the SCOUT_AGENT_PROMPT marker
        # "YOUR MISSION" which is unique to that prompt and stable
        # across structural changes.
        if "YOUR MISSION" in user_prompt:
            return mock_llm_response_topics
        # Fallback
        return '{"error": "unexpected prompt"}'

    return mock_client, call_llm_side_effect


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: scout_topics() - Success Path
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_success(
    mock_llm_client, mock_dedup_passthrough, sample_topics, capsys
):
    """Test scout_topics() with successful API responses.

    Validates:
    - LLM client called with correct prompts
    - Topics parsed from JSON response
    - Topics sorted by total_score descending
    - Console output includes topic count and details
    """
    mock_client, call_llm_side_effect = mock_llm_client

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
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


def test_scout_topics_with_focus_area(
    mock_llm_client, mock_dedup_passthrough, sample_topics
):
    """Test scout_topics() with focus_area parameter.

    Validates:
    - Focus area passed to build_grounded_trend_context
    - Topics still returned successfully
    """
    mock_client, call_llm_side_effect = mock_llm_client
    focus_area = "test automation"

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends") as mock_ground,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        topics = scout_topics(mock_client, focus_area)

    # Validate focus area passed to grounding module
    mock_ground.assert_called_once_with(focus_area=focus_area)

    # Validate results
    assert len(topics) == 2


def test_scout_topics_empty_results(mock_llm_client, mock_dedup_passthrough):
    """Test scout_topics() when LLM returns no valid topics.

    Validates:
    - Empty list returned
    - No exceptions raised
    - Warning message printed
    """
    mock_client, _ = mock_llm_client

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=["invalid json response"]),
    ):
        topics = scout_topics(mock_client)

    assert topics == []


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: scout_topics() - Error Handling
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_json_parse_error(mock_llm_client, mock_dedup_passthrough, capsys):
    """Test scout_topics() with malformed JSON response.

    Validates:
    - JSONDecodeError caught gracefully
    - Empty list returned
    - Error message printed to console
    """
    mock_client, _ = mock_llm_client

    # Return valid trends but malformed JSON for topics
    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm") as mock_call,
    ):
        mock_call.side_effect = ['[{"bad": json}']
        topics = scout_topics(mock_client)

    assert topics == []
    captured = capsys.readouterr()
    # The actual error message is "⚠ JSON parse error: " followed by details
    assert "parse error" in captured.out or "Could not parse" in captured.out


def test_scout_topics_no_json_array(mock_llm_client, mock_dedup_passthrough, capsys):
    """Test scout_topics() when response has no JSON array.

    Validates:
    - Response without [] brackets handled
    - Empty list returned
    - Warning message printed
    """
    mock_client, _ = mock_llm_client

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=["No array here"]),
    ):
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

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=Exception("API Error")),
        pytest.raises(Exception, match="API Error"),
    ):
        scout_topics(mock_client)


def test_scout_topics_partial_json(mock_llm_client, mock_dedup_passthrough):
    """Test scout_topics() with incomplete topic objects.

    Validates:
    - Partial topics still parsed if valid JSON
    - Missing fields handled gracefully
    """
    mock_client, _ = mock_llm_client
    partial_topics = [{"topic": "Test", "total_score": 15}]

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch(
            "topic_scout.call_llm", side_effect=[json.dumps(partial_topics)]
        ),
    ):
        topics = scout_topics(mock_client)

    assert len(topics) == 1
    assert topics[0]["topic"] == "Test"
    assert topics[0]["total_score"] == 15


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: Issue #237 — Dedup bypass regression guard
#
# These tests pin the behavior added to scout_topics() to fix the dedup
# bypass bug: topic_scout must run TopicDeduplicator.filter_topics() against
# the published_articles archive AND fail-closed when that archive is
# unavailable or empty (with an explicit allow_empty_archive opt-out for
# bootstrap runs). See issue #237.
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_runs_filter_topics(mock_llm_client, mock_dedup_passthrough):
    """scout_topics() must call TopicDeduplicator.filter_topics() on every run."""
    mock_client, call_llm_side_effect = mock_llm_client

    with patch("topic_scout.call_llm", side_effect=call_llm_side_effect):
        scout_topics(mock_client)

    assert mock_dedup_passthrough.filter_topics.called, (
        "scout_topics() must invoke TopicDeduplicator.filter_topics() — "
        "skipping dedup lets near-duplicate topics reach the pipeline."
    )


def test_scout_topics_drops_rejected_duplicates(mock_llm_client, sample_topics):
    """Topics rejected by filter_topics() must not appear in the returned list."""
    mock_client, call_llm_side_effect = mock_llm_client

    # Mock dedup to reject the first topic and keep the second.
    with (
        patch("topic_scout.TopicDeduplicator") as MockDedup,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        instance = MockDedup.return_value
        instance.collection = Mock()
        instance.collection.count = Mock(return_value=19)
        instance.filter_topics = Mock(
            side_effect=lambda topics: (
                [t for t in topics if t["topic"] != "The AI Testing Paradox"],
                [t for t in topics if t["topic"] == "The AI Testing Paradox"],
            )
        )
        topics = scout_topics(mock_client)

    returned_titles = {t["topic"] for t in topics}
    assert "The AI Testing Paradox" not in returned_titles
    assert "Flaky Tests: The Hidden Tax" in returned_titles


def test_scout_topics_fail_closed_when_collection_missing(mock_llm_client):
    """Missing ChromaDB collection must raise RuntimeError by default."""
    mock_client, call_llm_side_effect = mock_llm_client

    with (
        patch("topic_scout.TopicDeduplicator") as MockDedup,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        instance = MockDedup.return_value
        instance.collection = None  # ChromaDB unavailable
        with pytest.raises(RuntimeError, match="archive unavailable or empty"):
            scout_topics(mock_client)


def test_scout_topics_fail_closed_when_collection_empty(mock_llm_client):
    """Empty published_articles collection must raise RuntimeError by default."""
    mock_client, call_llm_side_effect = mock_llm_client

    with (
        patch("topic_scout.TopicDeduplicator") as MockDedup,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        instance = MockDedup.return_value
        instance.collection = Mock()
        instance.collection.count = Mock(return_value=0)
        with pytest.raises(RuntimeError, match="archive unavailable or empty"):
            scout_topics(mock_client)


def test_scout_topics_allow_empty_archive_override(mock_llm_client, sample_topics):
    """allow_empty_archive=True must downgrade empty archive to a warning and proceed."""
    mock_client, call_llm_side_effect = mock_llm_client

    with (
        patch("topic_scout.TopicDeduplicator") as MockDedup,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        instance = MockDedup.return_value
        instance.collection = Mock()
        instance.collection.count = Mock(return_value=0)
        instance.filter_topics = Mock(side_effect=lambda topics: (topics, []))
        topics = scout_topics(mock_client, allow_empty_archive=True)

    assert len(topics) == 2  # sample_topics pass through untouched


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
    with pytest.raises(FileNotFoundError), open(queue_file, "w") as f:
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
    with (
        patch("topic_scout.create_llm_client", side_effect=Exception("Auth error")),
        pytest.raises(Exception, match="Auth error"),
    ):
        create_client()


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: main() - End-to-End Integration
# ═══════════════════════════════════════════════════════════════════════════


def test_main_success_flow(
    mock_llm_client,
    mock_dedup_passthrough,
    sample_topics,
    tmp_path,
    monkeypatch,
    capsys,
):
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

    with (
        patch("topic_scout.create_client", return_value=mock_client),
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        from topic_scout import main

        main()

    # Validate content queue created
    assert (tmp_path / "content_queue.json").exists()

    # Validate workflow output printed
    captured = capsys.readouterr()
    assert "WORKFLOW-READY FORMAT" in captured.out
    assert "The AI Testing Paradox" in captured.out


def test_main_with_focus_area(
    mock_llm_client, mock_dedup_passthrough, sample_topics, tmp_path, monkeypatch
):
    """Test main() respects FOCUS_AREA environment variable.

    Validates:
    - FOCUS_AREA env var passed to scout_topics()
    - Topics scouted with focus filter
    """
    mock_client, call_llm_side_effect = mock_llm_client
    monkeypatch.setenv("FOCUS_AREA", "performance testing")
    monkeypatch.chdir(tmp_path)

    with (
        patch("topic_scout.create_client", return_value=mock_client),
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends") as mock_ground,
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        from topic_scout import main

        main()

    # Validate focus area passed to grounding module
    mock_ground.assert_called_once_with(focus_area="performance testing")


def test_main_github_actions_output(
    mock_llm_client, mock_dedup_passthrough, sample_topics, tmp_path, monkeypatch
):
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

    with (
        patch("topic_scout.create_client", return_value=mock_client),
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
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

    with (
        patch("topic_scout.create_client", return_value=mock_client),
        patch("topic_scout.scout_topics", return_value=[]),
    ):
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
    assert "major testing tool vendors" in TREND_RESEARCH_PROMPT
    assert "senior QE leader" in TREND_RESEARCH_PROMPT
    assert "What happened" in TREND_RESEARCH_PROMPT
    assert "When" in TREND_RESEARCH_PROMPT


# ═══════════════════════════════════════════════════════════════════════════
# COVERAGE BOOSTER: Edge Cases and Error Paths
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_topics_single_topic(mock_llm_client, mock_dedup_passthrough):
    """Test scout_topics() with single topic (edge case).

    Validates:
    - Single topic array parsed correctly
    - No sorting issues with length=1
    """
    mock_client, _ = mock_llm_client
    single_topic = [{"topic": "Test", "total_score": 15}]

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch(
            "topic_scout.call_llm", side_effect=[json.dumps(single_topic)]
        ),
    ):
        topics = scout_topics(mock_client)

    assert len(topics) == 1


def test_scout_topics_unsorted_input(
    mock_llm_client, mock_dedup_passthrough, sample_topics
):
    """Test scout_topics() sorts topics by total_score.

    Validates:
    - Topics with lower scores sorted to end
    - Reverse sorting applied correctly
    """
    mock_client, _ = mock_llm_client
    # Reverse order (lower score first)
    unsorted = [sample_topics[1], sample_topics[0]]

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=[json.dumps(unsorted)]),
    ):
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
    assert "quotes" in data[0]["topic"]


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

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=TimeoutError("Request timeout")),
        pytest.raises(TimeoutError),
    ):
        scout_topics(mock_client)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: ADR-0007 Feedback Loop — Performance Context Injection (Story #179)
# ═══════════════════════════════════════════════════════════════════════════


def test_performance_context_injected_into_scout_prompt(
    mock_llm_client, mock_dedup_passthrough, monkeypatch
):
    """Performance context from content_intelligence must appear in the scout prompt.

    This is the central integration test for Story #179: the feedback
    loop from ADR-0007. If this test fails, the whole "agent fleet is
    learning from audience data" claim is broken.
    """
    mock_client, call_llm_side_effect = mock_llm_client
    fake_context = (
        "## Performance Context\n\n"
        "Over the last 30 days, the blog served **50,000 pageviews**.\n\n"
        "### Top performers (build on what's working)\n"
        "| Score | Pageviews | Title |\n"
        "|-------|-----------|-------|\n"
        "| 0.500 | 1000 | Fake Top Article |\n"
    )
    monkeypatch.setattr(
        "topic_scout.get_performance_context", lambda **kwargs: fake_context
    )

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect) as mock_call,
    ):
        scout_topics(mock_client)

    # First LLM call is the scout prompt (trends are now grounded)
    scout_call = mock_call.call_args_list[0]
    scout_prompt = scout_call[0][2]  # user_prompt is the 3rd positional arg
    assert "Performance Context" in scout_prompt
    assert "Fake Top Article" in scout_prompt
    assert "50,000 pageviews" in scout_prompt
    assert "Top performers" in scout_prompt


def test_performance_context_fallback_when_db_missing(
    mock_llm_client, mock_dedup_passthrough, monkeypatch
):
    """When content_intelligence reports no data, scout must still run.

    Graceful degradation is an acceptance criterion for Story #179:
    the feedback loop should be a signal source, not a blocker.
    """
    mock_client, call_llm_side_effect = mock_llm_client
    fallback = (
        "## Performance Context\n\n"
        "_No performance data available yet. Run `scripts/ga4_etl.py` "
        "to populate `data/performance.db`._\n"
    )
    monkeypatch.setattr(
        "topic_scout.get_performance_context", lambda **kwargs: fallback
    )

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        topics = scout_topics(mock_client)

    # Scout should still succeed with the fallback context
    assert len(topics) == 2


def test_scout_prompt_explicitly_references_performance_data(
    mock_llm_client, mock_dedup_passthrough, monkeypatch
):
    """The scout prompt must tell the LLM to *use* the performance data.

    Injecting the data without instructions means the LLM may ignore
    it. The SCOUT_AGENT_PROMPT must instruct the LLM to favour topics
    similar to top performers and reframe underperformers.
    """
    mock_client, call_llm_side_effect = mock_llm_client
    monkeypatch.setattr(
        "topic_scout.get_performance_context",
        lambda **kwargs: "## Performance Context\n\nfake data\n",
    )

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect) as mock_call,
    ):
        scout_topics(mock_client)

    scout_prompt = mock_call.call_args_list[0][0][2]
    # The prompt must explicitly reference the performance context
    assert "TOP PERFORMERS" in scout_prompt or "top performers" in scout_prompt.lower()
    assert "UNDERPERFORMERS" in scout_prompt or "underperformer" in scout_prompt.lower()


def test_get_performance_context_called_once_per_scout_run(
    mock_llm_client, mock_dedup_passthrough, monkeypatch
):
    """Verify the feedback loop query happens exactly once per scout invocation."""
    mock_client, call_llm_side_effect = mock_llm_client
    call_count = {"n": 0}

    def counting_fake(**kwargs):
        call_count["n"] += 1
        return "## Performance Context\n\nfake\n"

    monkeypatch.setattr("topic_scout.get_performance_context", counting_fake)

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=call_llm_side_effect),
    ):
        scout_topics(mock_client)

    assert call_count["n"] == 1, f"expected 1 call, got {call_count['n']}"


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: classify_topic_theme() — Theme Classification
# ═══════════════════════════════════════════════════════════════════════════


def test_classify_topic_theme_uses_theme_field():
    """Honour the LLM-supplied 'theme' field when present."""
    topic = {"topic": "Some AI story", "theme": "security"}
    assert classify_topic_theme(topic) == "security"


def test_classify_topic_theme_normalises_theme_field():
    """LLM theme field is lower-cased and stripped."""
    topic = {"topic": "Observability tale", "theme": "  Observability  "}
    assert classify_topic_theme(topic) == "observability"


def test_classify_topic_theme_security():
    """Topics mentioning security keywords map to 'security'."""
    topic = {
        "topic": "DAST vs SAST: the hidden cost of shifting left too far",
        "hook": "DevSecOps teams spend more on OWASP tooling than on fixes",
        "thesis": "Automated vulnerability scanning creates false confidence",
        "contrarian_angle": "More scanners = more noise, not less risk",
        "talking_points": "CVE triage overhead, supply-chain security, SAST false positives",
    }
    assert classify_topic_theme(topic) == "security"


def test_classify_topic_theme_devops():
    """Topics mentioning DevOps/CI-CD keywords map to 'devops'."""
    topic = {
        "topic": "GitOps is eating Kubernetes deployments",
        "hook": "80% of teams report pipeline confusion with GitOps",
        "thesis": "CI/CD pipelines are now the bottleneck, not the code",
        "contrarian_angle": "Continuous delivery promised speed; it delivered debt",
        "talking_points": "release engineering, deployment frequency, rollback culture",
    }
    assert classify_topic_theme(topic) == "devops"


def test_classify_topic_theme_platform_engineering():
    """Topics mentioning platform engineering keywords map to 'platform_engineering'."""
    topic = {
        "topic": "Backstage and the illusion of the internal developer platform",
        "hook": "Teams spend 18 months building an IDP that 3 people use",
        "thesis": "Internal developer platforms solve org problems, not tech ones",
        "contrarian_angle": "Paved paths become paved cages",
        "talking_points": "developer portal adoption, golden path maintenance, IDP ROI",
    }
    assert classify_topic_theme(topic) == "platform_engineering"


def test_classify_topic_theme_observability():
    """Topics mentioning observability keywords map to 'observability'."""
    topic = {
        "topic": "OpenTelemetry: the standard nobody implements correctly",
        "hook": "Distributed tracing adoption is up 60% but alert noise is up 200%",
        "thesis": "SLOs without SLAs are just expensive dashboards",
        "contrarian_angle": "More metrics, less understanding",
        "talking_points": "OpenTelemetry, distributed tracing, alerting fatigue, SLO budgets",
    }
    assert classify_topic_theme(topic) == "observability"


def test_classify_topic_theme_developer_experience():
    """Topics mentioning developer experience keywords map to 'developer_experience'."""
    topic = {
        "topic": "Developer experience surveys: the metric engineering leaders ignore",
        "hook": "SPACE framework adoption is up, but cognitive load is too",
        "thesis": "Measuring DX without acting on it makes things worse",
        "contrarian_angle": "More developer productivity tools increase inner-loop complexity",
        "talking_points": "developer experience, DevEx scores, onboarding time, cognitive load",
    }
    assert classify_topic_theme(topic) == "developer_experience"


def test_classify_topic_theme_software_architecture():
    """Topics mentioning architecture keywords map to 'software_architecture'."""
    topic = {
        "topic": "Microservices migration: the technical debt that keeps giving",
        "hook": "60% of teams regret their monolith-to-microservices migration",
        "thesis": "Domain-driven design solves organisational problems, not scaling ones",
        "contrarian_angle": "Refactoring a monolith is usually the better investment",
        "talking_points": "software architecture, technical debt, design patterns, modular monolith",
    }
    assert classify_topic_theme(topic) == "software_architecture"


def test_classify_topic_theme_fallback_to_other():
    """Topics with no matching keywords return 'other'."""
    topic = {
        "topic": "Random unrelated topic",
        "hook": "Something happened",
        "thesis": "Things are different",
        "contrarian_angle": "Nothing matches",
        "talking_points": "completely unrelated words here",
    }
    assert classify_topic_theme(topic) == "other"


def test_classify_topic_theme_no_theme_field_uses_keywords():
    """Without a 'theme' field, keyword matching is the fallback."""
    topic = {
        "topic": "Kubernetes deployments and GitOps pipelines",
        "hook": "CI/CD complexity grows with team size",
        "thesis": "Continuous delivery is overengineered for most teams",
        "contrarian_angle": "Simpler release engineering beats fancy pipelines",
        "talking_points": "devops, pipeline optimisation, release frequency",
    }
    assert classify_topic_theme(topic) == "devops"


def test_classify_topic_theme_empty_topic():
    """An empty topic dict returns 'other' without raising."""
    assert classify_topic_theme({}) == "other"


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: check_topic_diversity() — Diversity Enforcement
# ═══════════════════════════════════════════════════════════════════════════


def test_check_topic_diversity_empty_list():
    """Empty topic list is considered diverse (no violation possible)."""
    is_diverse, dominant = check_topic_diversity([])
    assert is_diverse is True
    assert dominant == ""


def test_check_topic_diversity_single_topic():
    """Single topic: check_topic_diversity reports the raw 100% ratio (is_diverse=False)."""
    topics = [{"topic": "AI test generation", "theme": "ai_testing"}]
    is_diverse, dominant = check_topic_diversity(topics)
    # 1/1 = 100% > 40% → raw function returns False.
    # The 3-topic guard in scout_topics prevents regeneration for tiny lists.
    assert is_diverse is False
    assert dominant == "ai_testing"


def test_check_topic_diversity_passes_with_diverse_topics():
    """Five topics across 4+ themes should pass the 40% threshold."""
    topics = [
        {"topic": "AI test generators", "theme": "ai_testing"},
        {"topic": "OWASP supply chain risks", "theme": "security"},
        {"topic": "OpenTelemetry adoption", "theme": "observability"},
        {"topic": "Platform engineering ROI", "theme": "platform_engineering"},
        {"topic": "GitOps and deployment complexity", "theme": "devops"},
    ]
    is_diverse, dominant = check_topic_diversity(topics)
    assert is_diverse is True


def test_check_topic_diversity_fails_when_theme_exceeds_40_percent():
    """Three AI-testing topics in five total (60%) triggers the diversity alarm."""
    topics = [
        {"topic": "AI test generation", "theme": "ai_testing"},
        {"topic": "LLM-based visual testing", "theme": "ai_testing"},
        {"topic": "Copilot for test maintenance", "theme": "ai_testing"},
        {"topic": "OWASP supply chain risks", "theme": "security"},
        {"topic": "OpenTelemetry adoption", "theme": "observability"},
    ]
    is_diverse, dominant = check_topic_diversity(topics)
    assert is_diverse is False
    assert dominant == "ai_testing"


def test_check_topic_diversity_exactly_at_40_percent_passes():
    """Exactly 40% (2/5) of a single theme is NOT a violation (threshold is strict >40%)."""
    topics = [
        {"topic": "AI test generation", "theme": "ai_testing"},
        {"topic": "Copilot for tests", "theme": "ai_testing"},
        {"topic": "OWASP supply chain risks", "theme": "security"},
        {"topic": "OpenTelemetry adoption", "theme": "observability"},
        {"topic": "GitOps and pipelines", "theme": "devops"},
    ]
    is_diverse, dominant = check_topic_diversity(topics)
    assert is_diverse is True


def test_check_topic_diversity_returns_correct_dominant_theme():
    """The dominant theme returned matches the most frequent one."""
    topics = [
        {"topic": "Security topic 1", "theme": "security"},
        {"topic": "Security topic 2", "theme": "security"},
        {"topic": "Security topic 3", "theme": "security"},
        {"topic": "AI testing", "theme": "ai_testing"},
        {"topic": "DevOps thing", "theme": "devops"},
    ]
    is_diverse, dominant = check_topic_diversity(topics)
    assert is_diverse is False
    assert dominant == "security"


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: scout_topics() — Diversity-Triggered Regeneration
# ═══════════════════════════════════════════════════════════════════════════


def _make_topics_with_theme(theme: str, count: int, start_score: int = 20) -> list:
    """Build minimal topic dicts all sharing the same theme."""
    return [
        {
            "topic": f"{theme.title()} topic {i}",
            "theme": theme,
            "hook": f"Hook {i}",
            "thesis": f"Thesis {i}",
            "data_sources": [],
            "timeliness_trigger": "Now",
            "contrarian_angle": "Contrarian",
            "title_ideas": [],
            "scores": {
                "timeliness": 4,
                "data_availability": 4,
                "contrarian_potential": 4,
                "audience_fit": 4,
                "economist_fit": 4,
            },
            "total_score": start_score - i,
            "talking_points": f"point {i}",
        }
        for i in range(count)
    ]


def test_scout_topics_diversity_check_triggers_regeneration(
    mock_dedup_passthrough, capsys
):
    """When initial topics fail diversity, a 2nd LLM call is made with a diversity hint."""
    mock_client = Mock()

    # First batch: 3 AI-testing + 1 security + 1 observability (3/5 = 60% > 40%)
    non_diverse_topics = (
        _make_topics_with_theme("ai_testing", 3, start_score=24)
        + _make_topics_with_theme("security", 1, start_score=20)
        + _make_topics_with_theme("observability", 1, start_score=18)
    )
    # Second batch (after diversity hint): properly diverse
    diverse_topics = (
        _make_topics_with_theme("ai_testing", 1, start_score=22)
        + _make_topics_with_theme("security", 1, start_score=21)
        + _make_topics_with_theme("observability", 1, start_score=20)
        + _make_topics_with_theme("devops", 1, start_score=19)
        + _make_topics_with_theme("platform_engineering", 1, start_score=18)
    )

    call_responses = iter(
        [
            json.dumps(non_diverse_topics),
            json.dumps(diverse_topics),
        ]
    )

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch("topic_scout.call_llm", side_effect=lambda *a, **kw: next(call_responses)) as mock_call,
    ):
        topics = scout_topics(mock_client)

    # Two LLM calls: initial topics + regeneration (trends are grounded)
    assert mock_call.call_count == 2

    # Diversity hint was injected in the 2nd call
    regen_prompt = mock_call.call_args_list[1][0][2]
    assert "DIVERSITY ALERT" in regen_prompt
    assert "ai_testing" in regen_prompt

    # Final output is the diverse set
    assert len(topics) == 5

    captured = capsys.readouterr()
    assert "Diversity check failed" in captured.out


def test_scout_topics_diversity_check_skipped_for_two_topics(mock_dedup_passthrough):
    """Diversity check is not applied when fewer than 3 topics are returned."""
    mock_client = Mock()
    # Both topics share the same theme — normally a violation, but too few to check
    two_same_theme = _make_topics_with_theme("ai_testing", 2, start_score=20)

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch(
            "topic_scout.call_llm",
            side_effect=[json.dumps(two_same_theme)],
        ) as mock_call,
    ):
        topics = scout_topics(mock_client)

    # Only 1 LLM call — no regeneration triggered (trends are grounded)
    assert mock_call.call_count == 1
    assert len(topics) == 2


def test_scout_topics_diversity_passes_no_extra_call(mock_dedup_passthrough):
    """When topics are diverse from the first try, no regeneration call is made."""
    mock_client = Mock()
    diverse = (
        _make_topics_with_theme("ai_testing", 1, start_score=22)
        + _make_topics_with_theme("security", 1, start_score=21)
        + _make_topics_with_theme("observability", 1, start_score=20)
        + _make_topics_with_theme("devops", 1, start_score=19)
        + _make_topics_with_theme("platform_engineering", 1, start_score=18)
    )

    with (
        patch("topic_scout.build_grounded_trend_context", return_value="grounded trends"),
        patch(
            "topic_scout.call_llm",
            side_effect=[json.dumps(diverse)],
        ) as mock_call,
    ):
        topics = scout_topics(mock_client)

    # Exactly 1 LLM call — no regeneration (trends are grounded)
    assert mock_call.call_count == 1
    assert len(topics) == 5


# ═══════════════════════════════════════════════════════════════════════════
# TESTS: SCOUT_AGENT_PROMPT — Expanded Focus Areas
# ═══════════════════════════════════════════════════════════════════════════


def test_scout_prompt_includes_security_category():
    """Security must be in the topic categories to monitor."""
    assert "Security" in SCOUT_AGENT_PROMPT or "security" in SCOUT_AGENT_PROMPT.lower()


def test_scout_prompt_includes_devops_category():
    """DevOps must be in the topic categories to monitor."""
    assert "DevOps" in SCOUT_AGENT_PROMPT or "devops" in SCOUT_AGENT_PROMPT.lower()


def test_scout_prompt_includes_platform_engineering_category():
    """Platform Engineering must be in the topic categories to monitor."""
    assert (
        "Platform Engineering" in SCOUT_AGENT_PROMPT
        or "platform engineering" in SCOUT_AGENT_PROMPT.lower()
    )


def test_scout_prompt_includes_observability_category():
    """Observability must be in the topic categories to monitor."""
    assert (
        "Observability" in SCOUT_AGENT_PROMPT
        or "observability" in SCOUT_AGENT_PROMPT.lower()
    )


def test_scout_prompt_includes_developer_experience_category():
    """Developer Experience must be in the topic categories to monitor."""
    assert (
        "Developer Experience" in SCOUT_AGENT_PROMPT
        or "developer experience" in SCOUT_AGENT_PROMPT.lower()
    )


def test_scout_prompt_includes_software_architecture_category():
    """Software Architecture must be in the topic categories to monitor."""
    assert (
        "Software Architecture" in SCOUT_AGENT_PROMPT
        or "software architecture" in SCOUT_AGENT_PROMPT.lower()
    )


def test_scout_prompt_includes_diversity_requirement():
    """The scout prompt must instruct the LLM to spread topics across categories."""
    assert (
        "DIVERSITY" in SCOUT_AGENT_PROMPT or "diversity" in SCOUT_AGENT_PROMPT.lower()
    )


def test_theme_keywords_covers_all_required_themes():
    """THEME_KEYWORDS must include entries for all 6 required new categories."""
    required_themes = {
        "security",
        "devops",
        "platform_engineering",
        "observability",
        "developer_experience",
        "software_architecture",
    }
    assert required_themes.issubset(THEME_KEYWORDS.keys())


def test_trend_prompt_covers_broader_landscape():
    """Trend research prompt must reference each key area of the expanded landscape."""
    required_keywords = ["Security", "Platform", "Observability", "Developer"]
    for keyword in required_keywords:
        assert keyword.lower() in TREND_RESEARCH_PROMPT.lower(), (
            f"TREND_RESEARCH_PROMPT is missing '{keyword}'"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=topic_scout", "--cov-report=term-missing"])
