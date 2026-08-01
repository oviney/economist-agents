#!/usr/bin/env python3
"""SessionStart context — deliver the guides instead of storing them (B-030).

The audit graded guide *volume* a D: 8,031 lines of `SKILL.md`, a 210-line `CLAUDE.md`, a
2,601-line `.github/copilot-instructions.md`, and two more instruction files — the "50
markdown files" Boeckeler says cannot be the future.

This hook is the alternative shape. The five non-negotiable constraints are *computed and
injected* at session start, along with live repo state (branch, open backlog items) that no
static file can keep current. Injected context is always accurate, whereas a markdown file
listing open items is stale the moment an item closes.

It reads `CLAUDE.md` for the constraint block rather than restating it, so there remains
exactly one source of truth. If the file moves, the hook degrades to the branch and backlog
summary instead of asserting something false.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from scripts.hooks._io import run

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
BACKLOG_MD = REPO_ROOT / "BACKLOG.md"

#: Matches the numbered constraint headings in CLAUDE.md's non-negotiable block.
_CONSTRAINT_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)

#: `### B-030 · Title` in BACKLOG.md. Struck-through (withdrawn) items are excluded.
_BACKLOG_ITEM_RE = re.compile(r"^### (B-\d+) · (.+)$", re.MULTILINE)


def constraint_summary() -> str:
    """Return the one-line form of each non-negotiable constraint.

    Returns:
        A bulleted list, or ``""`` when `CLAUDE.md` is unreadable.

    """
    try:
        text = CLAUDE_MD.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("session context could not read CLAUDE.md: %s", exc)
        return ""

    start = text.find("## Operating Constraints")
    if start == -1:
        return ""
    end = text.find("\n## ", start + 1)
    block = text[start : end if end != -1 else len(text)]

    headings = _CONSTRAINT_RE.findall(block)
    return "\n".join(f"  {n}. {h}" for n, h in enumerate(headings, start=1))


def current_branch() -> str:
    """Return the checked-out branch name, or 'unknown'."""
    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("session context could not read the branch: %s", exc)
        return "unknown"
    return completed.stdout.strip() or "unknown"


def open_backlog_items(limit: int = 12) -> list[str]:
    """Return the `B-NNN · Title` lines from BACKLOG.md's Todo section.

    Args:
        limit: Maximum items to return, so session start stays cheap.

    Returns:
        Item headings in file order. Empty when the section cannot be located.

    """
    try:
        text = BACKLOG_MD.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("session context could not read BACKLOG.md: %s", exc)
        return []

    start = text.find("## Todo")
    if start == -1:
        return []
    end = text.find("\n## Done", start)
    section = text[start : end if end != -1 else len(text)]

    seen: set[str] = set()
    items: list[str] = []
    for ident, title in _BACKLOG_ITEM_RE.findall(section):
        if ident in seen:
            continue
        seen.add(ident)
        items.append(f"{ident} · {title.strip()}")
        if len(items) >= limit:
            break
    return items


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Build the session-start context block.

    Args:
        payload: The harness SessionStart payload (unused; present for the contract).

    Returns:
        A payload injecting the constraints, branch, and open items as
        ``additionalContext``.

    """
    del payload  # SessionStart carries no input this hook needs.

    parts: list[str] = ["HARNESS CONTEXT (injected by .claude/settings.json, B-030)"]

    constraints = constraint_summary()
    if constraints:
        parts.append(
            "Non-negotiable operating constraints — see CLAUDE.md for the full text; "
            "the PreToolUse guard enforces #1 computationally:\n" + constraints,
        )

    parts.append(f"Working branch: {current_branch()}")

    items = open_backlog_items()
    if items:
        parts.append(
            "Open backlog items (BACKLOG.md is the source of record; PRs live on "
            "GitHub via the gh CLI):\n" + "\n".join(f"  - {i}" for i in items),
        )

    parts.append(
        "Verification is local-first (ADR-0015): run `make ci-local` before merging. "
        "main is unprotected — you are the merge gate.",
    )

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(parts),
        },
    }


if __name__ == "__main__":
    raise SystemExit(run(handle))
