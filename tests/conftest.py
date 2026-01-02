"""Pytest configuration and shared fixtures for economist-agents tests."""

import pytest
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create temporary output directory for tests.
    
    Args:
        tmp_path: Pytest temporary directory fixture
        
    Returns:
        Path to temporary output directory
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "charts").mkdir()
    return output_dir


@pytest.fixture
def mock_anthropic_client() -> Mock:
    """Create mock Anthropic client for testing.
    
    Returns:
        Mock Anthropic client with messages.create method
    """
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text='{"data": "test"}')]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_openai_client() -> Mock:
    """Create mock OpenAI client for testing.
    
    Returns:
        Mock OpenAI client with chat.completions.create method
    """
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"data": "test"}'))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_research_data() -> dict:
    """Sample research agent output for testing.
    
    Returns:
        Dictionary with research data structure
    """
    return {
        "headline_stat": {
            "value": "80% of teams use AI testing",
            "source": "Gartner 2024 Survey",
            "year": "2024",
            "verified": True
        },
        "data_points": [
            {
                "stat": "50% reduction in test maintenance",
                "source": "Industry Report",
                "year": "2024",
                "verified": True
            }
        ],
        "chart_data": {
            "title": "AI Adoption in Testing",
            "type": "line",
            "data": [{"year": 2023, "value": 60}, {"year": 2024, "value": 80}]
        }
    }
