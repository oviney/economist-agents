#!/usr/bin/env python3
"""
Pre-commit Architecture Review

Checks staged Python files for architectural anti-patterns.
Fails the commit when new violations are detected, giving developers
immediate feedback rather than waiting for CI.

Anti-patterns detected:
  1. ADR-002: Direct LLM imports outside allowed files
  2. Unprotected json.loads calls (defensive-parsing pattern)
  3. Hardcoded secrets / API keys
  4. print() used instead of logger for errors/warnings

Usage (via pre-commit framework):
    pre-commit run arch-review --all-files

Manual usage:
    python3 scripts/pre_commit_arch_check.py [file1.py file2.py ...]
    python3 scripts/pre_commit_arch_check.py          # checks all staged files
"""

import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# ADR-002: Files allowed to import LLM libraries directly
LLM_IMPORT_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "agent_registry.py",
        "llm_client.py",
        "crewai_agents.py",
        "run_story2_crew.py",
        "run_story7_crew.py",
        "run_story10_crew.py",
        "run_story11_crew.py",
        "featured_image_agent.py",  # TODO: refactor (Story 10)
        "visual_qa.py",  # TODO: refactor (Story 10)
    }
)

# LLM libraries that must not be imported directly (ADR-002)
PROHIBITED_LLM_IMPORTS: frozenset[str] = frozenset({"openai", "anthropic", "crewai"})

# Patterns that suggest a hardcoded secret
SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*=\s*["\'][^"\']{8,}["\']'),
    re.compile(r'"sk-[A-Za-z0-9]{20,}"'),  # OpenAI-style key
    re.compile(r'"sk-ant-[A-Za-z0-9\-]{20,}"'),  # Anthropic-style key
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    """A single architectural violation found in a file."""

    file: str
    line: int
    rule: str
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass
class CheckResult:
    """Result of running all checks on a set of files."""

    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0

    @property
    def has_errors(self) -> bool:
        """Return True if any error-level violations were found."""
        return any(v.severity == "error" for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _get_imports(source: str, filename: str) -> list[tuple[int, str]]:
    """Return (lineno, base_module) pairs for all imports in *source*.

    Args:
        source: Python source code string.
        filename: Filename (used only for error reporting).

    Returns:
        List of (line_number, base_module_name) tuples.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []

    results: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((node.lineno, alias.name.split(".")[0]))
        elif isinstance(node, ast.ImportFrom) and node.module:
            results.append((node.lineno, node.module.split(".")[0]))

    return results


def _find_bare_json_loads(source: str, filename: str) -> list[int]:
    """Return line numbers where json.loads is called outside a try block.

    A *bare* call is one that is not directly inside a ``try`` body.  We use
    a simple AST walk: collect every ``json.loads`` call, then check whether
    its line falls inside any try-body range in the same file.

    Args:
        source: Python source code string.
        filename: Filename (used only for error reporting).

    Returns:
        List of line numbers with unprotected json.loads calls.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []

    # Collect ranges covered by try-body blocks
    try_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.body:
            start = node.body[0].lineno
            end = node.body[-1].end_lineno or node.body[-1].lineno
            try_ranges.append((start, end))

    def _in_try(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in try_ranges)

    bare_lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # json.loads(...)
        is_json_loads = (
            isinstance(func, ast.Attribute)
            and func.attr == "loads"
            and isinstance(func.value, ast.Name)
            and func.value.id == "json"
        )
        if is_json_loads and not _in_try(node.lineno):
            bare_lines.append(node.lineno)

    return bare_lines


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------


def check_llm_imports(path: Path, source: str) -> list[Violation]:
    """ADR-002: Direct LLM library imports are prohibited outside exceptions.

    Args:
        path: File path being checked.
        source: File source code.

    Returns:
        List of Violation objects for each prohibited import found.
    """
    if path.name in LLM_IMPORT_EXCEPTIONS:
        return []

    violations: list[Violation] = []
    for lineno, module in _get_imports(source, path.name):
        if module in PROHIBITED_LLM_IMPORTS:
            violations.append(
                Violation(
                    file=str(path),
                    line=lineno,
                    rule="ADR-002",
                    message=(
                        f"Direct import of '{module}' violates ADR-002. "
                        "Use AgentRegistry.get_agent() instead."
                    ),
                    severity="error",
                )
            )
    return violations


def check_unprotected_json_loads(path: Path, source: str) -> list[Violation]:
    """Defensive-parsing: json.loads must be wrapped in try/except.

    LLM responses may contain non-JSON text (markdown fences, prose).
    Bare json.loads calls will crash on unexpected output.

    Args:
        path: File path being checked.
        source: File source code.

    Returns:
        List of Violation objects.
    """
    violations: list[Violation] = []
    for lineno in _find_bare_json_loads(source, path.name):
        violations.append(
            Violation(
                file=str(path),
                line=lineno,
                rule="defensive-json-parsing",
                message=(
                    "json.loads() called outside try/except. "
                    "Wrap in try/except to handle malformed LLM responses."
                ),
                severity="warning",
            )
        )
    return violations


def check_hardcoded_secrets(path: Path, source: str) -> list[Violation]:
    """Security: API keys and secrets must not be hardcoded in source.

    Args:
        path: File path being checked.
        source: File source code.

    Returns:
        List of Violation objects.
    """
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        # Skip comment lines
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append(
                    Violation(
                        file=str(path),
                        line=lineno,
                        rule="no-hardcoded-secrets",
                        message=(
                            "Possible hardcoded secret or API key detected. "
                            "Use environment variables instead (e.g. os.getenv('API_KEY'))."
                        ),
                        severity="error",
                    )
                )
                break  # one violation per line is enough
    return violations


def check_print_for_errors(path: Path, source: str) -> list[Violation]:
    """Style/observability: print() should not be used for error reporting.

    Agent scripts must use a proper logger so output is structured and
    traceable.  Plain print() calls for error conditions slip past code
    review and break log aggregation.

    Only flags calls that include obvious error/warning keywords to avoid
    false-positives on intentional user-facing print statements.

    Args:
        path: File path being checked.
        source: File source code.

    Returns:
        List of Violation objects.
    """
    error_print_re = re.compile(
        r'\bprint\s*\(\s*[f"\'r].*?\b(error|warning|failed|exception)\b',
        re.IGNORECASE,
    )
    violations: list[Violation] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if error_print_re.search(line):
            violations.append(
                Violation(
                    file=str(path),
                    line=lineno,
                    rule="use-logger",
                    message=(
                        "Use logger.error() / logger.warning() instead of print() "
                        "for error/warning output."
                    ),
                    severity="warning",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------

CHECKS = [
    check_llm_imports,
    check_unprotected_json_loads,
    check_hardcoded_secrets,
    check_print_for_errors,
]


def check_file(path: Path) -> list[Violation]:
    """Run all architectural checks on a single Python file.

    Args:
        path: Absolute or relative path to a Python file.

    Returns:
        List of Violation objects (may be empty).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []

    violations: list[Violation] = []
    for check in CHECKS:
        violations.extend(check(path, source))
    return violations


def get_staged_python_files(repo_root: Path) -> list[Path]:
    """Return a list of staged (added/modified) Python files.

    Args:
        repo_root: Root directory of the git repository.

    Returns:
        List of Path objects for staged Python files that exist on disk.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    paths: list[Path] = []
    for line in result.stdout.splitlines():
        p = repo_root / line.strip()
        if p.suffix == ".py" and p.exists():
            paths.append(p)
    return paths


def run_checks(files: list[Path]) -> CheckResult:
    """Run all architectural checks on the given list of files.

    Args:
        files: List of Python file paths to check.

    Returns:
        CheckResult containing all violations and metadata.
    """
    result = CheckResult()
    result.files_checked = len(files)

    for path in files:
        result.violations.extend(check_file(path))

    return result


def format_report(result: CheckResult) -> str:
    """Format a human-readable report from a CheckResult.

    Args:
        result: The CheckResult to format.

    Returns:
        Multi-line string suitable for printing to the terminal.
    """
    lines: list[str] = []

    if not result.violations:
        lines.append(
            f"✅  Architecture check passed ({result.files_checked} file(s) reviewed)"
        )
        return "\n".join(lines)

    lines.append("")
    lines.append("=" * 72)
    lines.append("🏗️  ARCHITECTURE REVIEW — PRE-COMMIT CHECK")
    lines.append("=" * 72)

    for v in result.violations:
        icon = "❌" if v.severity == "error" else "⚠️ "
        lines.append(f"\n{icon}  [{v.rule}] {v.file}:{v.line}")
        lines.append(f"   {v.message}")

    lines.append("")
    lines.append(
        f"Found {result.error_count} error(s) and {result.warning_count} warning(s) "
        f"across {result.files_checked} file(s)."
    )

    if result.has_errors:
        lines.append("")
        lines.append("Commit BLOCKED — fix errors above before committing.")
        lines.append(
            "Run  pre-commit run arch-review --all-files  to re-check after fixing."
        )
    else:
        lines.append("")
        lines.append("Warnings are informational only; commit is allowed to proceed.")

    lines.append("=" * 72)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the pre-commit hook.

    When invoked by the pre-commit framework, filenames are passed as
    positional arguments.  When invoked manually with no arguments the
    staged files are discovered via ``git diff --cached``.

    Args:
        argv: List of file paths to check (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 if errors were found.
    """
    if argv is None:
        argv = sys.argv[1:]

    repo_root = Path(__file__).parent.parent

    if argv:
        files = [Path(f) for f in argv if Path(f).suffix == ".py"]
    else:
        files = get_staged_python_files(repo_root)

    if not files:
        print("✅  No Python files to check.")
        return 0

    result = run_checks(files)
    print(format_report(result))

    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
