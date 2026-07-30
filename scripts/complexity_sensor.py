#!/usr/bin/env python3
"""Complexity sensor (B-032) — a judgment call, not a number.

`ruff.toml` regulates style, imports, bugbear and simplification, but no complexity
dimension: no ``C901``, no ``PLR09xx``, no ``max-complexity``. Over-long, over-branched
functions are the characteristic failure mode of AI-written code, so the dimension an
agent is most likely to violate was the one nothing watched.

This module is the sensor for that dimension, built on Boeckeler's ESLint-message
technique (SE Radio 730): do not merely report that complexity is 18, tell the agent this
is usually a smell, ask it to make a judgment call, and give it a *recorded* escape hatch
so the exceptions become a reviewable register instead of a scatter of bare ``noqa``
comments.

Why the selectors live here rather than in ``ruff.toml``'s ``select``:
the repo carries 41 pre-existing ``C901`` violations (worst: 33) and 75 ``PLR09xx``.
Selecting them globally would turn ``make ci-local`` red on day one and the sensor would
be switched off within the hour. Instead the sensor owns the selectors and is pointed at
*touched files* by the ``PostToolUse`` hook (B-030) — which is where new complexity is
actually born. The threshold itself stays in ``ruff.toml`` so there is exactly one number.

Usage::

    python -m scripts.complexity_sensor scripts/foo.py src/bar.py
    python -m scripts.complexity_sensor --changed     # git-diff scoped
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import orjson

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The register of accepted complexity, one line per override.
OVERRIDES_PATH = REPO_ROOT / "docs" / "harness-overrides.md"

#: Rules the sensor enforces. C901 is cyclomatic complexity; the PLR09xx family covers
#: the shape defects that usually accompany it.
SELECTORS = ("C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915")

#: Present in every report so a hook (or a test) can recognise a judgment-call prompt.
JUDGMENT_CALL_MARKER = "Make a judgment call."

#: ruff phrases every one of these findings as "`name` is too complex (18 > 10)" or
#: "Too many branches (15 > 12)"; the backticked name is the function when present.
_FUNCTION_RE = re.compile(r"`([^`]+)`")

#: An override line looks like: - `path/to/file.py::function_name` — justification
_OVERRIDE_RE = re.compile(r"`([^`]+::[^`]+)`")


@dataclass(frozen=True)
class ComplexityFinding:
    """One complexity violation, normalised out of ruff's JSON output."""

    path: str
    line: int
    function: str
    code: str
    message: str

    @property
    def key(self) -> str:
        """Return the ``path::function`` identity used by the override register."""
        return f"{self.path}::{self.function}"


def _is_python(path: Path) -> bool:
    """Return True when ``path`` is an existing Python source file."""
    return path.suffix == ".py" and path.is_file()


def scan_paths(paths: list[Path]) -> list[ComplexityFinding]:
    """Run ruff's complexity rules over ``paths`` and return normalised findings.

    Non-Python and missing paths are dropped rather than raising: callers include the
    ``PostToolUse`` hook and ``--changed``, both of which routinely hand over deleted
    files and markdown.

    Args:
        paths: Candidate files to scan.

    Returns:
        Findings in ruff's order. Empty when nothing to scan or nothing found.

    """
    targets = [p for p in paths if _is_python(p)]
    if not targets:
        return []

    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--select",
        ",".join(SELECTORS),
        "--no-fix",
        "--output-format",
        "json",
        "--force-exclude",
        *[str(p) for p in targets],
    ]

    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            command,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # A sensor that crashes is worse than a sensor that abstains.
        logger.warning("complexity sensor could not run ruff: %s", exc)
        return []

    if not completed.stdout.strip():
        return []

    try:
        raw = orjson.loads(completed.stdout)
    except orjson.JSONDecodeError as exc:
        logger.warning("complexity sensor could not parse ruff output: %s", exc)
        return []

    findings: list[ComplexityFinding] = []
    for item in raw:
        message = str(item.get("message", ""))
        match = _FUNCTION_RE.search(message)
        findings.append(
            ComplexityFinding(
                path=_relative(str(item.get("filename", ""))),
                line=int((item.get("location") or {}).get("row", 0)),
                function=match.group(1) if match else "<module>",
                code=str(item.get("code", "")),
                message=message,
            ),
        )
    return findings


def _relative(filename: str) -> str:
    """Return ``filename`` relative to the repo root when it lives inside it."""
    try:
        return str(Path(filename).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return filename


def load_overrides(register: Path | None = None) -> set[str]:
    """Read the accepted-complexity register.

    Args:
        register: Path to the override markdown. Defaults to ``OVERRIDES_PATH``.

    Returns:
        The set of ``path::function`` keys the owner has explicitly accepted. Empty when
        the register is absent — an unwritten register grants no exemptions.

    """
    path = register or OVERRIDES_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()

    return {match.group(1) for match in _OVERRIDE_RE.finditer(text)}


def format_report(
    findings: list[ComplexityFinding],
    overrides: set[str] | None = None,
) -> str:
    """Render findings as a judgment-call prompt, or an empty string when clean.

    The wording matters more than the mechanism. A bare "complexity is 18" invites the
    agent to either ignore it or suppress it; naming the judgment call and the recorded
    escape hatch is what turns the sensor into a reviewable decision trail.

    Args:
        findings: Findings from :func:`scan_paths`.
        overrides: Accepted ``path::function`` keys to suppress.

    Returns:
        A human- and agent-readable report, or ``""`` when nothing is left to report.

    """
    accepted = overrides or set()
    live = [f for f in findings if f.key not in accepted]
    if not live:
        return ""

    by_file: dict[str, list[ComplexityFinding]] = {}
    for finding in live:
        by_file.setdefault(finding.path, []).append(finding)

    lines: list[str] = []
    for path, items in by_file.items():
        lines.append(f"COMPLEXITY SENSOR — {path}")
        for item in items:
            lines.append(f"  line {item.line}: {item.message} [{item.code}]")
    lines.append("")
    lines.append(
        "This is usually a smell. Consider: is this function doing more than one "
        "thing? Can a branch become a guard clause, or a block become a named helper?",
    )
    lines.append("")
    lines.append(
        f"{JUDGMENT_CALL_MARKER} If the complexity is genuinely warranted — a dispatch "
        "table, a parser, generated code, test data — you may keep it by recording an "
        "override in docs/harness-overrides.md with a one-line justification. Do NOT "
        "add a bare noqa: an unrecorded suppression is invisible at review time, which "
        "is the failure mode this sensor exists to prevent.",
    )
    return "\n".join(lines)


def changed_python_paths() -> list[Path]:
    """Return Python files that differ from HEAD, for ``--changed``.

    Returns:
        Existing ``*.py`` paths from ``git diff HEAD --name-only`` plus untracked files.
        Empty when git is unavailable — again, abstain rather than crash.

    """
    try:
        tracked = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "diff", "HEAD", "--name-only"],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=30,
            check=False,
        )
        untracked = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "ls-files", "--others", "--exclude-standard"],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("complexity sensor could not consult git: %s", exc)
        return []

    names = f"{tracked.stdout}\n{untracked.stdout}".split()
    return [REPO_ROOT / name for name in names if name.endswith(".py")]


def main(argv: list[str] | None = None) -> int:
    """Run the sensor from the command line.

    Returns:
        1 when unaccepted findings remain, 0 otherwise.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Files to scan")
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Scan Python files that differ from HEAD instead of explicit paths",
    )
    args = parser.parse_args(argv)

    paths = changed_python_paths() if args.changed else list(args.paths)
    report = format_report(scan_paths(paths), overrides=load_overrides())
    if not report:
        return 0

    sys.stderr.write(report + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
