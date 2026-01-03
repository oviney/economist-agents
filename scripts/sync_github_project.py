#!/usr/bin/env python3
"""
GitHub Projects Board Synchronization

Syncs Sprint 9 backlog to GitHub Projects for visibility and tracking.
Creates project board with all stories, configures fields, and sets up automation.

Usage:
    python3 scripts/sync_github_project.py --create
    python3 scripts/sync_github_project.py --sync
    python3 scripts/sync_github_project.py --status
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class GitHubProjectSync:
    """Sync sprint backlog to GitHub Projects"""

    def __init__(self, repo: str = "oviney/economist-agents"):
        self.repo = repo
        self.project_id = None
        self.sprint_tracker_path = Path("skills/sprint_tracker.json")

    def _run_gh(self, args: list[str]) -> tuple[str, int]:
        """Run gh CLI command and return output"""
        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            # Debug output for failures
            if result.returncode != 0:
                print(
                    f"   DEBUG: gh {' '.join(args[:2])} failed (code {result.returncode})"
                )
                if result.stderr:
                    print(f"   DEBUG: stderr={result.stderr[:300]}")
            return result.stdout.strip(), result.returncode
        except FileNotFoundError:
            print("❌ GitHub CLI (gh) not found. Install with: brew install gh")
            sys.exit(1)

    def check_auth(self) -> bool:
        """Verify GitHub CLI authentication"""
        output, code = self._run_gh(["auth", "status"])
        if code != 0:
            print("❌ Not authenticated. Run: gh auth login")
            return False
        print("✅ GitHub CLI authenticated")
        return True

    def load_sprint_tracker(self) -> dict:
        """Load sprint tracker data"""
        if not self.sprint_tracker_path.exists():
            print(f"❌ Sprint tracker not found: {self.sprint_tracker_path}")
            sys.exit(1)

        with open(self.sprint_tracker_path) as f:
            return json.load(f)

    def create_project(self, sprint_num: int = 9) -> str:
        """Create GitHub Project board"""
        tracker = self.load_sprint_tracker()
        sprint_key = f"sprint_{sprint_num}"

        if sprint_key not in tracker["sprints"]:
            print(f"❌ Sprint {sprint_num} not found in tracker")
            sys.exit(1)

        title = f"Sprint {sprint_num}: Validation & Measurement"

        # Create project
        print(f"\n📋 Creating GitHub Project: {title}")
        output, code = self._run_gh(
            [
                "project",
                "create",
                "--owner",
                self.repo.split("/")[0],
                "--title",
                title,
                "--format",
                "json",
            ]
        )

        if code != 0:
            print(f"❌ Failed to create project: {output}")
            sys.exit(1)

        project_data = json.loads(output)
        self.project_id = project_data["number"]
        project_url = project_data["url"]

        print(f"✅ Project created: {project_url}")
        print(f"   Project ID: {self.project_id}")

        return project_url

    def create_issues(self, sprint_num: int = 9) -> list[dict]:
        """Create GitHub issues for each story"""
        tracker = self.load_sprint_tracker()
        sprint_key = f"sprint_{sprint_num}"
        sprint = tracker["sprints"][sprint_key]

        created_issues = []

        print(f"\n📝 Creating issues for {len(sprint['stories'])} stories...")

        for story in sprint["stories"]:
            story_id = story["id"]
            story_name = story["name"]
            points = story["points"]
            priority = story["priority"]
            status = story.get("status", "not_started")

            # Create issue title
            title = f"Story {story_id}: {story_name}"

            # Create issue body
            body = f"""## Story Details

**Sprint**: 9
**Story Points**: {points}
**Priority**: {priority}
**Status**: {status}

**Story**: {story_name}

**Notes**: {story.get('notes', 'No notes available')}

---

*Auto-created by sync_github_project.py*
"""

            # Determine labels
            labels = [f"sprint-{sprint_num}", priority.lower()]
            if status == "complete":
                labels.append("completed")
            elif status == "in_progress":
                labels.append("in-progress")

            # Add story point label
            labels.append(f"{points}-points")

            # Create issue
            print(f"   Creating: {title}")
            output, code = self._run_gh(
                [
                    "issue",
                    "create",
                    "--repo",
                    self.repo,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    ",".join(labels),
                ]
            )

            if code != 0:
                print(f"   ⚠️  Failed to create issue: {output}")
                continue

            # Parse issue URL from output
            issue_url = output.strip()
            issue_num = issue_url.split("/")[-1]

            created_issues.append(
                {
                    "story_id": story_id,
                    "issue_number": issue_num,
                    "issue_url": issue_url,
                    "title": title,
                }
            )

            print(f"   ✅ Created issue #{issue_num}: {issue_url}")

        return created_issues

    def link_issues_to_project(self, issues: list[dict]) -> None:
        """Link created issues to project board"""
        if not self.project_id:
            print("⚠️  No project ID - skipping project linking")
            return

        print(f"\n🔗 Linking {len(issues)} issues to project...")

        for issue in issues:
            issue_num = issue["issue_number"]
            output, code = self._run_gh(
                [
                    "project",
                    "item-add",
                    str(self.project_id),
                    "--owner",
                    self.repo.split("/")[0],
                    "--url",
                    f"https://github.com/{self.repo}/issues/{issue_num}",
                ]
            )

            if code != 0:
                print(f"   ⚠️  Failed to link issue #{issue_num}: {output}")
            else:
                print(f"   ✅ Linked issue #{issue_num}")

    def update_sprint_tracker(self, project_url: str, issues: list[dict]) -> None:
        """Update sprint tracker with GitHub info"""
        tracker = self.load_sprint_tracker()

        # Add GitHub project info to Sprint 9
        if "sprint_9" not in tracker:
            tracker["sprint_9"] = {}

        tracker["sprint_9"]["github_project"] = {
            "url": project_url,
            "project_id": self.project_id,
            "synced_at": datetime.now().isoformat(),
            "issues": issues,
        }

        # Save updated tracker
        with open(self.sprint_tracker_path, "w") as f:
            json.dump(tracker, f, indent=2)

        print(f"\n✅ Updated {self.sprint_tracker_path} with GitHub info")

    def run_create(self, sprint_num: int = 9) -> dict:
        """Full workflow: create issues (simplified - no project board)"""
        print("=" * 70)
        print(f"🚀 GitHub Issues Creation - Sprint {sprint_num}")
        print("=" * 70)

        # Step 1: Check auth
        if not self.check_auth():
            sys.exit(1)

        # Step 2: Create issues (skip project board for now)
        print(
            "\n⚠️  Note: Creating issues only (project board requires 'project' scope)"
        )
        print("   Run 'gh auth refresh -s project' to enable project board creation")
        issues = self.create_issues(sprint_num)

        # Step 3: Update tracker (without project URL)
        tracker = self.load_sprint_tracker()
        if "sprint_9" not in tracker:
            tracker["sprint_9"] = {}

        tracker["sprint_9"]["github_issues"] = {
            "synced_at": datetime.now().isoformat(),
            "issues": issues,
        }

        with open(self.sprint_tracker_path, "w") as f:
            json.dump(tracker, f, indent=2)

        print(f"\n✅ Updated {self.sprint_tracker_path} with GitHub info")

        print("\n" + "=" * 70)
        print("✅ COMPLETE: GitHub Issues Created")
        print("=" * 70)
        print(f"\n📝 Issues Created: {len(issues)}")
        print(f"   Stories: {[i['story_id'] for i in issues]}")
        issues_url = f"https://github.com/{self.repo}/issues?q=is%3Aissue+label%3Asprint-{sprint_num}"
        print(f"\n🔗 View issues: {issues_url}")

        return {
            "issues_created": len(issues),
            "issues": issues,
            "issues_url": issues_url,
        }

    def show_status(self, sprint_num: int = 9) -> None:
        """Show current GitHub sync status"""
        tracker = self.load_sprint_tracker()

        sprint_key = f"sprint_{sprint_num}"
        if sprint_key not in tracker["sprints"]:
            print(f"❌ Sprint {sprint_num} not found")
            sys.exit(1)

        sprint = tracker["sprints"][sprint_key]

        print(f"\n📊 Sprint {sprint_num} Status")
        print("=" * 70)
        print(f"Status: {sprint.get('status', 'unknown')}")
        print(
            f"Points Delivered: {sprint.get('points_delivered', 0)}/{sprint.get('capacity', 0)}"
        )
        print(f"Completion: {sprint.get('completion_rate', 0)*100:.0f}%")

        if "github_project" in sprint:
            gh = sprint["github_project"]
            print("\n🔗 GitHub Project:")
            print(f"   URL: {gh['url']}")
            print(f"   Issues: {len(gh.get('issues', []))}")
            print(f"   Last Synced: {gh.get('synced_at', 'unknown')}")
        else:
            print("\n⚠️  Not synced to GitHub Projects yet")
            print("   Run: python3 scripts/sync_github_project.py --create")


def main():
    parser = argparse.ArgumentParser(
        description="Sync sprint backlog to GitHub Projects"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create new GitHub Project board with all stories",
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current GitHub sync status"
    )
    parser.add_argument(
        "--sprint", type=int, default=9, help="Sprint number to sync (default: 9)"
    )

    args = parser.parse_args()

    sync = GitHubProjectSync()

    if args.create:
        sync.run_create(args.sprint)
    elif args.status:
        sync.show_status(args.sprint)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
