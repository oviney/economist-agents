# Definition of Done (DoD)

**Purpose**: Quality gates that ALL stories must pass before completion

**Updated**: 2026-01-02 (Sprint 9 Story 0)
**Version**: 2.0 (added CI/CD requirements)

---

## Story-Level DoD

A story is **DONE** when ALL of the following are TRUE:

### 1. Code Quality ✅

- [ ] **All tests passing** (or exceptions documented with justification)
- [ ] **Test coverage ≥80%** for new code (measured by pytest-cov)
- [ ] **Ruff linting passing** (0 errors, or planned fixes documented)
- [ ] **Mypy type checking passing** (0 errors, or # type: ignore with justification)
- [ ] **No breaking changes** without semantic version bump

### 2. CI/CD Health ✅

**CRITICAL - Sprint 9 Story 0 Addition**:

- [ ] **GitHub Actions workflow GREEN** (all jobs passing)
- [ ] **Pre-commit hooks passing** (ruff format, pytest fast tests)
- [ ] **No skipped tests** without documented reason
- [ ] **Security scan passing** (bandit, no HIGH/CRITICAL issues)

**RED BUILD = P0 BLOCKER**:
- If CI fails, stop all sprint work
- Investigate root cause immediately
- Fix before resuming development
- Report to team at next standup

### 3. Documentation ✅

**CRITICAL - Sprint 9 Story 0 Addition**:

- [ ] **README.md updated** (if public API changed)
- [ ] **CHANGELOG.md entry added** (all user-facing changes)
- [ ] **ADRs created/updated** (for architectural decisions)
- [ ] **Inline code comments** (for complex logic)
- [ ] **Docstrings complete** (all public functions/classes)

**Documentation Checklist**:
- API changes → README.md
- Bug fixes → CHANGELOG.md
- Architecture changes → ADRs (docs/)
- New patterns → AGENT_PROMPT_PATTERNS.md
- Process changes → SCRUM_MASTER_PROTOCOL.md

### 4. Code Review ✅

- [ ] **Self-review completed** (use GitHub PR template)
- [ ] **Peer review completed** (if available)
- [ ] **All review comments addressed** (or deferred with reason)
- [ ] **No "TODO" comments** (convert to issues/stories)

### 5. Acceptance Criteria ✅

- [ ] **All AC met** (from story definition)
- [ ] **Edge cases tested** (negative tests, boundary conditions)
- [ ] **Error handling validated** (graceful degradation)
- [ ] **Performance acceptable** (no regressions)

### 6. Production Readiness ✅

- [ ] **Dependencies pinned** (requirements.txt versions exact)
- [ ] **Secrets not committed** (no API keys, tokens)
- [ ] **Environment vars documented** (in .env.example)
- [ ] **Migration path documented** (for breaking changes)

---

## Sprint-Level DoD

A sprint is **DONE** when ALL of the following are TRUE:

### 1. All Stories Complete ✅

- [ ] All committed stories meet Story-Level DoD
- [ ] All unplanned work (Story 0s) documented
- [ ] Deferred stories have clear justification

### 2. Sprint Ceremonies Complete ✅

- [ ] Sprint retrospective held (template in docs/RETROSPECTIVE_SX.md)
- [ ] Backlog refinement for next sprint done
- [ ] DoR validated for next sprint stories
- [ ] Velocity calculated and recorded

### 3. Quality Metrics Maintained ✅

- [ ] **Test pass rate ≥95%** (347/377 = 92% is below threshold)
- [ ] **Defect escape rate ≤20%** (production bugs / total bugs)
- [ ] **CI/CD uptime 100%** (no red builds unaddressed)
- [ ] **Documentation drift 0%** (all docs match code)

### 4. Technical Debt Managed ✅

- [ ] New tech debt logged in backlog
- [ ] Critical debt addressed (P0/P1)
- [ ] Refactoring stories planned
- [ ] Code complexity monitored

---

## Daily Standup Integration

**NEW - Sprint 9 Story 0**: Add to daily standup template

**Mandatory Questions**:
1. What did you complete yesterday?
2. What are you working on today?
3. Any blockers?
4. **➡️ Is CI green?** ← NEW

**If CI is RED**:
- Declare P0 blocker
- Stop all other work
- Investigate root cause
- Fix before continuing sprint

---

## Pre-Commit Enforcement

**Local Quality Gates** (enforced by .git/hooks/pre-commit):

1. **Python version check**: Verify ≤3.13 (prevent Python 3.14 issue)
2. **Ruff format check**: Code formatting standards
3. **Pytest fast tests**: Quick smoke tests (<30s)
4. **Type hints validation**: Basic mypy checks

**To bypass** (emergency only):
```bash
git commit --no-verify -m "Emergency fix"
# Then immediately create issue to fix properly
```

---

## CI/CD Monitoring

**NEW - Sprint 9 Story 0**: DevOps role assignment

**@quality-enforcer Responsibilities**:
- **Daily**: Check GitHub Actions status at start of day
- **On Failure**: Create P0 issue, notify team immediately
- **Red Build**: Stop sprint work until resolved
- **Weekly**: Report CI/CD health in sprint report

**GitHub Actions Workflow** (.github/workflows/ci.yml):
- **Job 1**: quality-checks (ruff format, ruff lint, mypy)
- **Job 2**: tests (pytest with 80% coverage, Python 3.11-3.13 matrix)
- **Job 3**: security-scan (bandit for vulnerabilities)

**Target SLA**:
- Green build uptime: ≥99% (max 1% red time)
- Time to fix red build: <4 hours
- Deploy frequency: ≥1/day (when changes exist)

---

## Exception Handling

**When DoD Cannot Be Met**:

1. **Document in PR**: Explain why DoD item skipped
2. **Create Follow-Up Issue**: Track remediation as technical debt
3. **Get Approval**: Product Owner must approve exception
4. **Set Timeline**: When will DoD be met? (target: next sprint)

**Example**:
```
DoD Exception: Mypy errors in crewai_agents.py

Reason: Incompatible Agent import from CrewAI (upstream issue)
Follow-Up: Issue #45 - Fix Agent type compatibility
Timeline: Sprint 10 (when CrewAI releases type stubs)
Approval: @product-owner (2026-01-02)
```

---

## Version History

**v2.0 (2026-01-02)** - Sprint 9 Story 0 updates:
- Added "CI/CD Health" section (critical)
- Added "Documentation" requirements (critical)
- Added daily standup "Is CI green?" check
- Added @quality-enforcer monitoring role
- Added pre-commit enforcement rules

**v1.0 (2025-12-31)** - Initial version:
- Story-level DoD with 6 categories
- Sprint-level DoD with 4 categories
- Quality metrics targets
- Technical debt tracking

---

## Related Documents

- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [SPRINT_CEREMONY_GUIDE.md](SPRINT_CEREMONY_GUIDE.md) - Ceremony automation
- [DEFECT_PREVENTION.md](DEFECT_PREVENTION.md) - Quality gates
- [ADR-004-python-version-constraint.md](ADR-004-python-version-constraint.md) - Python version policy

---

## Key Principles

**Quality First**: Green build is sacred, red build is P0
**Documentation as Code**: Docs drift = technical debt
**Shift Left**: Catch issues in pre-commit, not CI/CD
**Continuous Improvement**: DoD evolves based on learnings

---

**Enforced By**: Scrum Master, @quality-enforcer
**Reviewed By**: Sprint Retrospective (every sprint)
**Exceptions**: Require Product Owner approval
