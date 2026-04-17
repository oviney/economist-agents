---
name: scrum-master
description: Sprint orchestration, ceremony enforcement, and data-driven performance tracking. Use when running sprint ceremonies, when enforcing Definition of Ready/Done, when tracking sprint metrics, when managing blockers.
---

# Scrum Master

## Overview

The sprint orchestrator, process enforcer, and team facilitator. Maintains Agile discipline, ensures quality gates are met, and removes impediments to velocity. Quality over schedule, every single time.

## When to Use

- Running any sprint ceremony (planning, standup, review, retro, refinement)
- Validating Definition of Ready before sprint start
- Validating Definition of Done before marking stories complete
- Tracking sprint metrics and velocity
- Escalating and resolving blockers
- Updating sprint documentation after ceremonies

### When NOT to Use

- For GitHub issue sync mechanics — that's `sprint-management`
- For agent assignment decisions — that's `agent-delegation`
- For code quality enforcement — that's `quality-gates`
- For ADR lifecycle — that's `adr-governance`

## Core Process

### Sprint Ceremonies

| Ceremony | Duration | Trigger | Output |
|----------|----------|---------|--------|
| **Planning** | 2-4 hours | Sprint start | Sprint backlog, GitHub Issues, SPRINT.md |
| **Daily Standup** | 15 minutes | Every day | Updated tracker, blocker log |
| **Review** | 1-2 hours | Sprint end | Metrics report, stakeholder feedback |
| **Retrospective** | 1-2 hours | Sprint end | RETROSPECTIVE_SN.md, process improvements |
| **Refinement** | 1-2 hours | Weekly | Estimated stories ready for next sprint |

### Sprint Planning Gate

Cannot start sprint unless:
- All stories pass Definition of Ready (12-point checklist)
- Capacity calculated (velocity x sprint length x availability)
- Dependencies and risks identified
- Previous sprint retrospective completed

### Sprint Documentation Update (Post-Retro)

```
1. [ ] Update CHANGELOG.md with sprint entry
2. [ ] Update README.md project status
3. [ ] Update SPRINT.md header
4. [ ] Update sprint_badge.json
5. [ ] Update data/skills_state/sprint_tracker.json (current_sprint = N)
6. [ ] Update tests_badge.json if count changed
7. [ ] Commit all docs atomically
8. [ ] Push to GitHub immediately
```

### Blocker Escalation Protocol

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| P0 (Critical) | 2 hours | Engineering Lead immediately |
| P1 (High) | 4 hours | Engineering Lead same day |
| P2 (Medium) | Next standup | Team discussion |
| P3 (Low) | Next refinement | Backlog grooming |

### Definition of Ready (12-Point)

1. Clear title and description
2. Acceptance criteria defined
3. Story points estimated
4. Priority assigned (P0-P3)
5. Dependencies identified
6. Design/architecture reviewed (if applicable)
7. Test approach defined
8. Agent runtime assigned (per `agent-delegation`)
9. No unresolved blockers
10. Fits within sprint capacity
11. GitHub Issue created
12. Linked to sprint milestone

### Definition of Done

1. All acceptance criteria met
2. Tests written and passing (≥80% coverage)
3. Code reviewed and approved
4. Documentation updated
5. Sprint documentation updated (CHANGELOG, badges, tracker)
6. GitHub Issue closed with "Closes #N" in PR
7. No known defects introduced

### Metrics Tracked

| Metric | Target | Frequency |
|--------|--------|-----------|
| Velocity (points/sprint) | Stable ±20% | Per sprint |
| Completion rate | ≥80% | Per sprint |
| Defect escape rate | <10% | Per sprint |
| Sprint rating | ≥7/10 | Per sprint |
| Blocker resolution time | P0 <2h, P1 <4h | Per blocker |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "We can skip the retro, we know what happened" | `--can-start` blocks without retro for a reason — unexamined patterns repeat across sprints |
| "This story is ready enough, we'll refine during the sprint" | Stories that skip DoR validation cause mid-sprint scope changes and velocity drops |
| "We'll update the docs later" | Sprint 14 shipped without updating CHANGELOG, README, or badges — added mandatory checklist to prevent recurrence |
| "The blocker isn't critical, we'll work around it" | Unresolved blockers compound; a P2 today becomes a P0 when it blocks the next story |
| "We can take on more points this sprint" | Overcommitment is the #1 cause of incomplete sprints — trust the velocity data |

## Red Flags

- Sprint started without DoR validation for all stories
- Retrospective skipped before starting next sprint
- Documentation not updated after sprint completion (CHANGELOG, badges, tracker)
- P0 blocker without resolution plan within 2 hours
- Stories added mid-sprint without explicit scope change approval
- Velocity fluctuating >30% sprint over sprint (unstable estimation)
- Stories marked "done" without meeting Definition of Done
- No daily standup for 2+ consecutive days

## Verification

- [ ] All stories pass DoR before sprint starts — **evidence**: `sprint_ceremony_tracker.py --can-start N` passes
- [ ] All ceremonies completed — **evidence**: ceremony tracker shows all 5 ceremonies done
- [ ] Sprint documentation updated — **evidence**: CHANGELOG, README, badges, tracker all reflect current sprint
- [ ] All completed stories meet DoD — **evidence**: PRs closed with CI green, tests passing, docs updated
- [ ] Retrospective produced 1-3 actionable improvements — **evidence**: RETROSPECTIVE_SN.md has action items with owners
- [ ] Metrics tracked and visible — **evidence**: `data/skills_state/sprint_tracker.json` has velocity and completion data

### Integration Points

- `scripts/sprint_ceremony_tracker.py` — ceremony enforcement
- `scripts/github_sprint_sync.py` — GitHub issue sync
- `data/skills_state/sprint_tracker.json` — sprint state and metrics
- `data/skills_state/defect_tracker.json` — defect tracking with RCA
- `docs/SCRUM_MASTER_PROTOCOL.md` — detailed ceremony protocols
