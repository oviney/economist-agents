#!/usr/bin/env python3
"""
Sprint Badge Generator

Generates shields.io JSON endpoint for Sprint badge from sprint_tracker.json.

Usage:
    python3 scripts/generate_sprint_badge.py
    python3 scripts/generate_sprint_badge.py --output sprint_badge.json
"""

import json
import sys
from pathlib import Path


def generate_sprint_badge(output_path: Path = None) -> dict:
    """Generate sprint badge JSON from sprint_tracker.json"""
    repo_root = Path(__file__).parent.parent
    tracker_path = repo_root / "skills" / "sprint_tracker.json"

    try:
        with open(tracker_path) as f:
            tracker_data = json.load(f)

        current_sprint = tracker_data.get("current_sprint")

        if not current_sprint:
            print("❌ Error: current_sprint not found in sprint_tracker.json")
            return None

        badge_data = {
            "schemaVersion": 1,
            "label": "Sprint",
            "message": str(current_sprint),
            "color": "blue",
        }

        if output_path:
            output_path = repo_root / output_path
            with open(output_path, "w") as f:
                json.dump(badge_data, f, indent=2)
                f.write("\n")
            print(f"✅ Sprint badge generated: {output_path}")
            print(f"   Sprint: {current_sprint}")

        return badge_data

    except FileNotFoundError:
        print(f"❌ Error: {tracker_path} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing sprint_tracker.json: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Sprint badge JSON")
    parser.add_argument(
        "--output",
        default="sprint_badge.json",
        help="Output file path (default: sprint_badge.json)",
    )

    args = parser.parse_args()

    result = generate_sprint_badge(args.output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
