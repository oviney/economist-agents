# Action Items - CI/CD Fix January 4, 2026

**Priority**: P0 - BLOCKER
**Status**: Awaiting user action
**Estimated Time**: 10 minutes

---

## Summary

✅ **Local build is GREEN** - all 11 files formatted, all tests passing
🔴 **Remote CI/CD is RED** - needs GitHub Secret configuration

---

## Required Actions (User Must Complete)

### Action 1: Add GitHub Secret (5 minutes) ⚡ CRITICAL

**Step 1**: Navigate to GitHub repository settings
```
https://github.com/oviney/economist-agents/settings/secrets/actions
```

**Step 2**: Click "New repository secret"

**Step 3**: Add secret:
- **Name**: `ANTHROPIC_API_KEY`
- **Value**: `sk-ant-...` (your actual API key)

**Step 4**: Click "Add secret"

---

### Action 2: Update CI Workflow (3 minutes) ⚡ CRITICAL

**File to edit**: `.github/workflows/ci.yml`

**Location**: Lines 75-85 (Test Suite job)

**Current code**:
```yaml
- name: Run tests with coverage
  run: |
    pytest tests/ -v \
      --cov=scripts \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=40
```

**Required change**:
```yaml
- name: Run tests with coverage
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    pytest tests/ -v \
      --cov=scripts \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=40
```

**What changed**: Added `env:` block with `ANTHROPIC_API_KEY` from secrets

---

### Action 3: Commit and Push (2 minutes)

```bash
cd /Users/ouray.viney/code/economist-agents

# Commit the workflow change
git add .github/workflows/ci.yml
git commit -m "ci: Add ANTHROPIC_API_KEY env var to fix test failures

- 18 tests require LLM API key to initialize SMEffectivenessBenchmark
- Add secret from GitHub repository settings
- Tests now run with proper credentials

Resolves: 18 test failures in test_sm_effectiveness_benchmark.py"

# Push to trigger CI/CD
git push origin main

# Watch the build (optional)
gh run watch
```

---

## Expected Outcome

After completing Actions 1-3, the next CI/CD run should:

✅ **Code Quality Checks**: PASS (11 files already formatted locally)
✅ **Test Suite Python 3.11**: PASS (18 previously failing tests now have API key)
✅ **Test Suite Python 3.12**: PASS (no longer cancelled)
✅ **Security Scan**: PASS (already passing)

**Overall Status**: 🟢 **GREEN BUILD**

---

## Verification Steps

### Step 1: Watch CI/CD Run
```bash
gh run list --limit 1
# Should show: "ci: Add ANTHROPIC_API_KEY env var..." with status "in_progress"

gh run watch
# Live view of build progress
```

### Step 2: Check Build Results
```bash
gh run view --log
# Should show all jobs passing
```

### Step 3: Verify Test Results
```bash
gh run view <run-id>
# Look for:
# ✓ Code Quality Checks
# ✓ Test Suite (Python 3.11) 
# ✓ Test Suite (Python 3.12)
# ✓ Security Scan
```

---

## Backup Plan (If API Key Not Available)

If you don't have an Anthropic API key immediately available:

### Option A: Use OpenAI Instead
```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Option B: Skip LLM Tests Temporarily
Add this to `.github/workflows/ci.yml`:
```yaml
- name: Run tests with coverage
  env:
    SKIP_LLM_TESTS: true
  run: |
    pytest tests/ -v \
      -m "not llm_required" \
      --cov=scripts \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=35
```

Then mark LLM tests:
```python
# In tests/test_sm_effectiveness_benchmark.py
import pytest

@pytest.mark.llm_required
class TestSMEffectivenessBenchmark:
    ...
```

---

## Files Ready to Commit

These files were formatted locally and are ready to push:

1. `scripts/agent_registry.py`
2. `scripts/archived/legacy_sync/sync_github_project.py`
3. `scripts/benchmarks/measure_sm_effectiveness.py`
4. `scripts/test_agent_integration.py`
5. `src/manager.py`
6. `tests/test_architecture_compliance.py`
7. `tests/test_generate_chart.py`
8. `tests/test_github_integration.py`
9. `tests/test_improvements.py`
10. `tests/test_quality_system.py`
11. `tests/test_sm_effectiveness_benchmark.py`

**Status**: These files appear to be already committed based on "Everything up-to-date" message from git push.

---

## Timeline

| Action | Time | Status |
|--------|------|--------|
| Add GitHub Secret | 5 min | ⏳ **PENDING USER** |
| Update ci.yml | 3 min | ⏳ **PENDING USER** |
| Commit & Push | 2 min | ⏳ **PENDING USER** |
| CI/CD Run | ~2-3 min | Auto-triggered after push |
| **Total** | **~12-13 min** | |

---

## Questions?

**Q**: Do I need both ANTHROPIC_API_KEY and OPENAI_API_KEY?
**A**: No, just one is sufficient. The LLM client will use whichever is available.

**Q**: Will CI/CD consume API credits on every run?
**A**: Yes. To avoid this, use Option B (mock LLM client) in the backup plan.

**Q**: What if the tests still fail after adding the API key?
**A**: Check the error message - it may indicate an invalid key format or rate limit.

**Q**: Why weren't the formatting fixes already pushed?
**A**: Git reported "Everything up-to-date", suggesting they were committed in a previous operation.

---

## Success Criteria

- [ ] GitHub Secret `ANTHROPIC_API_KEY` added to repository
- [ ] `.github/workflows/ci.yml` updated with `env:` block
- [ ] Changes committed and pushed to `main` branch
- [ ] CI/CD build triggered automatically
- [ ] All 4 jobs in Quality Gates CI pass (Code Quality, Test Suite × 2, Security)
- [ ] No red X badges on GitHub Actions page

---

**Next**: Complete Actions 1-3 above, then verify with "gh run watch"
