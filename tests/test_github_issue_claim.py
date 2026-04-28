"""Tests for multi-agent GitHub issue claiming."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import scripts.github_issue_claim as claim_module
from scripts.github_issue_claim import CLAIM_LABEL, GitHubIssueClaimer


def _issue_payload(*labels: str) -> dict[str, object]:
    """Create a minimal GitHub issue payload."""
    return {"labels": [{"name": label} for label in labels], "body": "", "title": "T"}


def _claim_comment(runtime: str, *, expires_at: datetime) -> dict[str, str]:
    """Create a structured claim comment payload."""
    claimed = expires_at - timedelta(hours=1)
    comment = (
        "<!-- agent-claim "
        f'{{"runtime":"{runtime}","claimed_at":"{claimed.isoformat().replace("+00:00", "Z")}","expires_at":"{expires_at.isoformat().replace("+00:00", "Z")}","files":["scripts/example.py"]}}'
        " -->"
    )
    return {"body": comment}


def test_get_claim_status_uses_active_comment_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh claim comment should be treated as the active owner."""
    claimer = GitHubIssueClaimer()
    now = datetime(2026, 4, 26, 12, 0, tzinfo=UTC)
    expires_at = now + timedelta(hours=4)

    monkeypatch.setattr(
        claimer,
        "fetch_issue",
        lambda issue_number: _issue_payload(CLAIM_LABEL, "owner:claude"),
    )
    monkeypatch.setattr(
        claimer,
        "fetch_issue_comments",
        lambda issue_number: [_claim_comment("claude", expires_at=expires_at)],
    )

    status = claimer.get_claim_status(123, now=now)
    assert status.active is True
    assert status.runtime == "claude"
    assert status.expires_at == expires_at
    assert status.files == ("scripts/example.py",)
    assert status.source == "comment"


def test_check_issue_access_blocks_other_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Another runtime's active claim should block work."""
    claimer = GitHubIssueClaimer()
    now = datetime(2026, 4, 26, 12, 0, tzinfo=UTC)
    expires_at = now + timedelta(hours=2)

    monkeypatch.setattr(claim_module, "_utc_now", lambda: now)
    monkeypatch.setattr(
        claimer,
        "fetch_issue",
        lambda issue_number: _issue_payload(CLAIM_LABEL, "owner:claude"),
    )
    monkeypatch.setattr(
        claimer,
        "fetch_issue_comments",
        lambda issue_number: [_claim_comment("claude", expires_at=expires_at)],
    )

    allowed, message = claimer.check_issue_access(77, "codex")
    assert allowed is False
    assert "claimed by claude" in message


def test_find_next_claimable_issue_skips_active_other_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue selection should skip work actively claimed by another runtime."""
    claimer = GitHubIssueClaimer()
    now = datetime(2026, 4, 26, 12, 0, tzinfo=UTC)
    future = now + timedelta(hours=4)
    issues = [
        {"number": 10, "title": "First", "body": ""},
        {"number": 11, "title": "Second", "body": ""},
    ]

    monkeypatch.setattr(claim_module, "_utc_now", lambda: now)
    monkeypatch.setattr(
        claimer,
        "gh_api",
        lambda endpoint: (
            issues
            if "issues?" in endpoint
            else _issue_payload(CLAIM_LABEL, "owner:claude")
            if endpoint.endswith("/10")
            else _issue_payload()
        ),
    )
    monkeypatch.setattr(
        claimer,
        "fetch_issue_comments",
        lambda issue_number: (
            [_claim_comment("claude", expires_at=future)] if issue_number == 10 else []
        ),
    )

    next_issue = claimer.find_next_claimable_issue(["enhancement", "quality"], "codex")
    assert next_issue == 11


def test_claim_issue_rejects_active_other_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim attempts should fail when another runtime holds the lease."""
    claimer = GitHubIssueClaimer()
    now = datetime(2026, 4, 26, 12, 0, tzinfo=UTC)
    future = now + timedelta(hours=4)

    monkeypatch.setattr(claim_module, "_utc_now", lambda: now)
    monkeypatch.setattr(claimer, "ensure_labels_exist", lambda labels: None)
    monkeypatch.setattr(
        claimer,
        "fetch_issue",
        lambda issue_number: _issue_payload(CLAIM_LABEL, "owner:claude"),
    )
    monkeypatch.setattr(
        claimer,
        "fetch_issue_comments",
        lambda issue_number: [_claim_comment("claude", expires_at=future)],
    )

    with pytest.raises(RuntimeError, match="actively claimed by claude"):
        claimer.claim_issue(5, "codex")
