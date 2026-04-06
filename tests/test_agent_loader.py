"""Unit tests for scripts/agent_loader.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Add scripts dir to path so agent_loader can be imported
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from agent_loader import (
    AGENTS_DIR,
    AgentConfig,
    load_agent,
    load_board_members,
    load_content_agent,
    load_scout_prompts,
    validate_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yaml(tmp_path: Path, extra: dict | None = None) -> Path:
    """Create a minimal valid agent YAML file in tmp_path."""
    data: dict = {
        "name": "Test Agent",
        "role": "Test Role",
        "goal": "Test goal",
        "backstory": "Test backstory",
        "system_message": "You are a test agent.",
        "metadata": {
            "version": "1.0",
            "created": "2026-01-01",
            "author": "test",
            "category": "content_generation",
        },
    }
    if extra:
        data.update(extra)
    p = tmp_path / "test_agent.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True))
    return p


# ---------------------------------------------------------------------------
# test_load_agent_valid
# ---------------------------------------------------------------------------

def test_load_agent_valid(tmp_path: Path) -> None:
    """Loading a valid YAML file returns a populated AgentConfig."""
    yaml_path = _make_yaml(tmp_path)
    config = load_agent(yaml_path)

    assert isinstance(config, AgentConfig)
    assert config.name == "Test Agent"
    assert config.role == "Test Role"
    assert config.system_message == "You are a test agent."
    assert config.weight == 1.0
    assert config.tools == []


def test_load_agent_with_optional_fields(tmp_path: Path) -> None:
    """Optional fields are loaded correctly when present."""
    yaml_path = _make_yaml(tmp_path, {"tools": ["bash", "grep"], "weight": 1.5})
    config = load_agent(yaml_path)

    assert config.tools == ["bash", "grep"]
    assert config.weight == 1.5


# ---------------------------------------------------------------------------
# test_load_agent_invalid_missing_required_field
# ---------------------------------------------------------------------------

def test_load_agent_invalid_missing_required_field(tmp_path: Path) -> None:
    """YAML missing a required field raises ValueError."""
    data = {
        "name": "Incomplete Agent",
        # missing role, goal, backstory, system_message, metadata
    }
    p = tmp_path / "bad_agent.yaml"
    p.write_text(yaml.dump(data))

    with pytest.raises(ValueError, match="missing required fields"):
        load_agent(p)


def test_load_agent_file_not_found() -> None:
    """Non-existent YAML path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Agent YAML not found"):
        load_agent(Path("/nonexistent/path/agent.yaml"))


# ---------------------------------------------------------------------------
# test_load_board_members_returns_all_six
# ---------------------------------------------------------------------------

def test_load_board_members_returns_all_six() -> None:
    """load_board_members returns exactly 6 board member entries."""
    members = load_board_members()
    assert len(members) == 6


# ---------------------------------------------------------------------------
# test_load_board_members_has_correct_keys
# ---------------------------------------------------------------------------

def test_load_board_members_has_correct_keys() -> None:
    """Each board member dict has name, weight, and prompt keys."""
    members = load_board_members()
    expected_slugs = {
        "vp_engineering",
        "senior_qe_lead",
        "data_skeptic",
        "career_climber",
        "economist_editor",
        "busy_reader",
    }
    assert set(members.keys()) == expected_slugs

    for slug, member in members.items():
        assert "name" in member, f"{slug} missing 'name'"
        assert "weight" in member, f"{slug} missing 'weight'"
        assert "prompt" in member, f"{slug} missing 'prompt'"
        assert isinstance(member["weight"], float), f"{slug} weight should be float"
        assert len(member["prompt"]) > 10, f"{slug} prompt is too short"


def test_load_board_members_weights_correct() -> None:
    """Board member weights match the original hardcoded values."""
    members = load_board_members()
    assert members["vp_engineering"]["weight"] == pytest.approx(1.2)
    assert members["senior_qe_lead"]["weight"] == pytest.approx(1.0)
    assert members["data_skeptic"]["weight"] == pytest.approx(1.1)
    assert members["career_climber"]["weight"] == pytest.approx(0.8)
    assert members["economist_editor"]["weight"] == pytest.approx(1.3)
    assert members["busy_reader"]["weight"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# test_load_scout_prompts_returns_both
# ---------------------------------------------------------------------------

def test_load_scout_prompts_returns_both() -> None:
    """load_scout_prompts returns both 'scout' and 'trend' keys."""
    prompts = load_scout_prompts()
    assert "scout" in prompts
    assert "trend" in prompts
    assert len(prompts["scout"]) > 100
    assert len(prompts["trend"]) > 100


def test_load_scout_prompts_content() -> None:
    """Scout prompt contains expected content markers."""
    prompts = load_scout_prompts()
    assert "Topic Scout" in prompts["scout"]
    assert "quality engineering" in prompts["scout"].lower()
    assert "trends" in prompts["trend"].lower()


# ---------------------------------------------------------------------------
# test_load_content_agent_researcher
# ---------------------------------------------------------------------------

def test_load_content_agent_researcher() -> None:
    """load_content_agent('researcher') returns a valid AgentConfig."""
    config = load_content_agent("researcher")
    assert isinstance(config, AgentConfig)
    assert config.name
    assert "Research" in config.name or "research" in config.system_message.lower()
    assert len(config.system_message) > 100


def test_load_content_agent_writer() -> None:
    """load_content_agent('writer') returns a valid AgentConfig."""
    config = load_content_agent("writer")
    assert isinstance(config, AgentConfig)
    assert len(config.system_message) > 100


def test_load_content_agent_editor() -> None:
    """load_content_agent('editor') returns a valid AgentConfig."""
    config = load_content_agent("editor")
    assert isinstance(config, AgentConfig)
    assert len(config.system_message) > 100


def test_load_content_agent_graphics() -> None:
    """load_content_agent('graphics') returns a valid AgentConfig."""
    config = load_content_agent("graphics")
    assert isinstance(config, AgentConfig)
    assert len(config.system_message) > 100


def test_load_content_agent_invalid_name() -> None:
    """load_content_agent with unknown name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown content agent"):
        load_content_agent("nonexistent")


# ---------------------------------------------------------------------------
# test_schema_validation_rejects_invalid
# ---------------------------------------------------------------------------

def test_schema_validation_rejects_invalid(tmp_path: Path) -> None:
    """Schema validation rejects a YAML missing the metadata object."""
    data = {
        "name": "Bad Agent",
        "role": "Bad Role",
        "goal": "Bad goal",
        "backstory": "Bad backstory",
        "system_message": "You are bad.",
        # metadata missing entirely
    }
    p = tmp_path / "bad_metadata.yaml"
    p.write_text(yaml.dump(data))

    with pytest.raises((ValueError, Exception)):
        load_agent(p)


# ---------------------------------------------------------------------------
# test_all_eleven_agents_load
# ---------------------------------------------------------------------------

def test_all_eleven_agents_load() -> None:
    """All 11 agent YAML files can be loaded without error."""
    expected_yamls = [
        AGENTS_DIR / "discovery" / "topic_scout.yaml",
        AGENTS_DIR / "editorial_board" / "vp_engineering.yaml",
        AGENTS_DIR / "editorial_board" / "senior_qe_lead.yaml",
        AGENTS_DIR / "editorial_board" / "data_skeptic.yaml",
        AGENTS_DIR / "editorial_board" / "career_climber.yaml",
        AGENTS_DIR / "editorial_board" / "economist_editor.yaml",
        AGENTS_DIR / "editorial_board" / "busy_reader.yaml",
        AGENTS_DIR / "content_generation" / "researcher.yaml",
        AGENTS_DIR / "content_generation" / "writer.yaml",
        AGENTS_DIR / "content_generation" / "editor.yaml",
        AGENTS_DIR / "content_generation" / "graphics.yaml",
    ]

    assert len(expected_yamls) == 11

    for yaml_path in expected_yamls:
        assert yaml_path.exists(), f"Missing: {yaml_path}"
        config = load_agent(yaml_path)
        assert isinstance(config, AgentConfig), f"Failed to load: {yaml_path}"
        assert config.system_message, f"Empty system_message in: {yaml_path}"


# ---------------------------------------------------------------------------
# validate_all integration test
# ---------------------------------------------------------------------------

def test_validate_all_succeeds() -> None:
    """validate_all() returns True when all YAML files are valid."""
    result = validate_all()
    assert result is True


# ---------------------------------------------------------------------------
# Backward-compatibility checks
# ---------------------------------------------------------------------------

def test_board_members_backward_compatible() -> None:
    """Board member prompts contain personas matching original hardcoded content."""
    members = load_board_members()

    vp = members["vp_engineering"]
    assert "VP of Engineering" in vp["prompt"]
    assert "Series C" in vp["prompt"]

    editor = members["economist_editor"]
    assert "Economist" in editor["prompt"]
    assert editor["weight"] == pytest.approx(1.3)


def test_scout_prompts_backward_compatible() -> None:
    """Scout prompts contain key phrases from original hardcoded constants."""
    prompts = load_scout_prompts()

    # SCOUT_AGENT_PROMPT markers
    assert "EVALUATION CRITERIA" in prompts["scout"]
    assert "OUTPUT FORMAT" in prompts["scout"]

    # TREND_RESEARCH_PROMPT markers
    assert "testing tool vendors" in prompts["trend"]
    assert "QE communities" in prompts["trend"]


def test_research_prompt_backward_compatible() -> None:
    """Research agent prompt contains key constraint text."""
    config = load_content_agent("researcher")
    assert "CRITICAL RULES" in config.system_message
    assert "[UNVERIFIED]" in config.system_message
    assert "SOURCE DIVERSITY" in config.system_message


def test_writer_prompt_has_format_placeholders() -> None:
    """Writer prompt preserves {current_date} and {research_brief} placeholders."""
    config = load_content_agent("writer")
    assert "{current_date}" in config.system_message
    assert "{research_brief}" in config.system_message


def test_editor_prompt_has_format_placeholders() -> None:
    """Editor prompt preserves {draft} and {current_date} placeholders."""
    config = load_content_agent("editor")
    assert "{draft}" in config.system_message
    assert "{current_date}" in config.system_message


def test_graphics_prompt_has_chart_spec_placeholder() -> None:
    """Graphics prompt preserves {chart_spec} placeholder."""
    config = load_content_agent("graphics")
    assert "{chart_spec}" in config.system_message
