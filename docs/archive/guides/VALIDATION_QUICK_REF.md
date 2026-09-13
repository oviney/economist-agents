# validate_closed_loop.py - Quick Reference

## Basic Usage

```bash
# Run all checks
python3 scripts/validate_closed_loop.py

# Verbose output
python3 scripts/validate_closed_loop.py --verbose

# Single stage
python3 scripts/validate_closed_loop.py --stage storage
```

## Stage Options

| Stage | Tests | Speed |
|-------|-------|-------|
| `storage` | SkillsManager + orjson | Fast (0.5s) |
| `synthesis` | skill_synthesizer.py | Medium (2-3s) |
| `integration` | blog_qa_agent.py | Medium (1-2s) |
| `sync` | sync_copilot_context.py | Fast (1s) |
| `reporting` | skills_gap_analyzer.py | Medium (1-2s) |

## Exit Codes

- `0` - All checks passed ✅
- `1` - One or more checks failed ❌

## Common Commands

```bash
# Full validation
./scripts/validate_closed_loop.py

# Debug a failing stage
./scripts/validate_closed_loop.py --stage synthesis --verbose

# Quick storage check
./scripts/validate_closed_loop.py --stage storage

# Help
./scripts/validate_closed_loop.py --help
```

## What Each Stage Validates

### Storage Check
- ✓ SkillsManager creates files
- ✓ Uses orjson (not json)
- ✓ learn_pattern() works
- ✓ File structure correct

### Synthesis Check
- ✓ skill_synthesizer.py runs
- ✓ Extracts patterns from logs
- ✓ Pattern schema valid
- ✓ Severity values correct

### Integration Check
- ✓ blog_qa_agent.py runs
- ✓ Detects validation issues
- ✓ Updates skills file
- ✓ Broken link detection

### Sync Check
- ✓ sync_copilot_context.py runs
- ✓ Copilot instructions exist
- ✓ "Learned Anti-Patterns" present
- ✓ Synchronization works

### Reporting Check
- ✓ skills_gap_analyzer.py runs
- ✓ "Team Skills Assessment" generated
- ✓ Markdown table format
- ✓ Role-based analysis

## Troubleshooting

### ModuleNotFoundError: orjson
```bash
source .venv/bin/activate
python3 scripts/validate_closed_loop.py
```

### Stage times out
```bash
export ANTHROPIC_API_KEY='your-key'
python3 scripts/validate_closed_loop.py --stage synthesis
```

### See what's happening
```bash
python3 scripts/validate_closed_loop.py --verbose
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Validate Architecture
  run: python3 scripts/validate_closed_loop.py
```

### Pre-commit Hook
```bash
python3 scripts/validate_closed_loop.py --stage storage
```

## Files

- Script: `scripts/validate_closed_loop.py`
- Tests: `tests/test_closed_loop_validation.py`
- Docs: `docs/CLOSED_LOOP_VALIDATION.md`

---

**Quick Status Check**: `python3 scripts/validate_closed_loop.py`
