#!/usr/bin/env python3
"""
Badge Validation

Validates README badge accuracy against live data sources.

Usage:
    python3 scripts/validate_badges.py
    python3 scripts/validate_badges.py --strict  # Exit with error if validation fails
"""

import json
import re
import subprocess
import sys
from pathlib import Path


class BadgeValidator:
    """Validates README badges against live data sources"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.repo_root = Path(__file__).parent.parent
        self.readme_path = self.repo_root / "README.md"
        self.quality_json_path = self.repo_root / "quality_score.json"
        self.sprint_tracker_path = self.repo_root / "skills" / "sprint_tracker.json"
        self.issues: list[str] = []

    def validate_quality_badge(self) -> bool:
        """Validate quality score badge"""
        try:
            # Get actual quality score
            result = subprocess.run(
                [sys.executable, "scripts/quality_dashboard.py"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            match = re.search(r"\*\*Quality Score\*\*:\s*(\d+)/100", result.stdout)
            if not match:
                self.issues.append("Could not parse quality score from dashboard")
                return False

            actual_score = int(match.group(1))

            # Check quality_score.json
            with open(self.quality_json_path) as f:
                quality_json = json.load(f)
                json_score = int(quality_json["message"].split("/")[0])

            if actual_score != json_score:
                self.issues.append(
                    f"Quality score mismatch: quality_score.json={json_score}, actual={actual_score}"
                )
                return False

            print(f"✅ Quality badge: {json_score}/100 (accurate)")
            return True

        except Exception as e:
            self.issues.append(f"Quality badge validation error: {e}")
            return False

    def validate_tests_badge(self) -> bool:
        """Validate tests count badge"""
        try:
            # Count actual tests
            result = subprocess.run(
                ["bash", "-c", "grep -rh '^def test_' tests/*.py 2>/dev/null | wc -l"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
            actual_count = int(result.stdout.strip())

            # Check if tests_badge.json exists and is accurate
            tests_badge_path = self.repo_root / "tests_badge.json"
            if tests_badge_path.exists():
                with open(tests_badge_path) as f:
                    badge_data = json.load(f)
                    badge_message = badge_data["message"]
                    badge_count = int(badge_message.split()[0])

                if actual_count != badge_count:
                    self.issues.append(
                        f"Tests count mismatch: tests_badge.json={badge_count}, actual={actual_count}"
                    )
                    return False

                print(f"✅ Tests badge: {badge_count} passing (accurate)")
                return True
            else:
                self.issues.append("tests_badge.json not found")
                return False

        except Exception as e:
            self.issues.append(f"Tests badge validation error: {e}")
            return False

    def validate_sprint_badge(self) -> bool:
        """Validate sprint number badge"""
        try:
            # Get actual sprint
            with open(self.sprint_tracker_path) as f:
                tracker_data = json.load(f)
                actual_sprint = tracker_data.get("current_sprint")

            # Check if sprint_badge.json exists and is accurate
            sprint_badge_path = self.repo_root / "sprint_badge.json"
            if sprint_badge_path.exists():
                with open(sprint_badge_path) as f:
                    badge_data = json.load(f)
                    badge_sprint = int(badge_data["message"])

                if actual_sprint != badge_sprint:
                    self.issues.append(
                        f"Sprint number mismatch: sprint_badge.json={badge_sprint}, actual={actual_sprint}"
                    )
                    return False

                print(f"✅ Sprint badge: {badge_sprint} (accurate)")
                return True
            else:
                self.issues.append("sprint_badge.json not found")
                return False

        except Exception as e:
            self.issues.append(f"Sprint badge validation error: {e}")
            return False

    def validate_badge_urls(self) -> bool:
        """Validate all badge URLs are accessible"""
        try:
            with open(self.readme_path) as f:
                readme = f.read()

            # Extract all badge URLs
            badge_urls = re.findall(r"!\[[^\]]*\]\((https?://[^\)]+)\)", readme)

            all_valid = True
            for url in badge_urls:
                # Basic URL format validation
                if not url.startswith(("https://img.shields.io", "https://github.com")):
                    print(f"⚠️  Unusual badge URL: {url}")

                # Check if endpoint badges have valid JSON files
                if "endpoint?url=" in url:
                    endpoint_match = re.search(r"url=([^)]+)", url)
                    if endpoint_match:
                        endpoint_url = endpoint_match.group(1)
                        # Extract JSON filename from GitHub raw URL
                        json_match = re.search(r"/([^/]+\.json)$", endpoint_url)
                        if json_match:
                            json_file = json_match.group(1)
                            json_path = self.repo_root / json_file
                            if not json_path.exists():
                                self.issues.append(
                                    f"Badge endpoint file missing: {json_file}"
                                )
                                all_valid = False
                            else:
                                print(f"✅ Badge endpoint exists: {json_file}")

            return all_valid

        except Exception as e:
            self.issues.append(f"Badge URL validation error: {e}")
            return False

    def validate_all(self) -> dict[str, bool]:
        """Run all badge validations"""
        print("\n🔍 Badge Validation Report")
        print("=" * 60)

        results = {
            "quality": self.validate_quality_badge(),
            "tests": self.validate_tests_badge(),
            "sprint": self.validate_sprint_badge(),
            "urls": self.validate_badge_urls(),
        }

        print("=" * 60)

        if all(results.values()):
            print("\n✅ All badge validations passed!")
            return {"valid": True, "results": results, "issues": []}
        else:
            print("\n❌ Badge validation failed:")
            for issue in self.issues:
                print(f"  • {issue}")
            return {"valid": False, "results": results, "issues": self.issues}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate README badges")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if validation fails",
    )

    args = parser.parse_args()

    validator = BadgeValidator(strict=args.strict)
    result = validator.validate_all()

    if args.strict and not result["valid"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
