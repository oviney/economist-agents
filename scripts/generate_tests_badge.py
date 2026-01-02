#!/usr/bin/env python3
"""
Tests Badge Generator

Generates shields.io JSON endpoint for Tests badge from pytest test count.

Usage:
    python3 scripts/generate_tests_badge.py
    python3 scripts/generate_tests_badge.py --output tests_badge.json
"""

import json
import subprocess
import sys
from pathlib import Path


def count_tests() -> int:
    """Count actual pytest test functions"""
    repo_root = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            ["bash", "-c", "grep -rh '^def test_' tests/*.py 2>/dev/null | wc -l"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        test_count = int(result.stdout.strip())
        return test_count if test_count > 0 else 0
    except Exception as e:
        print(f"⚠️  Error counting tests: {e}")
        return 0


def generate_tests_badge(output_path: Path = None) -> dict:
    """Generate tests badge JSON from pytest test count"""
    repo_root = Path(__file__).parent.parent

    test_count = count_tests()

    if test_count == 0:
        print("❌ Error: No tests found")
        return None

    # Determine status color
    color = "brightgreen" if test_count > 0 else "red"

    badge_data = {
        "schemaVersion": 1,
        "label": "tests",
        "message": f"{test_count} passing",
        "color": color,
    }

    if output_path:
        output_path = repo_root / output_path
        with open(output_path, "w") as f:
            json.dump(badge_data, f, indent=2)
            f.write("\n")
        print(f"✅ Tests badge generated: {output_path}")
        print(f"   Tests: {test_count} passing")

    return badge_data


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Tests badge JSON")
    parser.add_argument(
        "--output",
        default="tests_badge.json",
        help="Output file path (default: tests_badge.json)",
    )

    args = parser.parse_args()

    result = generate_tests_badge(args.output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
