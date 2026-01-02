# Track 1 Brief: Story 1 - CrewAI Agent Generation

**Assigned to**: @refactor-specialist
**Story Points**: 5
**Priority**: P0
**Sprint**: Sprint 7

---

## Story Context

You are creating the foundational module that generates CrewAI agents from our declarative YAML registry. This is the first step in migrating Stage 3 (Content Generation) to CrewAI framework.

## Background Reading (REQUIRED)

1. **ADR-003**: `/Users/ouray.viney/code/economist-agents/docs/ADR-003-crewai-migration-strategy.md`
   - Read sections: "Architecture After Migration", "Phase 1: Foundation"
   - Key decision: We're migrating Stage 3 only, keeping Stages 1-2 custom

2. **CrewAI Mapping**: `/Users/ouray.viney/code/economist-agents/docs/crewai-economist-agents-mapping.md`
   - Read section: "Core CrewAI Concepts → Agents"
   - Understand role/goal/backstory mapping

3. **Agent Registry**: `/Users/ouray.viney/code/economist-agents/schemas/agents.yaml`
   - This is your data source
   - Contains 4 agents: research_agent, writer_agent, editor_agent, graphics_agent

## Your Task

Create `/Users/ouray.viney/code/economist-agents/scripts/crewai_agents.py` with:

### Module Structure

```python
#!/usr/bin/env python3
"""
CrewAI Agent Factory

Generates CrewAI Agent instances from declarative YAML configurations.
Part of Phase 1: CrewAI Migration (ADR-003).

Usage:
    from scripts.crewai_agents import AgentFactory

    factory = AgentFactory()
    research_agent = factory.create_agent('research_agent')
    writer_agent = factory.create_agent('writer_agent')
"""

from crewai import Agent
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class AgentFactory:
    """Factory for creating CrewAI agents from YAML configurations"""

    def __init__(self, config_path: str = None):
        """
        Initialize factory with agent registry.

        Args:
            config_path: Path to agents.yaml (default: schemas/agents.yaml)
        """
        pass

    def create_agent(self, agent_id: str, **kwargs) -> Agent:
        """
        Create a CrewAI Agent instance from registry configuration.

        Args:
            agent_id: Agent identifier from agents.yaml
            **kwargs: Override any agent properties

        Returns:
            CrewAI Agent instance

        Raises:
            ValueError: If agent_id not found in registry
        """
        pass

    def create_all_agents(self) -> Dict[str, Agent]:
        """
        Create all agents defined in registry.

        Returns:
            Dict mapping agent_id to Agent instance
        """
        pass

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get raw configuration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent configuration dict
        """
        pass
```

## Acceptance Criteria

- [ ] `scripts/crewai_agents.py` created with AgentFactory class
- [ ] Loads configurations from `schemas/agents.yaml`
- [ ] `create_agent()` method instantiates CrewAI Agent with:
  - role (from YAML)
  - goal (from YAML)
  - backstory (from YAML)
  - verbose=True (for debugging)
  - allow_delegation=False (agents don't delegate in our pipeline)
- [ ] `create_all_agents()` returns dict of all 4 agents
- [ ] Validates agent_id exists before creation (raises ValueError if not)
- [ ] Unit tests in `tests/test_crewai_agents.py`:
  - Test loading agents.yaml
  - Test creating single agent
  - Test creating all agents
  - Test invalid agent_id raises ValueError
- [ ] Module docstring explains purpose and usage
- [ ] CLI entry point: `python scripts/crewai_agents.py --list` shows all agent IDs

## Implementation Notes

1. **YAML Loading**: Use `yaml.safe_load()` for security
2. **Path Resolution**: Use `Path(__file__).parent.parent / 'schemas' / 'agents.yaml'`
3. **Error Handling**: Provide helpful error messages if agents.yaml is malformed
4. **Testing**: Mock agents.yaml in tests to avoid file I/O dependencies
5. **CrewAI Import**: If `crewai` not installed, provide clear error message

## Example Usage

```python
# In economist_agent.py (future migration)
from scripts.crewai_agents import AgentFactory

factory = AgentFactory()

# Replace current agents with CrewAI agents
research_agent = factory.create_agent('research_agent')
writer_agent = factory.create_agent('writer_agent')
editor_agent = factory.create_agent('editor_agent')
```

## Dependencies

- `crewai` package (in requirements.txt)
- `schemas/agents.yaml` (exists)
- `pyyaml` (already installed)

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Code passes ruff linting
- [ ] Code passes mypy type checking
- [ ] Unit tests pass (pytest)
- [ ] Module documented with examples
- [ ] Can instantiate all 4 agents successfully
- [ ] CLI works: `python scripts/crewai_agents.py --list`

## Estimated Duration

3-4 hours (includes reading, implementation, testing)

## Checkpoint

Report progress at 2-hour mark to Scrum Master in SPRINT_7_PARALLEL_EXECUTION_LOG.md

---

**Status**: 🟢 READY TO START
**Assigned Agent**: @refactor-specialist
**Start Time**: TBD
