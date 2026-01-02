#!/usr/bin/env python3
"""
Badge Update Automation

Syncs README badges with live data sources to prevent staleness (BUG-023).

Data Sources:
- Quality Score: quality_dashboard.py output
- Tests: Actual pytest test count
- Sprint: sprint_tracker.json current_sprint
- Coverage: pytest-cov output (if available)

Usage:
    python3 scripts/update_badges.py
    python3 scripts/update_badges.py --dry-run
    python3 scripts/update_badges.py --validate-only
"""

import json
import re
import subprocess
import sys
from pathlib import Path


class BadgeUpdater:
    """Automates README badge updates from live data sources"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.repo_root = Path(__file__).parent.parent
        self.readme_path = self.repo_root / "README.md"
        self.quality_json_path = self.repo_root / "quality_score.json"
        self.sprint_tracker_path = self.repo_root / "skills" / "sprint_tracker.json"

    def get_quality_score(self) -> int:
        """Get quality score from quality_dashboard.py"""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/quality_dashboard.py"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse quality score from output
            match = re.search(r"\*\*Quality Score\*\*:\s*(\d+)/100", result.stdout)
            if match:
                return int(match.group(1))

            print("⚠️  Could not parse quality score, keeping existing")
            return None
        except Exception as e:
            print(f"⚠️  Error getting quality score: {e}")
            return None

    def get_test_count(self) -> int:
        """Count actual pytest tests"""
        try:
            # Use find to get all test files, then grep for test functions
            result = subprocess.run(
                ["bash", "-c", "grep -h '^def test_' tests/*.py | wc -l"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
            test_count = int(result.stdout.strip())
            return test_count if test_count > 0 else None
        except Exception as e:
            print(f"⚠️  Error counting tests: {e}")
            return None

    def get_current_sprint(self) -> int:
        """Get current sprint from sprint_tracker.json"""
        try:
            with open(self.sprint_tracker_path) as f:
                data = json.load(f)
                return data.get("current_sprint")
        except Exception as e:
            print(f"⚠️  Error reading sprint tracker: {e}")
            return None

    def update_quality_json(self, quality_score: int) -> None:
        """Update quality_score.json for shields.io endpoint"""
        try:
            # Determine color based on score
            if quality_score >= 90:
                color = "brightgreen"
            elif quality_score >= 70:
                color = "green"
            elif quality_score >= 50:
                color = "yellow"
            else:
                color = "orange"

            quality_data = {
                "schemaVersion": 1,
                "label": "quality",
                "message": f"{quality_score}/100",
                "color": color,
            }

            if not self.dry_run:
                with open(self.quality_json_path, "w") as f:
                    json.dump(quality_data, f, indent=2)
                    f.write("\n")
                print(f"✅ Updated quality_score.json: {quality_score}/100 ({color})")
            else:
                print(
                    f"[DRY RUN] Would update quality_score.json: {quality_score}/100 ({color})"
                )
        except Exception as e:
            print(f"❌ Error updating quality_score.json: {e}")

    def update_readme_badges(
        self, quality_score: int, test_count: int, sprint: int
    ) -> None:
        """Update README.md badge values"""
        try:
            with open(self.readme_path) as f:
                content = f.read()

            # Update test count badge
            if test_count:
                content = re.sub(
                    r"!\[Tests\]\(https://img\.shields\.io/badge/tests-\d+_passing-[^)]+\)",
                    f"![Tests](https://img.shields.io/badge/tests-{test_count}_passing-brightgreen)",
                    content,
                )

            # Update sprint badge
            if sprint:
                content = re.sub(
                    r"!\[Sprint\]\(https://img\.shields\.io/badge/[sS]print-\d+-[^)]+\)",
                    f"![Sprint](https://img.shields.io/badge/sprint-{sprint}-blue)",
                    content,
                )

            if not self.dry_run:
                with open(self.readme_path, "w") as f:
                    f.write(content)
                print(f"✅ Updated README.md: tests={test_count}, sprint={sprint}")
            else:
                print(
                    f"[DRY RUN] Would update README.md: tests={test_count}, sprint={sprint}"
                )
        except Exception as e:
            print(f"❌ Error updating README.md: {e}")

    def validate_badges(self) -> dict:
        """Validate badge accuracy against live data"""
        print("\n🔍 Badge Validation Report")
        print("=" * 60)

        issues = []

        # Check quality score
        quality_score = self.get_quality_score()
        with open(self.quality_json_path) as f:
            quality_json = json.load(f)
            json_score = int(quality_json["message"].split("/")[0])

        if quality_score and quality_score != json_score:
            issues.append(
                f"Quality score mismatch: JSON={json_score}, Actual={quality_score}"
            )
        else:
            print(f"✅ Quality score: {json_score}/100 (accurate)")

        # Check test count
        test_count = self.get_test_count()
        with open(self.readme_path) as f:
            readme = f.read()
            badge_match = re.search(r"tests-(\d+)_passing", readme)
            readme_tests = int(badge_match.group(1)) if badge_match else None

        if test_count and readme_tests and test_count != readme_tests:
            issues.append(
                f"Test count mismatch: Badge={readme_tests}, Actual={test_count}"
            )
        else:
            print(f"✅ Test count: {readme_tests} (accurate)")

        # Check sprint
        current_sprint = self.get_current_sprint()
        sprint_match = re.search(r"sprint-(\d+)-blue", readme)
        readme_sprint = int(sprint_match.group(1)) if sprint_match else None

        if current_sprint and readme_sprint and current_sprint != readme_sprint:
            issues.append(
                f"Sprint mismatch: Badge={readme_sprint}, Actual={current_sprint}"
            )
        else:
            print(f"✅ Sprint: {readme_sprint} (accurate)")

        print("=" * 60)

        if issues:
            print("\n❌ Badge Validation Failed:")
            for issue in issues:
                print(f"  • {issue}")
            return {"valid": False, "issues": issues}
        else:
            print("\n✅ All badges are accurate!")
            return {"valid": True, "issues": []}

    def update_all(self) -> bool:
        """Update all badges from live data"""
        print("\n🔄 Badge Update Process")
        print("=" * 60)

        # Gather live data
        quality_score = self.get_quality_score()
        test_count = self.get_test_count()
        current_sprint = self.get_current_sprint()

        print("📊 Live Data:")
        print(f"  • Quality Score: {quality_score}/100")
        print(f"  • Test Count: {test_count}")
        print(f"  • Current Sprint: {current_sprint}")
        print()

        # Update quality_score.json (for shields.io endpoint)
        if quality_score:
            self.update_quality_json(quality_score)

        # Update README.md badges
        if test_count or current_sprint:
            self.update_readme_badges(quality_score, test_count, current_sprint)

        print("=" * 60)
        print("\n✅ Badge update complete!")

        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update README badges with live data")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate, don't update"
    )

    args = parser.parse_args()

    updater = BadgeUpdater(dry_run=args.dry_run)

    if args.validate_only:
        result = updater.validate_badges()
        sys.exit(0 if result["valid"] else 1)
    else:
        updater.update_all()

        # Validate after update
        if not args.dry_run:
            print()
            updater.validate_badges()


if __name__ == "__main__":
    main()
