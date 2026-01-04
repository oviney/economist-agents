#!/usr/bin/env python3
"""
Story 10 Fix: Relocate Stage3Crew to Proper Directory Structure

Goal: Fix the directory structure by moving agents/stage3_crew.py to src/crews/stage3_crew.py
      and updating all imports to match the new location.

Usage:
    ./run.sh scripts/run_story10_fix.py

This is a simple refactoring script (no CrewAI required).
"""

import subprocess
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

OLD_PATH = Path("agents/stage3_crew.py")
NEW_PATH = Path("src/crews/stage3_crew.py")
TEST_FILE = Path("tests/reproduce_stage3.py")
OLD_IMPORT = "from agents.stage3_crew import Stage3Crew"
NEW_IMPORT = "from src.crews.stage3_crew import Stage3Crew"


# ============================================================================
# TASK FUNCTIONS
# ============================================================================


def task1_architecture_check():
    """Task 1: Verify agents/stage3_crew.py exists and read its content."""
    print("\n" + "=" * 80)
    print("TASK 1: Architecture Check")
    print("=" * 80)

    if not OLD_PATH.exists():
        print(f"\n❌ ERROR: {OLD_PATH} does not exist!")
        return None

    content = OLD_PATH.read_text()
    lines = content.split("\n")

    print(f"\n✓ File exists: {OLD_PATH}")
    print(f"✓ File size: {len(content)} bytes")
    print(f"✓ Line count: {len(lines)}")
    print("\nFirst 10 lines:")
    print("---")
    for i, line in enumerate(lines[:10], 1):
        print(f"{i:2}: {line}")
    print("---")

    if "Stage3Crew" in content:
        print("\n✓ Stage3Crew class confirmed present")
    else:
        print("\n⚠️  WARNING: Stage3Crew class not found in file")

    return content


def task2_relocation(content):
    """Task 2: Move the Stage3Crew file to its correct location."""
    print("\n" + "=" * 80)
    print("TASK 2: File Relocation")
    print("=" * 80)

    # Ensure target directory exists
    NEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Directory created/verified: {NEW_PATH.parent}")

    # Write content to new location
    NEW_PATH.write_text(content)
    print(f"✓ File written: {NEW_PATH}")

    # Verify
    if NEW_PATH.exists():
        new_content = NEW_PATH.read_text()
        if new_content == content:
            print(f"✓ Content verified: matches original ({len(content)} bytes)")
        else:
            print("⚠️  WARNING: Content mismatch!")
            return False
    else:
        print(f"❌ ERROR: Failed to create {NEW_PATH}")
        return False

    return True


def task3_import_fix():
    """Task 3: Update the import statement in the test file."""
    print("\n" + "=" * 80)
    print("TASK 3: Update Test Imports")
    print("=" * 80)

    if not TEST_FILE.exists():
        print(f"\n❌ ERROR: {TEST_FILE} does not exist!")
        return False

    content = TEST_FILE.read_text()
    print(f"\n✓ Read test file: {TEST_FILE}")

    if OLD_IMPORT not in content:
        print("⚠️  WARNING: Old import not found in test file")
        print(f"   Looking for: {OLD_IMPORT}")
        return False

    # Replace import
    new_content = content.replace(OLD_IMPORT, NEW_IMPORT)
    TEST_FILE.write_text(new_content)

    print("✓ Import updated:")
    print(f"  FROM: {OLD_IMPORT}")
    print(f"  TO:   {NEW_IMPORT}")

    # Verify
    verify_content = TEST_FILE.read_text()
    if NEW_IMPORT in verify_content and OLD_IMPORT not in verify_content:
        print("✓ Import change verified")
        return True
    else:
        print("❌ ERROR: Import update failed verification")
        return False


def task4_verification():
    """Task 4: Run pytest to confirm the fix works."""
    print("\n" + "=" * 80)
    print("TASK 4: Build Verification")
    print("=" * 80)

    print(f"\n🧪 Running: pytest {TEST_FILE} -v\n")

    try:
        result = subprocess.run(
            ["pytest", str(TEST_FILE), "-v"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        if result.returncode == 0:
            print("\n✅ SUCCESS: All tests passed!")
            return True
        else:
            print(f"\n⚠️  TESTS FAILED (exit code {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("\n⏱️  Test execution timed out")
        return False
    except FileNotFoundError:
        print("\n⚠️  pytest not found. Please install: pip install pytest")
        print(f"   Or run manually: pytest {TEST_FILE} -v")
        return False
    except Exception as e:
        print(f"\n⚠️  Could not run pytest: {e}")
        print(f"   Please run manually: pytest {TEST_FILE} -v")
        return False


def cleanup_old_file():
    """Delete the old file after successful relocation."""
    print("\n" + "=" * 80)
    print("POST-EXECUTION CLEANUP")
    print("=" * 80)

    if OLD_PATH.exists() and NEW_PATH.exists():
        print(f"\n✓ New file exists: {NEW_PATH}")
        print(f"✓ Old file exists: {OLD_PATH}")
        print(f"\n🗑️  Removing old file: {OLD_PATH}")
        try:
            OLD_PATH.unlink()
            print(f"✓ Successfully deleted {OLD_PATH}")
            return True
        except Exception as e:
            print(f"⚠️  Could not delete {OLD_PATH}: {e}")
            print("   Please delete manually")
            return False
    else:
        print("\n⚠️  Cleanup skipped (files not in expected state)")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Execute the directory structure fix."""

    print("\n" + "=" * 80)
    print("STORY 10 FIX: Directory Structure Relocation")
    print("=" * 80)
    print(f"\nGoal: Move {OLD_PATH} → {NEW_PATH}")
    print(f"      Update imports in {TEST_FILE}")

    # Task 1: Check
    content = task1_architecture_check()
    if content is None:
        sys.exit(1)

    # Task 2: Relocate
    if not task2_relocation(content):
        sys.exit(1)

    # Task 3: Fix imports
    if not task3_import_fix():
        sys.exit(1)

    # Task 4: Verify
    tests_passed = task4_verification()

    # Cleanup (only if tests passed)
    if tests_passed:
        cleanup_old_file()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✓ Relocated: {OLD_PATH} → {NEW_PATH}")
    print(f"✓ Updated: {TEST_FILE} import path")

    if tests_passed:
        print("✓ Verified: Tests passing")
        print("✓ Cleanup: Old file removed")
        print("\n✅ Story 10 fix complete!\n")
        sys.exit(0)
    else:
        print("⚠️  Tests failed - review output above")
        print("⚠️  Old file NOT removed (kept for safety)")
        print("\n❌ Story 10 fix incomplete\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
