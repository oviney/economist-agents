#!/usr/bin/env python3
"""
Fix Story 11 Import Error in Stage3Crew

This script fixes the ImportError by:
1. Removing the problematic import from agents.graphics_agent
2. Adding a default GRAPHICS_AGENT_PROMPT constant
3. Verifying the fix with pytest

Usage:
    python3 scripts/fix_story11_import.py
"""

import os
import subprocess
import sys
from pathlib import Path


def read_file(filepath: str) -> str:
    """Read file contents."""
    with open(filepath) as f:
        return f.read()


def write_file(filepath: str, content: str) -> None:
    """Write content to file."""
    with open(filepath, "w") as f:
        f.write(content)


def fix_stage3_crew_import():
    """Fix the import error in src/crews/stage3_crew.py."""

    file_path = "src/crews/stage3_crew.py"

    print(f"📖 Reading {file_path}...")
    content = read_file(file_path)

    # Step 1: Remove the problematic import line
    print("🔧 Removing problematic import...")
    old_import = "from agents.graphics_agent import GRAPHICS_AGENT_PROMPT"

    if old_import not in content:
        print(f"⚠️  Import line not found: {old_import}")
        print("   File may already be fixed.")
        return False

    # Remove the import line (including newline)
    content = content.replace(f"{old_import}\n", "")

    # Step 2: Add the default GRAPHICS_AGENT_PROMPT constant
    print("✏️  Adding default GRAPHICS_AGENT_PROMPT constant...")

    # Find the position after imports (after the last import and before the class)
    default_prompt = '''
# Default prompt for Graphics Agent
GRAPHICS_AGENT_PROMPT = """
You are a Data Visualization Specialist.
Your goal is to take complex data and describe how it should be visualized.

Create clear, accurate charts that follow Economist style guidelines:
- Clean, minimalist design
- Proper zone boundaries (red bar, title, chart, x-axis, source)
- Inline labels instead of legends
- High-quality export (PNG, 300 DPI)
"""
'''

    # Insert after imports, before the class definition
    # Find the line "from crew_ai import Crew, Agent, Task"
    import_marker = "from crew_ai import Crew, Agent, Task"

    if import_marker in content:
        # Insert the default prompt after this import
        content = content.replace(
            f"{import_marker}\n", f"{import_marker}\n{default_prompt}\n"
        )
    else:
        print(f"⚠️  Could not find import marker: {import_marker}")
        print("   Adding prompt at the beginning of the file instead.")
        # Fallback: add after the first import block
        lines = content.split("\n")
        # Find the last import line
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                last_import_idx = i

        # Insert after the last import
        lines.insert(last_import_idx + 1, default_prompt)
        content = "\n".join(lines)

    # Step 3: Save the file
    print(f"💾 Saving changes to {file_path}...")
    write_file(file_path, content)

    print("✅ Import fix applied successfully!")
    return True


def verify_fix():
    """Run pytest to verify the fix."""
    print("\n🧪 Verifying fix with pytest...")
    print("=" * 60)

    try:
        # Run pytest on the specific test file
        result = subprocess.run(
            ["pytest", "tests/reproduce_stage3.py", "-v"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print("=" * 60)
            print("✅ All tests passed! Import error is fixed.")
            return True
        else:
            print("=" * 60)
            print(f"⚠️  Tests failed with exit code: {result.returncode}")
            print(
                "   The import error may be fixed, but tests are failing for other reasons."
            )
            return False

    except subprocess.TimeoutExpired:
        print("⏱️  Test execution timed out after 30 seconds.")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install: pip install pytest")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def main():
    """Main execution flow."""
    print("=" * 60)
    print("Story 11 Import Fix")
    print("=" * 60)
    print()

    # Change to project root if needed
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"📁 Working directory: {os.getcwd()}")
    print()

    # Step 1: Fix the import
    fixed = fix_stage3_crew_import()

    if not fixed:
        print("\n❌ Fix not applied. Exiting.")
        sys.exit(1)

    # Step 2: Verify with tests
    tests_passed = verify_fix()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Import fix applied: {fixed}")
    print(
        f"{'✅' if tests_passed else '⚠️ '} Tests executed: {tests_passed or 'Failed/Incomplete'}"
    )
    print()

    if fixed and tests_passed:
        print("🎉 Story 11 import error successfully fixed!")
        print("   The ImportError should now be resolved.")
        sys.exit(0)
    elif fixed:
        print("⚠️  Import error fixed, but tests need attention.")
        print("   Check test output above for details.")
        sys.exit(0)
    else:
        print("❌ Unable to complete fix. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
