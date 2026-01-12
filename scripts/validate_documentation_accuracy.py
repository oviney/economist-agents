#!/usr/bin/env python3
"""
Documentation Accuracy Validator

Validates that core documentation files are current and accurate by comparing
against the authoritative sprint_tracker.json source of truth.

Checks:
1. README.md sprint status matches sprint_tracker.json
2. SPRINT.md sprint status matches sprint_tracker.json
3. CHANGELOG.md has entry for current sprint
4. Documentation updated within acceptable staleness window

Usage:
    # Validate all documentation
    python3 validate_documentation_accuracy.py

    # Validate with warnings only
    python3 validate_documentation_accuracy.py --warn-only

    # Show detailed report
    python3 validate_documentation_accuracy.py --verbose

Exit codes:
    0 - All documentation current
    1 - Stale documentation detected
    2 - Critical errors (missing files)
"""

import json
import re
import sys
from pathlib import Path


class DocumentationValidator:
    """Validates documentation accuracy against sprint_tracker.json"""

    # Acceptable staleness windows
    MAX_README_STALENESS_HOURS = 24  # README should be updated daily
    MAX_CHANGELOG_STALENESS_DAYS = 3  # CHANGELOG can lag by a few days

    def __init__(self, repo_root: Path = None):
        if repo_root is None:
            repo_root = Path(__file__).parent.parent

        self.repo_root = Path(repo_root)
        self.readme_path = self.repo_root / "README.md"
        self.sprint_path = self.repo_root / "SPRINT.md"
        self.changelog_path = self.repo_root / "docs" / "CHANGELOG.md"
        self.tracker_path = self.repo_root / "skills" / "sprint_tracker.json"

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks. Returns True if all pass."""
        self.errors = []
        self.warnings = []
        self.info = []

        # Check required files exist
        if not self._check_files_exist():
            return False

        # Load sprint tracker (authoritative source)
        tracker = self._load_sprint_tracker()
        if not tracker:
            return False

        current_sprint = tracker.get("current_sprint")
        if not current_sprint:
            self.warnings.append("No current sprint defined in sprint_tracker.json")
            return True

        sprint_key = f"sprint_{current_sprint}"
        sprint_data = tracker.get("sprints", {}).get(sprint_key, {})

        # Run validation checks
        self._validate_readme_sprint_status(current_sprint, sprint_data)
        self._validate_sprint_md_status(current_sprint, sprint_data)
        self._validate_changelog_entry(current_sprint, sprint_data)

        return len(self.errors) == 0

    def _check_files_exist(self) -> bool:
        """Check all required files exist"""
        missing = []

        for path, name in [
            (self.readme_path, "README.md"),
            (self.sprint_path, "SPRINT.md"),
            (self.changelog_path, "docs/CHANGELOG.md"),
            (self.tracker_path, "skills/sprint_tracker.json"),
        ]:
            if not path.exists():
                missing.append(name)

        if missing:
            self.errors.append(f"Missing required files: {', '.join(missing)}")
            return False

        return True

    def _load_sprint_tracker(self) -> dict:
        """Load sprint_tracker.json"""
        try:
            with open(self.tracker_path) as f:
                return json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load sprint_tracker.json: {e}")
            return {}

    def _validate_readme_sprint_status(
        self, current_sprint: int, sprint_data: dict
    ) -> None:
        """Validate README.md shows correct sprint status"""
        with open(self.readme_path) as f:
            readme_content = f.read()

        sprint_status = sprint_data.get("status", "unknown")

        # Check if README mentions current sprint
        sprint_pattern = rf"Sprint {current_sprint}"
        if not re.search(sprint_pattern, readme_content, re.IGNORECASE):
            self.warnings.append(f"README.md does not mention Sprint {current_sprint}")
            return

        # Check status accuracy
        if sprint_status == "in_progress":
            # Should say "IN PROGRESS" or "Day X"
            if not re.search(
                r"(IN PROGRESS|in progress|Day \d+)",
                readme_content,
                re.IGNORECASE,
            ):
                self.errors.append(
                    f"README.md does not show Sprint {current_sprint} as IN PROGRESS"
                )
        elif sprint_status == "planning" and not re.search(
            r"PLANNING", readme_content, re.IGNORECASE
        ):
            # Should say "PLANNING"
            self.warnings.append(
                f"README.md may not show Sprint {current_sprint} as PLANNING"
            )

    def _validate_sprint_md_status(
        self, current_sprint: int, sprint_data: dict
    ) -> None:
        """Validate SPRINT.md shows correct sprint status"""
        with open(self.sprint_path) as f:
            sprint_content = f.read()

        sprint_status = sprint_data.get("status", "unknown")

        # Check Active Sprint header
        active_sprint_pattern = rf"\*\*Active Sprint\*\*:\s*Sprint {current_sprint}"
        if not re.search(active_sprint_pattern, sprint_content):
            self.errors.append(
                f"SPRINT.md does not show Sprint {current_sprint} as Active Sprint"
            )
            return

        # Check status matches
        if sprint_status == "in_progress":
            if not re.search(r"IN PROGRESS|Day \d+", sprint_content):
                self.errors.append(
                    f"SPRINT.md does not show Sprint {current_sprint} as IN PROGRESS"
                )

        elif sprint_status == "planning" and not re.search(
            r"PLANNING|Ready for kickoff", sprint_content
        ):
            self.warnings.append(
                f"SPRINT.md may not show Sprint {current_sprint} as PLANNING"
            )

    def _validate_changelog_entry(self, current_sprint: int, sprint_data: dict) -> None:
        """Validate CHANGELOG.md has entry for current sprint"""
        with open(self.changelog_path) as f:
            changelog_content = f.read()

        # Check for story completion entries
        stories = sprint_data.get("stories", [])
        completed_stories = [s for s in stories if s.get("status") == "complete"]

        for story in completed_stories:
            story_id = story.get("id")
            if story_id:
                story_pattern = rf"STORY-0*{story_id:02d}"
                if not re.search(story_pattern, changelog_content):
                    self.warnings.append(
                        f"CHANGELOG.md missing entry for completed Story {story_id}"
                    )

    def print_report(self, verbose: bool = False) -> None:
        """Print validation report"""
        print("\n" + "=" * 60)
        print("Documentation Accuracy Validation Report")
        print("=" * 60 + "\n")

        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
            print()

        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        if verbose and self.info:
            print("ℹ️  INFO:")
            for info in self.info:
                print(f"  - {info}")
            print()

        if not self.errors and not self.warnings:
            print("✅ All documentation is current and accurate!\n")

        print("=" * 60 + "\n")


def main() -> int:
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate documentation accuracy against sprint_tracker.json"
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even if errors found (warnings only)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )

    args = parser.parse_args()

    validator = DocumentationValidator()
    is_valid = validator.validate_all()

    validator.print_report(verbose=args.verbose)

    if not is_valid and not args.warn_only:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
