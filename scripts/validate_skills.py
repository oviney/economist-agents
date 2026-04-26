#!/usr/bin/env python3
"""Skill format validator (GitHub issue #294).

Checks every ``skills/<name>/SKILL.md`` against the canonical anatomy
documented in ``docs/skill-anatomy.md``:

1. Valid YAML frontmatter.
2. ``name`` field equals the parent directory name.
3. ``description`` field is non-empty.
4. Six required ``## Headings`` are all present:
   Overview, When to Use, Core Process *(prefix-match — subtitle allowed)*,
   Common Rationalizations, Red Flags, Verification.

Exit codes:
    0 — every SKILL.md passes
    1 — one or more failures (CI / pre-commit will block)

Usage:
    python scripts/validate_skills.py
    python scripts/validate_skills.py --skills-dir skills
    python scripts/validate_skills.py --json   # machine-readable
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Required frontmatter keys, exact match.
REQUIRED_FRONTMATTER_KEYS = ("name", "description")

# Required ## headings. "Core Process" matches by prefix so subtitles like
# "## Core Process: The 10 Rules" or "## Core Process: 4-Layer Architecture"
# are accepted. The other entries match exactly (after whitespace normalisation).
REQUIRED_SECTIONS = (
    "Overview",
    "When to Use",
    "Core Process",  # prefix-match
    "Common Rationalizations",
    "Red Flags",
    "Verification",
)
PREFIX_MATCH_SECTIONS = frozenset({"Core Process"})


@dataclass
class SkillValidationResult:
    """Per-skill validation outcome."""

    name: str
    path: str
    passed: bool
    errors: list[str] = field(default_factory=list)


def _parse_frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    """Return (frontmatter dict, body) or (None, body) on parse failure."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, parts[2]
    if not isinstance(fm, dict):
        return None, parts[2]
    return fm, parts[2]


def _extract_h2_headings(body: str) -> list[str]:
    """Return the text of every top-level ``##`` heading, in order."""
    return [m.strip() for m in re.findall(r"^##\s+(.+?)\s*$", body, re.M)]


def _section_present(required: str, headings: list[str]) -> bool:
    """Match either by exact equality or by prefix (for Core Process)."""
    if required in PREFIX_MATCH_SECTIONS:
        return any(h == required or h.startswith(required + ":") for h in headings)
    return required in headings


def validate_skill(skill_path: Path) -> SkillValidationResult:
    """Validate a single SKILL.md."""
    rel_path = str(skill_path)
    skill_dir = skill_path.parent.name
    result = SkillValidationResult(name=skill_dir, path=rel_path, passed=True)

    if not skill_path.exists():
        result.passed = False
        result.errors.append(f"file does not exist: {rel_path}")
        return result

    text = skill_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    if fm is None:
        result.passed = False
        result.errors.append("missing or unparseable YAML frontmatter")
        return result

    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in fm or not fm[key]:
            result.errors.append(f"frontmatter missing or empty: {key}")

    if "name" in fm and fm["name"] != skill_dir:
        result.errors.append(
            f"frontmatter name '{fm['name']}' does not match directory '{skill_dir}'"
        )

    headings = _extract_h2_headings(body)
    for required in REQUIRED_SECTIONS:
        if not _section_present(required, headings):
            result.errors.append(f"missing required section: ## {required}")

    result.passed = not result.errors
    return result


def validate_skills_dir(skills_dir: Path) -> list[SkillValidationResult]:
    """Validate every ``<dir>/SKILL.md`` directly under ``skills_dir``."""
    if not skills_dir.exists():
        raise FileNotFoundError(f"skills directory not found: {skills_dir}")
    results: list[SkillValidationResult] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        results.append(validate_skill(skill_md))
    return results


def render_text_report(results: list[SkillValidationResult]) -> str:
    """Render a human-readable report. Returns the full report string."""
    lines: list[str] = []
    n_pass = sum(1 for r in results if r.passed)
    n_fail = len(results) - n_pass
    lines.append(
        f"Validated {len(results)} SKILL.md file(s): "
        f"{n_pass} passed, {n_fail} failed"
    )
    lines.append("")
    for r in results:
        marker = "✓" if r.passed else "✗"
        lines.append(f"  {marker} {r.name}")
        for err in r.errors:
            lines.append(f"      - {err}")
    return "\n".join(lines)


def render_json_report(results: list[SkillValidationResult]) -> str:
    """Render a machine-readable JSON report."""
    return json.dumps(
        [
            {
                "name": r.name,
                "path": r.path,
                "passed": r.passed,
                "errors": r.errors,
            }
            for r in results
        ],
        indent=2,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("skills"),
        help="Directory containing skill subdirectories (default: skills)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report instead of text",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    try:
        results = validate_skills_dir(args.skills_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json_report(results))
    else:
        print(render_text_report(results))

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
