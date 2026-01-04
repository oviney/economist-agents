# DevOps Agent - Skills & Capabilities Documentation

**Agent**: DevOps Engineer  
**Role**: Infrastructure Automation, CI/CD Maintenance, GitHub Projects Evolution Owner  
**Version**: 1.0  
**Created**: 2026-01-03  

---

## Overview

DevOps Engineer is responsible for infrastructure automation, CI/CD pipeline health, and GitHub project tracking evolution. Primary mission: Enable autonomous sprint visibility through GitHub Projects v2 integration, automated reporting, and infrastructure reliability.

**Primary Mission**: Transform GitHub project tracking from basic Issues into comprehensive Projects v2 with burndown charts, velocity tracking, custom views, and automated hygiene.

**Key Principle**: Infrastructure enables team velocity. Automated visibility creates autonomous execution.

---

## Core Responsibilities

### 1. GitHub Projects v2 Implementation (NEW - Sprint 10 Focus)

#### Purpose
Evolve GitHub project tracking from Issues-only to full Projects v2 with custom views, automated burndown, velocity tracking, and hygiene automation.

#### Current State (Sprint 9)
- ✅ GitHub Issues creation working (8 issues: #50-57)
- ✅ Labels system implemented (sprint-N, p0/p1/p2, points, status)
- ✅ sync_github_project.py functional (330 lines, Sprint 6)
- ⚠️ GitHub Projects v2 board NOT created (token scope limitation)
- ❌ Burndown charts not implemented
- ❌ Velocity tracking not implemented
- ❌ Custom project views not configured
- ❌ Automated hygiene not implemented

#### Target State (Sprint 10)
- 🎯 GitHub Projects v2 board created with sprint milestone
- 🎯 Custom views: Kanban (status lanes), Table (sortable), Roadmap (timeline)
- 🎯 Burndown chart generated daily from GitHub API
- 🎯 Velocity graph displaying last 5 sprints
- 🎯 Custom fields: sprint, story-points, priority, owner, status
- 🎯 Automated hygiene: stale issue cleanup, status sync, duplicate detection
- 🎯 Bidirectional sync: sprint_tracker.json ↔ GitHub Projects

#### Implementation Steps

**Step 1: GitHub Token Refresh (User Action Required)**
```bash
# Current token scopes: repo, workflow, read:org, gist
# Required additional scopes: read:project, write:project

gh auth refresh -s project

# Verify new scopes
gh auth status
# Expected: ✓ Logged in to github.com as oviney (...) with scopes: project, read:org, repo, workflow
```

**Step 2: Create GitHub Project Board**
```bash
# Create Sprint 10 project board
gh project create "Sprint 10: Autonomous Orchestration" \
  --owner oviney \
  --format "Board"

# Note project number (e.g., "Project #1")
```

**Step 3: Configure Custom Fields**
```bash
# Add story points field (numeric)
gh project field-create --owner oviney \
  --project-number 1 \
  --name "Story Points" \
  --data-type "NUMBER"

# Add sprint field (single select)
gh project field-create --owner oviney \
  --project-number 1 \
  --name "Sprint" \
  --data-type "SINGLE_SELECT" \
  --options "Sprint 10,Sprint 11,Sprint 12,Backlog"

# Add priority field (single select)
gh project field-create --owner oviney \
  --project-number 1 \
  --name "Priority" \
  --data-type "SINGLE_SELECT" \
  --options "P0,P1,P2,P3"

# Add owner field (assignee is built-in, but custom owner for planning)
gh project field-create --owner oviney \
  --project-number 1 \
  --name "Owner" \
  --data-type "SINGLE_SELECT" \
  --options "@devops,@scrum-master,@quality-enforcer,@test-writer,@refactor-specialist"
```

**Step 4: Link Existing Issues to Project**
```bash
# Bulk link Sprint 9 issues to project
for issue in {50..57}; do
  gh project item-add --owner oviney \
    --project-number 1 \
    --url https://github.com/oviney/economist-agents/issues/$issue
done

# Verify linkage
gh project item-list --owner oviney --project-number 1 --format json
```

**Step 5: Configure Custom Views**
```bash
# View 1: Kanban (status-based lanes)
gh project view-create --owner oviney \
  --project-number 1 \
  --name "Sprint Kanban" \
  --layout "BOARD" \
  --group-by "Status"

# View 2: Table (sortable by priority/points)
gh project view-create --owner oviney \
  --project-number 1 \
  --name "Sprint Backlog" \
  --layout "TABLE" \
  --visible-fields "title,assignees,priority,story-points,status,sprint"

# View 3: Roadmap (sprint timeline)
gh project view-create --owner oviney \
  --project-number 1 \
  --name "Sprint Timeline" \
  --layout "ROADMAP" \
  --date-field "Sprint"
```

**Step 6: Implement Burndown Chart Generation**

Create `scripts/generate_burndown.py`:
```python
#!/usr/bin/env python3
"""Generate sprint burndown chart from GitHub Projects API data."""

import os
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import requests


class BurndownGenerator:
    def __init__(self, owner: str, project_number: int, sprint: int):
        self.owner = owner
        self.project_number = project_number
        self.sprint = sprint
        self.token = os.environ.get("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"
        
    def fetch_sprint_data(self) -> list:
        """Fetch sprint issue data from GitHub GraphQL API."""
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              items(first: 100) {
                nodes {
                  fieldValues(first: 10) {
                    nodes {
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field {
                          ... on ProjectV2Field {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldNumberValue {
                        number
                        field {
                          ... on ProjectV2Field {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field {
                          ... on ProjectV2SingleSelectField {
                            name
                          }
                        }
                      }
                    }
                  }
                  content {
                    ... on Issue {
                      number
                      title
                      state
                      closedAt
                      createdAt
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"owner": self.owner, "number": self.project_number}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            self.api_url,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        data = response.json()
        return data["data"]["user"]["projectV2"]["items"]["nodes"]
    
    def calculate_burndown(self, sprint_start: str, sprint_end: str) -> dict:
        """Calculate daily remaining points for burndown chart."""
        items = self.fetch_sprint_data()
        
        # Extract story points and completion dates
        total_points = 0
        completed_by_date = {}  # {date: points_completed}
        
        for item in items:
            # Parse custom fields
            story_points = 0
            sprint_field = None
            
            for field_value in item["fieldValues"]["nodes"]:
                field_name = field_value.get("field", {}).get("name")
                
                if field_name == "Story Points":
                    story_points = field_value.get("number", 0)
                elif field_name == "Sprint":
                    sprint_field = field_value.get("name")
            
            # Filter to current sprint
            if sprint_field != f"Sprint {self.sprint}":
                continue
            
            total_points += story_points
            
            # Track completion date
            content = item.get("content", {})
            if content.get("state") == "CLOSED":
                closed_at = content.get("closedAt", "").split("T")[0]
                completed_by_date[closed_at] = (
                    completed_by_date.get(closed_at, 0) + story_points
                )
        
        # Generate daily burndown
        start = datetime.fromisoformat(sprint_start)
        end = datetime.fromisoformat(sprint_end)
        
        burndown = []
        remaining = total_points
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # Subtract completed points
            completed = completed_by_date.get(date_str, 0)
            remaining -= completed
            
            burndown.append({
                "date": date_str,
                "remaining": max(0, remaining),
                "completed": total_points - remaining,
                "ideal": total_points * (1 - (current - start).days / (end - start).days),
            })
            
            current += timedelta(days=1)
        
        return {
            "total_points": total_points,
            "burndown": burndown,
        }
    
    def generate_chart(self, burndown_data: dict, output_path: str):
        """Generate burndown chart visualization."""
        data = burndown_data["burndown"]
        
        dates = [d["date"] for d in data]
        remaining = [d["remaining"] for d in data]
        ideal = [d["ideal"] for d in data]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, remaining, label="Actual", marker="o", linewidth=2, color="#17648d")
        plt.plot(dates, ideal, label="Ideal", linestyle="--", linewidth=2, color="#888888")
        
        plt.title(f"Sprint {self.sprint} Burndown Chart", fontsize=16, fontweight="bold")
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Story Points Remaining", fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=150, facecolor="white")
        print(f"✅ Burndown chart saved to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sprint burndown chart")
    parser.add_argument("--sprint", type=int, required=True, help="Sprint number")
    parser.add_argument("--output", default="output/burndown.png", help="Output file path")
    parser.add_argument("--start", required=True, help="Sprint start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="Sprint end date (YYYY-MM-DD)")
    parser.add_argument("--owner", default="oviney", help="GitHub owner")
    parser.add_argument("--project", type=int, default=1, help="Project number")
    
    args = parser.parse_args()
    
    generator = BurndownGenerator(args.owner, args.project, args.sprint)
    burndown_data = generator.calculate_burndown(args.start, args.end)
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    generator.generate_chart(burndown_data, args.output)
    
    print(f"Total Points: {burndown_data['total_points']}")
    print(f"Remaining: {burndown_data['burndown'][-1]['remaining']}")


if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Generate Sprint 10 burndown chart
python3 scripts/generate_burndown.py \
  --sprint 10 \
  --start 2026-01-06 \
  --end 2026-01-17 \
  --output output/sprint-10-burndown.png
```

**Step 7: Implement Velocity Tracking**

Create `scripts/generate_velocity.py`:
```python
#!/usr/bin/env python3
"""Generate velocity tracking chart from sprint history."""

import matplotlib.pyplot as plt
from pathlib import Path


class VelocityTracker:
    def __init__(self, sprint_tracker_path: str = "skills/sprint_tracker.json"):
        self.tracker_path = sprint_tracker_path
    
    def calculate_velocity(self, sprint_range: tuple[int, int]) -> list:
        """Calculate velocity for sprint range."""
        import json
        
        with open(self.tracker_path) as f:
            tracker = json.load(f)
        
        velocity_data = []
        
        for sprint_num in range(sprint_range[0], sprint_range[1] + 1):
            sprint_key = f"sprint_{sprint_num}"
            
            if sprint_key not in tracker:
                continue
            
            sprint = tracker[sprint_key]
            
            # Calculate completed story points
            completed_points = sum(
                story.get("story_points", 0)
                for story in sprint.get("stories", [])
                if story.get("status") == "complete"
            )
            
            velocity_data.append({
                "sprint": sprint_num,
                "completed_points": completed_points,
                "planned_points": sprint.get("capacity", 0),
                "completion_rate": (
                    completed_points / sprint.get("capacity", 1) * 100
                    if sprint.get("capacity") else 0
                ),
            })
        
        return velocity_data
    
    def generate_chart(self, velocity_data: list, output_path: str):
        """Generate velocity chart visualization."""
        sprints = [d["sprint"] for d in velocity_data]
        completed = [d["completed_points"] for d in velocity_data]
        planned = [d["planned_points"] for d in velocity_data]
        
        # Calculate rolling average (last 3 sprints)
        rolling_avg = []
        for i in range(len(completed)):
            start_idx = max(0, i - 2)
            avg = sum(completed[start_idx:i+1]) / (i - start_idx + 1)
            rolling_avg.append(avg)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = range(len(sprints))
        ax.bar(x, completed, label="Completed", alpha=0.7, color="#17648d")
        ax.plot(x, planned, label="Planned", marker="o", linestyle="--", color="#888888")
        ax.plot(x, rolling_avg, label="3-Sprint Avg", marker="s", linewidth=2, color="#e3120b")
        
        ax.set_xlabel("Sprint", fontsize=12)
        ax.set_ylabel("Story Points", fontsize=12)
        ax.set_title("Sprint Velocity Tracking", fontsize=16, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"S{s}" for s in sprints])
        ax.legend(fontsize=10)
        ax.grid(True, axis="y", alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor="white")
        print(f"✅ Velocity chart saved to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate velocity tracking chart")
    parser.add_argument("--sprints", required=True, help="Sprint range (e.g., 6-10)")
    parser.add_argument("--output", default="output/velocity.png", help="Output file path")
    
    args = parser.parse_args()
    
    sprint_range = tuple(map(int, args.sprints.split("-")))
    
    tracker = VelocityTracker()
    velocity_data = tracker.calculate_velocity(sprint_range)
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    tracker.generate_chart(velocity_data, args.output)
    
    # Print summary
    avg_velocity = sum(d["completed_points"] for d in velocity_data) / len(velocity_data)
    print(f"Average Velocity: {avg_velocity:.1f} points/sprint")


if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Generate velocity chart for Sprints 6-10
python3 scripts/generate_velocity.py --sprints 6-10 --output output/velocity.png
```

**Step 8: Implement Automated Hygiene**

Create `scripts/project_hygiene.py`:
```python
#!/usr/bin/env python3
"""Automated GitHub project hygiene checks and cleanup."""

import os
from datetime import datetime, timedelta

import requests


class ProjectHygiene:
    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.token = os.environ.get("GITHUB_TOKEN")
        self.api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    def get_stale_issues(self, threshold_days: int = 90) -> list:
        """Find issues with no activity for N days."""
        threshold = datetime.now() - timedelta(days=threshold_days)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.api_url}/issues",
            params={"state": "open", "per_page": 100},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        issues = response.json()
        
        stale = []
        for issue in issues:
            updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
            
            if updated_at < threshold:
                days_stale = (datetime.now() - updated_at.replace(tzinfo=None)).days
                stale.append({
                    "number": issue["number"],
                    "title": issue["title"],
                    "updated_at": issue["updated_at"],
                    "days_stale": days_stale,
                    "url": issue["html_url"],
                })
        
        return stale
    
    def close_stale_issues(self, dry_run: bool = True):
        """Close stale issues (>90 days no activity)."""
        stale = self.get_stale_issues(threshold_days=90)
        
        print(f"Found {len(stale)} stale issues (>90 days)")
        
        if dry_run:
            print("\n🔍 DRY RUN - Would close:")
            for issue in stale:
                print(f"  #{issue['number']}: {issue['title']} ({issue['days_stale']} days)")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        for issue in stale:
            print(f"Closing #{issue['number']}: {issue['title']}")
            
            # Add comment before closing
            comment_url = f"{self.api_url}/issues/{issue['number']}/comments"
            requests.post(
                comment_url,
                json={"body": f"Auto-closing due to {issue['days_stale']} days of inactivity."},
                headers=headers,
                timeout=30,
            )
            
            # Close issue
            issue_url = f"{self.api_url}/issues/{issue['number']}"
            requests.patch(
                issue_url,
                json={"state": "closed"},
                headers=headers,
                timeout=30,
            )
    
    def check_priority_drift(self) -> list:
        """Find P0 issues older than P2/P3 issues."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.api_url}/issues",
            params={"state": "open", "per_page": 100},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        issues = response.json()
        
        # Group by priority
        by_priority = {"p0": [], "p1": [], "p2": [], "p3": []}
        
        for issue in issues:
            labels = [label["name"] for label in issue.get("labels", [])]
            
            for priority in ["p0", "p1", "p2", "p3"]:
                if priority in labels:
                    by_priority[priority].append({
                        "number": issue["number"],
                        "title": issue["title"],
                        "created_at": datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")),
                    })
        
        # Find P0 older than P2/P3
        drift = []
        
        for p0_issue in by_priority["p0"]:
            for p2_issue in by_priority["p2"] + by_priority["p3"]:
                if p0_issue["created_at"] < p2_issue["created_at"]:
                    days_diff = (p2_issue["created_at"] - p0_issue["created_at"]).days
                    
                    if days_diff > 14:  # 2+ weeks
                        drift.append({
                            "p0_number": p0_issue["number"],
                            "p0_title": p0_issue["title"],
                            "newer_priority": "P2/P3",
                            "days_older": days_diff,
                        })
        
        return drift
    
    def generate_health_report(self, sprint: int) -> dict:
        """Generate sprint health report."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.api_url}/issues",
            params={"state": "open", "labels": f"sprint-{sprint}", "per_page": 100},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        issues = response.json()
        
        # Calculate metrics
        total = len(issues)
        by_status = {}
        by_priority = {}
        total_points = 0
        
        for issue in issues:
            labels = [label["name"] for label in issue.get("labels", [])]
            
            # Status
            for label in labels:
                if label in ["status:not-started", "status:in-progress", "status:complete"]:
                    status = label.split(":")[1]
                    by_status[status] = by_status.get(status, 0) + 1
            
            # Priority
            for label in labels:
                if label in ["p0", "p1", "p2", "p3"]:
                    by_priority[label] = by_priority.get(label, 0) + 1
            
            # Story points
            for label in labels:
                if label.startswith("points:"):
                    points = int(label.split(":")[1])
                    total_points += points
        
        return {
            "sprint": sprint,
            "total_issues": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "total_points": total_points,
            "stale_count": len(self.get_stale_issues(threshold_days=30)),
            "priority_drift": len(self.check_priority_drift()),
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub project hygiene automation")
    parser.add_argument("--close-stale", action="store_true", help="Close stale issues")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--threshold", type=int, default=90, help="Stale threshold (days)")
    parser.add_argument("--health-report", action="store_true", help="Generate health report")
    parser.add_argument("--sprint", type=int, help="Sprint number for health report")
    parser.add_argument("--owner", default="oviney", help="GitHub owner")
    parser.add_argument("--repo", default="economist-agents", help="GitHub repo")
    
    args = parser.parse_args()
    
    hygiene = ProjectHygiene(args.owner, args.repo)
    
    if args.close_stale:
        hygiene.close_stale_issues(dry_run=args.dry_run)
    
    if args.health_report:
        if not args.sprint:
            print("Error: --sprint required for health report")
            return
        
        report = hygiene.generate_health_report(args.sprint)
        
        print(f"\n📊 Sprint {args.sprint} Health Report")
        print(f"Total Issues: {report['total_issues']}")
        print(f"Total Points: {report['total_points']}")
        print(f"\nStatus Breakdown:")
        for status, count in report['by_status'].items():
            print(f"  {status}: {count}")
        print(f"\nPriority Breakdown:")
        for priority, count in report['by_priority'].items():
            print(f"  {priority.upper()}: {count}")
        print(f"\nHygiene Alerts:")
        print(f"  Stale Issues (>30 days): {report['stale_count']}")
        print(f"  Priority Drift: {report['priority_drift']}")


if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Check for stale issues (dry run)
python3 scripts/project_hygiene.py --close-stale --dry-run --threshold 90

# Generate Sprint 10 health report
python3 scripts/project_hygiene.py --health-report --sprint 10
```

#### Quality Gates

**Before Sprint Start**:
- ✅ GitHub token has 'project' scope (gh auth status)
- ✅ Project Board created with sprint milestone
- ✅ Custom fields configured (story-points, sprint, priority, owner)
- ✅ All sprint issues linked to project
- ✅ Kanban view configured with backlog

**During Sprint**:
- ✅ Burndown chart updates daily (automated or manual)
- ✅ Project Board status synced with sprint_tracker.json
- ✅ Stale issues flagged (>30 days no update)
- ✅ Priority drift checked (P0 older than P2)

**End of Sprint**:
- ✅ Final burndown chart generated and archived
- ✅ Velocity calculated and added to history
- ✅ Sprint health report generated
- ✅ Project Board cleaned up (closed issues removed)

---

### 2. CI/CD Infrastructure Maintenance

#### Build Health Monitoring

**Daily Tasks**:
```bash
# Check CI status
python3 scripts/ci_health_check.py --detailed

# Expected output:
# ✅ CI/CD Health: GREEN
# - Workflows: 4/4 passing
# - Test Pass Rate: 92.3% (348/377)
# - Coverage: 52%
# - Build Time: 4m 32s
```

**Red Build Response** (P0):
```bash
# 1. Diagnose failure
python3 scripts/ci_health_check.py --diagnose

# 2. Check logs
gh run list --limit 5
gh run view <run-id> --log-failed

# 3. Fix locally
make test-all
make lint
make type-check

# 4. Commit fix
git commit -m "CI: Fix failing tests in test_editor_agent.py"
```

#### Test Coverage Tracking

```bash
# Generate coverage report
pytest --cov=scripts --cov=agents --cov-report=html

# Update coverage badge
python3 scripts/update_badges.py --coverage

# Target: >80% coverage
```

#### Security Scanning

```bash
# Run Bandit security scan
bandit -r scripts/ -f json -o bandit-report.json

# Critical vulnerabilities = P0 fix
# High/Medium = review and schedule fix
```

---

### 3. Infrastructure as Code Management

#### Python Environment Management

**Environment Configuration**:
```bash
# Pin Python version
echo "3.13" > .python-version

# Update dependencies
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt

# Sync environment
pip-sync requirements.txt requirements-dev.txt
```

**Linting & Type Checking**:
```bash
# Run ruff linter
ruff check . --fix

# Run mypy type checker
mypy scripts/ agents/ --ignore-missing-imports

# Configuration files: ruff.toml, mypy.ini
```

#### Makefile Targets

```makefile
# Test targets
test: pytest tests/
test-all: pytest tests/ scripts/ -v
test-coverage: pytest --cov=scripts --cov=agents

# Quality targets
lint: ruff check . --fix
type-check: mypy scripts/ agents/
format: ruff format .

# CI targets
ci-check: lint type-check test-coverage
ci-fix: make lint && make test
```

---

## Collaboration Protocols

### With Scrum Master (@scrum-master)

**Scrum Master Requests**:
- "Generate Sprint 10 burndown chart"
- "Update velocity dashboard with Sprint 9 data"
- "Run hygiene report for Sprint 10"
- "Create GitHub Project Board for Sprint 11"

**DevOps Delivers**:
- Burndown chart PNG + embed in README
- Velocity graph PNG + rolling average calculation
- Health report with stale issues, priority drift alerts
- Project Board URL + custom view configurations

**Quality Gate**:
- All delivered artifacts must be production-ready (not placeholders)
- Data accuracy validated against sprint_tracker.json
- Charts include source attribution and timestamps
- Documentation includes usage examples

### With Quality Enforcer (@quality-enforcer)

**Quality Enforcer Requests**:
- "Fix red CI build" (P0)
- "Update test coverage badge"
- "Run security scan and report vulnerabilities"

**DevOps Delivers**:
- CI fix commit + validation that tests pass
- Updated badge in README with accurate coverage %
- Security scan report with severity categorization

**Escalation Protocol**:
- P0 red builds: Fix within 1 hour or escalate to human
- Critical security vulnerabilities: Report within 30 minutes

---

## Tools & Technology Stack

### GitHub API Clients

**REST API** (requests library):
- Issues CRUD operations
- Milestones management
- Labels management
- Webhook handling

**GraphQL API** (requests + custom queries):
- Projects v2 queries (items, fields, views)
- Custom field mutations
- Bulk data fetching
- Real-time updates

### Data Visualization

**Matplotlib**:
- Burndown charts (line plots)
- Velocity graphs (bar charts + line overlay)
- Sprint health dashboards (composite charts)

**Configuration**:
```python
# Economist-style chart configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 0.5

# Economist colors
NAVY = "#17648d"
BURGUNDY = "#843844"
RED_BAR = "#e3120b"
BG_COLOR = "#f1f0e9"
```

### Infrastructure Tools

**GitHub CLI (gh)**:
- Project management: `gh project create/edit/view`
- Issue operations: `gh issue list/create/close`
- Workflow management: `gh run list/view/rerun`

**Python Tools**:
- pytest: Testing framework
- ruff: Fast linter (replaces flake8, black, isort)
- mypy: Static type checking
- bandit: Security scanning
- coverage: Test coverage measurement

---

## Metrics & Reporting

### Infrastructure Health Metrics

**CI/CD Uptime**:
- Target: >99% green builds
- Calculation: (successful runs / total runs) × 100
- Alert threshold: <95%

**Build Time**:
- Target: <5 minutes
- Measurement: Average of last 10 runs
- Alert threshold: >7 minutes

**Test Pass Rate**:
- Target: >90%
- Current: 92.3% (348/377 tests)
- Alert threshold: <85%

**Security Score**:
- Target: 0 critical vulnerabilities
- Current: 2 medium (BUG-026, BUG-027)
- Alert threshold: Any critical

### Project Board Quality Metrics

**Issue Sync Accuracy**:
- Target: 100% GitHub ↔ sprint_tracker.json
- Validation: Bidirectional sync test
- Alert threshold: Any mismatch

**Stale Issue Count**:
- Target: <5 issues >90 days
- Weekly check: project_hygiene.py
- Alert threshold: >10 issues

**Sprint Burndown Variance**:
- Target: <10% from ideal burndown
- Calculation: |actual - ideal| / total_points
- Alert threshold: >20% variance

**Velocity Predictability**:
- Target: ±15% sprint-to-sprint
- Calculation: |current - rolling_avg| / rolling_avg
- Alert threshold: >30% deviation

### Automation Effectiveness

**Auto-Sync Success Rate**:
- Target: >95% successful syncs
- Failure handling: Retry 3x with exponential backoff
- Alert threshold: <90%

**Manual Intervention Frequency**:
- Target: <2 manual fixes per sprint
- Tracking: Count of manual GitHub operations
- Alert threshold: >5 per sprint

---

## Documentation & Training

### Quick Start Guide

**New Team Member Onboarding**:
1. Install GitHub CLI: `brew install gh`
2. Authenticate: `gh auth login`
3. Refresh token with project scope: `gh auth refresh -s project`
4. Clone repo: `git clone https://github.com/oviney/economist-agents`
5. Setup Python: `python3.13 -m venv .venv && source .venv/bin/activate`
6. Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
7. Run health check: `python3 scripts/ci_health_check.py`

### Common Tasks

**Generate Sprint Artifacts**:
```bash
# Daily: Capture burndown snapshot
python3 scripts/generate_burndown.py --sprint 10 \
  --start 2026-01-06 --end 2026-01-17 \
  --output output/sprint-10-burndown.png

# Weekly: Update velocity dashboard
python3 scripts/generate_velocity.py --sprints 6-10 \
  --output output/velocity.png

# End of sprint: Health report
python3 scripts/project_hygiene.py --health-report --sprint 10
```

**Fix CI Issues**:
```bash
# Check what failed
gh run list --limit 5
gh run view <run-id> --log-failed

# Run locally
make test-all

# Fix and commit
git commit -m "CI: Fix test_integration.py mock setup"
```

---

## Version History

**v1.0** (2026-01-03):
- Initial DevOps skills documentation
- GitHub Projects v2 implementation guide
- Burndown/velocity generation procedures
- Project hygiene automation
- CI/CD maintenance protocols
- Collaboration workflows with @scrum-master

**Sprint 10 Deliverables** (Target):
- GitHub Projects v2 board operational
- Burndown chart automated (daily refresh)
- Velocity tracking historical (5 sprints)
- Hygiene automation weekly (stale cleanup)
- Bidirectional sync validated

---

## References

- **Agent Definition**: .github/agents/devops.agent.md
- **Story 6 Baseline**: STORY_6_GITHUB_SYNC_COMPLETE.md
- **Sprint Tracker**: skills/sprint_tracker.json
- **GitHub API Docs**: https://docs.github.com/en/graphql/reference/objects#projectv2
- **Scrum Master Collaboration**: skills/scrum-master/SKILL.md § GitHub Projects Integration
