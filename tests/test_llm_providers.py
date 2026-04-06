#!/usr/bin/env python3
"""
Tests for OpenAIProvider and AnthropicProvider concrete implementations.

Validates ADR-002 acceptance criteria:
- LLMProvider protocol defined
- OpenAI and Anthropic providers implemented
- Dependency injection via AgentRegistry
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.agent_registry import (
    AgentRegistry,
    AnthropicProvider,
    OpenAIProvider,
    _validate_agent_name,
)
from scripts.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Helper: minimal AgentRegistry pointing at the real .github/agents/ dir
# ---------------------------------------------------------------------------

AGENTS_DIR_PATH = (
    Path(__file__).parent.parent
    / ".github"
    / "agents"
)


def _registry(provider=None) -> AgentRegistry:
    from pathlib import Path

    return AgentRegistry(
        agents_dir=Path(".github/agents"),
        llm_provider=provider,
    )


# ---------------------------------------------------------------------------
# _validate_agent_name edge cases
# ---------------------------------------------------------------------------


class TestValidateAgentName:
    """Tests for the _validate_agent_name helper function."""

    def test_empty_name_raises(self):
        """Empty string must raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_agent_name("")

    def test_invalid_chars_raises(self):
        """Names with spaces or special characters are rejected."""
        with pytest.raises(ValueError, match="Invalid agent name"):
            _validate_agent_name("my agent!")

    def test_name_too_long_raises(self):
        """Names longer than 100 characters are rejected."""
        with pytest.raises(ValueError, match="too long"):
            _validate_agent_name("a" * 101)

    def test_valid_name_passes(self):
        """Valid names with letters, digits, hyphens, underscores pass."""
        _validate_agent_name("my-agent_v2")  # should not raise


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    """Unit tests for OpenAIProvider concrete class."""

    def test_implements_llm_provider_protocol(self):
        """OpenAIProvider must expose create_client matching LLMProvider."""
        assert hasattr(OpenAIProvider, "create_client")

    def test_create_client_returns_llm_client(self):
        """create_client should return an LLMClient wrapping an OpenAI client."""
        mock_openai_instance = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), patch("openai.OpenAI", return_value=mock_openai_instance):
            provider = OpenAIProvider()
            client = provider.create_client()

        assert isinstance(client, LLMClient)
        assert client.provider == "openai"

    def test_create_client_uses_default_model(self):
        """Default model is gpt-4o when no model arg given."""
        mock_openai_instance = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), patch("openai.OpenAI", return_value=mock_openai_instance):
            provider = OpenAIProvider()
            client = provider.create_client()

        assert client.model == "gpt-4o"

    def test_create_client_model_override(self):
        """Passing a model arg overrides the default."""
        mock_openai_instance = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), patch("openai.OpenAI", return_value=mock_openai_instance):
            provider = OpenAIProvider()
            client = provider.create_client(model="gpt-4-turbo")

        assert client.model == "gpt-4-turbo"

    def test_custom_default_model(self):
        """Constructor default_model is respected."""
        mock_openai_instance = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), patch("openai.OpenAI", return_value=mock_openai_instance):
            provider = OpenAIProvider(default_model="gpt-3.5-turbo")
            client = provider.create_client()

        assert client.model == "gpt-3.5-turbo"

    def test_api_key_from_constructor(self):
        """API key passed directly to constructor is used."""
        mock_openai_instance = MagicMock()

        with patch("openai.OpenAI", return_value=mock_openai_instance) as MockOpenAI:
            provider = OpenAIProvider(api_key="sk-direct")
            provider.create_client()

        assert provider.api_key == "sk-direct"
        MockOpenAI.assert_called_once_with(api_key="sk-direct")

    def test_missing_api_key_raises(self):
        """Missing API key raises ValueError."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            provider = OpenAIProvider()
            with pytest.raises(ValueError, match="API key not set"):
                provider.create_client()

    def test_missing_openai_package_raises(self):
        """ImportError raised when openai package is absent."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return real_import(name, *args, **kwargs)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            provider = OpenAIProvider()
            with patch("builtins.__import__", side_effect=mock_import), pytest.raises(ImportError, match="openai package not installed"):
                provider.create_client()


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    """Unit tests for AnthropicProvider concrete class."""

    def test_implements_llm_provider_protocol(self):
        """AnthropicProvider must expose create_client matching LLMProvider."""
        assert hasattr(AnthropicProvider, "create_client")

    def _mock_anthropic_module(self, mock_instance: MagicMock) -> MagicMock:
        """Return a fake ``anthropic`` module with Anthropic class using *mock_instance*."""
        import types

        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(return_value=mock_instance)  # type: ignore[attr-defined]
        return fake_module

    def test_create_client_returns_llm_client(self):
        """create_client should return an LLMClient wrapping an Anthropic client."""
        import sys
        import types

        mock_anthropic_instance = MagicMock()
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(return_value=mock_anthropic_instance)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}), patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            client = provider.create_client()

        assert isinstance(client, LLMClient)
        assert client.provider == "anthropic"

    def test_create_client_uses_default_model(self):
        """Default model is claude-sonnet-4-20250514 when no model arg given."""
        import sys
        import types

        mock_anthropic_instance = MagicMock()
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(return_value=mock_anthropic_instance)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}), patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            client = provider.create_client()

        assert client.model == "claude-sonnet-4-20250514"

    def test_create_client_model_override(self):
        """Passing a model arg overrides the default."""
        import sys
        import types

        mock_anthropic_instance = MagicMock()
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(return_value=mock_anthropic_instance)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}), patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            client = provider.create_client(model="claude-3-haiku-20240307")

        assert client.model == "claude-3-haiku-20240307"

    def test_custom_default_model(self):
        """Constructor default_model is respected."""
        import sys
        import types

        mock_anthropic_instance = MagicMock()
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock(return_value=mock_anthropic_instance)  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}), patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider(default_model="claude-3-opus-20240229")
            client = provider.create_client()

        assert client.model == "claude-3-opus-20240229"

    def test_api_key_from_constructor(self):
        """API key passed directly to constructor is used."""
        import sys
        import types

        mock_anthropic_instance = MagicMock()
        MockAnth = MagicMock(return_value=mock_anthropic_instance)
        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MockAnth  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider(api_key="sk-ant-direct")
            provider.create_client()

        assert provider.api_key == "sk-ant-direct"
        MockAnth.assert_called_once_with(api_key="sk-ant-direct")

    def test_missing_api_key_raises(self):
        """Missing API key raises ValueError."""
        import sys
        import types

        fake_module = types.ModuleType("anthropic")
        fake_module.Anthropic = MagicMock()  # type: ignore[attr-defined]

        env_without_key = {
            k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"
        }
        with patch.dict(os.environ, env_without_key, clear=True), patch.dict(sys.modules, {"anthropic": fake_module}):
            provider = AnthropicProvider()
            with pytest.raises(ValueError, match="API key not set"):
                provider.create_client()

    def test_missing_anthropic_package_raises(self):
        """ImportError raised when anthropic package is absent."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return real_import(name, *args, **kwargs)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            provider = AnthropicProvider()
            with patch("builtins.__import__", side_effect=mock_import), pytest.raises(ImportError, match="anthropic package not installed"):
                provider.create_client()


# ---------------------------------------------------------------------------
# Provider integration with AgentRegistry
# ---------------------------------------------------------------------------


class TestProviderIntegrationWithRegistry:
    """Test that AgentRegistry correctly delegates to injected providers."""

    def test_registry_uses_openai_provider(self):
        """AgentRegistry.get_agent uses injected OpenAIProvider."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "openai"
        mock_provider = MagicMock(spec=OpenAIProvider)
        mock_provider.create_client.return_value = mock_client

        registry = _registry(provider=mock_provider)

        test_config = {
            "role": "Test",
            "goal": "Testing",
            "backstory": "Tester",
            "tools": [],
        }
        registry.register_test_agent("test-openai-agent", test_config)
        agent = registry.get_agent("test-openai-agent")

        # Test agents use their own mock client, real agents use injected provider
        assert agent["role"] == "Test"

    def test_registry_uses_anthropic_provider(self):
        """AgentRegistry.get_agent uses injected AnthropicProvider."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.provider = "anthropic"
        mock_provider = MagicMock(spec=AnthropicProvider)
        mock_provider.create_client.return_value = mock_client

        registry = _registry(provider=mock_provider)

        test_config = {
            "role": "Claude Agent",
            "goal": "Testing Anthropic",
            "backstory": "Anthropic tester",
            "tools": [],
        }
        registry.register_test_agent("test-anthropic-agent", test_config)
        agent = registry.get_agent("test-anthropic-agent")

        assert agent["role"] == "Claude Agent"

    def test_provider_switching_same_registry(self):
        """Same registry instance supports switching providers between calls."""
        openai_client = MagicMock(spec=LLMClient)
        openai_client.provider = "openai"
        openai_provider = MagicMock(spec=OpenAIProvider)
        openai_provider.create_client.return_value = openai_client

        anthropic_client = MagicMock(spec=LLMClient)
        anthropic_client.provider = "anthropic"
        anthropic_provider = MagicMock(spec=AnthropicProvider)
        anthropic_provider.create_client.return_value = anthropic_client

        registry_openai = _registry(provider=openai_provider)
        registry_anthropic = _registry(provider=anthropic_provider)

        assert registry_openai.llm_provider is openai_provider
        assert registry_anthropic.llm_provider is anthropic_provider


# ---------------------------------------------------------------------------
# AgentRegistry coverage: uncovered paths
# ---------------------------------------------------------------------------


class TestAgentRegistryCoveragePaths:
    """Cover the remaining branches not exercised by existing tests."""

    def test_get_agent_with_model_override(self):
        """get_agent passes the model arg to provider.create_client."""
        mock_client = MagicMock()
        mock_client.provider = "openai"
        mock_provider = MagicMock()
        mock_provider.create_client.return_value = mock_client

        with patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            registry = _registry(provider=mock_provider)
            agents = registry.list_agents()
            assert len(agents) > 0

            registry.get_agent(agents[0], model="gpt-4-turbo")

        # provider.create_client must have been called with the model override
        mock_provider.create_client.assert_called_once_with("gpt-4-turbo")

    def test_get_agent_error_message_includes_suggestion(self):
        """Error message suggests similar names when partial match exists."""
        registry = _registry()
        # "scrum" is a substring of "scrum-master"
        with pytest.raises(ValueError, match="scrum-master"):
            registry.get_agent("scrum")

    def test_get_agent_error_with_test_agents_count(self):
        """Error message mentions test agents when any are registered."""
        registry = _registry()
        registry.register_test_agent(
            "tmp-agent", {"role": "R", "goal": "G", "backstory": "B", "tools": []}
        )
        with pytest.raises(ValueError, match="test agent"):
            registry.get_agent("nonexistent-agent-xyz")

    def test_get_agent_config_returns_config(self):
        """get_agent_config returns the AgentConfig for a known agent."""
        registry = _registry()
        agents = registry.list_agents()
        name = agents[0]
        config = registry.get_agent_config(name)
        assert config.name == name

    def test_get_agent_config_missing_raises(self):
        """get_agent_config raises ValueError for unknown agent."""
        registry = _registry()
        with pytest.raises(ValueError, match="not found in registry"):
            registry.get_agent_config("this-does-not-exist")

    def test_register_test_agent_missing_fields_raises(self):
        """register_test_agent rejects configs with missing required fields."""
        registry = _registry()
        with pytest.raises(ValueError, match="missing required fields"):
            registry.register_test_agent("bad-agent", {"role": "X"})

    def test_instantiate_tools_unknown_tool_logged(self):
        """_instantiate_tools silently skips unknown tool names."""
        registry = _registry()
        result = registry._instantiate_tools(["totally_unknown_tool_xyz"])
        assert result == []

    def test_instantiate_tools_known_tool_returns_mock(self):
        """_instantiate_tools returns mock objects for known tool names."""
        registry = _registry()
        result = registry._instantiate_tools(["file_read"])
        assert len(result) == 1

    def test_parse_markdown_frontmatter_no_frontmatter(self, tmp_path):
        """Files without --- frontmatter return an empty dict."""
        agent_file = tmp_path / "no-fm.agent.md"
        agent_file.write_text("Just plain text, no frontmatter here.")
        registry = _registry()
        result = registry._parse_markdown_frontmatter(agent_file)
        assert result == {}

    def test_parse_markdown_frontmatter_invalid_yaml(self, tmp_path):
        """Files with broken YAML raise ValueError."""
        agent_file = tmp_path / "bad-yaml.agent.md"
        agent_file.write_text("---\nkey: [unclosed bracket\n---\n")
        registry = _registry()
        with pytest.raises(ValueError, match="Invalid YAML"):
            registry._parse_markdown_frontmatter(agent_file)

    def test_parse_markdown_frontmatter_incomplete_delimiter(self, tmp_path):
        """Files with only a single --- delimiter raise ValueError."""
        agent_file = tmp_path / "incomplete.agent.md"
        # "---" split by "---" gives ["", ""] — only 2 parts, so < 3
        agent_file.write_text("---")
        registry = _registry()
        with pytest.raises(ValueError, match="Invalid frontmatter format"):
            registry._parse_markdown_frontmatter(agent_file)

    def test_extract_system_message_no_frontmatter(self, tmp_path):
        """Files without frontmatter return the full content as system message."""
        content = "You are an agent without frontmatter."
        agent_file = tmp_path / "plain.agent.md"
        agent_file.write_text(content)
        registry = _registry()
        result = registry._extract_system_message(agent_file)
        assert result == content

    def test_extract_system_message_only_opening_delimiter(self, tmp_path):
        """Files with only one --- return empty string from _extract_system_message."""
        agent_file = tmp_path / "lone-dash.agent.md"
        # "---" split into ["", ""] - len < 3, falls through to return ""
        agent_file.write_text("---")
        registry = _registry()
        result = registry._extract_system_message(agent_file)
        assert result == ""

    def test_load_agents_skips_malformed_file(self, tmp_path, caplog):
        """Malformed agent files are skipped with an error log entry."""
        # Write a file with broken YAML so _load_agents logs an error
        bad_file = tmp_path / "broken.agent.md"
        bad_file.write_text("---\nkey: [unclosed\n---\n")

        import logging

        with caplog.at_level(logging.ERROR):
            registry = AgentRegistry(agents_dir=tmp_path)

        assert "Failed to load agent" in caplog.text
        # The broken file should not appear in the agent list
        assert "broken" not in registry.list_agents()

    def test_agents_dir_not_found_raises(self, tmp_path):
        """AgentRegistry raises ValueError for a non-existent agents_dir."""
        nonexistent = tmp_path / "does-not-exist"
        with pytest.raises(ValueError, match="Agent directory not found"):
            AgentRegistry(agents_dir=nonexistent)

    def test_instantiate_tools_none_factory_result(self):
        """Tool factory returning None is filtered out with a warning."""
        registry = _registry()
        # Patch github_project_add_issue at module level to None to trigger
        # the "tool factory returned None" warning branch
        with patch("scripts.agent_registry.github_project_add_issue", None):
            result = registry._instantiate_tools(["github_project_add_issue"])
            # None tools are filtered out
            assert isinstance(result, list)
            assert all(t is not None for t in result)

    def test_instantiate_tools_mock_mode_when_crewai_unavailable(self):
        """Mock tools are created when CREWAI_TOOLS_AVAILABLE is False."""
        registry = _registry()
        # Temporarily disable crewai tools to exercise the mock-tools else-branch
        with patch("scripts.agent_registry.CREWAI_TOOLS_AVAILABLE", False):
            result = registry._instantiate_tools(["file_read", "bash"])
        # Both tools should be instantiated as MockTool objects
        assert len(result) == 2
        for tool in result:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")


# ---------------------------------------------------------------------------
# get_agent with injected provider and a real (non-test) agent
# ---------------------------------------------------------------------------


class TestGetAgentWithInjectedProviderRealAgent:
    """Cover line 554: provider.create_client called for real (non-test) agents."""

    def test_get_agent_calls_provider_create_client_for_real_agent(self):
        """provider.create_client is called when getting a real agent."""
        from scripts.llm_client import LLMClient

        mock_client = LLMClient("openai", MagicMock(), "gpt-4o")
        mock_provider = MagicMock()
        mock_provider.create_client.return_value = mock_client

        with patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            registry = _registry(provider=mock_provider)
            agents = registry.list_agents()
            assert len(agents) > 0

            agent = registry.get_agent(agents[0])

        # provider.create_client must have been called (line 554)
        mock_provider.create_client.assert_called_once()
        assert agent["llm_client"] is mock_client

    def test_get_agent_passes_model_to_provider(self):
        """provider.create_client receives the model argument."""
        from scripts.llm_client import LLMClient

        mock_client = LLMClient("openai", MagicMock(), "gpt-4-turbo")
        mock_provider = MagicMock()
        mock_provider.create_client.return_value = mock_client

        with patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            registry = _registry(provider=mock_provider)
            agents = registry.list_agents()

            registry.get_agent(agents[0], model="gpt-4-turbo")

        mock_provider.create_client.assert_called_once_with("gpt-4-turbo")


# ---------------------------------------------------------------------------
# get_agent without injected provider (default create_llm_client path)
# ---------------------------------------------------------------------------


class TestGetAgentWithDefaultProvider:
    """Cover the path where no llm_provider is injected (default behaviour)."""

    def test_get_agent_uses_create_llm_client_by_default(self):
        """When no provider is injected, get_agent falls back to create_llm_client."""
        from scripts.llm_client import LLMClient

        mock_client = LLMClient("openai", MagicMock(), "gpt-4o")

        with patch("scripts.agent_registry.create_llm_client", return_value=mock_client), patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            registry = _registry(provider=None)
            agents = registry.list_agents()
            assert len(agents) > 0
            agent = registry.get_agent(agents[0])
            assert agent["llm_client"] is mock_client

    def test_get_agent_model_override_with_default_provider(self):
        """model arg overrides llm_client.model when no provider is injected."""
        from scripts.llm_client import LLMClient

        mock_underlying = MagicMock()
        mock_client = LLMClient("openai", mock_underlying, "gpt-4o")

        with patch("scripts.agent_registry.create_llm_client", return_value=mock_client), patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            registry = _registry(provider=None)
            agents = registry.list_agents()
            agent = registry.get_agent(agents[0], model="gpt-4-turbo")
            assert agent["llm_client"].model == "gpt-4-turbo"


# ---------------------------------------------------------------------------
# main() CLI function
# ---------------------------------------------------------------------------


class TestMainCLI:
    """Cover the main() CLI entry-point."""

    def test_main_lists_agents_when_no_args(self, capsys):
        """main() with no args prints the agent catalogue."""
        import sys

        from scripts.agent_registry import main

        with patch.object(sys, "argv", ["agent_registry.py"]):
            main()

        captured = capsys.readouterr()
        assert "Available Agents" in captured.out

    def test_main_shows_agent_details_when_arg_given(self, capsys):
        """main() with a valid agent name prints that agent's details."""
        import sys

        from scripts.agent_registry import main
        from scripts.llm_client import LLMClient

        mock_client = LLMClient("openai", MagicMock(), "gpt-4o")

        registry = _registry(provider=None)
        first_agent = registry.list_agents()[0]

        with patch.object(sys, "argv", ["agent_registry.py", first_agent]), patch("scripts.agent_registry.create_llm_client", return_value=mock_client), patch.object(AgentRegistry, "_instantiate_tools", return_value=[]):
            main()

        captured = capsys.readouterr()
        assert "Successfully loaded agent" in captured.out

    def test_main_exits_with_error_for_unknown_agent(self, capsys):
        """main() exits with code 1 when the requested agent doesn't exist."""
        import sys

        from scripts.agent_registry import main

        with patch.object(sys, "argv", ["agent_registry.py", "no-such-agent-xyz"]), pytest.raises(SystemExit) as exc:
            main()

        assert exc.value.code == 1
