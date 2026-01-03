# GitHub Native Features Skill

## Overview
Complete guide to GitHub's **web-based** project tracking, reporting, and visualization features. All reporting is done through GitHub's online interface - **no local files or scripts needed**.

## Version
**2.0** - Focus on web UI and live reporting (no static files)

## Why GitHub Web Interface?

**Benefits**:
- ✅ **Always Live**: Real-time updates, no stale reports
- ✅ **Zero Maintenance**: No scripts to maintain or files to commit
- ✅ **Accessible Anywhere**: View from any browser, any device
- ✅ **Team Collaboration**: Everyone sees the same live data
- ✅ **Built-in Visualizations**: Charts and graphs update automatically
- ✅ **Free**: Included with GitHub (no setup required)

**What You Get**:
1. **Project Boards** (Web UI) - Live Kanban, table, roadmap views
2. **Insights Dashboard** (Web UI) - Real-time contribution graphs, code frequency
3. **Issues Dashboard** (Web UI) - Live filtering, sorting, searching
4. **Pulse Reports** (Web UI) - Weekly activity summaries
5. **Milestones** (Web UI) - Live progress bars and burndown tracking
6. **PR Insights** (Web UI) - Review statistics and cycle time trends

---

## 1. GitHub Projects (v2) - Live Project Dashboard

### What is GitHub Projects v2?
**Web-based** project management built directly into GitHub. Access at:
```
https://github.com/users/YOUR_USERNAME/projects
https://github.com/orgs/YOUR_ORG/projects  
https://github.com/YOUR_USERNAME/YOUR_REPO/projects
```

### Key Features - All Live in Browser

#### A. Board View (Live Kanban)
**URL Format**: `https://github.com/users/oviney/projects/1/views/1`

Visual workflow with **real-time updates**:
- 📋 **Backlog** - Prioritized work (auto-populated from issues)
- 🏗️ **In Progress** - Active development (updates when PR opens)
- 👀 **In Review** - Pull requests under review (auto-tracked)
- ✅ **Done** - Completed work (auto-moves when PR merges)

**Key Benefits**:
- Drag-and-drop between columns
- Auto-updates when issues/PRs change state
- Filter by assignee, label, sprint
- Color-coded by priority
- Card preview on hover

**How to Access**:
1. Go to repository → **Projects** tab
2. Click your project name
3. Default view is Board
4. Changes are instant (no refresh needed)

#### B. Table View (Live Database)
**URL Format**: `https://github.com/users/oviney/projects/1/views/2`

Spreadsheet-like view with **live filtering and sorting**:

**Built-in Fields** (always current):
- **Status**: Automatically syncs with issue state
- **Assignee**: Live from issue assignments  
- **Labels**: Updates when labels change
- **Linked PRs**: Shows connected pull requests
- **Milestone**: Live milestone progress
- **Last Updated**: Real-time timestamp

**Custom Fields** (you can add):
- **Priority**: Dropdown (P0, P1, P2, P3)
- **Sprint**: Dropdown (Sprint 7, 8, 9...)
- **Story Points**: Number (1, 2, 3, 5, 8, 13)
- **Due Date**: Date picker
- **Team**: Dropdown (Frontend, Backend, QA)

**Live Filtering** (instantly updates view):
```
Examples you can type in filter box:
- status:"In Progress" assignee:@me
- priority:P0 sprint:"Sprint 9"
- label:bug status:open
- no:assignee status:open  (unassigned items)
```

**Live Sorting**:
- Click any column header to sort
- Multi-sort: Shift+click multiple columns
- Priority descending → Due date ascending

**How to Access**:
1. Open your project
2. Click **"Table"** view (top tabs)
3. Use filter box to refine
4. Click column headers to sort

#### C. Roadmap View (Live Timeline)
**URL Format**: `https://github.com/users/oviney/projects/1/views/3`

Visual timeline that **updates in real-time**:

**Features**:
- Gantt-chart style layout
- Drag to adjust dates (saves automatically)
- Zoom: Day, week, month, quarter views
- Dependencies shown as arrows
- Milestone markers
- Today indicator line

**Use Cases**:
- Sprint planning: See all work for next 2 weeks
- Release planning: Map features to quarters
- Dependency tracking: Visualize blocking relationships
- Capacity planning: See team workload

**How to Access**:
1. Open your project
2. Click **"Roadmap"** view (top tabs)
3. Set date range with zoom controls
4. Drag items to adjust timeline

### Setting Up a Project (Web UI Only)

**Step-by-step**:
1. Go to: `https://github.com/oviney/economist-agents`
2. Click **"Projects"** tab
3. Click **"Link a project"** → **"New project"**
4. Choose template:
   - **Board**: Best for sprints (Kanban workflow)
   - **Table**: Best for backlog management (database view)
   - **Roadmap**: Best for release planning (timeline)
5. Customize:
   - Add custom fields (Priority, Sprint, Points)
   - Set up views (Board, Table, Roadmap)
   - Configure automations (auto-add, auto-move)

**No code, no CLI, no files** - all done in browser!

### Project Automation (Built-in Workflows)

**Access**: Project → ⚙️ **Settings** → **Workflows**

**Built-in Automations** (no code required):

1. **Auto-add to project**
   - When: Issue opened
   - Filter: `label:sprint-9`
   - Action: Add to project → "Backlog" column
   
2. **Auto-set status**
   - When: PR opened
   - Action: Set status → "In Progress"
   
3. **Auto-complete**
   - When: Issue closed
   - Action: Set status → "Done"
   
4. **Auto-archive**
   - When: Status is "Done" for 30 days
   - Action: Archive item

**Result**: Board updates automatically as work happens!

---

## 2. GitHub Insights - Live Analytics Dashboard

### Repository Insights Tab

**Access**: `https://github.com/oviney/economist-agents/pulse` (and other insight pages)

All reports are **live** and **automatically generated** - no setup required!

#### A. Pulse (Live Weekly Summary)
**URL**: `https://github.com/oviney/economist-agents/pulse`

**What it shows** (updated in real-time):
- Pull requests opened/merged/closed this week
- Issues opened/closed this week
- New contributors this week
- Commits by all contributors
- Unresolved conversations
- Most active contributors

**Use case**: Perfect for Monday standup or Friday retrospective

**Time Range Selection**:
- Period dropdown: Last 24 hours, 3 days, 1 week, 1 month
- Updates instantly when you change range

#### B. Contributors Graph (Live Activity)
**URL**: `https://github.com/oviney/economist-agents/graphs/contributors`

**What it shows** (real-time data):
- **Line chart**: Commits over time per person
- **Bar chart**: Total commits per person
- **Activity heatmap**: When people commit (by hour/day)
- **Additions/deletions**: Code change volume

**Interactive Features**:
- Click contributor to see their specific activity
- Hover over data points for exact numbers
- Zoom time range: 1 month, 3 months, 1 year, all time
- Toggle between different visualizations

**Use case**: Team velocity analysis, identify specialists

#### C. Code Frequency (Live Development Pace)
**URL**: `https://github.com/oviney/economist-agents/graphs/code-frequency`

**What it shows** (weekly updates):
- 📊 **Green bars**: Lines added each week
- 📊 **Red bars**: Lines deleted each week
- 📊 **Net change**: Overall code growth/shrinkage

**Use case**: 
- Sprint velocity: "We added 2,000 lines last sprint"
- Refactoring efforts: "We deleted 500 lines (good!)"
- Development pace: "Activity increasing/decreasing?"

#### D. Commit Activity (52-Week View)
**URL**: `https://github.com/oviney/economist-agents/graphs/commit-activity`

**What it shows** (weekly aggregation):
- Bar chart of commits per week
- 52-week rolling window
- Trend line showing velocity changes
- Hover for exact commit counts

**Use case**: Long-term velocity tracking, seasonal patterns

#### E. Network Graph (Branch Visualization)
**URL**: `https://github.com/oviney/economist-agents/network`

**What it shows** (live branch topology):
- All branches and their relationships
- Merge points and divergence
- Active forks
- Parallel development streams

**Interactive**:
- Zoom and pan
- Click commits to see details
- Hover branches for names
- Filter by date range

**Use case**: Understanding team branching strategy, finding long-running branches

#### F. Pull Request Insights (Beta)
**URL**: `https://github.com/oviney/economist-agents/pulls?q=is%3Apr` → **Insights** button (top right)

**What it shows** (if enabled):
- ⏱️ **Cycle time**: PR open → merge (median, p50, p95)
- 👀 **Review time**: First review turnaround
- 📈 **Merge rate**: PRs merged vs closed
- 🔄 **Reopened rate**: PRs that needed rework
- 👥 **Reviewer distribution**: Who reviews most

**Time controls**: Last 7 days, 30 days, 90 days, 1 year

**Use case**: Identify bottlenecks, optimize review process

### Dependency Graph (Security & Inventory)

**URL**: `https://github.com/oviney/economist-agents/network/dependencies`

**What it shows** (auto-detected from requirements.txt, package.json, etc.):
- 📦 All dependencies (tree view)
- 🔒 Security vulnerabilities (Dependabot alerts)
- 📊 Dependency count by language
- 🔗 Dependents (who uses this repo)

**Interactive**:
- Click package to see version
- Click vulnerability for CVE details
- View dependency graph (visual tree)

**Use case**: Security audits, understanding tech stack

---

## 3. Issues Dashboard - Live Work Tracking

### Issues List (Powerful Live Filtering)

**URL**: `https://github.com/oviney/economist-agents/issues`

**Built-in Filters** (click to apply):
- 👤 **Assigned to you**: See your work instantly
- 📝 **Created by you**: Track issues you opened  
- 💬 **Mentioning you**: Where you're mentioned
- 🔍 **Custom search**: Powerful query language

**Search Query Examples** (type in search box):
```
assignee:@me state:open
  → My open issues

label:P0-critical is:open
  → Critical items needing attention

is:open no:assignee label:sprint-9
  → Unassigned sprint work

is:issue is:closed closed:>2026-01-01
  → Issues closed this year

label:bug is:open sort:created-asc
  → Oldest open bugs first

author:@me is:closed
  → Issues I reported that are fixed
```

**Live Sorting Options**:
- Newest (default)
- Oldest  
- Most commented
- Least commented
- Recently updated
- Least recently updated
- Best match (for searches)

**Saved Searches**: Bookmark complex queries
```
https://github.com/oviney/economist-agents/issues?q=is%3Aopen+assignee%3A%40me+label%3AP0-critical

Bookmark as: "My Critical Work"
```

### Milestones - Live Sprint Tracking

**URL**: `https://github.com/oviney/economist-agents/milestones`

**What You See** (live data):
- 📊 Progress bar (% complete) - updates when issues close
- 🎯 Open/closed counts - real-time
- 📅 Due date - with countdown
- 📝 Description - sprint goals

**Click a Milestone** to see:
```
https://github.com/oviney/economist-agents/milestone/9
```

**Milestone View Shows**:
- All issues in this sprint/milestone
- Progress bar (visual completion %)
- Open vs closed counts  
- Days until due date
- Filter issues by label, assignee, etc.

**Create Milestone** (via web UI):
1. Go to Issues → Milestones
2. Click "New milestone"
3. Fill in:
   - Title: "Sprint 9: Validation & Measurement"
   - Due date: Pick from calendar
   - Description: Sprint goals
4. Click "Create milestone"

**Add Issues to Milestone**:
1. Open any issue
2. Right sidebar → "Milestone" dropdown
3. Select milestone
4. Auto-saves, progress bar updates instantly!

**Use case**: Live sprint burndown - watch progress bar fill as team closes issues

### Labels - Visual Categorization

**URL**: `https://github.com/oviney/economist-agents/labels`

**Standard Labels** (click to see all issues with that label):
- 🔴 `P0-critical` - Click → See all critical issues
- 🐛 `bug` - Click → See all bugs
- ✨ `enhancement` - Click → See all features
- 📚 `documentation` - Click → See all doc work

**Create Custom Labels**:
1. Go to Issues → Labels
2. Click "New label"
3. Choose:
   - Name: `sprint-9`
   - Description: "Sprint 9 work"
   - Color: Pick from palette
4. Use label on issues

**Pro Tip**: Use label colors for quick visual scanning
- Red: Urgent/critical
- Orange: High priority
- Yellow: Medium priority
- Green: Low priority
- Blue: Information/documentation
- Purple: Questions/discussion

---

## 4. Pull Requests - Live Review Dashboard

### Pull Requests List (Filtered Views)

**URL**: `https://github.com/oviney/economist-agents/pulls`

**Quick Filters** (built-in tabs):
- 🟢 **Open** - Active PRs (default view)
- ✅ **Closed** - Historical PRs
- 👤 **Your pull requests** - PRs you created
- 🔍 **Review requests** - PRs awaiting your review

**Advanced Search** (type in search box):
```
is:pr is:open review-requested:@me
  → PRs waiting for my review

is:pr is:open author:@me
  → My open PRs

is:pr is:merged merged:>2026-01-01
  → PRs merged this year

is:pr is:open label:size-small
  → Small PRs (easy to review)

is:pr is:open draft:false no:review
  → PRs needing first review

is:pr is:open created:<2025-12-01
  → Old PRs (stale?)
```

**Sort Options**:
- Newest
- Oldest
- Most commented
- Recently updated

### PR Details Page (Rich Information)

**URL**: `https://github.com/oviney/economist-agents/pull/123`

**What You See** (all live):
- 📝 **Conversation**: All comments and reviews
- 🔍 **Files changed**: Diff view with inline comments
- ✅ **Checks**: CI/CD status (auto-refreshes)
- 💬 **Reviewers**: Who's assigned, who approved
- 🔗 **Linked issues**: "Closes #N" connections
- 📊 **Deployment status**: If deployed to staging

**Interactive Features**:
- Comment on specific lines of code
- Request changes or approve
- Suggest code changes (reviewers can propose edits)
- Re-request review after changes
- Merge button (when checks pass and approved)

### Review Workflow (In Browser)

1. **Get Assigned to Review**:
   - Notification appears (bell icon)
   - Email notification (if enabled)
   - Shows in "Review requests" filter

2. **Open PR → Files Changed**:
   - See all modified files
   - Side-by-side or unified diff
   - Hover line → Click "+" → Add comment

3. **Start a Review**:
   - Click "Review changes" (top right)
   - Options:
     - ✅ **Approve**: Looks good!
     - 💬 **Comment**: Just comments, no approval/rejection
     - ❌ **Request changes**: Needs work before merge

4. **PR Author Addresses Feedback**:
   - Makes changes
   - Pushes new commits
   - Re-requests review

5. **Final Approval → Merge**:
   - Green "Merge pull request" button appears
   - Options:
     - Merge commit (default)
     - Squash and merge (clean history)
     - Rebase and merge (linear history)

**All in browser, no CLI needed!**

---

## 5. Live Reporting Dashboards (URLs to Bookmark)

### Daily Standup View

**My Work Today**:
```
https://github.com/issues/assigned/@me
```
Bookmark this! Shows all issues assigned to you across all repos.

**Team's Open Issues**:
```
https://github.com/oviney/economist-agents/issues?q=is%3Aopen+is%3Aissue
```

**Team's Open PRs**:
```
https://github.com/oviney/economist-agents/pulls?q=is%3Aopen+is%3Apr
```

### Sprint Dashboard

**Current Sprint (Milestone 9)**:
```
https://github.com/oviney/economist-agents/milestone/9
```
Live progress bar shows completion percentage!

**Current Sprint Project Board**:
```
https://github.com/users/oviney/projects/1
```
Drag cards between columns as work progresses.

**Sprint Issues by Priority**:
```
P0: https://github.com/oviney/economist-agents/issues?q=is%3Aopen+label%3AP0-critical+milestone%3A%22Sprint+9%22
P1: https://github.com/oviney/economist-agents/issues?q=is%3Aopen+label%3AP1-high+milestone%3A%22Sprint+9%22
```

### Weekly Review Dashboards

**Pulse (Last 7 Days)**:
```
https://github.com/oviney/economist-agents/pulse
```
Change dropdown to "1 week" for weekly summary.

**Merged PRs This Week**:
```
https://github.com/oviney/economist-agents/pulls?q=is%3Apr+is%3Amerged+merged%3A%3E2026-01-03
```
(Update date to start of week)

**Closed Issues This Week**:
```
https://github.com/oviney/economist-agents/issues?q=is%3Aissue+is%3Aclosed+closed%3A%3E2026-01-03
```

### Metrics Dashboards

**Contributors Activity (Last 30 Days)**:
```
https://github.com/oviney/economist-agents/graphs/contributors?from=2025-12-01&to=2026-01-03
```
Adjust dates in URL for different time ranges.

**Code Frequency**:
```
https://github.com/oviney/economist-agents/graphs/code-frequency
```
Shows additions/deletions over time (bar chart).

**Commit Activity (52 Weeks)**:
```
https://github.com/oviney/economist-agents/graphs/commit-activity
```
Shows commits per week (velocity trend).

---

## 6. GitHub CLI for Quick Access

While web UI is primary, CLI is useful for quick queries:

### Installation

```bash
# macOS
brew install gh

# Authenticate
gh auth login
```

### Quick Commands (Output to Terminal)

```bash
# View sprint status
gh milestone view "Sprint 9"

# My open issues
gh issue list --assignee @me --state open

# PRs needing my review
gh pr list --search "review-requested:@me"

# Open sprint board in browser
gh project list --owner oviney --web

# Open specific issue in browser
gh issue view 123 --web

# Open PR in browser
gh pr view 456 --web
```

**Key Point**: CLI opens web UI, doesn't generate static reports!

---

## 7. Best Practices for Live Reporting

### Bookmark Strategy

Create browser bookmarks folder: "GitHub Dashboards"

**Essential Bookmarks**:
1. 📊 My Work: `https://github.com/issues/assigned/@me`
2. 👀 My Reviews: `https://github.com/pulls/review-requested/@me`
3. 🎯 Current Sprint: `https://github.com/oviney/economist-agents/milestone/9`
4. 📋 Sprint Board: `https://github.com/users/oviney/projects/1`
5. 📈 Team Activity: `https://github.com/oviney/economist-agents/pulse`
6. 👥 Contributors: `https://github.com/oviney/economist-agents/graphs/contributors`

### Daily Routine

**Morning (5 minutes)**:
1. Open "My Work" bookmark → See assigned issues
2. Open "My Reviews" bookmark → See PRs to review
3. Open "Sprint Board" → Move yesterday's cards to "Done"
4. Open "Current Sprint" → Check progress bar

**Evening (3 minutes)**:
1. Move completed work to "Done" on board
2. Close resolved issues (auto-updates milestone)
3. Update any blocked items with comments

### Weekly Review (15 minutes)

**Friday Afternoon**:
1. Open Pulse → Review week's activity
2. Open Sprint Milestone → Check if on track
3. Open Contributors graph → See team activity
4. Review blocked items → Unblock what you can

### Monthly Retrospective

1. **Velocity**: Code Frequency graph → Compare to last month
2. **Quality**: PR review times → Compare to last month
3. **Bottlenecks**: Old open PRs → Identify stale work
4. **Team health**: Contributors graph → Even distribution?

---

## 8. Advanced Web UI Features

### Saved Searches (Custom Filters)

Any search URL can be bookmarked:

**Bug Triage Dashboard**:
```
https://github.com/oviney/economist-agents/issues?q=is%3Aopen+label%3Abug+sort%3Acreated-asc
```
Oldest bugs first (triage these!)

**Unassigned Work**:
```
https://github.com/oviney/economist-agents/issues?q=is%3Aopen+no%3Aassignee+label%3Asprint-9
```
Sprint work that needs assignment.

**Stale PRs**:
```
https://github.com/oviney/economist-agents/pulls?q=is%3Aopen+updated%3A%3C2025-12-01
```
PRs not updated in over a month.

### Custom Project Views

In any GitHub Project:

1. Click **"+ New view"** (top tabs)
2. Choose type: Board, Table, or Roadmap
3. Name it (e.g., "P0 Only", "My Work", "This Week")
4. Set filters:
   ```
   Priority: is P0
   Status: is In Progress
   Assignee: is @me
   ```
5. Save view

Now you have custom dashboard views!

### GitHub Mobile App

**iOS/Android**: Search "GitHub" in app store

**Features**:
- View issues and PRs
- Comment and review code
- Merge pull requests
- Get notifications
- View project boards

**Use case**: Review PRs from phone during commute!

---

## 9. Summary: Everything is Live

**No scripts needed**:
- ❌ No `generate_report.py`
- ❌ No static JSON/markdown files
- ❌ No cron jobs or scheduled tasks
- ❌ No manual report generation

**Just open URLs**:
- ✅ Milestone page → Live burndown (progress bar)
- ✅ Pulse page → Live weekly activity
- ✅ Project board → Live Kanban with drag-drop
- ✅ Contributors graph → Live velocity charts
- ✅ Issues list → Live filtered views

**Reports update automatically** as team works:
- Close issue → Milestone progress bar increases
- Merge PR → Contributor graph updates
- Move card on board → Project view reflects instantly
- Add comment → Issue activity timeline updates

**Access from anywhere**:
- 💻 Desktop browser
- 📱 Mobile browser
- 📲 GitHub mobile app
- 🖥️ Any device with internet

---

## 10. Quick Start Checklist

Week 1: Setup
- [ ] Create GitHub Project board for current sprint
- [ ] Create Milestone for current sprint
- [ ] Add all sprint issues to milestone
- [ ] Set up project automation (auto-add, auto-move)
- [ ] Bookmark essential dashboard URLs

Week 2: Adoption
- [ ] Team checks "My Work" bookmark daily
- [ ] Team updates project board daily
- [ ] Use Pulse for weekly standup
- [ ] Review Contributors graph in retrospective

Week 3: Optimization
- [ ] Create custom project views
- [ ] Set up saved search bookmarks
- [ ] Install GitHub mobile app
- [ ] Share dashboard URLs with team

---

**Last Updated**: 2026-01-03
**Version**: 2.0 (Web UI focus, no static reports)
**Status**: Production-ready
**Owner**: Scrum Master

