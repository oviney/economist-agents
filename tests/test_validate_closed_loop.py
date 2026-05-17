"""Direct unit tests for src/quality/validate_closed_loop.py.

These tests exercise the public surface of the module in-process, in contrast
to tests/test_closed_loop_validation.py which drives the module via subprocess.
Together the two files cover both the CLI contract and the internal behavior
of each ValidationStage, ClosedLoopValidator, and main().

Mocking strategy (per stage):
- StorageCheck       -> tmp_path; uses real SkillsManager (in-process, fast).
- SynthesisCheck     -> monkeypatch subprocess.run + _SCRIPTS_DIR.
- IntegrationCheck   -> monkeypatch subprocess.run + _SCRIPTS_DIR.
- SyncCheck          -> monkeypatch subprocess.run + _SCRIPTS_DIR + _REPO_ROOT.
- ReportingCheck     -> monkeypatch subprocess.run + _SCRIPTS_DIR.
- ClosedLoopValidator-> inject stub ValidationStage subclasses.
- main()             -> monkeypatch sys.argv; capsys for stdout.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import orjson
import pytest

from src.quality import validate_closed_loop as vcl

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


class _CompletedProc:
    """Lightweight stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _patch_subprocess(monkeypatch: pytest.MonkeyPatch, result: Any) -> list[list[str]]:
    """Replace subprocess.run with a recorder returning ``result``.

    Returns the list of recorded argv lists for assertion.
    """
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(vcl.subprocess, "run", fake_run)
    return calls


# ═══════════════════════════════════════════════════════════════════════════
# ValidationStage (base class)
# ═══════════════════════════════════════════════════════════════════════════


class TestValidationStageBase:
    """Behavior of the abstract ValidationStage base class."""

    def test_initializes_with_empty_error_and_warning_lists(self):
        stage = vcl.ValidationStage("My Stage")
        assert stage.name == "My Stage"
        assert stage.verbose is False
        assert stage.errors == []
        assert stage.warnings == []

    def test_error_appends_to_errors_list(self):
        stage = vcl.ValidationStage("S")
        stage.error("boom")
        assert stage.errors == ["boom"]

    def test_warn_appends_to_warnings_list(self):
        stage = vcl.ValidationStage("S")
        stage.warn("careful")
        assert stage.warnings == ["careful"]

    def test_log_silent_when_not_verbose(self, capsys: pytest.CaptureFixture[str]):
        stage = vcl.ValidationStage("S", verbose=False)
        stage.log("hello")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_log_prints_when_verbose(self, capsys: pytest.CaptureFixture[str]):
        stage = vcl.ValidationStage("S", verbose=True)
        stage.log("hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_log_uses_distinct_prefixes_per_level(
        self, capsys: pytest.CaptureFixture[str]
    ):
        stage = vcl.ValidationStage("S", verbose=True)
        stage.log("ok", "info")
        stage.log("hmm", "warn")
        stage.log("nope", "error")
        out = capsys.readouterr().out
        assert "ok" in out and "hmm" in out and "nope" in out
        # Each level uses a different glyph
        lines = [line for line in out.splitlines() if line.strip()]
        assert len({line.split()[0] for line in lines}) == 3

    def test_log_unknown_level_raises_keyerror(self):
        stage = vcl.ValidationStage("S", verbose=True)
        with pytest.raises(KeyError):
            stage.log("x", level="bogus")

    def test_validate_not_implemented_on_base_class(self):
        stage = vcl.ValidationStage("S")
        with pytest.raises(NotImplementedError):
            stage.validate()


# ═══════════════════════════════════════════════════════════════════════════
# StorageCheck
# ═══════════════════════════════════════════════════════════════════════════


class TestStorageCheck:
    """StorageCheck validates SkillsManager file creation and persistence."""

    def test_validate_happy_path_returns_true(self):
        check = vcl.StorageCheck(verbose=False)
        assert check.validate() is True
        assert check.errors == []
        # File should have been created during validate
        assert check.test_skills_file is not None
        assert check.test_skills_file.exists()
        # And should contain the learned pattern
        data = orjson.loads(check.test_skills_file.read_bytes())
        assert "test_category" in data["skills"]
        check.cleanup()

    def test_cleanup_removes_created_file(self):
        check = vcl.StorageCheck(verbose=False)
        check.validate()
        path = check.test_skills_file
        assert path is not None and path.exists()
        check.cleanup()
        assert not path.exists()

    def test_cleanup_is_safe_when_no_file_created(self):
        check = vcl.StorageCheck(verbose=False)
        # cleanup() before validate() should be a no-op, not raise
        check.cleanup()
        assert check.test_skills_file is None

    def test_validate_reports_error_when_save_does_not_create_file(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """If SkillsManager.save() silently fails to create the file, validate
        must record an error and return False."""

        class FakeManager:
            def __init__(self, **_kwargs):
                pass

            def save(self):
                # Pretend save was called but no file was written
                pass

            def learn_pattern(self, *a, **kw):
                pass

        monkeypatch.setattr(vcl, "SkillsManager", FakeManager)
        check = vcl.StorageCheck(verbose=False)
        assert check.validate() is False
        assert any("not created" in e for e in check.errors)

    def test_validate_returns_false_when_skillsmanager_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def explode(**_kwargs):
            raise RuntimeError("kaboom")

        monkeypatch.setattr(vcl, "SkillsManager", explode)
        check = vcl.StorageCheck(verbose=False)
        assert check.validate() is False
        assert any("kaboom" in e for e in check.errors)


# ═══════════════════════════════════════════════════════════════════════════
# SynthesisCheck
# ═══════════════════════════════════════════════════════════════════════════


class TestSynthesisCheck:
    """SynthesisCheck wraps a subprocess invocation of skill_synthesizer.py."""

    def test_validate_returns_false_when_script_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        # Point _SCRIPTS_DIR at an empty directory so the script lookup fails
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is False
        assert any("not found" in e for e in check.errors)

    def test_validate_happy_path_with_mocked_subprocess(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        # Provide a fake synthesizer script on disk so the existence check passes
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=0, stdout="Identified 0 patterns", stderr=""),
        )

        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is True
        assert check.errors == []
        check.cleanup()

    def test_validate_returns_false_on_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=2, stdout="", stderr="bad args"),
        )

        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is False
        assert any("exit code 2" in e for e in check.errors)
        check.cleanup()

    def test_validate_returns_false_on_timeout(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            subprocess.TimeoutExpired(cmd=["x"], timeout=30),
        )

        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is False
        assert any("timed out" in e for e in check.errors)
        check.cleanup()

    def test_validate_records_warning_when_no_patterns_identified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=0, stdout="nothing here", stderr=""),
        )
        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is True
        # No "Identified" in stdout -> warning recorded
        assert any("No patterns" in w for w in check.warnings)
        check.cleanup()

    def test_validate_rejects_pattern_missing_required_field(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        # JSON array with a pattern missing 'severity'
        bad_pattern_json = (
            '[{"category":"c","pattern_id":"p","pattern":"x",'
            '"check":"x","learned_from":"x"}]'
        )
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(
                returncode=0,
                stdout=f"Identified 1 pattern {bad_pattern_json}",
                stderr="",
            ),
        )
        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is False
        assert any("missing required field" in e for e in check.errors)
        check.cleanup()

    def test_validate_rejects_pattern_with_invalid_severity(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        bad_pattern_json = (
            '[{"category":"c","pattern_id":"p","severity":"nuclear",'
            '"pattern":"x","check":"x","learned_from":"x"}]'
        )
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(
                returncode=0,
                stdout=f"Identified 1 pattern {bad_pattern_json}",
                stderr="",
            ),
        )
        check = vcl.SynthesisCheck(verbose=False)
        assert check.validate() is False
        assert any("Invalid severity" in e for e in check.errors)
        check.cleanup()

    def test_cleanup_removes_temporary_log_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skill_synthesizer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(monkeypatch, _CompletedProc(returncode=0, stdout=""))
        check = vcl.SynthesisCheck(verbose=False)
        check.validate()
        log = check.log_file
        assert log is not None and log.exists()
        check.cleanup()
        assert not log.exists()

    def test_cleanup_is_safe_when_no_log_created(self):
        check = vcl.SynthesisCheck(verbose=False)
        # Should not raise even though validate was never called
        check.cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# IntegrationCheck
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegrationCheck:
    """IntegrationCheck runs blog_qa_agent.py against a synthetic blog tree."""

    def test_validate_returns_false_when_script_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        check = vcl.IntegrationCheck(verbose=False)
        assert check.validate() is False
        assert any("not found" in e for e in check.errors)

    def test_validate_happy_path_detects_issues(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "blog_qa_agent.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        # Use a fresh repo root so the optional skills file check has nothing
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(
                returncode=1,
                stdout="Found broken link and missing categories",
                stderr="",
            ),
        )
        check = vcl.IntegrationCheck(verbose=False)
        assert check.validate() is True
        assert check.errors == []
        check.cleanup()

    def test_validate_warns_when_agent_unexpectedly_passes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "blog_qa_agent.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=0, stdout="", stderr=""),
        )
        check = vcl.IntegrationCheck(verbose=False)
        assert check.validate() is True
        # Three warnings expected: unexpected pass, no broken-link line, no categor
        assert len(check.warnings) >= 1
        check.cleanup()

    def test_validate_returns_false_on_timeout(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "blog_qa_agent.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch,
            subprocess.TimeoutExpired(cmd=["x"], timeout=30),
        )
        check = vcl.IntegrationCheck(verbose=False)
        assert check.validate() is False
        assert any("timed out" in e for e in check.errors)
        check.cleanup()

    def test_validate_handles_preexisting_skills_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """If skills/blog_qa_skills.json exists, the pre-count path runs."""
        (tmp_path / "blog_qa_agent.py").write_text("# fake")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "blog_qa_skills.json").write_bytes(
            orjson.dumps(
                {"skills": {"cat": {"patterns": [{"id": "p1"}, {"id": "p2"}]}}}
            )
        )
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=1, stdout="broken missing categor", stderr=""),
        )
        check = vcl.IntegrationCheck(verbose=True)
        assert check.validate() is True
        check.cleanup()

    def test_cleanup_removes_test_blog_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "blog_qa_agent.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(monkeypatch, _CompletedProc(returncode=1, stdout="broken"))
        check = vcl.IntegrationCheck(verbose=False)
        check.validate()
        blog_dir = check.test_blog_dir
        assert blog_dir is not None and blog_dir.exists()
        check.cleanup()
        assert not blog_dir.exists()

    def test_cleanup_is_safe_when_no_blog_dir_created(self):
        check = vcl.IntegrationCheck(verbose=False)
        check.cleanup()  # must not raise


# ═══════════════════════════════════════════════════════════════════════════
# SyncCheck
# ═══════════════════════════════════════════════════════════════════════════


class TestSyncCheck:
    """SyncCheck validates the copilot-instructions sync script."""

    def test_validate_returns_false_when_script_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is False
        assert any("not found" in e for e in check.errors)

    def test_validate_returns_false_when_copilot_file_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "sync_copilot_context.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is False
        assert any("Copilot instructions not found" in e for e in check.errors)

    def test_validate_returns_false_when_section_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "sync_copilot_context.py").write_text("# fake")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("no section here")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is False
        assert any("Learned Anti-Patterns" in e for e in check.errors)

    def test_validate_happy_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / "sync_copilot_context.py").write_text("# fake")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text(
            "## Learned Anti-Patterns\n- something"
        )
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=0, stdout="syncing pattern x", stderr=""),
        )
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is True
        assert check.errors == []

    def test_validate_returns_false_when_subprocess_exits_nonzero(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "sync_copilot_context.py").write_text("# fake")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text(
            "## Learned Anti-Patterns\n"
        )
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(
            monkeypatch, _CompletedProc(returncode=3, stdout="", stderr="oops")
        )
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is False
        assert any("exit code 3" in e for e in check.errors)

    def test_validate_returns_false_on_timeout(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "sync_copilot_context.py").write_text("# fake")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text(
            "## Learned Anti-Patterns\n"
        )
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        monkeypatch.setattr(vcl, "_REPO_ROOT", tmp_path)
        _patch_subprocess(monkeypatch, subprocess.TimeoutExpired(cmd=["x"], timeout=30))
        check = vcl.SyncCheck(verbose=False)
        assert check.validate() is False
        assert any("timed out" in e for e in check.errors)

    def test_cleanup_is_a_noop(self):
        check = vcl.SyncCheck(verbose=False)
        # Should not raise and should not change anything observable
        assert check.cleanup() is None


# ═══════════════════════════════════════════════════════════════════════════
# ReportingCheck
# ═══════════════════════════════════════════════════════════════════════════


class TestReportingCheck:
    """ReportingCheck validates the skills_gap_analyzer report output."""

    def test_validate_returns_false_when_script_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is False
        assert any("not found" in e for e in check.errors)

    def test_validate_happy_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / "skills_gap_analyzer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(
                returncode=0,
                stdout=(
                    "# Team Skills Assessment\n"
                    "| Role | Skills |\n| --- | --- |\n"
                    "| blog_qa | 5 |\n"
                ),
                stderr="",
            ),
        )
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is True
        assert check.errors == []

    def test_validate_returns_false_when_assessment_section_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skills_gap_analyzer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(returncode=0, stdout="some other output", stderr=""),
        )
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is False
        assert any("Team Skills Assessment" in e for e in check.errors)

    def test_validate_returns_false_on_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skills_gap_analyzer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch, _CompletedProc(returncode=4, stdout="", stderr="bad")
        )
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is False
        assert any("exit code 4" in e for e in check.errors)

    def test_validate_returns_false_on_timeout(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skills_gap_analyzer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(monkeypatch, subprocess.TimeoutExpired(cmd=["x"], timeout=30))
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is False
        assert any("timed out" in e for e in check.errors)

    def test_validate_records_warnings_when_table_or_roles_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        (tmp_path / "skills_gap_analyzer.py").write_text("# fake")
        monkeypatch.setattr(vcl, "_SCRIPTS_DIR", tmp_path)
        _patch_subprocess(
            monkeypatch,
            _CompletedProc(
                returncode=0,
                stdout="Team Skills Assessment but no table here",
                stderr="",
            ),
        )
        check = vcl.ReportingCheck(verbose=False)
        assert check.validate() is True
        # No "|" and no role names -> two warnings expected
        assert len(check.warnings) >= 1

    def test_cleanup_is_a_noop(self):
        check = vcl.ReportingCheck(verbose=False)
        assert check.cleanup() is None


# ═══════════════════════════════════════════════════════════════════════════
# ClosedLoopValidator
# ═══════════════════════════════════════════════════════════════════════════


class _AlwaysPasses(vcl.ValidationStage):
    def __init__(self, name: str = "Pass Stage", verbose: bool = False):
        super().__init__(name, verbose)
        self.cleaned = False

    def validate(self) -> bool:
        return True

    def cleanup(self) -> None:
        self.cleaned = True


class _AlwaysFails(vcl.ValidationStage):
    def __init__(self, name: str = "Fail Stage", verbose: bool = False):
        super().__init__(name, verbose)

    def validate(self) -> bool:
        self.error("intentional failure")
        self.warn("also a warning")
        return False

    def cleanup(self) -> None:
        pass


class _Raises(vcl.ValidationStage):
    def __init__(self, name: str = "Boom Stage", verbose: bool = False):
        super().__init__(name, verbose)
        self.cleaned = False

    def validate(self) -> bool:
        raise RuntimeError("validate exploded")

    def cleanup(self) -> None:
        self.cleaned = True


class _CleanupRaises(vcl.ValidationStage):
    def __init__(self, name: str = "Bad Cleanup", verbose: bool = False):
        super().__init__(name, verbose)

    def validate(self) -> bool:
        return True

    def cleanup(self) -> None:
        raise RuntimeError("cleanup failed")


class TestClosedLoopValidator:
    """ClosedLoopValidator orchestrates ValidationStage instances."""

    def test_init_creates_five_default_stages(self):
        validator = vcl.ClosedLoopValidator(verbose=False)
        assert len(validator.stages) == 5
        # Spot-check class membership rather than identity
        class_names = [type(s).__name__ for s in validator.stages]
        assert "StorageCheck" in class_names
        assert "SynthesisCheck" in class_names
        assert "IntegrationCheck" in class_names
        assert "SyncCheck" in class_names
        assert "ReportingCheck" in class_names

    def test_run_all_pass(self, capsys: pytest.CaptureFixture[str]):
        validator = vcl.ClosedLoopValidator(verbose=False)
        validator.stages = [_AlwaysPasses("A"), _AlwaysPasses("B")]
        passed, total = validator.run()
        assert (passed, total) == (2, 2)
        out = capsys.readouterr().out
        assert "PASS" in out
        # Cleanup was invoked
        assert all(getattr(s, "cleaned", False) for s in validator.stages)

    def test_run_mixed_results(self, capsys: pytest.CaptureFixture[str]):
        validator = vcl.ClosedLoopValidator(verbose=False)
        validator.stages = [_AlwaysPasses("A"), _AlwaysFails("B")]
        passed, total = validator.run()
        assert (passed, total) == (1, 2)
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "intentional failure" in out
        assert "also a warning" in out

    def test_run_catches_exception_in_validate(
        self, capsys: pytest.CaptureFixture[str]
    ):
        validator = vcl.ClosedLoopValidator(verbose=False)
        boom = _Raises("Boom")
        validator.stages = [boom]
        passed, total = validator.run()
        assert (passed, total) == (0, 1)
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "validate exploded" in out
        # Cleanup still runs in the finally block
        assert boom.cleaned is True

    def test_run_swallows_cleanup_exception(self, capsys: pytest.CaptureFixture[str]):
        validator = vcl.ClosedLoopValidator(verbose=True)
        validator.stages = [_CleanupRaises("Bad")]
        # Should not raise even though cleanup raises
        passed, total = validator.run()
        assert (passed, total) == (1, 1)
        out = capsys.readouterr().out
        # Verbose mode surfaces the cleanup error
        assert "Cleanup error" in out

    def test_stage_filter_runs_only_matching_stage(
        self, capsys: pytest.CaptureFixture[str]
    ):
        validator = vcl.ClosedLoopValidator(verbose=False, stage="storage")
        passed_stage = _AlwaysPasses("Storage Check")
        skipped_stage = _AlwaysFails("Synthesis Check")
        validator.stages = [passed_stage, skipped_stage]
        passed, total = validator.run()
        # Only the storage-prefixed stage should have run
        assert (passed, total) == (1, 1)

    def test_stage_filter_case_insensitive(self):
        validator = vcl.ClosedLoopValidator(verbose=False, stage="STORAGE")
        validator.stages = [_AlwaysPasses("Storage Check")]
        passed, total = validator.run()
        assert (passed, total) == (1, 1)

    def test_print_summary_all_passed(self, capsys: pytest.CaptureFixture[str]):
        validator = vcl.ClosedLoopValidator(verbose=False)
        validator.print_summary(5, 5)
        out = capsys.readouterr().out
        assert "ALL CHECKS PASSED" in out
        assert "5/5" in out

    def test_print_summary_some_failed(self, capsys: pytest.CaptureFixture[str]):
        validator = vcl.ClosedLoopValidator(verbose=False)
        validator.print_summary(3, 5)
        out = capsys.readouterr().out
        assert "SOME CHECKS FAILED" in out
        assert "3/5" in out


# ═══════════════════════════════════════════════════════════════════════════
# main() CLI entrypoint
# ═══════════════════════════════════════════════════════════════════════════


class TestMain:
    """main() is the CLI entrypoint; returns an exit code."""

    def test_cleanup_only_returns_zero_without_running_validation(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        monkeypatch.setattr(sys, "argv", ["validate_closed_loop", "--cleanup-only"])

        class _Sentinel:
            def __init__(self, *a, **kw):
                raise AssertionError("validator must not be constructed")

        monkeypatch.setattr(vcl, "ClosedLoopValidator", _Sentinel)

        assert vcl.main() == 0
        out = capsys.readouterr().out
        assert "Cleanup mode" in out

    def test_returns_zero_when_all_stages_pass(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "argv", ["validate_closed_loop"])

        with (
            patch.object(vcl.ClosedLoopValidator, "run", return_value=(5, 5)),
            patch.object(vcl.ClosedLoopValidator, "print_summary"),
        ):
            assert vcl.main() == 0

    def test_returns_one_when_any_stage_fails(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "argv", ["validate_closed_loop"])

        with (
            patch.object(vcl.ClosedLoopValidator, "run", return_value=(3, 5)),
            patch.object(vcl.ClosedLoopValidator, "print_summary"),
        ):
            assert vcl.main() == 1

    def test_returns_zero_when_no_stages_selected_via_filter(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """A stage filter that matches nothing yields (0, 0). 0 == 0 -> exit 0."""
        monkeypatch.setattr(sys, "argv", ["validate_closed_loop", "--stage", "storage"])

        with (
            patch.object(vcl.ClosedLoopValidator, "run", return_value=(0, 0)),
            patch.object(vcl.ClosedLoopValidator, "print_summary"),
        ):
            assert vcl.main() == 0

    def test_rejects_invalid_stage_value(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_closed_loop", "--stage", "not_a_real_stage"],
        )
        with pytest.raises(SystemExit) as exc:
            vcl.main()
        # argparse uses exit code 2 for argument errors
        assert exc.value.code == 2

    def test_verbose_flag_is_passed_to_validator(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "argv", ["validate_closed_loop", "--verbose"])
        recorded: dict[str, Any] = {}

        original_init = vcl.ClosedLoopValidator.__init__

        def spy_init(self, *args, **kwargs):
            recorded.update(kwargs)
            original_init(self, *args, **kwargs)

        with (
            patch.object(vcl.ClosedLoopValidator, "__init__", spy_init),
            patch.object(vcl.ClosedLoopValidator, "run", return_value=(0, 0)),
            patch.object(vcl.ClosedLoopValidator, "print_summary"),
        ):
            vcl.main()

        assert recorded.get("verbose") is True
