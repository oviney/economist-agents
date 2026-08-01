#!/usr/bin/env python3
"""Stop gate — the agent closes the loop, not the owner (B-030).

`make ci-local` is the merge authority and stays so. The problem was that it was also the
*first* place anything got checked: an agent could finish a turn with the tree red and the
owner would find out later. This hook moves the first check to the end of the turn, where
the agent still has the context to fix it.

**Why it blocks at most once per session.** A `Stop` hook that blocks unconditionally is a
session trap: block → the model works → it stops again → blocked again, indefinitely. The
bound is the safety property, not a convenience, and `tests/test_harness_hooks.py` asserts
it. One block gives the agent one chance to self-correct with full context; after that the
owner's gate takes over, which is where authority belonged all along.

**Lint plus scoped tests (B-035 Task 1).** The gate originally ran only `ruff check`, and
the objection to adding tests was cost. The measurement removed it: the full suite is ~100s,
but one *matching* test file is 3.4s, and 40 of 48 `scripts/` modules (83%) have a match. So
the gate does not run the suite — it runs `tests/test_X.py` for each changed `X.py`.

Lint regulates maintainability only. A red test is the correctness signal, which is the
feedback loop that actually matters. Tests are **additive**: lint stays always-on, and
anything other than a clean red test result — no match, a timeout, a missing pytest —
degrades to lint-only rather than blocking. Never block on a timeout; a slow suite is not a
broken one.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.complexity_sensor import changed_python_paths
from scripts.hooks._io import run

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the one-block-per-session sentinels live (gitignored runtime state).
STATE_DIR = REPO_ROOT / "logs" / ".session_gate"

_RUFF_TIMEOUT_SECONDS = 90

#: Hard cap on the scoped test run. One matching file measured 3.4s (6.2s wall), so 60s
#: buys a wide margin while keeping the worst case bounded. On expiry the gate reports
#: nothing rather than blocking — see `collect_test_failures`.
_PYTEST_TIMEOUT_SECONDS = 60

#: Reentrancy guard. The gate's own test file matches the mapping rule, so a gate that
#: spawns pytest from inside a pytest run would recurse forever. Set in the child's
#: environment; its presence makes `collect_test_failures` a no-op.
_REENTRY_ENV = "HARNESS_SESSION_GATE_ACTIVE"


def collect_violations(paths: list[Path] | None = None) -> str:
    """Return ruff's complaints about dirty Python files, or '' when clean.

    Args:
        paths: Files to check. Defaults to Python files differing from HEAD.

    Returns:
        ruff's output, or ``""`` when there is nothing to report or ruff could not run.

    """
    targets = paths if paths is not None else changed_python_paths()
    existing = [p for p in targets if p.is_file()]
    if not existing:
        return ""

    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--no-fix",
                "--force-exclude",
                *[str(p) for p in existing],
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=_RUFF_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("session gate could not run ruff: %s", exc)
        return ""

    if completed.returncode == 0:
        return ""
    return (completed.stdout or completed.stderr).strip()


def matching_test_files(
    paths: list[Path] | None = None,
    repo_root: Path | None = None,
) -> list[Path]:
    """Map changed Python files to the test files that cover them.

    ``scripts/foo.py`` maps to ``tests/test_foo.py``; a changed test file maps to
    itself. Modules with no matching test (17% of ``scripts/``) map to nothing —
    that is a degradation to lint-only, not an error.

    Args:
        paths: Changed files. Defaults to Python files differing from HEAD.
        repo_root: Repository root; defaults to the real one (tests override it).

    Returns:
        Existing test files, deduplicated, in a stable order.

    """
    root = repo_root or REPO_ROOT
    targets = paths if paths is not None else changed_python_paths()

    found: list[Path] = []
    for path in targets:
        stem = path.stem
        candidate = (
            path if stem.startswith("test_") else root / "tests" / f"test_{stem}.py"
        )
        if candidate.is_file() and candidate not in found:
            found.append(candidate)

    return found


def collect_test_failures(paths: list[Path] | None = None) -> str:
    """Return pytest's report for the scoped test files, or '' when not red.

    Every non-red outcome yields ``""``: no matching files, a pass, a timeout, or
    a pytest that will not start. Tests are additive to lint, so an inconclusive
    run must degrade to lint-only rather than block.

    Args:
        paths: Test files to run. Defaults to those matching the changed files.

    Returns:
        pytest's output when tests fail, otherwise ``""``.

    """
    if os.environ.get(_REENTRY_ENV):
        # Already inside a gate-spawned pytest. This hook's own test file matches
        # its mapping rule, so without this the child would spawn a grandchild,
        # and so on. Bounds the recursion at depth one.
        return ""

    targets = matching_test_files() if paths is None else paths
    if not targets:
        return ""

    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
                *[str(p) for p in targets],
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=_PYTEST_TIMEOUT_SECONDS,
            check=False,
            env={**os.environ, _REENTRY_ENV: "1"},
        )
    except subprocess.TimeoutExpired:
        # A slow suite is not a broken one. Blocking here would punish the agent
        # for someone else's slow test.
        logger.warning("session gate: scoped tests timed out, standing down")
        return ""
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("session gate could not run pytest: %s", exc)
        return ""

    if completed.returncode == 0:
        return ""
    return (completed.stdout or completed.stderr).strip()


def _sentinel(session_id: str, state_dir: Path) -> Path:
    """Return the path recording that this session has already been blocked once.

    Args:
        session_id: Harness session id; an empty id still gets a stable slot, so a
            payload without one cannot escape the bound.
        state_dir: Directory holding the sentinels.

    Returns:
        The sentinel path.

    """
    digest = hashlib.sha256((session_id or "anonymous").encode()).hexdigest()[:16]
    return state_dir / f"{digest}.blocked"


def handle(
    payload: dict[str, Any],
    violations: str | None = None,
    state_dir: Path | None = None,
    test_failures: str | None = None,
) -> dict[str, Any]:
    """Block once per session when the working tree's Python is red.

    "Red" means either sensor: lint on the changed files, or the tests that cover
    them. Lint is always-on; tests are additive and degrade to silence when they
    cannot produce a clean verdict.

    Args:
        payload: The harness Stop payload.
        violations: Pre-computed lint text; collected from ruff when omitted.
        state_dir: Override for the sentinel directory (tests).
        test_failures: Pre-computed pytest text; collected when omitted.

    Returns:
        A ``decision: "block"`` payload on the session's first red stop, else ``{}``.

    """
    directory = state_dir or STATE_DIR
    lint = collect_violations() if violations is None else violations
    tests = collect_test_failures() if test_failures is None else test_failures

    sections = []
    if lint:
        sections.append(f"ruff is red on Python files you changed:\n\n{lint}")
    if tests:
        sections.append(f"tests covering your changes are failing:\n\n{tests}")
    if not sections:
        return {}

    detail = "\n\n".join(sections)

    sentinel = _sentinel(str(payload.get("session_id", "")), directory)
    if sentinel.exists():
        # Already used this session's one block. Handing it back would loop.
        return {}

    try:
        directory.mkdir(parents=True, exist_ok=True)
        sentinel.touch()
    except OSError as exc:
        # If the bound cannot be recorded, do not block at all — an unbounded block is
        # strictly worse than a missed one.
        logger.warning(
            "session gate could not record its bound, standing down: %s", exc
        )
        return {}

    return {
        "decision": "block",
        "reason": (
            "Harness Stop gate — fix these before finishing the turn. `make ci-local` "
            "is the merge gate and will reject them anyway, and you have the context "
            "now that the owner will not have later.\n\n"
            f"{detail}\n\n"
            "This gate fires at most once per session, so this is the only reminder."
        ),
    }


if __name__ == "__main__":
    raise SystemExit(run(handle))
