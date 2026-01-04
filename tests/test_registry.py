#!/usr/bin/env python3
"""
Test Agent Registry

Validates that AgentRegistry can load and instantiate Stage3Crew and Stage4Crew.
"""

import os

import pytest

from src.registry import AgentRegistry

# Skip tests that require CrewAI and API keys
requires_crewai = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY for CrewAI",
)


class TestAgentRegistry:
    """Test cases for AgentRegistry"""

    def test_registry_initialization(self):
        """Test that AgentRegistry initializes correctly"""
        registry = AgentRegistry()
        assert registry is not None

    @requires_crewai
    def test_load_stage3_crew(self):
        """Test that AgentRegistry can load Stage3Crew"""
        registry = AgentRegistry()

        # Load Stage3Crew class
        stage3_class = registry.get_crew_class("Stage3Crew")
        assert stage3_class is not None

        # Instantiate with a topic
        crew_instance = stage3_class(topic="Test Topic")
        assert crew_instance is not None
        assert hasattr(crew_instance, "kickoff")

    @requires_crewai
    def test_load_stage4_crew(self):
        """Test that AgentRegistry can load Stage4Crew"""
        registry = AgentRegistry()

        # Load Stage4Crew class
        stage4_class = registry.get_crew_class("Stage4Crew")
        assert stage4_class is not None

        # Instantiate (Stage4Crew takes no __init__ args)
        crew_instance = stage4_class()
        assert crew_instance is not None
        assert hasattr(crew_instance, "kickoff")

    def test_get_available_crews(self):
        """Test that AgentRegistry can list available crews"""
        registry = AgentRegistry()

        available_crews = registry.get_available_crews()
        assert isinstance(available_crews, list)
        assert "Stage3Crew" in available_crews
        assert "Stage4Crew" in available_crews

    def test_invalid_crew_name(self):
        """Test that requesting an invalid crew raises appropriate error"""
        registry = AgentRegistry()

        with pytest.raises((ValueError, KeyError)):
            registry.get_crew_class("NonExistentCrew")
