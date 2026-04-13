#!/usr/bin/env python3
"""Agent Loader Module.

Loads agent configurations from YAML files and provides backward-compatible
constants for existing code (SCOUT_AGENT_PROMPT, BOARD_MEMBERS, etc.).

Usage:
    from agent_loader import load_agent, load_board_members, load_scout_prompts
    from agent_loader import load_content_agent

CLI:
    python scripts/agent_loader.py --validate
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).parent.parent / "agents"
SCHEMA_PATH = AGENTS_DIR / "schema.json"

# Map editorial board YAML filenames to BOARD_MEMBERS dict keys
_BOARD_MEMBER_MAP: dict[str, str] = {
    "vp_engineering": "vp_engineering",
    "senior_qe_lead": "senior_qe_lead",
    "data_skeptic": "data_skeptic",
    "career_climber": "career_climber",
    "economist_editor": "economist_editor",
    "busy_reader": "busy_reader",
}


@dataclass
class AgentConfig:
    """Parsed and validated agent configuration.

    Attributes:
        name: Human-readable agent name.
        role: Short role title.
        goal: Primary goal the agent pursues.
        backstory: Background context for the agent persona.
        system_message: Full system prompt sent to the LLM.
        tools: List of tool names available to this agent.
        weight: Voting weight for editorial board agents (default 1.0).
        metadata: Metadata dict with version, created, author, category.
    """

    name: str
    role: str
    goal: str
    backstory: str
    system_message: str
    tools: list[str] = field(default_factory=list)
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _load_schema() -> dict[str, Any] | None:
    """Load the JSON Schema from disk, returning None if unavailable.

    Returns:
        Parsed schema dict, or None if schema file is missing or jsonschema
        is not installed.
    """
    try:
        import json

        import jsonschema  # noqa: F401 — just checking availability

        if not SCHEMA_PATH.exists():
            logger.warning(
                "Schema file not found at %s — skipping validation", SCHEMA_PATH
            )
            return None

        with SCHEMA_PATH.open() as f:
            return json.load(f)
    except ImportError:
        logger.warning("jsonschema not installed — skipping schema validation")
        return None


def _validate_against_schema(data: dict[str, Any], yaml_path: Path) -> None:
    """Validate agent data against the JSON Schema.

    Args:
        data: Parsed YAML data dict.
        yaml_path: Source path (used in error messages).

    Raises:
        ValueError: If the data fails schema validation.
    """
    schema = _load_schema()
    if schema is None:
        return

    try:
        import jsonschema

        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(
            f"Agent config '{yaml_path}' failed schema validation: {exc.message}"
        ) from exc


def load_agent(yaml_path: Path | str) -> AgentConfig:
    """Load and validate a single agent YAML file.

    Args:
        yaml_path: Path to the agent YAML file.

    Returns:
        Populated AgentConfig dataclass.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the YAML is missing required fields or fails schema validation.
    """
    path = Path(yaml_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Agent YAML not found: {path}. "
            "Ensure the file exists under agents/<category>/<name>.yaml"
        )

    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    # Required field check (fast feedback before jsonschema)
    required = ("name", "role", "goal", "backstory", "system_message")
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise ValueError(f"Agent config '{path}' is missing required fields: {missing}")

    _validate_against_schema(data, path)

    return AgentConfig(
        name=data["name"],
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        system_message=data["system_message"],
        tools=data.get("tools") or [],
        weight=float(data.get("weight", 1.0)),
        metadata=data.get("metadata") or {},
    )


def load_board_members() -> dict[str, dict[str, Any]]:
    """Load all editorial board members as a BOARD_MEMBERS-compatible dict.

    Returns a dict keyed by member slug (e.g. ``"vp_engineering"``) where each
    value has the same structure that the original hardcoded ``BOARD_MEMBERS``
    dict used::

        {
            "vp_engineering": {
                "name": "The VP of Engineering",
                "weight": 1.2,
                "prompt": "You are a VP of Engineering..."
            },
            ...
        }

    Returns:
        Dict of board member configs keyed by slug.

    Raises:
        FileNotFoundError: If any board member YAML is missing.
    """
    board_dir = AGENTS_DIR / "editorial_board"
    result: dict[str, dict[str, Any]] = {}

    for slug in _BOARD_MEMBER_MAP:
        yaml_path = board_dir / f"{slug}.yaml"
        config = load_agent(yaml_path)
        result[slug] = {
            "name": config.name,
            "weight": config.weight,
            "prompt": config.system_message,
        }

    logger.debug("Loaded %d editorial board members", len(result))
    return result


def load_scout_prompts() -> dict[str, str]:
    """Load topic scout prompts from YAML.

    Returns:
        Dict with keys ``"scout"`` (SCOUT_AGENT_PROMPT) and ``"trend"``
        (TREND_RESEARCH_PROMPT), matching the original module-level constants.

    Raises:
        FileNotFoundError: If topic_scout.yaml is missing.
        ValueError: If required prompt fields are absent.
    """
    yaml_path = AGENTS_DIR / "discovery" / "topic_scout.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Topic scout YAML not found: {yaml_path}")

    with yaml_path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    scout_prompt = data.get("system_message", "")
    trend_prompt = data.get("trend_system_message", "")

    if not scout_prompt:
        raise ValueError("topic_scout.yaml missing 'system_message' field")
    if not trend_prompt:
        raise ValueError("topic_scout.yaml missing 'trend_system_message' field")

    return {"scout": scout_prompt, "trend": trend_prompt}


def load_content_agent(agent_name: str) -> AgentConfig:
    """Load a content generation agent by name.

    Args:
        agent_name: One of ``"researcher"``, ``"writer"``, ``"editor"``,
            or ``"graphics"``.

    Returns:
        Populated AgentConfig for the requested agent.

    Raises:
        ValueError: If agent_name is not a recognised content agent.
        FileNotFoundError: If the corresponding YAML file is missing.
    """
    valid_names = ("researcher", "writer", "editor", "graphics")
    if agent_name not in valid_names:
        raise ValueError(
            f"Unknown content agent '{agent_name}'. Valid names: {valid_names}"
        )

    yaml_path = AGENTS_DIR / "content_generation" / f"{agent_name}.yaml"
    return load_agent(yaml_path)


def validate_all() -> bool:
    """Validate every agent YAML file against the schema.

    Returns:
        True if all files are valid, False if any errors were found.
    """
    all_valid = True
    errors: list[str] = []

    yaml_files = list(AGENTS_DIR.rglob("*.yaml"))
    if not yaml_files:
        logger.warning("No YAML files found under %s", AGENTS_DIR)
        return True

    for yaml_path in sorted(yaml_files):
        try:
            load_agent(yaml_path)
            logger.info("✓ %s", yaml_path.relative_to(AGENTS_DIR.parent))
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"✗ {yaml_path.relative_to(AGENTS_DIR.parent)}: {exc}")
            all_valid = False

    if errors:
        for err in errors:
            logger.error(err)
        print(f"\n{len(errors)} validation error(s) found.", file=sys.stderr)
    else:
        print(f"All {len(yaml_files)} agent YAML file(s) are valid.")

    return all_valid


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Agent YAML loader and validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate all agent YAML files against the schema and exit",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    if args.validate:
        success = validate_all()
        sys.exit(0 if success else 1)
    else:
        print("Use --validate to validate all agent YAML files.")
        sys.exit(0)
