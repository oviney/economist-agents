"""Tests for ``scripts/validate_skills.py`` (GitHub issue #294).

Covers:
- Validation contract (frontmatter, name match, required sections).
- Real corpus passes 100%.
- Subtitled "Core Process" headings accepted.
- CLI exit codes and output shapes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_skills as vs  # noqa: E402

REAL_SKILLS_DIR = REPO_ROOT / "skills"

VALID_FRONTMATTER = """\
---
name: example
description: Use when configuring the example agent.
---

"""

ALL_SECTIONS = """\
## Overview

Body.

## When to Use

- bullet

## Core Process

Step 1.

## Common Rationalizations

| A | B |
|---|---|
| x | y |

## Red Flags

- thing

## Verification

- run pytest
"""


def _write_skill(tmp_path: Path, dirname: str, content: str) -> Path:
    """Helper: create a tmp skill dir + SKILL.md with given content."""
    d = tmp_path / dirname
    d.mkdir()
    skill_md = d / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    return skill_md


class TestRealCorpus:
    """The repo's own skills/ must pass the validator unchanged."""

    @pytest.fixture(scope="class")
    def results(self) -> list[vs.SkillValidationResult]:
        return vs.validate_skills_dir(REAL_SKILLS_DIR)

    def test_corpus_size_reasonable(
        self, results: list[vs.SkillValidationResult]
    ) -> None:
        assert len(results) >= 17

    def test_every_skill_passes(
        self, results: list[vs.SkillValidationResult]
    ) -> None:
        failing = [r for r in results if not r.passed]
        assert not failing, "\n".join(
            f"{r.name}: {r.errors}" for r in failing
        )


class TestFrontmatter:
    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        sm = _write_skill(tmp_path, "no-fm", "# No frontmatter here\n" + ALL_SECTIONS)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any("frontmatter" in e for e in result.errors)

    def test_unparseable_frontmatter_fails(self, tmp_path: Path) -> None:
        sm = _write_skill(
            tmp_path, "bad-fm", "---\nname: [unclosed\n---\n\n" + ALL_SECTIONS
        )
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any("frontmatter" in e for e in result.errors)

    @pytest.mark.parametrize("missing", ["name", "description"])
    def test_missing_required_key(self, tmp_path: Path, missing: str) -> None:
        keys = {"name": "miss-key", "description": "Use when X."}
        del keys[missing]
        fm = "---\n" + "\n".join(f"{k}: {v}" for k, v in keys.items()) + "\n---\n\n"
        sm = _write_skill(tmp_path, "miss-key", fm + ALL_SECTIONS)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any(missing in e for e in result.errors)

    def test_empty_description_fails(self, tmp_path: Path) -> None:
        fm = "---\nname: empty-desc\ndescription:\n---\n\n"
        sm = _write_skill(tmp_path, "empty-desc", fm + ALL_SECTIONS)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any("description" in e for e in result.errors)


class TestNameMatchesDirectory:
    def test_name_mismatch_fails(self, tmp_path: Path) -> None:
        fm = "---\nname: wrong-name\ndescription: Use when X.\n---\n\n"
        sm = _write_skill(tmp_path, "actual-dir", fm + ALL_SECTIONS)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any("does not match directory" in e for e in result.errors)

    def test_name_match_passes(self, tmp_path: Path) -> None:
        fm = "---\nname: my-skill\ndescription: Use when X.\n---\n\n"
        sm = _write_skill(tmp_path, "my-skill", fm + ALL_SECTIONS)
        result = vs.validate_skill(sm)
        assert result.passed, result.errors


class TestRequiredSections:
    @pytest.mark.parametrize(
        "section",
        [
            "Overview",
            "When to Use",
            "Core Process",
            "Common Rationalizations",
            "Red Flags",
            "Verification",
        ],
    )
    def test_missing_section_fails(self, tmp_path: Path, section: str) -> None:
        body = ALL_SECTIONS.replace(f"## {section}", f"## NOT-{section}")
        fm = "---\nname: missing-sec\ndescription: x\n---\n\n"
        sm = _write_skill(tmp_path, "missing-sec", fm + body)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any(section in e for e in result.errors)

    def test_core_process_subtitle_accepted(self, tmp_path: Path) -> None:
        """`## Core Process: The 10 Rules` must be accepted (prefix match)."""
        body = ALL_SECTIONS.replace(
            "## Core Process", "## Core Process: The 10 Rules"
        )
        fm = "---\nname: subtitle\ndescription: x\n---\n\n"
        sm = _write_skill(tmp_path, "subtitle", fm + body)
        result = vs.validate_skill(sm)
        assert result.passed, result.errors

    def test_core_without_process_keyword_fails(self, tmp_path: Path) -> None:
        """`## Core Patterns` is NOT accepted — must be `Core Process`."""
        body = ALL_SECTIONS.replace("## Core Process", "## Core Patterns")
        fm = "---\nname: only-patterns\ndescription: x\n---\n\n"
        sm = _write_skill(tmp_path, "only-patterns", fm + body)
        result = vs.validate_skill(sm)
        assert not result.passed
        assert any("Core Process" in e for e in result.errors)


class TestReporting:
    def test_text_report_summary_counts(self, tmp_path: Path) -> None:
        good_fm = "---\nname: good\ndescription: x\n---\n\n"
        _write_skill(tmp_path, "good", good_fm + ALL_SECTIONS)
        bad_fm = "---\nname: bad\ndescription: x\n---\n\n"
        _write_skill(tmp_path, "bad", bad_fm + "## Overview\n\nbody\n")
        results = vs.validate_skills_dir(tmp_path)
        report = vs.render_text_report(results)
        assert "1 passed, 1 failed" in report
        assert "✓ good" in report
        assert "✗ bad" in report

    def test_json_report_round_trip(self, tmp_path: Path) -> None:
        fm = "---\nname: rt\ndescription: x\n---\n\n"
        _write_skill(tmp_path, "rt", fm + ALL_SECTIONS)
        results = vs.validate_skills_dir(tmp_path)
        loaded = json.loads(vs.render_json_report(results))
        assert isinstance(loaded, list) and len(loaded) == 1
        assert loaded[0]["name"] == "rt"
        assert loaded[0]["passed"] is True


class TestEdgeCases:
    def test_missing_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            vs.validate_skills_dir(tmp_path / "does-not-exist")

    def test_empty_skills_dir_returns_empty(self, tmp_path: Path) -> None:
        # No skill subdirs — validator should return empty list, not error.
        results = vs.validate_skills_dir(tmp_path)
        assert results == []
