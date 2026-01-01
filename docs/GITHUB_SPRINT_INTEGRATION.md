# GitHub Integration Guide

## Overview

Sprint discipline is now **fully integrated with GitHub**. No need for local-only tools - everything lives in GitHub's native features.

---

## 🎯 GitHub Projects Board

### Setup (One-Time)

1. Go to your repo → **Projects** → **New project**
2. Choose **Board** layout
3. Name it "Sprint 2 (Jan 8-14, 2026)"
4. Add columns:
   - 📋 **Backlog** (Not started, future work)
   - 🔄 **In Progress** (Active work this sprint)
   - ✅ **Done** (Completed this sprint)
   - 🎉 **Shipped** (Deployed to production)

### Using the Board

**Create Stories as GitHub Issues:**
- Click **New Issue** → Choose template: "📋 Sprint Story"
- Fill out story details (auto-prompts for priority, points, AC)
- Issue gets added to project board automatically

**Move Cards:**
- Drag stories across columns as work progresses
- Visual view of sprint progress
- Filter by sprint, priority, story points

---

## 📝 Creating Sprint Stories (GitHub Issues)

### Use Issue Templates

Click **New Issue** → **📋 Sprint Story**

Template provides:
- Sprint selection dropdown
- Priority (P0/P1/P2/P3)
- Story points (1/2/3/5/8)
- Tasks checklist
- Acceptance criteria
- Dependencies

### Story Naming Convention

```
Story: [Brief description]
```

Example:
```
Story: Validate Quality System in Production
```

GitHub will assign:
- Issue number (e.g., #25)
- Labels (sprint-story, needs-estimation)
- Milestone (if configured)

---

## 🔄 Workflow: From Story to Merge

### 1. Create Story (GitHub Issue)

```bash
# Go to GitHub repo → Issues → New Issue → Sprint Story template
# Fill out form → Submit
# GitHub assigns issue number (e.g., #25)
```

### 2. Validate Before Starting Work

```bash
# Still use local validator (references GitHub issue)
./scripts/pre_work_check.sh "Validate Quality System in Production"

# Checks:
# ✅ Story exists in GitHub Issues
# ✅ Has story points label
# ✅ Has acceptance criteria
# ✅ Part of active sprint milestone
```

### 3. Create Branch

```bash
# Naming convention: story-NUMBER-brief-description
git checkout -b story-25-validate-quality-system
```

### 4. Work on Story

Update GitHub issue as you progress:
- Check off tasks in issue description
- Add comments with progress updates
- Reference commit with "Story 25: ..." prefix

```bash
git commit -m "Story 25: Add self-validation metrics collection

- Tracks validation pass/fail counts
- Logs regeneration triggers
- Updates skills system with effectiveness data"
```

### 5. Create Pull Request

```bash
git push origin story-25-validate-quality-system
# Go to GitHub → Create Pull Request
```

PR template auto-fills checklist:
- Sprint story reference
- Acceptance criteria checkboxes
- Testing instructions
- Sprint context

### 6. Automated Validation (GitHub Actions)

On PR creation, GitHub Actions runs:

**Sprint Discipline Checks:**
- ✅ Commit messages reference story number
- ✅ PR title/body references story
- ✅ SPRINT.md exists and is valid
- ✅ Active sprint is marked

**Quality Tests:**
- ✅ All tests pass
- ✅ Skills JSON valid
- ✅ No new errors

### 7. Merge

After PR approved:
```bash
# Merge button in GitHub
# PR automatically closes linked issue
# Issue moves to "Done" column
```

---

## 🤖 GitHub Actions Workflows

### 1. Sprint Discipline Validator

**File:** `.github/workflows/sprint-discipline.yml`

**Runs on:** Every PR and push to main

**Checks:**
- Commit messages reference story numbers or issues
- PRs link to sprint stories
- SPRINT.md exists
- Active sprint marked

**Failure Example:**
```
❌ SPRINT DISCIPLINE VIOLATION
Commits must reference a sprint story:
  - Story 1: Add feature X
  - Fixes #123
  - Or use prefix: docs:, chore:, ci:
```

### 2. Quality System Tests

**File:** `.github/workflows/quality-tests.yml`

**Runs on:** Every PR and push to main

**Checks:**
- Integration tests pass
- Sprint validator runs
- Skills JSON integrity

---

## 📋 Issue Templates

### Sprint Story Template
**File:** `.github/ISSUE_TEMPLATE/sprint_story.yml`

**Provides:**
- Sprint selection dropdown
- Priority (P0-P3)
- Story points (1/2/3/5/8)
- Goal statement
- Tasks checklist
- Acceptance criteria (required)
- Dependencies linking

### Bug Report Template
**File:** `.github/ISSUE_TEMPLATE/bug_report.yml`

**Provides:**
- Severity levels
- Reproduction steps
- Expected vs actual behavior
- Logs/screenshots section

### Sprint Retrospective Template
**File:** `.github/ISSUE_TEMPLATE/sprint_retrospective.md`

**Documents:**
- What went well
- What could improve
- Action items for next sprint
- Velocity metrics
- Skills system updates

---

## 🔗 PR Template

**File:** `.github/PULL_REQUEST_TEMPLATE.md`

Auto-populated checklist ensures:
- Story reference (closes #X)
- Acceptance criteria met
- Tests pass
- Sprint progress updated
- Code quality maintained

---

## 🏃 Daily Workflow

### Morning Standup (Solo)

1. **Check GitHub Project Board**
   - What's in "In Progress"?
   - Any blockers?

2. **Pick Next Story**
   - From sprint backlog
   - Highest priority first

3. **Validate Story**
   ```bash
   ./scripts/pre_work_check.sh "Story description"
   ```

4. **Create Branch**
   ```bash
   git checkout -b story-N-description
   ```

### During Work

1. **Update Issue Tasks**
   - Check off completed tasks in GitHub issue
   - Add progress comments

2. **Commit with Story Reference**
   ```bash
   git commit -m "Story N: Specific change"
   ```

3. **Move Card on Board**
   - Drag to "In Progress" when starting
   - Drag to "Done" when complete

### End of Day

1. **Push Work**
   ```bash
   git push origin story-N-description
   ```

2. **Update Sprint Progress**
   - Comment on issue with status
   - Update SPRINT.md if needed

3. **Check Sprint Health**
   ```bash
   python scripts/sprint_validator.py --validate-sprint
   ```

---

## 📊 Sprint Metrics (GitHub Insights)

GitHub provides built-in analytics:

1. **Issues → Milestones**
   - Set sprint as milestone
   - Shows % complete
   - Burn down chart

2. **Projects → Insights**
   - Velocity trends
   - Story points completed
   - Cycle time

3. **Actions → Runs**
   - Test pass rate
   - Validation failures
   - Build times

---

## 🔄 Sprint Cadence

### Sprint Start (Day 1)

1. **Create Sprint Milestone** in GitHub
   - Go to Issues → Milestones → New
   - Name: "Sprint 2 (Jan 8-14, 2026)"
   - Due date: End of sprint

2. **Create Sprint Issues**
   - Use Sprint Story template
   - Add to milestone
   - Label with story points

3. **Set Up Project Board**
   - New board for sprint
   - Add issues to board

### During Sprint (Days 2-4)

1. **Work on Stories**
   - Follow daily workflow above
   - Update GitHub issues continuously

2. **Monitor Progress**
   - Check project board
   - Review milestone progress
   - GitHub Actions passing?

### Sprint End (Day 5)

1. **Close Sprint Milestone**
   - All stories done?
   - Move incomplete to next sprint

2. **Create Retrospective Issue**
   - Use Sprint Retrospective template
   - Document learnings
   - Action items for next sprint

3. **Update Skills System**
   - Add patterns learned
   - Commit skills update with "docs:" prefix

---

## 🎯 Benefits of GitHub Integration

### Visual Progress
- Project board shows sprint at a glance
- Drag & drop simplicity
- Filter by sprint, priority, points

### Automated Validation
- GitHub Actions enforce discipline
- Can't merge without story reference
- Tests run automatically

### Team Collaboration
- Issues are shareable
- Comments for discussion
- Code review in PRs
- Historical record

### Metrics & Insights
- Built-in burn down charts
- Velocity tracking
- Issue cycle time
- Action pass rates

### No Context Switching
- Everything in GitHub
- No external tools needed
- Mobile accessible
- Notifications built-in

---

## 🚀 Quick Start

### First Sprint with GitHub

```bash
# 1. Create Sprint 2 issues in GitHub
# (Use Sprint Story template)

# 2. Validate before starting work
./scripts/pre_work_check.sh "Story description"

# 3. Create branch
git checkout -b story-N-description

# 4. Work & commit
git commit -m "Story N: Change"

# 5. Create PR
git push origin story-N-description
# Go to GitHub → Create PR

# 6. GitHub Actions validate automatically

# 7. Merge when approved
# Issue auto-closes, moves to Done
```

---

## 📚 Related Documentation

- [SPRINT.md](../SPRINT.md) - Current sprint plan
- [SPRINT_DISCIPLINE_GUIDE.md](SPRINT_DISCIPLINE_GUIDE.md) - Daily workflow
- Sprint discipline skills in `skills/blog_qa_skills.json`

---

## Next Steps

1. **Create Sprint 2 Project Board** in GitHub
2. **Convert SPRINT.md stories** to GitHub Issues
3. **Set up Sprint 2 Milestone**
4. **Start using workflow** for Story 1

The system is ready! 🎉
