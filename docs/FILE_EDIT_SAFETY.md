# File Edit Safety Guide - Multi-Replace Operations

**Purpose**: Prevent file corruption when editing code with AI agents  
**Context**: Sprint 8 Story 4 file corruption (editor_agent.py became syntactically invalid)  
**Last Updated**: 2026-01-03

---

## The Problem

**Sprint 8 Incident** (editor_agent.py corruption):
- Multiple `replace_string_in_file` operations on same file
- Overlapping edits created invalid syntax:
  - Unterminated triple-quoted strings (line 529)
  - Duplicate method definitions (edit() appeared twice)
  - Incomplete class structure
  - SyntaxError preventing Python parsing
- Recovery attempts failed (file untracked, no clean backup)
- Resolution: Created minimal stub, deferred full reconstruction to Sprint 9

**Root Cause**: Multiple sequential replace operations on same file without validation between edits

---

## Safe Editing Patterns

### Pattern 1: Single-Shot Edits (Recommended)

Use `multi_replace_string_in_file` for multiple changes to same file:

```python
multi_replace_string_in_file(
    explanation="Fix Editor Agent gate counting + temperature",
    replacements=[
        {
            "filePath": "/path/to/file.py",
            "oldString": """    def parse_gates(self, response):
        # Current logic
        return gates""",
            "newString": """    def parse_gates(self, response):
        # New logic with regex
        return gates""",
            "explanation": "Fix gate counting logic"
        },
        {
            "filePath": "/path/to/file.py",
            "oldString": """        response = call_llm(client, prompt, msg, max_tokens=4000)""",
            "newString": """        response = call_llm(client, prompt, msg, max_tokens=4000, temperature=0.0)""",
            "explanation": "Add deterministic temperature"
        }
    ]
)
```

**Benefits**:
- All edits validated together
- Atomic operation (all succeed or all fail)
- Clear failure messages if any edit fails

**When to Use**:
- Multiple changes to same file
- Related changes (same feature/fix)
- Complex refactoring

---

### Pattern 2: Edit-Validate-Edit (For Complex Changes)

For large refactors, validate syntax after each logical group:

```python
# Step 1: Edit method A
replace_string_in_file(...)

# Step 2: VALIDATE - run syntax check
run_in_terminal(
    command="python -m py_compile path/to/file.py",
    explanation="Validate syntax after edit",
    isBackground=False
)

# Step 3: If valid, proceed to method B
replace_string_in_file(...)

# Step 4: VALIDATE again
run_in_terminal(...)
```

**Benefits**:
- Early detection of syntax errors
- Easier to identify which edit broke syntax
- Can recover after each checkpoint

**When to Use**:
- Large class restructuring
- Method signature changes
- Import reorganization

---

### Pattern 3: File Backup (For High-Risk Edits)

For risky operations, create backup first:

```bash
# Create backup
cp file.py file.py.backup

# Make edits
# ...

# Validate
python -m py_compile file.py

# If valid: remove backup
# If invalid: restore from backup
mv file.py.backup file.py
```

**When to Use**:
- Untested refactoring patterns
- Editing files with complex dependencies
- Multi-agent file modifications

---

## Required Context for AI Agents

**Rule**: Include 3-5 lines of unchanged code before AND after target section

### ❌ WRONG (Insufficient Context)

```python
oldString = """def parse_gates(self):
    return gates"""
```

**Problem**: Multiple locations could match, wrong section gets replaced

### ✅ CORRECT (Adequate Context)

```python
oldString = """    def run_editor_agent(self, client, draft):
        # Existing code
        
        def parse_gates(self, response):
            # Current logic
            return gates
        
        # More existing code
        return edited_article"""
```

**Benefits**:
- Unique match location
- Preserves surrounding code
- Clear intent

---

## Validation Checklist

**Before Committing Multi-Edit Changes**:

- [ ] File syntax valid: `python -m py_compile file.py`
- [ ] Imports still work: `python -c "import module"`
- [ ] Tests pass: `pytest tests/test_file.py`
- [ ] No duplicate definitions: `grep -n "def method_name" file.py`
- [ ] String literals closed: No unterminated quotes
- [ ] Indentation consistent: `ruff check file.py`

**Automated Pre-Commit Hook** (Recommended):

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate all Python files
for file in $(git diff --cached --name-only --diff-filter=AM | grep '\.py$'); do
    python -m py_compile "$file"
    if [ $? -ne 0 ]; then
        echo "❌ Syntax error in $file"
        exit 1
    fi
done

echo "✅ All Python files valid"
```

---

## Recovery Procedures

### Scenario 1: Syntax Error After Edit

```bash
# Check error location
python -m py_compile file.py
# SyntaxError: unterminated string literal at line 529

# Option A: Git restore (if tracked)
git restore file.py

# Option B: Restore from backup
mv file.py.backup file.py

# Option C: Manual fix with context
# Open file, fix line 529, validate
```

### Scenario 2: File Corruption (Sprint 8 Pattern)

**Symptoms**:
- Multiple duplicate methods
- Unterminated strings
- Invalid class structure

**Recovery**:
1. Check git history: `git log --all -- path/to/file.py`
2. If tracked: `git restore file.py`
3. If untracked: Search for backup copies
4. Last resort: Create minimal stub, defer reconstruction

**Lesson**: Track all files before multi-edit operations

---

## Best Practices Summary

### DO ✅

- Use `multi_replace_string_in_file` for same-file edits
- Include 3-5 lines context before/after
- Validate syntax after each edit group
- Create backup before risky operations
- Run pre-commit hooks before pushing
- Track files in git before major edits

### DON'T ❌

- Use multiple sequential `replace_string_in_file` on same file
- Edit with minimal context (1-2 lines)
- Skip validation between edit groups
- Assume edits will work without testing
- Commit without running `py_compile`
- Edit untracked files without backup

---

## Tool Comparison

| Tool | Use Case | Safety | Speed |
|------|----------|--------|-------|
| `multi_replace_string_in_file` | Multiple edits, same file | High | Fast |
| `replace_string_in_file` | Single edit | Medium | Fast |
| Manual edit + commit | Complex restructure | Low | Slow |
| Edit-Validate-Edit pattern | Large refactor | High | Medium |

---

## Related Documentation

- [Scrum Master Protocol](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [Sprint 8 Story 4 Remediation](SPRINT_8_STORY_4_REMEDIATION_COMPLETE.md) - File corruption incident
- [Sprint 9 Story 1 Complete](SPRINT_9_STORY_1_COMPLETE.md) - Reconstruction after corruption

---

**Version**: 1.0  
**Status**: Active  
**Applies To**: All Python file editing operations  
**Enforcement**: Pre-commit hook + Code review
