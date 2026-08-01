#!/usr/bin/env python3
"""PostToolUse sensor — the self-correction loop (B-030).

This is the hook the whole audit points at. Boeckeler describes the mechanism precisely:

    "Then the analysis tool says, over there, cyclomatic complexity is too high... And then
    that starts another little loop where the agent tries to self-correct and then asks the
    sensor again."

This repo had every sensor and no loop. After an agent edits a Python file, this hook
formats it, applies safe autofixes, and feeds anything remaining — lint plus the B-032
complexity findings — straight back into the model's context. The agent gets the feedback
while it still has the context to act on it, instead of the owner getting it at
`make ci-local` an hour later.

Two design choices worth keeping:

* **Silence on success.** A clean file produces no output. A hook that speaks on every edit
  becomes the Sonar server in the corner that nobody watches.
* **Scoped to the touched file.** Never the whole tree. The repo carries a 41-violation
  complexity backlog; re-reporting it on every edit would drown the one finding that is
  actually the agent's fault.

It also revives `scripts/agent_trace_logger.py`, which was complete, schema-versioned,
secret-redacting — and imported by nothing but its own test. It now writes the per-session
sensor history that answers Boeckeler's observability question: "how did the number of
analysis violations evolve?"
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import orjson

from scripts.complexity_sensor import format_report, load_overrides, scan_paths
from scripts.hooks._io import run

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Per-session sensor snapshots (gitignored — runtime data, not source).
HISTORY_PATH = REPO_ROOT / "logs" / "sensor_history.jsonl"

_RUFF_TIMEOUT_SECONDS = 60


def _extract_path(payload: dict[str, Any]) -> Path | None:
    """Pull the edited file path out of a PostToolUse payload.

    The harness reports it as ``tool_input.file_path`` for Edit/Write and as
    ``tool_response.filePath`` for some tool variants, so both are checked.

    Args:
        payload: The harness payload.

    Returns:
        The path, or None when the payload names no file.

    """
    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}
    raw = ""
    if isinstance(tool_input, dict):
        raw = str(tool_input.get("file_path") or "")
    if not raw and isinstance(tool_response, dict):
        raw = str(tool_response.get("filePath") or "")
    return Path(raw) if raw else None


def _ruff(args: list[str], target: Path) -> subprocess.CompletedProcess[str] | None:
    """Invoke ruff on one file, returning None when it could not run.

    Args:
        args: Subcommand and flags, e.g. ``["check", "--fix"]``.
        target: The file to act on.

    Returns:
        The completed process, or None on any spawn failure.

    """
    try:
        return subprocess.run(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-m", "ruff", *args, "--force-exclude", str(target)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=_RUFF_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("post-edit sensor could not run ruff: %s", exc)
        return None


def record_snapshot(
    session_id: str,
    path: str,
    finding_count: int,
    history_path: Path | None = None,
) -> None:
    """Append one sensor snapshot to the session history.

    Uses :class:`~scripts.agent_trace_logger.AgentTraceLogger` to build the entry so the
    snapshot inherits its schema version and its automatic redaction of sensitive keys,
    rather than reinventing a second trace format.

    Failure is swallowed unconditionally: observability must never be able to break an edit.

    Args:
        session_id: The harness session id, for grouping a session's snapshots.
        path: File the sensors ran against.
        finding_count: Number of findings reported back to the agent.
        history_path: Override for tests.

    """
    target = history_path or HISTORY_PATH
    try:
        from scripts.agent_trace_logger import AgentTraceLogger

        tracer = AgentTraceLogger()
        entry = tracer.log_agent_action(
            agent_name="HarnessSensor",
            stage="post_edit",
            inputs={"session_id": session_id, "path": path},
            outputs={"finding_count": finding_count},
            decision=("reported findings" if finding_count else "clean"),
            status="revision" if finding_count else "success",
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("ab") as handle:
            handle.write(orjson.dumps(entry) + b"\n")
    except Exception as exc:  # noqa: BLE001 — never break an edit over telemetry
        logger.debug("sensor history not recorded: %s", exc)


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Format, autofix, and report on the file that was just edited.

    Args:
        payload: The harness PostToolUse payload.

    Returns:
        A payload injecting sensor feedback as ``additionalContext``, or ``{}`` when the
        file is clean, absent, or not Python.

    """
    target = _extract_path(payload)
    if target is None or target.suffix != ".py" or not target.is_file():
        return {}

    # Mechanical cleanups first: never make the agent spend a turn on whitespace.
    _ruff(["format"], target)
    _ruff(["check", "--fix"], target)

    sections: list[str] = []

    remaining = _ruff(["check", "--no-fix"], target)
    if remaining is not None and remaining.returncode != 0:
        detail = (remaining.stdout or remaining.stderr).strip()
        if detail:
            sections.append(f"LINT (not auto-fixable)\n{detail}")

    complexity = format_report(scan_paths([target]), overrides=load_overrides())
    if complexity:
        sections.append(complexity)

    record_snapshot(
        session_id=str(payload.get("session_id", "")),
        path=str(target),
        finding_count=len(sections),
    )

    if not sections:
        return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"Harness sensors ran on {target.name} after your edit "
                "(formatting and safe autofixes are already applied):\n\n"
                + "\n\n".join(sections)
            ),
        },
    }


if __name__ == "__main__":
    raise SystemExit(run(handle))
