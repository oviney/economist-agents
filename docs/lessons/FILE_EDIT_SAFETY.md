# File Edit Safety Guidelines

**Purpose**: Prevent file corruption from overlapping multi-edit operations (Sprint 8 Story 4 lesson)

**Incident**: agents/editor_agent.py corrupted (2026-01-02) via 4 sequential `replace_string_in_file` operations without intermediate validation. Symptoms: unterminated strings (line 529), duplicate methods, incomplete class structures.

**Recovery Time**: 3 hours (Sprint 9 Story 1 reconstruction)

---

## Multi-Edit Anti-Patterns (~50 lines)

### 1. Overlapping Context Windows ❌

**Problem**: Sequential edits to same file without re-reading current state.

**Example** (Sprint 8):
```
Edit 1: Add GATE_PATTERNS at lines 15-25
Edit 2: Add method at lines 200-228 (but line 200 is now 210!)
Edit 3: Add method at lines 230-249 (context shifted again)
Edit 4: Modify edit() at lines 180-190 (overlaps with Edit 2)
Result: Corruption - unterminated strings, duplicate definitions
```

**Why It Fails**: Line numbers shift after each edit. Using stale line numbers causes overlapping replacements.

### 2. Insufficient Context ❌

**Problem**: oldString matches multiple locations.

**Example**:
```python
# Ambiguous (matches 3 places):
oldString = "def edit(self, draft: str):"

# Unique (matches 1 place):
oldString = """
    def edit(self, draft: str) -> tuple[str, int, int]:
        \"\"\"Run Editor Agent with quality gates.\"\"\"
        
        print("🔍 Editor Agent: Quality gates...")
"""
```

**Rule**: Include 5+ lines of unique surrounding context.

### 3. Untracked Files ❌

**Problem**: Can't recover with `git restore` if file not committed.

**Sprint 8**: agents/editor_agent.py was newly extracted (untracked) → git restore failed → required full reconstruction.

**Rule**: Commit files before complex edits OR create timestamped backup: `cp file.py file.py.backup-$(date +%Y%m%d-%H%M%S)`

### 4. No Validation Between Edits ❌

**Problem**: Corruption discovered only after Edit 4.

**Should Have**: Validated after each edit:
```bash
python3 -m py_compile agents/editor_agent.py
```

If syntax check had run after Edit 2, corruption would have been caught 2 edits earlier.

### 5. Large Insertions in Single Edit ❌

**Problem**: Inserting 20+ line methods increases risk of context mismatch.

**Better**: Split into smaller edits (5-10 lines each) with validation between.

---

## Safe Edit Patterns (~75 lines)

### 1. Atomic Single-Edit Operations ✅

**Pattern**: One `replace_string_in_file` → validate → commit. Repeat.

```bash
# Edit 1
replace_string_in_file(file, old, new)
python3 -m py_compile file.py
git commit -m "Add import"

# Edit 2
replace_string_in_file(file, old2, new2)
python3 -m py_compile file.py
git commit -m "Add constant"
```

**Benefits**: Clear history, easy rollback, identifies problematic edit immediately.

### 2. Read → Validate → Write ✅

**Pattern**: Always read current file state before next edit.

```python
# Step 1: Read current state
read_file(path, 1, 100)

# Step 2: Plan edit using CURRENT line numbers

# Step 3: Validate oldString with 5+ unique lines

# Step 4: Execute
replace_string_in_file(path, old, new)

# Step 5: Re-read to confirm
read_file(path, 90, 110)

# Step 6: Syntax check
python3 -m py_compile path
```

**Sprint 8 Lesson**: After Edit 1 added GATE_PATTERNS, should have re-read file to see where edit() method actually was.

### 3. Backup Before Complex Edits ✅

**When**: Any file requiring 2+ edits in same session.

```bash
# Timestamped backup
cp file.py file.py.backup-$(date +%Y%m%d-%H%M%S)

# Or git checkpoint
git add file.py
git commit -m "WIP: Pre-edit checkpoint"
```

**Sprint 8 Outcome**: No backups existed, required complete reconstruction (3 hours).

### 4. JSON Schema Validation ✅

**Pattern**: For structured files, validate both syntax and schema.

```python
import json

# Validate JSON after edit
with open('file.json') as f:
    data = json.load(f)  # Syntax check

# Schema check
assert 'current_sprint' in data
assert isinstance(data['current_sprint'], int)
```

### 5. Prefer Regeneration Over Multi-Edit ✅

**When to Regenerate**: File needs 5+ edits, significant restructuring, or large sections replaced.

**Sprint 9 Example**:
```python
# Instead of 10 edits to fix editor_agent.py:
# 1. Read SPRINT_8_STORY_4_REMEDIATION_COMPLETE.md (complete code)
# 2. Regenerate EditorAgent class from docs
# 3. Single write operation
# 4. Validate + test
```

**Benefits**: No overlapping edits, guaranteed consistency, faster.

---

## Recovery Procedures (~50 lines)

### Detection (30 seconds)

**Symptoms**: `SyntaxError`, `json.JSONDecodeError`, missing delimiters (`"""`, `}`), duplicate definitions.

**Quick Check**:
```bash
python3 -m py_compile file.py  # Syntax
ruff check file.py             # Linting
```

### Recovery Options (1-60 min)

**Option 1: Git Restore** (if tracked, 1 min)
```bash
git restore agents/editor_agent.py
```

**Option 2: Backup Restore** (if created, 2 min)
```bash
ls -lt agents/*.backup-* | head -1
cp agents/editor_agent.py.backup-20260102-1430 agents/editor_agent.py
```

**Option 3: Documentation Reconstruction** (30-60 min)
```bash
# Sprint 8 method:
# 1. Find complete code in docs/*_COMPLETE.md
# 2. Extract relevant class/function
# 3. Recreate file
# 4. Validate + test
```

**Option 4: Minimal Stub** (5 min, unblocks imports)
```python
# Temporary - reconstruction needed
class EditorAgent:
    def __init__(self, client):
        self.client = client
    def edit(self, draft: str) -> tuple[str, int, int]:
        return (draft, 5, 0)
```

### Post-Recovery Validation

```bash
python3 -m py_compile file.py
ruff check file.py
mypy file.py --ignore-missing-imports
pytest tests/test_file.py -v
```

---

## Prevention Checklist (~50 lines)

### Pre-Edit (30 seconds)

- [ ] File is committed to git (or create backup: `cp file.py file.py.backup-$(date +%Y%m%d-%H%M%S)`)
- [ ] File passes syntax check (`python3 -m py_compile file.py`)
- [ ] You have 5+ lines of unique context for oldString match
- [ ] Edit is <10 lines (if larger, split into atomic steps)
- [ ] No other edits pending on this file

### During-Edit (real-time)

- [ ] Re-read file to confirm edit applied correctly
- [ ] Run syntax check immediately
- [ ] Commit if syntax valid (creates recovery checkpoint)

### Post-Edit (1 minute)

- [ ] Full syntax check: `python3 -m py_compile file.py`
- [ ] Linting: `ruff check file.py`
- [ ] Tests passing: `pytest tests/test_*.py`
- [ ] Git commit with descriptive message

### Multi-Edit Warning Signs

**Abort and restart if**:
- [ ] Edit 3+ fails to apply (context mismatch)
- [ ] Syntax check fails and you can't see why
- [ ] File growing unexpectedly large (duplicate content)
- [ ] Git diff shows unintended changes

**Sprint 8 Red Flag**: Edit 4 failed → should have aborted, created backup, restarted with atomic operations.

---

## Quick Reference Card

### ✅ DO
- Commit files to git before complex edits
- Create timestamped backups: `file.backup-$(date +%Y%m%d-%H%M%S)`
- Include 5+ lines of unique context in oldString
- Validate syntax after EVERY edit (`python3 -m py_compile`)
- Keep edits small (≤10 lines per operation)
- Re-read file state between edits

### ❌ DON'T
- Queue multiple edits without intermediate validation
- Edit untracked files without backup
- Use line numbers from before first edit
- Insert 20+ line methods in single edit
- Skip syntax validation "to save time"

---

## Sprint 8 Case Study

**Anti-Pattern (What Happened)**:
```
1. Edit 1: Add GATE_PATTERNS (no validation)
2. Edit 2: Add method (used stale line numbers)
3. Edit 3: Add method (overlapping context)
4. Edit 4: Modify edit() (corruption discovered)
```

**Result**: 3 hours recovery time.

**Safe Pattern (What Should Have Been)**:
```
1. git commit -m "Pre-edit checkpoint"
2. Edit 1 → validate → commit
3. Re-read file (update line numbers)
4. Edit 2 → validate → commit
5. Re-read file
6. Edit 3 → validate → commit
7. Edit 4 → validate → test → commit
```

**Result**: 4 clean commits, no corruption, easy rollback.

---

## Summary

**Prevention Cost**: 15 minutes validation per complex edit  
**Recovery Cost**: 3 hours (Sprint 8 example)  
**ROI**: 12:1 time savings

**Key Principles**:
1. Small atomic edits (one change per commit)
2. Validation after each edit (syntax + lint)
3. Backup before complexity (git or timestamped copies)
4. Read current state (don't assume line numbers)
5. Documentation (enables reconstruction)

---

**Last Updated**: 2026-01-03 (Sprint 9 Story 6)  
**Incident Reference**: Sprint 8 Story 4, agents/editor_agent.py corruption  
**Status**: Operational guide for all file editing operations
