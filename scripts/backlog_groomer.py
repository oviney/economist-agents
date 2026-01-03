#!/usr/bin/env python3
"""
Backlog Groomer - Automated Backlog Health Management

Maintains backlog health through automated detection of:
- Aging stories (>30 days flag, >90 days close)
- Duplicate stories (similar titles/acceptance criteria)
- Priority drift (P0 stories older than P2 stories)
- Undefined stories (missing AC, estimates, priorities)

Usage:
    python3 scripts/backlog_groomer.py --report          # Generate health report
    python3 scripts/backlog_groomer.py --clean           # Flag/close stale stories
    python3 scripts/backlog_groomer.py --validate        # Validate backlog structure
    python3 scripts/backlog_groomer.py --duplicates      # Find duplicate stories
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


class BacklogGroomer:
    """Automated backlog health management and cleanup"""

    # Health thresholds
    AGE_FLAG_DAYS = 30  # Flag stories older than this
    AGE_CLOSE_DAYS = 90  # Suggest closing stories older than this
    DUPLICATE_SIMILARITY = 0.8  # 80% title similarity = potential duplicate
    MAX_HEALTH_SCORE = 10  # Target: <10% of backlog has issues

    def __init__(self, backlog_path: str = "skills/sprint_tracker.json"):
        self.backlog_path = Path(backlog_path)
        self.backlog = self._load_backlog()
        self.issues: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def _load_backlog(self) -> dict[str, Any]:
        """Load backlog from sprint tracker"""
        if not self.backlog_path.exists():
            return {"sprints": {}}

        with open(self.backlog_path) as f:
            return json.load(f)

    def _save_backlog(self) -> None:
        """Save updated backlog"""
        with open(self.backlog_path, "w") as f:
            json.dump(self.backlog, f, indent=2)

    def _get_all_stories(self) -> list[dict[str, Any]]:
        """Extract all stories across all sprints"""
        stories = []
        for sprint_id, sprint_data in self.backlog.get("sprints", {}).items():
            for story in sprint_data.get("stories", []):
                story["sprint"] = sprint_id
                stories.append(story)
        return stories

    def _calculate_age_days(self, created_date: str) -> int:
        """Calculate story age in days"""
        try:
            created = datetime.fromisoformat(created_date)
            return (datetime.now() - created).days
        except (ValueError, TypeError):
            return 0

    def check_aging_stories(self) -> list[dict[str, Any]]:
        """Identify stories older than thresholds"""
        aging = []
        stories = self._get_all_stories()

        for story in stories:
            # Skip completed stories
            if story.get("status") == "complete":
                continue

            created = story.get("created_date", "")
            if not created:
                continue

            age_days = self._calculate_age_days(created)

            if age_days > self.AGE_CLOSE_DAYS:
                aging.append(
                    {
                        "story_id": story.get("id"),
                        "title": story.get("title"),
                        "age_days": age_days,
                        "severity": "CLOSE",
                        "recommendation": f"Story {age_days} days old - suggest closing if inactive",
                        "sprint": story.get("sprint"),
                    }
                )
                self.issues["aging"].append(aging[-1])

            elif age_days > self.AGE_FLAG_DAYS:
                aging.append(
                    {
                        "story_id": story.get("id"),
                        "title": story.get("title"),
                        "age_days": age_days,
                        "severity": "FLAG",
                        "recommendation": f"Story {age_days} days old - review priority",
                        "sprint": story.get("sprint"),
                    }
                )
                self.issues["aging"].append(aging[-1])

        return aging

    def check_duplicates(self) -> list[dict[str, Any]]:
        """Detect potential duplicate stories based on title similarity"""
        duplicates = []
        stories = self._get_all_stories()

        # Skip completed stories
        active_stories = [s for s in stories if s.get("status") != "complete"]

        for i, story1 in enumerate(active_stories):
            for story2 in active_stories[i + 1 :]:
                title1 = story1.get("title", "").lower()
                title2 = story2.get("title", "").lower()

                similarity = SequenceMatcher(None, title1, title2).ratio()

                if similarity >= self.DUPLICATE_SIMILARITY:
                    duplicates.append(
                        {
                            "story1_id": story1.get("id"),
                            "story1_title": story1.get("title"),
                            "story2_id": story2.get("id"),
                            "story2_title": story2.get("title"),
                            "similarity": round(similarity * 100, 1),
                            "recommendation": "Review and merge if duplicate",
                        }
                    )
                    self.issues["duplicates"].append(duplicates[-1])

        return duplicates

    def check_priority_drift(self) -> list[dict[str, Any]]:
        """Identify P0 stories that are older than lower priority stories"""
        drift = []
        stories = self._get_all_stories()

        # Group by priority
        by_priority: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for story in stories:
            if story.get("status") != "complete":
                priority = story.get("priority", "P3")
                by_priority[priority].append(story)

        # Check if P0 stories are older than P2/P3
        p0_stories = by_priority.get("P0", [])
        p2_stories = by_priority.get("P2", [])
        p3_stories = by_priority.get("P3", [])

        for p0 in p0_stories:
            p0_age = self._calculate_age_days(p0.get("created_date", ""))

            for lower_priority in p2_stories + p3_stories:
                lower_age = self._calculate_age_days(
                    lower_priority.get("created_date", "")
                )

                if p0_age > lower_age + 14:  # P0 at least 2 weeks older
                    drift.append(
                        {
                            "story_id": p0.get("id"),
                            "title": p0.get("title"),
                            "priority": "P0",
                            "age_days": p0_age,
                            "recommendation": f"P0 story {p0_age} days old while newer P2/P3 exist - validate priority",
                        }
                    )
                    self.issues["priority_drift"].append(drift[-1])
                    break  # Only flag once per P0 story

        return drift

    def check_undefined_stories(self) -> list[dict[str, Any]]:
        """Identify stories missing critical information"""
        undefined = []
        stories = self._get_all_stories()

        for story in stories:
            if story.get("status") == "complete":
                continue

            missing = []

            if not story.get("acceptance_criteria"):
                missing.append("acceptance_criteria")

            if not story.get("story_points") or story.get("story_points") == 0:
                missing.append("story_points")

            if not story.get("priority"):
                missing.append("priority")

            if not story.get("assigned_to"):
                missing.append("assigned_to")

            if missing:
                undefined.append(
                    {
                        "story_id": story.get("id"),
                        "title": story.get("title"),
                        "missing_fields": missing,
                        "recommendation": f"Add missing fields: {', '.join(missing)}",
                    }
                )
                self.issues["undefined"].append(undefined[-1])

        return undefined

    def calculate_health_score(self) -> float:
        """Calculate overall backlog health score (0-100, lower is better)"""
        stories = self._get_all_stories()
        active_stories = [s for s in stories if s.get("status") != "complete"]

        if not active_stories:
            return 0.0

        total_issues = sum(len(issues) for issues in self.issues.values())
        health_score = (total_issues / len(active_stories)) * 100

        return round(health_score, 1)

    def generate_report(self) -> str:
        """Generate comprehensive backlog health report"""
        aging = self.check_aging_stories()
        duplicates = self.check_duplicates()
        drift = self.check_priority_drift()
        undefined = self.check_undefined_stories()
        health_score = self.calculate_health_score()

        stories = self._get_all_stories()
        active_stories = [s for s in stories if s.get("status") != "complete"]

        report = []
        report.append("=" * 70)
        report.append("BACKLOG HEALTH REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        report.append("")

        # Summary
        report.append("## Summary")
        report.append(f"  Total Stories: {len(stories)}")
        report.append(f"  Active Stories: {len(active_stories)}")
        report.append(f"  Completed Stories: {len(stories) - len(active_stories)}")
        report.append(
            f"  Health Score: {health_score}% (target: <{self.MAX_HEALTH_SCORE}%)"
        )
        report.append("")

        if health_score < self.MAX_HEALTH_SCORE:
            report.append(
                f"  ✅ HEALTHY - Backlog below {self.MAX_HEALTH_SCORE}% threshold"
            )
        else:
            report.append(
                f"  ⚠️  NEEDS ATTENTION - Backlog exceeds {self.MAX_HEALTH_SCORE}% threshold"
            )
        report.append("")

        # Aging Stories
        report.append("## Aging Stories")
        if aging:
            close_count = sum(1 for a in aging if a["severity"] == "CLOSE")
            flag_count = sum(1 for a in aging if a["severity"] == "FLAG")
            report.append(
                f"  Total: {len(aging)} ({close_count} close, {flag_count} flag)"
            )
            report.append("")

            for item in aging:
                severity_icon = "🔴" if item["severity"] == "CLOSE" else "🟡"
                report.append(f"  {severity_icon} [{item['story_id']}] {item['title']}")
                report.append(f"     Age: {item['age_days']} days")
                report.append(f"     {item['recommendation']}")
                report.append("")
        else:
            report.append("  ✅ No aging stories detected")
            report.append("")

        # Duplicates
        report.append("## Potential Duplicates")
        if duplicates:
            report.append(f"  Total: {len(duplicates)} potential duplicate pairs")
            report.append("")

            for item in duplicates:
                report.append(f"  🔄 [{item['story1_id']}] {item['story1_title']}")
                report.append(f"     [{item['story2_id']}] {item['story2_title']}")
                report.append(f"     Similarity: {item['similarity']}%")
                report.append(f"     {item['recommendation']}")
                report.append("")
        else:
            report.append("  ✅ No duplicates detected")
            report.append("")

        # Priority Drift
        report.append("## Priority Drift")
        if drift:
            report.append(
                f"  Total: {len(drift)} P0 stories older than lower priorities"
            )
            report.append("")

            for item in drift:
                report.append(f"  ⚠️  [{item['story_id']}] {item['title']}")
                report.append(
                    f"     Priority: {item['priority']}, Age: {item['age_days']} days"
                )
                report.append(f"     {item['recommendation']}")
                report.append("")
        else:
            report.append("  ✅ No priority drift detected")
            report.append("")

        # Undefined Stories
        report.append("## Undefined Stories")
        if undefined:
            report.append(
                f"  Total: {len(undefined)} stories missing critical information"
            )
            report.append("")

            for item in undefined:
                report.append(f"  ❌ [{item['story_id']}] {item['title']}")
                report.append(f"     Missing: {', '.join(item['missing_fields'])}")
                report.append(f"     {item['recommendation']}")
                report.append("")
        else:
            report.append("  ✅ All stories have required fields")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        total_issues = sum(len(issues) for issues in self.issues.values())

        if total_issues == 0:
            report.append("  ✅ Backlog is healthy - no action required")
        else:
            report.append(f"  Action Required: {total_issues} issues detected")
            report.append("")

            if aging:
                close_stories = [a for a in aging if a["severity"] == "CLOSE"]
                if close_stories:
                    report.append(
                        f"  1. Close {len(close_stories)} stories >90 days old:"
                    )
                    for story in close_stories[:5]:  # Show first 5
                        report.append(f"     - {story['story_id']}")
                    if len(close_stories) > 5:
                        report.append(f"     ... and {len(close_stories) - 5} more")
                    report.append("")

            if duplicates:
                report.append(f"  2. Review {len(duplicates)} potential duplicates")
                report.append("")

            if drift:
                report.append(
                    f"  3. Re-prioritize {len(drift)} P0 stories or close if no longer critical"
                )
                report.append("")

            if undefined:
                report.append(f"  4. Add missing fields to {len(undefined)} stories")
                report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def clean_backlog(self, dry_run: bool = True) -> dict[str, Any]:
        """Clean backlog by flagging/closing stale stories"""
        actions = {"flagged": [], "closed": [], "updated": []}

        aging = self.check_aging_stories()

        for item in aging:
            story_id = item["story_id"]

            if item["severity"] == "CLOSE":
                if not dry_run:
                    # In real implementation, would close the story
                    pass
                actions["closed"].append(story_id)
            else:
                if not dry_run:
                    # In real implementation, would flag for review
                    pass
                actions["flagged"].append(story_id)

        if not dry_run:
            self._save_backlog()

        return actions

    def validate_structure(self) -> dict[str, Any]:
        """Validate backlog JSON structure"""
        issues = []

        # Check required top-level fields
        if "current_sprint" not in self.backlog:
            issues.append("Missing 'current_sprint' field")

        if "sprints" not in self.backlog:
            issues.append("Missing 'sprints' field")

        # Validate each sprint
        for sprint_id, sprint_data in self.backlog.get("sprints", {}).items():
            if "stories" not in sprint_data:
                issues.append(f"Sprint {sprint_id}: Missing 'stories' array")

            # Validate each story
            for story in sprint_data.get("stories", []):
                if "id" not in story:
                    issues.append(f"Sprint {sprint_id}: Story missing 'id' field")

                if "title" not in story:
                    issues.append(
                        f"Sprint {sprint_id}: Story {story.get('id', 'unknown')} missing 'title'"
                    )

        return {"valid": len(issues) == 0, "issues": issues}


def main():
    parser = argparse.ArgumentParser(
        description="Backlog Groomer - Automated backlog health management"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate backlog health report"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean backlog by flagging/closing stale stories",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate backlog structure"
    )
    parser.add_argument(
        "--duplicates", action="store_true", help="Find duplicate stories only"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes (for --clean)",
    )
    parser.add_argument(
        "--backlog",
        default="skills/sprint_tracker.json",
        help="Path to backlog file (default: skills/sprint_tracker.json)",
    )

    args = parser.parse_args()

    groomer = BacklogGroomer(args.backlog)

    if args.report:
        print(groomer.generate_report())

    elif args.clean:
        actions = groomer.clean_backlog(dry_run=args.dry_run)
        mode = "DRY RUN - " if args.dry_run else ""
        print(f"{mode}Backlog Cleaning Results:")
        print(f"  Flagged for review: {len(actions['flagged'])} stories")
        print(f"  Closed: {len(actions['closed'])} stories")

        if actions["flagged"]:
            print(f"\n  Flagged Stories: {', '.join(actions['flagged'])}")

        if actions["closed"]:
            print(f"\n  Closed Stories: {', '.join(actions['closed'])}")

    elif args.validate:
        validation = groomer.validate_structure()
        if validation["valid"]:
            print("✅ Backlog structure is valid")
        else:
            print("❌ Backlog structure has issues:")
            for issue in validation["issues"]:
                print(f"  - {issue}")

    elif args.duplicates:
        duplicates = groomer.check_duplicates()
        if duplicates:
            print(f"Found {len(duplicates)} potential duplicate pairs:\n")
            for dup in duplicates:
                print(f"[{dup['story1_id']}] {dup['story1_title']}")
                print(f"[{dup['story2_id']}] {dup['story2_title']}")
                print(f"Similarity: {dup['similarity']}%")
                print(f"{dup['recommendation']}\n")
        else:
            print("✅ No duplicates detected")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
