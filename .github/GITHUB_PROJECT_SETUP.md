# GitHub Project Management Setup

This guide shows how to migrate from BACKLOG.md to GitHub's project management features.

## Why Migrate?

**Benefits of GitHub Issues + Projects**:
- ✅ Better visibility and collaboration
- ✅ Automatic notifications and assignments
- ✅ Rich filtering and search
- ✅ Integration with pull requests
- ✅ Project boards (Kanban, Table, Roadmap views)
- ✅ Automation (auto-close on PR merge, etc.)

## Migration Steps

### 1. Install GitHub CLI (if needed)

```bash
# macOS
brew install gh

# Authenticate
gh auth login
```

### 2. Preview Migration (Dry Run)

```bash
# See what will be created
python3 scripts/migrate_backlog_to_github.py --dry-run
```

This shows:
- Issue titles and bodies
- Labels that will be applied
- Which items will be created (skips completed by default)

### 3. Setup Labels

```bash
# Create standard priority and status labels
python3 scripts/migrate_backlog_to_github.py --setup-labels --dry-run

# Actually create them
python3 scripts/migrate_backlog_to_github.py --setup-labels --create
```

**Labels Created**:
- **Priority**: P0 (red), P1 (orange), P2 (yellow), P3 (green), P4 (purple)
- **Status**: complete, in-progress, blocked, icebox
- **Effort**: small, medium, large
- **Type**: enhancement

### 4. Create Issues

```bash
# Create issues for pending work (skips completed items)
python3 scripts/migrate_backlog_to_github.py --create

# Include completed items too (for historical record)
python3 scripts/migrate_backlog_to_github.py --create --include-completed
```

### 5. Create GitHub Project Board

**Via Web UI**:
1. Go to your repository on GitHub
2. Click "Projects" tab
3. Click "New project"
4. Choose template:
   - **Team backlog** - Good for this use case
   - **Feature** - Good for specific initiatives
   - **Bug tacker** - If tracking bugs separately

**Recommended Setup**:
- **Name**: "Architecture Improvements"
- **Description**: "Tracking improvements from architecture review"
- **Template**: Team backlog

### 6. Add Issues to Project

**Option A: Manually**
1. Open your project board
2. Click "Add item"
3. Search for issues by label (P0, P1, etc.)
4. Add them to the board

**Option B: Automation**
1. Go to project settings
2. Add workflow: "Auto-add issues with label"
3. Configure to auto-add issues with P0-P4 labels

### 7. Organize Board

**Recommended Columns**:
- **Icebox** - P4 items, good ideas but not prioritized
- **Backlog** - P2-P3 items, ready to work on
- **Ready** - P0-P1 items, next up
- **In Progress** - Currently being worked on
- **Done** - Completed

**Board Views**:
- **Table View** - See all metadata (priority, effort, status)
- **Board View** - Kanban-style workflow
- **Roadmap View** - Timeline-based planning (if using milestones)

## Advanced Features

### Milestones

Group related work:
```bash
# Create milestone
gh milestone create "Q1 2026 Improvements" --description "First quarter improvements"

# Add issues to milestone
gh issue edit 123 --milestone "Q1 2026 Improvements"
```

### Automation Rules

**Auto-close on PR merge**:
1. In issue body, add: `Closes #123`
2. When PR merges, issue auto-closes

**Auto-move cards**:
1. Project settings → Workflows
2. Add: "When issue is closed, move to Done"

### Custom Fields (Projects v2)

Add custom fields to issues:
- **Estimated hours**
- **Actual hours**
- **Dependencies**
- **Sprint** (if using sprints)

## Alternative: Export to JSON

If you prefer manual import or want to use a different tool:

```bash
# Export backlog to JSON
python3 scripts/migrate_backlog_to_github.py --export backlog.json
```

Then import into:
- Jira
- Linear
- Asana
- Other project management tools

## Keeping BACKLOG.md

**Option 1: Replace with link**
Update BACKLOG.md to redirect to GitHub:

```markdown
# Project Backlog

**This backlog has moved to GitHub Issues!**

👉 [View Issues](https://github.com/your-org/economist-agents/issues)
👉 [View Project Board](https://github.com/your-org/economist-agents/projects/1)

For historical reference, see git history of this file.
```

**Option 2: Keep as changelog**
Rename to BACKLOG_ARCHIVE.md and keep completed items for reference.

**Option 3: Auto-sync**
Create GitHub Action to generate BACKLOG.md from issues (advanced).

## FAQ

**Q: Will this delete BACKLOG.md?**
A: No, the script only reads it. You decide what to do with the file after.

**Q: Can I undo this?**
A: Yes, you can bulk-close issues or delete the project board. But there's no automated "undo" script.

**Q: What about completed items?**
A: By default they're skipped. Use `--include-completed` to migrate them too (good for historical record).

**Q: Can I migrate to a different repo?**
A: Yes, use `--repo owner/repo` flag.

**Q: Do I need to close issues manually?**
A: No, issues will have `status:complete` label. You can filter them out or close them in bulk.

## Recommended Workflow

After migration:

1. **New work**:
   - Create GitHub Issue directly
   - Apply priority label (P0-P4)
   - Add to project board

2. **Work in progress**:
   - Move card to "In Progress" column
   - Update issue with progress comments

3. **Complete work**:
   - Close issue with PR reference
   - Card auto-moves to "Done"

4. **Regular reviews**:
   - Weekly: Review "In Progress" (are things moving?)
   - Monthly: Review "Backlog" (re-prioritize)
   - Quarterly: Review "Icebox" (still relevant?)

## Example Commands

```bash
# Full migration workflow
python3 scripts/migrate_backlog_to_github.py --setup-labels --dry-run
python3 scripts/migrate_backlog_to_github.py --setup-labels --create
python3 scripts/migrate_backlog_to_github.py --create

# View created issues
gh issue list --label P0
gh issue list --label "status:in-progress"

# Update an issue
gh issue edit 123 --add-label "blocked"
gh issue comment 123 --body "Blocked by dependency X"

# Close an issue
gh issue close 123 --comment "Fixed in PR #456"
```

## Support

If migration fails:
1. Check `gh auth status` - are you authenticated?
2. Try `--dry-run` first to see what will happen
3. Use `--export` to generate JSON and inspect manually
4. Check script output for specific errors

For GitHub Projects help: https://docs.github.com/en/issues/planning-and-tracking-with-projects
