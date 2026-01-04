#!/usr/bin/env python3
"""
GitHub Issue Validator - Prevents Duplicate Issue Creation

Validates against defect_tracker.json before creating GitHub issues.
Prevents duplicate issues by checking existing bug entries.

Usage:
    # Check if bug already has GitHub issue
    python3 scripts/github_issue_validator.py --bug BUG-026

    # Validate before creation (blocks if duplicate)
    python3 scripts/github_issue_validator.py --validate BUG-026 --title "Bug title"

    # List all bugs without GitHub issues
    python3 scripts/github_issue_validator.py --list-missing
"""

import argparse
import json
import sys
from pathlib import Path


class GitHubIssueValidator:
    """Validates GitHub issue creation against defect tracker"""

    def __init__(self, tracker_file: str = None):
        if tracker_file is None:
            script_dir = Path(__file__).parent.parent
            tracker_file = script_dir / "skills" / "defect_tracker.json"

        self.tracker_file = Path(tracker_file)
        self.tracker = self._load_tracker()

    def _load_tracker(self) -> dict:
        """Load defect tracker"""
        if not self.tracker_file.exists():
            return {"bugs": []}

        with open(self.tracker_file) as f:
            return json.load(f)

    def check_existing_issue(self, bug_id: str) -> tuple[bool, int | None]:
        """
        Check if bug already has GitHub issue.

        Returns:
            (bug_exists, github_issue_number)
        """
        bug = self._find_bug(bug_id)

        if not bug:
            return False, None

        github_issue = bug.get("github_issue")
        return True, github_issue

    def _find_bug(self, bug_id: str) -> dict | None:
        """Find bug in tracker"""
        for bug in self.tracker.get("bugs", []):
            if bug["id"] == bug_id:
                return bug
        return None

    def validate_before_create(
        self, bug_id: str, title: str = None
    ) -> tuple[bool, str]:
        """
        Validate before creating GitHub issue.

        Returns:
            (can_create, message)
        """
        bug_exists, github_issue = self.check_existing_issue(bug_id)

        if not bug_exists:
            return True, f"✅ OK to create: {bug_id} not in tracker (will need to add)"

        if github_issue is not None:
            return False, (
                f"❌ BLOCKED: {bug_id} already has GitHub issue #{github_issue}\n"
                f"   View: gh issue view {github_issue}\n"
                f"   Reuse existing issue instead of creating duplicate"
            )

        return True, f"✅ OK to create: {bug_id} exists but has no GitHub issue yet"

    def list_bugs_without_issues(self) -> list[dict]:
        """List all bugs that don't have GitHub issues"""
        bugs_missing_issues = []

        for bug in self.tracker.get("bugs", []):
            if bug.get("github_issue") is None and bug.get("status") == "open":
                bugs_missing_issues.append(
                    {
                        "id": bug["id"],
                        "severity": bug["severity"],
                        "description": bug["description"],
                        "discovered_in": bug["discovered_in"],
                    }
                )

        return bugs_missing_issues

    def get_next_bug_id(self) -> str:
        """Get next available BUG-XXX ID"""
        bug_ids = [bug["id"] for bug in self.tracker.get("bugs", [])]

        if not bug_ids:
            return "BUG-001"

        # Extract numbers
        numbers = []
        for bug_id in bug_ids:
            if bug_id.startswith("BUG-"):
                try:
                    num = int(bug_id.split("-")[1])
                    numbers.append(num)
                except ValueError:
                    continue

        if not numbers:
            return "BUG-001"

        next_num = max(numbers) + 1
        return f"BUG-{next_num:03d}"


def main():
    parser = argparse.ArgumentParser(
        description="Validate GitHub issue creation against defect tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check if bug has issue
  python3 scripts/github_issue_validator.py --bug BUG-026

  # Validate before creation
  python3 scripts/github_issue_validator.py --validate BUG-026 --title "Command injection"

  # List bugs missing issues
  python3 scripts/github_issue_validator.py --list-missing

  # Get next bug ID
  python3 scripts/github_issue_validator.py --next-id
        """,
    )

    parser.add_argument("--bug", help="Check if specific bug has GitHub issue")
    parser.add_argument(
        "--validate", help="Validate before creating issue (blocks if duplicate)"
    )
    parser.add_argument("--title", help="Issue title for validation")
    parser.add_argument(
        "--list-missing",
        action="store_true",
        help="List all bugs without GitHub issues",
    )
    parser.add_argument(
        "--next-id", action="store_true", help="Get next available BUG-XXX ID"
    )

    args = parser.parse_args()

    validator = GitHubIssueValidator()

    if args.bug:
        bug_exists, github_issue = validator.check_existing_issue(args.bug)

        if not bug_exists:
            print(f"ℹ️  {args.bug} not found in defect tracker")
            sys.exit(0)

        if github_issue is not None:
            print(f"⚠️  {args.bug} already has GitHub issue #{github_issue}")
            print(f"   View: gh issue view {github_issue}")
            sys.exit(1)
        else:
            print(f"✅ {args.bug} exists but has no GitHub issue")
            sys.exit(0)

    elif args.validate:
        can_create, message = validator.validate_before_create(
            args.validate, args.title
        )

        print(message)

        if not can_create:
            sys.exit(1)
        else:
            sys.exit(0)

    elif args.list_missing:
        bugs = validator.list_bugs_without_issues()

        if not bugs:
            print("✅ All open bugs have GitHub issues")
            sys.exit(0)

        print(f"\n📋 {len(bugs)} open bugs without GitHub issues:\n")
        for bug in bugs:
            print(f"  {bug['id']} ({bug['severity'].upper()})")
            print(f"    {bug['description']}")
            print(f"    Discovered: {bug['discovered_in']}\n")

        sys.exit(0)

    elif args.next_id:
        next_id = validator.get_next_bug_id()
        print(f"Next bug ID: {next_id}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
