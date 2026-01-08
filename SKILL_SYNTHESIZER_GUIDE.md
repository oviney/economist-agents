# Skill Synthesizer Guide

## Overview

`scripts/skill_synthesizer.py` is an automated learning system that parses failure logs (like `generation.log`, pytest output, or error traces) and uses LLM analysis to identify root causes. It generates structured patterns matching the `SkillsManager.learn_pattern` schema to ensure no learning is lost.

## How It Works

### 1. Log Parsing
The synthesizer auto-detects log format and extracts failure information:
- **Generation logs**: Quality gate failures, unverified claims, Visual QA issues, word count problems
- **Pytest output**: Test failures, error messages
- **Generic errors**: Python tracebacks, error keywords

### 2. LLM Analysis
Uses OpenAI GPT-4o (or configured LLM) to:
- Identify root causes of failures
- Extract actionable patterns (things that can be detected automatically)
- Ignore transient issues (network timeouts, rate limits)
- Provide specific validation rules

### 3. Pattern Generation
Generates JSON matching `SkillsManager.learn_pattern` schema:
```json
{
  "category": "quality_gates",
  "pattern_id": "editorial_gate_failure",
  "severity": "high",
  "pattern": "Editor Agent failed 3/5 quality gates on draft content",
  "check": "Verify editor_agent response has 'Quality gates: X passed, Y failed' and X >= 4",
  "learned_from": "generation.log editorial review section",
  "prevention_strategy": "Add pre-editor validation to catch common issues before Editor Agent runs"
}
```

### 4. Skill Learning
Automatically applies patterns to role-specific `SkillsManager` instances:
- `skills/blog_qa_skills.json`
- `skills/editor_agent_skills.json`
- `skills/writer_agent_skills.json`
- etc.

## Usage Examples

### Test Run (Dry Run)
```bash
# Analyze generation.log without saving patterns
python3 scripts/skill_synthesizer.py \
  --log generation.log \
  --role editor_agent \
  --dry-run \
  -v
```

**Output:**
```
📊 Analyzing log: generation.log (1377 bytes)
   Log format: generation_log
   Failures detected: 3
🤖 Using LLM to synthesize patterns...
✅ Identified 2 patterns:
   [DRY RUN] Would learn: quality_gates.editorial_gate_failure
   [DRY RUN] Would learn: data_verification.unverified_claims_present

[DRY RUN] Would have saved 2 patterns
```

### Production Run
```bash
# Analyze and save patterns
python3 scripts/skill_synthesizer.py \
  --log generation.log \
  --role editor_agent
```

**Output:**
```
📊 Analyzing log: generation.log (1377 bytes)
🤖 Using LLM to synthesize patterns...
✅ Identified 2 patterns:
   - quality_gates.editorial_gate_failure (high severity)
   - data_verification.unverified_claims_present (medium severity)
💾 Saved 2 patterns to skills/editor_agent_skills.json

✅ Successfully learned 2 new patterns
   Skills file: skills/editor_agent_skills.json
```

### Category Filter
```bash
# Only learn patterns in specific category
python3 scripts/skill_synthesizer.py \
  --log validation.log \
  --role po_agent \
  --category requirements_gap
```

### Multiple Roles
```bash
# Analyze same log for different roles
python3 scripts/skill_synthesizer.py --log generation.log --role writer_agent
python3 scripts/skill_synthesizer.py --log generation.log --role editor_agent
python3 scripts/skill_synthesizer.py --log generation.log --role graphics_agent
```

## Integration with Automated Learning Loop

The skill synthesizer is designed for automated use in CI/CD or failure workflows:

### 1. Pre-commit Hook (Manual Learning)
```bash
# .git/hooks/pre-commit
if [ -f generation.log ]; then
  python3 scripts/skill_synthesizer.py --log generation.log --role blog_qa
fi
```

### 2. GitHub Actions (Automated Learning)
```yaml
# .github/workflows/learn-from-failures.yml
name: Learn from Failures
on:
  workflow_run:
    workflows: ["CI"]
    types:
      - completed
jobs:
  synthesize:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    steps:
      - uses: actions/checkout@v3
      - name: Download failure logs
        uses: actions/download-artifact@v3
        with:
          name: test-results
      - name: Synthesize patterns
        run: |
          python3 scripts/skill_synthesizer.py --log pytest_output.txt --role test_automation
      - name: Commit learned patterns
        run: |
          git add skills/
          git commit -m "chore: learned patterns from CI failure"
          git push
```

### 3. Blog QA Agent Integration
```python
# scripts/blog_qa_agent.py (existing integration point)
def run_learning_loop(log_path: Path, role_name: str = "blog_qa") -> bool:
    """Execute automated learning loop via skill_synthesizer.py."""
    if not log_path.exists():
        return False

    result = subprocess.run(
        [
            sys.executable,
            "scripts/skill_synthesizer.py",
            "--log", str(log_path),
            "--role", role_name,
            "--category", "blog_validation",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    return result.returncode == 0
```

## Pattern Categories

Typical categories used by the synthesizer:

- **quality_gates**: Editor Agent quality gate failures
- **data_verification**: Research Agent unverified claims
- **visual_qa**: Graphics Agent zone violations
- **content_quality**: Writer Agent style issues
- **integration_errors**: Agent coordination failures
- **performance**: Slow generation times
- **requirements_gap**: Missing or unclear requirements

## Validation Schema

Each pattern must match this schema (enforced by `SkillsManager.learn_pattern`):

```python
{
  "category": str,           # Required: Pattern category
  "pattern_id": str,         # Required: Unique identifier (lowercase_with_underscores)
  "severity": str,           # Required: "critical", "high", "medium", or "low"
  "pattern": str,            # Required: Human-readable description
  "check": str,              # Required: Specific validation rule
  "learned_from": str,       # Required: Source context
  "prevention_strategy": str # Optional: How to prevent in future
}
```

## Advanced Usage

### Custom Log Formats
The synthesizer auto-detects formats, but you can extend `LogParser` for custom formats:

```python
# scripts/skill_synthesizer.py

class LogParser:
    @staticmethod
    def parse_custom_format(content: str) -> dict[str, Any]:
        """Parse custom log format."""
        failures = []
        # Add custom parsing logic
        return {"format": "custom", "failures": failures, "raw_content": content}

    @classmethod
    def auto_parse(cls, content: str) -> dict[str, Any]:
        # Add custom detection
        if "CUSTOM_LOG_MARKER" in content:
            return cls.parse_custom_format(content)
        # ... existing logic
```

### LLM Provider Configuration
Uses `llm_client.py` for LLM provider abstraction:

```bash
# Use Anthropic Claude
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Use OpenAI (default)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

### Temperature Control
The synthesizer uses `temperature=0.0` for deterministic pattern extraction. This ensures consistent pattern identification across runs.

## Success Metrics

Track learning effectiveness:

```python
from skills_manager import SkillsManager

# View learned patterns
manager = SkillsManager(role_name="editor_agent")
stats = manager.get_stats()

print(f"Total runs: {stats['total_runs']}")
print(f"Issues found: {stats['issues_found']}")
print(f"Issues fixed: {stats['issues_fixed']}")

# View specific patterns
patterns = manager.get_patterns("quality_gates")
for pattern in patterns:
    print(f"{pattern['id']}: {pattern['pattern']}")
```

## Continuous Improvement

The skill synthesizer enables a continuous learning loop:

1. **Failure occurs** → Log generated
2. **Synthesizer analyzes** → Patterns identified
3. **Skills updated** → `SkillsManager` learns patterns
4. **Validation applies** → Future runs catch issues earlier
5. **Repeat** → System gets smarter over time

This mirrors how Claude learns from conversations - building context and improving over time.

## Troubleshooting

### No patterns identified
- Check log contains actual failures (not just warnings)
- Verify LLM API key is configured
- Use `--verbose` flag for detailed logging
- Try `--dry-run` to see LLM analysis without saving

### JSON parse errors
- LLM may wrap JSON in markdown fences (handled automatically)
- Check LLM response with `--verbose` flag
- Reduce log size if too large (synthesizer uses first 4000 bytes)

### Pattern validation failures
- Ensure all required fields present (severity, pattern, check, learned_from)
- Check severity is one of: critical, high, medium, low
- Verify pattern_id uses lowercase_with_underscores format

## Files

- **Implementation**: `scripts/skill_synthesizer.py` (500 lines)
- **Skills Manager**: `scripts/skills_manager.py` (288 lines)
- **LLM Client**: `scripts/llm_client.py` (283 lines)
- **Documentation**: `docs/SKILLS_LEARNING.md`

## Related Work

- **Blog QA Agent**: Uses skills system for Jekyll validation (`scripts/blog_qa_agent.py`)
- **Defect Tracker**: Tracks bugs with RCA (`scripts/defect_tracker.py`)
- **Defect Prevention**: Uses learned patterns to prevent bugs (`scripts/defect_prevention_rules.py`)

---

**Last Updated**: 2026-01-05
**Status**: ✅ Fully operational and tested
