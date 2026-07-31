#!/usr/bin/env python3
"""Per-file mypy gate with a grandfathered baseline (B-035 Task 2).

B-031 made mypy able to fail for the first time. The measurement then showed the
cost: 12 of 48 ``scripts/*.py`` files would block a commit **merely by being
touched**, on errors the commit did not introduce. One commit in four blocked by
someone else's debt is the noise-overload failure mode that gets a gate reverted
to ``manual`` — which is exactly how mypy went inert in the first place.

The answer is not a weaker guide. ``CLAUDE.md`` keeps "Type hints mandatory".
This records the known-dirty files with the error count each is grandfathered
at, and blocks only on errors *beyond* that count. A new error in a baselined
file still blocks: the baseline is a per-file count, not a mute.

B-032 built this same mechanism for complexity (``docs/harness-overrides.md``).
This reuses the shape — one mechanism, two sensors — rather than inventing a
second answer to the same question.

The register lives in ``docs/mypy-baseline.md``: markdown so it is reviewable,
parsed so it is enforced. ``tests/test_mypy_baseline.py`` fails if any file's
count grows, or if a file that improved keeps its old allowance, so the baseline
can only shrink.

Usage:
    python3 scripts/mypy_baseline.py scripts/foo.py scripts/bar.py
    python3 scripts/mypy_baseline.py --all
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_DOC = REPO_ROOT / "docs" / "mypy-baseline.md"

#: ``- `path/to/file.py` — 8`` — em dash is house style, ASCII hyphen tolerated.
_BASELINE_ENTRY = re.compile(r"^\s*-\s+`([^`]+)`\s*[—-]\s*(\d+)\s*$")

#: mypy writes ``path:line: error: message  [code]``. Notes are not errors.
_MYPY_ERROR = re.compile(r"^(?P<path>[^:]+):\d+:(?:\d+:)?\s*error:")


def parse_baseline(text: str) -> dict[str, int]:
    """Parse the markdown baseline register into ``{path: allowed_errors}``.

    Args:
        text: Contents of ``docs/mypy-baseline.md``

    Returns:
        Mapping of repo-relative path to its grandfathered error count

    """
    baseline: dict[str, int] = {}
    in_fence = False

    for line in text.split("\n"):
        # The document shows the entry format in a fenced example. Parsing that
        # example would baseline a file named `scripts/foo.py`, so fences are
        # illustration, never data.
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = _BASELINE_ENTRY.match(line)
        if match:
            baseline[match.group(1)] = int(match.group(2))

    return baseline


def count_errors(mypy_output: str) -> dict[str, int]:
    """Count mypy errors per file.

    Args:
        mypy_output: Raw stdout from a mypy run

    Returns:
        Mapping of path to error count; files with no errors are absent

    """
    counts: dict[str, int] = {}
    for line in mypy_output.split("\n"):
        match = _MYPY_ERROR.match(line)
        if match:
            path = match.group("path")
            counts[path] = counts.get(path, 0) + 1
    return counts


def check(counts: dict[str, int], baseline: dict[str, int]) -> list[str]:
    """Find files whose error count exceeds what they are grandfathered at.

    Args:
        counts: Measured errors per file
        baseline: Grandfathered errors per file

    Returns:
        Human-readable violation lines; empty means the gate passes

    """
    violations = []
    for path in sorted(counts):
        allowed = baseline.get(path, 0)
        if counts[path] > allowed:
            new = counts[path] - allowed
            violations.append(
                f"{path}: {counts[path]} errors > {allowed} allowed ({new} new)",
            )
    return violations


def run_mypy(paths: list[str]) -> str:
    """Run mypy over ``paths`` the way the pre-commit hook does.

    ``--follow-imports=silent`` is what makes the gate survivable: without it a
    commit touching one clean file inherits the 611-error repo-wide backlog.

    Args:
        paths: Files to check

    Returns:
        mypy's stdout

    """
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file=mypy.ini",
            "--follow-imports=silent",
            "--no-error-summary",
            *paths,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Returns:
        0 when every file is at or below its baseline, 1 otherwise

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files to check")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check every scripts/*.py file instead of the given paths",
    )
    args = parser.parse_args(argv)

    if args.all:
        paths = sorted(
            str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "scripts").glob("*.py")
        )
    else:
        paths = args.paths

    if not paths:
        return 0

    baseline = (
        parse_baseline(BASELINE_DOC.read_text(encoding="utf-8"))
        if BASELINE_DOC.exists()
        else {}
    )
    violations = check(count_errors(run_mypy(paths)), baseline)

    if not violations:
        return 0

    logger.error("mypy: new type errors beyond the recorded baseline\n")
    for violation in violations:
        logger.error("  %s", violation)
    logger.error(
        "\nFix them. Do NOT raise docs/mypy-baseline.md — a test enforces that the\n"
        "baseline only shrinks, so raising it fails the suite instead of the commit.",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
