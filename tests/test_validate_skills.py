"""Tests for ``scripts/validate_skills.py`` — issue #294."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_skills import (
    REQUIRED_SECTIONS,
    discover_skill_files,
    main,
    validate_skill,
)


def _write_skill(tmp_path: Path, name: str, *, body: str | None = None) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    skill = skill_dir / "SKILL.md"
    if body is None:
        body = "\n\n".join(
            f"## {section}\nFiller text." for section in REQUIRED_SECTIONS
        )
    skill.write_text(
        f"---\nname: {name}\ndescription: Use to test the validator.\n---\n\n{body}\n"
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
        body = "\n\n".join(f"## {s}\nFiller." for s in REQUIRED_SECTIONS)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: wrong-name\ndescription: Use to test.\n---\n\n{body}\n"
        )
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("does not match directory" in e for e in report.errors)

    def test_extra_frontmatter_key_rejected(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "extra-key"
        skill_dir.mkdir()
        body = "\n\n".join(f"## {s}\nFiller." for s in REQUIRED_SECTIONS)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: extra-key\n"
            "description: Use to test.\n"
            "version: 1.0\n"
            "---\n\n"
            f"{body}\n"
        )
        report = validate_skill(skill_dir / "SKILL.md")
        assert not report.ok
        assert any("unexpected frontmatter key" in e for e in report.errors)

    def test_missing_section(self, tmp_path: Path) -> None:
        body = "\n\n".join(
            f"## {s}\nFiller." for s in REQUIRED_SECTIONS if s != "Verification"
        )
        skill = _write_skill(tmp_path, "no-verify", body=body)
        report = validate_skill(skill)
        assert not report.ok
        assert any("Verification" in e for e in report.errors)

    def test_subtitled_heading_accepted(self, tmp_path: Path) -> None:
        """`## Core Process: subtitle` should still satisfy the rule."""
        body = []
        for s in REQUIRED_SECTIONS:
            heading = f"## {s}: subtitle here" if s == "Core Process" else f"## {s}"
            body.append(f"{heading}\nFiller.")
        skill = _write_skill(tmp_path, "subtitle", body="\n\n".join(body))
        report = validate_skill(skill)
        assert report.ok, report.errors

    def test_description_without_terminal_punctuation_flagged(
        self, tmp_path: Path
    ) -> None:
        skill_dir = tmp_path / "no-punct"
        skill_dir.mkdir()
        body = "\n\n".join(f"## {s}\nFiller." for s in REQUIRED_SECTIONS)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: no-punct\n"
            "description: A description with no punctuation\n"
            "---\n\n"
            f"{body}\n"
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
        """The repo's own skills must satisfy the validator at all times."""
        rc = main(["skills", "--quiet"])
        assert rc == 0


@pytest.mark.parametrize("section", list(REQUIRED_SECTIONS))
def test_each_required_section_is_load_bearing(tmp_path: Path, section: str) -> None:
    """Removing any single required section should fail validation."""
    body = "\n\n".join(f"## {s}\nFiller." for s in REQUIRED_SECTIONS if s != section)
    skill = _write_skill(tmp_path, "load-bearing", body=body)
    report = validate_skill(skill)
    assert not report.ok
    assert any(section in e for e in report.errors)
