#!/usr/bin/env python3
"""
GitHub Sprint Sync

Syncs sprint information between SPRINT.md and GitHub:
- Creates GitHub issues from sprint stories
- Updates SPRINT.md with issue numbers
- Syncs sprint progress from GitHub Projects

Usage:
    # Push sprint stories to GitHub Issues
    python3 scripts/github_sprint_sync.py --push-to-github

    # Pull status from GitHub Issues to update SPRINT.md
    python3 scripts/github_sprint_sync.py --pull-from-github

    # Show sprint status from GitHub
    python3 scripts/github_sprint_sync.py --show-github-status
"""

import os
import re
import sys
from pathlib import Path

try:
    from github import Github, GithubException
except ImportError:
    print("❌ PyGithub not installed")
    print("   Run: pip install PyGithub")
    sys.exit(1)


class GitHubSprintSync:
    """Sync sprint data with GitHub Issues and Projects"""

    def __init__(self, repo_name: str = "oviney/economist-agents"):
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GITHUB_TOKEN not set. Create a token at:\n"
                "https://github.com/settings/tokens\n"
                "Then: export GITHUB_TOKEN='your_token'"
            )

        self.gh = Github(token)
        self.repo = self.gh.get_repo(repo_name)
        self.sprint_file = Path("SPRINT.md")

    def parse_sprint_stories(self, sprint_number: int) -> list[dict]:
        """Parse stories from SPRINT.md for given sprint"""
        with open(self.sprint_file) as f:
            content = f.read()

        # Find the sprint section
        pattern = rf"## Sprint {sprint_number}:([^\n]+)\n(.*?)(?=## Sprint \d+:|## Sprint Metrics|$)"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return []

        sprint_section = match.group(2)

        # Parse stories
        stories = []
        story_pattern = r"#### Story (\d+): ([^\n]+)\n\*\*Priority\*\*: ([^\n]+)\n\*\*Story Points\*\*: (\d+)\n\*\*Goal\*\*: ([^\n]+)"

        for match in re.finditer(story_pattern, sprint_section):
            story_num = int(match.group(1))
            title = match.group(2)
            priority = match.group(3)
            points = int(match.group(4))
            goal = match.group(5)

            # Extract tasks
            story_start = match.end()
            next_story = re.search(r"#### Story \d+:", sprint_section[story_start:])
            story_end = (
                story_start + next_story.start() if next_story else len(sprint_section)
            )
            story_content = sprint_section[story_start:story_end]

            tasks = re.findall(r"- \[([ x])\] ([^\n]+)", story_content)

            # Extract acceptance criteria
            ac_section = re.search(
                r"\*\*Acceptance Criteria:\*\*\n(.*?)(?=\*\*|$)",
                story_content,
                re.DOTALL,
            )
            acceptance_criteria = []
            if ac_section:
                ac_text = ac_section.group(1)
                acceptance_criteria = re.findall(r"- ([^\n]+)", ac_text)

            stories.append(
                {
                    "number": story_num,
                    "title": title,
                    "priority": priority,
                    "points": points,
                    "goal": goal,
                    "tasks": [(checked == "x", text) for checked, text in tasks],
                    "acceptance_criteria": acceptance_criteria,
                }
            )

        return stories

    def create_github_issue_from_story(self, story: dict, sprint_number: int) -> int:
        """Create GitHub issue from sprint story"""

        # Build issue body
        body_parts = [
            f"## Story Goal\n{story['goal']}\n",
            f"## Priority\n{story['priority']}\n",
            f"## Story Points\n{story['points']}\n",
        ]

        if story["tasks"]:
            body_parts.append("## Tasks\n")
            for completed, task in story["tasks"]:
                checkbox = "x" if completed else " "
                body_parts.append(f"- [{checkbox}] {task}\n")
            body_parts.append("")

        if story["acceptance_criteria"]:
            body_parts.append("## Acceptance Criteria\n")
            for ac in story["acceptance_criteria"]:
                body_parts.append(f"- [ ] {ac}\n")
            body_parts.append("")

        body_parts.append(
            f"\n---\n*Generated from Sprint {sprint_number}, Story {story['number']}*"
        )

        body = "\n".join(body_parts)

        # Create issue
        title = f"Story {story['number']}: {story['title']}"

        labels = [
            "sprint-story",
            f"sprint-{sprint_number}",
            f"{story['points']}-points",
        ]

        # Map priority to label
        priority_map = {
            "P0 (Must Do)": "P0",
            "P1 (High)": "P1",
            "P2 (Medium)": "P2",
            "P3": "P3",
        }
        priority_label = priority_map.get(story["priority"], "P2")
        labels.append(priority_label)

        try:
            issue = self.repo.create_issue(title=title, body=body, labels=labels)
            return issue.number
        except GithubException as e:
            print(f"  ❌ Failed to create issue: {e}")
            return None

    def push_to_github(self, sprint_number: int = 2):
        """Create GitHub issues for all sprint stories"""
        print(f"🔄 Pushing Sprint {sprint_number} stories to GitHub...\n")

        stories = self.parse_sprint_stories(sprint_number)

        if not stories:
            print(f"  ❌ No stories found for Sprint {sprint_number}")
            return

        print(f"  Found {len(stories)} stories\n")

        created_issues = {}

        for story in stories:
            print(
                f"  Creating issue for Story {story['number']}: {story['title'][:50]}..."
            )
            issue_num = self.create_github_issue_from_story(story, sprint_number)

            if issue_num:
                created_issues[story["number"]] = issue_num
                print(f"    ✅ Created #{issue_num}")

        if created_issues:
            print(f"\n✅ Created {len(created_issues)} GitHub issues:")
            for story_num, issue_num in created_issues.items():
                print(f"   Story {story_num} → Issue #{issue_num}")
                print(f"   https://github.com/{self.repo.full_name}/issues/{issue_num}")

    def show_github_status(self):
        """Show sprint status from GitHub Issues"""
        print("📊 GitHub Sprint Status\n")

        # Get sprint stories
        issues = self.repo.get_issues(labels=["sprint-story"], state="open")

        stories_by_sprint = {}

        for issue in issues:
            # Extract sprint number from labels
            sprint_label = next(
                (
                    label.name
                    for label in issue.labels
                    if label.name.startswith("sprint-")
                ),
                None,
            )
            if not sprint_label:
                continue

            sprint_num = sprint_label.replace("sprint-", "")

            if sprint_num not in stories_by_sprint:
                stories_by_sprint[sprint_num] = []

            # Extract story points
            points_label = next(
                (label.name for label in issue.labels if "-points" in label.name), None
            )
            points = int(points_label.replace("-points", "")) if points_label else 0

            stories_by_sprint[sprint_num].append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "points": points,
                    "state": issue.state,
                    "comments": issue.comments,
                }
            )

        for sprint_num in sorted(stories_by_sprint.keys()):
            stories = stories_by_sprint[sprint_num]
            total_points = sum(s["points"] for s in stories)

            print(f"Sprint {sprint_num}:")
            print(f"  Stories: {len(stories)}")
            print(f"  Story Points: {total_points}")
            print()

            for story in stories:
                print(f"  #{story['number']}: {story['title']}")
                print(f"    Points: {story['points']} | Comments: {story['comments']}")
            print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync sprint with GitHub")
    parser.add_argument(
        "--push-to-github",
        action="store_true",
        help="Create GitHub issues from SPRINT.md",
    )
    parser.add_argument(
        "--pull-from-github",
        action="store_true",
        help="Update SPRINT.md from GitHub issues",
    )
    parser.add_argument(
        "--show-github-status",
        action="store_true",
        help="Show sprint status from GitHub",
    )
    parser.add_argument(
        "--sprint", type=int, default=2, help="Sprint number (default: 2)"
    )

    args = parser.parse_args()

    try:
        sync = GitHubSprintSync()

        if args.push_to_github:
            sync.push_to_github(args.sprint)
        elif args.show_github_status:
            sync.show_github_status()
        elif args.pull_from_github:
            print("Pull from GitHub - Not yet implemented")
            print("Manually sync by checking GitHub issue status")
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
