"""Unit tests for src/quality/governance.py.

Covers the public surface of the governance module:

- ``GovernanceTracker`` (init, log_agent_output, request_approval,
  log_decision, generate_report)
- ``InteractiveMode`` (review_and_edit, select_option)
- ``create_governance_tracker`` factory

Tests rely on ``tmp_path`` for filesystem isolation and ``monkeypatch`` to
stub ``builtins.input`` plus the editor ``subprocess.run`` invocation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.quality.governance import (
    GovernanceTracker,
    InteractiveMode,
    create_governance_tracker,
)

# ---------------------------------------------------------------------------
# GovernanceTracker.__init__
# ---------------------------------------------------------------------------


def test_init_creates_output_and_session_directories(tmp_path: Path) -> None:
    output_dir = tmp_path / "gov"
    tracker = GovernanceTracker(output_dir=str(output_dir))

    assert output_dir.exists()
    assert tracker.session_dir.exists()
    assert tracker.session_dir.parent == output_dir
    assert tracker.decisions == []
    assert tracker.agent_outputs == {}
    # session_id matches the YYYYMMDD_HHMMSS pattern
    assert len(tracker.session_id) == 15
    assert tracker.session_id[8] == "_"


def test_init_with_existing_output_dir_does_not_raise(tmp_path: Path) -> None:
    output_dir = tmp_path / "preexisting"
    output_dir.mkdir()
    # Edge case: directory already exists → should still succeed
    tracker = GovernanceTracker(output_dir=str(output_dir))

    assert tracker.session_dir.exists()


# ---------------------------------------------------------------------------
# GovernanceTracker.log_agent_output
# ---------------------------------------------------------------------------


def test_log_agent_output_writes_json_file_and_caches_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    tracker.log_agent_output(
        "research_agent",
        {"data_points": 5},
        metadata={"topic": "AI"},
    )

    output_file = tracker.session_dir / "research_agent.json"
    assert output_file.exists()

    payload = json.loads(output_file.read_text())
    assert payload["agent"] == "research_agent"
    assert payload["output"] == {"data_points": 5}
    assert payload["metadata"] == {"topic": "AI"}
    assert "timestamp" in payload

    # Cached in-memory
    assert "research_agent" in tracker.agent_outputs
    assert tracker.agent_outputs["research_agent"]["output"] == {"data_points": 5}

    # Confirmation message printed
    captured = capsys.readouterr()
    assert "research_agent" in captured.out


def test_log_agent_output_without_metadata_uses_empty_dict(tmp_path: Path) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    tracker.log_agent_output("writer", "some output")

    payload = json.loads((tracker.session_dir / "writer.json").read_text())
    assert payload["metadata"] == {}


def test_log_agent_output_serializes_non_json_default(tmp_path: Path) -> None:
    """Edge case: non-JSON-native types must fall back to ``default=str``."""
    tracker = GovernanceTracker(output_dir=str(tmp_path))

    class Weird:
        def __str__(self) -> str:
            return "weird-value"

    tracker.log_agent_output("oddball", {"thing": Weird()})

    raw = (tracker.session_dir / "oddball.json").read_text()
    assert "weird-value" in raw


# ---------------------------------------------------------------------------
# GovernanceTracker.request_approval
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("response", ["", "y", "Y", "yes", "YES"])
def test_request_approval_returns_true_for_affirmative_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response: str,
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: response)

    approved = tracker.request_approval("Research", "summary")

    assert approved is True
    assert tracker.decisions[-1]["approved"] is True
    assert tracker.decisions[-1]["stage"] == "Research"
    assert tracker.decisions[-1]["skip_all"] is False


def test_request_approval_returns_false_for_negative_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: "n")

    approved = tracker.request_approval("Research", "summary")

    assert approved is False
    assert tracker.decisions[-1]["approved"] is False


def test_request_approval_skip_all_returns_true_and_flags_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: "skip-all")

    approved = tracker.request_approval("Research", "summary")

    assert approved is True
    assert tracker.decisions[-1]["skip_all"] is True


def test_request_approval_renders_details_and_review_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Edge case: stage name maps onto a logged agent output → review file shown."""
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    tracker.log_agent_output("research_phase", {"ok": True})
    monkeypatch.setattr("builtins.input", lambda _: "y")

    tracker.request_approval(
        "Research Phase",
        "Found 3 sources",
        details={"sources": 3, "verified": 2},
    )

    out = capsys.readouterr().out
    assert "APPROVAL GATE: Research Phase" in out
    assert "Found 3 sources" in out
    assert "sources" in out
    assert "Review file" in out
    assert "research_phase.json" in out


# ---------------------------------------------------------------------------
# GovernanceTracker.log_decision
# ---------------------------------------------------------------------------


def test_log_decision_appends_to_jsonl_and_memory(tmp_path: Path) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))

    tracker.log_decision(
        "model_choice",
        "claude-opus",
        "highest quality available",
        data={"context_tokens": 1000},
    )

    decisions_file = tracker.session_dir / "decisions.jsonl"
    assert decisions_file.exists()

    line = decisions_file.read_text().strip()
    payload = json.loads(line)
    assert payload["type"] == "model_choice"
    assert payload["choice"] == "claude-opus"
    assert payload["rationale"] == "highest quality available"
    assert payload["data"] == {"context_tokens": 1000}

    assert tracker.decisions[-1]["type"] == "model_choice"


def test_log_decision_multiple_appends_one_line_per_call(tmp_path: Path) -> None:
    """Edge case: repeated calls must produce one JSONL line each, no overwrite."""
    tracker = GovernanceTracker(output_dir=str(tmp_path))

    tracker.log_decision("a", "x", "r1")
    tracker.log_decision("b", "y", "r2")
    tracker.log_decision("c", "z", "r3")

    lines = (tracker.session_dir / "decisions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert [p["type"] for p in parsed] == ["a", "b", "c"]


def test_log_decision_without_data_uses_empty_dict(tmp_path: Path) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    tracker.log_decision("simple", "ok", "no extras")

    payload = json.loads((tracker.session_dir / "decisions.jsonl").read_text().strip())
    assert payload["data"] == {}


# ---------------------------------------------------------------------------
# GovernanceTracker.generate_report
# ---------------------------------------------------------------------------


def test_generate_report_default_path_includes_outputs_and_decisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    tracker.log_agent_output("research", {"ok": True}, metadata={"topic": "AI"})
    monkeypatch.setattr("builtins.input", lambda _: "y")
    tracker.request_approval("Research", "ok")
    tracker.log_decision("model_choice", "claude", "default")

    report = tracker.generate_report()

    default_file = tracker.session_dir / "governance_report.md"
    assert default_file.exists()
    assert "# Governance Report" in report
    assert tracker.session_id in report
    assert "Research" in report
    assert "Approved" in report
    assert "model_choice" in report
    # Metadata is rendered
    assert "topic" in report
    # File content matches return value
    assert default_file.read_text() == report


def test_generate_report_rejected_approval_renders_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: "n")
    tracker.request_approval("Rejected Stage", "nope")

    report = tracker.generate_report()
    assert "Rejected" in report


def test_generate_report_custom_output_file(tmp_path: Path) -> None:
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    custom = tmp_path / "custom_report.md"
    tracker.generate_report(output_file=str(custom))

    assert custom.exists()
    assert "# Governance Report" in custom.read_text()


def test_generate_report_empty_session_still_produces_valid_report(
    tmp_path: Path,
) -> None:
    """Edge case: no logged outputs or decisions still yields a valid report."""
    tracker = GovernanceTracker(output_dir=str(tmp_path))
    report = tracker.generate_report()

    assert "# Governance Report" in report
    assert "## Agent Outputs" in report
    assert "## Decisions" in report


# ---------------------------------------------------------------------------
# InteractiveMode.review_and_edit
# ---------------------------------------------------------------------------


def test_review_and_edit_continue_returns_content_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "c")
    result = InteractiveMode.review_and_edit("hello world", content_type="article")

    assert result == "hello world"


def test_review_and_edit_default_response_returns_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case: any non-edit, non-reject response (incl. empty) → continue."""
    monkeypatch.setattr("builtins.input", lambda _: "")
    result = InteractiveMode.review_and_edit("abc")
    assert result == "abc"


def test_review_and_edit_reject_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "r")

    with pytest.raises(ValueError, match="Content rejected"):
        InteractiveMode.review_and_edit("doomed content")


def test_review_and_edit_edit_path_invokes_editor_and_returns_edited_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "e")

    # Replace the editor subprocess so it doesn't try to launch nano.
    # The temp file contains the original content; simulate edits by appending.
    def fake_subprocess_run(args, check=False):  # noqa: ARG001
        # args is [editor, temp_path]
        temp_path = args[1]
        with open(temp_path, "a") as f:
            f.write("\nEDITED")
        return None

    # ``subprocess`` is imported lazily inside the function under test, so
    # patch the attribute on the real ``subprocess`` module directly.
    import subprocess as _subprocess

    monkeypatch.setattr(_subprocess, "run", fake_subprocess_run)

    result = InteractiveMode.review_and_edit("original")

    assert result.startswith("original")
    assert "EDITED" in result


def test_review_and_edit_truncation_message_for_long_content(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Edge case: content >500 chars triggers truncation notice in output."""
    monkeypatch.setattr("builtins.input", lambda _: "c")
    long_content = "x" * 750

    InteractiveMode.review_and_edit(long_content)

    out = capsys.readouterr().out
    assert "more characters" in out


# ---------------------------------------------------------------------------
# InteractiveMode.select_option
# ---------------------------------------------------------------------------


def test_select_option_returns_zero_based_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "2")

    idx = InteractiveMode.select_option("Pick one:", ["alpha", "beta", "gamma"])

    assert idx == 1


def test_select_option_reprompts_on_out_of_range_then_invalid_then_valid(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Edge case: out-of-range and non-numeric inputs are rejected and retried."""
    answers = iter(["99", "not-a-number", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    idx = InteractiveMode.select_option("Pick:", ["only", "two"])

    assert idx == 0
    out = capsys.readouterr().out
    assert "between 1 and 2" in out
    assert "Invalid input" in out


# ---------------------------------------------------------------------------
# create_governance_tracker
# ---------------------------------------------------------------------------


def test_factory_uses_explicit_output_dir(tmp_path: Path) -> None:
    tracker = create_governance_tracker(output_dir=str(tmp_path / "explicit"))

    assert isinstance(tracker, GovernanceTracker)
    assert tracker.output_dir == tmp_path / "explicit"


def test_factory_honours_governance_dir_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "from_env"
    monkeypatch.setenv("GOVERNANCE_DIR", str(target))

    tracker = create_governance_tracker()

    assert tracker.output_dir == target


def test_factory_defaults_when_env_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case: no arg and no env → falls back to 'output/governance' literal."""
    monkeypatch.delenv("GOVERNANCE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    tracker = create_governance_tracker()

    assert tracker.output_dir == Path("output/governance")
    assert (tmp_path / "output" / "governance").exists()
