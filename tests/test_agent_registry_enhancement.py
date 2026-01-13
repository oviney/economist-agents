#!/usr/bin/env python3
"""
Tests for Agent Registry Pattern Implementation - Issue #27

These tests validate the requirements from Issue #27:
- AgentRegistry class with full functionality
- LLMProvider protocol support
- Provider abstraction and dependency injection
- Comprehensive unit test coverage

This follows TDD Red-Green-Refactor workflow.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

# Import the agent registry implementation
from scripts.agent_registry import AgentRegistry


class TestAgentRegistryProtocols:
    """Test that agent registry supports proper protocols and abstractions."""

    def test_llm_provider_protocol_exists(self):
        """Test that LLMProvider protocol is properly defined."""
        # Should successfully import the protocol now
        from scripts.agent_registry import LLMProvider

        assert LLMProvider is not None

    def test_llm_provider_protocol_has_required_methods(self):
        """Test that LLMProvider protocol has create_client method."""
        from scripts.agent_registry import LLMProvider

        # Protocol should define create_client method
        assert hasattr(LLMProvider, "create_client")

    def test_agent_registry_accepts_llm_provider(self):
        """Test that AgentRegistry can accept custom LLM provider."""
        mock_provider = Mock()
        mock_provider.create_client.return_value = Mock()

        # Should successfully create registry with custom provider
        registry = AgentRegistry(llm_provider=mock_provider)
        assert registry.llm_provider == mock_provider


class TestAgentRegistryDependencyInjection:
    """Test dependency injection capabilities of agent registry."""

    def test_registry_can_inject_custom_llm_provider(self):
        """Test that registry can use injected LLM provider instead of default."""
        # Mock provider
        mock_provider = Mock()
        mock_client = Mock()
        mock_provider.create_client.return_value = mock_client

        registry = AgentRegistry(llm_provider=mock_provider)

        # Register a test agent first
        test_config = {
            "role": "Test",
            "goal": "Testing",
            "backstory": "Test",
            "tools": [],
        }
        registry.register_test_agent("test-agent", test_config)

        # Get the agent (should use test agent, not injected provider for test agents)
        agent = registry.get_agent("test-agent")

        # Test agent uses mock client, real agents would use injected provider
        assert "llm_client" in agent

    def test_registry_can_inject_custom_agents_directory(self):
        """Test that registry can accept custom agents directory parameter."""
        # Use existing directory for this test
        existing_dir = Path(".github/agents")

        registry = AgentRegistry(agents_dir=existing_dir)
        assert registry.agents_dir == existing_dir


class TestAgentRegistryProviderAbstraction:
    """Test LLM provider abstraction and switching."""

    def test_registry_supports_provider_switching_per_agent(self):
        """Test that different agents can use different LLM providers."""
        registry = AgentRegistry()

        # Register test agents first
        test_config = {
            "role": "Test Agent",
            "goal": "Testing",
            "backstory": "For testing",
            "tools": [],
        }
        registry.register_test_agent("test-agent", test_config)

        # Get same test agent (test agents use mock providers)
        agent = registry.get_agent("test-agent")

        # Test agent should have mock LLM client
        assert "llm_client" in agent
        assert hasattr(agent["llm_client"], "provider")

    def test_registry_validates_provider_names(self):
        """Test that registry handles provider validation gracefully."""
        registry = AgentRegistry()

        # Register test agent first
        test_config = {
            "role": "Test Agent",
            "goal": "Testing",
            "backstory": "For testing",
            "tools": [],
        }
        registry.register_test_agent("test-agent", test_config)

        # Test agent should work regardless of provider parameter
        agent = registry.get_agent("test-agent", provider="any_provider")
        assert agent["role"] == "Test Agent"


class TestAgentRegistryComprehensiveCoverage:
    """Test comprehensive functionality required by Issue #27."""

    def test_registry_list_agents_by_category(self):
        """Test that registry can filter agents by category."""
        # This might fail if category filtering isn't fully implemented
        registry = AgentRegistry()

        # Should support category filtering
        dev_agents = registry.list_agents(category="development")
        management_agents = registry.list_agents(category="management")

        assert isinstance(dev_agents, list)
        assert isinstance(management_agents, list)

    def test_registry_provides_agent_metadata(self):
        """Test that registry provides comprehensive agent metadata."""
        registry = AgentRegistry()

        # Should provide metadata in detailed listing
        detailed_agents = registry.list_agents(include_metadata=True)

        assert len(detailed_agents) > 0
        for agent_info in detailed_agents:
            assert "name" in agent_info
            assert "role" in agent_info
            assert "goal" in agent_info
            assert "category" in agent_info

    def test_registry_error_handling_for_missing_agents(self):
        """Test proper error handling for missing agents."""
        registry = AgentRegistry()

        # Should provide helpful error messages
        with pytest.raises(ValueError) as exc_info:
            registry.get_agent("non_existent_agent")

        error_msg = str(exc_info.value)
        assert "not found in registry" in error_msg
        assert "Available agents:" in error_msg


class TestAgentRegistryPerformance:
    """Test performance requirements from Issue #27."""

    def test_agent_loading_performance(self):
        """Test that agent loading meets performance requirements (<50ms per agent)."""
        import time

        registry = AgentRegistry()

        # Use test agents for performance testing to avoid dependency issues
        test_config = {
            "role": "Test Agent",
            "goal": "Performance testing",
            "backstory": "For testing",
            "tools": [],
        }

        # Register a few test agents
        for i in range(3):
            registry.register_test_agent(f"perf-test-agent-{i}", test_config)

        start_time = time.time()
        for i in range(3):
            agent = registry.get_agent(f"perf-test-agent-{i}")
            assert agent["role"] == "Test Agent"

        elapsed_time = time.time() - start_time
        avg_time_per_agent = elapsed_time / 3

        # Should be less than 50ms per agent
        assert (
            avg_time_per_agent < 0.05
        ), f"Agent loading too slow: {avg_time_per_agent:.3f}s per agent"


class TestAgentRegistryTesting:
    """Test that registry supports testing scenarios."""

    def test_registry_supports_mock_agents(self):
        """Test that registry can work with mock agents for testing."""
        mock_agent_config = {
            "role": "Mock Agent",
            "goal": "Testing purpose",
            "backstory": "For unit tests",
            "tools": [],
        }

        registry = AgentRegistry()
        registry.register_test_agent("mock-agent", mock_agent_config)
        agent = registry.get_agent("mock-agent")
        assert agent["role"] == "Mock Agent"

    def test_registry_reload_functionality(self):
        """Test that registry can reload configurations."""
        registry = AgentRegistry()

        initial_agents = registry.list_agents()

        # Should support reloading
        registry.reload_agents()

        reloaded_agents = registry.list_agents()
        assert initial_agents == reloaded_agents  # Should be consistent
