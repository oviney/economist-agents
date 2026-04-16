---
name: sprint-management
description: GitHub-integrated sprint lifecycle management with automated sync. Use when starting a sprint, when syncing sprint status with GitHub, when closing a sprint with retrospective.
---

# Sprint Management

## Overview

Manages the full sprint lifecycle — planning, execution, and close — with bidirectional sync between SPRINT.md and GitHub Issues/Milestones. Enforces ceremony completion and story validation before sprints can start.

## When to Use

- Starting a new sprint (validation, milestone creation, issue sync)
- During sprint execution (status checks, issue tracking)
- Closing a sprint (retrospective, milestone close, metrics)
- Syncing SPRINT.md with GitHub issue state

### When NOT to Use

- For agent assignment decisions — that's `agent-delegation`
- For code quality enforcement — that's `quality-gates`
- For ADR lifecycle — that's `adr-governance`
- For scrum master ceremony protocol — that's `scrum-master`

## Core Process

### Sprint Start

```
1. Check ceremonies complete:  sprint_ceremony_tracker.py --can-start N
   ↓
2. Validate sprint stories:   github_sprint_sync.py --validate-sprint N
   (points >0, acceptance criteria present, priority set)
   ↓
3. Create milestone:          gh milestone create "Sprint N: Title" --due-date DATE
   ↓
4. Preview sync:              github_sprint_sync.py --push-to-github --sprint N --dry-run
   ↓
5. Create GitHub issues:      github_sprint_sync.py --push-to-github --sprint N
```

### Sprint Execution

```
Daily:  github_sprint_sync.py --show-github-status
        gh issue list --label "sprint-N" --state open

On PR merge:
  - GitHub Actions auto-updates SPRINT.md
  - Issues auto-closed via "Closes #N" in PR

Manual sync if needed:
  github_sprint_sync.py --pull-from-github --sprint N
```

### Sprint Close

```
1. Pull final status:     github_sprint_sync.py --pull-from-github --sprint N
   ↓
2. Generate retrospective: sprint_ceremony_tracker.py --retrospective N
   ↓
3. Close milestone:        gh milestone close "Sprint N: Title"
   ↓
4. Mark sprint complete:   sprint_ceremony_tracker.py --end-sprint N
```

### Learned Anti-Patterns

| Pattern | Severity | Prevention |
|---------|----------|-----------|
| Work without planning | CRITICAL | `--validate-sprint` before `--push-to-github` |
| Scope creep mid-sprint | HIGH | Lock backlog after sync to GitHub |
| Missing progress tracking | MEDIUM | Daily `--show-github-status` |
| Skipped retrospective | HIGH | `--can-start N` blocks without retro |
| Work without acceptance criteria | HIGH | `--validate-sprint` checks ACs |
| Unestimated work | MEDIUM | `--validate-sprint` checks points >0 |

### Tools Reference

| Tool | Purpose |
|------|---------|
| `scripts/github_sprint_sync.py` | SPRINT.md <-> GitHub sync |
| `scripts/sprint_ceremony_tracker.py` | Ceremony enforcement |
| `scripts/sprint_validator.py` | SPRINT.md structure validation |
| `gh` CLI | Milestone/issue management |
| `.github/workflows/sprint-sync.yml` | Auto-update on issue close |
| `.github/workflows/sprint-discipline.yml` | Commit message enforcement |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "We'll track this informally, no need for GitHub issues" | Informal tracking breaks audit trail and sprint velocity metrics |
| "Validation is too strict — we'll add ACs later" | Stories without acceptance criteria can't be verified as done |
| "Skip the retrospective, we know what happened" | `--can-start` blocks for a reason — unexamined patterns repeat |
| "Dry-run is unnecessary, just sync directly" | Dry-run catches duplicate issues, missing labels, and milestone conflicts before they happen |
| "We can add stories mid-sprint" | Scope creep is the #1 sprint failure mode; lock the backlog after sync |

## Red Flags

- Sprint started without `--validate-sprint` passing
- Stories missing points, acceptance criteria, or priority
- No milestone created for the sprint
- SPRINT.md and GitHub issues out of sync for >1 day
- Retrospective skipped before starting next sprint
- Stories added after sprint start without explicit scope change
- Commit messages don't reference story numbers

## Verification

- [ ] All stories have points >0, ACs, and priority — **evidence**: `--validate-sprint` passes
- [ ] Milestone exists with correct name and due date — **evidence**: `gh milestone list` shows sprint
- [ ] All stories have GitHub issues — **evidence**: `gh issue list --label sprint-N` count matches story count
- [ ] SPRINT.md and GitHub in sync — **evidence**: `--show-github-status` shows no discrepancies
- [ ] Previous sprint has retrospective — **evidence**: `--can-start N` passes
- [ ] All PRs reference issue numbers — **evidence**: `sprint-discipline.yml` CI check passes
