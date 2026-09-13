# Agentic Architecture Evolution - Phase 1: Foundation

**Initiative:** Agentic Architecture Evolution (24 weeks, Phases 1-7)
**Phase 1 Duration:** 2 weeks (January 2-15, 2026)
**Phase Goal:** Establish modular agent configuration system by extracting all agents to YAML
**Runs During:** Sprint 4 (or next available sprint)
**Total Story Points:** 8 points
**Team Capacity:** 8-10 points (1 developer, full-time)

---

## Context: Epic vs Sprint

**Epic/Initiative:** Agentic Architecture Evolution (Phases 1-7)
**Sprint:** Your existing sprint cadence (currently Sprint 3)
**Integration:** Phase 1 work will be executed in your next sprint (Sprint 4 or 5)

**Key Distinction:**
- **Sprints** = Time-boxed iterations (2 weeks each)
- **Phases** = Feature groupings in this epic (Foundation, Registry, Tools, etc.)

---

## Phase 1 Scope

### In Scope

**Issue #27: Extract Agent Configurations to YAML** (8 points)
- **Priority:** P1-high
- **Effort:** Medium
- **Type:** Refactoring
- **Status:** Ready for Sprint

**Key Deliverables:**
1. YAML schema with JSON Schema validation (`agents/schema.json`)
2. Agent loader implementation (`scripts/agent_loader.py`)
3. All 11 agents migrated to YAML format:
   - 6 editorial board personas
   - 4 content generation agents
   - 1 topic scout agent
4. Unit tests for loader (100% coverage target)
5. Pre-commit hook for YAML validation
6. Documentation (`agents/README.md`)

### Out of Scope

- Issue #28 (Agent Registry) - Depends on #27, scheduled for Sprint 2
- Issue #29 (MCP Tools) - Phase 3
- All other issues (#30-32) - Later phases

---

## Sprint Breakdown

### Week 1: Schema Design & Loader Implementation (Jan 2-8)

**Day 1-2: Schema Design**
- [ ] Design YAML schema structure
- [ ] Define required fields: `name`, `role`, `goal`, `backstory`, `system_message`
- [ ] Define optional fields: `tools`, `scoring_criteria`, `metadata`
- [ ] Create JSON Schema for validation (`agents/schema.json`)
- [ ] Add schema examples and documentation

**Day 3-4: Loader Implementation**
- [ ] Create `scripts/agent_loader.py` module
- [ ] Implement YAML parsing with validation
- [ ] Create `AgentConfig` dataclass
- [ ] Add error handling for malformed configs
- [ ] Implement file discovery (scan `agents/` directory)

**Day 5: Testing Infrastructure**
- [ ] Write unit tests for loader (`tests/test_agent_loader.py`)
- [ ] Create fixture YAML files for testing
- [ ] Test edge cases (missing fields, invalid YAML, etc.)
- [ ] Add schema validation tests
- [ ] Achieve 100% test coverage for loader

**Week 1 Exit Criteria (Mid-phase checkpoint):**
- ✅ Schema documented and validated
- ✅ Loader working with test fixtures
- ✅ 100% unit test coverage
- ✅ Can load and validate at least 1 sample agent

---

### Week 2: Migration & Integration (Jan 9-15)

**Day 6-7: Editorial Board Migration**
- [ ] Extract 6 editorial board agents to YAML:
  - `agents/editorial_board/vp_engineering.yaml`
  - `agents/editorial_board/senior_qe_lead.yaml`
  - `agents/editorial_board/data_skeptic.yaml`
  - `agents/editorial_board/career_climber.yaml`
  - `agents/editorial_board/economist_editor.yaml`
  - `agents/editorial_board/busy_reader.yaml`

**Day 8: Content Generation Migration**
- [ ] Extract 4 content agents to YAML:
  - `agents/content_generation/researcher.yaml`
  - `agents/content_generation/writer.yaml`
  - `agents/content_generation/editor.yaml`
  - `agents/content_generation/graphics.yaml`

**Day 9: Discovery Agent Migration**
- [ ] Extract topic scout to YAML:
  - `agents/discovery/topic_scout.yaml`

**Day 10: Validation & Documentation**
- [ ] Run schema validation on all 11 YAML files
- [ ] Test loading all agents via loader
- [ ] Verify no data loss from Python constants
- [ ] Add pre-commit hook for YAML validation
- [ ] Update `agents/README.md` with:
  - Schema documentation
  - Usage examples
  - Contribution guidelines
  - Agent categories explanation

**Week 2 Exit Criteria (Phase 1 completion):**
- ✅ All 11 agents in YAML format
- ✅ All agents pass schema validation
- ✅ Pre-commit hook operational
- ✅ Documentation complete
- ✅ Ready for Sprint 2 (Agent Registry integration)

---

## Dependencies

**External Dependencies:**
- None (self-contained refactoring)

**Blockers:**
- None

**Enables:**
- Sprint 2: Issue #28 (Agent Registry Pattern)
- Future: Agent versioning, A/B testing, community contributions

---

## Definition of Done

### Story-Level DoD
- [ ] All acceptance criteria met
- [ ] Code reviewed (self-review + automated checks)
- [ ] Unit tests passing (100% coverage target)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Pre-commit hooks configured
- [ ] No regressions in existing functionality

### Phase-Level DoD
- [ ] Phase 1 goal achieved (agents extracted to YAML)
- [ ] All story points completed (8/8)
- [ ] Phase 1 review prepared (demo-ready)
- [ ] Phase 1 retrospective completed
- [ ] Next phase (Phase 2) backlog ready

---

## Testing Strategy

### Unit Tests
- `test_agent_loader.py` - Loader functionality
- `test_schema_validation.py` - Schema compliance
- `test_agent_configs.py` - Individual agent configs

### Integration Tests
- Load all 11 agents successfully
- Verify schema validation catches errors
- Test pre-commit hook functionality

### Regression Tests
- Compare YAML agent output vs Python constant output
- Ensure no behavior changes in pipeline

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Schema design needs iteration | Medium | Medium | Start with minimal viable schema, iterate |
| Agent extraction reveals inconsistencies | Low | Medium | Document and fix as found |
| Performance degradation from YAML parsing | Low | Low | Measure, cache if needed |
| Pre-commit hook conflicts | Low | Medium | Test with existing hooks |

---

## Success Metrics

### Quantitative
- ✅ 11/11 agents migrated to YAML
- ✅ 100% schema validation pass rate
- ✅ 100% unit test coverage
- ✅ 0 regressions in pipeline output
- ✅ Agent load time <100ms per agent

### Qualitative
- ✅ YAML files are readable and maintainable
- ✅ Schema is extensible for future needs
- ✅ Documentation enables non-technical stakeholders
- ✅ Team confident in YAML approach

---

## Phase Ceremonies

### Daily Progress Tracking
- **Format:** Update SPRINT.md with progress
- **Focus:** What's done, what's next, any blockers
- **Note:** Integrates with your existing sprint standups

### Phase Planning
- **Date:** When phase added to sprint backlog
- **Duration:** 1 hour
- **Outcome:** Phase 1 backlog finalized, tasks assigned

### Phase Review
- **Date:** Phase 1 completion (target: January 15, 2026)
- **Duration:** 30 minutes
- **Attendees:** Product owner (Ouray)
- **Agenda:** Demo YAML agent system, review metrics

### Phase Retrospective
- **Date:** Phase 1 completion
- **Duration:** 30 minutes
- **Format:** What went well, what to improve, action items for Phase 2

---

## Tools & Automation

### GitHub Integration
- Issues: https://github.com/oviney/economist-agents/issues/27
- Milestone: https://github.com/oviney/economist-agents/milestone/3
- Project Board: (To be created)

### Scripts
- `scripts/github_sprint_sync.py` - Sync sprint status with GitHub
- `scripts/sprint_validator.py` - Validate sprint discipline

### Pre-commit Hooks
- YAML validation (via `yamllint`)
- JSON Schema validation (via `jsonschema`)
- Unit test execution

---

## Next Phase Preview

**Phase 2: Agent Registry (Jan 16-29, during next sprint)**
- Issue #28: Implement Agent Registry Pattern (5 points)
- Refactor all scripts to use registry
- LLM provider abstraction (OpenAI/Anthropic)
- Dependency injection for testing

**Note:** Phase 2 will be scheduled in your next available sprint slot

---

## Communication Plan

### Status Updates
- Daily: Update SPRINT.md progress
- Weekly: GitHub milestone progress report
- End of Sprint: Sprint completion report

### Escalation Path
1. **Blocker Identified** → Document in SPRINT.md
2. **Cannot Resolve in 1 day** → Escalate to product owner
3. **Scope Change Needed** → Sprint planning adjustment

---

## Reference Documentation

- **Roadmap:** [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)
- **ADR:** [docs/ADR-001-agent-configuration-extraction.md](docs/ADR-001-agent-configuration-extraction.md)
- **GitHub Issues:** [GITHUB_ISSUES.md](GITHUB_ISSUES.md)
- **Sprint Template:** [docs/SPRINT_DISCIPLINE_GUIDE.md](docs/SPRINT_DISCIPLINE_GUIDE.md)

---

**Initiative Owner:** Ouray Viney
**Product Owner:** Ouray Viney
**Team Size:** 1 developer
**Phase 1 Commitment:** 8 story points
**Phase Status:** Ready to add to next sprint ✅
**Integration Note:** Schedule Phase 1 work in Sprint 4 or next available sprint slot
