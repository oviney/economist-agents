# Sprint Discipline System - Quick Reference

## The Problem We Solved

**Sprint 1 Issue**: We jumped into implementing Nick Tune's quality system without proper sprint planning. This led to:
- No upfront estimation
- No progress tracking
- No clear prioritization
- Missed opportunity to align work to sprint goals

## The Solution: Enforced Sprint Discipline

We created a **meta-skill** that enforces sprint planning at every step.

---

## Daily Workflow

### Before Starting ANY Work

```bash
./scripts/pre_work_check.sh "Description of work"
```

**What it checks:**
1. ✅ Is there an active sprint?
2. ✅ Does this work match a sprint story?
3. ✅ Are acceptance criteria defined?
4. ✅ Is the story estimated?

**If checks fail:** You're BLOCKED until you fix the issue.

### Example: Valid Work

```bash
$ ./scripts/pre_work_check.sh "Validate Quality System in Production"

✅ Active Sprint: Sprint 2 - Iterate & Validate
✅ Matched to Story 1: Validate Quality System in Production
✅ Acceptance criteria defined
✅ Story estimated at 2 points

ALL CHECKS PASSED - You're clear to start work!
```

### Example: Invalid Work (Blocked)

```bash
$ ./scripts/pre_work_check.sh "Build random feature not in sprint"

❌ [CRITICAL] work_without_planning
   'Build random feature not in sprint' doesn't match any sprint story

ACTION REQUIRED:
   Add this work to sprint backlog OR wait until next sprint.

Command exited with code 1  ← Blocks you from starting
```

---

## During Work

### Track Progress in SPRINT.md

As you complete tasks, update checkboxes:

```markdown
#### Story 1: Validate Quality System in Production
- [x] Generate article with new self-validating agents
- [x] Observe self-validation logs
- [ ] Verify regeneration triggers
- [ ] Document effectiveness
```

### Check Sprint Health

```bash
python3 scripts/sprint_validator.py --validate-sprint
```

Shows:
- Sprint progress (stories/points completed)
- Remaining tasks per story
- On-track status

---

## End of Sprint

### Validate Sprint Completion

```bash
python3 scripts/sprint_validator.py --check-sprint-complete
```

**Checks:**
1. ✅ All stories complete?
2. ✅ Retrospective documented?

**Blocks sprint close if incomplete.**

### Required Retrospective

Answer in SPRINT.md:
1. What went well?
2. What could improve?
3. Action items for next sprint

**Sprint not complete until retrospective is done.**

---

## Skills System Integration

The sprint discipline skills live in `skills/blog_qa_skills.json`:

### 6 Learned Patterns

1. **work_without_planning** (critical)
   - Starting implementation without sprint story
   - Prevention: STOP and create sprint story first

2. **scope_creep_mid_sprint** (high)
   - Adding new work during active sprint
   - Prevention: Only add if P0 bug, else next sprint

3. **missing_progress_tracking** (medium)
   - Not updating SPRINT.md daily
   - Prevention: Update task checkboxes in commits

4. **skipped_retrospective** (high)
   - Completing sprint without retrospective
   - Prevention: Schedule retro as final sprint task

5. **work_without_acceptance_criteria** (high)
   - Starting story without definition of done
   - Prevention: Define AC before implementation

6. **unestimated_work** (medium)
   - Working on story without story points
   - Prevention: Estimate using 1/2/3/5/8 scale

---

## Files in This System

| File | Purpose |
|------|---------|
| `SPRINT.md` | Active sprint plan, stories, progress |
| `scripts/sprint_validator.py` | Validation engine (Python) |
| `scripts/pre_work_check.sh` | Pre-work checklist (Bash) |
| `skills/blog_qa_skills.json` | Learned patterns (sprint_discipline) |
| `README.md` | Updated with sprint requirements |

---

## Commit Message Format

Always reference story number:

```bash
git commit -m "Story 1: Validate quality system in production

- Generated article with self-validating agents
- Observed regeneration on critical issues
- Documented 80% improvement in validation

Progress: Story 1 complete (2/8 points done)"
```

---

## Rules (From skills/blog_qa_skills.json)

### Before Implementation
- [ ] Active sprint exists
- [ ] Work maps to sprint story
- [ ] Acceptance criteria defined
- [ ] Story points estimated

### During Sprint
- [ ] Update SPRINT.md task checkboxes daily
- [ ] Reference story number in commits
- [ ] Run tests before committing
- [ ] Check sprint health regularly

### End of Sprint
- [ ] All stories complete
- [ ] Retrospective documented
- [ ] Calculate actual velocity
- [ ] Plan next sprint

---

## Benefits

1. **Prevents Scope Creep**: Can't start unplanned work
2. **Forces Planning**: Must define AC and estimate first
3. **Tracks Progress**: Daily visibility into sprint health
4. **Ensures Learning**: Retrospectives mandatory
5. **Builds Velocity**: Historical data for planning

---

## Next Steps

Now that sprint discipline is enforced, we can:

1. ✅ Start Story 1 with confidence (it's properly planned)
2. ✅ Track progress systematically
3. ✅ Complete Sprint 2 with full retrospective
4. ✅ Use velocity data for Sprint 3 planning

**To start work on Story 1:**

```bash
./scripts/pre_work_check.sh "Validate Quality System in Production"
# ... checks pass ...
# Start implementation!
```

---

## Maintenance

The system is self-documenting:
- Update SPRINT.md as you go
- Skills learn from violations (future enhancement)
- Sprint validator enforces rules automatically

**No manual governance needed** - the tools enforce discipline.
