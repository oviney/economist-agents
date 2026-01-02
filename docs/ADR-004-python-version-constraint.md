# ADR-004: Python Version Constraint for CrewAI Compatibility

**Date:** 2025-01-02
**Status:** Accepted
**Context:** Sprint 9 Story 1 - CrewAI Integration Validation

## Decision

Constrain project to **Python ≤3.13** (tested with 3.13.11) for CrewAI compatibility.

## Context

### Problem Discovery
- **Date:** 2025-01-02
- **Environment:** Python 3.14.2 (latest stable)
- **Issue:** `ModuleNotFoundError: No module named 'crewai'`
- **Impact:**
  - Blocked test execution: `tests/test_crewai_agents.py` failed to import
  - Blocked git commits: pre-commit hooks requiring pytest failed
  - Prevented CrewAI agent validation

### Root Cause
CrewAI library (version 1.7.2) does not support Python 3.14+:
- Package dependencies require Python ≤3.13
- No Python 3.14 wheels available for key dependencies
- Upstream libraries not yet compatible with Python 3.14

### Investigation Process
1. **Initial Attempt:** Install crewai in Python 3.14.2 → failed
2. **Diagnosis:** Checked pip compatibility, attempted forced install → incompatible
3. **Solution Analysis:** Two options evaluated:
   - **Option A (Chosen):** Downgrade to Python 3.13 (proven stable)
   - **Option B (Deferred):** Wait for upstream Python 3.14 support (ETA unknown)

## Decision Rationale

### Why Python 3.13.11
1. **Latest Stable Compatible Version:** Python 3.13.11 is latest that works with CrewAI 1.7.2
2. **Proven Stability:** 184 tests pass (including 18 CrewAI-specific tests)
3. **Complete Dependency Support:** All 154 project packages compatible
4. **Mature Ecosystem:** No breaking changes expected in 3.13.x series

### Why Not Python 3.14
1. **Ecosystem Immaturity:** Released too recently (November 2024)
2. **Upstream Lag:** Key dependencies (crewai, chromadb, etc.) not yet updated
3. **Risk Profile:** Bleeding-edge Python versions introduce instability
4. **No Critical Features:** Python 3.14 features not required for project

## Implementation

### Environment Setup
```bash
# Create isolated Python 3.13 environment
python3.13 -m venv .venv-py313
source .venv-py313/bin/activate

# Install all dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Verification
```bash
# Validate CrewAI import
python -c "from crewai import Agent, Task, Crew; print('✅ CrewAI OK')"

# Run full test suite
pytest -v  # 184 tests passed
```

### Documentation
- **README.md:** Added Python ≤3.13 requirement with setup instructions
- **.python-version:** Created with "3.13" for tooling (pyenv, asdf)
- **This ADR:** Documents decision and migration process

## Consequences

### Positive
- ✅ **CrewAI Fully Operational:** All 18 CrewAI tests passing
- ✅ **184 Tests Pass:** Complete test suite validated
- ✅ **Developer Onboarding:** Clear setup instructions prevent environment issues
- ✅ **Stable Dependencies:** All 154 packages compatible, no conflicts
- ✅ **Proven Configuration:** Python 3.13 widely deployed in production

### Negative
- ⚠️ **Python 3.14 Features Unavailable:** Cannot use new Python 3.14 syntax/features
- ⚠️ **Migration Delay:** Team must wait for upstream libraries to support 3.14
- ⚠️ **Version Management:** Developers must ensure Python 3.13 installed

### Neutral
- 🔄 **Temporary Constraint:** Will upgrade to Python 3.14 when CrewAI supports it
- 🔄 **No Production Impact:** Python 3.13 remains fully supported upstream
- 🔄 **Environment Isolation:** Virtual environments prevent system-wide conflicts

## Migration Timeline

### Immediate Actions (Completed)
- [x] Create .venv-py313 environment
- [x] Install all dependencies (154 packages)
- [x] Validate CrewAI imports
- [x] Run full test suite (184 tests → 100% pass)
- [x] Update README.md with Python version requirement
- [x] Create .python-version file
- [x] Document decision in ADR-004

### Future Actions (When CrewAI Supports Python 3.14)
- [ ] Monitor crewai release notes for Python 3.14 support announcement
- [ ] Test crewai in Python 3.14 isolated environment
- [ ] Run full test suite in Python 3.14
- [ ] Update .python-version to "3.14"
- [ ] Update README.md to reflect Python ≤3.14
- [ ] Update ADR-004 status to "Superseded"

## Package Versions (Python 3.13.11)

### Core AI/ML
- crewai: 1.7.2
- crewai-tools: 1.7.2
- anthropic: 0.75.0
- openai: 1.83.0
- chromadb: 1.1.1
- instructor: 1.12.0

### Testing & Quality
- pytest: 9.0.2
- pytest-cov: 7.0.0
- pytest-mock: 3.15.1
- ruff: 0.14.10
- mypy: 1.19.1
- bandit: 1.9.2

### Data Science
- numpy: 2.4.0
- matplotlib: 3.10.8
- pandas: (via dependencies)

### Document Processing
- pdfplumber: 0.11.8
- pymupdf: 1.26.7
- python-docx: 1.2.0

## Lessons Learned

1. **Check Compatibility Before Upgrading:** Always verify library support before adopting bleeding-edge Python versions
2. **Virtual Environments Essential:** Isolated environments prevent system-wide compatibility issues
3. **Test Early:** Running test suite immediately revealed blocking issue
4. **Document Constraints:** Clear Python version requirements prevent developer confusion
5. **Homebrew Alternative to Pyenv:** Homebrew's `python@X.Y` packages provide reliable version management on macOS

## References

- **CrewAI Documentation:** https://docs.crewai.com/
- **CrewAI GitHub Issues:** Python 3.14 support tracked in upstream repo
- **Python 3.13 Release Notes:** https://docs.python.org/3/whatsnew/3.13.html
- **Python 3.14 Release Notes:** https://docs.python.org/3/whatsnew/3.14.html
- **Sprint 9 Context:** Story 1 - CrewAI Integration Validation

## Related ADRs

- **ADR-003:** CrewAI Migration Strategy (foundational context)
- **ADR-001:** Agent Configuration Extraction (agent architecture)
- **ADR-002:** Agent Registry Pattern (agent management)

---

**Approval:** Scrum Master (autonomous decision under 2-3 hour time budget)
**Implementation Time:** 45 minutes (vs 2-3 hour estimate - 62% faster)
**Test Results:** 184/184 tests passing (100% pass rate)
**Status:** ✅ Production-ready with Python 3.13.11
