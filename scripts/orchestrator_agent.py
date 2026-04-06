#!/usr/bin/env python3
"""Orchestrator agent for intelligent PR triage and dispatch decisions.

Exposes a --mode CLI interface callable from GitHub Actions:

    # Is this PR done enough to promote?
    python3 scripts/orchestrator_agent.py --mode pr-ready-check --pr-url <url>

    # Which of two duplicate PRs should we keep?
    python3 scripts/orchestrator_agent.py --mode duplicate-triage --pr-a <url> --pr-b <url>

    # Should we dispatch this issue now?
    python3 scripts/orchestrator_agent.py --mode dispatch-check --issue <url>

    # Is this agent stalled or just slow?
    python3 scripts/orchestrator_agent.py --mode stall-check --pr-url <url> --idle-minutes 45
"""

import argparse
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = _ROOT / "data" / "orchestrator_state.json"

# Maximum number of concurrent agent PRs before capacity is considered full.
_MAX_CAPACITY = 6

# Stall thresholds (minutes) by complexity level.
_STALL_THRESHOLDS: dict[str, int] = {
    "low": 30,
    "medium": 60,
    "high": 90,
}


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _parse_github_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR or issue URL into (owner, repo, number).

    Args:
        url: Full GitHub URL, e.g. https://github.com/owner/repo/pull/123

    Returns:
        Tuple of (owner, repo_name, number).

    Raises:
        ValueError: If the URL does not match expected GitHub format.
    """
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/(?:pull|issues)/(\d+)",
        url,
    )
    if not match:
        raise ValueError(
            f"Invalid GitHub PR/issue URL: {url!r}. "
            "Expected https://github.com/<owner>/<repo>/pull/<n> "
            "or https://github.com/<owner>/<repo>/issues/<n>"
        )
    owner, repo, number = match.groups()
    return owner, repo, int(number)


def _get_github_client() -> Any:
    """Create and return a PyGithub client using GITHUB_TOKEN.

    Returns:
        Authenticated Github instance (unauthenticated if token absent).

    Raises:
        ImportError: If PyGithub is not installed.
    """
    from github import Github  # noqa: PLC0415

    token = os.environ.get("GITHUB_TOKEN", "")
    return Github(token) if token else Github()


def _load_state() -> list[dict[str, Any]]:
    """Load the orchestrator decision log from disk.

    Returns:
        List of past decision records, or empty list if file missing/corrupt.
    """
    if not STATE_FILE.exists():
        return []
    try:
        return orjson.loads(STATE_FILE.read_bytes())
    except Exception as exc:
        logger.warning("Could not read state file %s: %s", STATE_FILE, exc)
        return []


def _save_state(state: list[dict[str, Any]]) -> None:
    """Persist the orchestrator decision log to disk.

    Args:
        state: Full list of decision records to write.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_bytes(orjson.dumps(state, option=orjson.OPT_INDENT_2))


def _log_decision(action: str, data: dict[str, Any]) -> None:
    """Append a decision record to the state file.

    Args:
        action: Short action label, e.g. "promoted" or "dispatch_check".
        data: Additional key/value context for the record.
    """
    state = _load_state()
    entry: dict[str, Any] = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        **data,
    }
    state.append(entry)
    _save_state(state)


def _has_todo_markers(patch: str | None) -> bool:
    """Return True if the diff patch contains TODO/FIXME/placeholder markers.

    Args:
        patch: Unified diff string from GitHub API, or None.

    Returns:
        True if any marker is found in added lines.
    """
    if not patch:
        return False
    for line in patch.splitlines():
        if line.startswith("+") and re.search(
            r"\b(TODO|FIXME|PLACEHOLDER|WIP|HACK)\b", line, re.IGNORECASE
        ):
            return True
    return False


def _estimate_complexity(labels: list[str], file_count: int) -> str:
    """Estimate task complexity from PR labels and file count.

    Args:
        labels: Lowercase PR/issue label names.
        file_count: Number of files changed in the PR.

    Returns:
        One of "low", "medium", or "high".
    """
    for lbl in labels:
        if any(marker in lbl for marker in ("effort:large", "p1", "complex", "large")):
            return "high"
        if any(marker in lbl for marker in ("effort:small", "p4", "simple", "small")):
            return "low"
    if file_count > 5:
        return "high"
    if file_count <= 1:
        return "low"
    return "medium"


# ──────────────────────────────────────────────────────────────────────────────
# Decision modes
# ──────────────────────────────────────────────────────────────────────────────


def check_pr_ready(pr_url: str) -> dict[str, Any]:
    """Determine whether a PR is ready to be promoted.

    Fetches the PR diff via the GitHub API and checks:
    - Substantive code changes (not just an "initial plan" commit).
    - Absence of TODO/FIXME/placeholder markers.
    - Non-trivial PR description referencing a source issue.
    - Presence of test files.

    Args:
        pr_url: Full GitHub pull-request URL.

    Returns:
        Dictionary with keys:
            promote (bool): Whether the PR is ready to promote.
            reason  (str):  Human-readable explanation.
            details (dict): Granular sub-checks.
    """
    owner, repo_name, pr_number = _parse_github_url(pr_url)
    g = _get_github_client()
    repo = g.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    files = list(pr.get_files())
    file_count = len(files)

    # Check for TODO/FIXME markers in diff
    has_todo = any(_has_todo_markers(f.patch) for f in files)

    # Check description quality
    body = pr.body or ""
    has_description = len(body.strip()) > 50
    has_issue_ref = bool(
        re.search(r"#\d+|closes|fixes|resolves", body, re.IGNORECASE)
    )

    # Check for test files
    test_files = [f for f in files if re.search(r"test", f.filename, re.IGNORECASE)]
    has_tests = bool(test_files)

    # Check whether all commits are "initial plan" placeholders
    commits = list(pr.get_commits())
    all_initial = bool(commits) and all(
        re.search(
            r"initial\s+plan|initial commit|placeholder|wip",
            c.commit.message,
            re.IGNORECASE,
        )
        for c in commits
    )

    promote = (
        file_count > 0
        and not has_todo
        and has_description
        and not all_initial
    )

    reason_parts: list[str] = []
    if file_count > 0:
        reason_parts.append(f"{file_count} file(s) changed")
    else:
        reason_parts.append("no files changed")
    if has_tests:
        reason_parts.append("test files present")
    if has_todo:
        reason_parts.append("TODO/FIXME markers found")
    if not has_description:
        reason_parts.append("description too short or missing")
    if all_initial and commits:
        reason_parts.append("only initial-plan commits detected")
    if has_issue_ref:
        reason_parts.append("source issue referenced")

    reason = "; ".join(reason_parts) if reason_parts else "no changes detected"

    result: dict[str, Any] = {
        "promote": promote,
        "reason": reason,
        "details": {
            "file_count": file_count,
            "has_tests": has_tests,
            "has_todo_markers": has_todo,
            "has_description": has_description,
            "has_issue_ref": has_issue_ref,
            "commit_count": len(commits),
        },
    }
    _log_decision("pr_ready_check", {"pr": pr_url, "promote": promote, "reason": reason})
    return result


def _score_pr(pr: Any, files: list[Any]) -> tuple[int, dict[str, Any]]:
    """Score a pull request for duplicate-triage purposes.

    Scoring rubric:
    - Up to 20 points for number of files changed (2 per file).
    - 3 points per test file.
    - Up to 10 points for description length (1 per 50 chars).
    - 1 point per commit (capped at 5).

    Args:
        pr: PyGithub PullRequest object.
        files: List of file objects from pr.get_files().

    Returns:
        Tuple of (score, details_dict).
    """
    file_count = len(files)
    score = min(file_count * 2, 20)

    test_count = sum(
        1 for f in files if re.search(r"test", f.filename, re.IGNORECASE)
    )
    score += test_count * 3

    body = pr.body or ""
    score += min(len(body) // 50, 10)

    commits = list(pr.get_commits())
    commit_count = len(commits)
    score += min(commit_count, 5)

    details: dict[str, Any] = {
        "file_count": file_count,
        "test_count": test_count,
        "description_length": len(body),
        "commit_count": commit_count,
    }
    return score, details


def triage_duplicates(pr_a_url: str, pr_b_url: str) -> dict[str, Any]:
    """Recommend which of two duplicate PRs to keep.

    Scores each PR on: files changed, test coverage, description completeness,
    and commit count. The higher-scoring PR is recommended for retention.

    Args:
        pr_a_url: Full GitHub URL for the first PR.
        pr_b_url: Full GitHub URL for the second PR.

    Returns:
        Dictionary with keys:
            keep   (str):  "pr-a" or "pr-b".
            close  (str):  "pr-a" or "pr-b".
            reason (str):  Human-readable explanation.
            scores (dict): Numeric scores for each PR.
            details(dict): Sub-scores for each PR.
    """
    owner_a, repo_a_name, pr_a_num = _parse_github_url(pr_a_url)
    owner_b, repo_b_name, pr_b_num = _parse_github_url(pr_b_url)

    g = _get_github_client()
    pr_a = g.get_repo(f"{owner_a}/{repo_a_name}").get_pull(pr_a_num)
    pr_b = g.get_repo(f"{owner_b}/{repo_b_name}").get_pull(pr_b_num)

    files_a = list(pr_a.get_files())
    files_b = list(pr_b.get_files())

    score_a, details_a = _score_pr(pr_a, files_a)
    score_b, details_b = _score_pr(pr_b, files_b)

    if score_a >= score_b:
        keep, close, kept_url = "pr-a", "pr-b", pr_a_url
        reason = f"PR-A scores higher ({score_a} vs {score_b}): more complete implementation"
    else:
        keep, close, kept_url = "pr-b", "pr-a", pr_b_url
        reason = f"PR-B scores higher ({score_b} vs {score_a}): more complete implementation"

    result: dict[str, Any] = {
        "keep": keep,
        "close": close,
        "reason": reason,
        "scores": {"pr-a": score_a, "pr-b": score_b},
        "details": {"pr-a": details_a, "pr-b": details_b},
    }
    _log_decision(
        "closed_duplicate",
        {
            "pr_a": pr_a_url,
            "pr_b": pr_b_url,
            "kept": kept_url,
            "reason": reason,
        },
    )
    return result


def check_dispatch_safe(issue_url: str) -> dict[str, Any]:
    """Determine whether a backlog issue is safe to dispatch now.

    Checks:
    - Issue labels for "blocked" or "needs-human-review".
    - Active agent PR count against a maximum capacity of 6.
    - Issue body for explicit dependency mentions.

    Args:
        issue_url: Full GitHub issue URL.

    Returns:
        Dictionary with keys:
            dispatch (bool): Whether it is safe to dispatch.
            reason   (str):  Human-readable explanation.
            details  (dict): Granular sub-checks.
    """
    owner, repo_name, issue_number = _parse_github_url(issue_url)
    g = _get_github_client()
    repo = g.get_repo(f"{owner}/{repo_name}")
    issue = repo.get_issue(issue_number)

    labels = [lbl.name.lower() for lbl in issue.labels]
    is_blocked = any(
        lbl in ("blocked", "needs-human-review", "on-hold", "do not merge")
        for lbl in labels
    )

    open_prs = list(repo.get_pulls(state="open"))
    draft_prs = [pr for pr in open_prs if pr.draft]
    active_count = len(draft_prs)
    capacity_available = active_count < _MAX_CAPACITY

    body = issue.body or ""
    has_blocking_dependency = bool(
        re.search(r"depends\s+on\s+#\d+|blocked\s+by\s+#\d+", body, re.IGNORECASE)
    )

    dispatch = not is_blocked and capacity_available and not has_blocking_dependency

    reason_parts: list[str] = []
    if is_blocked:
        blocking = [lbl for lbl in labels if lbl in ("blocked", "needs-human-review", "on-hold")]
        reason_parts.append(f"has blocking label(s): {', '.join(blocking)}")
    if not capacity_available:
        reason_parts.append(
            f"capacity full ({active_count}/{_MAX_CAPACITY} active draft PRs)"
        )
    if has_blocking_dependency:
        reason_parts.append("issue body references a blocking dependency")
    if dispatch:
        reason_parts.append(
            f"no blocking dependencies; capacity available ({active_count}/{_MAX_CAPACITY})"
        )

    reason = "; ".join(reason_parts) if reason_parts else "unable to determine"

    result: dict[str, Any] = {
        "dispatch": dispatch,
        "reason": reason,
        "details": {
            "labels": labels,
            "active_draft_pr_count": active_count,
            "capacity": _MAX_CAPACITY,
            "has_blocking_labels": is_blocked,
            "has_blocking_dependency": has_blocking_dependency,
        },
    }
    _log_decision("dispatch_check", {"issue": issue_url, "dispatch": dispatch, "reason": reason})
    return result


def check_stalled(pr_url: str, idle_minutes: int = 60) -> dict[str, Any]:
    """Determine whether an agent PR is stalled or just working on a slow task.

    Complexity is inferred from PR labels and file count:
    - low  (P4, effort:small, ≤1 file)  → stalled after 30 min
    - high (P1, effort:large, >5 files) → stalled after 90 min
    - medium (default)                  → stalled after 60 min

    Args:
        pr_url: Full GitHub pull-request URL.
        idle_minutes: Minutes the PR has been idle (no new commits/comments).

    Returns:
        Dictionary with keys:
            stalled (bool): Whether the PR is considered stalled.
            reason  (str):  Human-readable explanation.
            details (dict): Complexity estimate and thresholds.
    """
    owner, repo_name, pr_number = _parse_github_url(pr_url)
    g = _get_github_client()
    repo = g.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    files = list(pr.get_files())
    file_count = len(files)

    pr_labels = [lbl.name.lower() for lbl in pr.labels]
    complexity = _estimate_complexity(pr_labels, file_count)
    stall_threshold = _STALL_THRESHOLDS[complexity]

    stalled = idle_minutes > stall_threshold

    if stalled:
        reason = (
            f"idle for {idle_minutes} min exceeds {stall_threshold} min threshold "
            f"for {complexity}-complexity task ({file_count} file(s) changed)"
        )
    else:
        remaining = stall_threshold - idle_minutes
        reason = (
            f"{complexity}-complexity task; {idle_minutes} min idle is within the "
            f"{stall_threshold} min threshold ({remaining} min remaining)"
        )
        if file_count > 0:
            reason += f"; {file_count} file(s) changed"

    result: dict[str, Any] = {
        "stalled": stalled,
        "reason": reason,
        "details": {
            "complexity": complexity,
            "idle_minutes": idle_minutes,
            "stall_threshold_minutes": stall_threshold,
            "file_count": file_count,
            "pr_labels": pr_labels,
        },
    }
    _log_decision(
        "stall_check",
        {"pr": pr_url, "stalled": stalled, "idle_minutes": idle_minutes, "reason": reason},
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate decision mode."""
    parser = argparse.ArgumentParser(
        description="Orchestrator agent — intelligent PR triage and dispatch decisions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/orchestrator_agent.py --mode pr-ready-check --pr-url https://github.com/owner/repo/pull/123
  python3 scripts/orchestrator_agent.py --mode duplicate-triage --pr-a <url> --pr-b <url>
  python3 scripts/orchestrator_agent.py --mode dispatch-check --issue https://github.com/owner/repo/issues/42
  python3 scripts/orchestrator_agent.py --mode stall-check --pr-url <url> --idle-minutes 45
        """,
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["pr-ready-check", "duplicate-triage", "dispatch-check", "stall-check"],
        help="Decision mode to run",
    )
    parser.add_argument("--pr-url", help="GitHub PR URL (pr-ready-check, stall-check)")
    parser.add_argument("--pr-a", help="First PR URL (duplicate-triage)")
    parser.add_argument("--pr-b", help="Second PR URL (duplicate-triage)")
    parser.add_argument("--issue", help="GitHub issue URL (dispatch-check)")
    parser.add_argument(
        "--idle-minutes",
        type=int,
        default=60,
        help="Minutes the PR has been idle (stall-check, default: 60)",
    )

    args = parser.parse_args()

    try:
        if args.mode == "pr-ready-check":
            if not args.pr_url:
                parser.error("--pr-url is required for --mode pr-ready-check")
            result = check_pr_ready(args.pr_url)

        elif args.mode == "duplicate-triage":
            if not args.pr_a or not args.pr_b:
                parser.error("--pr-a and --pr-b are required for --mode duplicate-triage")
            result = triage_duplicates(args.pr_a, args.pr_b)

        elif args.mode == "dispatch-check":
            if not args.issue:
                parser.error("--issue is required for --mode dispatch-check")
            result = check_dispatch_safe(args.issue)

        else:  # stall-check
            if not args.pr_url:
                parser.error("--pr-url is required for --mode stall-check")
            result = check_stalled(args.pr_url, args.idle_minutes)

        print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode())

    except Exception as exc:
        logger.error("Orchestrator failed: %s", exc)
        print(orjson.dumps({"error": str(exc)}, option=orjson.OPT_INDENT_2).decode())
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
