# GitHub Features Tutorial

Step-by-step guide to using GitHub's native project tracking features.

## Prerequisites

```bash
# Install GitHub CLI
brew install gh  # macOS
# or follow: https://cli.github.com/

# Authenticate
gh auth login
```

---

## Tutorial 1: Setting Up Your First Project Board

### Step 1: Create a Project

**Via Web UI** (Recommended for first time):
1. Go to: https://github.com/oviney/economist-agents
2. Click **"Projects"** tab (top menu)
3. Click **"New project"** (green button)
4. Choose **"Board"** template
5. Name it: "Sprint 9 - Validation & Measurement"
6. Click **"Create project"**

**Via CLI**:
```bash
gh project create \
  --owner oviney \
  --title "Sprint 9 - Validation & Measurement" \
  --format board
```

### Step 2: Add Columns

Default columns are good:
- **📋 Todo** - Work not started
- **🏗️ In Progress** - Active development
- **✅ Done** - Completed

You can add more:
- **👀 Review** - In code review
- **🚫 Blocked** - Waiting on dependency

### Step 3: Add Issues to Project

**Via Web UI**:
1. Open your project board
2. Click **"+ Add item"** at bottom of column
3. Search for issue number (e.g., #123)
4. Click to add

**Via CLI**:
```bash
# Add issue #123 to project
gh project item-add 1 --owner oviney \
  --url https://github.com/oviney/economist-agents/issues/123
```

### Step 4: Set Up Automation

1. In project → Click ⚙️ **"Settings"** (top right)
2. Click **"Workflows"** in left sidebar
3. Add workflow: **"Auto-add to project"**
   - When: Issue opened
   - Filter: label:sprint-9
   - Then: Add to project → Todo column
4. Add workflow: **"Auto-move when closed"**
   - When: Issue closed
   - Then: Move to "Done" column

Now issues automatically flow through your board!

---

## Tutorial 2: Creating a Sprint Milestone

### Step 1: Create Milestone

**Via Web UI**:
1. Go to: https://github.com/oviney/economist-agents/issues
2. Click **"Milestones"** (top menu)
3. Click **"New milestone"**
4. Fill in:
   - **Title**: Sprint 9: Validation & Measurement
   - **Due date**: 2026-01-15
   - **Description**: 15 story points, focus on quality gates
5. Click **"Create milestone"**

**Via CLI**:
```bash
gh milestone create "Sprint 9: Validation & Measurement" \
  --description "15 story points - Quality gates and metrics" \
  --due-date 2026-01-15 \
  --repo oviney/economist-agents
```

### Step 2: Add Issues to Milestone

**Via Web UI**:
1. Open an issue
2. Right sidebar → **"Milestone"**
3. Select "Sprint 9: Validation & Measurement"
4. Repeat for all sprint issues

**Via CLI**:
```bash
# Add issue #123 to milestone
gh issue edit 123 --milestone "Sprint 9: Validation & Measurement"

# Bulk add (all issues with sprint-9 label)
gh issue list --label "sprint-9" --json number --jq '.[].number' | \
  while read issue; do
    gh issue edit $issue --milestone "Sprint 9: Validation & Measurement"
  done
```

### Step 3: View Milestone Progress

**Via Web UI**:
1. Go to: https://github.com/oviney/economist-agents/milestones
2. Click on "Sprint 9: Validation & Measurement"
3. See:
   - Progress bar (% complete)
   - Open/closed issues
   - Due date countdown

**Via CLI**:
```bash
gh milestone view "Sprint 9: Validation & Measurement"
```

**Output**:
```
Sprint 9: Validation & Measurement
Due: 2026-01-15 (12 days from now)
15 story points - Quality gates and metrics

Progress: 40% complete
█████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░

12 open, 8 closed (20 total)
```

---

## Tutorial 3: Generating Your First Report

### Sprint Status Report

```bash
# Generate report
python3 scripts/generate_sprint_report.py --sprint 9

# Save to file
python3 scripts/generate_sprint_report.py --sprint 9 \
  --output reports/sprint_9_status.md

# View in browser
python3 scripts/generate_sprint_report.py --sprint 9 | \
  gh issue create --title "Sprint 9 Status" --body-file -
```

**What you get**:
- ✅ Story completion rate
- 📊 Burndown data
- 🚨 Critical items (P0)
- 🔥 High priority items (P1)
- 🚫 Blocked items
- ✅ Recently completed
- 📈 Recommendations

### Metrics Dashboard

```bash
# Last 30 days metrics
python3 scripts/github_metrics_dashboard.py --days 30

# Save to file
python3 scripts/github_metrics_dashboard.py --days 30 \
  --export reports/metrics_dashboard.md
```

**What you get**:
- 📈 PR cycle time metrics
- 📋 Issue resolution metrics
- 👥 Contributor activity
- 🎯 Insights and recommendations

---

## Tutorial 4: Using GitHub Insights

### Pulse (Weekly Summary)

1. Go to: https://github.com/oviney/economist-agents/pulse
2. See:
   - PRs opened/merged/closed this week
   - Issues opened/closed this week
   - New contributors
   - Commits this week

**Use case**: Weekly standup report

### Contributors Graph

1. Go to: https://github.com/oviney/economist-agents/graphs/contributors
2. See:
   - Commits over time per person (line chart)
   - Additions/deletions per person (bar chart)
   - Activity heatmap

**Use case**: Team velocity analysis

### Code Frequency

1. Go to: https://github.com/oviney/economist-agents/graphs/code-frequency
2. See:
   - Additions (green bars)
   - Deletions (red bars)
   - Net change over time

**Use case**: Development pace tracking

### Network Graph

1. Go to: https://github.com/oviney/economist-agents/network
2. See:
   - All branches
   - Merge points
   - Parallel development

**Use case**: Understanding branch strategy

---

## Tutorial 5: Power User CLI Commands

### My Daily Workflow

```bash
# 1. What do I need to work on today?
gh issue list --assignee @me --state open

# 2. Any PRs need my review?
gh pr list --search "review-requested:@me"

# 3. What's blocked?
gh issue list --label blocked

# 4. Quick standup summary
cat << 'EOF' > ~/bin/standup
#!/bin/bash
echo "🎯 My Open Issues:"
gh issue list --assignee @me --state open --limit 5
echo ""
echo "👀 PRs Needing Review:"
gh pr list --search "review-requested:@me" --limit 5
echo ""
echo "🚫 Blocked Items:"
gh issue list --label blocked --limit 5
EOF
chmod +x ~/bin/standup
standup
```

### Sprint Management

```bash
# View sprint overview
gh milestone view "Sprint 9"

# Add story to sprint
gh issue edit 123 --milestone "Sprint 9"

# Close story
gh issue close 123 --comment "Completed in PR #456"

# Generate sprint report
python3 scripts/generate_sprint_report.py --sprint 9 | less
```

### Team Metrics

```bash
# PRs merged this week
gh pr list --search "merged:>=$(date -d '7 days ago' +%Y-%m-%d)" --state merged

# Issues closed this week
gh issue list --search "closed:>=$(date -d '7 days ago' +%Y-%m-%d)" --state closed

# Who's been most active?
gh api repos/oviney/economist-agents/stats/contributors | \
  jq -r '.[] | "\(.author.login): \(.total) commits"' | sort -t: -k2 -rn | head -5
```

---

## Tutorial 6: Creating Custom Reports

### Weekly Team Report

Create `~/bin/weekly-report`:
```bash
#!/bin/bash

WEEK_AGO=$(date -d '7 days ago' +%Y-%m-%d)
REPO="oviney/economist-agents"

echo "# Weekly Report - $(date +%Y-%m-%d)"
echo ""

echo "## 📊 Activity This Week"
echo ""
PR_COUNT=$(gh pr list --search "merged:>=$WEEK_AGO" --state merged --repo $REPO | wc -l)
ISSUE_CLOSED=$(gh issue list --search "closed:>=$WEEK_AGO" --state closed --repo $REPO | wc -l)
ISSUE_OPENED=$(gh issue list --search "created:>=$WEEK_AGO" --repo $REPO | wc -l)

echo "- **PRs Merged**: $PR_COUNT"
echo "- **Issues Closed**: $ISSUE_CLOSED"
echo "- **Issues Opened**: $ISSUE_OPENED"
echo ""

echo "## 🎯 Top Contributors"
echo ""
gh api repos/$REPO/stats/contributors | \
  jq -r '.[] | "- **\(.author.login)**: \(.total) commits"' | head -5
echo ""

echo "## 🐛 Bug Status"
echo ""
OPEN_BUGS=$(gh issue list --label bug --state open --repo $REPO | wc -l)
CLOSED_BUGS=$(gh issue list --label bug --search "closed:>=$WEEK_AGO" --state closed --repo $REPO | wc -l)
echo "- **Open Bugs**: $OPEN_BUGS"
echo "- **Bugs Closed This Week**: $CLOSED_BUGS"
echo ""

echo "## 🚀 Next Week"
echo ""
gh milestone view "Sprint 9" --repo $REPO 2>/dev/null || echo "*No active milestone*"
```

Make executable:
```bash
chmod +x ~/bin/weekly-report
```

Run it:
```bash
weekly-report
# or
weekly-report > reports/week_$(date +%Y%m%d).md
```

### Burndown Chart Data

Create `~/bin/burndown-data`:
```bash
#!/bin/bash

MILESTONE="Sprint 9"
REPO="oviney/economist-agents"

echo "date,remaining_points,completed_points"

# Get all issues in milestone
ISSUES=$(gh issue list --milestone "$MILESTONE" --state all --json number,labels,closedAt --repo $REPO)

# For each day of sprint
for day in {14..0}; do
  DATE=$(date -d "$day days ago" +%Y-%m-%d)
  
  # Count points for issues closed after this date
  REMAINING=$(echo "$ISSUES" | jq --arg date "$DATE" '
    [.[] | 
      select(
        (.closedAt == null) or 
        (.closedAt > $date)
      ) | 
      .labels[] | 
      select(.name | startswith("points-")) | 
      .name | 
      split("-")[1] | 
      tonumber
    ] | add // 0
  ')
  
  # Count completed points
  TOTAL=$(echo "$ISSUES" | jq '
    [.[] | 
      .labels[] | 
      select(.name | startswith("points-")) | 
      .name | 
      split("-")[1] | 
      tonumber
    ] | add // 0
  ')
  
  COMPLETED=$((TOTAL - REMAINING))
  
  echo "$DATE,$REMAINING,$COMPLETED"
done
```

Make executable and run:
```bash
chmod +x ~/bin/burndown-data
burndown-data > burndown.csv

# View in spreadsheet
open burndown.csv
# or import into Google Sheets
```

---

## Tutorial 7: Automation with GitHub Actions

### Daily Sprint Report

Create `.github/workflows/daily-sprint-report.yml`:
```yaml
name: Daily Sprint Report

on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install PyGithub
      
      - name: Generate Sprint Report
        run: |
          python3 scripts/generate_sprint_report.py --sprint 9 \
            --output reports/daily_$(date +%Y%m%d).md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit Report
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add reports/
          git commit -m "Daily sprint report: $(date +%Y-%m-%d)" || exit 0
          git push
```

### Weekly Metrics Dashboard

Create `.github/workflows/weekly-metrics.yml`:
```yaml
name: Weekly Metrics

on:
  schedule:
    - cron: '0 17 * * 5'  # Friday 5 PM
  workflow_dispatch:

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install PyGithub matplotlib
      
      - name: Generate Metrics Dashboard
        run: |
          python3 scripts/github_metrics_dashboard.py --days 7 \
            --export reports/metrics_$(date +%Y%m%d).md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit Report
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add reports/
          git commit -m "Weekly metrics: $(date +%Y-%m-%d)" || exit 0
          git push
```

---

## Common Questions

### Q: How do I see only my work?

```bash
gh issue list --assignee @me --state open
gh pr list --author @me --state open
```

### Q: How do I generate a burndown chart?

Use the `burndown-data` script from Tutorial 6, then:
```bash
burndown-data > burndown.csv
# Import into Google Sheets or Excel
# Create line chart with "date" on X-axis and "remaining_points" on Y-axis
```

### Q: How do I track velocity across sprints?

```bash
for sprint in {7..9}; do
  POINTS=$(gh issue list --milestone "Sprint $sprint" --state closed --json labels --jq '
    [.[] | .labels[] | select(.name | startswith("points-")) | .name | split("-")[1] | tonumber] | add // 0
  ')
  echo "Sprint $sprint: $POINTS points"
done
```

### Q: How do I find bottlenecks?

```bash
# Long-running PRs
gh pr list --state open --json number,title,createdAt | \
  jq -r '.[] | select((.createdAt | fromdateiso8601) < (now - 604800)) | "#\(.number): \(.title)"'

# Old open issues
gh issue list --state open --json number,title,createdAt | \
  jq -r '.[] | select((.createdAt | fromdateiso8601) < (now - 2592000)) | "#\(.number): \(.title)"'

# Review bottlenecks
gh pr list --search "review:required" --json number,title,reviewDecision
```

---

## Next Steps

1. **Set up your first project board** (Tutorial 1)
2. **Create milestone for current sprint** (Tutorial 2)
3. **Generate your first report** (Tutorial 3)
4. **Add aliases to your shell** (Tutorial 5)
5. **Set up automation** (Tutorial 7)

---

## Resources

- **Complete Skills Guide**: [skills/github-features/SKILL.md](../skills/github-features/SKILL.md)
- **Quick Reference**: [GITHUB_REPORTING_QUICK_REFERENCE.md](GITHUB_REPORTING_QUICK_REFERENCE.md)
- **GitHub CLI Manual**: https://cli.github.com/manual/
- **GitHub API Docs**: https://docs.github.com/en/rest

---

**Last Updated**: 2026-01-03
**Version**: 1.0
