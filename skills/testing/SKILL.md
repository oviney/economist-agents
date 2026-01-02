# Testing Skill for Economist-Agents

## Overview
This skill defines testing patterns for the economist-agents multi-agent AI system. Focus on mocking API calls, testing agent workflows, and achieving >80% code coverage.

## Testing Philosophy

**All agent code must be testable:**
- Mock all external API calls (OpenAI, Anthropic)
- Test both success and failure paths
- Validate agent outputs against schemas
- Ensure governance workflows are tested
- Achieve minimum 80% code coverage

## Testing Framework

**Use pytest with these plugins:**
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `unittest.mock` - Python standard library mocking

## Test Structure

**Follow Arrange-Act-Assert pattern:**

```python
def test_function_name():
    # Arrange - Set up test data and mocks
    mock_client = Mock()
    expected_result = {"key": "value"}
    
    # Act - Call the function being tested
    result = function_under_test(mock_client)
    
    # Assert - Verify the results
    assert result == expected_result
```

## Mocking API Calls

### Mocking OpenAI API

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('openai.OpenAI') as mock:
        mock_instance = Mock()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"result": "success"}'))
        ]
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response.model = "gpt-4o"
        
        mock_instance.chat.completions.create.return_value = mock_response
        mock.return_value = mock_instance
        
        yield mock_instance

def test_with_openai_mock(mock_openai_client):
    """Test function that calls OpenAI."""
    result = my_function(mock_openai_client)
    assert "result" in result
```

### Mocking Anthropic API

```python
@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    with patch('anthropic.Anthropic') as mock:
        mock_instance = Mock()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.content = [
            Mock(text='{"result": "success"}')
        ]
        mock_response.usage = Mock(
            input_tokens=100,
            output_tokens=50
        )
        mock_response.model = "claude-sonnet-4-20250514"
        
        mock_instance.messages.create.return_value = mock_response
        mock.return_value = mock_instance
        
        yield mock_instance
```

### Testing API Error Handling

```python
from openai import APIError

def test_api_error_handling(mock_openai_client, caplog):
    """Test that API errors are handled correctly."""
    # Arrange
    mock_openai_client.chat.completions.create.side_effect = APIError(
        "Rate limit exceeded"
    )
    
    # Act & Assert
    with pytest.raises(APIError):
        my_function(mock_openai_client)
    
    # Verify error was logged
    assert "API call failed" in caplog.text
```

## Testing Agent Workflows

### Testing Topic Scout

```python
# tests/test_topic_scout.py
import pytest
from unittest.mock import Mock, patch
import orjson
from scripts.topic_scout import discover_topics, validate_topics_schema

@pytest.fixture
def sample_topics_response():
    """Sample topics JSON response."""
    return {
        "topics": [
            {
                "title": "AI in Quality Engineering",
                "description": "How AI is transforming QE practices",
                "relevance_score": 9
            },
            {
                "title": "Shift-Left Testing",
                "description": "Moving testing earlier in SDLC",
                "relevance_score": 8
            }
        ]
    }

def test_discover_topics_success(mock_openai_client, sample_topics_response):
    """Test successful topic discovery."""
    # Arrange
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = (
        orjson.dumps(sample_topics_response).decode()
    )
    
    # Act
    result = discover_topics(mock_openai_client)
    
    # Assert
    assert "topics" in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["title"] == "AI in Quality Engineering"

def test_discover_topics_empty_result(mock_openai_client):
    """Test handling of empty topic list."""
    # Arrange
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = (
        '{"topics": []}'
    )
    
    # Act
    result = discover_topics(mock_openai_client)
    
    # Assert
    assert "topics" in result
    assert len(result["topics"]) == 0

def test_validate_topics_schema_valid():
    """Test schema validation with valid data."""
    # Arrange
    topics = {
        "topics": [
            {"title": "Test", "description": "Desc", "relevance_score": 5}
        ]
    }
    
    # Act
    result = validate_topics_schema(topics)
    
    # Assert
    assert result is True

def test_validate_topics_schema_missing_field():
    """Test schema validation with missing required field."""
    # Arrange
    topics = {
        "topics": [
            {"title": "Test", "description": "Desc"}  # Missing score
        ]
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match="Missing required field"):
        validate_topics_schema(topics)
```

### Testing Editorial Board

```python
# tests/test_editorial_board.py
import pytest
from unittest.mock import Mock, patch
from scripts.editorial_board import collect_votes, aggregate_scores, PERSONA_PROMPTS

@pytest.fixture
def sample_topic():
    """Sample topic for voting."""
    return {
        "title": "AI in QE",
        "description": "Emerging AI practices",
        "relevance_score": 9
    }

def test_collect_votes_all_personas(mock_openai_client, sample_topic):
    """Test that all 6 personas vote."""
    # Arrange
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "8"
    
    # Act
    votes = collect_votes(mock_openai_client, sample_topic)
    
    # Assert
    assert len(votes) == 6
    assert all(persona in votes for persona in PERSONA_PROMPTS.keys())
    assert all(isinstance(vote, int) for vote in votes.values())

def test_aggregate_scores_weighted():
    """Test weighted score aggregation."""
    # Arrange
    votes = {
        "practitioner": 9,
        "consultant": 8,
        "academic": 7,
        "vendor": 6,
        "skeptic": 5,
        "visionary": 10
    }
    
    # Act
    final_score = aggregate_scores(votes)
    
    # Assert
    assert isinstance(final_score, float)
    assert 5.0 <= final_score <= 10.0

def test_validate_vote_score_valid():
    """Test vote score validation with valid score."""
    # Arrange
    vote = 8
    
    # Act
    result = validate_vote_score(vote)
    
    # Assert
    assert result == 8

def test_validate_vote_score_out_of_range():
    """Test vote score validation with invalid score."""
    # Arrange
    vote = 15  # Out of 0-10 range
    
    # Act & Assert
    with pytest.raises(ValueError, match="Vote score must be between 0 and 10"):
        validate_vote_score(vote)
```

### Testing Economist Agent Pipeline

```python
# tests/test_economist_agent.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from scripts.economist_agent import (
    run_research_stage,
    run_graphics_stage,
    run_writing_stage,
    run_editing_stage,
    generate_article
)

@pytest.fixture
def temp_session_dir(tmp_path):
    """Create temporary session directory."""
    session_dir = tmp_path / "test_session"
    session_dir.mkdir()
    return session_dir

@pytest.fixture
def sample_topic():
    """Sample topic for article generation."""
    return {
        "title": "AI-Driven Test Automation",
        "description": "The future of automated testing",
        "relevance_score": 9
    }

def test_run_research_stage(mock_openai_client, sample_topic, temp_session_dir):
    """Test research stage execution."""
    # Arrange
    expected_research = {
        "data_points": ["Point 1", "Point 2"],
        "sources": ["Source 1", "Source 2"]
    }
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = (
        orjson.dumps(expected_research).decode()
    )
    
    # Act
    result = run_research_stage(mock_openai_client, sample_topic, temp_session_dir)
    
    # Assert
    assert "data_points" in result
    assert len(result["data_points"]) == 2
    
    # Verify output was saved
    output_file = temp_session_dir / "research_agent.json"
    assert output_file.exists()

def test_generate_article_full_pipeline(
    mock_openai_client,
    sample_topic,
    tmp_path
):
    """Test full article generation pipeline."""
    # Arrange
    with patch('scripts.economist_agent.OUTPUT_DIR', tmp_path):
        # Mock all stage responses
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = (
            '{"result": "success"}'
        )
        
        # Act
        article_path = generate_article(sample_topic, interactive=False)
        
        # Assert
        assert article_path is not None
        assert article_path.exists()
        assert article_path.suffix == ".md"

def test_generate_article_interactive_rejection(
    mock_openai_client,
    sample_topic,
    tmp_path
):
    """Test interactive mode with user rejection."""
    # Arrange
    with patch('scripts.economist_agent.OUTPUT_DIR', tmp_path):
        with patch('scripts.economist_agent.approve_stage', return_value=False):
            # Act
            article_path = generate_article(sample_topic, interactive=True)
            
            # Assert
            assert article_path is None  # Generation stopped by user
```

## Testing File Operations

### Testing with Temporary Directories

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory structure."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "charts").mkdir()
    (output_dir / "governance").mkdir()
    return output_dir

def test_save_agent_output(temp_output_dir):
    """Test saving agent output to JSON."""
    # Arrange
    output_data = {"key": "value", "list": [1, 2, 3]}
    output_file = temp_output_dir / "test_output.json"
    
    # Act
    save_agent_output(output_data, output_file)
    
    # Assert
    assert output_file.exists()
    
    # Verify content
    with open(output_file, "rb") as f:
        loaded_data = orjson.loads(f.read())
    assert loaded_data == output_data
```

## Testing Logging

### Capturing Log Output

```python
import logging

def test_error_logging(caplog):
    """Test that errors are properly logged."""
    # Arrange
    caplog.set_level(logging.ERROR)
    
    # Act
    try:
        raise ValueError("Test error")
    except ValueError as e:
        logger.error(f"Caught error: {e}")
    
    # Assert
    assert "Caught error: Test error" in caplog.text
    assert caplog.records[0].levelname == "ERROR"
```

## Testing Environment Variables

```python
import os
import pytest

def test_missing_api_key(monkeypatch):
    """Test handling of missing API key."""
    # Arrange
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    # Act & Assert
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable not set"):
        initialize_client()

def test_with_api_key(monkeypatch):
    """Test with API key present."""
    # Arrange
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    
    # Act
    client = initialize_client()
    
    # Assert
    assert client is not None
```

## Coverage Requirements

**Minimum coverage: 80%**

Run coverage with:
```bash
pytest --cov=scripts --cov-report=term-missing tests/
```

**Coverage report should show:**
```
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
scripts/topic_scout.py           45      2    96%   123, 145
scripts/editorial_board.py       67      5    93%   89-93
scripts/economist_agent.py      134     15    89%   234-248
scripts/generate_chart.py        42      8    81%   67-74
-----------------------------------------------------------
TOTAL                           288     30    90%
```

## Pytest Configuration

**Create `pytest.ini`:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=scripts
    --cov-report=term-missing
    --cov-fail-under=80
    --strict-markers
markers =
    integration: Integration tests (require API access)
    unit: Unit tests (no external dependencies)
```

## Fixtures File

**Create `tests/conftest.py`:**
```python
"""Shared pytest fixtures for economist-agents tests."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import orjson

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch('openai.OpenAI') as mock:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"result": "success"}'))]
        mock_response.usage = Mock(total_tokens=100)
        mock_response.model = "gpt-4o"
        mock_instance.chat.completions.create.return_value = mock_response
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch('anthropic.Anthropic') as mock:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text='{"result": "success"}')]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_response.model = "claude-sonnet-4-20250514"
        mock_instance.messages.create.return_value = mock_response
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory structure."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "charts").mkdir()
    (output_dir / "governance").mkdir()
    return output_dir

@pytest.fixture
def sample_agent_response():
    """Sample agent response for testing."""
    return {
        "content": "Agent response content",
        "usage": {"total_tokens": 150},
        "model": "gpt-4o"
    }
```

## Best Practices

1. **Test file naming**: `test_<module_name>.py`
2. **Test function naming**: `test_<function>_<scenario>`
3. **One assertion per test**: Focus on single behavior
4. **Use descriptive names**: Test names should explain what they verify
5. **Mock external dependencies**: Never call real APIs in tests
6. **Test edge cases**: Empty inputs, invalid data, API errors
7. **Keep tests isolated**: No test should depend on another
8. **Use fixtures**: Share common setup code
9. **Test both paths**: Success and failure scenarios

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_topic_scout.py

# Run specific test
pytest tests/test_topic_scout.py::test_discover_topics_success

# Run with coverage
pytest --cov=scripts --cov-report=html tests/

# Run only unit tests
pytest -m unit tests/

# Run with verbose output
pytest -v tests/
```

---

**Remember:** Good tests are the foundation of reliable multi-agent systems. Test early, test often, and aim for >80% coverage.
