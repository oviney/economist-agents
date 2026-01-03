# Sprint Status Tool Documentation

## Overview

The Sprint Status Tool (`scripts/sprint_status.py`) provides real-time sprint progress reports answering the question: **"Where are we in the sprint right now?"**

This tool is part of the Scrum Master's toolkit for transparent sprint tracking and stakeholder communication.

## Features

### Core Capabilities

1. **Progress Metrics**
   - Points completed vs total
   - Completion percentage
   - Days elapsed vs sprint duration
   - Current velocity (points/day)
   - Pace variance (ahead/behind schedule)

2. **Story Breakdown**
   - Stories by status (complete, in progress, ready, not started, blocked)
   - Points distribution
   - Detailed notes (with `--detailed` flag)

3. **Risk Assessment**
   - Pace risks (behind schedule)
   - Completion risks (velocity insufficient)
   - Automatic mitigation recommendations

4. **Recommendations**
   - Actionable next steps
   - Parallel execution opportunities
   - Scope adjustment suggestions

5. **Export Options**
   - Console output (formatted)
   - Markdown export for documentation

## Usage

### Basic Status Report

```bash
python3 scripts/sprint_status.py
```

**Output:**
```
================================================================================
SPRINT 9 STATUS REPORT
================================================================================

📊 EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Status: 🟢 ON TRACK
Progress: 11/14 points (78.6%)
Day: 2/7
Velocity: 5.5 points/day
Pace: +50.0% vs expected

📋 STORY BREAKDOWN
--------------------------------------------------------------------------------
✅ COMPLETE: 6 stories (11 points)
⏸️ NOT_STARTED: 2 stories (3 points)

💡 RECOMMENDATIONS
--------------------------------------------------------------------------------
  🎯 Ahead of pace - maintain quality, consider stretch goals
  📊 Mid-sprint - continue steady pace
```

### Detailed Story Information

```bash
python3 scripts/sprint_status.py --detailed
```

Shows individual story details with completion notes.

### Export to Markdown

```bash
python3 scripts/sprint_status.py --export-markdown
```

Creates `SPRINT_N_STATUS.md` with formatted report.

### Custom Output File

```bash
python3 scripts/sprint_status.py --export-markdown --output reports/sprint_9.md
```

### Specific Sprint

```bash
python3 scripts/sprint_status.py --sprint 8 --detailed
```

## Data Source

Reads from `skills/sprint_tracker.json` which contains:
- Sprint metadata (start date, capacity, objectives)
- Story details (id, name, points, status, notes)
- Historical data for velocity calculations

## Status Indicators

### Sprint Status

- 🟢 **ON TRACK**: Pace variance ≥ -5%
- 🟡 **CAUTION**: Pace variance -15% to -5%
- 🔴 **AT RISK**: Pace variance < -15%

### Story Status

- ✅ **COMPLETE**: Story delivered and accepted
- 🔄 **IN PROGRESS**: Active development
- 🟢 **READY**: Ready to start (DoR met)
- ⏸️ **NOT STARTED**: Planned but not begun
- 🚫 **BLOCKED**: Dependencies not met

## Metrics Explained

### Pace Variance

```
Pace Variance = (Actual Completion %) - (Expected Completion %)
Expected Completion = (Days Elapsed / Sprint Duration) × 100
```

**Examples:**
- +50% = Delivering 50% faster than expected (good!)
- 0% = Perfect pace alignment
- -20% = Behind schedule by 20% (risk!)

### Velocity

```
Velocity = Completed Points / Days Elapsed
```

Used to forecast completion and assess capacity.

## Risk Assessment

### Pace Risk

| Pace Variance | Risk Level | Action |
|---------------|------------|--------|
| < -10% | HIGH | Parallel execution or scope reduction |
| -10% to -5% | MEDIUM | Monitor closely, increase velocity |
| ≥ -5% | LOW | Continue current pace |

### Completion Risk

Compares required velocity to current velocity:
- **HIGH**: Need 1.5x current velocity to complete
- **MEDIUM**: Need 1.2x current velocity
- **LOW**: Current velocity sufficient

## Integration with Scrum Master Protocol

The Sprint Status Tool integrates with the Scrum Master Protocol:

1. **Daily Standups**: Run status check before standup
2. **Mid-Sprint Reviews**: Generate markdown reports
3. **Stakeholder Updates**: Export reports for distribution
4. **Retrospectives**: Historical data for improvement

## Automation

### GitHub Actions (Future)

```yaml
name: Sprint Status Update
on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
  workflow_dispatch:

jobs:
  update-status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate Status
        run: |
          python3 scripts/sprint_status.py --export-markdown
          git add SPRINT_*_STATUS.md
          git commit -m "Update sprint status"
          git push
```

### Pre-commit Hook

```bash
#!/bin/sh
# Update sprint status before commits
python3 scripts/sprint_status.py --export-markdown --output .sprint_status.md
```

## Troubleshooting

### "No sprint data found"

**Cause**: `sprint_tracker.json` missing or corrupted

**Fix**: Restore from backup or initialize:
```bash
python3 scripts/sprint_ceremony_tracker.py --initialize
```

### "Invalid sprint number"

**Cause**: Sprint doesn't exist in tracker

**Fix**: Check current sprint with:
```bash
python3 scripts/sprint_ceremony_tracker.py --report
```

### Incorrect metrics

**Cause**: Sprint data not updated after story completion

**Fix**: Update sprint tracker:
```bash
# Update story status
python3 scripts/sprint_ceremony_tracker.py --update-story 3 --status complete
```

## Examples

### Use Case 1: Daily Standup

```bash
# Morning standup prep
python3 scripts/sprint_status.py

# Question: "Are we on track?"
# Answer: Check pace variance in output
```

### Use Case 2: Stakeholder Report

```bash
# Generate report for email
python3 scripts/sprint_status.py --export-markdown --output reports/sprint_status_$(date +%Y%m%d).md

# Attach markdown to email
```

### Use Case 3: Mid-Sprint Review

```bash
# Detailed review on Day 3-4
python3 scripts/sprint_status.py --detailed --export-markdown

# Review risks and recommendations with team
```

### Use Case 4: Historical Analysis

```bash
# Compare Sprint 8 vs Sprint 9
python3 scripts/sprint_status.py --sprint 8
python3 scripts/sprint_status.py --sprint 9

# Analyze velocity trends
```

## Future Enhancements

### Planned Features

1. **Burndown Chart Generation**
   - Daily point tracking
   - Visual burndown using matplotlib
   - Ideal vs actual burn rate

2. **Velocity Trends**
   - Sprint-over-sprint comparison
   - Moving average calculation
   - Capacity forecasting

3. **Team Metrics**
   - Individual story assignments
   - Collaboration patterns
   - Blocked time analysis

4. **Integration Enhancements**
   - Slack notifications
   - Email reports
   - GitHub Projects sync

5. **Predictive Analytics**
   - Monte Carlo simulation
   - Completion probability
   - Risk forecasting

## Related Documentation

- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [SPRINT_CEREMONY_GUIDE.md](SPRINT_CEREMONY_GUIDE.md) - Ceremony tracking
- [SPRINT.md](../SPRINT.md) - Sprint planning and history

## Version History

**v1.0** (2026-01-03)
- Initial release
- Basic metrics (progress, velocity, pace)
- Story breakdown by status
- Risk assessment
- Markdown export
- Detailed mode

**Maintained By**: Scrum Master (Autonomous)
**Review Frequency**: After each sprint
**Update Trigger**: New metrics or features requested

## Support

### Questions?

1. Check `scripts/sprint_status.py --help`
2. Review examples in this document
3. Consult [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md)
4. Ask Scrum Master: `@scrum-master sprint status help`

### Issues?

Report bugs to defect tracker:
```bash
python3 scripts/defect_tracker.py --log \
  --bug-id "BUG-XXX" \
  --component "sprint_status" \
  --description "Sprint status tool issue"
```
