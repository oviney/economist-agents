# Mission Template: Autonomous Pod Pattern

## Purpose

This template standardizes the "Autonomous Pod" execution pattern for sprint stories. Instead of writing crew execution scripts from scratch, teams can simply **fill in the blanks** and run.

## Quick Start

```bash
# 1. Copy template for your story
cp scripts/templates/mission_template.py scripts/run_story3_crew.py

# 2. Edit the CONFIGURATION SECTION
#    - Set STORY_ID = "Story 3"
#    - Fill in STORY_CONTEXT with user story + acceptance criteria
#    - List REQUIRED_AGENTS (e.g., ["scrum-master", "qa-specialist"])

# 3. Customize tasks in TASK FACTORY
#    - Adjust task descriptions for your story
#    - Assign appropriate agents to each task
#    - Update expected outputs

# 4. Run
python3 scripts/run_story3_crew.py
```

## Template Structure

### 1. Configuration Section
```python
STORY_ID = "Story 3"
STORY_CONTEXT = """
User story with acceptance criteria and constraints
"""
REQUIRED_AGENTS = ["scrum-master", "qa-specialist"]
```

**Fill in**:
- `STORY_ID`: Sprint story identifier (e.g., "Story 3", "Story 4")
- `STORY_CONTEXT`: Complete user story in standard format:
  ```
  AS A [role]
  I WANT [capability]
  SO THAT [benefit]
  
  ACCEPTANCE CRITERIA:
  - [ ] Criterion 1
  - [ ] Criterion 2
  
  DEFINITION OF DONE:
  - [ ] Code implemented
  - [ ] Tests passing
  - [ ] Documentation updated
  ```
- `REQUIRED_AGENTS`: List of agent IDs needed (see Available Agents below)

### 2. Task Factory

```python
def create_tasks(agents: dict) -> list[Task]:
    """Create task sequence for this story."""
    
    audit_task = Task(
        description="Audit current state...",
        agent=agents["scrum-master"],
        expected_output="Audit report..."
    )
    
    execute_task = Task(
        description="Execute work...",
        agent=agents["qa-specialist"],
        expected_output="Implementation complete...",
        context=[audit_task]
    )
    
    verify_task = Task(
        description="Verify completion...",
        agent=agents["qa-specialist"],
        expected_output="All criteria verified...",
        context=[execute_task]
    )
    
    return [audit_task, execute_task, verify_task]
```

**Pattern**: Audit → Execute → Verify
- **Audit**: Assess current state, identify gaps
- **Execute**: Implement changes, fix issues  
- **Verify**: Validate all acceptance criteria met

**Customize**:
- Task descriptions to match your story
- Agent assignments (which agent does what)
- Expected outputs
- Task dependencies via `context=[...]`

### 3. Execution Logic (Standard Boilerplate)

**DO NOT MODIFY** - This section is standardized:
- `load_agents()`: Loads agents from registry using AgentFactory
- `inject_story_context()`: Context passed via task descriptions
- `save_execution_log()`: Saves log to `docs/sprint_logs/story_{N}_log.md`
- `main()`: Orchestrates the entire execution flow

## Available Agents

Common agents you can use (from `.github/agents/*.agent.md`):

| Agent ID | Role | Best For |
|----------|------|----------|
| `scrum-master` | Sprint orchestration | Planning, tracking, coordination |
| `qa-specialist` | Quality assurance | Testing, validation, bug fixes |
| `devops-specialist` | Infrastructure | CI/CD, deployments, monitoring |
| `product-owner` | Requirements | Story refinement, prioritization |
| `research-agent` | Content research | Data gathering, fact-checking |
| `writer-agent` | Content writing | Article drafting, editing |

**Full list**: Run `python3 scripts/agent_registry.py --list`

## Example: Story 2 (Integration Tests)

```python
# CONFIGURATION
STORY_ID = "Story 2"
STORY_CONTEXT = """
Story 2: Fix Integration Tests
AS A Developer
I WANT 100% pass rate on integration tests (currently 56%)
SO THAT the CI/CD pipeline is reliable.

ACCEPTANCE CRITERIA:
- [ ] All integration tests passing
- [ ] No mock setup errors
- [ ] Clean test output

KNOWN ISSUES:
1. Visual QA: Mock setup broken
2. Defect Prevention: API mismatch
3. Publication Validator: Logic error
"""
REQUIRED_AGENTS = ["qa-specialist"]

# TASK FACTORY
def create_tasks(agents: dict) -> list[Task]:
    audit_task = Task(
        description="Run pytest tests/integration to confirm failures",
        agent=agents["qa-specialist"],
        expected_output="Current failure report with error messages"
    )
    
    fix_task = Task(
        description="Fix the 3 known issues",
        agent=agents["qa-specialist"],
        expected_output="Fixed code for all issues",
        context=[audit_task]
    )
    
    verify_task = Task(
        description="Run pytest again until GREEN",
        agent=agents["qa-specialist"],
        expected_output="100% pass rate confirmed",
        context=[fix_task]
    )
    
    return [audit_task, fix_task, verify_task]
```

## Output

Execution log saved to: `docs/sprint_logs/story_{N}_log.md`

Example log structure:
```markdown
# Story 2 Execution Log

**Date**: 2026-01-04T10:30:00

## Story Context
[Full story context here]

## Execution Results
[Crew output with all task results]
```

## Benefits

### 1. Standardization
- Consistent execution pattern across all stories
- Reduces copy-paste errors
- Easier code review

### 2. Speed
- "Fill in the blanks" vs writing from scratch
- Focus on story-specific logic, not boilerplate
- Faster story completion

### 3. Quality
- Tested execution pattern (ADR-002 compliant)
- Standard logging and error handling
- Predictable behavior

### 4. Maintainability
- Single template to update for pattern improvements
- All stories automatically benefit from updates
- Clear separation: config vs execution logic

## Advanced Usage

### Custom Task Sequences

Not every story follows Audit → Execute → Verify. Customize as needed:

```python
def create_tasks(agents: dict) -> list[Task]:
    # Example: Parallel tasks
    task_a = Task(description="...", agent=agents["qa-specialist"])
    task_b = Task(description="...", agent=agents["devops-specialist"])
    
    # Both complete before final task
    final_task = Task(
        description="...",
        agent=agents["scrum-master"],
        context=[task_a, task_b]
    )
    
    return [task_a, task_b, final_task]
```

### Multi-Agent Collaboration

Use multiple agents with delegation:

```python
REQUIRED_AGENTS = [
    "scrum-master",
    "qa-specialist", 
    "devops-specialist"
]

def create_tasks(agents: dict) -> list[Task]:
    # Scrum Master orchestrates
    plan_task = Task(
        description="Create execution plan",
        agent=agents["scrum-master"]
    )
    
    # QA executes tests
    test_task = Task(
        description="Run tests",
        agent=agents["qa-specialist"],
        context=[plan_task]
    )
    
    # DevOps deploys
    deploy_task = Task(
        description="Deploy if tests pass",
        agent=agents["devops-specialist"],
        context=[test_task]
    )
    
    return [plan_task, test_task, deploy_task]
```

### Iterative Tasks

Use loops for verify-until-pass patterns:

```python
verify_task = Task(
    description="""
    Run tests repeatedly until 100% pass.
    
    LOOP:
    1. Run pytest
    2. If failures, analyze and fix
    3. Repeat until GREEN
    4. Report final status
    """,
    agent=agents["qa-specialist"],
    expected_output="All tests passing"
)
```

## Troubleshooting

### Agent Not Found
```bash
ValueError: Agent 'my-agent' not found in registry
```
**Solution**: Run `python3 scripts/agent_registry.py --list` to see available agents

### Import Error
```bash
ModuleNotFoundError: No module named 'crewai'
```
**Solution**: Install CrewAI: `pip install crewai crewai-tools`

### Empty Results
```bash
Crew execution returned empty result
```
**Solution**: Check task descriptions are clear and expected_output is specific

## Related Documentation

- [ADR-002: Agent Registry Pattern](../../docs/ADR-002-agent-registry-pattern.md)
- [Agent Registry API](../agent_registry.py)
- [CrewAI Agents](../crewai_agents.py)
- [Story 2 Example](../run_story2_crew.py)

## Version History

- **v1.0** (2026-01-04): Initial template with Audit → Execute → Verify pattern
