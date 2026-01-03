# STORY-053: GitHub Project Board Setup - DevOps Assignment

**Agent**: @devops  
**Story Points**: 2  
**Priority**: P1  
**Sprint**: 9  
**Status**: assigned  
**Assigned Date**: 2026-01-03  

---

## Context

The `sync_github_project.py` script is ready but fails when GitHub labels don't exist. User requires full automation with no manual steps. This work must be tracked for agent performance metrics.

**Error Encountered**:
```
could not add label: 'story-points-2' not found
```

## Objective

Enable browser-based sprint tracking via GitHub Project board with full automation and proper label management.

## Tasks

### 1. Enhance Label Management (30 min)
**File**: `scripts/sync_github_project.py`

Add automatic label creation with proper error handling:
- Add `ensure_labels_exist()` method to GitHubProjectSync class
- Check if labels exist before using them
- Auto-create missing labels with appropriate colors:
  - `sprint-9` (color: #0052CC)
  - `story-points-1` through `story-points-8` (color: #FFA500)
  - `p0`, `p1`, `p2` (colors: #D73A4A, #FF9800, #4CAF50)
- Make script idempotent (safe to run multiple times)

### 2. Create GitHub Issue for Story 6 (5 min)
Use enhanced script or gh CLI to create issue for STORY-053 with:
- Title: "STORY-053: GitHub Project Board Setup"
- Body: User story with acceptance criteria
- Labels: sprint-9, story-points-2, p1
- Auto-handle missing labels

### 3. Execute Board Creation (10 min)
Run: `python3 scripts/sync_github_project.py --create`
- Create GitHub Project board for Sprint 9
- Convert all 7 stories from sprint_tracker.json to GitHub issues
- Link issues to project board

### 4. Verification (5 min)
Confirm:
- All Sprint 9 stories visible as issues
- Project board accessible at github.com/oviney/economist-agents/projects/N
- Labels created correctly
- Script can be re-run without errors

### 5. Performance Metrics (5 min)
Document in completion report:
- Total execution time
- Issues created (count)
- Labels created (count)
- Project URL
- Any errors/warnings

## Success Criteria

- [ ] GitHub Project board created and accessible in browser
- [ ] All 7 Sprint 9 stories exist as GitHub issues
- [ ] All required labels exist in repository
- [ ] Script runs without errors (idempotent)
- [ ] Browser-based sprint tracking operational
- [ ] Completion metrics documented

## Deliverables

1. Enhanced `scripts/sync_github_project.py` with label management
2. GitHub Project board at github.com/oviney/economist-agents/projects/N
3. 7 GitHub issues for Sprint 9 stories
4. Completion report: `tasks/STORY-053-completion.md`

## Estimated Time

**Total**: 55 minutes (within 2 story points @ 2.8h/point = 5.6h budget)

## Dependencies

- GitHub CLI (gh) - authenticated in workspace ✅
- Python 3.13 virtual environment ✅
- sprint_tracker.json with Sprint 9 data ✅

## Notes for CrewAI Migration

This task format is designed for future automation:
- Clear task breakdown with time estimates
- Explicit success criteria (checkboxes)
- Structured deliverables list
- Machine-parseable metrics requirements
- Self-contained context and dependencies

---

**Handoff to @devops**: Execute tasks 1-5 and report completion metrics.
