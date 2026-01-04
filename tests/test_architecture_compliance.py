"""Architecture Compliance Tests - Enforce ADR-002 Agent Registry Pattern.

This test suite prevents "Agent Sprawl" by ensuring scripts use the AgentRegistry
pattern instead of directly instantiating LLM clients.

ADR-002 Context:
- All LLM instantiation should go through AgentRegistry
- Direct imports of openai, anthropic, or crewai are prohibited
- Exceptions: agent_registry.py, llm_client.py, crewai_agents.py

Target: 100% compliance across scripts/
"""

import ast
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ═══════════════════════════════════════════════════════════════════════════
# TEST CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Files allowed to import LLM libraries directly (ADR-002 exceptions)
ALLOWED_FILES = {
    "agent_registry.py",  # Factory for LLM instantiation
    "llm_client.py",  # Unified LLM client wrapper
    "crewai_agents.py",  # Legacy adapter (to be deprecated)
    # TECHNICAL DEBT: Legacy files predating ADR-002 (to be refactored)
    "featured_image_agent.py",  # TODO: Refactor to use AgentRegistry (Story 10)
    "visual_qa.py",  # TODO: Refactor to use AgentRegistry (Story 10)
}

# LLM libraries that should not be imported directly
PROHIBITED_IMPORTS = {
    "openai",  # OpenAI GPT models
    "anthropic",  # Anthropic Claude models
    "crewai",  # CrewAI framework (use via registry)
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts all imports from a Python file."""

    def __init__(self):
        self.imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements (e.g., 'import openai')."""
        for alias in node.names:
            # Get base module name (e.g., 'openai' from 'openai.chat')
            base_module = alias.name.split(".")[0]
            self.imports.add(base_module)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-imports (e.g., 'from openai import OpenAI')."""
        if node.module:
            # Get base module name
            base_module = node.module.split(".")[0]
            self.imports.add(base_module)


def get_imports_from_file(file_path: Path) -> set[str]:
    """Extract all imports from a Python file using AST parsing.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        Set of imported module names (base modules only)

    Raises:
        SyntaxError: If file cannot be parsed
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        visitor = ImportVisitor()
        visitor.visit(tree)
        return visitor.imports

    except SyntaxError as e:
        pytest.fail(f"Syntax error in {file_path.name}: {e}")
        return set()


def get_all_python_files(directory: Path) -> list[Path]:
    """Get all Python files in a directory (non-recursive).

    Args:
        directory: Directory to scan for .py files

    Returns:
        List of Python file paths
    """
    return sorted(directory.glob("*.py"))


def check_file_for_violations(
    file_path: Path,
) -> tuple[bool, list[str]]:
    """Check a Python file for architecture violations.

    Args:
        file_path: Path to Python file to check

    Returns:
        Tuple of (has_violations, list_of_violated_imports)
    """
    # Skip allowed files
    if file_path.name in ALLOWED_FILES:
        return False, []

    # Skip __init__.py and __pycache__
    if file_path.name.startswith("__"):
        return False, []

    # Extract imports
    imports = get_imports_from_file(file_path)

    # Check for prohibited imports
    violations = [imp for imp in imports if imp in PROHIBITED_IMPORTS]

    return len(violations) > 0, violations


# ═══════════════════════════════════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════════════════════════════════


def test_scripts_directory_exists():
    """Verify scripts directory exists for testing."""
    assert SCRIPTS_DIR.exists(), f"Scripts directory not found: {SCRIPTS_DIR}"
    assert SCRIPTS_DIR.is_dir(), f"Scripts path is not a directory: {SCRIPTS_DIR}"


def test_no_direct_llm_imports_in_scripts():
    """Enforce ADR-002: Scripts must not import LLM libraries directly.

    Architecture Rule:
    - All LLM instantiation must go through AgentRegistry
    - Direct imports of openai, anthropic, crewai are prohibited
    - Exceptions: agent_registry.py, llm_client.py, crewai_agents.py

    Why:
    - Prevents agent sprawl and coupling
    - Enables centralized provider swapping
    - Facilitates testing with mock agents
    - Enforces single responsibility principle
    """
    python_files = get_all_python_files(SCRIPTS_DIR)
    assert len(python_files) > 0, "No Python files found in scripts/"

    violations: list[tuple[str, list[str]]] = []

    for file_path in python_files:
        has_violation, violated_imports = check_file_for_violations(file_path)

        if has_violation:
            violations.append((file_path.name, violated_imports))

    # Assert no violations found
    if violations:
        error_messages = []
        error_messages.append("\n" + "=" * 80)
        error_messages.append(
            "ARCHITECTURE VIOLATION (ADR-002): Direct LLM imports detected"
        )
        error_messages.append("=" * 80)
        error_messages.append("")

        for filename, imports in violations:
            error_messages.append(f"❌ {filename}")
            error_messages.append(f"   Prohibited imports: {', '.join(imports)}")
            error_messages.append(
                "   Solution: Use AgentRegistry.get_agent() instead of direct instantiation"
            )
            error_messages.append("")

        error_messages.append("Allowed exceptions (ADR-002):")
        for allowed in ALLOWED_FILES:
            error_messages.append(f"  ✓ {allowed}")
        error_messages.append("")

        error_messages.append("Why this matters:")
        error_messages.append("  - Prevents agent sprawl and tight coupling")
        error_messages.append("  - Enables centralized LLM provider swapping")
        error_messages.append("  - Facilitates testing with mock agents")
        error_messages.append("  - Enforces single responsibility principle")
        error_messages.append("")

        error_messages.append("See: docs/ADR-002-agent-registry-pattern.md")
        error_messages.append("=" * 80)

        pytest.fail("\n".join(error_messages))


def test_allowed_files_have_llm_imports():
    """Verify exception files actually import LLM libraries (sanity check).

    This ensures our ALLOWED_FILES list is accurate and not stale.
    """
    found_exceptions = []

    for file_path in get_all_python_files(SCRIPTS_DIR):
        if file_path.name in ALLOWED_FILES:
            imports = get_imports_from_file(file_path)
            has_llm_import = any(imp in PROHIBITED_IMPORTS for imp in imports)

            if has_llm_import:
                found_exceptions.append(file_path.name)

    # At least llm_client.py should have LLM imports
    assert (
        len(found_exceptions) > 0
    ), "No LLM imports found in exception files - ALLOWED_FILES may be stale"


def test_ast_parsing_works():
    """Verify AST parsing correctly identifies imports.

    This is a meta-test to ensure our detection logic works correctly.
    """
    # Create a test file content with various import styles
    test_code = """
import openai
from anthropic import Anthropic
import os
from pathlib import Path
from crewai import Agent, Task
"""

    tree = ast.parse(test_code)
    visitor = ImportVisitor()
    visitor.visit(tree)

    # Should detect LLM imports
    assert "openai" in visitor.imports, "Failed to detect 'import openai'"
    assert "anthropic" in visitor.imports, "Failed to detect 'from anthropic import'"
    assert "crewai" in visitor.imports, "Failed to detect 'from crewai import'"

    # Should also detect standard library imports
    assert "os" in visitor.imports
    assert "pathlib" in visitor.imports


@pytest.mark.parametrize(
    "filename,should_be_allowed",
    [
        ("agent_registry.py", True),
        ("llm_client.py", True),
        ("crewai_agents.py", True),
        ("economist_agent.py", False),
        ("topic_scout.py", False),
        ("editorial_board.py", False),
    ],
)
def test_allowed_files_configuration(filename: str, should_be_allowed: bool):
    """Verify ALLOWED_FILES configuration is correct.

    Args:
        filename: File to check
        should_be_allowed: Whether file should be allowed to import LLMs
    """
    is_allowed = filename in ALLOWED_FILES
    assert (
        is_allowed == should_be_allowed
    ), f"{filename} allowed status is incorrect: expected {should_be_allowed}, got {is_allowed}"


# ═══════════════════════════════════════════════════════════════════════════
# COVERAGE REPORT
# ═══════════════════════════════════════════════════════════════════════════


def test_generate_architecture_compliance_report():
    """Generate a comprehensive compliance report for all scripts.

    This is informational and always passes, but logs compliance status.
    """
    python_files = get_all_python_files(SCRIPTS_DIR)

    compliant_files = []
    exception_files = []
    violation_files = []

    for file_path in python_files:
        if file_path.name in ALLOWED_FILES:
            exception_files.append(file_path.name)
            continue

        if file_path.name.startswith("__"):
            continue

        has_violation, violated_imports = check_file_for_violations(file_path)

        if has_violation:
            violation_files.append((file_path.name, violated_imports))
        else:
            compliant_files.append(file_path.name)

    # Print report (always visible with pytest -v)
    print("\n" + "=" * 80)
    print("ARCHITECTURE COMPLIANCE REPORT (ADR-002)")
    print("=" * 80)
    print(f"\n✅ Compliant Files: {len(compliant_files)}")
    for filename in compliant_files:
        print(f"   {filename}")

    print(f"\n⚠️  Exception Files (Allowed): {len(exception_files)}")
    for filename in exception_files:
        print(f"   {filename}")

    if violation_files:
        print(f"\n❌ Violations: {len(violation_files)}")
        for filename, imports in violation_files:
            print(f"   {filename}: {', '.join(imports)}")
    else:
        print("\n✅ No violations detected")

    total_files = len(compliant_files) + len(exception_files)
    print(f"\nTotal analyzed: {total_files} files")
    print("=" * 80 + "\n")

    # This test always passes (informational only)
    assert True
