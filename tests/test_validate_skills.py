"""Tests for ``scripts/validate_skills.py`` — issue #294.

Updated to match the addyosmani/agent-skills format: skills use skill-specific
section names (e.g. "The TDD Cycle", "Skill Discovery") so validation checks
minimum section count rather than fixed section names.
"""

from __future__ import annotations

from pathlib import Path

from scripts.validate_skills import (
    MIN_SECTION_COUNT,
    discover_skill_files,
    main,
    validate_skill,
)

# Build a minimal valid body with exactly MIN_SECTION_COUNT sections.
_SECTION_NAMES = [
    "Overview",
    "When to Use",
    "The Core Process",
    "Common Rationalizations",
    "Red Flags",
    "Verification",
]
assert len(_SECTION_NAMES) >= MIN_SECTION_COUNT


def _valid_body() -> str:
    return "\n\n".join(f"## {s}\nFiller text." for s in _SECTION_NAMES)


def _write_skill(tmp_path: Path, name: str, *, body: str | None = None) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        f"---\nname: {name}\ndescription: Use to test the validator.\n---\n\n"
        f"{body if body is not None else _valid_body()}\n",
    )
    return skill


class TestValidateSkill:
    def test_well_formed_skill_passes(self, tmp_path: Path) -> None:
        skill = _write_skill(tmp_path, "good-skill")
        report = validate_skill(skill)
        assert report.ok, report.errors

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "no-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No frontmatter here\n\n## Overview\n")
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("missing YAML frontmatter" in e for e in report.errors)

    def test_name_mismatch(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "actual-dir"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: wrong-name\ndescription: Use to test.\n---\n\n{_valid_body()}\n",
        )
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("does not match directory" in e for e in report.errors)

    def test_extra_frontmatter_key_rejected(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "extra-key"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: extra-key\n"
            "description: Use to test.\n"
            "version: 1.0\n"
            "---\n\n"
            f"{_valid_body()}\n",
        )
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("unexpected frontmatter key" in e for e in report.errors)

    def test_too_few_sections_fails(self, tmp_path: Path) -> None:
        """A skill with fewer than MIN_SECTION_COUNT ## headings should fail."""
        thin_body = "\n\n".join(
            f"## Section {i}\nFiller." for i in range(MIN_SECTION_COUNT - 1)
        )
        skill = _write_skill(tmp_path, "thin-skill", body=thin_body)
        report = validate_skill(skill)
        assert not report.ok
        assert any("too few ## sections" in e for e in report.errors)

    def test_skill_specific_section_names_accepted(self, tmp_path: Path) -> None:
        """Skills can use any section names — e.g. addyosmani originals."""
        body = (
            "## Overview\nSome overview.\n\n"
            "## Skill Discovery\nHow to route tasks.\n\n"
            "## Core Operating Behaviors\nThe six behaviors.\n\n"
            "## Failure Modes to Avoid\nCommon pitfalls.\n\n"
            "## Skill Rules\nThe rules.\n\n"
            "## Quick Reference\nTable of skills."
        )
        skill = _write_skill(tmp_path, "custom-sections", body=body)
        report = validate_skill(skill)
        assert report.ok, report.errors

    def test_description_without_terminal_punctuation_flagged(
        self,
        tmp_path: Path,
    ) -> None:
        skill_dir = tmp_path / "no-punct"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: no-punct\n"
            "description: A description with no punctuation\n"
            "---\n\n"
            f"{_valid_body()}\n",
        )
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("terminal punctuation" in e for e in report.errors)


class TestDiscovery:
    def test_finds_skill_files(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "alpha")
        _write_skill(tmp_path, "beta")
        files = discover_skill_files(tmp_path)
        assert len(files) == 2
        assert all(f.name == "SKILL.md" for f in files)

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        assert discover_skill_files(tmp_path) == []

    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        assert discover_skill_files(tmp_path / "does-not-exist") == []


class TestMainExitCodes:
    def test_zero_exit_when_all_pass(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "good")
        rc = main([str(tmp_path), "--quiet"])
        assert rc == 0

    def test_nonzero_exit_when_any_fails(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "good")
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("no frontmatter\n")
        rc = main([str(tmp_path), "--quiet"])
        assert rc == 1

    def test_two_when_no_skills_found(self, tmp_path: Path, capsys) -> None:
        rc = main([str(tmp_path / "missing"), "--quiet"])
        assert rc == 2

    def test_repo_skills_pass(self) -> None:
        """All 39 repo skills (addyosmani + domain) must satisfy the validator."""
        rc = main(["skills", "--quiet"])
        assert rc == 0


def test_min_section_count_is_enforced(tmp_path: Path) -> None:
    """Exactly MIN_SECTION_COUNT-1 sections fails; MIN_SECTION_COUNT passes."""
    under = "\n\n".join(f"## S{i}\nFiller." for i in range(MIN_SECTION_COUNT - 1))
    at_min = "\n\n".join(f"## S{i}\nFiller." for i in range(MIN_SECTION_COUNT))
    skill_under = _write_skill(tmp_path, "under", body=under)
    skill_at = _write_skill(tmp_path, "at-min", body=at_min)
    assert not validate_skill(skill_under).ok
    assert validate_skill(skill_at).ok
