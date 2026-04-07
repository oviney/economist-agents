"""Tests for the pre-commit architecture review checker.

Validates that each anti-pattern rule detects violations correctly
and that clean code passes without false positives.
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from pre_commit_arch_check import (  # noqa: E402
    CheckResult,
    LLM_IMPORT_EXCEPTIONS,
    Violation,
    check_file,
    check_hardcoded_secrets,
    check_llm_imports,
    check_print_for_errors,
    check_unprotected_json_loads,
    format_report,
    get_staged_python_files,
    run_checks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_py(tmp_path: Path):
    """Factory fixture: write source to a temp .py file and return its Path."""

    def _write(content: str, name: str = "test_module.py") -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    return _write


# ---------------------------------------------------------------------------
# check_llm_imports
# ---------------------------------------------------------------------------


class TestCheckLLMImports:
    """ADR-002: direct LLM imports must not appear outside exception files."""

    def test_direct_import_flagged(self, tmp_py):
        source = "import openai\n"
        path = tmp_py(source)
        violations = check_llm_imports(path, source)
        assert len(violations) == 1
        assert violations[0].rule == "ADR-002"
        assert violations[0].severity == "error"
        assert "openai" in violations[0].message

    def test_from_import_flagged(self, tmp_py):
        source = "from anthropic import Anthropic\n"
        path = tmp_py(source)
        violations = check_llm_imports(path, source)
        assert len(violations) == 1
        assert "anthropic" in violations[0].message

    def test_crewai_import_flagged(self, tmp_py):
        source = "from crewai import Agent\n"
        path = tmp_py(source)
        violations = check_llm_imports(path, source)
        assert len(violations) == 1

    def test_standard_library_allowed(self, tmp_py):
        source = "import os\nfrom pathlib import Path\n"
        path = tmp_py(source)
        violations = check_llm_imports(path, source)
        assert violations == []

    def test_exception_file_skipped(self, tmp_py):
        """llm_client.py is in LLM_IMPORT_EXCEPTIONS and must not be flagged."""
        source = "import anthropic\n"
        path = tmp_py(source, name="llm_client.py")
        violations = check_llm_imports(path, source)
        assert violations == []

    def test_all_exception_files_skipped(self, tmp_py):
        """Every file in LLM_IMPORT_EXCEPTIONS should pass without violations."""
        source = "import anthropic\nimport openai\nfrom crewai import Agent\n"
        for exception_file in LLM_IMPORT_EXCEPTIONS:
            path = tmp_py(source, name=exception_file)
            violations = check_llm_imports(path, source)
            assert violations == [], f"{exception_file} should be exempt"

    def test_line_number_reported(self, tmp_py):
        source = "# line 1\nimport openai\n"
        path = tmp_py(source)
        violations = check_llm_imports(path, source)
        assert violations[0].line == 2


# ---------------------------------------------------------------------------
# check_unprotected_json_loads
# ---------------------------------------------------------------------------


class TestCheckUnprotectedJsonLoads:
    """Bare json.loads() calls should be flagged as warnings."""

    def test_bare_json_loads_flagged(self, tmp_py):
        source = (
            "import json\n"
            "data = json.loads(response)\n"
        )
        path = tmp_py(source)
        violations = check_unprotected_json_loads(path, source)
        assert len(violations) == 1
        assert violations[0].rule == "defensive-json-parsing"
        assert violations[0].severity == "warning"

    def test_json_loads_in_try_allowed(self, tmp_py):
        source = (
            "import json\n"
            "try:\n"
            "    data = json.loads(response)\n"
            "except json.JSONDecodeError:\n"
            "    data = {}\n"
        )
        path = tmp_py(source)
        violations = check_unprotected_json_loads(path, source)
        assert violations == []

    def test_no_json_loads_clean(self, tmp_py):
        source = "import os\nx = 1 + 1\n"
        path = tmp_py(source)
        violations = check_unprotected_json_loads(path, source)
        assert violations == []

    def test_orjson_loads_not_flagged(self, tmp_py):
        """orjson.loads uses a different AST node (different variable name)."""
        source = (
            "import orjson\n"
            "data = orjson.loads(response)\n"
        )
        path = tmp_py(source)
        # orjson.loads uses 'orjson', not 'json' — should NOT be flagged
        violations = check_unprotected_json_loads(path, source)
        assert violations == []


# ---------------------------------------------------------------------------
# check_hardcoded_secrets
# ---------------------------------------------------------------------------


class TestCheckHardcodedSecrets:
    """Hardcoded API keys and secrets must be blocked."""

    def test_api_key_assignment_flagged(self, tmp_py):
        source = 'API_KEY = "sk-abcdef1234567890abcd"\n'
        path = tmp_py(source)
        violations = check_hardcoded_secrets(path, source)
        assert len(violations) == 1
        assert violations[0].rule == "no-hardcoded-secrets"
        assert violations[0].severity == "error"

    def test_anthropic_key_flagged(self, tmp_py):
        source = 'key = "sk-ant-api03-AbcDefGhIjKlMnOpQrStUvWxYz1234"\n'
        path = tmp_py(source)
        violations = check_hardcoded_secrets(path, source)
        assert len(violations) == 1

    def test_env_var_usage_allowed(self, tmp_py):
        source = 'API_KEY = os.getenv("ANTHROPIC_API_KEY")\n'
        path = tmp_py(source)
        violations = check_hardcoded_secrets(path, source)
        assert violations == []

    def test_comment_line_skipped(self, tmp_py):
        source = '# API_KEY = "sk-abcdef1234567890abcd"  # example\n'
        path = tmp_py(source)
        violations = check_hardcoded_secrets(path, source)
        assert violations == []

    def test_short_string_not_flagged(self, tmp_py):
        """Short strings (< 8 chars) should not trip the secret detector."""
        source = 'password = "short"\n'
        path = tmp_py(source)
        violations = check_hardcoded_secrets(path, source)
        assert violations == []


# ---------------------------------------------------------------------------
# check_print_for_errors
# ---------------------------------------------------------------------------


class TestCheckPrintForErrors:
    """print() calls that contain error/warning keywords should be flagged."""

    def test_print_error_flagged(self, tmp_py):
        source = 'print(f"Error: {e}")\n'
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert len(violations) == 1
        assert violations[0].rule == "use-logger"
        assert violations[0].severity == "warning"

    def test_print_warning_flagged(self, tmp_py):
        source = 'print("Warning: rate limit hit")\n'
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert len(violations) == 1

    def test_print_single_quote_flagged(self, tmp_py):
        """Single-quoted error print should also be detected."""
        source = "print('Error: request failed')\n"
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert len(violations) == 1

    def test_neutral_print_allowed(self, tmp_py):
        """A plain informational print should not be flagged."""
        source = 'print("Starting pipeline...")\n'
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert violations == []

    def test_logger_call_not_flagged(self, tmp_py):
        source = 'logger.error(f"Error: {e}")\n'
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert violations == []

    def test_comment_line_skipped(self, tmp_py):
        source = '# print(f"Error: ignored")\n'
        path = tmp_py(source)
        violations = check_print_for_errors(path, source)
        assert violations == []


# ---------------------------------------------------------------------------
# check_file integration
# ---------------------------------------------------------------------------


class TestCheckFile:
    """Integration test: check_file runs all rules on one file."""

    def test_clean_file_no_violations(self, tmp_py):
        source = (
            "import os\n"
            "import json\n"
            "import logging\n"
            "\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            "def run() -> None:\n"
            '    api_key = os.getenv("API_KEY")\n'
            "    try:\n"
            "        data = json.loads('{}')\n"
            "    except Exception as exc:\n"
            "        logger.error('Failed: %s', exc)\n"
        )
        path = tmp_py(source)
        violations = check_file(path)
        assert violations == []

    def test_multiple_violations_detected(self, tmp_py):
        source = (
            "import anthropic\n"
            "import json\n"
            "data = json.loads(response)\n"
        )
        path = tmp_py(source)
        violations = check_file(path)
        # Should catch ADR-002 and bare json.loads
        rules = {v.rule for v in violations}
        assert "ADR-002" in rules
        assert "defensive-json-parsing" in rules

    def test_nonexistent_file_returns_empty(self):
        path = Path("/nonexistent/fake_module.py")
        violations = check_file(path)
        assert violations == []


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------


class TestRunChecks:
    """run_checks aggregates results across multiple files."""

    def test_empty_file_list(self):
        result = run_checks([])
        assert result.files_checked == 0
        assert result.violations == []
        assert not result.has_errors

    def test_counts_files_checked(self, tmp_py):
        f1 = tmp_py("import os\n", name="a.py")
        f2 = tmp_py("import os\n", name="b.py")
        result = run_checks([f1, f2])
        assert result.files_checked == 2

    def test_aggregates_violations(self, tmp_py):
        f1 = tmp_py("import openai\n", name="bad_a.py")
        f2 = tmp_py("import anthropic\n", name="bad_b.py")
        result = run_checks([f1, f2])
        assert result.error_count == 2

    def test_has_errors_false_for_warnings_only(self, tmp_py):
        source = (
            "import json\n"
            "data = json.loads(response)\n"
        )
        path = tmp_py(source)
        result = run_checks([path])
        # Only warning (unprotected json.loads), no errors
        assert result.warning_count >= 1
        assert not result.has_errors


# ---------------------------------------------------------------------------
# CheckResult properties
# ---------------------------------------------------------------------------


class TestCheckResult:
    """Unit tests for CheckResult helper properties."""

    def test_has_errors_with_error(self):
        r = CheckResult(violations=[Violation("f.py", 1, "rule", "msg", "error")])
        assert r.has_errors is True

    def test_has_errors_without_error(self):
        r = CheckResult(violations=[Violation("f.py", 1, "rule", "msg", "warning")])
        assert r.has_errors is False

    def test_error_count(self):
        r = CheckResult(
            violations=[
                Violation("f.py", 1, "r", "m", "error"),
                Violation("f.py", 2, "r", "m", "warning"),
                Violation("f.py", 3, "r", "m", "error"),
            ]
        )
        assert r.error_count == 2
        assert r.warning_count == 1


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """format_report should produce human-readable output."""

    def test_clean_report_shows_passed(self):
        result = CheckResult(violations=[], files_checked=3)
        report = format_report(result)
        assert "passed" in report.lower()
        assert "3 file" in report

    def test_error_report_shows_blocked(self):
        result = CheckResult(
            violations=[Violation("bad.py", 5, "ADR-002", "Direct import", "error")],
            files_checked=1,
        )
        report = format_report(result)
        assert "BLOCKED" in report
        assert "ADR-002" in report
        assert "bad.py" in report

    def test_warning_only_not_blocked(self):
        result = CheckResult(
            violations=[
                Violation("warn.py", 3, "use-logger", "Use logger", "warning")
            ],
            files_checked=1,
        )
        report = format_report(result)
        assert "BLOCKED" not in report
        assert "warning" in report.lower()


# ---------------------------------------------------------------------------
# get_staged_python_files
# ---------------------------------------------------------------------------


class TestGetStagedPythonFiles:
    """get_staged_python_files should handle edge cases gracefully."""

    def test_returns_list(self, tmp_path):
        # May return empty list if called outside a git repo, but must not crash
        result = get_staged_python_files(tmp_path)
        assert isinstance(result, list)

    def test_real_repo_returns_paths(self):
        repo_root = Path(__file__).parent.parent
        result = get_staged_python_files(repo_root)
        # All returned paths should be .py files that exist
        for path in result:
            assert path.suffix == ".py"
            assert path.exists()
