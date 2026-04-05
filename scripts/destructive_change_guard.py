#!/usr/bin/env python3
"""Destructive Change Guard — CI check that blocks PRs that gut critical files.

Prevents the failure mode where an AI coding agent (Copilot, CrewAI, etc.)
rewrites a file from scratch instead of making targeted edits, destroying
existing implementation.

Usage:
    python scripts/destructive_change_guard.py

    Reads git diff against the base branch and flags files that lost
    more than 50% of their lines. Exits 1 if critical files are affected.
"""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

# Files that must never be gutted — core pipeline infrastructure
CRITICAL_FILES = [
    "src/economist_agents/flow.py",
    "src/crews/stage3_crew.py",
    "src/crews/stage4_crew.py",
    "scripts/publication_validator.py",
    "scripts/editorial_judge.py",
    "scripts/agent_reviewer.py",
    "scripts/frontmatter_schema.py",
    "scripts/article_evaluator.py",
    ".github/workflows/content-pipeline.yml",
    ".github/workflows/ci.yml",
]

# Maximum percentage of lines that can be deleted from a critical file
MAX_DELETION_PCT = 50


def get_base_branch() -> str:
    """Detect the base branch (main or origin/main)."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        capture_output=True,
        text=True,
    )
    return "origin/main" if result.returncode == 0 else "main"


def get_diff_stats(base: str) -> list[dict[str, int | str]]:
    """Get per-file addition/deletion stats from git diff."""
    result = subprocess.run(
        ["git", "diff", "--numstat", base],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    stats = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, filepath = parts
        if added == "-" or deleted == "-":
            continue  # Binary file
        stats.append({"added": int(added), "deleted": int(deleted), "file": filepath})
    return stats


def get_file_line_count(base: str, filepath: str) -> int:
    """Get the line count of a file in the base branch."""
    result = subprocess.run(
        ["git", "show", f"{base}:{filepath}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0  # File didn't exist in base
    return len(result.stdout.split("\n"))


def check_destructive_changes() -> list[str]:
    """Check for destructive changes in critical files.

    Returns:
        List of violation messages. Empty if all clear.
    """
    base = get_base_branch()
    stats = get_diff_stats(base)
    violations = []

    for stat in stats:
        filepath = stat["file"]
        if filepath not in CRITICAL_FILES:
            continue

        deleted = stat["deleted"]
        base_lines = get_file_line_count(base, filepath)

        if base_lines == 0:
            continue  # New file, no destruction possible

        deletion_pct = round(deleted / base_lines * 100)

        if deletion_pct > MAX_DELETION_PCT:
            violations.append(
                f"BLOCKED: {filepath} lost {deletion_pct}% of its content "
                f"({deleted}/{base_lines} lines deleted). "
                f"This looks like a destructive rewrite, not a targeted edit. "
                f"Maximum allowed: {MAX_DELETION_PCT}%."
            )

    return violations


def main() -> None:
    """CLI entry point."""
    violations = check_destructive_changes()

    if violations:
        print("=" * 60)
        print("DESTRUCTIVE CHANGE GUARD — BLOCKED")
        print("=" * 60)
        for v in violations:
            print(f"\n  ❌ {v}")
        print()
        print("This check prevents AI coding agents from rewriting files")
        print("from scratch instead of making targeted edits.")
        print("If this is intentional, add the file to the PR description")
        print("with: 'Intentional rewrite: <filename>'")
        sys.exit(1)
    else:
        print("✅ Destructive change guard: no critical files gutted")
        sys.exit(0)


if __name__ == "__main__":
    main()
