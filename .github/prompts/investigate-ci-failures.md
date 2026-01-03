# CI Failure Investigation Prompt

**Assigned Agent**: @quality-enforcer  
**Priority**: P0 - CRITICAL  
**Date**: 2026-01-03  

---

## Current Situation

The **Quality Gates CI** workflow has **5 consecutive failures** (runs #23-27):
- Latest failure: Run #20673192171 (2026-01-03 05:56:34 UTC)
- URL: https://github.com/oviney/economist-agents/actions/runs/20673192171

## Identified Issues

### 1. Security Scan Failures (Bandit) ❌

Two security issues detected that are causing the Security Scan step to fail:

#### Issue 1: HIGH SEVERITY 🔴
```
Location: scripts/governance.py:212
Issue: Starting a process with a shell, possible injection detected
Code: B605 - shell=True parameter in subprocess call
```

**Security Risk**: Command injection vulnerability if user input reaches subprocess.

**Required Fix**:
- Remove `shell=True` parameter from subprocess.run()
- Use list-based arguments instead of string command
- Example:
  ```python
  # BEFORE (UNSAFE):
  subprocess.run(f"git add {file}", shell=True)
  
  # AFTER (SAFE):
  subprocess.run(["git", "add", file], shell=False)
  ```

#### Issue 2: MEDIUM SEVERITY 🟡
```
Location: scripts/featured_image_agent.py:172
Issue: Call to requests without timeout parameter
Code: B113 - Missing timeout on HTTP request
```

**Security Risk**: Potential hanging requests, Denial of Service vulnerability.

**Required Fix**:
- Add `timeout` parameter to all requests.get/post calls
- Example:
  ```python
  # BEFORE (VULNERABLE):
  response = requests.get(url)
  
  # AFTER (SECURE):
  response = requests.get(url, timeout=30)
  ```

### 2. Test Suite Status ✅

**Current Status**: All 377 tests PASSING (48% coverage)
- Test suite is healthy and not blocking CI
- Coverage exceeds 40% threshold
- No action needed for tests

---

## Investigation Tasks for @quality-enforcer

### Task 1: Fix Security Issues (Estimated: 30 minutes)

**Priority**: P0 - Must fix before any PR can merge

**Subtasks**:
1. **Fix governance.py (HIGH severity)**:
   - [ ] Locate line 212 in scripts/governance.py
   - [ ] Identify the subprocess call using `shell=True`
   - [ ] Refactor to use list-based arguments without shell
   - [ ] Verify no user input can reach the command
   - [ ] Test locally that git operations still work

2. **Fix featured_image_agent.py (MEDIUM severity)**:
   - [ ] Locate line 172 in scripts/featured_image_agent.py
   - [ ] Add `timeout=30` parameter to requests.get() or requests.post()
   - [ ] Verify DALL-E API calls work with timeout
   - [ ] Consider adding retry logic for network failures

### Task 2: Validate Fixes (Estimated: 15 minutes)

**Run local validation**:
```bash
# Run Bandit security scan locally
bandit -r scripts/ \
  -f json \
  -o bandit-report.json \
  --severity-level medium

# Should exit with code 0 (no issues)
echo $?

# Check for any remaining issues
cat bandit-report.json | jq -r '.results[] | "\(.issue_severity) - \(.issue_text)"'
```

### Task 3: Commit and Verify CI (Estimated: 10 minutes)

**Commit with proper documentation**:
```bash
git add scripts/governance.py scripts/featured_image_agent.py
git commit -m "security: Fix Bandit security vulnerabilities (B605, B113)

HIGH: Remove shell=True from subprocess in governance.py
- Refactored to use list-based arguments
- Prevents command injection vulnerability

MEDIUM: Add timeout to HTTP requests in featured_image_agent.py
- Added timeout=30 to prevent hanging requests
- Mitigates DoS vulnerability

Fixes CI failure in Security Scan step
Closes: BUG-026, BUG-027"

git push origin main
```

**Monitor CI**:
- Watch: https://github.com/oviney/economist-agents/actions
- Expected: Green checkmark on Security Scan step
- Expected: All tests still passing (377/377)

---

## Success Criteria

- [ ] Bandit security scan passes with 0 HIGH/MEDIUM issues
- [ ] All tests still passing (377/377)
- [ ] Coverage still ≥ 40%
- [ ] CI workflow shows green checkmark ✅
- [ ] No new security vulnerabilities introduced

---

## Additional Context

### Bandit Security Rules
- **B605**: Detects `subprocess` calls with `shell=True` (HIGH risk)
- **B113**: Detects HTTP requests without `timeout` (MEDIUM risk)

### Why These Matter
1. **Command Injection (B605)**: If any user input reaches the subprocess call, attackers could execute arbitrary commands on the system
2. **DoS via Hanging Requests (B113)**: Without timeouts, requests can hang indefinitely, consuming resources and potentially crashing the application

### Related Documentation
- Defect tracker: `skills/defect_tracker.json` (BUG-026, BUG-027 already logged)
- Security scan config: `.github/workflows/ci.yml` (Security Scan step)
- Pre-commit hooks: `.pre-commit-config.yaml` (local validation)

---

## Questions to Research

1. **Governance.py subprocess usage**: What git operations require subprocess? Can we use GitPython library instead?
2. **Featured image timeout**: What's the typical DALL-E API response time? Is 30s sufficient?
3. **Error handling**: Should we add retry logic for timeout exceptions?
4. **Validation**: Are there other files using subprocess or requests without proper security?

---

## Report Back Format

Please provide:
1. **Files changed**: List with line numbers
2. **Fix approach**: Brief description of solution
3. **Test results**: Local Bandit scan output
4. **CI status**: Link to successful workflow run
5. **Risk assessment**: Any remaining security concerns

---

**Assigned**: @quality-enforcer  
**Due**: ASAP (blocking all PR merges)  
**Estimated Time**: 55 minutes total
