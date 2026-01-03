# GitHub Web UI Navigation Guide

Visual guide to finding all reporting and project tracking features in GitHub's web interface.

## Table of Contents
1. [Accessing Your Repository](#accessing-your-repository)
2. [Finding Project Boards](#finding-project-boards)
3. [Viewing Live Insights](#viewing-live-insights)
4. [Sprint Milestones](#sprint-milestones)
5. [Creating Bookmarks](#creating-bookmarks)

---

## Accessing Your Repository

**URL**: `https://github.com/oviney/economist-agents`

**Top Navigation Bar** (always visible):
```
[Code] [Issues] [Pull requests] [Actions] [Projects] [Security] [Insights]
```

---

## Finding Project Boards

### Step 1: Click "Projects" Tab

Located in top navigation:
```
https://github.com/oviney/economist-agents
↓
Click [Projects] tab
```

### Step 2: View Existing Projects or Create New

**If projects exist**: You'll see list of project boards
- Click any project name to open it

**To create new project**:
1. Click green "Link a project" button
2. Select "New project"
3. Choose template: Board, Table, or Roadmap
4. Click "Create"

### Step 3: Explore Project Views

Once in a project, top tabs show:
```
[Board] [Table] [Roadmap] [Settings]
```

**Board View**: `https://github.com/users/oviney/projects/1/views/1`
- Kanban-style columns
- Drag and drop cards
- Real-time updates

**Table View**: `https://github.com/users/oviney/projects/1/views/2`
- Spreadsheet interface
- Filter box at top
- Sort by clicking column headers

**Roadmap View**: `https://github.com/users/oviney/projects/1/views/3`
- Timeline/Gantt chart
- Drag to adjust dates
- Zoom controls: Day/Week/Month/Quarter

### Step 4: Bookmark Your Project

**Browser Bookmark**:
```
Name: "Sprint 9 Board"
URL: https://github.com/users/oviney/projects/1
```

---

## Viewing Live Insights

### Insights Tab Location

**From repository homepage**:
```
https://github.com/oviney/economist-agents
↓
Click [Insights] tab (top navigation)
```

### Insights Sidebar Menu

Left sidebar shows all insight types:
```
📊 Pulse
👥 Contributors  
📈 Code frequency
🔄 Commit activity
🌐 Network
📦 Dependency graph
```

### Individual Insight Pages

#### Pulse (Weekly Activity)
```
https://github.com/oviney/economist-agents/pulse
```

**What you see**:
- Dropdown: "Period: 1 week" (can change to 24h, 3 days, 1 month)
- Summary stats: PRs opened/merged/closed, issues opened/closed
- Active contributors list
- Recent commits

**Bookmark as**: "Team Weekly Activity"

#### Contributors (Team Velocity)
```
https://github.com/oviney/economist-agents/graphs/contributors
```

**What you see**:
- Line chart: Commits over time per person
- Dropdown: Time range (1 month, 3 months, 1 year, all time)
- Hover data points for exact numbers
- Click contributor names to filter

**Bookmark as**: "Team Velocity Graph"

#### Code Frequency (Development Pace)
```
https://github.com/oviney/economist-agents/graphs/code-frequency
```

**What you see**:
- Green bars: Lines added per week
- Red bars: Lines deleted per week
- Hover for exact numbers
- Shows last 52 weeks

**Bookmark as**: "Code Change Trends"

#### Commit Activity (Velocity Trend)
```
https://github.com/oviney/economist-agents/graphs/commit-activity
```

**What you see**:
- Bar chart: Commits per week
- 52-week rolling window
- Hover bars for exact counts
- Shows activity patterns

**Bookmark as**: "Commit Velocity"

---

## Sprint Milestones

### Accessing Milestones

**From Issues Page**:
```
https://github.com/oviney/economist-agents/issues
↓
Click [Milestones] button (next to Labels and New issue)
```

**Direct URL**:
```
https://github.com/oviney/economist-agents/milestones
```

### Milestones List Page

**What you see**:
```
Open Milestones:
  Sprint 9: Validation & Measurement
  ████████████░░░░░░░░░░ 40% complete (8 closed, 12 open)
  Due by January 15, 2026 (12 days from now)
  [View milestone]

  Sprint 10: Next Phase
  ░░░░░░░░░░░░░░░░░░░░ 0% complete (0 closed, 15 open)
  Due by January 31, 2026 (28 days from now)
  [View milestone]

Closed Milestones: (click to expand)
  Sprint 8: Completed
  ████████████████████ 100% complete
  [View milestone]
```

### Individual Milestone Page

**Click any milestone** or go directly:
```
https://github.com/oviney/economist-agents/milestone/9
```

**What you see**:
```
Sprint 9: Validation & Measurement
████████████░░░░░░░░░░ 40% complete

Due by January 15, 2026 (12 days from now)
8 closed / 12 open

[List of all issues in this milestone with labels and assignees]
```

**Interactive features**:
- Progress bar updates in real-time as issues close
- Filter issues: Click labels, search box
- Sort: Newest, oldest, most commented
- Each issue shows labels, assignee, comments count

**Bookmark as**: "Sprint 9 Progress"

### Creating a New Milestone

**From Milestones page**:
1. Click green "New milestone" button
2. Fill in form:
   - **Title**: Sprint 10: Next Phase
   - **Due date**: Click calendar picker → Select date
   - **Description**: Sprint goals and focus areas
3. Click green "Create milestone" button

**Adding issues to milestone**:
1. Open any issue
2. Right sidebar → "Milestone" section
3. Click gear icon → Select milestone from dropdown
4. Milestone progress updates automatically!

---

## Creating Bookmarks

### Essential Bookmarks Folder

Create browser bookmarks folder: **"GitHub Dashboards"**

### Recommended Bookmarks

#### Personal Dashboards

**1. My Work**
```
Name: 🎯 My Open Issues
URL: https://github.com/issues/assigned/@me
```

**2. My Reviews**
```
Name: 👀 PRs Needing My Review
URL: https://github.com/pulls/review-requested/@me
```

**3. My PRs**
```
Name: 📝 My Pull Requests
URL: https://github.com/pulls?q=is%3Aopen+is%3Apr+author%3A%40me
```

#### Team Dashboards

**4. Current Sprint**
```
Name: 🎯 Sprint 9 Progress
URL: https://github.com/oviney/economist-agents/milestone/9
```

**5. Sprint Board**
```
Name: 📋 Sprint 9 Board
URL: https://github.com/users/oviney/projects/1
```

**6. Team Activity**
```
Name: 📊 Team Pulse
URL: https://github.com/oviney/economist-agents/pulse
```

**7. Team Velocity**
```
Name: 📈 Contributor Graph
URL: https://github.com/oviney/economist-agents/graphs/contributors
```

#### Filtered Views

**8. Critical Issues**
```
Name: 🚨 P0 Issues
URL: https://github.com/oviney/economist-agents/issues?q=is%3Aopen+label%3AP0-critical
```

**9. Blocked Items**
```
Name: 🚫 Blocked Work
URL: https://github.com/oviney/economist-agents/issues?q=is%3Aopen+label%3Ablocked
```

**10. Unassigned Sprint Work**
```
Name: 📍 Needs Assignment
URL: https://github.com/oviney/economist-agents/issues?q=is%3Aopen+no%3Aassignee+label%3Asprint-9
```

### Browser Setup by Browser

#### Chrome/Edge
1. Press `Ctrl+Shift+O` (Windows) or `Cmd+Shift+O` (Mac)
2. Right-click "Bookmarks bar" → "Add folder"
3. Name: "GitHub Dashboards"
4. Right-click folder → "Add page"
5. Paste name and URL from above

#### Firefox
1. Press `Ctrl+Shift+B` (Windows) or `Cmd+Shift+B` (Mac)
2. Right-click "Bookmarks Toolbar" → "New Folder"
3. Name: "GitHub Dashboards"
4. Right-click folder → "New Bookmark"
5. Paste name and URL from above

#### Safari
1. Press `Cmd+Shift+L`
2. Click "+" button in sidebar
3. Choose "New Folder"
4. Name: "GitHub Dashboards"
5. Right-click folder → "Add Bookmark"
6. Paste name and URL from above

---

## Daily Workflow with Bookmarks

### Morning Routine (5 minutes)

**Open these 4 bookmarks**:
1. 🎯 My Open Issues
2. 👀 PRs Needing My Review
3. 🎯 Sprint 9 Progress
4. 📋 Sprint 9 Board

**What to do**:
- Review assigned issues → Pick 1-2 to work on today
- Review PRs → Schedule time to review
- Check sprint progress → Are we on track?
- Move yesterday's cards to "Done" on board

### End of Day (3 minutes)

**Open these 2 bookmarks**:
1. 📋 Sprint 9 Board
2. 🎯 My Open Issues

**What to do**:
- Move completed cards to "Done"
- Close finished issues (auto-updates milestone!)
- Add comments to any blocked work

### Friday Retrospective (15 minutes)

**Open these 4 bookmarks**:
1. 📊 Team Pulse (set to "1 week")
2. 🎯 Sprint 9 Progress
3. 📈 Contributor Graph
4. 🚫 Blocked Work

**What to review**:
- Pulse: How many PRs merged? Issues closed?
- Sprint Progress: On track for sprint goal?
- Contributors: Even workload distribution?
- Blocked: Can we unblock anything over weekend?

---

## Mobile Access

### GitHub Mobile App

**Download**:
- iOS: Search "GitHub" in App Store
- Android: Search "GitHub" in Play Store

**Features on mobile**:
- View all dashboards (issues, PRs, projects)
- Comment on issues and PRs
- Review code
- Merge pull requests
- Get push notifications
- Scan QR codes to open repos

**Recommended mobile bookmarks**:
- My Open Issues
- PRs Needing My Review  
- Current Sprint Milestone

**Use case**: Quick PR reviews during commute!

---

## Pro Tips

### 1. Use Browser Profiles for Multiple Accounts

If you work with multiple GitHub accounts:
- Chrome: Create separate profiles
- Firefox: Use containers
- Each profile has its own bookmarks

### 2. Keyboard Shortcuts in GitHub

Press `?` on any GitHub page to see shortcuts:
- `g i` → Go to Issues
- `g p` → Go to Pull Requests
- `g c` → Go to Code
- `/` → Focus search bar

### 3. Pin Browser Tabs

Pin frequently used dashboards:
1. Open dashboard
2. Right-click tab
3. Select "Pin tab"
4. Tab stays open and loads on browser start

**Recommended pins**:
- My Open Issues
- Sprint 9 Board

### 4. Use GitHub CLI to Open in Browser

```bash
# Install
brew install gh && gh auth login

# Quick open commands
gh issue list --assignee @me --web
gh pr list --web
gh project list --web
gh milestone view "Sprint 9" --web
```

All commands open results in your default browser!

---

## Troubleshooting

### "I don't see the Projects tab"

**Solution**: Projects may not be enabled
1. Go to repository Settings
2. Scroll to "Features"
3. Check "Projects" checkbox

### "I don't see Insights tab"

**Solution**: Need repository access
- Must have "Read" access minimum
- Ask repository owner to add you as collaborator

### "Milestone progress not updating"

**Solution**: Check issue is assigned to milestone
1. Open issue
2. Right sidebar → "Milestone"
3. If blank, click gear → Select milestone

### "Project board not showing my issues"

**Solution**: Add issues to project
1. Go to project board
2. Click "+ Add item" at bottom of column
3. Search for issue number
4. Click to add

Or set up automation:
1. Project → Settings → Workflows
2. Add "Auto-add to project" rule
3. Filter by label (e.g., `label:sprint-9`)

---

## Next Steps

1. **Create your bookmarks folder** (5 min)
2. **Bookmark essential URLs** (10 min)
3. **Try morning routine tomorrow** (5 min)
4. **Share bookmark URLs with team** (team meeting)

---

## Related Documentation

- **Complete Skills Guide**: [../skills/github-features/SKILL.md](../skills/github-features/SKILL.md)
- **Quick Reference**: [GITHUB_REPORTING_QUICK_REFERENCE.md](GITHUB_REPORTING_QUICK_REFERENCE.md)
- **Tutorial**: [GITHUB_FEATURES_TUTORIAL.md](GITHUB_FEATURES_TUTORIAL.md)

---

**Last Updated**: 2026-01-03
**Version**: 1.0
**Focus**: Web UI navigation and bookmarks
