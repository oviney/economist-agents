# GitHub Reporting Quick Reference

Quick commands and workflows for common reporting tasks in GitHub.

## Table of Contents

1. [Daily Reports](#daily-reports)
2. [Sprint Reports](#sprint-reports)
3. [Team Metrics](#team-metrics)
4. [Quality Metrics](#quality-metrics)
5. [Custom Reports](#custom-reports)

---

## Daily Reports

### My Work Today

```bash
# Issues assigned to me
gh issue list --assignee @me --state open

# PRs I need to review
gh pr list --search "review-requested:@me"

# PRs I created
gh pr list --author @me --state open

# Issues I commented on
gh issue list --search "commenter:@me updated:>=$(date -d '1 day ago' +%Y-%m-%d)"
```

### Team Activity

```bash
# What was merged yesterday
gh pr list --search "merged:>=$(date -d '1 day ago' +%Y-%m-%d)" --state merged

# What was closed yesterday
gh issue list --search "closed:>=$(date -d '1 day ago' +%Y-%m-%d)" --state closed

# What's in progress
gh issue list --label "in-progress"

# What's blocked
gh issue list --label "blocked"
```

### Standup Report

```bash
# Generate standup report
cat << 'EOF' > standup.sh
#!/bin/bash
echo "## Standup Report - $(date +%Y-%m-%d)"
echo ""
echo "### Yesterday"
gh pr list --author @me --search "updated:>=$(date -d '1 day ago' +%Y-%m-%d)" --limit 5
echo ""
echo "### Today"
gh issue list --assignee @me --label "in-progress"
echo ""
echo "### Blockers"
gh issue list --assignee @me --label "blocked"
EOF
chmod +x standup.sh
./standup.sh
```

---

## Sprint Reports

### Sprint Status

```bash
# Sprint 9 overview
gh milestone view "Sprint 9"

# Sprint 9 open items
gh issue list --milestone "Sprint 9" --state open

# Sprint 9 closed items
gh issue list --milestone "Sprint 9" --state closed

# Sprint 9 completion rate
gh milestone view "Sprint 9" --json title,dueOn,state,description,issues | \
  jq -r '"\(.title): \(.issues.closed)/\(.issues.total) complete (\(.issues.closed * 100 / .issues.total)%)"'
```

### Burndown Data

```bash
# Generate burndown CSV
cat << 'EOF' > burndown.sh
#!/bin/bash
SPRINT="Sprint 9"
echo "date,remaining_points"
for day in {0..14}; do
  DATE=$(date -d "$day days ago" +%Y-%m-%d)
  REMAINING=$(gh issue list --milestone "$SPRINT" --state open --search "created:<$DATE" --json labels | \
    jq '[.[] | .labels[] | select(.name | startswith("points-")) | .name | split("-")[1] | tonumber] | add // 0')
  echo "$DATE,$REMAINING"
done
EOF
chmod +x burndown.sh
./burndown.sh > burndown.csv
```

### Sprint Retrospective Data

```bash
# Completed stories
gh issue list --milestone "Sprint 9" --state closed --json number,title,closedAt

# Incomplete stories
gh issue list --milestone "Sprint 9" --state open --json number,title,labels

# Blockers encountered
gh issue list --milestone "Sprint 9" --search "label:blocked" --json number,title,comments

# Export for retrospective
gh issue list --milestone "Sprint 9" --json number,title,state,labels,comments > sprint_9_retro.json
```

### Automated Sprint Report

```bash
# Generate comprehensive sprint report
python3 scripts/generate_sprint_report.py --sprint 9

# Export to file
python3 scripts/generate_sprint_report.py --sprint 9 --output reports/sprint_9_$(date +%Y%m%d).md

# Post to issue
python3 scripts/generate_sprint_report.py --sprint 9 | gh issue comment 123 --body-file -
```

---

## Team Metrics

### Velocity Tracking

```bash
# Last 6 sprints velocity
for sprint in {4..9}; do
  COMPLETED=$(gh issue list --milestone "Sprint $sprint" --state closed --json labels | \
    jq '[.[] | .labels[] | select(.name | startswith("points-")) | .name | split("-")[1] | tonumber] | add // 0')
  echo "Sprint $sprint: $COMPLETED points"
done
```

### Contributor Activity

```bash
# Commits per person (last 30 days)
gh api repos/oviney/economist-agents/stats/contributors | \
  jq -r '.[] | "\(.author.login): \(.total) commits"'

# PRs per person (last 30 days)
gh pr list --search "merged:>=$(date -d '30 days ago' +%Y-%m-%d)" --state merged --json author,number | \
  jq -r 'group_by(.author.login) | .[] | "\(.[0].author.login): \(length) PRs"'

# Reviews per person (last 30 days)
gh api repos/oviney/economist-agents/pulls --jq '[.[] | select(.merged_at > "$(date -d '30 days ago' +%Y-%m-%d)") | .requested_reviewers[].login] | group_by(.) | .[] | "\(.[0]): \(length) reviews"'
```

### Cycle Time Metrics

```bash
# PR cycle time (last 20 PRs)
gh pr list --state merged --limit 20 --json number,title,createdAt,mergedAt | \
  jq -r '.[] | "\(.number): \((.mergedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) seconds"'

# Average cycle time
gh pr list --state merged --limit 50 --json createdAt,mergedAt | \
  jq '[.[] | ((.mergedAt | fromdateiso8601) - (.createdAt | fromdateiso8601))] | add / length / 3600 | "Avg cycle time: \(.) hours"'

# Issue resolution time
gh issue list --state closed --limit 50 --json createdAt,closedAt | \
  jq '[.[] | ((.closedAt | fromdateiso8601) - (.createdAt | fromdateiso8601))] | add / length / 3600 | "Avg resolution: \(.) hours"'
```

### Code Review Stats

```bash
# Review turnaround time
gh pr list --state merged --limit 20 --json number,reviews | \
  jq -r '.[] | select(.reviews | length > 0) | "\(.number): \(.reviews[0].submittedAt)"'

# Reviewer workload
gh api repos/oviney/economist-agents/pulls | \
  jq -r '[.[] | .requested_reviewers[].login] | group_by(.) | .[] | "\(.[0]): \(length) pending reviews"'
```

---

## Quality Metrics

### Test Coverage Trends

```bash
# Collect coverage data from CI runs
gh run list --workflow=ci.yml --limit 10 --json conclusion,createdAt,displayTitle | \
  jq -r '.[] | "\(.createdAt): \(.conclusion)"'

# View latest coverage report
gh run view --log | grep -i "coverage"
```

### Bug Metrics

```bash
# Open bugs by priority
gh issue list --label bug --label P0-critical --state open
gh issue list --label bug --label P1-high --state open
gh issue list --label bug --label P2-medium --state open

# Bugs opened this week
gh issue list --label bug --search "created:>=$(date -d '7 days ago' +%Y-%m-%d)"

# Bugs closed this week
gh issue list --label bug --search "closed:>=$(date -d '7 days ago' +%Y-%m-%d)" --state closed

# Bug age (oldest open bugs)
gh issue list --label bug --state open --json number,title,createdAt | \
  jq -r 'sort_by(.createdAt) | .[] | "\(.number): \(.title) (opened \(.createdAt))"' | head -10
```

### Code Quality Gates

```bash
# CI success rate (last 20 runs)
gh run list --workflow=ci.yml --limit 20 --json conclusion | \
  jq '[.[] | .conclusion] | group_by(.) | .[] | "\(.[0]): \(length)"'

# Failed CI runs
gh run list --workflow=ci.yml --status failure --limit 10

# Latest quality score
cat quality_score.json | jq .
```

---

## Custom Reports

### Weekly Summary

```bash
# Generate weekly summary
cat << 'EOF' > weekly_report.sh
#!/bin/bash
WEEK_AGO=$(date -d '7 days ago' +%Y-%m-%d)

echo "# Weekly Summary - $(date +%Y-%m-%d)"
echo ""

echo "## 📊 Activity"
echo "- PRs merged: $(gh pr list --search "merged:>=$WEEK_AGO" --state merged | wc -l)"
echo "- Issues closed: $(gh issue list --search "closed:>=$WEEK_AGO" --state closed | wc -l)"
echo "- Issues opened: $(gh issue list --search "created:>=$WEEK_AGO" | wc -l)"
echo ""

echo "## 🎯 Top Contributors"
gh api repos/oviney/economist-agents/stats/contributors | \
  jq -r '.[] | "\(.author.login): \(.total) commits"' | head -5
echo ""

echo "## 🐛 Bug Status"
echo "- Open bugs: $(gh issue list --label bug --state open | wc -l)"
echo "- Bugs closed this week: $(gh issue list --label bug --search "closed:>=$WEEK_AGO" --state closed | wc -l)"
echo ""

echo "## 🚀 Next Week"
gh milestone view "Sprint 9" --json title,dueOn,issues | \
  jq -r '"Milestone: \(.title)\nDue: \(.dueOn)\nProgress: \(.issues.closed)/\(.issues.total) complete"'
EOF
chmod +x weekly_report.sh
./weekly_report.sh
```

### Custom Metrics Dashboard

```bash
# Generate comprehensive metrics
python3 scripts/github_metrics_dashboard.py

# 30-day window
python3 scripts/github_metrics_dashboard.py --days 30

# Export to file
python3 scripts/github_metrics_dashboard.py --days 30 --export reports/metrics_$(date +%Y%m%d).md

# View in browser (convert to HTML)
python3 scripts/github_metrics_dashboard.py | \
  pandoc -f markdown -t html -o metrics.html && \
  open metrics.html
```

### Sprint Comparison

```bash
# Compare last 3 sprints
for sprint in {7..9}; do
  echo "Sprint $sprint:"
  gh milestone view "Sprint $sprint" --json title,issues | \
    jq -r '"  Completed: \(.issues.closed)/\(.issues.total)"'
done
```

### Release Notes

```bash
# Generate release notes from milestone
gh issue list --milestone "Sprint 9" --state closed --json number,title,labels | \
  jq -r '.[] | "- \(.title) (#\(.number))"' > release_notes.md

# Group by type
gh issue list --milestone "Sprint 9" --state closed --json number,title,labels | \
  jq -r 'group_by(.labels[].name | select(. == "bug" or . == "enhancement")) | 
    .[] | "## \(.[0].labels[0].name | ascii_upcase)\n" + (.[] | "- \(.title) (#\(.number))") + "\n"'
```

---

## Automation Scripts

### Daily Metrics Collection

**File**: `.github/workflows/daily-metrics.yml`

```yaml
name: Daily Metrics Collection
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM daily
  workflow_dispatch:

jobs:
  collect-metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Sprint Report
        run: |
          python3 scripts/generate_sprint_report.py --sprint 9 \
            --output reports/daily_$(date +%Y%m%d).md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Generate Metrics Dashboard
        run: |
          python3 scripts/github_metrics_dashboard.py --days 7 \
            --export reports/metrics_$(date +%Y%m%d).md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit Reports
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add reports/
          git commit -m "Daily metrics: $(date +%Y-%m-%d)" || true
          git push
```

### Weekly Summary Email

**File**: `.github/workflows/weekly-summary.yml`

```yaml
name: Weekly Summary
on:
  schedule:
    - cron: '0 17 * * 5'  # Friday 5 PM
  workflow_dispatch:

jobs:
  summary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Summary
        id: summary
        run: |
          ./weekly_report.sh > summary.md
          echo "summary<<EOF" >> $GITHUB_OUTPUT
          cat summary.md >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      
      - name: Post to Discussion
        run: |
          gh api repos/oviney/economist-agents/discussions \
            -X POST \
            -f title="Weekly Summary - $(date +%Y-%m-%d)" \
            -f body="${{ steps.summary.outputs.summary }}" \
            -f category_id=12345
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Tips & Tricks

### Save Common Queries

```bash
# Add to ~/.bashrc or ~/.zshrc
alias gh-my-work="gh issue list --assignee @me --state open"
alias gh-my-prs="gh pr list --author @me --state open"
alias gh-review-needed="gh pr list --search 'review-requested:@me'"
alias gh-blocked="gh issue list --label blocked"
alias gh-sprint="gh milestone view 'Sprint 9'"
```

### Format Output

```bash
# Table format
gh issue list --json number,title,state --template '{{range .}}{{.number}} | {{.title}} | {{.state}}{{"\n"}}{{end}}'

# Custom format
gh pr list --json number,title,author --template '{{range .}}PR #{{.number}}: {{.title}} by @{{.author.login}}{{"\n"}}{{end}}'
```

### Export Data

```bash
# Export to CSV
gh issue list --json number,title,state,createdAt,closedAt | \
  jq -r '["number","title","state","created","closed"], (.[] | [.number, .title, .state, .createdAt, .closedAt]) | @csv'

# Export to JSON
gh issue list --json number,title,state,labels,assignees > issues.json

# Export to Markdown
gh issue list --json number,title,state | \
  jq -r '.[] | "- [\(.state)] #\(.number): \(.title)"'
```

---

## Resources

- **GitHub CLI Manual**: https://cli.github.com/manual/
- **GitHub API Docs**: https://docs.github.com/en/rest
- **GitHub GraphQL API**: https://docs.github.com/en/graphql
- **Skills Reference**: `skills/github-features/SKILL.md`
- **Sprint Management**: `skills/sprint-management/SKILL.md`

---

**Last Updated**: 2026-01-03
**Version**: 1.0
