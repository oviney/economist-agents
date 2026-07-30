#!/usr/bin/env python3
"""PreToolUse guard — turn two guides into sensors (B-030).

The audit's sharpest structural finding was that **where a guide and a default disagree,
the default wins**:

* `CLAUDE.md` constraint #1 is *"NO new API keys. Ever."* — the most emphatic sentence in
  the repo, with zero computational backing. Neither `destructive_change_guard.py` nor
  `pre_commit_arch_check.py` mentions `OPENAI_API_KEY`.
* B-028: the B-013 review stage exists only as prose, while `deploy_to_blog.py:681` sets
  `default="post"`. Running the *documented* command silently publishes without review.

Both are policies expressed as guides, and a guide is skippable. Expressed as a
`permissionDecision: "deny"`, they are not. This hook does that, and only that.

**The calibration matters as much as the rule.** A guard that blocked `grep OPENAI_API_KEY`
would be disabled within a day — the noise-overload failure mode that makes teams stop
watching their own static analysis. So the guard denies *introducing* a key (assignment,
export, install) and allows reading, grepping, and documenting one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.hooks._io import run

#: Keys forbidden as a *requirement* by CLAUDE.md constraints #1-#3.
#:
#: ANTHROPIC_API_KEY is deliberately absent: it is the legacy Stage-1 path (BUG-046, tracked
#: in B-010), so denying it would block work on the very item that removes it.
FORBIDDEN_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "SERPER_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
)

#: Packages that only exist to reach a forbidden service.
FORBIDDEN_INSTALLS: tuple[str, ...] = (
    "openai",
    "google-generativeai",
    "dalle",
)

#: Config files where a forbidden key name is a wiring change, not documentation.
GUARDED_CONFIG_SUFFIXES: frozenset[str] = frozenset(
    {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".env"},
)

#: `NAME=` or `export NAME=` — an introduction. Bare mentions are reads and are allowed.
_ASSIGNMENT_RE = re.compile(
    r"(?:^|[;&|]\s*|\bexport\s+|\benv\s+)(" + "|".join(FORBIDDEN_KEYS) + r")\s*=",
)

_INSTALL_RE = re.compile(
    r"\b(?:pip3?|uv|poetry|conda)\s+(?:install|add)\b[^;&|]*\b("
    + "|".join(re.escape(pkg) for pkg in FORBIDDEN_INSTALLS)
    + r")\b",
)

_DEPLOY_RE = re.compile(r"\bdeploy_to_blog\b")


def _deny(reason: str) -> dict[str, Any]:
    """Build a PreToolUse deny response.

    Args:
        reason: Shown to the model and the user in place of the tool call.

    Returns:
        The harness payload that refuses the call.

    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def check_command(command: str) -> dict[str, Any]:
    """Evaluate a Bash command against both policies.

    Args:
        command: The command the agent proposes to run.

    Returns:
        A deny payload, or ``{}`` to let the normal permission flow proceed.

    """
    assignment = _ASSIGNMENT_RE.search(command)
    if assignment:
        key = assignment.group(1)
        return _deny(
            f"Blocked: this sets {key}. CLAUDE.md constraint #1 is 'NO new API keys. "
            "Ever.' — including free-tier keys. The runtime is keyless: writing, "
            "graphics and vision run on the Claude subscription via the Agent SDK, and "
            "research uses arXiv + Semantic Scholar. If the task appears to need a key, "
            "the answer is to do it keyless or to say it cannot be done keyless.",
        )

    install = _INSTALL_RE.search(command)
    if install:
        return _deny(
            f"Blocked: installing '{install.group(1)}' only makes sense to reach a "
            "forbidden paid service (CLAUDE.md constraints #1-#2). ADR-0014 retired the "
            "DALL-E path; heroes are drawn as SVG on the subscription (constraint #4).",
        )

    if _DEPLOY_RE.search(command) and not _is_review_deploy(command):
        return _deny(
            "Blocked: deploy_to_blog without '--mode review'. Article two was published "
            "unreviewed this way (B-028): the tool's default is 'post', so the "
            "documented command bypasses the B-013 live review stage with no warning. "
            "Deploy with '--mode review', get the unlisted /review/<slug>-<token>/ URL "
            "approved, then promote with 'make publish SLUG=<slug>'.",
        )

    return {}


def _is_review_deploy(command: str) -> bool:
    """Return True when a deploy_to_blog invocation is safe to allow.

    Args:
        command: The proposed command.

    Returns:
        True for review-mode deploys and for informational invocations (``--help``,
        ``--dry-run``), which publish nothing.

    """
    return any(
        flag in command for flag in ("--mode review", "--help", "-h", "--dry-run")
    )


def check_file_write(file_path: str, content: str) -> dict[str, Any]:
    """Evaluate a Write/Edit against the forbidden-key policy.

    Documentation is explicitly allowed: this repo's own guides, ADRs and backlog discuss
    the banned keys by name, and a guard that blocked those would be unusable.

    Args:
        file_path: Target path.
        content: Text being written (``content`` or ``new_string``).

    Returns:
        A deny payload, or ``{}``.

    """
    suffix = Path(file_path).suffix.lower()
    name = Path(file_path).name.lower()
    is_config = suffix in GUARDED_CONFIG_SUFFIXES or name.startswith(".env")
    if not is_config:
        return {}

    for key in FORBIDDEN_KEYS:
        if key in content:
            return _deny(
                f"Blocked: this writes {key} into {Path(file_path).name}. CLAUDE.md "
                "constraint #1 forbids requiring any API key. B-034 removed the last "
                "two such entries from .mcp.json; re-adding one would put the harness "
                "back in contradiction with its own guides.",
            )
    return {}


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Route a PreToolUse payload to the right check.

    Args:
        payload: The harness payload.

    Returns:
        A deny payload, or ``{}`` to allow.

    """
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return {}

    tool_name = str(payload.get("tool_name", ""))

    if tool_name == "Bash":
        return check_command(str(tool_input.get("command", "")))

    if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        content = str(
            tool_input.get("content")
            or tool_input.get("new_string")
            or tool_input.get("new_source")
            or "",
        )
        return check_file_write(str(tool_input.get("file_path", "")), content)

    return {}


if __name__ == "__main__":
    raise SystemExit(run(handle))
