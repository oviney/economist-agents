# Sprint Ceremony Guide

Complete guide to using the Sprint Ceremony Tracker to enforce Definition of Ready and maintain Agile discipline.

## Overview

The Sprint Ceremony Tracker prevents Definition of Ready violations by:
- Tracking sprint state and ceremony completion
- Blocking sprint planning without proper ceremonies
- Generating ceremony templates automatically
- Enforcing 8-point DoR checklist
- Providing audit trail of process compliance

## Quick Start

### End of Sprint Workflow

```bash
# 1. Mark sprint as complete
python3 scripts/sprint_ceremony_tracker.py --end-sprint 6

# 2. Complete retrospective (generates template)
python3 scripts/sprint_ceremony_tracker.py --retrospective 6
# Edit: docs/RETROSPECTIVE_S6.md

# 3. Refine backlog for next sprint (generates template)
python3 scripts/sprint_ceremony_tracker.py --refine-backlog 7
# Edit: docs/SPRINT_7_BACKLOG.md

# 4. Validate Definition of Ready
python3 scripts/sprint_ceremony_tracker.py --validate-dor 7

# 5. Check if sprint can start
python3 scripts/sprint_ceremony_tracker.py --can-start 7
# ✅ Sprint 7 ready to start - all ceremonies complete

# 6. View status anytime
python3 scripts/sprint_ceremony_tracker.py --report
```

## Architecture

```
Sprint State (sprint_tracker.json)
    ↓
Ceremony Validation (sprint_ceremony_tracker.py)
    ↓
DoR Enforcement (8-point checklist)
    ↓
Template Generation (retrospective, backlog)
    ↓
Sprint Ready Gate (can_start_sprint)
```

## Commands Reference

### --end-sprint N

Marks sprint N as complete and initializes ceremony tracking.

```bash
python3 scripts/sprint_ceremony_tracker.py --end-sprint 6
```

**Output:**
```
✅ Sprint 6 marked complete
⚠️  Next: Complete retrospective before starting Sprint 7
```

**State Changes:**
- Sets sprint status to "complete"
- Records end date
- Initializes ceremony flags (all false)
- Updates current_sprint pointer

### --retrospective N

Completes retrospective ceremony and generates template.

```bash
python3 scripts/sprint_ceremony_tracker.py --retrospective 6
```

**Output:**
```
✅ Sprint 6 retrospective complete
📝 Template generated: docs/RETROSPECTIVE_S6.md
   Edit template, then run: --refine-backlog 7
```

**Template Sections:**
- What Went Well ✅
- What Needs Improvement ⚠️
- Action Items 🎯
- Insights for Next Sprint 💡
- Sprint Summary

**State Changes:**
- Sets `retrospective_done: true`
- Records retrospective date

### --refine-backlog N

Completes backlog refinement and generates story template.

```bash
python3 scripts/sprint_ceremony_tracker.py --refine-backlog 7
```

**Output:**
```
✅ Sprint 7 backlog refinement complete
📝 Story template generated: docs/SPRINT_7_BACKLOG.md
   Fill in stories, then run: --validate-dor 7
```

**Template Sections:**
- Sprint Goal
- Story 1, 2, 3... (with full structure)
  - User Story (As a/I need/So that)
  - Acceptance Criteria (Given/When/Then)
  - Definition of Done
  - Story Points
  - Task Breakdown
- Three Amigos Review Notes
- Sprint Scope

**State Changes:**
- Sets `backlog_refined: true`
- Records refinement date

### --validate-dor N

Validates Definition of Ready for sprint N.

```bash
python3 scripts/sprint_ceremony_tracker.py --validate-dor 7
```

**Success Output:**
```
✅ Sprint 7 Definition of Ready MET
   All 8 DoR criteria passed
   Sprint 7 ready to start
```

**Failure Output:**
```
❌ Sprint 7 Definition of Ready NOT MET
   3 criteria missing:

   • Stories have placeholder titles
   • Acceptance criteria not defined
   • Story points not estimated
```

**8-Point DoR Checklist:**
1. ✓ Story written with clear goal
2. ✓ Acceptance criteria defined
3. ✓ Three Amigos review complete
4. ✓ Dependencies identified
5. ✓ Risks documented
6. ✓ Story points estimated
7. ✓ Definition of Done agreed
8. ✓ User/Product Owner approval

**Validation Logic:**
- Checks if backlog file exists
- Scans for placeholder text (e.g., `[Story Title]`)
- Verifies previous sprint retrospective done
- Validates all required fields filled
- Updates state if all checks pass

**State Changes:**
- Sets `next_sprint_dor_met: true` (if valid)

### --can-start N

Checks if sprint N can start (blocking operation).

```bash
python3 scripts/sprint_ceremony_tracker.py --can-start 7
```

**Success Output:**
```
✅ Sprint 7 ready to start - all ceremonies complete
```

**Exit code**: 0

**Blocked Output:**
```
❌ BLOCKED: Sprint 6 retrospective not complete
   Run: python3 sprint_ceremony_tracker.py --retrospective 6
```

**Exit code**: 1

**Use Cases:**
- Pre-sprint planning gate
- CI/CD integration (block deployment)
- Automated sprint start validation
- Process compliance checking

### --report

Generates ceremony status report.

```bash
python3 scripts/sprint_ceremony_tracker.py --report
```

**Sample Output:**
```
============================================================
SPRINT CEREMONY STATUS REPORT
============================================================
Generated: 2026-01-01 12:00:00

Current Sprint: 6

Sprint 6
----------------------------------------
  Status: complete
  Ended: 2026-01-01
  Retrospective: ✅ Done
    Completed: 2026-01-01
  Backlog Refined: ✅ Done
    Completed: 2026-01-01
  Next Sprint DoR: ✅ Met

NEXT ACTIONS
----------------------------------------
  ✅ All ceremonies complete - Sprint 7 ready to start
============================================================
```

**Use Cases:**
- Daily standup reference
- Sprint planning preparation
- Process audit trail
- Team visibility into ceremony status

### --test

Runs self-tests to validate tracker functionality.

```bash
python3 scripts/sprint_ceremony_tracker.py --test
```

**Output:**
```
============================================================
SPRINT CEREMONY TRACKER - SELF-TESTS
============================================================

Test 1: Sprint end and blocking logic
----------------------------------------
✅ Test 1 PASSED - Sprint 7 blocked without ceremonies

Test 2: Ceremony completion and DoR validation
----------------------------------------
✅ Test 2 PASSED - DoR validation caught 3 issues

Test 3: Full ceremony completion flow
----------------------------------------
✅ Test 3 PASSED - Sprint 7 can start after ceremonies

Test 4: Report generation
----------------------------------------
✅ Test 4 PASSED - Report generated successfully

============================================================
SELF-TESTS COMPLETE
============================================================
```

## Integration Points

### Pre-Commit Hook

Block commits mentioning "Sprint N" without DoR met:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check if CHANGELOG mentions new sprint
if grep -q "Sprint 7" CHANGELOG.md; then
    python3 scripts/sprint_ceremony_tracker.py --can-start 7 || {
        echo "❌ Sprint 7 not ready - complete ceremonies first"
        exit 1
    }
fi
```

### CI/CD Pipeline

GitHub Actions workflow:

```yaml
name: Sprint Validation

on:
  push:
    paths:
      - 'docs/SPRINT_*.md'
      - 'docs/CHANGELOG.md'

jobs:
  validate-sprint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check Sprint Readiness
        run: |
          SPRINT_NUM=$(grep -oP 'Sprint \K\d+' CHANGELOG.md | head -1)
          python3 scripts/sprint_ceremony_tracker.py --can-start $SPRINT_NUM
```

### Manual Workflow Integration

**Scrum Master Protocol Integration:**

Before any "What's next?" discussion:
1. Run `--report` to check ceremony status
2. If ceremonies incomplete, present that before options
3. Never discuss sprint objectives without DoR met
4. Use tracker output as decision gate

**Example:**
```python
# In Scrum Master decision logic
tracker = SprintCeremonyTracker()
if not tracker.can_start_sprint(7):
    return "BLOCKED: Complete ceremonies first (see --report)"
else:
    return present_sprint_options()
```

## File Locations

**Tracker State:**
- `skills/sprint_tracker.json` - Persistent state

**Generated Templates:**
- `docs/RETROSPECTIVE_S{N}.md` - Sprint N retrospective
- `docs/SPRINT_{N}_BACKLOG.md` - Sprint N backlog/stories

**Integration:**
- `.git/hooks/pre-commit` - Optional enforcement
- `.github/workflows/sprint-validation.yml` - CI/CD

## Troubleshooting

### Issue: "Sprint N not found in tracker"

**Cause:** Forgot to run `--end-sprint` first

**Fix:**
```bash
python3 scripts/sprint_ceremony_tracker.py --end-sprint 6
```

### Issue: DoR validation fails with placeholder errors

**Cause:** Template not fully edited

**Fix:**
1. Edit `docs/SPRINT_N_BACKLOG.md`
2. Replace all `[Story Title]`, `[role]`, `[capability]` placeholders
3. Fill in acceptance criteria, story points, tasks
4. Re-run `--validate-dor N`

### Issue: Can't start sprint despite completing ceremonies

**Cause:** DoR not validated after completing backlog

**Fix:**
```bash
python3 scripts/sprint_ceremony_tracker.py --validate-dor 7
```

### Issue: Lost sprint state after system crash

**Cause:** `sprint_tracker.json` corrupted

**Fix:**
1. Restore from backup (if available)
2. Or manually reconstruct state:
```json
{
  "current_sprint": 6,
  "sprints": {
    "sprint_6": {
      "status": "complete",
      "retrospective_done": true,
      "backlog_refined": true,
      "next_sprint_dor_met": true
    }
  }
}
```

## Best Practices

### Daily Standup Integration

Start each standup with:
```bash
python3 scripts/sprint_ceremony_tracker.py --report
```

Shows team what ceremonies are pending.

### Sprint Boundary Ritual

**Friday EOD (Last day of sprint):**
```bash
# 1. Mark sprint complete
python3 scripts/sprint_ceremony_tracker.py --end-sprint 6

# 2. Schedule retro for Monday morning
```

**Monday AM (First day between sprints):**
```bash
# 3. Run retrospective
python3 scripts/sprint_ceremony_tracker.py --retrospective 6

# 4. Refine backlog (entire team)
python3 scripts/sprint_ceremony_tracker.py --refine-backlog 7

# 5. Validate DoR before lunch
python3 scripts/sprint_ceremony_tracker.py --validate-dor 7

# 6. Start sprint planning (PM)
python3 scripts/sprint_ceremony_tracker.py --can-start 7
```

### Template Customization

Edit generated templates immediately:
1. Retrospective: Fill during ceremony
2. Backlog: Collaborative editing with team
3. Commit edited templates to git for history

### Audit Trail

All ceremony completion is timestamped:
- `retrospective_date`
- `refinement_date`
- `end_date`

Use `--report` to generate process compliance documentation.

## Metrics & Reporting

### Ceremony Velocity

Track time from sprint end to DoR met:
```bash
# Sprint end: 2026-01-01 17:00
# DoR met:    2026-01-02 12:00
# Velocity:   19 hours (good)
```

Target: <24 hours from sprint end to DoR met.

### DoR Compliance Rate

Track what % of sprints start with DoR met:
```
Sprints with DoR: 10
Total sprints: 10
Compliance: 100%
```

Target: 100% compliance (enforced by tracker).

### Common DoR Blockers

Track which checklist items fail most often:
- Story points not estimated (40%)
- Acceptance criteria incomplete (30%)
- Task breakdown missing (20%)
- Dependencies not documented (10%)

Use to improve template guidance.

## Future Enhancements

### Planned Features

1. **AI Story Generation**: Auto-generate story templates from user requests
2. **Velocity Tracking**: Calculate sprint velocity trends
3. **Burndown Charts**: Generate visual progress tracking
4. **Slack Integration**: Post ceremony reminders
5. **Jira Sync**: Two-way sync with external tools
6. **Sprint Metrics Dashboard**: HTML report generation

### Extensibility

The tracker is designed for extension:
```python
class CustomSprintTracker(SprintCeremonyTracker):
    def custom_validation(self, sprint_number):
        # Add custom DoR checks
        pass
```

## Related Documentation

- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [copilot-instructions.md](../copilot-instructions.md) - Quality culture
- [DEFECT_PREVENTION.md](DEFECT_PREVENTION.md) - Prevention pattern

---

**Version**: 1.0  
**Last Updated**: 2026-01-01  
**Status**: ✅ Production-ready
