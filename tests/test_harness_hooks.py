"""Tests for the B-030 harness hooks.

The audit's central finding was that every sensor in this repo fires at the *owner's* gate
(pre-commit, `make ci-local`) rather than the agent's, so the owner performs triage an
agent could have done mid-session. These hooks close that loop.

Two contracts are asserted here, and they matter more than any internal detail:

1. **Payload in, payload out.** Each hook is exercised through the exact stdin JSON the
   harness sends, and asserted on the parsed stdout JSON. A passing test therefore means
   the hook works with Claude Code, not merely that its functions are reachable.
2. **A hook may never break the session.** Malformed input, a missing file, an unavailable
   subprocess — every one of these must yield exit 0 and an empty payload. A broken sensor
   degrades to *no* sensor; it must never degrade to a blocked developer.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import orjson
import pytest

from scripts.hooks import guard_constraints, session_context, session_gate
from scripts.hooks import post_edit_sensor as post_edit
from scripts.hooks._io import emit_payload, read_payload

REPO_ROOT = Path(__file__).resolve().parents[1]

HOOK_MODULES = (
    "scripts.hooks.post_edit_sensor",
    "scripts.hooks.guard_constraints",
    "scripts.hooks.session_gate",
    "scripts.hooks.session_context",
)


@pytest.fixture(autouse=True)
def isolate_sensor_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests out of the repo's real sensor history.

    `post_edit.handle` records a snapshot on every call. Without this, running the suite
    appends test noise to `logs/sensor_history.jsonl` — the file whose whole purpose is to
    be a truthful record of what the sensors saw during real sessions.
    """
    monkeypatch.setattr(post_edit, "HISTORY_PATH", tmp_path / "sensor_history.jsonl")


def run_hook_process(module: str, payload: object) -> tuple[int, dict]:
    """Run a hook exactly as the harness does: JSON on stdin, JSON on stdout.

    Args:
        module: Dotted module path of the hook.
        payload: Object to serialise as the hook's stdin.

    Returns:
        ``(exit_code, parsed_stdout)``. Empty stdout parses as ``{}``.

    """
    completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [sys.executable, "-m", module],
        input=orjson.dumps(payload),
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    raw = completed.stdout.decode().strip()
    return completed.returncode, (orjson.loads(raw) if raw else {})


# ── The never-crash guarantee ───────────────────────────────────────────────────


class TestNeverBreaksTheSession:
    """Every hook exits 0 on garbage. This is the load-bearing safety property."""

    @pytest.mark.parametrize("module", HOOK_MODULES)
    def test_malformed_stdin_exits_zero(self, module: str) -> None:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-m", module],
            input=b"this is not json {{{",
            capture_output=True,
            cwd=REPO_ROOT,
            timeout=120,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr.decode()

    @pytest.mark.parametrize("module", HOOK_MODULES)
    def test_empty_payload_exits_zero_and_returns_valid_json(self, module: str) -> None:
        code, payload = run_hook_process(module, {})

        assert code == 0
        assert isinstance(payload, dict)


class TestIoContract:
    """The stdin/stdout plumbing shared by every hook."""

    def test_read_payload_returns_empty_dict_on_garbage(self) -> None:
        assert read_payload("not json") == {}

    def test_read_payload_returns_empty_dict_for_non_object_json(self) -> None:
        """A JSON array is valid JSON but not a hook payload."""
        assert read_payload("[1, 2, 3]") == {}

    def test_emit_payload_writes_compact_json(self, capsys) -> None:
        emit_payload({"systemMessage": "hi"})

        assert orjson.loads(capsys.readouterr().out) == {"systemMessage": "hi"}

    def test_emit_payload_writes_nothing_for_an_empty_payload(self, capsys) -> None:
        """An empty payload must not emit `{}` noise into the transcript."""
        emit_payload({})

        assert capsys.readouterr().out == ""


# ── PreToolUse: the deny guards ─────────────────────────────────────────────────


def deny_reason(result: dict) -> str:
    """Extract the deny reason from a PreToolUse hook payload, or '' if allowed."""
    specific = result.get("hookSpecificOutput", {})
    if specific.get("permissionDecision") != "deny":
        return ""
    return str(specific.get("permissionDecisionReason", ""))


class TestForbiddenKeyGuard:
    """CLAUDE.md constraint #1 — "NO new API keys. Ever." — becomes computational.

    It is the most emphatic sentence in the repo and had zero enforcement: neither
    destructive_change_guard.py nor pre_commit_arch_check.py mentions OPENAI_API_KEY.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "export OPENAI_API_KEY=sk-test",
            "OPENAI_API_KEY=sk-test python foo.py",
            "export SERPER_API_KEY=abc123",
            "export GEMINI_API_KEY=xyz",
            "pip install openai",
        ],
    )
    def test_denies_introducing_a_forbidden_key(self, command: str) -> None:
        result = guard_constraints.handle(
            {"tool_name": "Bash", "tool_input": {"command": command}},
        )

        assert deny_reason(result), f"should have denied: {command}"

    @pytest.mark.parametrize(
        "command",
        [
            "git status",
            "grep -rn OPENAI_API_KEY docs/",
            "rg SERPER_API_KEY --files-with-matches",
            "cat CLAUDE.md",
            "make ci-local",
        ],
    )
    def test_allows_reading_and_searching_for_key_names(self, command: str) -> None:
        """Discussing or grepping a forbidden key is not introducing one.

        An over-broad guard that blocks `grep OPENAI_API_KEY` would be switched off
        within a day, which is the real failure mode for a sensor like this.
        """
        result = guard_constraints.handle(
            {"tool_name": "Bash", "tool_input": {"command": command}},
        )

        assert deny_reason(result) == "", f"should have allowed: {command}"

    def test_deny_reason_names_the_constraint(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "export OPENAI_API_KEY=sk-test"},
            },
        )

        assert "CLAUDE.md" in deny_reason(result)


class TestUnreviewedPublishGuard:
    """B-028 as a sensor rather than prose.

    `deploy_to_blog.py:681` sets `default="post"`, so the *documented* command silently
    publishes without review. B-028 owns changing that default; this guard makes the
    policy hold from the harness side either way.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "python -m scripts.deploy_to_blog --article output/posts/x.md --mode post",
            "python -m scripts.deploy_to_blog --article output/posts/x.md",
        ],
    )
    def test_denies_deploy_without_review_mode(self, command: str) -> None:
        result = guard_constraints.handle(
            {"tool_name": "Bash", "tool_input": {"command": command}},
        )

        assert deny_reason(result), f"should have denied: {command}"

    def test_allows_deploy_in_review_mode(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "python -m scripts.deploy_to_blog "
                        "--article output/posts/x.md --mode review"
                    ),
                },
            },
        )

        assert deny_reason(result) == ""

    def test_allows_help(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python -m scripts.deploy_to_blog --help"},
            },
        )

        assert deny_reason(result) == ""

    def test_deny_reason_points_at_the_review_workflow(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python -m scripts.deploy_to_blog --mode post"
                },
            },
        )

        assert "--mode review" in deny_reason(result)


class TestConfigWriteGuard:
    """Writing a forbidden key into a config file is the other introduction path."""

    def test_denies_writing_a_forbidden_key_into_mcp_json(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(REPO_ROOT / ".mcp.json"),
                    "content": '{"env": {"OPENAI_API_KEY": "${OPENAI_API_KEY}"}}',
                },
            },
        )

        assert deny_reason(result)

    def test_allows_documenting_a_forbidden_key_in_markdown(self) -> None:
        """This very repo documents the ban in prose; the guard must not block docs."""
        result = guard_constraints.handle(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(REPO_ROOT / "docs" / "notes.md"),
                    "content": "Never require OPENAI_API_KEY — see constraint #1.",
                },
            },
        )

        assert deny_reason(result) == ""

    def test_allows_a_clean_config_write(self) -> None:
        result = guard_constraints.handle(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(REPO_ROOT / ".mcp.json"),
                    "content": '{"mcpServers": {}}',
                },
            },
        )

        assert deny_reason(result) == ""


# ── PostToolUse: the edit-time sensor ───────────────────────────────────────────


def injected_context(result: dict) -> str:
    """Extract additionalContext from a hook payload, or '' when absent."""
    return str(result.get("hookSpecificOutput", {}).get("additionalContext", ""))


class TestPostEditSensor:
    """Lint and complexity feedback must reach the agent, not wait for the owner."""

    def test_ignores_non_python_files(self, tmp_path: Path) -> None:
        note = tmp_path / "note.md"
        note.write_text("# hi\n", encoding="utf-8")

        result = post_edit.handle(
            {"tool_name": "Write", "tool_input": {"file_path": str(note)}},
        )

        assert result == {}

    def test_reports_complexity_back_to_the_agent(self, tmp_path: Path) -> None:
        tangled = tmp_path / "tangled.py"
        body = "\n".join(
            f'    if value > {n}:\n        out += "{n}"' for n in range(1, 13)
        )
        tangled.write_text(
            f'"""Fixture."""\n\n\ndef tangled(value: int) -> str:\n'
            f'    """Branchy."""\n    out = ""\n{body}\n    return out\n',
            encoding="utf-8",
        )

        result = post_edit.handle(
            {"tool_name": "Edit", "tool_input": {"file_path": str(tangled)}},
        )

        assert "COMPLEXITY SENSOR" in injected_context(result)

    def test_clean_file_produces_no_feedback(self, tmp_path: Path) -> None:
        """Silence on success — otherwise the hook becomes the noise nobody reads."""
        tidy = tmp_path / "tidy.py"
        tidy.write_text('"""Fixture."""\n\n\nX = 1\n', encoding="utf-8")

        result = post_edit.handle(
            {"tool_name": "Write", "tool_input": {"file_path": str(tidy)}},
        )

        assert injected_context(result) == ""

    def test_reads_the_path_from_tool_response_when_input_lacks_it(
        self,
        tmp_path: Path,
    ) -> None:
        tidy = tmp_path / "tidy.py"
        tidy.write_text('"""Fixture."""\n\n\nX = 1\n', encoding="utf-8")

        result = post_edit.handle(
            {"tool_name": "Write", "tool_response": {"filePath": str(tidy)}},
        )

        assert result == {} or injected_context(result) == ""

    def test_missing_file_is_ignored(self, tmp_path: Path) -> None:
        result = post_edit.handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(tmp_path / "gone.py")},
            },
        )

        assert result == {}


class TestSensorHistory:
    """Boeckeler's sidecar: sensor state recorded over a session, not just per-check."""

    def test_snapshot_appends_one_jsonl_line(self, tmp_path: Path) -> None:
        history = tmp_path / "sensor_history.jsonl"

        post_edit.record_snapshot(
            session_id="sess-1",
            path="scripts/foo.py",
            finding_count=2,
            history_path=history,
        )
        post_edit.record_snapshot(
            session_id="sess-1",
            path="scripts/bar.py",
            finding_count=0,
            history_path=history,
        )

        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        first = orjson.loads(lines[0])
        assert first["outputs"]["finding_count"] == 2
        assert first["schema_version"], "must carry the trace logger's schema version"

    def test_snapshot_failure_is_swallowed(self, tmp_path: Path) -> None:
        """Observability must never be able to break an edit."""
        unwritable = tmp_path / "no-such-dir" / "deep" / "history.jsonl"

        post_edit.record_snapshot(
            session_id="s",
            path="x.py",
            finding_count=0,
            history_path=unwritable,
        )  # must not raise


# ── Stop: the bounded session gate ──────────────────────────────────────────────


class TestSessionGate:
    """A blocking Stop hook is a session trap unless it is bounded. This bounds it."""

    def test_blocks_once_then_never_again_for_the_same_session(
        self,
        tmp_path: Path,
    ) -> None:
        first = session_gate.handle(
            {"session_id": "sess-A"},
            violations="scripts/foo.py:1:1 E999 SyntaxError",
            test_failures="",
            state_dir=tmp_path,
        )
        second = session_gate.handle(
            {"session_id": "sess-A"},
            violations="scripts/foo.py:1:1 E999 SyntaxError",
            test_failures="",
            state_dir=tmp_path,
        )

        assert first.get("decision") == "block"
        assert second == {}, "a second block would trap the session in a loop"

    def test_a_different_session_still_gets_its_one_block(self, tmp_path: Path) -> None:
        session_gate.handle(
            {"session_id": "sess-A"},
            violations="boom",
            test_failures="",
            state_dir=tmp_path,
        )
        other = session_gate.handle(
            {"session_id": "sess-B"},
            violations="boom",
            test_failures="",
            state_dir=tmp_path,
        )

        assert other.get("decision") == "block"

    def test_clean_tree_does_not_block(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-C"},
            violations="",
            test_failures="",
            state_dir=tmp_path,
        )

        assert result == {}

    def test_block_reason_includes_the_violations(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-D"},
            violations="scripts/foo.py:3:1 F821 undefined name",
            test_failures="",
            state_dir=tmp_path,
        )

        assert "F821" in str(result.get("reason", ""))

    def test_missing_session_id_still_bounds_itself(self, tmp_path: Path) -> None:
        """No session_id must not mean unlimited blocks."""
        first = session_gate.handle(
            {}, violations="boom", test_failures="", state_dir=tmp_path
        )
        second = session_gate.handle(
            {}, violations="boom", test_failures="", state_dir=tmp_path
        )

        assert first.get("decision") == "block"
        assert second == {}


# ── Stop: scoped tests as the correctness signal (B-035 Task 1) ─────────────────


class TestMatchingTestFiles:
    """`scripts/X.py` maps to `tests/test_X.py` — nothing broader runs.

    The objection to running tests in a Stop gate was cost, and the measurement
    removed it: the full suite is ~100s, one matching test file is 3.4s, and 40
    of 48 `scripts/` modules (83%) have a match.
    """

    def test_source_file_maps_to_its_test(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "foo.py").touch()
        target = tmp_path / "tests" / "test_foo.py"
        target.touch()

        found = session_gate.matching_test_files(
            [tmp_path / "scripts" / "foo.py"],
            repo_root=tmp_path,
        )

        assert found == [target]

    def test_module_without_a_test_maps_to_nothing(self, tmp_path: Path) -> None:
        """17% of modules have no match; they must degrade, not error."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "orphan.py").touch()

        found = session_gate.matching_test_files(
            [tmp_path / "scripts" / "orphan.py"],
            repo_root=tmp_path,
        )

        assert found == []

    def test_a_changed_test_file_maps_to_itself(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        target = tmp_path / "tests" / "test_foo.py"
        target.touch()

        found = session_gate.matching_test_files([target], repo_root=tmp_path)

        assert found == [target]

    def test_results_are_deduplicated(self, tmp_path: Path) -> None:
        """Editing both `scripts/foo.py` and `tests/test_foo.py` runs it once."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "foo.py").touch()
        target = tmp_path / "tests" / "test_foo.py"
        target.touch()

        found = session_gate.matching_test_files(
            [tmp_path / "scripts" / "foo.py", target],
            repo_root=tmp_path,
        )

        assert found == [target]

    def test_no_changed_files_maps_to_nothing(self, tmp_path: Path) -> None:
        assert session_gate.matching_test_files([], repo_root=tmp_path) == []


class TestCollectTestFailures:
    """Tests are additive. Anything that is not a clean red result must not block."""

    def test_timeout_does_not_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Never block on a timeout — a slow suite is not a broken one."""

        def _timeout(*args: object, **kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)

        monkeypatch.setattr(subprocess, "run", _timeout)

        assert session_gate.collect_test_failures([Path("tests/test_foo.py")]) == ""

    def test_pytest_missing_does_not_block(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _explode(*args: object, **kwargs: object) -> None:
            raise OSError("no pytest")

        monkeypatch.setattr(subprocess, "run", _explode)

        assert session_gate.collect_test_failures([Path("tests/test_foo.py")]) == ""

    def test_no_matching_files_does_not_run_pytest(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail(*args: object, **kwargs: object) -> None:
            raise AssertionError("pytest must not run with no targets")

        monkeypatch.setattr(subprocess, "run", _fail)

        assert session_gate.collect_test_failures([]) == ""

    def test_passing_tests_report_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=0, stdout="2 passed", stderr=""),
        )

        assert session_gate.collect_test_failures([Path("tests/test_foo.py")]) == ""

    def test_failing_tests_report_the_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(
                returncode=1,
                stdout="FAILED tests/test_foo.py::test_bar - assert 1 == 2",
                stderr="",
            ),
        )

        detail = session_gate.collect_test_failures([Path("tests/test_foo.py")])

        assert "test_bar" in detail

    def test_does_not_recurse_into_itself(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The gate's own test file matches its mapping rule.

        Without a reentrancy guard the gate spawns a pytest that re-enters the
        gate, which spawns another. Caught by this suite hanging.
        """

        def _fail(*args: object, **kwargs: object) -> None:
            raise AssertionError("must not spawn pytest from inside a pytest run")

        monkeypatch.setenv(session_gate._REENTRY_ENV, "1")
        monkeypatch.setattr(subprocess, "run", _fail)

        assert session_gate.collect_test_failures([Path("tests/test_foo.py")]) == ""

    def test_child_run_carries_the_reentry_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Belt and braces: the spawned pytest is marked so it cannot recurse."""
        seen: dict[str, object] = {}

        def _capture(*args: object, **kwargs: object) -> SimpleNamespace:
            seen.update(kwargs)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.delenv(session_gate._REENTRY_ENV, raising=False)
        monkeypatch.setattr(subprocess, "run", _capture)
        session_gate.collect_test_failures([Path("tests/test_foo.py")])

        assert seen["env"][session_gate._REENTRY_ENV] == "1"  # type: ignore[index]

    def test_uses_a_sixty_second_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: dict[str, object] = {}

        def _capture(*args: object, **kwargs: object) -> SimpleNamespace:
            seen.update(kwargs)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", _capture)
        session_gate.collect_test_failures([Path("tests/test_foo.py")])

        assert seen["timeout"] == 60


class TestLintAndTestsCompose:
    """Lint stays always-on; tests are additive, not a replacement."""

    def test_red_tests_block_even_when_lint_is_clean(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-T1"},
            violations="",
            test_failures="FAILED tests/test_foo.py::test_bar",
            state_dir=tmp_path,
        )

        assert result.get("decision") == "block"
        assert "test_bar" in str(result.get("reason", ""))

    def test_red_lint_blocks_even_when_tests_are_clean(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-T2"},
            violations="scripts/foo.py:1:1 F821 undefined name",
            test_failures="",
            state_dir=tmp_path,
        )

        assert result.get("decision") == "block"
        assert "F821" in str(result.get("reason", ""))

    def test_both_red_reports_both(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-T3"},
            violations="scripts/foo.py:1:1 F821 undefined name",
            test_failures="FAILED tests/test_foo.py::test_bar",
            state_dir=tmp_path,
        )

        reason = str(result.get("reason", ""))
        assert "F821" in reason
        assert "test_bar" in reason

    def test_both_clean_does_not_block(self, tmp_path: Path) -> None:
        result = session_gate.handle(
            {"session_id": "sess-T4"},
            violations="",
            test_failures="",
            state_dir=tmp_path,
        )

        assert result == {}

    def test_test_fallback_still_bounded_to_one_block(self, tmp_path: Path) -> None:
        """The one-block-per-session bound covers the test path too."""
        first = session_gate.handle(
            {"session_id": "sess-T5"},
            violations="",
            test_failures="FAILED tests/test_foo.py::test_bar",
            state_dir=tmp_path,
        )
        second = session_gate.handle(
            {"session_id": "sess-T5"},
            violations="",
            test_failures="FAILED tests/test_foo.py::test_bar",
            state_dir=tmp_path,
        )

        assert first.get("decision") == "block"
        assert second == {}


# ── SessionStart: the guide injection ───────────────────────────────────────────


class TestSessionContext:
    """Constraints delivered at session start instead of carried in prose forever."""

    def test_injects_the_non_negotiable_constraints(self) -> None:
        context = injected_context(session_context.handle({}))

        assert "NO new API keys" in context

    def test_names_the_current_branch(self) -> None:
        context = injected_context(session_context.handle({}))

        assert "branch" in context.lower()

    def test_lists_open_backlog_items(self) -> None:
        context = injected_context(session_context.handle({}))

        assert "B-0" in context, "open B- items should be surfaced at session start"
