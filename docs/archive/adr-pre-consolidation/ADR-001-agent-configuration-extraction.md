# ADR-001: Extract Agent Definitions to YAML Configuration

**Status:** Proposed
**Date:** 2026-01-01
**Deciders:** Ouray Viney (Agentic AI Architect)
**Context:** Architecture review following discovery of multi-agent frameworks (CrewAI, AutoGen)

## Context

The economist-agents system currently has agent prompts and configurations hardcoded as Python string constants within script files (`topic_scout.py`, `editorial_board.py`, `economist_agent.py`). This creates several challenges:

1. **Difficult to tune:** Changing agent behavior requires editing code
2. **No version control:** Can't A/B test different agent configurations
3. **Not reusable:** Can't share agent definitions across projects
4. **Code coupling:** Agent logic mixed with orchestration logic
5. **Limited collaboration:** Non-technical stakeholders can't modify personas

## Decision

We will extract all agent definitions (personas, prompts, system messages, scoring criteria) into YAML configuration files stored in an `agents/` directory structure:

```
agents/
├── editorial_board/
│   ├── vp_engineering.yaml
│   ├── senior_qe_lead.yaml
│   ├── data_skeptic.yaml
│   ├── career_climber.yaml
│   ├── economist_editor.yaml
│   └── busy_reader.yaml
├── content_generation/
│   ├── researcher.yaml
│   ├── writer.yaml
│   ├── editor.yaml
│   └── graphics.yaml
└── discovery/
    └── topic_scout.yaml
```

## Schema

Each agent YAML file will follow this structure:

```yaml
# agent_name.yaml
name: "Agent Name"
role: "One-line role description"
goal: "What this agent optimizes for"
backstory: |
  Multi-line description of the agent's
  perspective and expertise
system_message: |
  The full system prompt that defines
  agent behavior and constraints
tools: []  # Optional: List of tool names
scoring_criteria:  # Optional: For voting agents
  - metric_name: 0-10
  - another_metric: 0-10
metadata:
  version: "1.0"
  created: "2026-01-01"
  author: "oviney"
  category: "editorial_board"
```

## Consequences

### Positive

1. **Configuration as Code:** Agent definitions under version control
2. **Rapid Iteration:** A/B test different personas without code changes
3. **Reusability:** Share agent configs across projects or with community
4. **Separation of Concerns:** Agent definitions separate from orchestration
5. **Accessibility:** Non-engineers can tune agent behavior
6. **Foundation for Registry:** Enables agent discovery and factory patterns

### Negative

1. **Additional Abstraction:** One more layer between definition and execution
2. **Schema Maintenance:** Need to maintain YAML schema and validation
3. **Migration Effort:** ~10 agents to migrate from Python to YAML
4. **Loading Overhead:** Parse YAML files at runtime (minimal impact)

### Neutral

1. **No framework lock-in:** Works with custom orchestration or CrewAI/AutoGen
2. **Incremental adoption:** Can migrate one agent at a time

## Implementation Plan

### Phase 1: Schema & Loader (Week 1)
- [ ] Create `agents/schema.json` (JSON Schema for validation)
- [ ] Create `scripts/agent_loader.py` (YAML → Agent object)
- [ ] Add unit tests for loader
- [ ] Document schema in `agents/README.md`

### Phase 2: Migration (Week 2)
- [ ] Extract editorial board agents (6 files)
- [ ] Extract content generation agents (4 files)
- [ ] Extract topic scout (1 file)
- [ ] Update scripts to use loader
- [ ] Verify output equivalence

### Phase 3: Validation (Week 2)
- [ ] Add pre-commit hook for YAML validation
- [ ] Run full pipeline with YAML configs
- [ ] Compare outputs with baseline
- [ ] Update documentation

## Alternatives Considered

### 1. Keep Python Constants
**Pros:** Simple, no new dependencies
**Cons:** Technical debt, not reusable
**Verdict:** Rejected - doesn't address root problems

### 2. Use JSON Instead of YAML
**Pros:** Easier to parse, more structured
**Cons:** Less human-readable, can't use multi-line strings easily
**Verdict:** Rejected - YAML better for prose-heavy agent prompts

### 3. Use Framework's Native Format (CrewAI YAML)
**Pros:** Direct compatibility if we migrate
**Cons:** Framework lock-in, may not support our custom fields
**Verdict:** Deferred - design our schema first, migrate later if needed

### 4. Database Storage
**Pros:** Queryable, supports versioning
**Cons:** Overkill for ~10 agents, adds infrastructure
**Verdict:** Rejected - YAML files sufficient for current scale

## Success Metrics

- [ ] All 11 agents migrated to YAML without behavior changes
- [ ] Agent loading time < 100ms per agent
- [ ] Zero schema validation errors in CI/CD
- [ ] At least one successful A/B test of agent persona tuning
- [ ] Community contributor submits first agent config PR

## References

- CrewAI agent configuration: https://docs.crewai.com/concepts/agents
- AutoGen agent definition patterns: https://microsoft.github.io/autogen
- JSON Schema specification: https://json-schema.org/
- Related ADRs: ADR-002 (Agent Registry Pattern)

## Notes

This ADR sets foundation for ADR-002 (Agent Registry) and ADR-003 (CrewAI Migration). The YAML schema should be designed to be framework-agnostic to avoid future lock-in.
