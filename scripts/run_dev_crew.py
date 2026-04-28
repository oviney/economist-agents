#!/usr/bin/env python3
"""Autonomous Development Crew Runner.

Fetches a GitHub issue, extracts story data, creates a feature branch,
runs the Development Crew (TDD workflow), creates a PR, and requests
human review.  This is the autonomous loop that connects GitHub issues
to implemented, reviewed, tested code.

Usage:
    python scripts/run_dev_crew.py --issue 117

    # Or let it pick the next ready issue automatically
    python scripts/run_dev_crew.py --next
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from github_issue_claim import GitHubIssueClaimer

logger = logging.getLogger(__name__)
DEFAULT_RUNTIME = "claude"


def gh_api(endpoint: str, method: str = "GET") -> dict[str, Any] | list[Any]:
    """Call GitHub API via gh CLI."""
    cmd = ["gh", "api", endpoint]
    if method != "GET":
        cmd.extend(["-X", method])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def gh_run(args: list[str], check: bool = True) -> str:
    """Run a gh CLI command."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if check and result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def git_run(args: list[str], check: bool = True) -> str:
    """Run a git command."""
    result = subprocess.run(["git", *args], capture_output=True, text=True, timeout=60)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_issue(issue_number: int) -> dict[str, Any]:
    """Fetch a GitHub issue and extract story data."""
    data = gh_api(f"repos/oviney/economist-agents/issues/{issue_number}")

    title = data.get("title", "")
    body = data.get("body", "")
    labels = [label["name"] for label in data.get("labels", [])]

    # Extract acceptance criteria from body (lines starting with - [ ])
    acs = re.findall(r"- \[[ x]\] (.+)", body)

    # Extract story points from title (e.g., "(3pts)")
    points_match = re.search(r"\((\d+)pts?\)", title)
    story_points = int(points_match.group(1)) if points_match else None

    # Extract escalation questions
    escalations = []
    in_escalations = False
    for line in body.split("\n"):
        if "escalation" in line.lower():
            in_escalations = True
            continue
        if in_escalations and line.startswith("- "):
            escalations.append(line[2:].strip())
        elif in_escalations and line.startswith("#"):
            in_escalations = False

    return {
        "issue_number": issue_number,
        "story_title": title,
        "story_number": str(issue_number),
        "acceptance_criteria": acs,
        "story_points": story_points,
        "labels": labels,
        "body": body,
        "escalations": escalations,
        "url": data.get("html_url", ""),
    }


def find_next_issue(runtime: str) -> int | None:
    """Find the next claimable open issue with enhancement+quality labels."""
    claimer = GitHubIssueClaimer()
    return claimer.find_next_claimable_issue(["enhancement", "quality"], runtime)


def create_branch(issue_number: int, title: str) -> str:
    """Create a feature branch for the issue."""
    slug = title.lower()
    for ch in " :?!,.'\"()":
        slug = slug.replace(ch, "-")
    slug = re.sub(r"-+", "-", slug).strip("-")[:40]
    branch = f"story/{issue_number}-{slug}"

    git_run(["checkout", "main"])
    git_run(["pull"])
    git_run(["checkout", "-b", branch])

    return branch


def run_development_crew(story_data: dict[str, Any]) -> dict[str, Any]:
    """Run the Development Crew on a story."""
    # Import here to avoid loading CrewAI at module level
    from dotenv import load_dotenv

    load_dotenv()

    sys.path.insert(0, str(Path(__file__).parent.parent))
    sys.path.insert(0, str(Path(__file__).parent))

    from src.crews.development_crew import DevelopmentCrew

    crew = DevelopmentCrew()
    return crew.kickoff(story_data)


def create_pr(
    branch: str, story_data: dict[str, Any], crew_result: dict[str, Any]
) -> str:
    """Create a PR for the implemented story."""
    issue_num = story_data["issue_number"]
    title = story_data["story_title"]

    # Push branch
    git_run(["push", "-u", "origin", branch])

    # Build PR body
    acs = "\n".join(f"- [x] {ac}" for ac in story_data["acceptance_criteria"])
    phases = "\n".join(f"- [x] {p}" for p in crew_result.get("phases_completed", []))

    pr_url = gh_run(
        [
            "pr",
            "create",
            "--repo",
            "oviney/economist-agents",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"{title}",
            "--body",
            f"""## Story #{issue_num}

### Acceptance Criteria
{acs}

### Development Phases Completed
{phases}

### Quality Metrics
- Tests: {"passing" if crew_result.get("quality_metrics", {}).get("tests_passing") else "unknown"}
- Code review: {"approved" if crew_result.get("quality_metrics", {}).get("code_review_approved") else "pending"}
- Quality standards: {"met" if crew_result.get("quality_metrics", {}).get("quality_standards_met") else "unknown"}

### Human Governance
This PR was implemented autonomously by the Development Crew (4 agents: test-specialist, code-quality-specialist, code-reviewer, git-operator) using TDD workflow.

**Requesting human review before merge.**

Closes #{issue_num}

🤖 Implemented by Development Crew via `scripts/run_dev_crew.py`
""",
        ]
    )

    return pr_url


def log_to_issue(issue_number: int, message: str) -> None:
    """Add a comment to the GitHub issue for traceability."""
    gh_run(
        [
            "issue",
            "comment",
            str(issue_number),
            "--repo",
            "oviney/economist-agents",
            "--body",
            message,
        ],
        check=False,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Autonomous Development Crew Runner")
    parser.add_argument("--issue", type=int, help="GitHub issue number to implement")
    parser.add_argument(
        "--next", action="store_true", help="Pick next ready issue automatically"
    )
    parser.add_argument(
        "--runtime",
        default=DEFAULT_RUNTIME,
        help="Runtime name used for issue claiming",
    )
    args = parser.parse_args()

    # Determine which issue to work on
    if args.issue:
        issue_number = args.issue
    elif args.next:
        issue_number = find_next_issue(args.runtime)
        if not issue_number:
            print("No ready issues found with enhancement+quality labels")
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)

    print(f"{'=' * 60}")
    print("DEVELOPMENT CREW — Autonomous Implementation")
    print(f"{'=' * 60}")
    print(f"Issue: #{issue_number}")

    claimer = GitHubIssueClaimer()

    print("\n🔐 Claiming issue...")
    try:
        claim = claimer.claim_issue(issue_number, runtime=args.runtime)
        claim_expiry = (
            claim.expires_at.isoformat() if claim.expires_at is not None else "unknown"
        )
        print(f"   Owner: {claim.runtime}")
        print(f"   Lease expiry: {claim_expiry}")
    except RuntimeError as exc:
        print(f"   ❌ {exc}")
        sys.exit(1)

    # Step 1: Fetch issue
    print("\n📋 Fetching issue...")
    story_data = fetch_issue(issue_number)
    print(f"   Title: {story_data['story_title']}")
    print(f"   ACs: {len(story_data['acceptance_criteria'])}")
    print(f"   Points: {story_data['story_points']}")

    if story_data["escalations"]:
        print("\n   ⚠️  Escalations (need human input):")
        for e in story_data["escalations"]:
            print(f"      ? {e}")

    # Step 2: Log start to issue
    log_to_issue(
        issue_number,
        f"""🤖 **Development Crew picking up this story**

**Claim owner:** `{args.runtime}`

**Agents assigned:**
- test-specialist (TDD Red phase)
- code-quality-specialist (TDD Green + Refactor)
- code-reviewer (Senior review)
- git-operator (Commit + Push)

**Acceptance Criteria parsed:** {len(story_data["acceptance_criteria"])}
**Estimated points:** {story_data["story_points"]}

Starting autonomous implementation...
""",
    )

    # Step 3: Create branch
    print("\n🌿 Creating feature branch...")
    branch = create_branch(issue_number, story_data["story_title"])
    print(f"   Branch: {branch}")

    # Step 4: Run Development Crew
    print("\n🏗️  Running Development Crew (TDD workflow)...")
    print("   Phase 1: TDD Red (write failing tests)")
    print("   Phase 2: TDD Green (implement)")
    print("   Phase 3: Senior Review")
    print("   Phase 4: TDD Refactor")
    print("   Phase 5: Git Operations")

    try:
        crew_result = run_development_crew(story_data)
    except Exception as e:
        error_msg = f"Development Crew failed: {e}"
        print(f"\n❌ {error_msg}")
        log_to_issue(
            issue_number, f"❌ **Development Crew failed**\n\n```\n{error_msg}\n```"
        )
        git_run(["checkout", "main"])
        sys.exit(1)

    status = crew_result.get("status", "unknown")
    print(f"\n   Result: {status}")

    if status != "success":
        error = crew_result.get("error", "Unknown error")
        log_to_issue(
            issue_number,
            f"❌ **Development Crew completed with status: {status}**\n\n```\n{error}\n```",
        )
        git_run(["checkout", "main"])
        sys.exit(1)

    # Step 5: Create PR
    print("\n📝 Creating PR for human review...")
    try:
        pr_url = create_pr(branch, story_data, crew_result)
        print(f"   PR: {pr_url}")
    except Exception as e:
        print(f"   ⚠️  PR creation failed: {e}")
        pr_url = "PR creation failed"

    # Step 6: Log completion to issue
    phases = crew_result.get("phases_completed", [])
    log_to_issue(
        issue_number,
        f"""✅ **Development Crew completed implementation**

**Phases completed:**
{chr(10).join(f"- ✅ {p}" for p in phases)}

**PR:** {pr_url}

**Awaiting human governance review.**
""",
    )

    print(f"\n{'=' * 60}")
    print("COMPLETE — PR ready for human review")
    print(f"{'=' * 60}")
    print(f"Issue: #{issue_number}")
    print(f"Branch: {branch}")
    print(f"PR: {pr_url}")
    print(f"Status: {status}")


if __name__ == "__main__":
    main()
