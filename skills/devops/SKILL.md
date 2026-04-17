---
name: devops
description: Infrastructure automation, CI/CD pipeline health, and GitHub Projects integration. Use when configuring CI workflows, when setting up GitHub Projects, when automating sprint visibility, when debugging deployment pipelines.
---

# DevOps

## Overview

Responsible for infrastructure automation, CI/CD pipeline health, and GitHub project tracking. Primary mission: enable autonomous sprint visibility through GitHub Projects v2, automated reporting, and deployment reliability.

## When to Use

- Setting up or modifying CI/CD workflows (GitHub Actions)
- Configuring GitHub Projects v2 (boards, views, custom fields)
- Automating sprint visibility (burndown, velocity, status sync)
- Debugging deployment pipelines or infrastructure issues
- Managing GitHub token scopes and permissions

### When NOT to Use

- For sprint ceremony process — that's `scrum-master`
- For code quality standards — that's `python-quality`
- For pre-commit hook configuration — that's `quality-gates`
- For agent assignment — that's `agent-delegation`

## Core Process

### CI/CD Pipeline Architecture

```
Push/PR to main
  ↓
GitHub Actions: quality-tests.yml
  ├── ruff format --check
  ├── ruff check
  ├── pytest (Python 3.11, 3.12 matrix)
  └── security scan (bandit)
  ↓
Branch protection: require CI pass + PR approval
  ↓
Merge to main
  ↓
Content pipeline (content-pipeline.yml) — on schedule or dispatch
  ├── Topic discovery
  ├── Editorial review
  ├── Content generation
  ├── Quality gates
  └── Blog deployment
```

### GitHub Projects v2 Setup

**Required token scopes:**
```bash
gh auth refresh -s project
gh auth status  # verify: project, read:org, repo, workflow
```

**Board creation and configuration:**
```bash
gh project create "Sprint N: Title" --owner oviney --format "Board"
```

**Custom fields:** Sprint (single select), Story Points (number), Priority (single select), Owner (single select).

**Views:** Kanban (status lanes), Table (sortable), Roadmap (timeline).

### Sprint Tracking Automation

| Component | Purpose | Location |
|-----------|---------|----------|
| `sprint_tracker.json` | Sprint state, velocity, completion | `data/skills_state/` |
| `github_sprint_sync.py` | Bidirectional SPRINT.md <-> GitHub | `scripts/` |
| `sprint-sync.yml` | Auto-update on issue close | `.github/workflows/` |
| `sprint-discipline.yml` | Commit message enforcement | `.github/workflows/` |

### Deployment Pipeline

**Content pipeline stages:**
1. Topic Scout discovers topics
2. Editorial Board votes
3. Stage 3 generates article (research, graphics, writing)
4. Stage 4 reviews (quality gate, schema validation, publication validation)
5. Deploy to blog repo if quality gate passes

**Key configuration:**
- `BLOG_REPO_TOKEN` — auth for blog repo push
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — LLM API access
- `SERPER_API_KEY` — Google Scholar/web search (optional)

### Monitoring and Reporting

| Metric | Source | Automation |
|--------|--------|-----------|
| Sprint velocity | `sprint_tracker.json` | `generate_sprint_badge.py` |
| Test count | pytest discovery | `generate_tests_badge.py` |
| Quality score | `quality_dashboard.py` | `quality_score.json` |
| CI pass rate | GitHub Actions API | `gh run list` |
| Content pipeline success | `content-pipeline.yml` logs | Manual review |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Manual deployment is fine for now" | Manual steps are forgotten steps — automate the pipeline and catch failures in CI |
| "We don't need GitHub Projects, issues are enough" | Issues track work; Projects track flow — burndown and velocity need the structured views |
| "Token scope refresh is risky" | `gh auth refresh -s project` adds scope without invalidating existing permissions |
| "We'll monitor CI manually" | Unmonitored pipelines fail silently — badge automation makes failures visible in README |
| "The pipeline works locally, CI will be fine" | Local has different env vars, Python versions, and dependencies — CI is the source of truth |

## Red Flags

- CI pipeline failing on main branch (broken build)
- GitHub token missing required scopes (project, repo, workflow)
- Sprint tracker and GitHub issues out of sync
- Content pipeline running without quality gate checks
- Badge JSON files stale (not reflecting actual metrics)
- Deployment to blog repo without `BLOG_REPO_TOKEN` verification
- Workflow files modified without testing in a PR first

## Verification

- [ ] CI runs on every PR to main — **evidence**: `gh run list` shows recent runs for PRs
- [ ] Quality tests pass: ruff, pytest, security scan — **evidence**: green CI checks on latest PR
- [ ] GitHub Projects board exists for current sprint — **evidence**: `gh project list` shows board
- [ ] Sprint tracker in sync with GitHub — **evidence**: `github_sprint_sync.py --show-github-status` shows no discrepancies
- [ ] Badges reflect current metrics — **evidence**: `validate_badges.py` passes
- [ ] Content pipeline deploys successfully — **evidence**: latest `content-pipeline.yml` run is green

### Integration Points

- `.github/workflows/quality-tests.yml` — CI quality checks
- `.github/workflows/content-pipeline.yml` — article generation and deployment
- `.github/workflows/sprint-sync.yml` — sprint status auto-update
- `scripts/github_sprint_sync.py` — bidirectional sprint sync
- `scripts/validate_badges.py` ��� badge accuracy validation
- `data/skills_state/sprint_tracker.json` — sprint state tracking
