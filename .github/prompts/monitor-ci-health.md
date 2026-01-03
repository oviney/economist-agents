# Monitor CI/CD Health - Daily Check

**Agent**: @quality-enforcer  
**Frequency**: Daily at 9:00 AM (or on-demand)  
**Priority**: P1 (P0 if RED status detected)

---

## Objective

Perform automated CI/CD health monitoring to detect build failures early and trigger incident response when needed.

---

## Instructions

### 1. Load CI Health Skills

Consult the skills framework for learned patterns:

```python
from skills_manager import SkillsManager

ci_skills = SkillsManager("skills/ci_health_patterns.json")
patterns = ci_skills.get_patterns()
```

### 2. Execute Health Check

Run the monitoring script:

```bash
python3 scripts/ci_health_monitor.py --last-n 5
```

### 3. Apply Learned Patterns

The agent should:
- Check status thresholds from `ci_health_patterns.json`
- Apply failure detection patterns
- Use learned escalation triggers
- Follow documented response protocols

### 4. Take Action Based on Skills

**Skills-driven decisions**:
- Status interpretation (GREEN/YELLOW/RED)
- Escalation thresholds (consecutive failures)
- Response protocols (P0/P1 actions)
- Documentation requirements

### 5. Learn from This Run

After monitoring, update skills:

```python
if new_pattern_detected:
    ci_skills.learn_pattern(
        category="ci_monitoring",
        pattern_id="failure_type_X",
        pattern_data={
            "severity": "high",
            "pattern": "Description of pattern",
            "check": "How to detect",
            "learned_from": f"Run #{run_id}"
        }
    )
    ci_skills.save()
```

### 2. Generate Standup Report

For daily team updates, run:

```bash
python3 scripts/ci_health_monitor.py --standup
```

This provides a formatted report including:
- Current CI health status
- Recent run history
- Any active incidents
- Recommended actions

### 3. If Status is RED - Execute P0 Protocol

**CRITICAL**: RED status requires immediate action:

```bash
# Create GitHub issue automatically
python3 scripts/ci_health_monitor.py --last-n 5 --create-issue

# Check what failed
gh run list --limit 3
gh run view [latest-run-id] --log-failed

# Update incident log
# Add entry to docs/CI_HEALTH_LOG.md Active Incidents section
```

**P0 Response Protocol**:
1. **STOP** - Halt all feature work immediately
2. **INVESTIGATE** - Analyze failure logs
3. **FIX** - Address root cause
4. **VALIDATE** - Test locally before push
5. **DOCUMENT** - Update CI_HEALTH_LOG.md

### 4. If Status is YELLOW - Monitor

```bash
# Check specific run details
gh run view [run-id] --log

# Monitor next run
gh run watch
```

No immediate action required, but watch for pattern.

### 5. If Status is GREEN - Report

```bash
# Confirm all systems operational
echo "✅ CI Status: GREEN - All systems operational"
```

Update team in standup if there were recent incidents now resolved.

---

## Expected Outputs

### Daily Standup Report Format

```
CI/CD Health Status - 2026-01-03 09:00

Status: 🟢 GREEN
Recent Runs: ✅ ✅ ✅ ✅ ✅
Consecutive Failures: 0

Latest Run (#63):
- Commit: 7876032
- Branch: main
- Status: success
- Time: 2026-01-03 06:25

Recommendation: All systems operational. Continue normal work.
```

### RED Status Alert Format

```
🚨 CI FAILURE DETECTED - P0 RESPONSE REQUIRED

Status: 🔴 RED
Failed Run: #62
URL: https://github.com/oviney/economist-agents/actions/runs/20673454694
Branch: main
Commit: a4897da

Failure Pattern: 2 consecutive failures (systematic issue)

REQUIRED ACTIONS:
1. Create GitHub issue: [auto-created #XX]
2. View logs: gh run view 20673454694 --log-failed
3. Stop all sprint work until resolved
4. Update CI_HEALTH_LOG.md with incident
```

---

## Integration Points

**Pre-commit hooks**: Local quality gates (format, lint, tests)  
**GitHub Actions**: Remote CI/CD (4 jobs: tests, quality, security, discipline)  
**CI_HEALTH_LOG.md**: Historical incident tracking  
**Sprint ceremonies**: Weekly retrospective reviews

---

## Success Criteria

- ✅ Health check completed daily before 9:30 AM
- ✅ RED status escalated to P0 within 5 minutes
- ✅ Standup report shared with team
- ✅ All incidents documented in CI_HEALTH_LOG.md
- ✅ Consecutive failures = 0 (target maintained)

---

## References

- **[CI_MONITORING_GUIDE.md](../../CI_MONITORING_GUIDE.md)** - Complete operational guide
- **[CI_HEALTH_LOG.md](../../docs/CI_HEALTH_LOG.md)** - Incident tracking
- **[QUALITY_ENFORCER_RESPONSIBILITIES.md](../../docs/QUALITY_ENFORCER_RESPONSIBILITIES.md)** - Role definition
- **[DEFINITION_OF_DONE.md](../../docs/DEFINITION_OF_DONE.md)** - CI as DoD requirement

---

## Troubleshooting

**Issue**: Script not found  
**Solution**: Ensure you're in project root: `cd /Users/ouray.viney/code/economist-agents`

**Issue**: GitHub CLI auth error  
**Solution**: Run `gh auth login` to authenticate

**Issue**: Python virtual environment not activated  
**Solution**: Run `source .venv/bin/activate`

**Issue**: No recent runs found  
**Solution**: Check workflow ID with `gh workflow list`

---

**Last Updated**: 2026-01-03  
**Version**: 1.0  
**Owner**: @quality-enforcer
