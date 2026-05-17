#!/usr/bin/env python3
"""CI guard: forbid bare-name imports of scripts/ modules.

A bare-name import (`from llm_client import call_llm` or `import llm_client`)
resolves through sys.path; if another module named ``llm_client`` exists
anywhere on sys.path, it silently takes precedence. This is the CVE-377
adjacent class — module spoofing via sys.path manipulation. ADR-0010 mandates
fully-qualified imports (``from scripts.llm_client import call_llm``).

This guard walks every .py file under src/, scripts/, agents/, tests/, and
mcp_servers/ and uses ast to detect either form of the bare-name pattern
targeting any top-level module in scripts/. AST parsing means it does not
false-positive on docstring examples — only real import statements count.

Exit code 0 on clean, 1 on any violation.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCAN_ROOTS = ["src", "scripts", "agents", "tests", "mcp_servers"]
EXCLUDE_DIRS = {"archived", "__pycache__", ".venv", "venv", "node_modules"}

# scripts/__init__.py itself is allowed to use `from .X import Y` style;
# any module in scripts/ that re-exports siblings via relative imports is
# fine. We only flag bare-name absolute imports.


def _collect_scripts_modules() -> set[str]:
    """Return the set of module names defined at the top level of scripts/."""
    names: set[str] = set()
    for p in SCRIPTS_DIR.glob("*.py"):
        if p.name == "__init__.py":
            continue
        names.add(p.stem)
    return names


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for p in root_path.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            files.append(p)
    return files


def _check_file(path: Path, scripts_modules: set[str]) -> list[tuple[int, str]]:
    """Return list of (lineno, snippet) violations for a single file."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # `from X import Y` — flag when X is a bare scripts/ module name
            # and there is no leading dot (absolute import).
            if node.level == 0 and node.module in scripts_modules:
                violations.append(
                    (node.lineno, f"from {node.module} import ..."),
                )
        elif isinstance(node, ast.Import):
            # `import X` or `import X as Y` — flag when X is a bare
            # scripts/ module name.
            for alias in node.names:
                if alias.name in scripts_modules:
                    violations.append(
                        (alias.lineno or node.lineno, f"import {alias.name}"),
                    )
    return violations


def main() -> int:
    scripts_modules = _collect_scripts_modules()
    if not scripts_modules:
        print("error: no modules found under scripts/", file=sys.stderr)
        return 1

    all_violations: list[tuple[Path, int, str]] = []
    for path in _iter_py_files():
        for lineno, snippet in _check_file(path, scripts_modules):
            all_violations.append((path, lineno, snippet))

    if not all_violations:
        print(
            f"OK: no bare-name imports of {len(scripts_modules)} scripts/ "
            "modules found across the codebase.",
        )
        return 0

    print(
        f"::error::Bare-name import(s) of scripts/ modules detected "
        f"({len(all_violations)} site(s)). Use 'from scripts.<module> "
        "import ...' or 'from scripts import <module>' — see ADR-0010, "
        "PR #383, PR #391, issue #395.",
        file=sys.stderr,
    )
    for path, lineno, snippet in sorted(all_violations):
        rel = path.relative_to(REPO_ROOT)
        print(f"{rel}:{lineno}: {snippet}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
