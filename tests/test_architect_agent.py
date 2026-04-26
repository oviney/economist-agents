"""Tests for the AI Architect agent definition.

STORY-055 acceptance criteria covered:
- Agent definition under ``.github/agents/architect.agent.md`` parses cleanly
  via the YAML+Markdown contract used by ``scripts/agent_registry``.
- Required frontmatter fields are present.
- Body documents the rubric, ADR usage, and an explicit output contract.
- The agent's backing skill (``skills/architecture-patterns``) exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHITECT_FILE = REPO_ROOT / ".github" / "agents" / "architect.agent.md"
SKILL_FILE = REPO_ROOT / "skills" / "architecture-patterns" / "SKILL.md"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2].strip()


@pytest.fixture(scope="module")
def architect_file() -> Path:
    assert ARCHITECT_FILE.exists(), f"architect agent file missing: {ARCHITECT_FILE}"
    return ARCHITECT_FILE


@pytest.fixture(scope="module")
def architect_parsed(architect_file: Path) -> tuple[dict, str]:
    return _parse_frontmatter(architect_file.read_text(encoding="utf-8"))


class TestArchitectFrontmatter:
    """The frontmatter satisfies the registry contract."""

    def test_has_frontmatter(self, architect_parsed: tuple[dict, str]) -> None:
        fm, _ = architect_parsed
        assert fm, "architect agent must have YAML frontmatter"

    @pytest.mark.parametrize(
        "field", ["name", "description", "model", "tools", "skills"]
    )
    def test_required_field_present(
        self, architect_parsed: tuple[dict, str], field: str
    ) -> None:
        fm, _ = architect_parsed
        assert field in fm, f"frontmatter must include '{field}'"

    def test_name_is_architect(self, architect_parsed: tuple[dict, str]) -> None:
        fm, _ = architect_parsed
        assert fm["name"] == "architect"

    def test_tools_is_nonempty_list(self, architect_parsed: tuple[dict, str]) -> None:
        fm, _ = architect_parsed
        tools = fm.get("tools")
        assert isinstance(tools, list) and tools, "tools must be a non-empty list"

    def test_skills_includes_architecture_patterns(
        self, architect_parsed: tuple[dict, str]
    ) -> None:
        fm, _ = architect_parsed
        skills = fm.get("skills") or []
        joined = " ".join(str(s) for s in skills)
        assert "architecture-patterns" in joined


class TestArchitectBody:
    """The body documents the rubric, ADR usage, and an output contract."""

    @pytest.mark.parametrize(
        "section_keyword",
        ["role", "rubric", "adr", "output", "boundaries"],
    )
    def test_body_mentions(
        self, architect_parsed: tuple[dict, str], section_keyword: str
    ) -> None:
        _, body = architect_parsed
        assert section_keyword in body.lower(), (
            f"architect body must mention '{section_keyword}'"
        )

    def test_body_includes_json_output_example(
        self, architect_parsed: tuple[dict, str]
    ) -> None:
        _, body = architect_parsed
        assert "```json" in body, (
            "architect must document an explicit JSON output contract"
        )

    def test_body_includes_mermaid_or_diagram(
        self, architect_parsed: tuple[dict, str]
    ) -> None:
        _, body = architect_parsed
        assert "```mermaid" in body or "diagram" in body.lower()


class TestArchitectureSkill:
    """The backing skill file exists and parses."""

    def test_skill_file_exists(self) -> None:
        assert SKILL_FILE.exists(), f"missing skill file: {SKILL_FILE}"

    def test_skill_has_frontmatter(self) -> None:
        text = SKILL_FILE.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        assert fm.get("name") == "architecture-patterns"
        assert fm.get("description")
        assert body, "skill body must not be empty"

    def test_skill_documents_rubric(self) -> None:
        body = SKILL_FILE.read_text(encoding="utf-8").lower()
        for token in ("rubric", "frontmatter", "tool", "skill", "85"):
            assert token in body, f"skill must document '{token}'"
