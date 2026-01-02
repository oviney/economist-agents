#!/usr/bin/env python3
"""
Migrate BACKLOG.md to GitHub Issues

Converts markdown backlog to GitHub Issues with proper labels and metadata.
Requires GitHub CLI (gh) to be installed and authenticated.

Usage:
    # Preview what will be created (dry run)
    python3 scripts/migrate_backlog_to_github.py --dry-run

    # Actually create the issues
    python3 scripts/migrate_backlog_to_github.py --create

    # Export to JSON for manual import
    python3 scripts/migrate_backlog_to_github.py --export issues.json
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class BacklogParser:
    """Parse BACKLOG.md into structured data"""

    def __init__(self, backlog_path: str):
        self.backlog_path = Path(backlog_path)
        self.items = []

    def parse(self) -> list[dict[str, Any]]:
        """Parse backlog file and return list of items"""
        with open(self.backlog_path) as f:
            content = f.read()

        # Split by H3 headers (### Item Title)
        sections = re.split(r"\n### (✅|🟢|🔴|🟡|🧊) ", content)

        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                status = sections[i]
                title_and_body = sections[i + 1]

                item = self._parse_item(status, title_and_body)
                if item:
                    self.items.append(item)

        return self.items

    def _parse_item(self, status_emoji: str, content: str) -> dict[str, Any]:
        """Parse individual backlog item"""
        lines = content.split("\n")

        # First line is title
        title = lines[0].strip()

        # Extract metadata
        metadata = {}
        body_lines = []
        in_body = False

        for line in lines[1:]:
            if line.startswith("**Status**:"):
                metadata["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Priority**:"):
                priority = line.split(":", 1)[1].strip()
                # Extract P0, P1, etc.
                match = re.search(r"P(\d+)", priority)
                if match:
                    metadata["priority"] = f"P{match.group(1)}"
                    metadata["priority_label"] = priority
            elif line.startswith("**Effort**:"):
                metadata["effort"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Created**:") or line.startswith("**Completed**:"):
                key = line.split(":", 1)[0].strip("*").lower()
                metadata[key] = line.split(":", 1)[1].strip()
            elif line.startswith("**Problem**:"):
                in_body = True
                body_lines.append(line)
            elif line.strip() and not line.startswith("---"):
                if in_body or line.startswith("**"):
                    body_lines.append(line)

        body = "\n".join(body_lines).strip()

        # Map emoji to status
        status_map = {
            "✅": "complete",
            "🟢": "ready",
            "🔴": "blocked",
            "🟡": "in-progress",
            "🧊": "icebox",
        }

        return {
            "title": title,
            "body": body,
            "status": metadata.get("status", status_map.get(status_emoji, "ready")),
            "priority": metadata.get("priority", "P3"),
            "priority_label": metadata.get("priority_label", ""),
            "effort": metadata.get("effort", "Unknown"),
            "completed": metadata.get("completed"),
            "created": metadata.get("created"),
            "status_emoji": status_emoji,
        }


class GitHubIssueCreator:
    """Create GitHub Issues from backlog items"""

    def __init__(self, repo: str = None):
        self.repo = repo
        self.check_gh_cli()

    def check_gh_cli(self):
        """Check if GitHub CLI is installed and authenticated"""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError("GitHub CLI not authenticated. Run: gh auth login")
        except FileNotFoundError:
            raise RuntimeError(
                "GitHub CLI (gh) not installed.\n"
                "Install: brew install gh\n"
                "Then authenticate: gh auth login"
            )

    def create_issue(self, item: dict[str, Any], dry_run: bool = False) -> str:
        """Create a single GitHub issue"""
        # Build labels
        labels = [item["priority"]]

        if item["status"] == "complete":
            labels.append("status:complete")
        elif item["status"] == "in-progress":
            labels.append("status:in-progress")
        elif item["status"] == "blocked":
            labels.append("status:blocked")
        elif item["status"] == "icebox":
            labels.append("icebox")

        # Add effort label
        if item["effort"] in ["Small", "Medium", "Large"]:
            labels.append(f"effort:{item['effort'].lower()}")

        # Add type label
        labels.append("type:enhancement")

        # Build body with metadata
        body_parts = [item["body"]]

        if item.get("completed"):
            body_parts.append(f"\n---\n**Completed**: {item['completed']}")

        body = "\n".join(body_parts)

        if dry_run:
            print(f"\n{'=' * 60}")
            print(f"Title: {item['title']}")
            print(f"Labels: {', '.join(labels)}")
            print(f"Status: {item['status']}")
            print(f"Priority: {item['priority_label']}")
            print(f"Body preview: {body[:100]}...")
            return "DRY-RUN"

        # Create issue using gh CLI
        cmd = [
            "gh",
            "issue",
            "create",
            "--title",
            item["title"],
            "--body",
            body,
            "--label",
            ",".join(labels),
        ]

        if self.repo:
            cmd.extend(["--repo", self.repo])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issue_url = result.stdout.strip()
            print(f"✅ Created: {item['title']} → {issue_url}")
            return issue_url
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create issue: {e.stderr}")
            return None

    def create_all(
        self,
        items: list[dict[str, Any]],
        dry_run: bool = False,
        skip_completed: bool = True,
    ) -> list[str]:
        """Create issues for all backlog items"""
        created = []

        for item in items:
            # Skip completed items unless requested
            if skip_completed and item["status"] == "complete":
                print(f"⏭️  Skipping completed: {item['title']}")
                continue

            issue_url = self.create_issue(item, dry_run)
            if issue_url:
                created.append(issue_url)

        return created

    def ensure_labels(self, dry_run: bool = False):
        """Create standard labels if they don't exist"""
        labels = [
            ("P0", "Critical priority", "b60205"),
            ("P1", "High priority", "d93f0b"),
            ("P2", "Medium priority", "fbca04"),
            ("P3", "Low priority", "0e8a16"),
            ("P4", "Icebox", "d4c5f9"),
            ("status:complete", "Completed", "2ea44f"),
            ("status:in-progress", "In progress", "fbca04"),
            ("status:blocked", "Blocked", "b60205"),
            ("icebox", "Deferred", "d4c5f9"),
            ("effort:small", "Small effort", "c2e0c6"),
            ("effort:medium", "Medium effort", "f9d0c4"),
            ("effort:large", "Large effort", "f4c2c2"),
            ("type:enhancement", "Enhancement", "84b6eb"),
        ]

        for name, description, color in labels:
            if dry_run:
                print(f"Would create label: {name} ({description})")
            else:
                cmd = [
                    "gh",
                    "label",
                    "create",
                    name,
                    "--description",
                    description,
                    "--color",
                    color,
                ]
                if self.repo:
                    cmd.extend(["--repo", self.repo])

                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    print(f"✅ Created label: {name}")
                except subprocess.CalledProcessError:
                    # Label might already exist, that's OK
                    pass


def export_to_json(items: list[dict[str, Any]], output_path: str):
    """Export items to JSON for manual import"""
    with open(output_path, "w") as f:
        json.dump(items, f, indent=2)
    print(f"✅ Exported to {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate BACKLOG.md to GitHub Issues")
    parser.add_argument(
        "--backlog", default=".github/BACKLOG.md", help="Path to BACKLOG.md file"
    )
    parser.add_argument(
        "--repo", help="GitHub repository (owner/repo). Auto-detected if not specified."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what will be created without actually creating issues",
    )
    parser.add_argument(
        "--create", action="store_true", help="Actually create the GitHub issues"
    )
    parser.add_argument(
        "--export", metavar="FILE", help="Export to JSON file for manual import"
    )
    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Include completed items (default: skip them)",
    )
    parser.add_argument(
        "--setup-labels",
        action="store_true",
        help="Create standard labels in the repository",
    )

    args = parser.parse_args()

    # Parse backlog
    print("📖 Parsing backlog...")
    parser = BacklogParser(args.backlog)
    items = parser.parse()
    print(f"   Found {len(items)} items")

    # Count by status
    completed = sum(1 for i in items if i["status"] == "complete")
    pending = len(items) - completed
    print(f"   {completed} completed, {pending} pending")

    if args.export:
        # Export to JSON
        export_to_json(items, args.export)
        return

    # Create issues
    if args.dry_run or args.create:
        creator = GitHubIssueCreator(repo=args.repo)

        # Setup labels first
        if args.setup_labels:
            print("\n🏷️  Setting up labels...")
            creator.ensure_labels(dry_run=args.dry_run)

        print(f"\n{'🔍 DRY RUN' if args.dry_run else '🚀 CREATING ISSUES'}...")
        print("=" * 60)

        created = creator.create_all(
            items, dry_run=args.dry_run, skip_completed=not args.include_completed
        )

        print("\n" + "=" * 60)
        if args.dry_run:
            print(
                f"📊 Would create {len([i for i in items if i['status'] != 'complete' or args.include_completed])} issues"
            )
            print("\nTo actually create these issues, run:")
            print(f"  python3 {sys.argv[0]} --create")
        else:
            print(f"✅ Created {len(created)} issues")
            print("\nNext steps:")
            print("1. Visit your GitHub repository")
            print("2. Create a Project board (Projects tab)")
            print("3. Add these issues to your project")
            print("4. Organize by priority/status")
    else:
        print("\nNo action specified. Use --dry-run, --create, or --export")
        print(f"Run: python3 {sys.argv[0]} --help")


if __name__ == "__main__":
    main()
