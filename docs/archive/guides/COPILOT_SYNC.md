# Hybrid Copilot Strategy - Sync Guide

## Overview

The **Hybrid Copilot Strategy** bridges local agent memory (learned patterns from bugs, QA runs, and architecture reviews) with GitHub Copilot's contextual reasoning. This creates a self-improving code generation system that learns from your team's historical mistakes.

## Architecture

```
Agent Memory (Local)                 GitHub Copilot (IDE)
├─ skills/defect_tracker.json  ──┐
├─ skills/blog_qa_skills.json   ├──→ sync_copilot_context.py ──→ .github/copilot-instructions.md ──→ Real-time code suggestions
└─ docs/ARCHITECTURE_PATTERNS.md ──┘
```

## Pattern Sources

### 1. Defect Prevention Patterns
**Source**: `skills/defect_tracker.json`
**Extracted**: Bugs with root cause analysis (RCA)
**Format**:
```
BUG-XXX (severity) - root_cause
- Issue: Description of the bug
- Missed By: Test type that should have caught it
- Prevention: Actions taken to prevent recurrence
```

### 2. Content Quality Patterns
**Source**: `skills/blog_qa_skills.json`
**Extracted**: Patterns learned during blog QA validation runs
**Format**:
```
pattern_id (severity)
- Pattern: Description of the anti-pattern
- Check: How to detect/prevent it
```

### 3. Architectural Patterns
**Source**: `docs/ARCHITECTURE_PATTERNS.md`
**Extracted**: Architectural decisions and best practices
**Format**:
```
Pattern Name (severity)
- Pattern: Description
- Rationale: Why this pattern exists
- Check: How to validate compliance
```

## Running the Sync

### Manual Sync (Recommended After)
- Fixing bugs with RCA data
- Completing sprint retrospectives
- Adding new architectural patterns
- Major refactoring work

```bash
# Preview what will be synced (dry-run)
.venv/bin/python scripts/sync_copilot_context.py --dry-run

# Actually sync the patterns
.venv/bin/python scripts/sync_copilot_context.py

# Sync from a different repository path
.venv/bin/python scripts/sync_copilot_context.py --root /path/to/repo
```

### Automatic Sync (GitHub Actions)

The workflow `.github/workflows/sync-copilot.yml` automatically syncs on:

1. **Push triggers**:
   - Changes to `skills/defect_tracker.json`
   - Changes to `skills/blog_qa_skills.json`
   - Changes to `docs/ARCHITECTURE_PATTERNS.md`

2. **Scheduled**:
   - Weekly on Sundays at midnight UTC
   - Ensures patterns stay fresh even without defect updates

3. **Manual**:
   - Go to Actions → "Sync Copilot Context" → "Run workflow"
   - Useful after bulk updates or testing

## What Gets Synced

The sync creates a new section in `.github/copilot-instructions.md`:

```markdown
## Learned Anti-Patterns

*Auto-generated from skills/*.json and docs/ARCHITECTURE_PATTERNS.md on YYYY-MM-DD*

### Defect Prevention Patterns
[Categorized by root cause: code_logic, integration_error, prompt_engineering, etc.]

### Content Quality Patterns
[Categorized by pattern type: agent_architecture, chart_integration, etc.]

### Architectural Patterns
[Categorized by architectural concern: agent_architecture, data_flow, etc.]
```

**Injection Point**: Before the `## Additional Resources` section

## Pattern Counts (Current)

As of 2026-01-05:
- **Defect Prevention**: 8 patterns (BUG-015 through BUG-028)
- **Content Quality**: 36 patterns
- **Architectural**: 14 patterns
- **Total**: 58 patterns synced

## How GitHub Copilot Uses These Patterns

When you're coding in VS Code with GitHub Copilot active:

1. **Context Loading**: Copilot reads `.github/copilot-instructions.md` for each file
2. **Pattern Matching**: If your code touches related areas, Copilot references learned patterns
3. **Suggestion Steering**: Copilot avoids suggesting code that matches anti-patterns
4. **Proactive Prevention**: Copilot may suggest fixes based on prevention strategies

### Example: BUG-016 Prevention

When you edit `scripts/writer_agent.py`:
- **Pattern Known**: "Charts generated but never embedded in articles"
- **Copilot Behavior**: Suggests chart embedding code when chart_data is present
- **Prevention**: Won't generate code that creates charts without embedding them

## Validation

After syncing, verify the update:

```bash
# Check the diff
git diff .github/copilot-instructions.md

# Count patterns synced
grep -c "^\*\*" .github/copilot-instructions.md

# View the auto-generated section
sed -n '/## Learned Anti-Patterns/,/## Additional Resources/p' .github/copilot-instructions.md
```

## Troubleshooting

### Sync Reports No Patterns
**Cause**: Source files don't contain RCA data or patterns
**Fix**: 
- Ensure bugs in defect_tracker.json have `root_cause`, `missed_by_test_type`, and `prevention_strategy`
- Ensure blog_qa_skills.json has patterns with `severity` and `pattern` fields
- Ensure ARCHITECTURE_PATTERNS.md exists and is properly formatted

### Sync Fails with ModuleNotFoundError
**Cause**: Using system python instead of .venv
**Fix**: Always use `.venv/bin/python scripts/sync_copilot_context.py`

### GitHub Actions Workflow Fails
**Cause**: uv installation or venv creation issues
**Fix**: Check Actions logs, ensure python-version matches .python-version file

### Copilot Not Using Patterns
**Cause**: VS Code may not have reloaded the instructions
**Fix**:
1. Commit and push the updated copilot-instructions.md
2. Reload VS Code window (Cmd+Shift+P → "Reload Window")
3. Try opening a file related to the pattern
4. Copilot should now reference the learned patterns

## Best Practices

### When to Sync Manually
✅ **Do sync after**:
- Fixing a bug with full RCA (root_cause, test_gap, prevention_strategy)
- Completing a sprint retrospective with new learnings
- Discovering and documenting a new architectural pattern
- Major refactoring that establishes new conventions

❌ **Don't sync**:
- Before adding RCA data to bugs (incomplete data)
- Multiple times per hour (let automatic sync handle it)
- Without testing in dry-run mode first

### Pattern Quality
For patterns to be useful to Copilot:
- **Be specific**: "Charts not embedded" > "Chart issues"
- **Include checks**: "Scan for markdown ![...](chart.png)" > "Check charts"
- **Document prevention**: What code/process prevents recurrence?
- **Categorize correctly**: Use standard root_cause/category values

### Monitoring Effectiveness
Track these metrics over time:
- Pattern count growth (are we learning?)
- Defect escape rate (are patterns preventing bugs?)
- Time to detect bugs (are we catching them earlier?)
- Developer feedback (does Copilot mention patterns?)

## Integration with Development Workflow

### Sprint Retrospectives
```bash
# After retrospective, add new patterns to skills
vim skills/blog_qa_skills.json

# Sync immediately
.venv/bin/python scripts/sync_copilot_context.py

# Commit with context
git add skills/blog_qa_skills.json .github/copilot-instructions.md
git commit -m "retro: Add Sprint X learnings to Copilot context"
```

### Bug Fixes
```bash
# Fix the bug in code
vim scripts/writer_agent.py

# Update defect tracker with RCA
python scripts/defect_tracker.py  # (or edit JSON directly)

# Sync patterns (automatic via GitHub Actions on push)
# OR run manually: .venv/bin/python scripts/sync_copilot_context.py
```

### Pre-commit Hook (Optional)
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Auto-sync if defect tracker or skills changed
if git diff --cached --name-only | grep -q "skills/\|ARCHITECTURE_PATTERNS.md"; then
    .venv/bin/python scripts/sync_copilot_context.py
    git add .github/copilot-instructions.md
fi
```

## Future Enhancements

Potential improvements to the system:
- [ ] Bidirectional sync: Copilot suggests new patterns for review
- [ ] Pattern prioritization: Weight by frequency/severity
- [ ] Pattern expiration: Archive old patterns that are no longer relevant
- [ ] Metrics dashboard: Track sync history and pattern usage
- [ ] Pattern deduplication: Detect and merge similar patterns
- [ ] Cross-project sharing: Export/import learned patterns
- [ ] LLM-based synthesis: Auto-generate pattern descriptions from code diffs

## Additional Resources

- [sync_copilot_context.py](scripts/sync_copilot_context.py) - Sync script source
- [defect_tracker.py](scripts/defect_tracker.py) - Bug tracking with RCA
- [skills_manager.py](scripts/skills_manager.py) - Skills learning system
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Copilot context (target file)

---

**Last Updated**: 2026-01-05  
**Pattern Count**: 58 (8 defect + 36 QA + 14 architecture)  
**Status**: ✅ Fully operational with automatic GitHub Actions sync
