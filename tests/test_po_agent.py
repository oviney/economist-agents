#!/usr/bin/env python3
"""
Test Suite for Product Owner Agent

Tests story generation, AC generation, estimation, and backlog management.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from po_agent import ProductOwnerAgent


@pytest.fixture
def temp_backlog():
    """Create temporary backlog file for testing"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        f.write(
            json.dumps(
                {"version": "1.0", "created": "2026-01-02", "stories": [], "escalations": []}
            )
        )
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for deterministic testing"""
    with patch("po_agent.create_llm_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client


class TestProductOwnerAgent:
    """Test suite for ProductOwnerAgent"""

    def test_initialization(self, temp_backlog):
        """Test agent initialization with backlog file"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)
        assert agent.backlog_file == Path(temp_backlog)
        assert "stories" in agent.backlog
        assert "escalations" in agent.backlog

    def test_parse_user_request_valid(self, temp_backlog, mock_llm_client):
        """Test parsing valid user request into user story"""
        # Mock LLM response
        mock_response = {
            "user_story": "As a QE lead, I need automated test coverage analysis, so that I can identify gaps systematically",
            "acceptance_criteria": [
                "[ ] Given test suite, When analyzer runs, Then reports coverage by component",
                "[ ] Given coverage report, When gaps found, Then recommends specific tests",
                "[ ] Given 100+ tests, When analysis completes, Then finishes in <5 minutes",
                "[ ] Quality: 90% accuracy in gap detection vs manual review",
            ],
            "story_points": 5,
            "estimation_confidence": "medium",
            "quality_requirements": {
                "content_quality": "Documentation with examples",
                "performance": "Analysis completes in <5 minutes",
                "maintainability": "Code follows ruff standards",
            },
            "priority": "P1",
            "escalations": [],
            "implementation_notes": "Integrate with existing test infrastructure",
        }

        with patch("po_agent.call_llm") as mock_call:
            mock_call.return_value = json.dumps(mock_response)
            agent = ProductOwnerAgent(backlog_file=temp_backlog)
            story = agent.parse_user_request(
                "We need automated test coverage analysis"
            )

        # Validate story structure
        assert "user_story" in story
        assert "As a" in story["user_story"]
        assert len(story["acceptance_criteria"]) == 4
        assert story["story_points"] == 5
        assert story["priority"] == "P1"
        assert "created" in story
        assert "status" in story

    def test_parse_user_request_with_escalations(self, temp_backlog, mock_llm_client):
        """Test parsing ambiguous request that requires escalation"""
        mock_response = {
            "user_story": "As a developer, I need improved chart quality, so that users trust data visualization",
            "acceptance_criteria": [
                "[ ] Given chart, When rendered, Then meets visual standards",
                "[ ] Quality: Zero zone boundary violations",
                "[ ] Quality: 100% Visual QA pass rate",
            ],
            "story_points": 3,
            "estimation_confidence": "low",
            "quality_requirements": {},
            "priority": "P1",
            "escalations": [
                "What specific chart quality issues are most critical? (layout, colors, labels, data accuracy)",
                "Should this include existing chart refactoring or only new charts?",
            ],
            "implementation_notes": "Needs clarification before implementation",
        }

        with patch("po_agent.call_llm") as mock_call:
            mock_call.return_value = json.dumps(mock_response)
            agent = ProductOwnerAgent(backlog_file=temp_backlog)
            story = agent.parse_user_request("Improve chart quality")

        # Validate escalations
        assert len(story["escalations"]) == 2
        assert "clarification" in story["implementation_notes"].lower()

    def test_generate_acceptance_criteria(self, temp_backlog, mock_llm_client):
        """Test AC generation for existing user story"""
        mock_response = [
            "[ ] Given PO Agent, When user provides request, Then generates structured story",
            "[ ] Given story, When validated, Then meets DoR criteria",
            "[ ] Quality: Generation completes in <2 minutes",
        ]

        with patch("po_agent.call_llm") as mock_call:
            mock_call.return_value = json.dumps(mock_response)
            agent = ProductOwnerAgent(backlog_file=temp_backlog)
            criteria = agent.generate_acceptance_criteria(
                "As a PO, I need automated story generation, so that backlog refinement is faster"
            )

        assert len(criteria) == 3
        assert all("[ ]" in c for c in criteria)
        assert any("Quality:" in c for c in criteria)

    def test_estimate_story_points(self, temp_backlog, mock_llm_client):
        """Test story point estimation based on AC complexity"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)

        # Simple story (1 point)
        points, confidence = agent.estimate_story_points(
            "Simple bug fix",
            [
                "[ ] Given bug, When fixed, Then tests pass",
                "[ ] Quality: Fix deployed",
            ],
        )
        assert points == 1
        assert confidence == "high"

        # Complex story with many indicators (5+ points)
        points, confidence = agent.estimate_story_points(
            "Integration test suite",
            [
                "[ ] Given integration test, When run, Then validates agent coordination",
                "[ ] Given test failure, When edge case detected, Then logs clearly",
                "[ ] Given quality gate, When validation fails, Then blocks appropriately",
                "[ ] Given 10+ tests, When executed, Then all pass",
                "[ ] Quality: 90% coverage of integration points",
                "[ ] Quality: Tests run in CI/CD pipeline",
            ],
        )
        assert points >= 5
        assert confidence in ["medium", "low"]

    def test_validate_story_structure(self, temp_backlog, mock_llm_client):
        """Test story validation catches missing required fields"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)

        # Valid story
        valid_story = {
            "user_story": "As a dev, I need X, so that Y",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "story_points": 3,
        }
        assert agent._validate_story(valid_story) is True

        # Missing AC
        invalid_story = {
            "user_story": "As a dev, I need X, so that Y",
            "story_points": 3,
        }
        assert agent._validate_story(invalid_story) is False

        # Too few AC (need 3-7)
        invalid_story = {
            "user_story": "As a dev, I need X, so that Y",
            "acceptance_criteria": ["AC1", "AC2"],
            "story_points": 3,
        }
        assert agent._validate_story(invalid_story) is False

        # Invalid story points
        invalid_story = {
            "user_story": "As a dev, I need X, so that Y",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "story_points": 4,  # Not in Fibonacci sequence
        }
        assert agent._validate_story(invalid_story) is False

    def test_add_to_backlog(self, temp_backlog, mock_llm_client):
        """Test adding story to backlog file"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)

        story = {
            "user_story": "Test story",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "story_points": 2,
            "priority": "P1",
            "escalations": [],
        }

        agent.add_to_backlog(story)

        # Verify saved
        with open(temp_backlog) as f:
            backlog = json.load(f)

        assert len(backlog["stories"]) == 1
        assert backlog["stories"][0]["user_story"] == "Test story"

    def test_backlog_with_escalations(self, temp_backlog, mock_llm_client):
        """Test backlog tracks escalations separately"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)

        story = {
            "user_story": "Ambiguous story",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "story_points": 3,
            "priority": "P0",
            "escalations": [
                "Question 1: What is priority?",
                "Question 2: What is scope?",
            ],
        }

        agent.add_to_backlog(story)

        # Verify escalations tracked
        with open(temp_backlog) as f:
            backlog = json.load(f)

        assert len(backlog["escalations"]) == 2
        assert backlog["escalations"][0]["story_id"] == 0
        assert backlog["escalations"][0]["status"] == "pending"

    def test_backlog_summary(self, temp_backlog, mock_llm_client):
        """Test backlog summary generation"""
        agent = ProductOwnerAgent(backlog_file=temp_backlog)

        # Add multiple stories
        for i in range(3):
            story = {
                "user_story": f"Story {i}",
                "acceptance_criteria": ["AC1", "AC2", "AC3"],
                "story_points": 2 + i,
                "priority": ["P0", "P1", "P2"][i],
                "escalations": ["Question"] if i == 0 else [],
            }
            agent.add_to_backlog(story)

        summary = agent.get_backlog_summary()

        # Validate summary content
        assert "Total Stories: 3" in summary
        assert "Total Story Points: 9" in summary  # 2+3+4
        assert "P0: 1" in summary
        assert "P1: 1" in summary
        assert "P2: 1" in summary
        assert "Pending Escalations: 1" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
