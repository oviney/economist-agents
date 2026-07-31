#!/usr/bin/env python3
"""Validate that README badges still tell the truth (BUG-023, B-036).

A badge is a claim on the front page of the repository, and claims rot. Two of
this repo's four badges pointed at GitHub Actions workflows that ADR-0015
retired, and a third advertised a Python version the pin disagreed with.

The hook that was meant to prevent exactly this ran an earlier
``scripts/validate_badges.py`` that had been archived to ``scripts/archived/``.
Its pre-commit entry was ``bash -c '... || true'``, so it swallowed both the
stale-badge failures it existed to catch *and* the "no such file" error proving
it had no implementation. It was inert twice over. That archived copy also
resolved its paths relative to ``scripts/`` — it looked for ``scripts/README.md``
— and printed failures while exiting 0, so it could not have gated anything even
if it had been found.

This replacement is deliberately narrow. It checks the two things that actually
go stale, resolves every path from the repository root, and exits non-zero when
it finds a problem.

Usage:
    python3 scripts/validate_badges.py [repo_root]
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

#: Repo root, resolved from this file's location — never from the cwd, and never
#: relative to scripts/, which is the bug that made the archived copy useless.
REPO_ROOT = Path(__file__).resolve().parents[1]

#: `https://github.com/<owner>/<repo>/actions/workflows/<file>/badge.svg`
_WORKFLOW_BADGE = re.compile(r"actions/workflows/([A-Za-z0-9._-]+)/badge\.svg")

#: `https://img.shields.io/badge/Python-<version>-<colour>`
_PYTHON_BADGE = re.compile(r"img\.shields\.io/badge/Python-([0-9.]+)-")


def check_badges(root: Path | None = None) -> list[str]:
    """Check every badge in ``root/README.md`` against the repo's real state.

    Args:
        root: Repository root. Defaults to this file's repo.

    Returns:
        Human-readable problems; empty means the badges are honest.

    """
    base = root or REPO_ROOT
    readme = base / "README.md"

    if not readme.is_file():
        return [f"{readme} not found — cannot validate badges"]

    content = readme.read_text(encoding="utf-8")
    problems: list[str] = []

    # A workflow badge for a workflow that does not exist renders as a permanent
    # "no status" and tells a reader the project has CI it does not have.
    for workflow in _WORKFLOW_BADGE.findall(content):
        if not (base / ".github" / "workflows" / workflow).is_file():
            problems.append(
                f"README badge references .github/workflows/{workflow}, "
                "which does not exist (ADR-0015 retired GitHub Actions CI)",
            )

    # The badge must agree with the pin. A missing pin means there is nothing to
    # disagree with, so skip rather than invent a failure.
    pin_file = base / ".python-version"
    if pin_file.is_file():
        pin = pin_file.read_text(encoding="utf-8").strip()
        for advertised in _PYTHON_BADGE.findall(content):
            if advertised != pin:
                problems.append(
                    f"README Python badge says {advertised}, "
                    f"but .python-version pins {pin}",
                )

    return problems


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Optional ``[repo_root]``.

    Returns:
        0 when every badge is current, 1 otherwise.

    """
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else REPO_ROOT

    problems = check_badges(root)
    if not problems:
        logger.info("✅ README badges are current")
        return 0

    logger.error("❌ Badge validation failed:")
    for problem in problems:
        logger.error("  • %s", problem)
    logger.error(
        "\nFix the badge or the thing it describes. Do not delete this check — "
        "an always-green badge gate is how BUG-023 shipped (B-036).",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
