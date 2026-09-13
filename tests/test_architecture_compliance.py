"""Architecture compliance: the only LLM path is the Agent SDK on the subscription.

Constraint #3 (CLAUDE.md): no code under ``src/``, ``scripts/`` or ``mcp_servers/``
may import a pay-per-use provider SDK directly. Until B-048 slice 2 this was an
allow-list around a ``scripts/llm_client.py`` factory; the factory and its last
callers are gone, so the rule is now absolute and needs no exceptions.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_TOP_LEVEL = {"anthropic", "openai"}


def _production_files() -> list[Path]:
    files: list[Path] = []
    for top in ("src", "scripts", "mcp_servers"):
        files.extend(
            p
            for p in (REPO_ROOT / top).rglob("*.py")
            if "archived" not in p.parts and "__pycache__" not in p.parts
        )
    return files


def _direct_provider_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        else:
            continue
        found.extend(n for n in names if n.split(".")[0] in FORBIDDEN_TOP_LEVEL)
    return found


@pytest.mark.parametrize(
    "path", _production_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_direct_provider_sdk_imports(path: Path) -> None:
    assert _direct_provider_imports(path) == [], (
        f"{path.relative_to(REPO_ROOT)} imports a pay-per-use provider SDK directly; "
        "the only LLM auth is the Claude subscription via claude_agent_sdk (constraint #3)"
    )


def test_the_check_itself_can_fail(tmp_path: Path) -> None:
    """A sensor that cannot fail is decoration (B-043)."""
    bad = tmp_path / "bad.py"
    bad.write_text("from anthropic import Anthropic\n")
    assert _direct_provider_imports(bad) == ["anthropic"]
