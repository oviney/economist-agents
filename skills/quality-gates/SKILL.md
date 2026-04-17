---
name: quality-gates
description: Multi-layer quality gate strategy for automated checks at commit, push, and PR levels. Use when configuring pre-commit hooks, when setting up CI workflows, when debugging why a commit or push was blocked.
---

# Quality Gates

## Overview

Four-layer quality gate architecture that prevents defects from reaching production: pre-commit hooks (local), pre-push coverage (local), GitHub Actions CI (remote), and branch protection (policy).

## When to Use

- Setting up or modifying pre-commit hooks
- Configuring CI/CD quality workflows
- Debugging a blocked commit, push, or merge
- Adding a new quality check to any layer
- Reviewing branch protection settings

### When NOT to Use

- For Python coding standards — that's `python-quality`
- For test patterns and coverage strategies — that's `testing`
- For article/content quality — that's `article-evaluation`

## Core Process: 4-Layer Architecture

```
Layer 1: Pre-commit (blocks commit)
  ruff format → ruff check → badge validation → arch review → YAML/JSON checks
  ↓
Layer 2: Pre-push (blocks push)
  pytest with coverage (>80% required)
  ↓
Layer 3: GitHub Actions CI (blocks merge)
  Quality checks + tests (Python 3.11, 3.12) + security scan (bandit)
  ↓
Layer 4: Branch Protection (enforces policy)
  Require PR approval + CI pass + branch up-to-date
```

### Layer 1: Pre-commit Hooks

Configured in `.pre-commit-config.yaml`. Runs on every `git commit`.

| Hook | Purpose | Auto-fix? |
|------|---------|-----------|
| `ruff-format` | Code formatting | Yes |
| `ruff` | Linting | No (check only) |
| `badge-validation` | README badge accuracy | No |
| `adr-lint` | ADR numbering/status rules | No |
| `validate-agent-yaml` | Agent YAML schema | No |
| `arch-review` | Architectural anti-patterns | No |
| `check-yaml` | YAML validity | No |
| `check-json` | JSON validity | No |
| `check-added-large-files` | Prevent >1MB files | No |
| `check-merge-conflict` | Conflict markers | No |

**Installation:**
```bash
pre-commit install --install-hooks
pre-commit install --hook-type pre-push
```

### Layer 2: Pre-push Hook

Runs `pytest` with coverage on `git push`. Currently in `[manual]` stage while coverage is built up (51% -> 80% target).

### Layer 3: GitHub Actions CI

Configured in `.github/workflows/quality-tests.yml`. Runs on PRs to `main`.

- Quality checks: ruff format, ruff check
- Tests: pytest matrix across Python 3.11 + 3.12
- Security: bandit scan

### Layer 4: Branch Protection

GitHub settings on `main`:
- Require PR with 1 approval
- Require CI status checks to pass
- Require branch up-to-date
- Dismiss stale approvals on new commits

### Emergency Bypass

```bash
git commit --no-verify -m "Emergency fix"
git push --no-verify
```

Only when: critical production bug, broken hooks, or infinite-loop hook bug. Always create follow-up PR to fix violations.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Pre-commit hooks slow me down" | They catch 96% of defects locally; CI catches the same issues 5 minutes later with a longer feedback loop |
| "We can skip coverage for now" | Coverage ratchets up over time; skipping lets it decay permanently |
| "Branch protection is too strict" | One bad merge to main breaks CI for everyone; protection is cheaper than recovery |
| "--no-verify is fine for this one commit" | Every bypass should be followed by a fix PR; if it's not, you've created tech debt |
| "We don't need security scanning" | Bandit catches hardcoded secrets and injection patterns that code review misses |

## Red Flags

- Pre-commit hooks not installed (run `pre-commit install`)
- `--no-verify` used without a follow-up fix PR
- CI workflow modified to skip failing checks instead of fixing them
- Branch protection disabled "temporarily" (it never comes back)
- Coverage threshold lowered instead of writing tests
- Hook produces "files modified" on every commit (infinite loop bug)
- Security scan findings ignored across multiple PRs

## Verification

- [ ] Pre-commit hooks installed — **evidence**: `.git/hooks/pre-commit` exists and runs
- [ ] All hooks pass on `pre-commit run --all-files` — **evidence**: zero failures
- [ ] CI workflow runs on PRs — **evidence**: GitHub Actions shows recent runs
- [ ] Branch protection active on main — **evidence**: repo settings show rules
- [ ] No `--no-verify` commits without follow-up fix — **evidence**: git log audit
- [ ] Coverage at or above threshold — **evidence**: `pytest --cov` output
