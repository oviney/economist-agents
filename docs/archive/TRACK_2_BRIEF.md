# Track 2 Brief: BUG-023 - README Badge Regression Fix

**Assigned to**: @quality-enforcer
**Story Points**: 2
**Priority**: P0
**Sprint**: Sprint 7

---

## Bug Context

**BUG-023** (GitHub Issue #38): README badges show stale/incorrect data

**Impact**: New developers and stakeholders see incorrect metrics, undermining documentation trust.

**Root Cause**: Hardcoded badge values instead of dynamic data sources.

## Current Badge Issues (VERIFICATION NEEDED)

From `/Users/ouray.viney/code/economist-agents/README.md` (lines 1-50):

```markdown
[![Quality Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/quality_score.json)](https://github.com/oviney/economist-agents/blob/main/docs/QUALITY_DASHBOARD.md)
![Sprint](https://img.shields.io/badge/Sprint-7-blue)
```

**Badge 1: Quality Score** (shields.io endpoint badge)
- Source: `quality_score.json` in repo
- Current: Unknown (needs verification)
- Expected: Latest quality_dashboard.py output

**Badge 2: Sprint** (static badge)
- Current: `![Sprint](https://img.shields.io/badge/Sprint-7-blue)`
- Problem: Hardcoded value, not synced with SPRINT.md or sprint_tracker.json
- Expected: Dynamic badge reading from sprint_tracker.json

**Missing Badges** (from defect tracker investigation):
- **Coverage**: Should reflect 52% actual (from pytest coverage)
- **Tests**: Should reflect 166 passing (from CI test results)

## Your Task

### 1. Audit Current Badges

Verify accuracy of all badges in README.md:
- Quality Score: Check quality_score.json matches badge
- Sprint: Check sprint_tracker.json current_sprint vs badge
- CI badges: Verify GitHub Actions workflow badges are correct

### 2. Fix Stale Badges

**Sprint Badge**: Convert from static to dynamic
```markdown
# BEFORE (hardcoded)
![Sprint](https://img.shields.io/badge/Sprint-7-blue)

# AFTER (dynamic from shields.io)
![Sprint](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/sprint_badge.json)
```

**Required**: Create `sprint_badge.json` generator:
- Read `skills/sprint_tracker.json`
- Extract `current_sprint`
- Generate shields.io JSON endpoint format:
```json
{
  "schemaVersion": 1,
  "label": "Sprint",
  "message": "7",
  "color": "blue"
}
```

### 3. Add Missing Badges

**Coverage Badge** (from pytest):
```markdown
![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/coverage_badge.json)
```

**Tests Badge** (from pytest):
```markdown
![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/tests_badge.json)
```

### 4. Badge Validation Hook

Create `scripts/validate_badges.py`:
- Verify all badge URLs return 200 status
- Verify dynamic badges have valid JSON endpoints
- Verify badge values match source data (quality_score.json, sprint_tracker.json)
- Can be run as pre-commit hook

### 5. Documentation

Update README.md with:
- Badge configuration section
- How to update badge endpoints
- GitHub Actions integration for badge generation

## Acceptance Criteria

- [ ] All badges verified for accuracy
- [ ] Sprint badge converted to dynamic (shields.io endpoint)
- [ ] Coverage badge added with pytest data
- [ ] Tests badge added with CI data
- [ ] `scripts/generate_sprint_badge.py` created
- [ ] `scripts/generate_coverage_badge.py` created
- [ ] `scripts/generate_tests_badge.py` created
- [ ] `scripts/validate_badges.py` created
- [ ] Pre-commit hook configured to run badge validation
- [ ] README.md badges section documented
- [ ] BUG-023 marked fixed in `skills/defect_tracker.json`
- [ ] Prevention strategy documented (add badge validation to CI)

## Files to Modify

1. `README.md` - Update badge markdown
2. `scripts/generate_sprint_badge.py` - NEW
3. `scripts/generate_coverage_badge.py` - NEW
4. `scripts/generate_tests_badge.py` - NEW
5. `scripts/validate_badges.py` - NEW
6. `.pre-commit-config.yaml` - Add badge validation hook
7. `skills/defect_tracker.json` - Mark BUG-023 fixed
8. `.github/workflows/badges.yml` - NEW (optional: automate badge generation)

## Implementation Notes

**Shields.io Endpoint Format**:
```json
{
  "schemaVersion": 1,
  "label": "Badge Label",
  "message": "Value",
  "color": "blue"
}
```

**Badge Colors**:
- Quality: green (>80), yellow (60-80), red (<60)
- Coverage: green (>80%), yellow (50-80%), red (<50%)
- Tests: green (all passing), red (failures)
- Sprint: blue (always)

**GitHub Actions Integration** (optional enhancement):
- Trigger badge generation on push to main
- Commit updated badge JSON files
- Ensures badges always reflect latest state

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code passes quality checks (ruff, mypy)
- [ ] Badge validation tests pass
- [ ] README.md badges display correctly on GitHub
- [ ] BUG-023 closed in defect tracker
- [ ] Prevention documented (badge validation in CI)

## Estimated Duration

1-2 hours

## Checkpoint

Report progress at 2-hour mark (should be complete by then) to Scrum Master in SPRINT_7_PARALLEL_EXECUTION_LOG.md

---

**Status**: 🟢 READY TO START
**Assigned Agent**: @quality-enforcer
**Start Time**: TBD
