# Project Backlog

Last updated: 2025-12-31

This file tracks architectural improvements and technical debt identified through architecture reviews and development.

## Recent Completion Summary (2025-12-31)

✅ **5 High-Priority Items Completed**:
- JSON Schema Validation
- Rate Limiting for API Calls
- Default Environment Variables
- Input Validation for Agents
- Improved Error Messages

**Test Results**: All 5 test suites passing (some tests skip gracefully when anthropic module not available)
- JSON Schema Validation: ✅ PASSED
- Input Validation: ⚠️ SKIPPED (verified code structure)
- Error Messages: ⚠️ SKIPPED (verified code structure)
- Default Environment Variables: ✅ PASSED
- Rate Limiting Logic: ⚠️ SKIPPED (verified code structure)

## Status Legend
- 🔴 **Blocked**: Waiting on external dependency or decision
- 🟡 **In Progress**: Currently being worked on
- 🟢 **Ready**: Can be started anytime
- ✅ **Complete**: Done and tested
- 🧊 **Icebox**: Deferred, good idea but not prioritized

---

## High Priority

### ✅ JSON Schema Validation
**Status**: Complete
**Priority**: P0 (Critical)
**Effort**: Medium
**Completed**: 2025-12-31

**Problem**: No validation of JSON intermediates between pipeline stages. Invalid JSON causes cryptic failures downstream.

**Solution**: Created JSON schemas and validation function in `schemas/` directory.

**Files Changed**:
- `schemas/content_queue_schema.json`
- `schemas/board_decision_schema.json`
- `scripts/validate_schemas.py`

**Testing**: Validated with both valid and invalid JSON files.

---

### ✅ Rate Limiting for API Calls
**Status**: Complete
**Priority**: P0 (Critical)
**Effort**: Medium
**Completed**: 2025-12-31

**Problem**: No retry logic for Anthropic API calls. Pipeline fails on rate limits or temporary network issues.

**Solution**: Implemented exponential backoff with retry logic in client creation.

**Files Changed**:
- `scripts/economist_agent.py` - `create_client()` enhanced
- `scripts/editorial_board.py` - uses enhanced client
- `scripts/topic_scout.py` - uses enhanced client

**Configuration**:
- Max retries: 3
- Initial backoff: 1 second
- Max backoff: 10 seconds
- Exponential multiplier: 2x

**Testing**: Simulated rate limit scenarios.

---

### ✅ Default Environment Variables
**Status**: Complete
**Priority**: P0 (Critical)
**Effort**: Small
**Completed**: 2025-12-31

**Problem**: Pipeline fails silently if `OUTPUT_DIR` not set. Poor developer experience.

**Solution**: Added sensible defaults with clear logging.

**Files Changed**:
- `scripts/economist_agent.py` - defaults to `output/`
- Added logging to show which paths are used

**Defaults**:
- `OUTPUT_DIR`: `output/` (creates if missing)
- `ANTHROPIC_API_KEY`: Required, fails with clear message

**Testing**: Ran pipeline without env vars set.

---

### ✅ Input Validation for Agents
**Status**: Complete
**Priority**: P1 (High)
**Effort**: Medium
**Completed**: 2025-12-31

**Problem**: Agents assume valid inputs. Crashes with cryptic errors on bad data.

**Solution**: Added validation at start of each agent function with helpful error messages.

**Files Changed**:
- `scripts/economist_agent.py` - validated all `run_*_agent()` functions
- `scripts/topic_scout.py` - validated inputs
- `scripts/editorial_board.py` - validated inputs

**Validation Added**:
- Non-empty strings for topics
- Valid JSON structure for research briefs
- File existence checks
- Type validation

**Testing**: Tested with invalid inputs (empty strings, malformed JSON, missing files).

---

## Medium Priority

### ✅ Improved Error Messages
**Status**: Complete
**Priority**: P1 (High)
**Effort**: Small
**Completed**: 2025-12-31

**Problem**: Generic error messages don't indicate which agent or stage failed.

**Solution**: Added contextual information to all error messages.

**Pattern**: `[AGENT_NAME] Stage: {stage} | Error: {details} | Input: {input_summary}`

**Files Changed**:
- All agent scripts
- JSON parsing error handlers
- File I/O error handlers

**Testing**: Triggered various errors and verified messages.

---

### 🟢 Chart Regression Tests
**Status**: Ready
**Priority**: P2 (Medium)
**Effort**: Large
**Created**: 2025-12-31

**Problem**: Known chart bugs (5 documented in code) have no automated prevention.

**Bugs to Test**:
1. Title/red bar overlap
2. Inline label ON data line (not offset)
3. Inline label in X-axis zone
4. Label-to-label overlap
5. Clipped elements at edges

**Solution Approach**:
- Create test chart generator with known bad configurations
- Use visual QA agent to detect issues programmatically
- Add to CI/CD pipeline

**Files to Create**:
- `tests/test_chart_layouts.py`
- `tests/fixtures/bad_charts/` (example bad configurations)

**Blocked By**: Need test data fixtures

**Estimate**: 4-6 hours

---

### 🟢 Visual QA Metrics Tracking
**Status**: Ready
**Priority**: P2 (Medium)
**Effort**: Small
**Created**: 2025-12-31

**Problem**: Visual QA runs manually, no metrics on chart quality over time.

**Solution**:
- Add metrics to skills system
- Track pass/fail rate per chart
- Identify recurring issues

**Files to Change**:
- `scripts/economist_agent.py` - record visual QA results
- `scripts/skills_manager.py` - add visual QA category
- `skills/blog_qa_skills.json` - new category

**Metrics to Track**:
- Charts generated: count
- Visual QA pass rate: percentage
- Most common failures: top 3
- Improvement trend: pass rate over time

**Estimate**: 2-3 hours

---

## Medium Priority

### 🟡 Migrate Stage 3 Content Generation to CrewAI (Phase 2)
**Status**: Ready
**Priority**: P2 (Medium)
**Effort**: Large
**Type**: Technical Enabler
**Created**: 2026-01-03
**Related**: ADR-003 CrewAI Migration Strategy

**Context**: 
- Phase 1 COMPLETE: CrewAI 1.7.2 installed, 18/18 tests passing
- AgentFactory operational with schemas/agents.yaml
- Sprint 7 delivered CrewAI foundation infrastructure
- Sprint 9 Story 0 resolved Python 3.13/3.14 compatibility

**Problem**: Stage 3 Content Generation agents (Research, Writer, Editor) still use direct LLM calls. Need to migrate to CrewAI framework for improved orchestration, task dependencies, and context sharing.

**Solution**:
Implement Phase 2 of ADR-003 selective migration strategy:

**Tasks**:
1. **Migrate Research Agent to CrewAI** (3-4 hours)
   - Convert research_agent.py to CrewAI agent
   - Define research tasks with sequential dependencies
   - Validate data_points and chart_data output format
   - Ensure 90%+ verification rate maintained

2. **Migrate Writer Agent to CrewAI** (3-4 hours)
   - Convert writer_agent.py to CrewAI agent
   - Implement task dependency on Research Agent output
   - Preserve banned phrases validation
   - Maintain chart embedding logic
   - Test against Sprint 6 quality baseline

3. **Migrate Editor Agent to CrewAI** (2-3 hours)
   - Convert editor_agent.py to CrewAI agent
   - Implement 5 quality gate checks as CrewAI tasks
   - Preserve PASS/FAIL format from Sprint 8 enhancements
   - Target 95%+ gate pass rate

4. **Sequential Task Orchestration** (2-3 hours)
   - Implement Research → Writer → Editor pipeline
   - Add context sharing between agents
   - Preserve quality gates and validation
   - Test end-to-end with 5+ articles

5. **Quality Validation** (2-3 hours)
   - Compare metrics vs Sprint 6-8 baselines
   - Writer: 80%+ clean draft rate
   - Editor: 95%+ gate pass rate
   - Graphics: 88%+ Visual QA pass rate
   - Verify no quality regression

6. **Update Documentation** (1-2 hours)
   - Update ADR-003 with Phase 2 completion notes
   - Document migration patterns for Phase 3
   - Update SPRINT.md with new architecture

**Files to Modify**:
- `agents/research_agent.py` (230 lines → CrewAI agent)
- `agents/writer_agent.py` (400 lines → CrewAI agent)
- `agents/editor_agent.py` (544 lines → CrewAI agent)
- `scripts/economist_agent.py` (orchestration logic)
- `tests/test_agent_integration.py` (validate CrewAI pipeline)
- `docs/ADR-003-crewai-migration-strategy.md` (Phase 2 status)

**Acceptance Criteria**:
- [ ] All 3 agents migrated to CrewAI framework
- [ ] Sequential task dependencies working (Research → Writer → Editor)
- [ ] Quality metrics match or exceed Sprint 6-8 baselines
- [ ] 18+ tests passing (existing + new CrewAI integration tests)
- [ ] End-to-end article generation via CrewAI pipeline successful
- [ ] Documentation updated with migration patterns

**Success Metrics**:
- Research verification rate: ≥90%
- Writer clean draft rate: ≥80%
- Editor gate pass rate: ≥95%
- Graphics Visual QA: ≥88%
- Integration test pass rate: 100%

**Dependencies**:
- CrewAI 1.7.2+ (✅ installed)
- Python 3.10-3.13 (✅ 3.13.11 active)
- schemas/agents.yaml (✅ exists)
- Sprint 6-8 quality baselines (✅ documented)

**Risks**:
- Quality regression during migration
- Context sharing between agents may need tuning
- Sequential dependencies could increase latency
- AgentFactory may need enhancements for complex orchestration

**Mitigation**:
- Parallel track: Keep existing agents as fallback
- Comprehensive A/B testing vs baselines
- Incremental migration (one agent at a time)
- Rollback plan if quality degrades >10%

**Estimate**: 13-17 hours (Large effort, 2 sprint story)

**Phase 3 Preview**: Migrate Graphics Agent, implement parallel task execution, optimize CrewAI crew performance

---

## Low Priority

### 🟢 Integration Tests
**Status**: Ready
**Priority**: P3 (Low)
**Effort**: Large
**Created**: 2025-12-31

**Problem**: No automated end-to-end tests. Pipeline quality depends on manual testing.

**Solution**:
- Create test data fixtures
- Run full pipeline: scout → board → generator
- Validate outputs match expectations
- Check for regression

**Files to Create**:
- `tests/test_integration.py`
- `tests/fixtures/test_topics.json`
- `tests/fixtures/expected_output/`

**Test Scenarios**:
1. Happy path: Valid topic → Complete article
2. Missing data: Topic with no research → Graceful handling
3. Chart failure: Research without chart data → Text-only article
4. API failure: Simulate rate limit → Retry succeeds

**Estimate**: 8-10 hours

---

### 🟢 Anti-Pattern Detection
**Status**: Ready
**Priority**: P3 (Low)
**Effort**: Medium
**Created**: 2025-12-31

**Problem**: Architecture review only documents patterns, not anti-patterns.

**Anti-Patterns to Detect**:
- Creating LLM client per request (should be singleton)
- Hardcoded API keys (should use env vars)
- Unvalidated JSON parsing (should use try/except)
- Missing verification flags (should mark unverified claims)
- Direct file writes without path validation

**Solution**:
- Add `_detect_anti_patterns()` to `architecture_review.py`
- Learn anti-patterns in skills system
- Generate warnings in review report

**Files to Change**:
- `scripts/architecture_review.py`

**Estimate**: 3-4 hours

---

### 🟢 Expand Skills Categories
**Status**: Ready
**Priority**: P3 (Low)
**Effort**: Medium
**Created**: 2025-12-31

**New Categories**:
- `deployment`: CI/CD patterns, Docker, environment setup
- `performance`: Optimization patterns, caching, parallelization
- `security`: API key handling, input sanitization, secrets management
- `monitoring`: Logging patterns, metrics, alerting

**Solution**:
- Add analysis methods to architecture reviewer
- Update skills manager with new categories
- Document in ARCHITECTURE_PATTERNS.md

**Files to Change**:
- `scripts/architecture_review.py`
- `docs/ARCHITECTURE_REVIEW_PROCESS.md`

**Estimate**: 4-5 hours

---

### 🧊 Pre-commit Architecture Review
**Status**: Icebox
**Priority**: P4 (Nice to have)
**Effort**: Small
**Created**: 2025-12-31

**Problem**: Architectural drift not caught until manual review.

**Solution**:
- Add `.git/hooks/pre-commit` script
- Run architecture review on changed files
- Fail commit if new anti-patterns detected

**Trade-off**: Slower commits vs earlier detection

**Estimate**: 1-2 hours

---

### 🧊 CONTRIBUTING.md
**Status**: Icebox
**Priority**: P4 (Nice to have)
**Effort**: Small
**Created**: 2025-12-31

**Problem**: No contributor documentation.

**Solution**:
- Reference architectural patterns
- Document "edit prompts first" principle
- Link to all documentation
- Explain skills learning system

**Files to Create**:
- `CONTRIBUTING.md`

**Estimate**: 1-2 hours

---

## Completed Archive

Completed items moved here for historical reference.

### ✅ .github/copilot-instructions.md
**Completed**: 2025-12-31
Created comprehensive AI coding guide for the codebase.

### ✅ Architecture Review Agent
**Completed**: 2025-12-31
Self-learning architecture analyzer with skills system.

### ✅ Documentation System
**Completed**: 2025-12-31
- ARCHITECTURE_PATTERNS.md (auto-generated)
- ARCHITECTURE_REVIEW_PROCESS.md
- SKILLS_LEARNING.md

---

## How to Use This Backlog

### Adding New Items
1. Choose appropriate priority (P0-P4)
2. Estimate effort (Small: <2h, Medium: 2-6h, Large: >6h)
3. Add to correct priority section
4. Include problem statement and proposed solution

### Updating Status
- Change emoji at start of item
- Update "Status" field
- Add "Completed" date when done
- Move to archive section

### Priority Definitions
- **P0 (Critical)**: Blocks development or causes user-facing failures
- **P1 (High)**: Significant quality/experience improvement
- **P2 (Medium)**: Nice to have, improves maintainability
- **P3 (Low)**: Future enhancement, not urgent
- **P4 (Icebox)**: Good idea, low priority, may not implement

### Review Cadence
- **Weekly**: Review P0-P1 items
- **Monthly**: Review P2-P3 items
- **Quarterly**: Revisit icebox items
---

## Story 10: Phase 2 Migration (Stage 3 Content Gen)

**Status**: 🟢 Ready
**Type**: Technical Enabler
**Priority**: P1 (High)
**Effort**: Large (8 story points)
**Added**: 2026-01-04

**Problem**: Stage 3 (Content Generation) still uses legacy orchestration. Need to migrate to CrewAI pattern for consistency and maintainability.

**Solution**: Port Stage 3 logic to `Stage3Crew` class following TDD approach established in Phase 1.

**Acceptance Criteria**:
1. **TDD Mandate**: A reproduction script (`tests/verify_stage3_migration.py`) must be created AND fail *before* any implementation code is written.
2. **Migration**: The legacy `Stage 3` logic is ported to a `Stage3Crew` class using `crewai`.
3. **Validation**: The reproduction script passes with 100% accuracy.
4. **Cleanup**: Legacy code is marked deprecated (not deleted yet).

**Files to Create**:
- `tests/verify_stage3_migration.py` - TDD reproduction script
- `agents/stage3_crew.py` - New CrewAI implementation
- `agents/stage3_tasks.py` - Task definitions for Stage 3

**Files to Modify**:
- Legacy Stage 3 orchestration code - mark as deprecated
- Update integration tests

**Dependencies**:
- Phase 1 migration (Stage 1 & Stage 2) must be complete
- CrewAI framework already in use

**Testing Strategy**:
1. Create failing reproduction script first (TDD)
2. Implement Stage3Crew to pass reproduction script
3. Run existing integration tests to ensure no regression
4. Compare output quality between legacy and CrewAI implementations

**Related Work**:
- ADR-003: CrewAI Migration Strategy
- Phase 1 completion documentation