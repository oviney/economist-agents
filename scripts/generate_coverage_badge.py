#!/usr/bin/env python3
"""
Coverage Badge Generator

Generates shields.io JSON endpoint for Coverage badge from pytest-cov.

Usage:
    python3 scripts/generate_coverage_badge.py
    python3 scripts/generate_coverage_badge.py --output coverage_badge.json
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def get_coverage_percentage() -> int:
    """Get coverage percentage from pytest-cov"""
    repo_root = Path(__file__).parent.parent

    try:
        # Run pytest with coverage
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--cov=scripts", "--cov-report=term"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse coverage percentage from output
        # Look for "TOTAL" line with percentage
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", result.stdout)
        if match:
            return int(match.group(1))

        print("⚠️  Could not parse coverage percentage")
        return None
    except subprocess.TimeoutExpired:
        print("⚠️  Coverage check timed out")
        return None
    except Exception as e:
        print(f"⚠️  Error getting coverage: {e}")
        return None


def generate_coverage_badge(output_path: Path = None) -> dict:
    """Generate coverage badge JSON from pytest-cov"""
    repo_root = Path(__file__).parent.parent

    coverage = get_coverage_percentage()

    if coverage is None:
        print("❌ Error: Could not determine coverage percentage")
        # Use a placeholder for now
        coverage = 0
        print(
            "ℹ️  Using 0% as placeholder - run pytest with --cov to get actual coverage"
        )

    # Determine color based on coverage
    if coverage >= 80:
        color = "brightgreen"
    elif coverage >= 50:
        color = "yellow"
    else:
        color = "orange"

    badge_data = {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{coverage}%",
        "color": color,
    }

    if output_path:
        output_path = repo_root / output_path
        with open(output_path, "w") as f:
            json.dump(badge_data, f, indent=2)
            f.write("\n")
        print(f"✅ Coverage badge generated: {output_path}")
        print(f"   Coverage: {coverage}% ({color})")

    return badge_data


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Coverage badge JSON")
    parser.add_argument(
        "--output",
        default="coverage_badge.json",
        help="Output file path (default: coverage_badge.json)",
    )

    args = parser.parse_args()

    result = generate_coverage_badge(args.output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
