#!/usr/bin/env python3
"""
CI Health Monitor - Automated GitHub Actions Status Checker

Responsible Agent: @code-quality-specialist
Purpose: Daily CI/CD health monitoring and automated dispatch
Schedule: Run daily at 9:00 AM or on-demand
Created: 2026-01-03

Usage:
    python3 scripts/ci_health_monitor.py [--workflow-id ci.yml] [--alert]

Options:
    --workflow-id: GitHub Actions workflow file (default: ci.yml)
    --alert: Send alert if CI is red (Slack/email integration point)
    --last-n: Check last N runs (default: 3)
    --update-log: Update CI_HEALTH_LOG.md automatically
"""

import argparse
import json
import subprocess
from datetime import datetime


class CIHealthMonitor:
    """Monitor GitHub Actions CI/CD health and dispatch on failures"""

    def __init__(
        self, workflow_id: str = "ci.yml", repo: str = "oviney/economist-agents"
    ):
        self.workflow_id = workflow_id
        self.repo = repo
        self.gh_cli_available = self._check_gh_cli()

    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is installed"""
        try:
            subprocess.run(
                ["gh", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  GitHub CLI (gh) not installed")
            print("   Install: brew install gh")
            print("   Then run: gh auth login")
            return False

    def get_workflow_runs(self, last_n: int = 3) -> list[dict]:
        """Get last N workflow runs using GitHub CLI"""
        if not self.gh_cli_available:
            return []

        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    self.workflow_id,
                    "--repo",
                    self.repo,
                    "--limit",
                    str(last_n),
                    "--json",
                    "conclusion,status,createdAt,number,event,headBranch,headSha,url",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            runs = json.loads(result.stdout)
            return runs

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to fetch workflow runs: {e}")
            return []

    def check_health(self, last_n: int = 3) -> dict:
        """Check CI health status"""
        runs = self.get_workflow_runs(last_n)

        if not runs:
            return {
                "status": "UNKNOWN",
                "message": "Unable to fetch workflow runs",
                "action": "MANUAL_CHECK",
            }

        latest = runs[0]
        status = latest["status"]
        conclusion = latest.get("conclusion", "in_progress")

        # Analyze health
        if status == "completed":
            if conclusion == "success":
                health_status = "GREEN"
                message = "✅ CI is healthy - all workflows passing"
                action = "CONTINUE"
            elif conclusion == "failure":
                health_status = "RED"
                message = f"🚨 CI FAILURE - Run #{latest['number']} failed"
                action = "INVESTIGATE"
            else:
                health_status = "YELLOW"
                message = f"⚠️  CI completed with: {conclusion}"
                action = "REVIEW"
        elif status == "in_progress":
            health_status = "YELLOW"
            message = f"⏳ CI running - Run #{latest['number']}"
            action = "MONITOR"
        else:
            health_status = "YELLOW"
            message = f"⚠️  CI status: {status}"
            action = "REVIEW"

        # Check for streak of failures
        failure_count = sum(
            1
            for r in runs
            if r.get("conclusion") == "failure" and r["status"] == "completed"
        )

        return {
            "status": health_status,
            "message": message,
            "action": action,
            "latest_run": latest,
            "total_runs": len(runs),
            "failure_count": failure_count,
            "consecutive_failures": failure_count
            == len([r for r in runs if r["status"] == "completed"]),
            "runs": runs,
        }

    def dispatch_action(self, health: dict, create_issue: bool = False) -> None:
        """Dispatch appropriate action based on CI health"""
        status = health["status"]
        action = health["action"]

        print("\n" + "=" * 70)
        print("CI HEALTH CHECK REPORT")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Status: {status}")
        print(f"Message: {health['message']}")
        print(f"Action Required: {action}")
        print("=" * 70 + "\n")

        if status == "GREEN":
            print("✅ No action needed - CI is healthy")
            print("   Continue sprint work as planned\n")
            return

        if status == "RED":
            print("🚨 CRITICAL ACTION REQUIRED")
            print("   1. Stop all sprint work immediately")
            print("   2. Notify team in daily standup")
            print("   3. Investigate root cause")

            latest = health["latest_run"]
            print(f"\n   Failed Run: #{latest['number']}")
            print(f"   URL: {latest['url']}")
            print(f"   Branch: {latest['headBranch']}")
            print(f"   Commit: {latest['headSha'][:7]}")

            if health["consecutive_failures"]:
                print(
                    f"\n   ⚠️  {health['failure_count']} consecutive failures detected"
                )
                print("   This is a systematic issue requiring immediate attention")

            if create_issue:
                self._create_github_issue(health)

            print(
                "\n   Next Steps:"
                "\n   - View logs: gh run view {run_number} --repo {repo}"
                "\n   - Create issue: scripts/ci_health_monitor.py --alert --create-issue"
                "\n   - Update log: Update docs/CI_HEALTH_LOG.md manually"
            )

        elif status == "YELLOW":
            print("⚠️  MONITORING REQUIRED")
            print("   Check back in 10 minutes")
            print(f"   URL: {health['latest_run']['url']}")

    def _create_github_issue(self, health: dict) -> None:
        """Create GitHub issue for CI failure"""
        if not self.gh_cli_available:
            print("   ⚠️  Cannot create issue - GitHub CLI not available")
            return

        latest = health["latest_run"]
        title = (
            f"CI Failure: Build #{latest['number']} failed on {latest['headBranch']}"
        )

        body = f"""## CI/CD Failure Detected

**Detected By**: @code-quality-specialist (automated monitoring)
**Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Priority**: P0 - CRITICAL

### Failure Details

- **Run Number**: #{latest["number"]}
- **Workflow**: {self.workflow_id}
- **Branch**: {latest["headBranch"]}
- **Commit**: {latest["headSha"]}
- **Event**: {latest["event"]}
- **URL**: {latest["url"]}

### Failure Pattern

- **Consecutive Failures**: {health["failure_count"]} of last {health["total_runs"]} runs
- **Systematic Issue**: {"Yes - requires immediate attention" if health["consecutive_failures"] else "No - may be transient"}

### Required Actions

- [ ] View workflow logs: `gh run view {latest["number"]} --repo {self.repo}`
- [ ] Identify root cause
- [ ] Create fix plan with time estimate
- [ ] Notify team (stop sprint work if P0)
- [ ] Update CI_HEALTH_LOG.md with incident details
- [ ] Implement fix
- [ ] Validate fix with local testing
- [ ] Push fix and monitor next workflow run
- [ ] Update this issue with resolution

### Team Protocol

**If CI is RED**:
1. 🚨 **STOP ALL SPRINT WORK** until resolved
2. 🎙️ **REPORT IN STANDUP**: "CI red - P0 blocker"
3. 🔍 **INVESTIGATE**: Root cause analysis
4. 🛠️ **FIX**: Implement and test locally
5. ✅ **VALIDATE**: Confirm green build before resuming

### References

- [CI Health Log](../blob/main/docs/CI_HEALTH_LOG.md)
- [Quality Enforcer Responsibilities](../blob/main/docs/QUALITY_ENFORCER_RESPONSIBILITIES.md)
- [Definition of Done - CI/CD Requirements](../blob/main/docs/DEFINITION_OF_DONE.md)

---

**Assigned**: @code-quality-specialist
**Labels**: P0, ci-failure, devops
"""

        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    self.repo,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    "P0,ci-failure,devops",
                    "--assignee",
                    "@me",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            issue_url = result.stdout.strip()
            print(f"\n   ✅ Created issue: {issue_url}")

        except subprocess.CalledProcessError as e:
            print(f"\n   ❌ Failed to create issue: {e}")

    def generate_standup_report(self, health: dict) -> str:
        """Generate brief standup report"""
        status = health["status"]

        if status == "GREEN":
            return "✅ CI green - all workflows passing"
        elif status == "RED":
            return (
                f"🚨 CI red - P0 blocker (Run #{health['latest_run']['number']} failed)"
            )
        elif status == "YELLOW":
            return f"⚠️  CI yellow - monitoring (Run #{health['latest_run']['number']} in progress)"
        else:
            return "❓ CI status unknown - manual check required"


def main():
    parser = argparse.ArgumentParser(
        description="CI Health Monitor - Automated GitHub Actions status checker"
    )
    parser.add_argument(
        "--workflow-id",
        default="ci.yml",
        help="GitHub Actions workflow file (default: ci.yml)",
    )
    parser.add_argument(
        "--last-n",
        type=int,
        default=3,
        help="Check last N runs (default: 3)",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="Create GitHub issue if CI is red",
    )
    parser.add_argument(
        "--standup",
        action="store_true",
        help="Generate brief standup report only",
    )

    args = parser.parse_args()

    monitor = CIHealthMonitor(workflow_id=args.workflow_id)
    health = monitor.check_health(last_n=args.last_n)

    if args.standup:
        print(monitor.generate_standup_report(health))
    else:
        monitor.dispatch_action(health, create_issue=args.create_issue)


if __name__ == "__main__":
    main()
