# Governance & Human Review System - Quick Start

## What's New

The economist-agents pipeline now includes **governance and human review** features:

✅ **Visibility**: All agent outputs saved for inspection
✅ **Control**: Approval gates between pipeline stages
✅ **Auditability**: Complete decision logs and reports
✅ **Collaboration**: Review and edit agent outputs before proceeding

## Usage

### Non-Interactive Mode (Default)
Fully automated - agents run without human intervention:
```bash
.venv/bin/python scripts/economist_agent.py
```

### Interactive Mode (New!)
Human approval required between stages:
```bash
.venv/bin/python scripts/economist_agent.py --interactive
```

## Interactive Mode Features

### 1. Approval Gates
After each major stage, you'll be prompted:

```
🚦 APPROVAL GATE: Research Complete
══════════════════════════════════════════════════════════

Research agent gathered 4 data points (4 verified)

Details:
  • Unverified claims: 2
  • Has chart data: True
  • Review file: output/governance/20260101_123456/research_agent.json

📄 Review file: output/governance/20260101_123456/research_agent.json

Approve and continue? [Y/n/skip-all]:
```

**Options:**
- `Y` or `Enter` - Approve and continue
- `n` - Reject and stop pipeline
- `skip-all` - Skip remaining approval gates (continue automatically)

### 2. Saved Outputs
Every agent's output is saved as JSON:

```
output/governance/
└── 20260101_123456/          # Session ID (timestamp)
    ├── research_agent.json   # Research findings
    ├── graphics_agent.json   # Chart data & QA results
    ├── writer_agent.json     # Draft article
    ├── editor_agent.json     # Edited version
    ├── decisions.jsonl       # All approvals/rejections
    └── governance_report.md  # Human-readable summary
```

### 3. Governance Report
Auto-generated summary of the entire session:

```markdown
# Governance Report
**Session**: 20260101_123456
**Generated**: 2026-01-01 12:35:00

## Agent Outputs
### Research Agent
- Timestamp: 2026-01-01T12:34:56
- Data points: 4
- Verified: 4
- Unverified: 2

## Decisions
### Research Complete
- Status: ✅ Approved
- Time: 2026-01-01T12:35:00
```

## Example Workflow

### Automated (Default)
```bash
# Generate article - no human intervention
.venv/bin/python scripts/economist_agent.py

# Output
output/
├── 2026-01-01-article-title.md
└── charts/
    └── article-title.png
```

### Interactive (With Review)
```bash
# Enable interactive mode
.venv/bin/python scripts/economist_agent.py --interactive

# Session starts
🎯 GENERATING: Self-Healing Tests: Myth vs Reality
🚦 INTERACTIVE MODE: Approval gates enabled
📋 Governance tracking enabled: output/governance/20260101_123456

# Agent 1: Research
📊 Research Agent: Gathering verified data...
   ✓ Found 4 data points (4 verified)
   ⚠ 2 unverified claims flagged
   📁 Saved research_agent output

# Gate 1: Review research
🚦 APPROVAL GATE: Research Complete
Research agent gathered 4 data points (4 verified)
Approve and continue? [Y/n/skip-all]: Y

# Agent 2: Graphics
📈 Graphics Agent: Creating visualization...
   ✓ Chart saved
   📁 Saved graphics_agent output

# Agent 3: Writer
✍️  Writer Agent: Drafting article...
   ✓ Draft complete (850 words)
   📁 Saved writer_agent output

# Gate 2: Review draft
🚦 APPROVAL GATE: Draft Complete
Writer agent produced 850-word draft
Preview: Self-healing tests, hailed as a significant...
Approve and continue? [Y/n/skip-all]: Y

# Agent 4: Editor
📝 Editor Agent: Reviewing draft...
   Quality gates: 5 passed, 0 failed
   📁 Saved editor_agent output

# Complete
✅ COMPLETE
📊 Governance report: output/governance/20260101_123456/governance_report.md
```

## Custom Governance Directory

```bash
.venv/bin/python scripts/economist_agent.py \
  --interactive \
  --governance-dir /path/to/audit/logs
```

## Reviewing Saved Outputs

Each agent's JSON file contains:
- **agent**: Agent name
- **timestamp**: When it ran
- **output**: Complete agent output (draft, data, etc.)
- **metadata**: Summary stats (word count, data points, etc.)

```bash
# View research results
cat output/governance/*/research_agent.json | jq

# View draft article
cat output/governance/*/writer_agent.json | jq .output.draft

# View all decisions
cat output/governance/*/decisions.jsonl
```

## Integration with GitHub Actions

For CI/CD, use non-interactive mode:

```yaml
- name: Generate Article
  run: .venv/bin/python scripts/economist_agent.py
  # No --interactive flag = fully automated
```

For manual review workflows:

```yaml
- name: Generate Article (Manual Review)
  run: .venv/bin/python scripts/economist_agent.py --interactive
  # Requires approval for each stage
```

## Benefits

### For Solo Developers
- **Catch issues early**: Review research before expensive writing
- **Quality control**: Approve/reject at each stage
- **Learn from agents**: See their reasoning in saved outputs
- **Audit trail**: Track what worked and what didn't

### For Teams
- **Collaboration**: Multiple people can review saved outputs
- **Governance**: Complete audit trail for compliance
- **Knowledge sharing**: Review files document agent decisions
- **Improvement**: Analyze governance reports to refine prompts

## Tips

1. **First run**: Use `--interactive` to understand what each agent does
2. **Production**: Use default (non-interactive) for automated generation
3. **Debugging**: Check saved JSON files when quality is low
4. **Iteration**: Use `skip-all` after first approval to speed up testing

## Commands Cheat Sheet

```bash
# Automated (no human input)
.venv/bin/python scripts/economist_agent.py

# Interactive (approval gates)
.venv/bin/python scripts/economist_agent.py --interactive

# Custom governance location
.venv/bin/python scripts/economist_agent.py -i --governance-dir ./audit

# Show help
.venv/bin/python scripts/economist_agent.py --help

# Custom topic with interactive mode
export TOPIC="The Rise of AI in Testing"
.venv/bin/python scripts/economist_agent.py --interactive
```

## What Gets Saved

| File | Contents |
|------|----------|
| `research_agent.json` | Data points, sources, verification status |
| `graphics_agent.json` | Chart path, visual QA results |
| `writer_agent.json` | Draft article, word count |
| `editor_agent.json` | Edited article, quality gates |
| `decisions.jsonl` | Approval/rejection log (one per line) |
| `governance_report.md` | Human-readable summary |

## Next Steps

1. **Try interactive mode**: See what each agent produces
2. **Review a session**: Explore `output/governance/*/` files
3. **Customize prompts**: Use governance data to improve agent behavior
4. **Build dashboards**: Parse JSON files for analytics

---

**Documentation**: See [governance.py](scripts/governance.py) for implementation details.
