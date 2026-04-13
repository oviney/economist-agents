"""Lint the ADR tree against skills/adr-governance/SKILL.md rules.

Enforces:
1. All ADRs live in docs/adr/ (no other locations allowed)
2. Filenames match NNNN-kebab-case.md
3. Status is one of: Proposed | Accepted | Rejected | Deprecated | Superseded
4. No duplicate ADR numbers
5. Every ADR is referenced from mkdocs.yml
6. Bidirectional supersession: Superseded ADR links to superseder and vice versa

Exit code 0 on success, 1 on any violation.

Usage:
    python scripts/lint_adrs.py
    python scripts/lint_adrs.py --repo-root /path/to/repo
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

ALLOWED_STATUSES: set[str] = {
    "Proposed",
    "Accepted",
    "Rejected",
    "Deprecated",
    "Superseded",
}

ADR_FILENAME_PATTERN = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
TEMPLATE_FILENAME = "TEMPLATE.md"
CANONICAL_DIR = Path("docs/adr")
FORBIDDEN_PATTERNS: list[str] = [
    "docs/ADR-*.md",
    "docs/architecture/ADR*.md",
]


@dataclass
class AdrFile:
    """Parsed metadata for a single ADR file."""

    path: Path
    number: int
    title_slug: str
    status: str
    supersedes: str | None
    superseded_by: str | None


def find_canonical_adrs(repo_root: Path) -> list[Path]:
    """Return all ADR files under docs/adr/ except the TEMPLATE."""
    adr_dir = repo_root / CANONICAL_DIR
    if not adr_dir.exists():
        return []
    return sorted(p for p in adr_dir.glob("*.md") if p.name != TEMPLATE_FILENAME)


def find_forbidden_adrs(repo_root: Path) -> list[Path]:
    """Return any ADR files in forbidden legacy locations."""
    violations: list[Path] = []
    for pattern in FORBIDDEN_PATTERNS:
        violations.extend(sorted(repo_root.glob(pattern)))
    return violations


def parse_adr(path: Path) -> tuple[AdrFile | None, list[str]]:
    """Parse an ADR file's header. Returns (adr, errors)."""
    errors: list[str] = []
    filename_match = ADR_FILENAME_PATTERN.match(path.name)
    if not filename_match:
        errors.append(f"{path}: filename does not match NNNN-kebab-case.md pattern")
        return None, errors

    number = int(filename_match.group(1))
    title_slug = path.stem[5:]

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: could not read ({exc})")
        return None, errors

    status_match = re.search(r"^\*\*Status:\*\*\s*(.+?)(?:\n|$)", content, re.MULTILINE)
    if not status_match:
        errors.append(f"{path}: missing '**Status:**' header")
        return None, errors

    status_raw = status_match.group(1).strip()
    status_word = status_raw.split()[0] if status_raw else ""
    if status_word not in ALLOWED_STATUSES:
        errors.append(
            f"{path}: status '{status_word}' not in allowed set {sorted(ALLOWED_STATUSES)}"
        )

    supersedes_match = re.search(r"\*\*Supersedes:\*\*\s*\[?ADR-(\d{4})\]?", content)
    superseded_by_match = re.search(
        r"\*\*Superseded by\*\*[:]?\s*\[?ADR-(\d{4})\]?", content
    )
    if not superseded_by_match:
        superseded_by_match = re.search(
            r"Status:\*\*\s*Superseded by\s*\[?ADR-(\d{4})\]?", content
        )

    return (
        AdrFile(
            path=path,
            number=number,
            title_slug=title_slug,
            status=status_word,
            supersedes=supersedes_match.group(1) if supersedes_match else None,
            superseded_by=superseded_by_match.group(1) if superseded_by_match else None,
        ),
        errors,
    )


def check_no_duplicates(adrs: list[AdrFile]) -> list[str]:
    """Ensure no two ADRs share a number."""
    seen: dict[int, Path] = {}
    errors: list[str] = []
    for adr in adrs:
        if adr.number in seen:
            errors.append(
                f"duplicate ADR number {adr.number:04d}: {seen[adr.number]} and {adr.path}"
            )
        else:
            seen[adr.number] = adr.path
    return errors


def check_mkdocs_index(repo_root: Path, adrs: list[AdrFile]) -> list[str]:
    """Ensure every ADR is referenced in mkdocs.yml."""
    mkdocs_path = repo_root / "mkdocs.yml"
    if not mkdocs_path.exists():
        return [f"{mkdocs_path}: not found"]
    mkdocs_content = mkdocs_path.read_text(encoding="utf-8")
    errors: list[str] = []
    for adr in adrs:
        relative = f"adr/{adr.path.name}"
        if relative not in mkdocs_content:
            errors.append(
                f"{adr.path}: not referenced in mkdocs.yml (expected '{relative}')"
            )
    return errors


def check_supersession_integrity(adrs: list[AdrFile]) -> list[str]:
    """Verify bidirectional supersession links."""
    by_number = {adr.number: adr for adr in adrs}
    errors: list[str] = []
    for adr in adrs:
        if adr.status == "Superseded" and adr.superseded_by is None:
            errors.append(
                f"{adr.path}: status is Superseded but no 'Superseded by ADR-NNNN' link found"
            )
        if adr.superseded_by is not None:
            superseder_num = int(adr.superseded_by)
            superseder = by_number.get(superseder_num)
            if superseder is None:
                errors.append(
                    f"{adr.path}: superseded by ADR-{adr.superseded_by} which does not exist"
                )
            elif superseder.supersedes != f"{adr.number:04d}":
                errors.append(
                    f"{adr.path}: claims to be superseded by ADR-{adr.superseded_by} "
                    f"but {superseder.path} does not have 'Supersedes: ADR-{adr.number:04d}'"
                )
        if adr.supersedes is not None:
            superseded_num = int(adr.supersedes)
            superseded = by_number.get(superseded_num)
            if superseded is None:
                errors.append(
                    f"{adr.path}: supersedes ADR-{adr.supersedes} which does not exist"
                )
            elif superseded.superseded_by != f"{adr.number:04d}":
                errors.append(
                    f"{adr.path}: claims to supersede ADR-{adr.supersedes} "
                    f"but {superseded.path} does not have 'Superseded by ADR-{adr.number:04d}'"
                )
    return errors


def lint(repo_root: Path) -> list[str]:
    """Run all lint checks and return a combined error list."""
    all_errors: list[str] = []

    forbidden = find_forbidden_adrs(repo_root)
    for path in forbidden:
        all_errors.append(
            f"{path}: ADR found outside canonical location (docs/adr/). "
            f"Move it or archive it."
        )

    canonical_paths = find_canonical_adrs(repo_root)
    if not canonical_paths:
        all_errors.append(
            f"{repo_root / CANONICAL_DIR}: no ADRs found in canonical location"
        )
        return all_errors

    adrs: list[AdrFile] = []
    for path in canonical_paths:
        adr, errors = parse_adr(path)
        all_errors.extend(errors)
        if adr is not None:
            adrs.append(adr)

    all_errors.extend(check_no_duplicates(adrs))
    all_errors.extend(check_mkdocs_index(repo_root, adrs))
    all_errors.extend(check_supersession_integrity(adrs))

    return all_errors


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to the repository root (default: parent of this script)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    errors = lint(args.repo_root)
    if errors:
        for error in errors:
            logger.error(error)
        logger.error("%d ADR lint violation(s)", len(errors))
        return 1

    canonical_count = len(find_canonical_adrs(args.repo_root))
    logger.info("ADR lint passed: %d ADRs validated", canonical_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
