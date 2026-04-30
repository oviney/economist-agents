#!/usr/bin/env python3
"""Fix Typo Script - Fix package name typo in src/crews/stage3_crew.py

Goal: Replace all instances of 'crew_ai' with 'crewai' in imports.

Usage:
    python3 scripts/fix_typo.py
"""

import sys
from pathlib import Path


def fix_typo():
    """Fix the package name typo in src/crews/stage3_crew.py"""
    # Define file path
    file_path = Path("src/crews/stage3_crew.py")

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    # Read the file
    print(f"📖 Reading {file_path}...")
    content = file_path.read_text()

    # Track changes
    changes_made = 0

    # Fix 1: Replace 'from crew_ai' with 'from crewai'
    if "from crew_ai" in content:
        count = content.count("from crew_ai")
        content = content.replace("from crew_ai", "from crewai")
        print(f"✅ Fixed {count} instance(s) of 'from crew_ai' → 'from crewai'")
        changes_made += count

    # Fix 2: Replace 'import crew_ai' with 'import crewai'
    if "import crew_ai" in content:
        count = content.count("import crew_ai")
        content = content.replace("import crew_ai", "import crewai")
        print(f"✅ Fixed {count} instance(s) of 'import crew_ai' → 'import crewai'")
        changes_made += count

    # Save if changes were made
    if changes_made > 0:
        print(f"\n💾 Saving changes to {file_path}...")
        file_path.write_text(content)
        print(f"✅ Successfully fixed {changes_made} typo(s) in {file_path}")
        return True
    print(f"ℹ️  No typos found in {file_path}")
    return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("Fix Typo Script - src/crews/stage3_crew.py")
    print("=" * 60)
    print()

    # Fix the typo
    fixed = fix_typo()

    if fixed:
        print()
        print("=" * 60)
        print("🎉 Typo fix complete!")
        print("=" * 60)
        print()
        print("Next step: Run verification test")
        print("  $ pytest tests/reproduce_stage3.py -v")
        sys.exit(0)
    else:
        print()
        print("No changes needed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
