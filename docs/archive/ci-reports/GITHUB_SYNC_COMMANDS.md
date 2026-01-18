# GitHub Sync - Manual Execution Instructions

**Status**: GitHub CLI not authenticated
**Required**: Run `gh auth login` before executing these commands

---

## Prerequisites

```bash
# Authenticate GitHub CLI
gh auth login
# Choose: GitHub.com → HTTPS → Authenticate with web browser

# Verify authentication
gh auth status
```

---

## Step 1: Create Milestones (Phase 1-7)

```bash
# Phase 1: Agent Framework
gh milestone create --title "Phase 1: Agent Framework" \
  --description "Extract agent configurations, create registry pattern" \
  --due-date 2026-01-31 \
  --repo oviney/economist-agents

# Phase 2: Code Generation
gh milestone create --title "Phase 2: Code Generation" \
  --description "Generate CrewAI agent code from registry" \
  --due-date 2026-02-15 \
  --repo oviney/economist-agents

# Phase 3: Skills Library
gh milestone create --title "Phase 3: Skills Library" \
  --description "Migrate skills system to CrewAI" \
  --due-date 2026-02-28 \
  --repo oviney/economist-agents

# Phase 4: Migration Strategy
gh milestone create --title "Phase 4: Migration Strategy" \
  --description "Research and spike hierarchical patterns" \
  --due-date 2026-03-15 \
  --repo oviney/economist-agents

# Phase 5: Orchestration
gh milestone create --title "Phase 5: Orchestration" \
  --description "Build hierarchical orchestrator with Manager Agent" \
  --due-date 2026-03-31 \
  --repo oviney/economist-agents

# Phase 6: Integration
gh milestone create --title "Phase 6: Integration" \
  --description "End-to-end testing with existing pipeline" \
  --due-date 2026-04-15 \
  --repo oviney/economist-agents

# Phase 7: Deployment
gh milestone create --title "Phase 7: Deployment" \
  --description "Production deployment and monitoring" \
  --due-date 2026-04-30 \
  --repo oviney/economist-agents
```

---

## Step 2: Create Epic Issue

```bash
# Epic: CrewAI Migration
gh issue create --title "Epic: Migrate to CrewAI Framework" \
  --body "Migrate from custom multi-agent pipeline to CrewAI framework with hierarchical orchestration.

## Objectives
- Extract agent configurations into declarative format
- Build agent registry and code generation system
- Migrate skills library to CrewAI
- Implement hierarchical orchestration
- Maintain quality metrics and governance

## Success Criteria
- All agents operational in CrewAI
- Quality metrics maintained (≥80/100)
- Skills system integrated
- Full test coverage
- Documentation complete

## Stories
- #26: Agent Configuration Extraction (8 points)
- #27: Agent Registry Pattern (5 points)
- #28: Skills Library Migration (8 points)
- #29: Research Spike - Hierarchical Patterns (3 points)
- #30: Hierarchical Orchestrator (3 points)
- #31: Metrics Dashboard (5 points)

**Total**: 32 story points across 6 stories" \
  --label "epic" \
  --milestone "Phase 1: Agent Framework" \
  --repo oviney/economist-agents
```

---

## Step 3: Create User Stories (Issues #26-#32)

### Issue #26: Agent Configuration Extraction

```bash
gh issue create --title "Agent Configuration Extraction - Declarative YAML" \
  --body "## User Story
As a Developer, I need to extract agent configurations from economist_agent.py into declarative YAML files, so that I can generate CrewAI agent code programmatically.

## Acceptance Criteria
- [ ] Script: python3 scripts/extract_agent_configs.py operational
- [ ] YAML files generated: research_agent.yaml, writer_agent.yaml, editor_agent.yaml, graphics_agent.yaml
- [ ] All prompts extracted (RESEARCH_AGENT_PROMPT, WRITER_AGENT_PROMPT, etc.)
- [ ] Agent metadata captured (role, goal, tools, backstory)
- [ ] Validation: YAML schema compliance checked
- [ ] Documentation: config/README.md with structure explanation

## Complexity
**Story Points**: 8 (Large)

## Definition of Done
- [ ] All 4+ agent configs extracted to YAML
- [ ] Validation script passes (YAML well-formed)
- [ ] Documentation complete
- [ ] Zero manual editing needed (100% automated)
- [ ] Tested with real economist_agent.py

## Priority
P0 (Critical Path)

## Dependencies
None (starts Phase 1)

## Labels
- enhancement
- agent-framework
- phase-1" \
  --label "enhancement" --label "agent-framework" --label "phase-1" \
  --milestone "Phase 1: Agent Framework" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

### Issue #27: Agent Registry Pattern

```bash
gh issue create --title "Agent Registry Pattern - Centralized Management" \
  --body "## User Story
As a Developer, I need a centralized agent registry, so that I can manage agent configurations and generate CrewAI code consistently.

## Acceptance Criteria
- [ ] Module: scripts/agent_registry.py with AgentRegistry class
- [ ] Load YAML configs: registry.load_agents('config/agents/')
- [ ] Validate configs: registry.validate() checks completeness
- [ ] Query agents: registry.get_agent('research_agent') returns config
- [ ] List agents: registry.list_agents() returns all names
- [ ] Generate metadata: registry.export_metadata() for documentation

## Complexity
**Story Points**: 5 (Medium)

## Definition of Done
- [ ] AgentRegistry class operational
- [ ] All CRUD operations working
- [ ] Validation enforces schema
- [ ] Unit tests passing (90%+ coverage)
- [ ] Documentation in scripts/agent_registry.py

## Priority
P0 (Critical Path)

## Dependencies
- Blocks: #26 (needs YAML configs to exist)

## Labels
- enhancement
- agent-framework
- phase-1" \
  --label "enhancement" --label "agent-framework" --label "phase-1" \
  --milestone "Phase 1: Agent Framework" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

### Issue #28: Skills Library Migration

```bash
gh issue create --title "Skills Library Migration to CrewAI" \
  --body "## User Story
As a Quality Engineer, I need to migrate the skills learning system to CrewAI, so that agents can continue improving from validation runs.

## Acceptance Criteria
- [ ] Module: scripts/crewai_skills_adapter.py
- [ ] Integrate: SkillsManager with CrewAI agent memory
- [ ] Persist: Skills saved to agent-specific JSON files
- [ ] Load: Skills loaded on agent initialization
- [ ] Update: Agents learn patterns during execution
- [ ] Validate: blog_qa_agent continues learning

## Complexity
**Story Points**: 8 (Large)

## Definition of Done
- [ ] Skills adapter operational
- [ ] CrewAI memory integration working
- [ ] blog_qa_agent learns as before
- [ ] Skills persist across runs
- [ ] No regression in learning (stats tracked)
- [ ] Documentation in docs/SKILLS_LEARNING.md

## Priority
P1 (Important but not blocking)

## Dependencies
- Blocks: #26, #27 (agent infrastructure must exist)

## Labels
- enhancement
- skills-system
- phase-3" \
  --label "enhancement" --label "skills-system" --label "phase-3" \
  --milestone "Phase 3: Skills Library" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

### Issue #29: Research Spike - Hierarchical Patterns

```bash
gh issue create --title "Research Spike: Hierarchical CrewAI Patterns" \
  --body "## Spike Goal
Research and prototype hierarchical crew patterns in CrewAI for our multi-agent orchestration.

## Questions to Answer
1. How does CrewAI implement hierarchical crews?
2. What are best practices for manager/worker patterns?
3. How to integrate with existing governance system?
4. Performance implications of hierarchical vs sequential?
5. Can we preserve agent metrics tracking?

## Deliverables
- [ ] Research report: docs/CREWAI_HIERARCHICAL_RESEARCH.md
- [ ] Proof of concept: scripts/hierarchical_poc.py
- [ ] Recommendations: Architecture decision records (ADRs)
- [ ] Integration plan: How to migrate economist_agent.py

## Time Box
**Duration**: 1 day (8 hours)
**Story Points**: 3

## Acceptance Criteria
- [ ] Report complete with findings
- [ ] POC demonstrates key concepts
- [ ] ADR created for hierarchical approach
- [ ] Integration plan documented

## Priority
P0 (Blocks Phase 5)

## Dependencies
None (research can start independently)

## Labels
- spike
- research
- phase-4" \
  --label "spike" --label "research" --label "phase-4" \
  --milestone "Phase 4: Migration Strategy" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

### Issue #30: Hierarchical Orchestrator

```bash
gh issue create --title "Hierarchical Orchestrator - Manager Agent Pattern" \
  --body "## User Story
As a Project Lead, I need a hierarchical orchestrator that mimics economist_agent.py workflow, so that I can leverage CrewAI's built-in coordination.

## Acceptance Criteria
- [ ] Module: scripts/crewai_orchestrator.py with hierarchical crew
- [ ] Manager Agent: Coordinates Research → Writer → Editor → Graphics flow
- [ ] Worker Agents: Specialized agents for each pipeline stage
- [ ] Governance: Integrate approval gates from governance.py
- [ ] Metrics: Track agent performance in agent_metrics.json
- [ ] Test: Generate 3 articles end-to-end successfully

## Complexity
**Story Points**: 3 (Small but critical)

## Definition of Done
- [ ] Orchestrator generates articles successfully
- [ ] All pipeline stages execute in sequence
- [ ] Governance gates working
- [ ] Metrics tracked as before
- [ ] No regression in quality (≥80/100)
- [ ] Documentation in scripts/crewai_orchestrator.py

## Priority
P0 (Critical Path)

## Dependencies
- Blocks: #26, #27, #29 (needs registry + research findings)

## Labels
- enhancement
- orchestration
- phase-5" \
  --label "enhancement" --label "orchestration" --label "phase-5" \
  --milestone "Phase 5: Orchestration" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

### Issue #31: Metrics Dashboard

```bash
gh issue create --title "Metrics Dashboard - Quality Tracking" \
  --body "## User Story
As a Project Lead, I need a real-time metrics dashboard, so that I can monitor quality trends across sprints.

## Acceptance Criteria
- [ ] Script: python3 scripts/generate_quality_dashboard.py
- [ ] Dashboard: HTML report with charts and trends
- [ ] Metrics tracked:
  - Defect escape rate over time
  - Agent performance (clean draft rate, gate pass rate)
  - Test coverage trends
  - Quality score trajectory
- [ ] Automated: Runs in GitHub Actions on every merge
- [ ] Published: Hosted at /quality-dashboard.html

## Complexity
**Story Points**: 5 (Medium)

## Definition of Done
- [ ] Dashboard generates successfully
- [ ] All metrics visualized
- [ ] GitHub Actions workflow operational
- [ ] Dashboard accessible via URL
- [ ] Auto-updates on merge
- [ ] Documentation in docs/METRICS_GUIDE.md

## Priority
P2 (Nice to have)

## Dependencies
- Blocks: agent_metrics.json, defect_tracker.json (existing data)

## Labels
- enhancement
- metrics
- phase-6" \
  --label "enhancement" --label "metrics" --label "phase-6" \
  --milestone "Phase 6: Integration" \
  --assignee "@me" \
  --repo oviney/economist-agents
```

---

## Step 4: Verify Sync

```bash
# List all issues
gh issue list --repo oviney/economist-agents

# List milestones
gh milestone list --repo oviney/economist-agents

# View issue details
gh issue view 26 --repo oviney/economist-agents
```

---

## Step 5: Update Sprint Tracker

```bash
python3 scripts/sprint_ceremony_tracker.py --report
```

Expected output:
```
✅ Sprint 6 Definition of Ready MET
   All 8 DoR criteria passed
   Sprint 6 ready to start
```

---

## Troubleshooting

**If gh CLI not installed**:
```bash
# macOS
brew install gh

# Verify
gh --version
```

**If authentication fails**:
```bash
# Check existing auth
gh auth status

# Re-authenticate
gh auth logout
gh auth login
```

**If milestones not created**:
```bash
# Check existing milestones
gh milestone list --repo oviney/economist-agents

# Delete duplicate if needed
gh milestone delete --title "Phase 1: Agent Framework" --repo oviney/economist-agents
```

---

## Next Steps After Sync

1. ✅ GitHub issues created (#26-#32)
2. ✅ Milestones created (Phase 1-7)
3. ✅ Epic created (links all stories)
4. ✅ Sprint 6 backlog complete (docs/SPRINT_6_BACKLOG.md)
5. ✅ DoR validated (8/8 criteria)
6. 🔜 Start Sprint 6 execution (Story 1: BUG-020)

---

**Status**: ✅ READY FOR EXECUTION
**Next Action**: Authenticate gh CLI, then run commands above
**Estimated Time**: 15 minutes
