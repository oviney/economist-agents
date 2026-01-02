#!/usr/bin/env python3
"""
Unit tests for CrewAI Agent Factory

Tests agent loading, creation, validation, and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from scripts.crewai_agents import AgentFactory

# Sample agent configurations for testing
SAMPLE_AGENTS_YAML = """
agents:
  test_agent:
    role: "Test Agent"
    goal: "Test goal"
    backstory: "Test backstory"
    verbose: true
    allow_delegation: false

  another_agent:
    role: "Another Agent"
    goal: "Another goal"
    backstory: "Another backstory"
    verbose: false
    allow_delegation: true
    max_iter: 10
"""

INVALID_AGENTS_YAML = """
agents:
  missing_role:
    goal: "Goal without role"
    backstory: "Backstory"
"""

MALFORMED_YAML = """
agents:
  broken: [unclosed bracket
"""


@pytest.fixture
def temp_agents_file():
    """Create temporary agents.yaml for testing"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(SAMPLE_AGENTS_YAML)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink()


@pytest.fixture
def temp_invalid_file():
    """Create temporary invalid agents.yaml"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(INVALID_AGENTS_YAML)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink()


@pytest.fixture
def temp_malformed_file():
    """Create temporary malformed YAML"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(MALFORMED_YAML)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink()


class TestAgentFactoryInit:
    """Test AgentFactory initialization"""

    def test_init_with_valid_file(self, temp_agents_file):
        """Should load agents from valid YAML file"""
        factory = AgentFactory(config_path=temp_agents_file)
        assert "test_agent" in factory.agents
        assert "another_agent" in factory.agents
        assert factory.agents["test_agent"]["role"] == "Test Agent"

    def test_init_with_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError) as exc_info:
            AgentFactory(config_path="/nonexistent/agents.yaml")
        assert "Agent registry not found" in str(exc_info.value)

    def test_init_with_malformed_yaml(self, temp_malformed_file):
        """Should raise YAMLError for malformed YAML"""
        with pytest.raises(yaml.YAMLError) as exc_info:
            AgentFactory(config_path=temp_malformed_file)
        assert "Malformed agents.yaml" in str(exc_info.value)

    def test_init_with_missing_agents_key(self):
        """Should raise ValueError if 'agents' key missing"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not_agents:\n  test: value")
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                AgentFactory(config_path=temp_path)
            assert "missing 'agents' key" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_init_default_path(self):
        """Should use default path when no config_path provided"""
        # This will fail if schemas/agents.yaml doesn't exist
        # but tests the path resolution logic
        factory = AgentFactory()
        expected_path = Path(__file__).parent.parent / "schemas" / "agents.yaml"
        assert factory.config_path == expected_path


class TestCreateAgent:
    """Test agent creation"""

    @patch("scripts.crewai_agents.Agent")
    def test_create_agent_basic(self, mock_agent_class, temp_agents_file):
        """Should create agent with configuration from YAML"""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        factory = AgentFactory(config_path=temp_agents_file)
        agent = factory.create_agent("test_agent")

        # Verify Agent was called with correct parameters
        mock_agent_class.assert_called_once_with(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
            verbose=True,
            allow_delegation=False,
        )
        assert agent == mock_agent

    @patch("scripts.crewai_agents.Agent")
    def test_create_agent_with_overrides(self, mock_agent_class, temp_agents_file):
        """Should apply kwargs overrides to agent configuration"""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        factory = AgentFactory(config_path=temp_agents_file)
        _ = factory.create_agent("test_agent", verbose=False, goal="New goal")

        # Verify overrides were applied
        call_kwargs = mock_agent_class.call_args[1]
        assert call_kwargs["verbose"] is False
        assert call_kwargs["goal"] == "New goal"
        assert call_kwargs["role"] == "Test Agent"  # Not overridden

    @patch("scripts.crewai_agents.Agent")
    def test_create_agent_with_optional_params(
        self, mock_agent_class, temp_agents_file
    ):
        """Should include optional parameters when present"""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        factory = AgentFactory(config_path=temp_agents_file)
        _ = factory.create_agent("another_agent")

        call_kwargs = mock_agent_class.call_args[1]
        assert "max_iter" in call_kwargs
        assert call_kwargs["max_iter"] == 10

    def test_create_agent_invalid_id(self, temp_agents_file):
        """Should raise ValueError for nonexistent agent_id"""
        factory = AgentFactory(config_path=temp_agents_file)

        with pytest.raises(ValueError) as exc_info:
            factory.create_agent("nonexistent_agent")

        assert "not found in registry" in str(exc_info.value)
        assert "test_agent" in str(exc_info.value)  # Shows available agents


class TestCreateAllAgents:
    """Test creating all agents at once"""

    @patch("scripts.crewai_agents.Agent")
    def test_create_all_agents(self, mock_agent_class, temp_agents_file):
        """Should create all agents from registry"""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        factory = AgentFactory(config_path=temp_agents_file)
        agents = factory.create_all_agents()

        assert len(agents) == 2
        assert "test_agent" in agents
        assert "another_agent" in agents
        assert mock_agent_class.call_count == 2


class TestGetAgentConfig:
    """Test retrieving agent configuration"""

    def test_get_agent_config_valid(self, temp_agents_file):
        """Should return configuration dict for valid agent_id"""
        factory = AgentFactory(config_path=temp_agents_file)
        config = factory.get_agent_config("test_agent")

        assert config["role"] == "Test Agent"
        assert config["goal"] == "Test goal"
        assert config["backstory"] == "Test backstory"
        assert config["verbose"] is True

    def test_get_agent_config_invalid(self, temp_agents_file):
        """Should raise ValueError for invalid agent_id"""
        factory = AgentFactory(config_path=temp_agents_file)

        with pytest.raises(ValueError) as exc_info:
            factory.get_agent_config("nonexistent")

        assert "not found in registry" in str(exc_info.value)

    def test_get_agent_config_returns_copy(self, temp_agents_file):
        """Should return copy of config (not modify original)"""
        factory = AgentFactory(config_path=temp_agents_file)
        config1 = factory.get_agent_config("test_agent")
        config1["role"] = "Modified"

        config2 = factory.get_agent_config("test_agent")
        assert config2["role"] == "Test Agent"  # Original unchanged


class TestListAgents:
    """Test listing available agents"""

    def test_list_agents(self, temp_agents_file):
        """Should return list of all agent IDs"""
        factory = AgentFactory(config_path=temp_agents_file)
        agents = factory.list_agents()

        assert len(agents) == 2
        assert "test_agent" in agents
        assert "another_agent" in agents


class TestCLI:
    """Test CLI functionality"""

    @patch("scripts.crewai_agents.AgentFactory")
    @patch("sys.argv", ["crewai_agents.py", "--list"])
    def test_cli_list_command(self, mock_factory_class, temp_agents_file, capsys):
        """Should list all agents when --list flag used"""
        mock_factory = MagicMock()
        mock_factory.list_agents.return_value = ["agent1", "agent2"]
        mock_factory_class.return_value = mock_factory

        from scripts.crewai_agents import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "agent1" in captured.out
        assert "agent2" in captured.out

    @patch("scripts.crewai_agents.AgentFactory")
    @patch("sys.argv", ["crewai_agents.py", "--show", "test_agent"])
    def test_cli_show_command(self, mock_factory_class, capsys):
        """Should show agent config when --show flag used"""
        mock_factory = MagicMock()
        mock_factory.get_agent_config.return_value = {
            "role": "Test Role",
            "goal": "Test Goal",
            "backstory": "Test Backstory",
            "verbose": True,
            "allow_delegation": False,
        }
        mock_factory_class.return_value = mock_factory

        from scripts.crewai_agents import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Test Role" in captured.out
        assert "Test Goal" in captured.out


class TestRealAgentsYAML:
    """Integration tests with actual schemas/agents.yaml"""

    def test_load_real_agents_yaml(self):
        """Should successfully load schemas/agents.yaml if it exists"""
        agents_yaml = Path(__file__).parent.parent / "schemas" / "agents.yaml"

        if not agents_yaml.exists():
            pytest.skip("schemas/agents.yaml not found")

        factory = AgentFactory()
        assert len(factory.list_agents()) > 0

    @patch("scripts.crewai_agents.Agent")
    def test_create_real_agents(self, mock_agent_class):
        """Should create all real agents successfully"""
        agents_yaml = Path(__file__).parent.parent / "schemas" / "agents.yaml"

        if not agents_yaml.exists():
            pytest.skip("schemas/agents.yaml not found")

        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent

        factory = AgentFactory()
        agents = factory.create_all_agents()

        # Should have 4 agents: research, writer, editor, graphics
        assert len(agents) >= 4
        expected_agents = [
            "research_agent",
            "writer_agent",
            "editor_agent",
            "graphics_agent",
        ]
        for agent_id in expected_agents:
            assert agent_id in agents
