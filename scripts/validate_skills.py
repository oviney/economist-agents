#!/usr/bin/env python3
"""Validate every ``skills/*/SKILL.md`` file against the documented anatomy.

Spec: ``docs/skill-anatomy.md``. Issues #293 + #294.

Each SKILL.md must:

1. Live at ``skills/<name>/SKILL.md`` where ``<name>`` matches the
   ``name:`` frontmatter field.
2. Have YAML frontmatter with exactly the two fields ``name`` and
   ``description`` (no other keys allowed; both must be present).
3. Contain the six required ``##`` body sections, in any order:
   Overview, When to Use, Core Process, Common Rationalizations, Red
   Flags, Verification.

CLI:
    python scripts/validate_skills.py            # validate skills/
    python scripts/validate_skills.py path/      # validate a custom path
    python scripts/validate_skills.py --quiet    # exit code only

Exit codes:
    0 — every skill passes
    1 — at least one violation
    2 — usage error (no skills found, bad path)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FRONTMATTER_KEYS: frozenset[str] = frozenset({"name", "description"})
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Overview",
    "When to Use",
    "Core Process",
    "Common Rationalizations",
    "Red Flags",
    "Verification",
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:", re.MULTILINE)


@dataclass
class SkillReport:
    path: Path
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    """Return ``(frontmatter_dict, body)`` or ``(None, body)`` if missing."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    raw = match.group(1)
    fm: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key_match = _FRONTMATTER_KEY_RE.match(line)
        if not key_match:
            continue
        key = key_match.group(1)
        value = line[key_match.end() :].strip()
        fm[key] = value
    return fm, text[match.end() :]


def _required_sections_present(body: str) -> list[str]:
    """Return the names of sections missing from the body.

    A heading counts as present when a line starts with ``## <section>``
    optionally followed by ``:`` or `` —`` and an extension subtitle.
    Both ``## Core Process`` and ``## Core Process: 4-Layer Architecture``
    satisfy the requirement.
    """
    missing: list[str] = []
    for section in REQUIRED_SECTIONS:
        pattern = re.compile(
            rf"^##\s+{re.escape(section)}(\s*$|[:\s—-])",
            re.MULTILINE,
        )
        if not pattern.search(body):
            missing.append(section)
    return missing


def validate_skill(path: Path) -> SkillReport:
    """Validate a single SKILL.md file."""
    report = SkillReport(path=path)

    if not path.is_file():
        report.errors.append("file does not exist")
        return report

    text = path.read_text()
    frontmatter, body = _parse_frontmatter(text)
    if frontmatter is None:
        report.errors.append("missing YAML frontmatter (--- delimited block at top)")
        return report

    keys = set(frontmatter.keys())
    missing_keys = REQUIRED_FRONTMATTER_KEYS - keys
    extra_keys = keys - REQUIRED_FRONTMATTER_KEYS
    if missing_keys:
        report.errors.append(
            f"missing frontmatter key(s): {', '.join(sorted(missing_keys))}"
        )
    if extra_keys:
        report.errors.append(
            f"unexpected frontmatter key(s): {', '.join(sorted(extra_keys))}"
        )

    declared_name = frontmatter.get("name", "").strip().strip("\"'")
    parent_name = path.parent.name
    if declared_name and declared_name != parent_name:
        report.errors.append(
            f"frontmatter name '{declared_name}' does not match directory '{parent_name}'"
        )

    description = frontmatter.get("description", "").strip().strip("\"'")
    if description and not description.endswith((".", "!", "?")):
        report.errors.append("description should end with terminal punctuation")

    missing_sections = _required_sections_present(body)
    if missing_sections:
        report.errors.append(
            f"missing required ## section(s): {', '.join(missing_sections)}"
        )

    return report


def discover_skill_files(root: Path) -> list[Path]:
    """Return every ``<root>/*/SKILL.md`` in directory order."""
    if not root.is_dir():
        return []
    return sorted(root.glob("*/SKILL.md"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SKILL.md anatomy.")
    parser.add_argument(
        "root",
        nargs="?",
        default="skills",
        help="Directory containing skill subdirectories (default: skills)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file output; only set the exit code.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    skill_files = discover_skill_files(root)
    if not skill_files:
        print(f"No SKILL.md files found under {root}/", file=sys.stderr)
        return 2

    reports = [validate_skill(p) for p in skill_files]
    failed = [r for r in reports if not r.ok]

    if not args.quiet:
        for r in reports:
            status = "✓" if r.ok else "✗"
            rel = r.path.relative_to(Path.cwd()) if r.path.is_absolute() else r.path
            print(f"{status} {rel}")
            for err in r.errors:
                print(f"    - {err}")

        print()
        print(f"{len(reports) - len(failed)}/{len(reports)} skills passed.")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
