#!/usr/bin/env python3
"""
CrewAI Agent Factory

Generates CrewAI Agent instances from declarative YAML configurations.
Part of Phase 1: CrewAI Migration (ADR-003).

This module bridges our existing agent system with CrewAI framework:
- Loads agent configurations from schemas/agents.yaml
- Creates CrewAI Agent instances with role/goal/backstory
- Enables declarative agent management for Stage 3 migration

Usage:
    from scripts.crewai_agents import AgentFactory

    factory = AgentFactory()
    research_agent = factory.create_agent('research_agent')
    writer_agent = factory.create_agent('writer_agent')

CLI:
    python scripts/crewai_agents.py --list
    python scripts/crewai_agents.py --create research_agent
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# CrewAI is optional - delay import to avoid breaking pytest collection
Agent = None
try:
    from crewai import Agent
except ImportError:
    pass  # CrewAI not installed - will error if AgentFactory is actually used


class AgentFactory:
    """Factory for creating CrewAI agents from YAML configurations"""

    def __init__(self, config_path: str | None = None):
        """
        Initialize factory with agent registry.

        Args:
            config_path: Path to agents.yaml (default: schemas/agents.yaml)

        Raises:
            ImportError: If CrewAI is not installed
            FileNotFoundError: If agents.yaml not found
            yaml.YAMLError: If agents.yaml is malformed
        """
        if Agent is None:
            raise ImportError(
                "CrewAI not installed. Install with: pip install crewai crewai-tools"
            )

        if config_path is None:
            # Default: schemas/agents.yaml relative to this script
            self.config_path = Path(__file__).parent.parent / "schemas" / "agents.yaml"
        else:
            self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent registry not found: {self.config_path}\n"
                f"Expected location: schemas/agents.yaml\n"
                f"Create this file with agent definitions (see ADR-003)"
            )

        # Load and validate YAML
        try:
            with open(self.config_path) as f:
                self.registry = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Malformed agents.yaml: {e}\n"
                f"File: {self.config_path}\n"
                f"Fix YAML syntax errors and try again"
            ) from e

        if not self.registry or "agents" not in self.registry:
            raise ValueError(
                f"Invalid agents.yaml structure: missing 'agents' key\n"
                f"File: {self.config_path}\n"
                f"Expected format:\n"
                f"agents:\n"
                f"  agent_id:\n"
                f"    role: ...\n"
                f"    goal: ...\n"
                f"    backstory: ..."
            )

        self.agents = self.registry["agents"]

    def create_agent(self, agent_id: str, **kwargs: Any) -> Agent:
        """
        Create a CrewAI Agent instance from registry configuration.

        Args:
            agent_id: Agent identifier from agents.yaml (e.g., 'research_agent')
            **kwargs: Override any agent properties (role, goal, backstory, etc.)

        Returns:
            CrewAI Agent instance configured from YAML + overrides

        Raises:
            ValueError: If agent_id not found in registry

        Example:
            >>> factory = AgentFactory()
            >>> agent = factory.create_agent('research_agent', verbose=False)
            >>> print(agent.role)
            Quality Engineering Research Analyst
        """
        if agent_id not in self.agents:
            available = ", ".join(self.agents.keys())
            raise ValueError(
                f"Agent '{agent_id}' not found in registry\n"
                f"Available agents: {available}\n"
                f"File: {self.config_path}"
            )

        config = self.agents[agent_id].copy()

        # Apply overrides
        config.update(kwargs)

        # Extract CrewAI Agent parameters
        agent_params = {
            "role": config.get("role"),
            "goal": config.get("goal"),
            "backstory": config.get("backstory"),
            "verbose": config.get("verbose", True),
            "allow_delegation": config.get("allow_delegation", False),
        }

        # Add optional parameters if present
        if "tools" in config:
            agent_params["tools"] = config["tools"]
        if "max_iter" in config:
            agent_params["max_iter"] = config["max_iter"]
        if "max_rpm" in config:
            agent_params["max_rpm"] = config["max_rpm"]

        return Agent(**agent_params)

    def create_all_agents(self) -> dict[str, Agent]:
        """
        Create all agents defined in registry.

        Returns:
            Dict mapping agent_id to Agent instance

        Example:
            >>> factory = AgentFactory()
            >>> agents = factory.create_all_agents()
            >>> print(list(agents.keys()))
            ['research_agent', 'writer_agent', 'editor_agent', 'graphics_agent']
        """
        return {agent_id: self.create_agent(agent_id) for agent_id in self.agents}

    def get_agent_config(self, agent_id: str) -> dict[str, Any]:
        """
        Get raw configuration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent configuration dict from YAML

        Raises:
            ValueError: If agent_id not found in registry

        Example:
            >>> factory = AgentFactory()
            >>> config = factory.get_agent_config('research_agent')
            >>> print(config['role'])
            Quality Engineering Research Analyst
        """
        if agent_id not in self.agents:
            available = ", ".join(self.agents.keys())
            raise ValueError(
                f"Agent '{agent_id}' not found in registry\n"
                f"Available agents: {available}"
            )

        return self.agents[agent_id].copy()

    def list_agents(self) -> list[str]:
        """
        List all agent IDs in registry.

        Returns:
            List of agent identifiers

        Example:
            >>> factory = AgentFactory()
            >>> print(factory.list_agents())
            ['research_agent', 'writer_agent', 'editor_agent', 'graphics_agent']
        """
        return list(self.agents.keys())


def main() -> None:
    """CLI entry point for agent factory"""
    parser = argparse.ArgumentParser(
        description="CrewAI Agent Factory - Create agents from YAML registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available agents
  python scripts/crewai_agents.py --list

  # Show configuration for specific agent
  python scripts/crewai_agents.py --show research_agent

  # Create agent (validates configuration)
  python scripts/crewai_agents.py --create research_agent
        """,
    )

    parser.add_argument(
        "--list", action="store_true", help="List all agent IDs in registry"
    )
    parser.add_argument(
        "--show", metavar="AGENT_ID", help="Show configuration for agent"
    )
    parser.add_argument(
        "--create", metavar="AGENT_ID", help="Create agent (validates config)"
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to agents.yaml (default: schemas/agents.yaml)",
    )

    args = parser.parse_args()

    try:
        factory = AgentFactory(config_path=args.config)

        if args.list:
            print("Available agents:")
            for agent_id in factory.list_agents():
                print(f"  - {agent_id}")
            sys.exit(0)

        if args.show:
            config = factory.get_agent_config(args.show)
            print(f"\nAgent: {args.show}")
            print(f"Role: {config['role']}")
            print(f"Goal: {config['goal']}")
            print(f"\nBackstory:\n{config['backstory']}")
            print(f"\nVerbose: {config.get('verbose', True)}")
            print(f"Allow Delegation: {config.get('allow_delegation', False)}")
            sys.exit(0)

        if args.create:
            agent = factory.create_agent(args.create)
            print(f"✅ Created agent: {args.create}")
            print(f"   Role: {agent.role}")
            print(f"   Goal: {agent.goal[:80]}...")
            sys.exit(0)

        # No arguments - show help
        parser.print_help()
        sys.exit(1)

    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
