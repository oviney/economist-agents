# Quick Reference: Mission Template

## Copy & Fill Pattern (< 5 minutes)

```bash
# 1. Copy template
cp scripts/templates/mission_template.py scripts/run_story{N}_crew.py

# 2. Fill in 3 sections (search for "FILL IN")
#    - STORY_ID
#    - STORY_CONTEXT  
#    - REQUIRED_AGENTS

# 3. Customize 3 task descriptions (search for "ACTIONS:")
#    - Audit task
#    - Execute task
#    - Verify task

# 4. Run
python3 scripts/run_story{N}_crew.py
```

## Configuration Checklist

### Section 1: Story ID (Line ~40)
```python
STORY_ID = "Story X"  # ← Change to "Story 3", "Story 4", etc.
```

### Section 2: Story Context (Line ~43)
```python
STORY_CONTEXT = """
Story X: [Title]  # ← Add title

AS A [role]       # ← Define role
I WANT [capability]  # ← Define capability
SO THAT [benefit]    # ← Define benefit

ACCEPTANCE CRITERIA:
- [ ] Criterion 1  # ← List all criteria
- [ ] Criterion 2
- [ ] Criterion 3

KNOWN ISSUES:     # ← List known problems
- Issue 1: [description]
"""
```

### Section 3: Required Agents (Line ~66)
```python
REQUIRED_AGENTS = [
    "scrum-master",    # ← Add/remove agents as needed
    "qa-specialist",
]
```

## Task Customization (3 Tasks)

### Task 1: Audit (Line ~85)
```python
description=f"""
Audit current state for {STORY_ID}.

ACTIONS:
1. [What to assess]     # ← Customize
2. [What to check]      # ← Customize
3. [What to measure]    # ← Customize
4. [What to document]   # ← Customize
""",
agent=agents["scrum-master"],  # ← Pick agent
```

### Task 2: Execute (Line ~100)
```python
description=f"""
Execute work for {STORY_ID}.

ACTIONS:
1. [What to implement]  # ← Customize
2. [What to fix]        # ← Customize
3. [What to test]       # ← Customize
4. [What to document]   # ← Customize
""",
agent=agents["qa-specialist"],  # ← Pick agent
context=[audit_task],  # ← Dependencies
```

### Task 3: Verify (Line ~115)
```python
description=f"""
Verify {STORY_ID} completion.

ACTIONS:
1. [What to test]       # ← Customize
2. [What to validate]   # ← Customize
3. [What to check]      # ← Customize
4. [What to update]     # ← Customize
""",
agent=agents["qa-specialist"],  # ← Pick agent
context=[execute_task],  # ← Dependencies
```

## Common Agent Combinations

| Story Type | Agents |
|------------|--------|
| **Bug Fix** | `["qa-specialist"]` |
| **Feature** | `["scrum-master", "qa-specialist"]` |
| **Deployment** | `["devops-specialist", "qa-specialist"]` |
| **Content** | `["research-agent", "writer-agent"]` |
| **Planning** | `["product-owner", "scrum-master"]` |
| **Full Stack** | `["scrum-master", "qa-specialist", "devops-specialist"]` |

## Execution

```bash
# Run story
python3 scripts/run_story3_crew.py

# Output
# ═══════════════════════════════════════════════════════════════════════
# Story 3 Execution: Autonomous Pod Pattern
# ═══════════════════════════════════════════════════════════════════════
# 
# Step 1: Loading 2 agent(s)...
#   ✓ Loaded agent: scrum-master
#   ✓ Loaded agent: qa-specialist
# 
# Step 2: Injecting story context...
#   ℹ Story context will be provided via task descriptions
# 
# Step 3: Creating task sequence...
#   ✓ Created 3 tasks (Audit → Execute → Verify)
# 
# Step 4: Executing crew at 2026-01-04T10:30:00
# [... crew execution output ...]
# 
# ═══════════════════════════════════════════════════════════════════════
# ✅ Story 3 COMPLETE
# 📝 Log: docs/sprint_logs/story_3_log.md
# ═══════════════════════════════════════════════════════════════════════
```

## Troubleshooting (30 seconds)

| Error | Fix |
|-------|-----|
| Agent not found | `python3 scripts/agent_registry.py --list` |
| Import error | `pip install crewai crewai-tools` |
| Empty result | Make task descriptions more specific |
| Task fails | Check agent has right capabilities for task |

## Time Estimates

- **Copy template**: 10 seconds
- **Fill configuration**: 2 minutes
- **Customize tasks**: 2 minutes
- **Run & verify**: 1-10 minutes (depends on story)

**Total**: < 15 minutes from template to execution

## Next Steps

1. ✅ Copy template
2. ✅ Fill in configuration (3 sections)
3. ✅ Customize tasks (3 descriptions)
4. ✅ Run script
5. ✅ Review log in `docs/sprint_logs/`
6. ✅ Update sprint tracker with results

## Full Documentation

See `scripts/templates/README.md` for:
- Detailed explanations
- Advanced patterns
- Multi-agent examples
- Troubleshooting guide
