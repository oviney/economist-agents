# Copilot Context Sync Guide

## Overview

The `scripts/sync_copilot_context.py` script automatically synchronizes learned patterns from your skills database and architecture documentation into GitHub Copilot instructions. This enables Copilot to enforce quality rules in real-time while you code.

## What Gets Synced

The script reads patterns from three sources:

1. **Defect Prevention Patterns** (`skills/defect_tracker.json`)
   - Fixed bugs with root cause analysis
   - Prevention strategies and test gaps
   - 8 patterns currently tracked

2. **Content Quality Patterns** (`skills/blog_qa_skills.json`)
   - QA validation rules learned from production issues
   - Auto-fix strategies where available
   - 36 patterns currently tracked

3. **Architectural Patterns** (`docs/ARCHITECTURE_PATTERNS.md`)
   - Design patterns and best practices
   - Code organization principles
   - 14 patterns currently tracked

## Usage

### Basic Sync
```bash
python3 scripts/sync_copilot_context.py
```

This will:
- Extract all patterns from skills/*.json and docs/
- Format them into markdown sections
- Update `.github/copilot-instructions.md` "Learned Anti-Patterns" section
- Add timestamp to track when sync occurred

### Dry Run (Preview Changes)
```bash
python3 scripts/sync_copilot_context.py --dry-run
```

Shows what would be updated without modifying any files. Useful for:
- Verifying pattern extraction works correctly
- Previewing formatted output
- Testing after adding new patterns

### Output Example
```
2026-01-06 07:57:48,653 - INFO - Extracting patterns from skills and docs...
2026-01-06 07:57:48,653 - INFO - Extracted 8 defect patterns
2026-01-06 07:57:48,653 - INFO - Extracted 36 QA skill patterns
2026-01-06 07:57:48,654 - INFO - Extracted 14 architecture patterns
2026-01-06 07:57:48,654 - INFO - Total patterns extracted: 58
2026-01-06 07:57:48,655 - INFO - ✅ Successfully synced 58 patterns to Copilot instructions
```

## When to Run

### Automatically
Consider adding to:
- **Pre-commit hook**: Sync before each commit
- **CI/CD pipeline**: Sync after defect tracker updates
- **Weekly cron job**: Keep patterns fresh

### Manually
Run after:
- Adding new bugs to defect tracker
- Creating new QA skills patterns
- Updating architecture documentation
- Major sprint completions

## Integration with Copilot

Once synced, GitHub Copilot will:
- Suggest code that follows learned patterns
- Warn about known anti-patterns in real-time
- Provide inline documentation for quality checks
- Reference specific bug IDs and prevention strategies

### Example Benefits

**Before Sync:**
```python
# Copilot suggests generic code
response = client.messages.create(...)
```

**After Sync (with BUG-028 pattern):**
```python
# Copilot knows to add YAML delimiter
article = f"---\ntitle: {title}\ndate: {date}\n---\n\n{content}"
```

## Pattern Format

### Defect Prevention Patterns
```markdown
**BUG-XXX** (severity) - component
- **Issue**: Description of the bug
- **Missed By**: Test type that should have caught it
- **Prevention**:
  - Action 1
  - Action 2
```

### Content Quality Patterns
```markdown
**pattern_id** (severity)
- **Pattern**: What to look for
- **Check**: How to validate
- **Auto-fix**: Automated remediation (if available)
```

### Architectural Patterns
```markdown
**Pattern Name** (severity)
- **Pattern**: Core principle
- **Rationale**: Why this matters
- **Check**: How to validate adherence
```

## Troubleshooting

### Missing Dependency
```bash
ModuleNotFoundError: No module named 'orjson'
```
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### No Patterns Extracted
```bash
WARNING - No patterns extracted - nothing to sync
```
**Causes:**
- Empty or missing JSON files in skills/
- ARCHITECTURE_PATTERNS.md not found
- JSON parsing errors

**Solution:** Check that source files exist and are valid

### Update Failed
```bash
ERROR - Failed to update copilot instructions
```
**Solution:** Verify `.github/copilot-instructions.md` exists and is writable

## Maintenance

### Adding New Pattern Sources

To sync from additional JSON files, edit `sync_copilot_context.py`:

```python
def extract_custom_patterns(self) -> list[dict[str, Any]]:
    """Extract patterns from custom source."""
    patterns = []
    custom_file = self.skills_dir / "custom_patterns.json"
    
    # Add extraction logic
    
    return patterns
```

Then update `format_anti_patterns_section()` to include the new source.

### Testing Changes

Always test with `--dry-run` first:
```bash
# Make changes to pattern extraction
python3 scripts/sync_copilot_context.py --dry-run

# Verify output looks correct
# Then run without --dry-run
python3 scripts/sync_copilot_context.py
```

## Related Documentation

- [skills_manager.py](../scripts/skills_manager.py) - Pattern persistence layer
- [defect_tracker.py](../scripts/defect_tracker.py) - Bug tracking with RCA
- [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md) - Source of truth for patterns
- [copilot-instructions.md](../.github/copilot-instructions.md) - Target file for sync

## Best Practices

1. **Sync frequently**: Run after each bug fix or pattern discovery
2. **Commit synced changes**: Track pattern evolution in git history
3. **Review before merge**: Ensure patterns are accurate and helpful
4. **Update sources first**: Fix patterns in skills/*.json, then sync
5. **Use dry-run**: Always preview before updating production instructions

## Impact Metrics

**Current Sync Status:**
- 58 total patterns synchronized
- 8 defect prevention patterns (from real bugs)
- 36 content quality patterns (from QA learnings)
- 14 architectural patterns (from code reviews)
- Last updated: 2026-01-06

This creates a living knowledge base that improves code quality with every commit.
