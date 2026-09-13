# GitHub Sprint Workflow Guide

## Overview
Complete workflow for syncing sprints between SPRINT.md and GitHub Issues/Projects.

**Last Updated**: 2026-01-02
**Status**: Production-ready with automated sync

---

## Quick Start

```bash
# 1. Validate sprint ready
python3 scripts/github_sprint_sync.py --validate-sprint 7

# 2. Create milestone
gh milestone create "Sprint 7: CrewAI Migration" --due-date 2026-01-15

# 3. Sync to GitHub
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7

# 4. Create Project board (GitHub UI)

# Sprint runs...

# 5. Pull status at end
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

---

## Phase 1: Sprint Start (15 minutes)

### Step 1: Validate Ceremonies Complete (2 min)

**Check Definition of Ready**:
```bash
python3 scripts/sprint_ceremony_tracker.py --can-start 7
```

**If blocked**:
```
❌ BLOCKED: Sprint 6 retrospective not complete
   Run: python3 sprint_ceremony_tracker.py --retrospective 6
```

**Resolution**:
```bash
# Complete retrospective
python3 scripts/sprint_ceremony_tracker.py --retrospective 6
# Edit generated docs/RETROSPECTIVE_S6.md

# Refine backlog
python3 scripts/sprint_ceremony_tracker.py --refine-backlog 7
# Edit generated docs/SPRINT_7_BACKLOG.md

# Re-validate
python3 scripts/sprint_ceremony_tracker.py --can-start 7
```

### Step 2: Validate Sprint Structure (2 min)

**Run validation**:
```bash
python3 scripts/github_sprint_sync.py --validate-sprint 7
```

**Success output**:
```
✅ Sprint 7 is ready for GitHub sync
```

**Failure output**:
```
❌ Sprint 7 has validation issues:
   • Story 1: Missing story points
   • Story 2: Missing acceptance criteria
   • Story 3: Missing priority
```

**Resolution**: Fix issues in SPRINT.md, re-validate

**Validation Checks**:
- ✓ All stories have story points >0
- ✓ All stories have acceptance criteria (at least 1)
- ✓ All stories have priority (P0/P1/P2/P3)
- ✓ SPRINT.md has correct format

### Step 3: Create Milestone (1 min)

**Command**:
```bash
gh milestone create "Sprint 7: CrewAI Migration Foundation" \
  --description "15 story points - Agent coordination with CrewAI" \
  --due-date 2026-01-15 \
  --repo oviney/economist-agents
```

**Output**:
```
https://github.com/oviney/economist-agents/milestone/7
```

**Verify**:
```bash
gh milestone list --repo oviney/economist-agents
```

### Step 4: Preview Sync (1 min)

**Dry run**:
```bash
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run
```

**Output**:
```
🔄 Pushing Sprint 7 stories to GitHub...

  Found 4 stories

  🔍 DRY RUN MODE - No issues will be created

  Would create: Story 1: Implement CrewAI coordinator base
    Priority: P0 (Must Do) | Points: 5
  Would create: Story 2: Wire agents to coordinator
    Priority: P0 (Must Do) | Points: 3
  Would create: Story 3: Add crew configuration system
    Priority: P1 (High) | Points: 5
  Would create: Story 4: Document CrewAI integration
    Priority: P2 (Medium) | Points: 2

  Total: 4 issues would be created
```

**Review**:
- Check titles are clear
- Verify priorities correct
- Confirm story points match

### Step 5: Create GitHub Issues (3 min)

**Command**:
```bash
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7
```

**Output**:
```
🔄 Pushing Sprint 7 stories to GitHub...

  Found 4 stories

  Creating issue for Story 1: Implement CrewAI coordinator base...
    ✅ Created #42
  Creating issue for Story 2: Wire agents to coordinator...
    ✅ Created #43
  Creating issue for Story 3: Add crew configuration system...
    ✅ Created #44
  Creating issue for Story 4: Document CrewAI integration...
    ✅ Created #45

✅ Created 4 GitHub issues:
   Story 1 → Issue #42
   https://github.com/oviney/economist-agents/issues/42
   Story 2 → Issue #43
   https://github.com/oviney/economist-agents/issues/43
   ...
```

**What Happens**:
- Issues created with proper labels:
  - `sprint-story`
  - `sprint-7`
  - `P0` (or P1/P2/P3)
  - `5-points` (or 1/2/3/8-points)
- Issues assigned to Sprint 7 milestone
- Issue body contains:
  - Story goal
  - Priority
  - Story points
  - Tasks (with checkboxes)
  - Acceptance criteria

### Step 6: Create Project Board (5 min - Manual)

**GitHub UI Steps**:
1. Go to: https://github.com/oviney/economist-agents/projects
2. Click "New project"
3. Select "Board" template
4. Name: "Sprint 7: CrewAI Migration"
5. Click "Create"

**Add Columns**:
- 📋 **Backlog** (Not started)
- 🔄 **In Progress** (Active work)
- ✅ **Done** (Completed)

**Configure Automation**:
1. Click "..." on Backlog column → "Manage automation"
2. Enable: "Newly added issues and pull requests"
3. Click "..." on In Progress column → "Manage automation"
4. Enable: "Pull request opened"
5. Click "..." on Done column → "Manage automation"
6. Enable: "Pull request merged", "Issue closed"

**Add Items to Board**:
1. Click "+ Add item"
2. Search: `label:sprint-7`
3. Select all 4 issues
4. They appear in Backlog column

**Share Board URL**:
- Copy: https://github.com/users/oviney/projects/7
- Paste in Sprint 7 kickoff message

### Step 7: Report Sprint Start (1 min)

**Update team**:
```
Sprint 7: CrewAI Migration Foundation has started! 🚀

📊 Sprint Info:
- Duration: Jan 2-15, 2026 (2 weeks)
- Story Points: 15
- Stories: 4 (2 P0, 1 P1, 1 P2)

🔗 GitHub:
- Milestone: https://github.com/oviney/economist-agents/milestone/7
- Project Board: https://github.com/users/oviney/projects/7
- Issues: #42, #43, #44, #45

📋 Stories:
1. Story 1: Implement CrewAI coordinator base (#42) - 5 pts, P0
2. Story 2: Wire agents to coordinator (#43) - 3 pts, P0
3. Story 3: Add crew configuration system (#44) - 5 pts, P1
4. Story 4: Document CrewAI integration (#45) - 2 pts, P2

Let's build! 💪
```

---

## Phase 2: Sprint Execution (Daily)

### Daily Standup (5 min)

**Check GitHub Status**:
```bash
python3 scripts/github_sprint_sync.py --show-github-status
```

**Output**:
```
📊 GitHub Sprint Status

Sprint 7:
  Stories: 4
  Story Points: 15

  #42: Story 1: Implement CrewAI coordinator base
    Points: 5 | Comments: 3
  #43: Story 2: Wire agents to coordinator
    Points: 3 | Comments: 0
  #44: Story 3: Add crew configuration system
    Points: 5 | Comments: 1
  #45: Story 4: Document CrewAI integration
    Points: 2 | Comments: 0
```

**Check Open Issues**:
```bash
gh issue list --label "sprint-7" --state open --repo oviney/economist-agents
```

**Check PRs**:
```bash
gh pr list --label "sprint-7" --repo oviney/economist-agents
```

### Story Work Pattern

**Developer Workflow**:
```bash
# 1. Create branch from story number
git checkout -b story-1-crewai-coordinator

# 2. Commit with story reference
git commit -m "Story 1: Add CrewAI coordinator class

- Implement BaseCoordinator
- Add crew configuration
- Wire up agent registry

Closes #42"

# 3. Push and create PR
git push -u origin story-1-crewai-coordinator
gh pr create --title "Story 1: Implement CrewAI coordinator" \
  --body "Closes #42" \
  --label "sprint-7"

# 4. PR merged → Issue auto-closes → SPRINT.md auto-updates
```

**Automated Flow**:
1. PR created → Card moves to "In Progress"
2. PR merged → Card moves to "Done"
3. Issue closed → GitHub Actions runs
4. SPRINT.md updated with "✅ COMPLETE (Closes #42)"

### Manual Sync (if needed)

**When to use**:
- GitHub Actions failed
- Issue closed outside PR
- Need immediate status update

**Command**:
```bash
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

**Output**:
```
🔄 Pulling Sprint 7 status from GitHub...

  Found 4 GitHub issues

  ✅ Story 1: Marked complete (#42)
  ✅ Story 2: Marked complete (#43)

✅ Updated 2 stories in SPRINT.md
```

---

## Phase 3: Sprint Close (30 minutes)

### Step 1: Pull Final Status (2 min)

```bash
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

**Verifies**:
- All completed stories marked in SPRINT.md
- GitHub issue numbers recorded
- Status reflects GitHub state

### Step 2: Generate Retrospective (15 min)

**Generate template**:
```bash
python3 scripts/sprint_ceremony_tracker.py --retrospective 7
```

**Output**:
```
✅ Sprint 7 retrospective complete
📝 Template generated: docs/RETROSPECTIVE_S7.md
```

**Edit retrospective**:
```bash
code docs/RETROSPECTIVE_S7.md
```

**Fill in**:
- What went well (3-5 items)
- What could improve (3-5 items)
- Action items for next sprint (2-3 items)
- Sprint rating (1-10)
- Key metrics (velocity, completion %, defect escape rate)

**Example**:
```markdown
# Sprint 7 Retrospective

## What Went Well ✅
- CrewAI integration smoother than expected
- GitHub sync automation saved 2 hours/week
- All P0 stories completed on time

## What Could Improve ⚠️
- Story 3 blocked for 2 days (dependency on Story 1)
- Need better task breakdown for 5-point stories
- Retrospective delayed by 1 day

## Action Items 🎯
1. Add dependency detection to sprint validator
2. Break 5+ point stories into smaller tasks
3. Schedule retrospective at fixed time (Friday 4pm)

## Metrics
- Story Points: 15 planned, 13 completed (87%)
- Velocity: 13 (vs 14 Sprint 6)
- Sprint Rating: 8/10
- Defect Escape Rate: 0% (no production bugs)
```

### Step 3: Close Milestone (1 min)

```bash
gh milestone close "Sprint 7: CrewAI Migration Foundation" \
  --repo oviney/economist-agents
```

**Verify**:
```bash
gh milestone list --state closed --repo oviney/economist-agents
```

### Step 4: Archive Project Board (2 min)

**GitHub UI**:
1. Go to Project board
2. Click "..." menu → Settings
3. Under "Danger zone" → "Close project"
4. Confirm close

**Benefits**:
- Preserves history
- Board becomes read-only
- Can view for reference

### Step 5: Update SPRINT.md (5 min)

**Add sprint summary**:
```markdown
## Sprint 7: CrewAI Migration Foundation (Jan 2-15, 2026) ✅ COMPLETE

### Sprint Goal
Implement CrewAI coordination layer to automate agent orchestration.

### Completed Work ✅
- [x] Story 1: Implement CrewAI coordinator base (#42) - 5 pts, P0
- [x] Story 2: Wire agents to coordinator (#43) - 3 pts, P0
- [x] Story 3: Add crew configuration system (#44) - 5 pts, P1
- [ ] Story 4: Document CrewAI integration (#45) - 2 pts, P2 ⚠️ DEFERRED

**Total Story Points**: 15 planned, 13 completed (87%)
**Sprint Rating**: 8/10
**Defect Escape Rate**: 0%

### Sprint 7 Retrospective
See [docs/RETROSPECTIVE_S7.md](docs/RETROSPECTIVE_S7.md)
```

### Step 6: Mark Sprint Complete (1 min)

```bash
python3 scripts/sprint_ceremony_tracker.py --end-sprint 7
```

**Output**:
```
✅ Sprint 7 marked complete
⚠️  Next: Complete retrospective before starting Sprint 8
```

---

## Troubleshooting

### "No stories found for Sprint 7"

**Cause**: SPRINT.md format incorrect

**Check**:
- Section header: `## Sprint 7: Title`
- Story header: `#### Story N: Title`

**Fix**: Update SPRINT.md format

### "GITHUB_TOKEN not set"

**Cause**: Environment variable missing

**Fix**:
```bash
# Create token at: https://github.com/settings/tokens
# Permissions: repo (full)
export GITHUB_TOKEN='ghp_...'

# Or add to ~/.zshrc
echo 'export GITHUB_TOKEN="ghp_..."' >> ~/.zshrc
source ~/.zshrc
```

### "Failed to create issue: API rate limit"

**Cause**: Too many API calls

**Fix**:
- Wait 1 hour for rate limit reset
- Use personal access token (higher limits)
- Check rate limit: `gh api rate_limit`

### GitHub Actions not updating SPRINT.md

**Causes**:
- Issue missing `sprint-story` label
- Issue missing `sprint-N` label
- Workflow file syntax error
- GITHUB_TOKEN permissions

**Check**:
1. Issue labels: Must have both `sprint-story` AND `sprint-7`
2. Actions logs: Repository → Actions → sprint-sync
3. Workflow syntax: `.github/workflows/sprint-sync.yml`

**Fix**:
```bash
# Manual fallback
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

### Sync creating duplicate issues

**Cause**: Running --push-to-github twice

**Prevention**: Always use --dry-run first

**Fix**: Close duplicate issues manually
```bash
gh issue close 123 --comment "Duplicate" --repo oviney/economist-agents
```

---

## Best Practices

### ✅ Always validate before sync
```bash
python3 scripts/github_sprint_sync.py --validate-sprint 7
```

### ✅ Use dry-run first
```bash
python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run
```

### ✅ Pull status at sprint end
```bash
python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7
```

### ✅ Close milestone when done
```bash
gh milestone close "Sprint 7: Title"
```

### ✅ Archive Project board
Provides historical record for metrics

### ✅ Complete retrospective
Blocks next sprint start (by design)

---

## Metrics & Reports

### Sprint Velocity
```bash
# View sprint history
cat skills/sprint_history.json | jq '.sprints[] | {sprint, velocity, completion_rate}'
```

### Defect Escape Rate
```bash
# View defect tracker
python3 scripts/defect_tracker.py
```

### GitHub Insights
- Repository → Insights → Pulse (weekly activity)
- Repository → Insights → Contributors (commit activity)
- Project board → Insights (burndown chart)

---

## Quick Reference

| Task | Command |
|------|---------|
| Validate sprint | `python3 scripts/github_sprint_sync.py --validate-sprint 7` |
| Dry run sync | `python3 scripts/github_sprint_sync.py --push-to-github --sprint 7 --dry-run` |
| Create issues | `python3 scripts/github_sprint_sync.py --push-to-github --sprint 7` |
| Pull status | `python3 scripts/github_sprint_sync.py --pull-from-github --sprint 7` |
| Show status | `python3 scripts/github_sprint_sync.py --show-github-status` |
| Create milestone | `gh milestone create "Sprint N: Title" --due-date YYYY-MM-DD` |
| Close milestone | `gh milestone close "Sprint N: Title"` |
| List issues | `gh issue list --label "sprint-7"` |
| List PRs | `gh pr list --label "sprint-7"` |
| Generate retro | `python3 scripts/sprint_ceremony_tracker.py --retrospective 7` |
| End sprint | `python3 scripts/sprint_ceremony_tracker.py --end-sprint 7` |

---

## Additional Resources

- [GITHUB_SPRINT_INTEGRATION.md](GITHUB_SPRINT_INTEGRATION.md) - Original integration guide
- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [SPRINT_CEREMONY_GUIDE.md](SPRINT_CEREMONY_GUIDE.md) - Ceremony workflows
- [.github/agents/scrum-master.agent.md](../.github/agents/scrum-master.agent.md) - Agent reference
- [skills/sprint-management/SKILL.md](../skills/sprint-management/SKILL.md) - Skills documentation

---

**Last Updated**: 2026-01-02
**Version**: 2.0 (Full automation + bi-directional sync)
**Status**: Production-ready
