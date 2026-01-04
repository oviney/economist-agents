# Mission Template Usage Guide

## Overview

The `scripts/templates/mission_template.py` provides a standardized pattern for executing CrewAI autonomous pod missions with dynamic agent loading (ADR-002).

## Quick Start

```bash
# 1. Copy the template
cp scripts/templates/mission_template.py scripts/story_042_mission.py

# 2. Edit configuration
# Update STORY_ID, STORY_CONTEXT, REQUIRED_AGENTS

# 3. Define your tasks
# Implement define_tasks() function

# 4. Run the mission
python3 scripts/story_042_mission.py
```

## Configuration

```python
STORY_ID = "STORY-042"
STORY_CONTEXT = "Implement autonomous backlog refinement"
REQUIRED_AGENTS = ["product-owner", "scrum-master"]
```

## Key Features

### 1. Dynamic Agent Loading
Uses `AgentRegistry.get_agent()` to load agents by role name:
```python
registry = AgentRegistry()
agents = load_agents(registry)  # Returns dict: {"role": agent}
```

### 2. Mission Launch Banner
Prints clear mission start message with story context:
```
======================================================================
Starting Mission for Story STORY-042...
Context: Implement autonomous backlog refinement
Required Agents: product-owner, scrum-master
======================================================================
```

### 3. Verbose Execution
`Crew(verbose=True)` shows detailed agent reasoning and task progress.

### 4. Automatic Logging
Saves execution logs to `docs/sprint_logs/story_{STORY_ID}_log.md`:
```markdown
# Mission Log: Story STORY-042

**Context:** Implement autonomous backlog refinement
**Agents:** product-owner, scrum-master

## Execution Output
[Crew execution results]
```

## Task Definition Example

```python
def define_tasks(agents: dict) -> list[Task]:
    tasks = []
    
    # Analysis task
    tasks.append(
        Task(
            description="Analyze requirements for autonomous backlog refinement",
            agent=agents["product-owner"],
            expected_output="Requirements document with acceptance criteria",
        )
    )
    
    # Implementation task
    tasks.append(
        Task(
            description="Create backlog refinement automation script",
            agent=agents["scrum-master"],
            expected_output="Working script with integration tests",
            context=[tasks[0]],  # Depends on analysis
        )
    )
    
    return tasks
```

## Error Handling

The template includes helpful error messages:

**Configuration Not Complete:**
```
❌ Configuration Error: Define your tasks in define_tasks()...

Next Steps:
  1. Update STORY_ID, STORY_CONTEXT, REQUIRED_AGENTS
  2. Implement define_tasks() with your mission tasks
  3. Run again to execute the mission
```

**Agent Not Found:**
```
ValueError: Agent 'invalid-role' not found. 
Available: product-owner, scrum-master, qa-specialist, devops-specialist
```

## Architecture

```
┌─────────────────────────────────────────┐
│  Configuration Section                  │
│  - STORY_ID, STORY_CONTEXT             │
│  - REQUIRED_AGENTS                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  load_agents(registry)                  │
│  - Iterates REQUIRED_AGENTS             │
│  - Calls registry.get_agent(role)       │
│  - Returns dict: {"role": agent}        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  define_tasks(agents)                   │
│  - Creates list[Task] objects           │
│  - Assigns agents to tasks              │
│  - Defines task dependencies            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  run_mission()                          │
│  1. Print launch banner                 │
│  2. Load agents via registry            │
│  3. Define tasks                        │
│  4. Create Crew(verbose=True)           │
│  5. Execute crew.kickoff()              │
│  6. Save log to docs/sprint_logs/       │
│  7. Print completion banner             │
└─────────────────────────────────────────┘
```

## Comparison: Old vs New Pattern

### Old Pattern (AgentFactory)
```python
from scripts.agent_factory import AgentFactory

# Complex boilerplate
factory = AgentFactory()
agents = {}
for agent_id in REQUIRED_AGENTS:
    agent = factory.create_agent(
        agent_id,
        verbose=True,
        allow_delegation=False,
    )
    agents[agent_id] = agent

# Manual context injection
inject_story_context(agents, STORY_CONTEXT)

# Complex 5-step workflow
# Audit → Execute → Verify
tasks = create_tasks(agents)  # Fixed 3-task sequence
```

### New Pattern (AgentRegistry - ADR-002)
```python
from scripts.agent_registry import AgentRegistry

# Simple registry-based loading
registry = AgentRegistry()
agents = load_agents(registry)

# Context handled by task descriptions
# Flexible task definition
tasks = define_tasks(agents)  # Custom tasks per mission
```

## Benefits

1. **Simpler**: Removed 130+ lines of boilerplate
2. **Flexible**: Define any task sequence, not locked to Audit→Execute→Verify
3. **Discoverable**: AgentRegistry provides `.list_agents()` for exploration
4. **Consistent**: All missions follow same pattern (ADR-002)
5. **Clear**: Launch banner shows mission context upfront
6. **Transparent**: Verbose mode shows agent reasoning
7. **Traceable**: Automatic logging to sprint_logs/

## Related Documentation

- [ADR-002: Agent Registry Pattern](ADR-002-agent-registry-pattern.md)
- [Agent Registry Implementation](../scripts/agent_registry.py)
- [Available Agents](.github/agents/) - Agent `.agent.md` files

## Troubleshooting

**Problem:** `ValueError: Agent 'my-role' not found`
- **Solution:** Check available agents with `registry.list_agents()`
- Common roles: `product-owner`, `scrum-master`, `qa-specialist`, `devops-specialist`

**Problem:** `NotImplementedError: Define your tasks...`
- **Solution:** Implement `define_tasks()` and remove the `raise NotImplementedError` line

**Problem:** No agents loaded
- **Solution:** Verify `.agent.md` files exist in `.github/agents/` directory

**Problem:** Crew execution fails silently
- **Solution:** Check that tasks have valid `expected_output` and `agent` assignments
