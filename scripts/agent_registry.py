#!/usr/bin/env python3
"""
Agent Registry Pattern Implementation

Implements ADR-002: Central registry for agent discovery and creation.
Loads agent configurations from Markdown files with YAML frontmatter.

Usage:
    from agent_registry import AgentRegistry

    registry = AgentRegistry()
    writer = registry.get_agent("writer-agent")
    all_agents = registry.list_agents()
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from llm_client import create_llm_client

logger = logging.getLogger(__name__)

# CrewAI Tools - REQUIRED dependency
try:
    from crewai_tools import (
        DirectoryReadTool,
        FileReadTool,
        FileWriterTool,
    )
except ImportError as err:
    raise ImportError(
        "CRITICAL: 'crewai-tools' is missing. Run 'pip install crewai-tools'."
    ) from err

# Agile Discipline: Process Compliance System Prompt
# Injected into every agent to enforce Agile team discipline
AGILE_MINDSET = """

YOU ARE AN AGILE TEAM MEMBER.
1. NO TICKET, NO WORK: You must always know which User Story you are serving.
2. DEFINITION OF DONE: You do not consider a task finished until:
   - Code is written.
   - Tests are passed.
   - Documentation is updated.
3. STATUS UPDATES: You must report your progress clearly.
"""


@dataclass
class AgentConfig:
    """Loaded agent configuration from .agent.md file.

    Attributes:
        name: Agent identifier (filename without .agent.md)
        role: Agent's role description
        goal: Agent's primary objective
        backstory: Agent's background context
        system_message: Complete system message/instructions
        tools: List of tool names the agent can use
        metadata: Additional metadata (category, version, etc.)
        scoring_criteria: Optional performance evaluation criteria
    """

    name: str
    role: str
    goal: str
    backstory: str
    system_message: str
    tools: list[str]
    metadata: dict[str, str]
    scoring_criteria: dict[str, str] | None = None


class AgentRegistry:
    """Central registry for agent discovery and creation.

    Loads agent configurations from Markdown files with YAML frontmatter,
    creates LLM clients on-demand, and returns initialized agent instances.

    Attributes:
        agents_dir: Directory containing .agent.md files
        _agents: Internal cache of loaded agent configurations
    """

    def __init__(self, agents_dir: Path = Path(".github/agents")):
        """Initialize the agent registry.

        Args:
            agents_dir: Directory containing .agent.md files
                       (default: .github/agents)

        Raises:
            ValueError: If agents_dir does not exist
        """
        self.agents_dir = agents_dir
        self._agents: dict[str, AgentConfig] = {}

        if not self.agents_dir.exists():
            raise ValueError(f"Agent directory not found: {self.agents_dir}")

        self._load_agents()
        logger.info(f"Loaded {len(self._agents)} agents from {self.agents_dir}")

    def _load_agents(self) -> None:
        """Load all .agent.md files from the agents directory.

        Scans the directory for files matching *.agent.md pattern,
        parses their YAML frontmatter, and caches the configurations.
        """
        for agent_file in self.agents_dir.glob("*.agent.md"):
            try:
                config = self._parse_markdown_frontmatter(agent_file)
                agent_name = agent_file.stem.replace(".agent", "")

                # Build system message from Markdown body
                system_message = self._extract_system_message(agent_file)

                agent_config = AgentConfig(
                    name=agent_name,
                    role=config.get("role", ""),
                    goal=config.get("goal", ""),
                    backstory=config.get("backstory", ""),
                    system_message=system_message,
                    tools=config.get("tools", []),
                    metadata=config.get("metadata", {}),
                    scoring_criteria=config.get("scoring_criteria"),
                )

                self._agents[agent_name] = agent_config
                logger.debug(f"Loaded agent: {agent_name}")

            except Exception as e:
                logger.error(f"Failed to load agent {agent_file}: {e}")
                continue

    def _parse_markdown_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Extract YAML frontmatter from Markdown file.

        Args:
            file_path: Path to .agent.md file

        Returns:
            Dictionary of parsed YAML configuration

        Raises:
            ValueError: If file has no valid frontmatter
        """
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            # No frontmatter, return empty dict for now
            logger.warning(f"No frontmatter found in {file_path}")
            return {}

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid frontmatter format in {file_path}")

        try:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter if frontmatter else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}") from e

    def _extract_system_message(self, file_path: Path) -> str:
        """Extract Markdown body as system message.

        Args:
            file_path: Path to .agent.md file

        Returns:
            Markdown body text (after frontmatter)
        """
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            # No frontmatter, entire content is system message
            return content

        parts = content.split("---", 2)
        if len(parts) >= 3:
            # Return everything after the second --- delimiter
            return parts[2].strip()

        return ""

    def _instantiate_tools(self, tool_names: list[str]) -> list[Any]:
        """Convert tool name strings to actual tool instances.

        Args:
            tool_names: List of tool names from agent config (e.g., ['file_read', 'file_write'])

        Returns:
            List of instantiated CrewAI tool objects

        Raises:
            ValueError: If unknown tool name provided
        """
        # Tool factory mapping
        TOOL_FACTORY = {
            "file_read": FileReadTool,
            "file_write": FileWriterTool,
            "directory_read": DirectoryReadTool,
            # Add more tool mappings here as needed
        }

        instantiated = []
        for tool_name in tool_names:
            # Normalize tool name (handle both file_read and FileReadTool formats)
            normalized = tool_name.lower().replace("tool", "").replace("_tool", "")

            if normalized in TOOL_FACTORY:
                tool_class = TOOL_FACTORY[normalized]
                tool_instance = tool_class()
                instantiated.append(tool_instance)
                logger.debug(f"Instantiated tool: {tool_name} -> {tool_class.__name__}")
            else:
                logger.warning(
                    f"Unknown tool '{tool_name}' requested. "
                    f"Available: {', '.join(TOOL_FACTORY.keys())}"
                )

        return instantiated

    def get_agent(
        self, name: str, model: str | None = None, provider: str | None = None
    ) -> dict[str, Any]:
        """Factory method: Create agent instance with LLM client.

        Args:
            name: Agent name (without .agent.md extension)
            model: LLM model to use (default: provider default)
            provider: LLM provider ('anthropic' or 'openai', default: auto-detect)

        Returns:
            Dictionary containing agent configuration and LLM client:
            {
                'name': str,
                'config': AgentConfig,
                'llm_client': LLMClient,
                'role': str,
                'goal': str,
                'backstory': str,
                'system_message': str,
                'tools': List[str]
            }

        Raises:
            ValueError: If agent not found in registry

        Example:
            >>> registry = AgentRegistry()
            >>> writer = registry.get_agent("writer-agent")
            >>> print(writer['role'])
            'Content Writer specializing in Economist style'
        """
        if name not in self._agents:
            available = ", ".join(self._agents.keys())
            raise ValueError(
                f"Agent '{name}' not found in registry. Available agents: {available}"
            )

        config = self._agents[name]

        # Create LLM client
        llm_client = create_llm_client(provider=provider)

        # Override model if specified
        if model:
            llm_client.model = model
            logger.info(f"Using custom model for {name}: {model}")

        logger.info(f"Created agent instance: {name} with {llm_client.provider}")

        # Inject Agile discipline into backstory (ADR-002: Process Compliance)
        backstory_with_discipline = config.backstory + AGILE_MINDSET

        # Instantiate actual tool objects from string names
        tool_instances = self._instantiate_tools(config.tools)

        return {
            "name": config.name,
            "config": config,
            "llm_client": llm_client,
            "role": config.role,
            "goal": config.goal,
            "backstory": backstory_with_discipline,
            "system_message": config.system_message,
            "tools": tool_instances,  # Now actual tool instances, not strings
        }

    def list_agents(
        self, category: str | None = None, include_metadata: bool = False
    ) -> list[str] | list[dict[str, Any]]:
        """Discover available agents.

        Args:
            category: Filter by metadata category (optional)
            include_metadata: Return full metadata instead of just names

        Returns:
            List of agent names, or list of dicts with metadata if include_metadata=True

        Example:
            >>> registry = AgentRegistry()
            >>> all_agents = registry.list_agents()
            ['po-agent', 'scrum-master', 'writer-agent', ...]

            >>> dev_agents = registry.list_agents(category='development')
            ['refactor-specialist', 'test-writer']

            >>> detailed = registry.list_agents(include_metadata=True)
            [{'name': 'po-agent', 'role': '...', 'category': 'management'}, ...]
        """
        agents = self._agents.values()

        # Filter by category if specified
        if category:
            agents = [
                agent for agent in agents if agent.metadata.get("category") == category
            ]

        # Return full metadata or just names
        if include_metadata:
            return [
                {
                    "name": agent.name,
                    "role": agent.role,
                    "goal": agent.goal,
                    "category": agent.metadata.get("category", "unknown"),
                    "version": agent.metadata.get("version", "1.0"),
                }
                for agent in agents
            ]
        else:
            return [agent.name for agent in agents]

    def reload_agents(self) -> None:
        """Reload all agent configurations from disk.

        Useful for development when agent configurations are modified.
        """
        self._agents.clear()
        self._load_agents()
        logger.info(f"Reloaded {len(self._agents)} agents")

    def get_agent_config(self, name: str) -> AgentConfig:
        """Get raw agent configuration without creating LLM client.

        Args:
            name: Agent name (without .agent.md extension)

        Returns:
            AgentConfig dataclass with all configuration fields

        Raises:
            ValueError: If agent not found in registry

        Example:
            >>> registry = AgentRegistry()
            >>> config = registry.get_agent_config("writer-agent")
            >>> print(config.role)
            'Content Writer specializing in Economist style'
        """
        if name not in self._agents:
            available = ", ".join(self._agents.keys())
            raise ValueError(
                f"Agent '{name}' not found in registry. Available agents: {available}"
            )

        return self._agents[name]


def main() -> None:
    """CLI interface for testing the agent registry."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) > 1:
        agent_name = sys.argv[1]
        registry = AgentRegistry()

        try:
            agent = registry.get_agent(agent_name)
            print(f"\n✅ Successfully loaded agent: {agent_name}")
            print(f"   Role: {agent['role']}")
            print(f"   Goal: {agent['goal']}")
            print(f"   LLM: {agent['llm_client']}")
            print(f"   Tools: {', '.join(agent['tools']) or 'None'}")
        except ValueError as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        # List all agents
        registry = AgentRegistry()
        agents = registry.list_agents(include_metadata=True)

        print(f"\n📋 Available Agents ({len(agents)}):\n")
        for agent in agents:
            print(f"   • {agent['name']}")
            print(f"     Role: {agent['role']}")
            print(f"     Category: {agent.get('category', 'unknown')}")
            print()


if __name__ == "__main__":
    main()
