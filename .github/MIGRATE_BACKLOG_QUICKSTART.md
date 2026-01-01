# Quick Start: Migrate Backlog to GitHub

## 🚀 One-Command Migration

```bash
# 1. Preview what will be created
python3 scripts/migrate_backlog_to_github.py --dry-run

# 2. Setup labels (one-time)
python3 scripts/migrate_backlog_to_github.py --setup-labels --create

# 3. Create all issues (skips completed items)
python3 scripts/migrate_backlog_to_github.py --create
```

## 📊 What You Get

**12 GitHub Issues created** (pending items only):
- 7 items ready to work on
- Organized by priority (P0-P4 labels)
- Marked with effort (small/medium/large)
- Proper status tracking

## 🎯 Next Steps After Migration

### Step 1: Create Project Board
```bash
# Via web: https://github.com/YOUR_USER/economist-agents/projects/new
# Choose template: "Team backlog"
```

### Step 2: Add Issues to Board
```bash
# In project, click "Add item" and search by label:
# - P0 issues (critical)
# - P1 issues (high)
# - P2 issues (medium)
```

### Step 3: Organize Columns
```
Icebox → Backlog → Ready → In Progress → Done
  P4       P2-P3     P0-P1     Active      ✅
```

## 📌 Useful Commands

```bash
# View all issues
gh issue list

# View by priority
gh issue list --label P0
gh issue list --label P2

# View by status
gh issue list --label "status:in-progress"

# Update an issue
gh issue edit 42 --add-label "blocked"
gh issue comment 42 --body "Progress update..."

# Close an issue
gh issue close 42 --comment "Completed in PR #123"
```

## 🔄 Workflow Integration

**When starting work:**
```bash
gh issue edit 42 --remove-label "status:ready" --add-label "status:in-progress"
```

**When completing:**
```bash
# In PR description, add:
Closes #42

# Issue auto-closes when PR merges
```

## 📚 Full Documentation

See [.github/GITHUB_PROJECT_SETUP.md](.github/GITHUB_PROJECT_SETUP.md) for:
- Complete setup guide
- Advanced features (milestones, custom fields)
- Automation rules
- FAQ and troubleshooting

## ✅ Benefits

- **Visibility**: Everyone sees what's being worked on
- **Collaboration**: Comment, assign, discuss on issues
- **Tracking**: Automatic history and notifications
- **Integration**: Links with PRs, commits, and code
- **Planning**: Kanban board, roadmap, and filtering views
