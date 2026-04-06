#!/usr/bin/env python3
"""Tests for scripts/orchestrator_agent.py.

Unit tests for all four decision modes (pr-ready-check, duplicate-triage,
dispatch-check, stall-check) using mocked GitHub API responses.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure scripts/ is importable.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import orchestrator_agent as oa  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# Helpers to build lightweight mock PyGithub objects
# ─────────────────────────────────────────────────────────────────────────────


def _make_file(filename: str, patch_text: str = "") -> Mock:
    """Return a mock PullRequestFile-like object."""
    f = Mock()
    f.filename = filename
    f.patch = patch_text
    return f


def _make_commit(message: str) -> Mock:
    c = Mock()
    c.commit = Mock()
    c.commit.message = message
    return c


def _make_label(name: str) -> Mock:
    lbl = Mock()
    lbl.name = name
    return lbl


def _make_pr(
    body: str = "Closes #42 — implementation complete.",
    files: list[Mock] | None = None,
    commits: list[Mock] | None = None,
    labels: list[Mock] | None = None,
    draft: bool = False,
) -> Mock:
    pr = Mock()
    pr.body = body
    pr.draft = draft
    pr.labels = labels or []
    pr.get_files.return_value = files or []
    pr.get_commits.return_value = commits or [_make_commit("feat: implement feature")]
    return pr


def _make_issue(
    body: str = "Add support for new feature.",
    labels: list[Mock] | None = None,
) -> Mock:
    issue = Mock()
    issue.body = body
    issue.labels = labels or []
    return issue


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

PR_URL = "https://github.com/owner/repo/pull/1"
PR_A_URL = "https://github.com/owner/repo/pull/2"
PR_B_URL = "https://github.com/owner/repo/pull/3"
ISSUE_URL = "https://github.com/owner/repo/issues/10"


@pytest.fixture(autouse=True)
def _no_disk_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect state file to a temp directory so tests are isolated."""
    monkeypatch.setattr(oa, "STATE_FILE", tmp_path / "orchestrator_state.json")


# ─────────────────────────────────────────────────────────────────────────────
# _parse_github_url
# ─────────────────────────────────────────────────────────────────────────────


class TestParseGithubUrl:
    def test_parses_pr_url(self) -> None:
        owner, repo, number = oa._parse_github_url(
            "https://github.com/oviney/blog/pull/628"
        )
        assert owner == "oviney"
        assert repo == "blog"
        assert number == 628

    def test_parses_issue_url(self) -> None:
        owner, repo, number = oa._parse_github_url(
            "https://github.com/acme/project/issues/99"
        )
        assert owner == "acme"
        assert repo == "project"
        assert number == 99

    def test_http_scheme_accepted(self) -> None:
        owner, repo, number = oa._parse_github_url(
            "http://github.com/org/myrepo/pull/7"
        )
        assert number == 7

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid GitHub"):
            oa._parse_github_url("https://example.com/not/a/pr")

    def test_missing_number_raises(self) -> None:
        with pytest.raises(ValueError):
            oa._parse_github_url("https://github.com/owner/repo/pull/")


# ─────────────────────────────────────────────────────────────────────────────
# _has_todo_markers
# ─────────────────────────────────────────────────────────────────────────────


class TestHasTodoMarkers:
    def test_detects_todo(self) -> None:
        assert oa._has_todo_markers("+    # TODO: implement this") is True

    def test_detects_fixme(self) -> None:
        assert oa._has_todo_markers("+    # FIXME: broken") is True

    def test_detects_placeholder(self) -> None:
        assert oa._has_todo_markers("+    PLACEHOLDER = True") is True

    def test_detects_wip(self) -> None:
        assert oa._has_todo_markers("+    # WIP — not done") is True

    def test_ignores_removed_lines(self) -> None:
        # A removed TODO should not trigger
        assert oa._has_todo_markers("-    # TODO: old code") is False

    def test_clean_diff(self) -> None:
        assert oa._has_todo_markers("+    return 42") is False

    def test_none_patch(self) -> None:
        assert oa._has_todo_markers(None) is False

    def test_empty_patch(self) -> None:
        assert oa._has_todo_markers("") is False


# ─────────────────────────────────────────────────────────────────────────────
# _estimate_complexity
# ─────────────────────────────────────────────────────────────────────────────


class TestEstimateComplexity:
    def test_large_effort_label(self) -> None:
        assert oa._estimate_complexity(["effort:large"], 2) == "high"

    def test_p1_label(self) -> None:
        assert oa._estimate_complexity(["p1"], 1) == "high"

    def test_small_effort_label(self) -> None:
        assert oa._estimate_complexity(["effort:small"], 4) == "low"

    def test_p4_label(self) -> None:
        assert oa._estimate_complexity(["p4"], 3) == "low"

    def test_many_files_without_label(self) -> None:
        assert oa._estimate_complexity([], 6) == "high"

    def test_one_file_without_label(self) -> None:
        assert oa._estimate_complexity([], 1) == "low"

    def test_medium_default(self) -> None:
        assert oa._estimate_complexity([], 3) == "medium"


# ─────────────────────────────────────────────────────────────────────────────
# State persistence
# ─────────────────────────────────────────────────────────────────────────────


class TestStatePersistence:
    def test_load_empty_when_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(oa, "STATE_FILE", tmp_path / "missing.json")
        assert oa._load_state() == []

    def test_round_trip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(oa, "STATE_FILE", tmp_path / "state.json")
        oa._save_state([{"action": "test", "ts": "2026-01-01T00:00Z"}])
        loaded = oa._load_state()
        assert len(loaded) == 1
        assert loaded[0]["action"] == "test"

    def test_log_decision_appends(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(oa, "STATE_FILE", tmp_path / "state.json")
        oa._log_decision("promoted", {"pr": "blog#1"})
        oa._log_decision("promoted", {"pr": "blog#2"})
        state = oa._load_state()
        assert len(state) == 2
        assert state[0]["action"] == "promoted"
        assert "ts" in state[0]

    def test_corrupted_state_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{{{")
        monkeypatch.setattr(oa, "STATE_FILE", bad)
        assert oa._load_state() == []


# ─────────────────────────────────────────────────────────────────────────────
# check_pr_ready
# ─────────────────────────────────────────────────────────────────────────────


def _github_client_for_pr(pr: Mock) -> Mock:
    """Return a mock GitHub client whose get_repo().get_pull() returns pr."""
    repo_mock = Mock()
    repo_mock.get_pull.return_value = pr
    client = Mock()
    client.get_repo.return_value = repo_mock
    return client


class TestCheckPrReady:
    def test_promote_true_for_complete_pr(self) -> None:
        pr = _make_pr(
            body="Closes #10. Full implementation with tests added to ensure correctness.",
            files=[
                _make_file("src/feature.py", "+ def feature(): pass"),
                _make_file("tests/test_feature.py", "+ def test_feature(): pass"),
            ],
            commits=[_make_commit("feat: add feature")],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        assert result["promote"] is True
        assert "2 file(s) changed" in result["reason"]
        assert result["details"]["has_tests"] is True
        assert result["details"]["has_issue_ref"] is True

    def test_promote_false_for_empty_pr(self) -> None:
        pr = _make_pr(files=[], commits=[_make_commit("feat: start")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        assert result["promote"] is False
        assert result["details"]["file_count"] == 0

    def test_promote_false_when_todo_markers_present(self) -> None:
        pr = _make_pr(
            body="Closes #5. Partial implementation.",
            files=[_make_file("src/x.py", "+    # TODO: finish this")],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        assert result["promote"] is False
        assert result["details"]["has_todo_markers"] is True

    def test_promote_false_for_initial_plan_only(self) -> None:
        pr = _make_pr(
            body="Closes #3.",
            files=[_make_file("src/f.py", "+pass")],
            commits=[_make_commit("Initial plan"), _make_commit("initial commit")],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        assert result["promote"] is False

    def test_promote_false_for_short_description(self) -> None:
        pr = _make_pr(
            body="fix",  # too short
            files=[_make_file("a.py", "+x=1")],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        assert result["promote"] is False
        assert result["details"]["has_description"] is False

    def test_result_has_required_keys(self) -> None:
        pr = _make_pr()
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            result = oa.check_pr_ready(PR_URL)
        for key in ("promote", "reason", "details"):
            assert key in result

    def test_decision_logged_to_state(self) -> None:
        pr = _make_pr(files=[_make_file("f.py", "+x=1")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_pr(pr)):
            oa.check_pr_ready(PR_URL)
        state = oa._load_state()
        assert len(state) == 1
        assert state[0]["action"] == "pr_ready_check"

    def test_invalid_url_propagates_error(self) -> None:
        with pytest.raises(ValueError):
            oa.check_pr_ready("https://example.com/not-a-pr")


# ─────────────────────────────────────────────────────────────────────────────
# triage_duplicates
# ─────────────────────────────────────────────────────────────────────────────


def _github_client_for_two_prs(pr_a: Mock, pr_b: Mock) -> Mock:
    """Return a mock GitHub client for triage_duplicates."""
    repo_a = Mock()
    repo_a.get_pull.return_value = pr_a
    repo_b = Mock()
    repo_b.get_pull.return_value = pr_b
    client = Mock()
    # get_repo called twice with different args; return different repos by side_effect
    client.get_repo.side_effect = [repo_a, repo_b]
    return client


class TestTriageDuplicates:
    def test_keeps_pr_with_more_files(self) -> None:
        pr_a = _make_pr(
            body="Closes #1. Implementation.",
            files=[_make_file(f"src/f{i}.py", "+x=1") for i in range(5)],
        )
        pr_b = _make_pr(
            body="Fix.",
            files=[_make_file("src/g.py", "+y=2")],
        )
        client = _github_client_for_two_prs(pr_a, pr_b)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.triage_duplicates(PR_A_URL, PR_B_URL)
        assert result["keep"] == "pr-a"
        assert result["close"] == "pr-b"

    def test_keeps_pr_b_when_it_scores_higher(self) -> None:
        pr_a = _make_pr(body="x", files=[_make_file("a.py", "+x=1")])
        pr_b = _make_pr(
            body="Closes #2. Full implementation with tests.",
            files=[
                _make_file("src/b.py", "+x=1"),
                _make_file("tests/test_b.py", "+assert True"),
            ],
            commits=[_make_commit("feat: b"), _make_commit("test: add tests")],
        )
        client = _github_client_for_two_prs(pr_a, pr_b)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.triage_duplicates(PR_A_URL, PR_B_URL)
        assert result["keep"] == "pr-b"

    def test_result_has_required_keys(self) -> None:
        pr_a = _make_pr(files=[_make_file("a.py")])
        pr_b = _make_pr(files=[_make_file("b.py")])
        client = _github_client_for_two_prs(pr_a, pr_b)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.triage_duplicates(PR_A_URL, PR_B_URL)
        for key in ("keep", "close", "reason", "scores", "details"):
            assert key in result

    def test_scores_are_numeric(self) -> None:
        pr_a = _make_pr(files=[_make_file("a.py")])
        pr_b = _make_pr(files=[_make_file("b.py")])
        client = _github_client_for_two_prs(pr_a, pr_b)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.triage_duplicates(PR_A_URL, PR_B_URL)
        assert isinstance(result["scores"]["pr-a"], int)
        assert isinstance(result["scores"]["pr-b"], int)

    def test_decision_logged_to_state(self) -> None:
        pr_a = _make_pr(files=[_make_file("a.py")])
        pr_b = _make_pr(files=[_make_file("b.py")])
        client = _github_client_for_two_prs(pr_a, pr_b)
        with patch.object(oa, "_get_github_client", return_value=client):
            oa.triage_duplicates(PR_A_URL, PR_B_URL)
        state = oa._load_state()
        assert state[0]["action"] == "closed_duplicate"


# ─────────────────────────────────────────────────────────────────────────────
# check_dispatch_safe
# ─────────────────────────────────────────────────────────────────────────────


def _github_client_for_issue(
    issue: Mock,
    open_prs: list[Mock] | None = None,
) -> Mock:
    repo_mock = Mock()
    repo_mock.get_issue.return_value = issue
    repo_mock.get_pulls.return_value = open_prs or []
    client = Mock()
    client.get_repo.return_value = repo_mock
    return client


class TestCheckDispatchSafe:
    def test_dispatch_true_when_all_clear(self) -> None:
        issue = _make_issue(body="Add caching layer for API responses.")
        client = _github_client_for_issue(issue, open_prs=[])
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["dispatch"] is True
        assert "no blocking dependencies" in result["reason"].lower()

    def test_dispatch_false_when_blocked_label(self) -> None:
        issue = _make_issue(labels=[_make_label("blocked")])
        client = _github_client_for_issue(issue)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["dispatch"] is False
        assert "blocked" in result["reason"].lower()

    def test_dispatch_false_when_needs_human_review(self) -> None:
        issue = _make_issue(labels=[_make_label("needs-human-review")])
        client = _github_client_for_issue(issue)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["dispatch"] is False

    def test_dispatch_false_when_capacity_full(self) -> None:
        issue = _make_issue()
        draft_prs = [_make_pr(draft=True) for _ in range(6)]
        client = _github_client_for_issue(issue, open_prs=draft_prs)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["dispatch"] is False
        assert "capacity full" in result["reason"].lower()

    def test_dispatch_false_when_blocking_dependency_in_body(self) -> None:
        issue = _make_issue(body="Depends on #99 being merged first.")
        client = _github_client_for_issue(issue)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["dispatch"] is False
        assert "blocking dependency" in result["reason"].lower()

    def test_result_has_required_keys(self) -> None:
        issue = _make_issue()
        client = _github_client_for_issue(issue)
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        for key in ("dispatch", "reason", "details"):
            assert key in result

    def test_details_include_capacity_info(self) -> None:
        issue = _make_issue()
        client = _github_client_for_issue(issue, open_prs=[_make_pr(draft=True)])
        with patch.object(oa, "_get_github_client", return_value=client):
            result = oa.check_dispatch_safe(ISSUE_URL)
        assert result["details"]["capacity"] == 6
        assert result["details"]["active_draft_pr_count"] == 1

    def test_decision_logged_to_state(self) -> None:
        issue = _make_issue()
        client = _github_client_for_issue(issue)
        with patch.object(oa, "_get_github_client", return_value=client):
            oa.check_dispatch_safe(ISSUE_URL)
        state = oa._load_state()
        assert state[0]["action"] == "dispatch_check"


# ─────────────────────────────────────────────────────────────────────────────
# check_stalled
# ─────────────────────────────────────────────────────────────────────────────


def _github_client_for_stall(pr: Mock) -> Mock:
    repo_mock = Mock()
    repo_mock.get_pull.return_value = pr
    client = Mock()
    client.get_repo.return_value = repo_mock
    return client


class TestCheckStalled:
    def test_not_stalled_for_complex_task_at_60_min(self) -> None:
        pr = _make_pr(
            labels=[_make_label("effort:large")],
            files=[_make_file(f"f{i}.py") for i in range(8)],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, idle_minutes=60)
        assert result["stalled"] is False
        assert result["details"]["complexity"] == "high"
        assert result["details"]["stall_threshold_minutes"] == 90

    def test_stalled_for_simple_task_at_45_min(self) -> None:
        pr = _make_pr(
            labels=[_make_label("effort:small")],
            files=[_make_file("tiny.py")],
        )
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, idle_minutes=45)
        assert result["stalled"] is True
        assert result["details"]["stall_threshold_minutes"] == 30

    def test_stalled_for_medium_task_at_90_min(self) -> None:
        pr = _make_pr(files=[_make_file("a.py"), _make_file("b.py")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, idle_minutes=90)
        assert result["stalled"] is True

    def test_not_stalled_within_threshold(self) -> None:
        pr = _make_pr(files=[_make_file("a.py"), _make_file("b.py")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, idle_minutes=30)
        assert result["stalled"] is False

    def test_default_idle_minutes_is_60(self) -> None:
        pr = _make_pr(files=[_make_file("a.py"), _make_file("b.py")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL)
        # medium complexity threshold is 60 min; idle=60 means stalled
        assert result["details"]["idle_minutes"] == 60

    def test_result_has_required_keys(self) -> None:
        pr = _make_pr()
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, 30)
        for key in ("stalled", "reason", "details"):
            assert key in result

    def test_decision_logged_to_state(self) -> None:
        pr = _make_pr()
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            oa.check_stalled(PR_URL, 30)
        state = oa._load_state()
        assert state[0]["action"] == "stall_check"

    def test_p1_label_sets_high_complexity(self) -> None:
        pr = _make_pr(labels=[_make_label("p1")])
        with patch.object(oa, "_get_github_client", return_value=_github_client_for_stall(pr)):
            result = oa.check_stalled(PR_URL, 60)
        assert result["details"]["complexity"] == "high"
        assert result["stalled"] is False  # 60 < 90 threshold


# ─────────────────────────────────────────────────────────────────────────────
# MCP server importability
# ─────────────────────────────────────────────────────────────────────────────


class TestMcpServerImportable:
    def test_orchestrator_server_importable(self) -> None:
        from mcp_servers import orchestrator_server  # noqa: F401

        assert orchestrator_server.mcp is not None

    def test_all_tools_callable(self) -> None:
        from mcp_servers.orchestrator_server import (
            check_dispatch_safe_tool,
            check_pr_ready_tool,
            check_stalled_tool,
            triage_duplicates_tool,
        )

        assert callable(check_pr_ready_tool)
        assert callable(triage_duplicates_tool)
        assert callable(check_dispatch_safe_tool)
        assert callable(check_stalled_tool)

    def test_tools_have_docstrings(self) -> None:
        from mcp_servers.orchestrator_server import (
            check_dispatch_safe_tool,
            check_pr_ready_tool,
            check_stalled_tool,
            triage_duplicates_tool,
        )

        for fn in (check_pr_ready_tool, triage_duplicates_tool, check_dispatch_safe_tool, check_stalled_tool):
            assert fn.__doc__ is not None and len(fn.__doc__) > 10

    def test_mcp_tool_error_handling(self) -> None:
        """MCP tools must return error dicts, not raise exceptions."""
        from mcp_servers.orchestrator_server import check_pr_ready_tool

        result = check_pr_ready_tool("https://example.com/bad-url")
        assert "error" in result
        assert result["promote"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
