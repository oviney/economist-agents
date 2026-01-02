# Sprint Management Skill

## Overview
Comprehensive sprint management with GitHub integration, process discipline, and automated sync.

## Version
**2.0** - Added GitHub sprint sync workflows, bi-directional sync, automated issue creation

## Capabilities

### 1. GitHub Sprint Sync

**Push to GitHub** (SPRINT.md → GitHub Issues):
```bash
# Validate sprint ready
python3 scripts/github_sprint_sync.py --validate-sprint 7

# Dry run (preview)
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run

# Create issues
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7
```

**Validation Checks**:
- ✓ All stories have story points (>0)
- ✓ All stories have acceptance criteria
- ✓ All stories have priority (P0-P3)

**Pull from GitHub** (GitHub Issues → SPRINT.md):
```bash
# Update SPRINT.md with closed issue status
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

**Auto-sync** (GitHub Actions):
- Trigger: Issue closed with `sprint-story` label
- Action: Updates SPRINT.md automatically
- File: `.github/workflows/sprint-sync.yml`

### 2. Milestone Management

**Create Milestone**:
```bash
gh milestone create "Sprint 7: CrewAI Migration" \
  --description "15 story points" \
  --due-date 2026-01-15 \
  --repo oviney/economist-agents
```

**Close Milestone**:
```bash
gh milestone close "Sprint 7: CrewAI Migration" \
  --repo oviney/economist-agents
```

**List Milestones**:
```bash
gh milestone list --repo oviney/economist-agents
```

### 3. Project Board Automation

**Setup** (Manual - GitHub UI):
1. Repository → Projects → New Project
2. Template: Board
3. Columns: Backlog, In Progress, Done
4. Automation rules:
   - Issue opened → Backlog
   - PR opened → In Progress
   - PR merged → Done

**Benefits**:
- Visual sprint progress
- Automatic card movement
- Team visibility

### 4. Issue Creation Patterns

**From Template** (`.github/ISSUE_TEMPLATE/sprint_story.yml`):
- Sprint dropdown (Sprint 1-20)
- Priority: P0/P1/P2/P3
- Story points: 1/2/3/5/8
- Goal, Tasks, Acceptance Criteria
- Auto-labels: `sprint-story`, `sprint-N`, priority, points

**From Script** (automated):
- Parses SPRINT.md structure
- Creates issues with proper labels
- Assigns to milestone
- Links back to SPRINT.md

### 5. Commit → Story Linking

**Enforced by** `.github/workflows/sprint-discipline.yml`:
- All commits must have "Story N:" in message
- All PRs must link to story issues
- Validated before merge

**Pattern**:
```
Story 1: Implement CrewAI coordinator

- Add crew configuration
- Wire up agents

Closes #42
```

### 6. Sprint Status Tracking

**GitHub View**:
```bash
# Show all sprint stories
python3 scripts/github_sprint_sync.py --show-github-status

# List sprint issues
gh issue list --label "sprint-7"

# List sprint PRs
gh pr list --label "sprint-7"
```

**SPRINT.md View**:
- Pull from GitHub updates local file
- Marks completed stories: `✅ COMPLETE (Closes #123)`
- Tracks story points progress

## Workflows

### Sprint Start Workflow

```bash
# 1. Check ceremonies complete
python3 scripts/sprint_ceremony_tracker.py --can-start 7

# 2. Validate sprint ready
python3 scripts/github_sprint_sync.py --validate-sprint 7

# 3. Create milestone
gh milestone create "Sprint 7: Title" --due-date 2026-01-15

# 4. Preview sync
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run

# 5. Create GitHub issues
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7

# 6. Create Project board (manual)

# 7. Update SPRINT.md with issue numbers (optional)
```

### Sprint Execution Workflow

**Daily**:
```bash
# Check status
python3 scripts/github_sprint_sync.py --show-github-status

# View open stories
gh issue list --label "sprint-7" --state open
```

**On PR Merge**:
- GitHub Actions auto-updates SPRINT.md
- Issue auto-closed via "Closes #N" in PR

**Manual Sync** (if needed):
```bash
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

### Sprint Close Workflow

```bash
# 1. Pull final status
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7

# 2. Generate retrospective
python3 scripts/sprint_ceremony_tracker.py --retrospective 7

# 3. Close milestone
gh milestone close "Sprint 7: Title"

# 4. Archive Project board (manual)

# 5. Update SPRINT.md metrics

# 6. Mark sprint complete
python3 scripts/sprint_ceremony_tracker.py --end-sprint 7
```

## Learned Patterns (from sprint_tracker.json)

### Pattern: work_without_planning
**Severity**: CRITICAL
**Detection**: Starting story without DoR validation
**Prevention**: `--validate-sprint` before `--push-to-github`

### Pattern: scope_creep_mid_sprint
**Severity**: HIGH
**Detection**: Adding stories after sprint start
**Prevention**: Lock sprint backlog after sync to GitHub

### Pattern: missing_progress_tracking
**Severity**: MEDIUM
**Detection**: No daily standup, no status checks
**Prevention**: Daily `--show-github-status` runs

### Pattern: skipped_retrospective
**Severity**: HIGH
**Detection**: Starting new sprint without retrospective
**Prevention**: `--can-start N` blocks without retrospective

### Pattern: work_without_acceptance_criteria
**Severity**: HIGH
**Detection**: Story with empty AC list
**Prevention**: `--validate-sprint` checks for ACs

### Pattern: unestimated_work
**Severity**: MEDIUM
**Detection**: Story with 0 or missing story points
**Prevention**: `--validate-sprint` checks for points >0

## Integration Points

### With Sprint Ceremony Tracker
- `--can-start N` checks ceremonies complete
- `--validate-sprint N` checks story structure
- Together: Complete DoR validation

### With GitHub Actions
- `sprint-discipline.yml` enforces commit standards
- `sprint-sync.yml` auto-updates SPRINT.md
- Both: Automated quality gates

### With Skills System
- `sprint_history.json` tracks velocity
- `sprint_tracker.json` tracks ceremony completion
- `blog_qa_skills.json` has sprint discipline patterns

### With SPRINT.md
- Source of truth for sprint planning
- Updated by pull-from-github
- Validated by sprint validator

## Metrics Tracked

**Per Sprint**:
- Story points planned vs completed
- Defect escape rate
- Sprint velocity (rolling average)
- Sprint rating (1-10)
- Retrospective action items

**GitHub-Specific**:
- Issue creation count
- Issue close rate
- PR merge rate
- Commit message compliance

## Tools Reference

| Tool | Purpose | Usage |
|------|---------|-------|
| `github_sprint_sync.py` | SPRINT.md ↔ GitHub sync | `--push-to-github`, `--pull-from-github` |
| `sprint_ceremony_tracker.py` | Ceremony enforcement | `--can-start`, `--retrospective` |
| `sprint_validator.py` | SPRINT.md structure | Validates format |
| `gh` (GitHub CLI) | Milestone/issue management | `milestone create`, `issue list` |
| `.github/workflows/sprint-sync.yml` | Auto-update SPRINT.md | On issue close |
| `.github/workflows/sprint-discipline.yml` | Enforce standards | On PR |

## Configuration

**Environment Variables**:
- `GITHUB_TOKEN`: Required for API access
- Generate at: https://github.com/settings/tokens
- Permissions: repo (full), read:org

**Repository Settings**:
- Branch protection on `main`: Require PR, require status checks
- Required status checks: `sprint-discipline`, `quality-tests`

**Issue Templates**:
- Location: `.github/ISSUE_TEMPLATE/sprint_story.yml`
- Auto-labels: `sprint-story`, sprint number, priority, points

## Error Handling

**Validation Errors**:
```
❌ Sprint 7 has validation issues:
   • Story 1: Missing story points
   • Story 2: Missing acceptance criteria
```
→ Fix in SPRINT.md, re-run validation

**Sync Errors**:
```
❌ Failed to create issue: API rate limit
```
→ Wait 1 hour, or use personal access token with higher limits

**Auto-Sync Failures**:
→ Check GitHub Actions logs
→ Manual fallback: `--pull-from-github`

## Best Practices

1. **Always validate before sync**
   ```bash
   python3 scripts/github_sprint_sync.py --validate-sprint 7
   ```

2. **Use dry-run first**
   ```bash
   python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run
   ```

3. **Pull status at sprint end**
   ```bash
   python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
   ```

4. **Close milestone when done**
   ```bash
   gh milestone close "Sprint 7: Title"
   ```

5. **Archive Project board**
   - Provides historical record
   - Enables burndown analysis

## Troubleshooting

**Issue: "No stories found for Sprint 7"**
- Check SPRINT.md has `## Sprint 7:` section
- Verify story format: `#### Story N: Title`

**Issue: "GITHUB_TOKEN not set"**
- Export token: `export GITHUB_TOKEN='ghp_...'`
- Or add to `.env` file

**Issue: "Failed to create issue"**
- Check token has `repo` permission
- Check rate limit: `gh api rate_limit`

**Issue: "Auto-sync not working"**
- Check issue has `sprint-story` label
- Check issue has `sprint-N` label
- View Actions logs: Repository → Actions → sprint-sync

## Future Enhancements

- [ ] Burndown chart generation
- [ ] Velocity trend visualization
- [ ] Auto-generate sprint retrospective insights
- [ ] Slack integration for sprint events
- [ ] Auto-assign issues to team members based on capacity

## References

- [GitHub Sprint Integration Guide](../../docs/GITHUB_SPRINT_INTEGRATION.md)
- [Scrum Master Protocol](../../docs/SCRUM_MASTER_PROTOCOL.md)
- [Sprint Ceremony Guide](../../docs/SPRINT_CEREMONY_GUIDE.md)
- [Scrum Master Agent](../../.github/agents/scrum-master.agent.md)

---

**Last Updated**: 2026-01-02
**Version**: 2.0 (GitHub sync workflows added)
**Status**: Production-ready
