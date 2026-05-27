"""Acceptance tests for STORY-055 AI Architect agent."""

from pathlib import Path
from typing import Any

import yaml

from scripts.agent_registry import AgentRegistry

AGENT_PATH = Path(".github/agents/architect.agent.md")


def _frontmatter() -> dict[str, Any]:
    content = AGENT_PATH.read_text(encoding="utf-8")
    assert content.startswith("---")
    return yaml.safe_load(content.split("---", 2)[1])


def test_architect_agent_is_discoverable() -> None:
    """The AI Architect must be available through AgentRegistry."""
    registry = AgentRegistry()

    assert "architect" in registry.list_agents()
    config = registry.get_agent_config("architect")
    assert config.role == "Agentic AI Architect"
    assert "design and validate multi-agent systems" in config.goal
    assert "CrewAI" in config.backstory
    assert "AutoGen" in config.backstory


def test_architect_agent_exposes_extended_configuration() -> None:
    """STORY-055 requires reasoning, skills, and knowledge sources."""
    registry = AgentRegistry()
    config = registry.get_agent_config("architect")

    assert config.reasoning is True
    assert "skills/agent-architecture" in config.skills
    assert "skills/adr-governance" in config.skills
    assert "docs/adr/0006-agent-framework-selection.md" in config.knowledge_sources
    assert "docs/ARCHITECTURE_PATTERNS.md" in config.knowledge_sources

    for source in config.skills + config.knowledge_sources:
        assert Path(source).exists(), f"Referenced source does not exist: {source}"


def test_architect_prompt_covers_story_acceptance_criteria() -> None:
    """The system prompt must encode the backlog acceptance criteria."""
    config = AgentRegistry().get_agent_config("architect")
    prompt = config.system_message
    prompt_lower = prompt.lower()

    required_phrases = [
        "c4",
        "mermaid",
        "adr",
        "role, goal, backstory, tools",
        "bottlenecks",
        "trade-offs",
        "risk assessment",
        "architecture compliance score",
        ">85%",
        "security implications",
        "credential management",
        "under 30 minutes",
        "do not reinvent",
        "crewai",
        "autogen",
        "agent sdk",
    ]

    for phrase in required_phrases:
        assert phrase in prompt_lower


def test_architect_frontmatter_has_registry_metadata() -> None:
    """The raw agent definition should carry registry metadata."""
    data = _frontmatter()

    assert data["name"] == "architect"
    assert data["model"] == "claude-sonnet-4-20250514"
    assert data["reasoning"] is True
    assert data["metadata"]["category"] == "architecture"
    assert set(data["tools"]) == {"bash", "file_search"}
