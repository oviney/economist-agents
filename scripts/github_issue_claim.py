#!/usr/bin/env python3
"""GitHub issue ownership claims for multi-agent coordination."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    import orjson
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test envs

    class _OrjsonCompat:
        """Small compatibility wrapper for environments without orjson."""

        @staticmethod
        def loads(data: str | bytes) -> Any:
            if isinstance(data, bytes):
                data = data.decode()
            return json.loads(data)

        @staticmethod
        def dumps(data: Any) -> bytes:
            return json.dumps(data, separators=(",", ":")).encode()

        JSONDecodeError = json.JSONDecodeError

    orjson = _OrjsonCompat()

DEFAULT_REPO = "oviney/economist-agents"
DEFAULT_TTL_HOURS = 24
CLAIM_LABEL = "status:claimed"
OWNER_LABEL_PREFIX = "owner:"
CLAIM_COMMENT_PREFIX = "<!-- agent-claim "
CLAIM_COMMENT_SUFFIX = " -->"
LABEL_CONFIG: dict[str, tuple[str, str]] = {
    CLAIM_LABEL: ("0E8A16", "Issue currently claimed by an agent runtime"),
    "owner:claude": ("1D76DB", "Claimed by Claude Code"),
    "owner:codex": ("0969DA", "Claimed by Codex"),
    "owner:copilot": ("8250DF", "Claimed by GitHub Copilot"),
}


@dataclass(frozen=True)
class ClaimStatus:
    """Current ownership state for an issue."""

    issue_number: int
    runtime: str | None
    active: bool
    claimed_at: datetime | None = None
    expires_at: datetime | None = None
    files: tuple[str, ...] = ()
    source: str = "none"


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware UTC datetime."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    """Format a datetime as ISO-8601 with trailing Z."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class GitHubIssueClaimer:
    """Manage GitHub issue claims using labels plus lease comments."""

    def __init__(self, repo: str = DEFAULT_REPO):
        self.repo = repo

    def gh_api(self, endpoint: str, method: str = "GET") -> dict[str, Any] | list[Any]:
        """Call the GitHub API via ``gh``."""
        cmd = ["gh", "api", endpoint]
        if method != "GET":
            cmd.extend(["-X", method])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
        return orjson.loads(result.stdout)

    def gh_run(self, args: list[str]) -> str:
        """Run a ``gh`` command and return stdout."""
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def ensure_labels_exist(self, labels: list[str]) -> None:
        """Create claim labels if they do not already exist."""
        for label in labels:
            color, description = LABEL_CONFIG.get(
                label, ("BFD4F2", "Agent ownership coordination label")
            )
            self.gh_run(
                [
                    "label",
                    "create",
                    label,
                    "--repo",
                    self.repo,
                    "--color",
                    color,
                    "--description",
                    description,
                    "--force",
                ]
            )

    def fetch_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch issue metadata."""
        return self.gh_api(f"repos/{self.repo}/issues/{issue_number}")

    def fetch_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Fetch all comments for an issue."""
        response = self.gh_api(f"repos/{self.repo}/issues/{issue_number}/comments")
        return response if isinstance(response, list) else []

    def parse_claim_comment(self, body: str) -> dict[str, Any] | None:
        """Parse a structured claim payload from a comment body."""
        if not body.startswith(CLAIM_COMMENT_PREFIX) or not body.endswith(
            CLAIM_COMMENT_SUFFIX
        ):
            return None
        payload = body[len(CLAIM_COMMENT_PREFIX) : -len(CLAIM_COMMENT_SUFFIX)]
        try:
            decoded = orjson.loads(payload)
        except orjson.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None

    def build_claim_comment(
        self, runtime: str, ttl_hours: int, files: list[str] | None = None
    ) -> str:
        """Build a machine-readable claim comment."""
        claimed_at = _utc_now()
        payload = {
            "runtime": runtime,
            "claimed_at": _format_timestamp(claimed_at),
            "expires_at": _format_timestamp(
                claimed_at + timedelta(hours=max(ttl_hours, 1))
            ),
            "files": files or [],
        }
        return f"{CLAIM_COMMENT_PREFIX}{orjson.dumps(payload).decode()}{CLAIM_COMMENT_SUFFIX}"

    def _extract_label_runtime(self, labels: set[str]) -> str | None:
        """Return the sole owner label runtime when present."""
        owner_labels = sorted(
            label.removeprefix(OWNER_LABEL_PREFIX)
            for label in labels
            if label.startswith(OWNER_LABEL_PREFIX)
        )
        return owner_labels[0] if owner_labels else None

    def get_claim_status(
        self, issue_number: int, now: datetime | None = None
    ) -> ClaimStatus:
        """Return current claim state for an issue."""
        issue = self.fetch_issue(issue_number)
        labels = {label["name"] for label in issue.get("labels", [])}
        comments = self.fetch_issue_comments(issue_number)

        latest_payload: dict[str, Any] | None = None
        for comment in reversed(comments):
            latest_payload = self.parse_claim_comment(comment.get("body", ""))
            if latest_payload:
                break

        current_time = now or _utc_now()
        label_runtime = self._extract_label_runtime(labels)

        if latest_payload:
            expires_at = _parse_timestamp(str(latest_payload.get("expires_at", "")))
            runtime = (
                str(latest_payload.get("runtime", "") or label_runtime or "") or None
            )
            claimed_at = _parse_timestamp(str(latest_payload.get("claimed_at", "")))
            files = tuple(
                str(path)
                for path in latest_payload.get("files", [])
                if isinstance(path, str) and path
            )
            active = CLAIM_LABEL in labels and (
                expires_at is None or expires_at > current_time
            )
            return ClaimStatus(
                issue_number=issue_number,
                runtime=runtime,
                active=active,
                claimed_at=claimed_at,
                expires_at=expires_at,
                files=files,
                source="comment",
            )

        active = CLAIM_LABEL in labels and label_runtime is not None
        return ClaimStatus(
            issue_number=issue_number,
            runtime=label_runtime,
            active=active,
            source="label" if active else "none",
        )

    def _set_issue_labels(
        self, issue_number: int, add: list[str], remove: list[str]
    ) -> None:
        """Apply label changes to an issue."""
        args = ["issue", "edit", str(issue_number), "--repo", self.repo]
        if add:
            args.extend(["--add-label", ",".join(add)])
        if remove:
            args.extend(["--remove-label", ",".join(remove)])
        self.gh_run(args)

    def _post_issue_comment(self, issue_number: int, body: str) -> None:
        """Post an issue comment."""
        self.gh_run(
            [
                "issue",
                "comment",
                str(issue_number),
                "--repo",
                self.repo,
                "--body",
                body,
            ]
        )

    def claim_issue(
        self,
        issue_number: int,
        runtime: str,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        files: list[str] | None = None,
        force: bool = False,
    ) -> ClaimStatus:
        """Claim an issue for a specific runtime."""
        self.ensure_labels_exist([CLAIM_LABEL, f"{OWNER_LABEL_PREFIX}{runtime}"])
        current = self.get_claim_status(issue_number)
        if (
            current.active
            and current.runtime
            and current.runtime != runtime
            and not force
        ):
            raise RuntimeError(
                f"Issue #{issue_number} is actively claimed by {current.runtime} "
                f"until {_format_timestamp(current.expires_at) if current.expires_at else 'unknown'}"
            )

        issue = self.fetch_issue(issue_number)
        existing_labels = {label["name"] for label in issue.get("labels", [])}
        remove_labels = sorted(
            label
            for label in existing_labels
            if label.startswith(OWNER_LABEL_PREFIX)
            and label != f"{OWNER_LABEL_PREFIX}{runtime}"
        )
        add_labels = [
            label
            for label in [CLAIM_LABEL, f"{OWNER_LABEL_PREFIX}{runtime}"]
            if label not in existing_labels
        ]

        self._set_issue_labels(issue_number, add_labels, remove_labels)
        self._post_issue_comment(
            issue_number, self.build_claim_comment(runtime, ttl_hours, files)
        )
        return self.get_claim_status(issue_number)

    def release_issue(self, issue_number: int, runtime: str) -> None:
        """Release an issue claim for a runtime."""
        current = self.get_claim_status(issue_number)
        if current.runtime and current.runtime != runtime and current.active:
            raise RuntimeError(
                f"Issue #{issue_number} is owned by {current.runtime}, not {runtime}"
            )
        issue = self.fetch_issue(issue_number)
        existing_labels = {label["name"] for label in issue.get("labels", [])}
        remove_labels = [
            label
            for label in [CLAIM_LABEL, f"{OWNER_LABEL_PREFIX}{runtime}"]
            if label in existing_labels
        ]
        self._set_issue_labels(issue_number, [], remove_labels)
        self._post_issue_comment(
            issue_number,
            f"Ownership released by `{runtime}` at `{_format_timestamp(_utc_now())}`.",
        )

    def check_issue_access(self, issue_number: int, runtime: str) -> tuple[bool, str]:
        """Validate whether a runtime may safely work on an issue."""
        current = self.get_claim_status(issue_number)
        if current.active and current.runtime == runtime:
            expiry = (
                _format_timestamp(current.expires_at)
                if current.expires_at is not None
                else "unknown"
            )
            return True, f"Issue #{issue_number} claimed by {runtime} until {expiry}"
        if current.active and current.runtime and current.runtime != runtime:
            expiry = (
                _format_timestamp(current.expires_at)
                if current.expires_at is not None
                else "unknown"
            )
            return (
                False,
                f"Issue #{issue_number} is claimed by {current.runtime} until {expiry}",
            )
        if current.runtime and not current.active:
            return (
                False,
                f"Issue #{issue_number} has an expired claim from {current.runtime}; reclaim it before editing",
            )
        return (
            False,
            f"Issue #{issue_number} is unclaimed; claim it before starting work",
        )

    def find_next_claimable_issue(self, labels: list[str], runtime: str) -> int | None:
        """Find the next issue not actively claimed by another runtime."""
        query = ",".join(labels)
        response = self.gh_api(
            f"repos/{self.repo}/issues?labels={query}&state=open&sort=created&direction=asc"
        )
        issues = response if isinstance(response, list) else []
        for issue in issues:
            body = issue.get("body", "")
            if "## Stories" in body or "Epic:" in issue.get("title", ""):
                continue
            issue_number = int(issue["number"])
            claim = self.get_claim_status(issue_number)
            if not claim.active or claim.runtime == runtime:
                return issue_number
        return None


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="GitHub issue ownership claims")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository")
    subparsers = parser.add_subparsers(dest="command", required=True)

    claim_parser = subparsers.add_parser("claim", help="Claim an issue")
    claim_parser.add_argument("issue", type=int)
    claim_parser.add_argument(
        "--runtime", default=os.environ.get("AGENT_RUNTIME", "codex")
    )
    claim_parser.add_argument("--ttl-hours", type=int, default=DEFAULT_TTL_HOURS)
    claim_parser.add_argument("--files", nargs="*", default=[])
    claim_parser.add_argument("--force", action="store_true")

    status_parser = subparsers.add_parser("status", help="Show claim status")
    status_parser.add_argument("issue", type=int)

    check_parser = subparsers.add_parser("check", help="Check issue access")
    check_parser.add_argument("issue", type=int)
    check_parser.add_argument(
        "--runtime", default=os.environ.get("AGENT_RUNTIME", "codex")
    )

    next_parser = subparsers.add_parser("next", help="Find next claimable issue")
    next_parser.add_argument(
        "--runtime", default=os.environ.get("AGENT_RUNTIME", "codex")
    )
    next_parser.add_argument("--labels", nargs="+", default=["enhancement", "quality"])
    next_parser.add_argument("--claim", action="store_true")
    next_parser.add_argument("--ttl-hours", type=int, default=DEFAULT_TTL_HOURS)

    release_parser = subparsers.add_parser("release", help="Release an issue")
    release_parser.add_argument("issue", type=int)
    release_parser.add_argument(
        "--runtime", default=os.environ.get("AGENT_RUNTIME", "codex")
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()
    claimer = GitHubIssueClaimer(repo=args.repo)

    if args.command == "claim":
        status = claimer.claim_issue(
            args.issue,
            runtime=args.runtime,
            ttl_hours=args.ttl_hours,
            files=args.files,
            force=args.force,
        )
        print(
            f"Claimed issue #{status.issue_number} for {status.runtime} until "
            f"{_format_timestamp(status.expires_at) if status.expires_at else 'unknown'}"
        )
        return 0

    if args.command == "status":
        status = claimer.get_claim_status(args.issue)
        if not status.runtime:
            print(f"Issue #{args.issue} is unclaimed")
            return 0
        active_text = "active" if status.active else "expired"
        expires = _format_timestamp(status.expires_at) if status.expires_at else "n/a"
        print(
            f"Issue #{args.issue}: {active_text} claim by {status.runtime} (expires {expires})"
        )
        return 0

    if args.command == "check":
        allowed, message = claimer.check_issue_access(args.issue, args.runtime)
        print(message)
        return 0 if allowed else 1

    if args.command == "next":
        issue_number = claimer.find_next_claimable_issue(args.labels, args.runtime)
        if issue_number is None:
            print("No claimable issues found")
            return 1
        if args.claim:
            claimer.claim_issue(
                issue_number, runtime=args.runtime, ttl_hours=args.ttl_hours
            )
        print(issue_number)
        return 0

    if args.command == "release":
        claimer.release_issue(args.issue, args.runtime)
        print(f"Released issue #{args.issue} for {args.runtime}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
