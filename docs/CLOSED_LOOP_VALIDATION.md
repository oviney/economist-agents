# Closed-Loop Validation Script

## Overview

`scripts/validate_closed_loop.py` is a master validation script that programmatically verifies the entire closed-loop learning architecture by testing each component and their integrations.

## Purpose

This script ensures that all components of the learning system work together correctly:

1. **Storage** - SkillsManager creates JSON files with orjson
2. **Synthesis** - skill_synthesizer.py processes logs and extracts patterns
3. **Integration** - blog_qa_agent.py updates skills from errors
4. **Sync** - sync_copilot_context.py updates copilot instructions
5. **Reporting** - skills_gap_analyzer.py generates team assessments

## Quick Start

```bash
# Run all validation stages
python3 scripts/validate_closed_loop.py

# Run with verbose output
python3 scripts/validate_closed_loop.py --verbose

# Run specific stage only
python3 scripts/validate_closed_loop.py --stage storage
```

## Usage Examples

### Full Validation

```bash
$ python3 scripts/validate_closed_loop.py

╔════════════════════════════════════════════════════════════════╗
║ CLOSED-LOOP LEARNING ARCHITECTURE VALIDATION                   ║
╚════════════════════════════════════════════════════════════════╝

[1/5] Storage Check (SkillsManager)......................... ✅ PASS
[2/5] Synthesis Check (skill_synthesizer)................... ✅ PASS
[3/5] Integration Check (blog_qa_agent)..................... ✅ PASS
[4/5] Sync Check (sync_copilot_context)..................... ✅ PASS
[5/5] Reporting Check (skills_gap_analyzer)................. ✅ PASS

╔════════════════════════════════════════════════════════════════╗
║ VALIDATION RESULT: ✅ ALL CHECKS PASSED (5/5)                  ║
╚════════════════════════════════════════════════════════════════╝
```

### Verbose Mode

```bash
$ python3 scripts/validate_closed_loop.py --verbose

[1/5] Storage Check (SkillsManager).........................
   ℹ  Creating SkillsManager with role: test_bot
   ℹ  Skills file created: /tmp/test_bot_skills.json
   ℹ  ✓ File successfully parsed with orjson
   ℹ  ✓ All required keys present
   ℹ  ✓ learn_pattern() correctly saved pattern
✅ PASS
   ℹ  Cleaned up: /tmp/test_bot_skills.json
```

### Single Stage Validation

```bash
# Test storage only
$ python3 scripts/validate_closed_loop.py --stage storage

# Test synthesis only
$ python3 scripts/validate_closed_loop.py --stage synthesis

# Test integration only
$ python3 scripts/validate_closed_loop.py --stage integration
```

## Validation Stages

### Stage 1: Storage Check

**Purpose**: Verify SkillsManager creates JSON files with orjson

**What it tests**:
- SkillsManager creates skills file with correct structure
- File can be read/written with orjson (not standard json)
- learn_pattern() saves patterns correctly
- File contains required keys: version, last_updated, skills, validation_stats

**Test artifacts**: Creates temporary test_bot_skills.json (auto-cleaned)

### Stage 2: Synthesis Check

**Purpose**: Verify skill_synthesizer.py processes logs correctly

**What it tests**:
- skill_synthesizer.py exists and is executable
- Processes mock failure logs without errors
- Extracts patterns matching SkillsManager schema
- Pattern fields: category, pattern_id, severity, pattern, check, learned_from
- Severity values: critical, high, medium, low

**Test artifacts**: Creates temporary mock failure log (auto-cleaned)

### Stage 3: Integration Check

**Purpose**: Verify blog_qa_agent.py updates skills from errors

**What it tests**:
- blog_qa_agent.py exists and is executable
- Creates valid Jekyll blog structure
- Detects validation issues in test posts
- Can update skills file (when learning enabled)
- Broken link detection working
- Category field validation working

**Test artifacts**: Creates temporary test blog structure (auto-cleaned)

### Stage 4: Sync Check

**Purpose**: Verify sync_copilot_context.py updates copilot instructions

**What it tests**:
- sync_copilot_context.py exists and is executable
- Copilot instructions file exists
- "Learned Anti-Patterns" section present
- Script runs without errors in dry-run mode
- Pattern synchronization working

**Test artifacts**: None (uses existing files)

### Stage 5: Reporting Check

**Purpose**: Verify skills_gap_analyzer.py generates reports

**What it tests**:
- skills_gap_analyzer.py exists and is executable
- Generates "Team Skills Assessment" section
- Outputs markdown table format
- Role-based skills analysis working
- Report generation completes without errors

**Test artifacts**: None (only generates output)

## Command-Line Options

```
usage: validate_closed_loop.py [-h] [--verbose] [--stage {storage,synthesis,integration,sync,reporting}]
                               [--cleanup-only]

options:
  -h, --help            show this help message and exit
  --verbose, -v         Enable verbose output
  --stage, -s {storage,synthesis,integration,sync,reporting}
                        Run specific stage only
  --cleanup-only        Cleanup test artifacts only (no validation)
```

## Exit Codes

- **0** - All validation stages passed
- **1** - One or more validation stages failed

## Test Fixtures

### Mock Failure Log

```
Blog QA Validation Run - 2026-01-06T12:00:00
============================================================

Posts Validated: 1
Issues Found: 2

VALIDATION ISSUES:
------------------------------------------------------------
1. [YAML] Missing required field: categories
2. [LINKS] Line 15: Broken asset link: /assets/missing.png
```

### Mock Blog Post

```markdown
---
layout: post
title: "Test Article"
date: 2026-01-06
---

# Test Article

This is a test article with a broken link to [missing image](/assets/missing.png).
```

### Expected Pattern Schema

```json
{
  "required_fields": [
    "category",
    "pattern_id",
    "severity",
    "pattern",
    "check",
    "learned_from"
  ],
  "severity_values": ["critical", "high", "medium", "low"]
}
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: Validate Closed-Loop Architecture

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run validation
        run: python3 scripts/validate_closed_loop.py
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run validation before commit
python3 scripts/validate_closed_loop.py --stage storage --stage synthesis

if [ $? -ne 0 ]; then
    echo "❌ Closed-loop validation failed"
    exit 1
fi
```

## Troubleshooting

### ModuleNotFoundError: orjson

**Problem**: Script fails with `ModuleNotFoundError: No module named 'orjson'`

**Solution**: Activate virtual environment
```bash
source .venv/bin/activate
python3 scripts/validate_closed_loop.py
```

### Stage Timeout

**Problem**: Stage times out after 30 seconds

**Solution**: Check if LLM API is accessible (for synthesis stage)
```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 scripts/validate_closed_loop.py --stage synthesis
```

### Cleanup Errors

**Problem**: Temporary files not cleaned up

**Solution**: Run cleanup-only mode
```bash
python3 scripts/validate_closed_loop.py --cleanup-only
```

## Development

### Adding New Validation Stages

1. Create new `ValidationStage` subclass:

```python
class MyCheck(ValidationStage):
    """Stage N: Verify my component."""

    def __init__(self, verbose: bool = False):
        super().__init__("My Check (my_component)", verbose)

    def validate(self) -> bool:
        """Run validation logic."""
        try:
            # Your validation logic here
            self.log("✓ Check passed")
            return True
        except Exception as e:
            self.error(f"Check failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up test artifacts."""
        pass
```

2. Add to orchestrator:

```python
self.stages: list[ValidationStage] = [
    StorageCheck(verbose),
    SynthesisCheck(verbose),
    IntegrationCheck(verbose),
    SyncCheck(verbose),
    ReportingCheck(verbose),
    MyCheck(verbose),  # Add new stage
]
```

### Running Unit Tests

```bash
# Run validation script tests
python3 -m pytest tests/test_closed_loop_validation.py -v

# Run with coverage
python3 -m pytest tests/test_closed_loop_validation.py --cov=scripts --cov-report=html
```

## Related Documentation

- [SKILLS_LEARNING.md](../docs/SKILLS_LEARNING.md) - Skills system overview
- [SKILL_SYNTHESIZER_GUIDE.md](../SKILL_SYNTHESIZER_GUIDE.md) - Pattern synthesis
- [SKILLS_GAP_ANALYZER_SUMMARY.md](../SKILLS_GAP_ANALYZER_SUMMARY.md) - Team assessment
- [COPILOT_SYNC.md](../COPILOT_SYNC.md) - Copilot synchronization

## Metrics

### Performance

- **Full validation**: ~5-10 seconds
- **Storage check**: ~0.5 seconds
- **Synthesis check**: ~2-3 seconds (with LLM)
- **Integration check**: ~1-2 seconds
- **Sync check**: ~1 second
- **Reporting check**: ~1-2 seconds

### Coverage

- **5 validation stages** covering end-to-end flow
- **7 unit tests** for validation logic
- **Automatic cleanup** of test artifacts
- **Exit codes** for CI/CD integration

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 Closed-Loop Validation Script               │
└─────────────────────────────────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Storage   │    │  Synthesis  │    │ Integration │
│    Check    │    │    Check    │    │    Check    │
│             │    │             │    │             │
│ Skills      │    │ Pattern     │    │ blog_qa     │
│ Manager     │    │ Extraction  │    │ Skills      │
│             │    │             │    │ Update      │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
┌─────────────┐                        ┌─────────────┐
│    Sync     │                        │  Reporting  │
│    Check    │                        │    Check    │
│             │                        │             │
│ Copilot     │                        │ Team Skills │
│ Context     │                        │ Assessment  │
└─────────────┘                        └─────────────┘
```

## Best Practices

1. **Run before commits** - Catch integration issues early
2. **Use --verbose for debugging** - See detailed validation steps
3. **Run single stages** - Faster iteration during development
4. **Integrate with CI/CD** - Prevent broken deployments
5. **Keep fixtures up-to-date** - Match real-world scenarios

## Version History

- **1.0.0** (2026-01-06) - Initial release with 5 validation stages
  - Storage check for SkillsManager
  - Synthesis check for skill_synthesizer.py
  - Integration check for blog_qa_agent.py
  - Sync check for sync_copilot_context.py
  - Reporting check for skills_gap_analyzer.py
