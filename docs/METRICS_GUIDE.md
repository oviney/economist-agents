# Metrics Guide - Agent Performance Tracking

This guide explains how to use the metrics tracking system to monitor agent performance over time.

## Overview

The Economist Agents system now tracks:
1. **Quality Scores** - Overall article quality trends over time
2. **Agent Performance** - Per-agent metrics (Research, Writer, Editor, Graphics)
3. **Prediction Accuracy** - How well each agent meets its goals

All metrics are stored in `skills/` directory:
- `skills/quality_history.json` - Historical quality scores
- `skills/agent_metrics.json` - Agent performance data

## Quick Start

### View Metrics Dashboard

```bash
# Show all metrics (quality trend + agent summary + prediction accuracy)
python3 scripts/metrics_dashboard.py

# Show only quality trend
python3 scripts/metrics_dashboard.py --trend

# Show specific agent details
python3 scripts/metrics_dashboard.py --agent writer_agent

# Show prediction accuracy summary
python3 scripts/metrics_dashboard.py --accuracy

# Export report to markdown
python3 scripts/metrics_dashboard.py --export metrics_report.md
```

### Generate Article with Metrics

Metrics are automatically collected when you generate an article:

```bash
export TOPIC="The Economics of Flaky Tests"
export TALKING_POINTS="cost analysis, maintenance burden, developer productivity"

python3 scripts/economist_agent.py
```

After generation, view the accumulated metrics:

```bash
python3 scripts/metrics_dashboard.py
```

---

## Dashboard Output Examples

### Quality Trend View

```
QUALITY SCORE TREND (Last 10 runs)

2025-12-02 │ 91/100 (A-) │ █████████████████████████████████████████████
2025-12-07 │ 93/100 (A)  │ ██████████████████████████████████████████████
2025-12-12 │ 95/100 (A)  │ ███████████████████████████████████████████████
2025-12-17 │ 97/100 (A+) │ ████████████████████████████████████████████████
2025-12-22 │ 98/100 (A+) │ █████████████████████████████████████████████████
2025-12-27 │ 99/100 (A+) │ █████████████████████████████████████████████████

📈 Trend: improving ⬆️ (+8.0 points from first to most recent)
```

**Interpreting the trend:**
- ⬆️ improving - Quality increasing over time (good!)
- ➡️ stable - Quality consistent
- ⬇️ declining - Quality decreasing (investigate!)

---

### Agent Performance Summary

```
AGENT PERFORMANCE SUMMARY

Research Agent
  ✓ Avg verification rate: 84.7%
  ✓ Avg data points: 12.3
  ✓ Trend: improving ⬆️

Writer Agent
  ⚠ Clean draft rate: 66.7%
  ⚠ Avg regenerations: 0.3
  ⚠ Trend: stable ➡️

Editor Agent
  ✓ Gate pass rate: 100.0%
  ✓ Avg gates passed: 5.0/5
  ✓ Trend: improving ⬆️

Graphics Agent
  ✓ Visual QA pass rate: 83.3%
  ✓ Avg zone violations: 0.2
  ✓ Trend: stable ➡️
```

**What to monitor:**
- **Research Agent**: Verification rate should be >80%
- **Writer Agent**: Clean draft rate >70% ideal
- **Editor Agent**: Gate pass rate should be 100%
- **Graphics Agent**: Visual QA pass rate >80%

---

### Prediction Accuracy

```
PREDICTION ACCURACY

Agent            │ Accuracy │ Predictions
─────────────────┼──────────┼─────────────
Research Agent   │   66.7%  │ 4/6 correct
Writer Agent     │   66.7%  │ 4/6 correct
Editor Agent     │   33.3%  │ 2/6 correct ⚠️
Graphics Agent   │   83.3%  │ 5/6 correct
```

**What this means:**
- Each agent makes a prediction about its output (e.g., "Clean draft, 0 banned phrases")
- We track whether the actual outcome matches the prediction
- Low accuracy indicates the agent needs prompt refinement or better validation

**Red flags:**
- Accuracy <50% - Agent is overconfident or underperforming
- Editor Agent at 33.3% above - needs attention!

---

### Agent-Specific Details

```bash
python3 scripts/metrics_dashboard.py --agent writer_agent
```

Output:
```
WRITER AGENT - DETAILED METRICS
Total Runs: 6

Recent Performance:
  2025-12-02 │ ❌ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Needs improvement
  2025-12-07 │ ❌ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Needs improvement
  2025-12-12 │ ✅ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Pass
  2025-12-17 │ ✅ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Pass
  2025-12-22 │ ✅ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Pass
  2025-12-27 │ ✅ │ Predicted: Clean draft (0 banned phrases, chart embedded)
             │   │ Actual:    Pass

Summary Statistics:
  Avg Word Count: 1234
  Clean Draft Rate: 66.7%
  Avg Banned Phrases: 0.5
  Avg Regenerations: 0.3
  Chart Embedding Rate: 100.0%
```

---

## Metrics Data Format

### Quality History (`skills/quality_history.json`)

```json
{
  "version": "1.0",
  "created": "2025-12-27T10:30:00",
  "runs": [
    {
      "timestamp": "2025-12-27T10:30:00",
      "quality_score": 99,
      "grade": "A+",
      "coverage": 95,
      "pass_rate": 100,
      "documentation": 100,
      "style_score": 98.6
    }
  ],
  "trend": "improving"
}
```

### Agent Metrics (`skills/agent_metrics.json`)

```json
{
  "version": "1.0",
  "created": "2025-12-27T10:30:00",
  "runs": [
    {
      "timestamp": "2025-12-27T10:30:00",
      "agents": {
        "research_agent": {
          "data_points": 12,
          "verified": 10,
          "unverified": 2,
          "verification_rate": 83.3,
          "prediction": "High verification rate (>80%)",
          "actual": "Pass"
        },
        "writer_agent": {
          "word_count": 1234,
          "banned_phrases": 0,
          "validation_passed": true,
          "regenerations": 0,
          "chart_embedded": true,
          "prediction": "Clean draft (0 banned phrases, chart embedded)",
          "actual": "Pass"
        }
      }
    }
  ]
}
```

---

## Automated Metrics Collection

Metrics are automatically collected during article generation:

### 1. Research Agent
- **Tracked**: data points, verified count, unverified count
- **Calculated**: verification rate
- **Prediction**: "High verification rate (>80%)"
- **Pass Criteria**: verification_rate >= 80%

### 2. Writer Agent
- **Tracked**: word count, banned phrases, regenerations, chart embedding
- **Calculated**: clean draft rate
- **Prediction**: "Clean draft (0 banned phrases, chart embedded)"
- **Pass Criteria**: banned_phrases == 0 AND chart_embedded == true

### 3. Editor Agent
- **Tracked**: gates passed, gates failed, edits made
- **Calculated**: gate pass rate
- **Prediction**: "All gates pass (5/5)"
- **Pass Criteria**: gates_failed == 0

### 4. Graphics Agent
- **Tracked**: charts generated, visual QA passed, zone violations
- **Calculated**: visual QA pass rate
- **Prediction**: "Pass Visual QA (100%)"
- **Pass Criteria**: zone_violations == 0

---

## Using Metrics for Continuous Improvement

### 1. Identify Underperforming Agents

If prediction accuracy is low (<60%):
- Review agent's system prompt
- Check validation criteria
- Look at specific failure patterns

Example:
```bash
# Editor Agent at 33.3% accuracy
python3 scripts/metrics_dashboard.py --agent editor_agent

# Shows: Editor predicts "All gates pass" but 2/6 runs failed
# Action: Review editor prompt for overly optimistic predictions
```

### 2. Track Quality Improvements

After prompt changes:
```bash
# Before prompt change
python3 scripts/metrics_dashboard.py --trend
# Quality: 91 → 93 → 95 (improving)

# After prompt change
python3 scripts/economist_agent.py  # Generate article
python3 scripts/metrics_dashboard.py --trend
# Quality: 91 → 93 → 95 → 97 → 99 (accelerated improvement!)
```

### 3. Monitor Agent Stability

Look for sudden drops:
```bash
python3 scripts/metrics_dashboard.py

# If you see:
# Writer Agent: 80% → 80% → 40% ⬇️ (sudden drop)
# Investigate recent changes to Writer Agent prompt
```

### 4. Set Quality Baselines

Use historical data to set expectations:
```bash
# Research Agent should maintain >80% verification
# Writer Agent should maintain >70% clean draft rate
# Editor Agent should maintain 100% gate pass rate
# Graphics Agent should maintain >80% QA pass rate
```

---

## Troubleshooting

### Metrics not appearing

**Problem**: Dashboard shows "No data found"

**Solution**:
1. Check `skills/agent_metrics.json` exists
2. Generate at least one article: `python3 scripts/economist_agent.py`
3. Verify metrics are saved: `cat skills/agent_metrics.json | jq .`

### Metrics file corrupted

**Problem**: JSON parse error when loading metrics

**Solution**:
```bash
# Backup existing file
cp skills/agent_metrics.json skills/agent_metrics.json.bak

# Validate JSON
cat skills/agent_metrics.json | jq .

# If invalid, restore backup or regenerate
python3 scripts/generate_sample_metrics.py
```

### Agent metrics missing

**Problem**: Some agents show no data

**Solution**:
- Metrics only collected during full article generation
- Standalone agent calls don't trigger metrics
- Ensure you're calling `generate_economist_post()` function

---

## Integration with CI/CD

Add metrics checks to your pipeline:

```yaml
# .github/workflows/quality-gate.yml
- name: Check Quality Trend
  run: |
    python3 scripts/metrics_dashboard.py --trend > trend.txt
    if grep -q "declining" trend.txt; then
      echo "❌ Quality declining!"
      exit 1
    fi

- name: Check Agent Performance
  run: |
    python3 scripts/metrics_dashboard.py --accuracy > accuracy.txt
    # Fail if any agent <50% accuracy
    if grep -E "[0-9]{1}\.[0-9]%" accuracy.txt | grep -vE "[5-9][0-9]\.[0-9]%"; then
      echo "❌ Agent accuracy too low!"
      exit 1
    fi
```

---

## Best Practices

1. **Review metrics after each sprint**
   - Look for trends
   - Identify agents needing attention
   - Celebrate improvements!

2. **Set quality gates**
   - Minimum verification rate: 80%
   - Minimum clean draft rate: 70%
   - Gate pass rate: 100%
   - Visual QA pass rate: 80%

3. **Export reports for retrospectives**
   ```bash
   python3 scripts/metrics_dashboard.py --export sprint_4_metrics.md
   ```

4. **Track prompt changes with metrics**
   - Note when you change agent prompts
   - Compare before/after metrics
   - Document successful improvements

5. **Don't over-optimize**
   - Focus on agents with <60% prediction accuracy
   - Ignore minor fluctuations (±5%)
   - Quality >95 is excellent, don't chase 100%

---

## Related Documentation

- [Sprint 4 Retrospective](SPRINT_4_RETROSPECTIVE.md) - How metrics were built
- [Agent Metrics API](../scripts/agent_metrics.py) - Technical implementation
- [Quality Calculator](../scripts/calculate_quality_score.py) - Quality score formula
- [Dashboard Tool](../scripts/metrics_dashboard.py) - Visualization code

---

**Last Updated**: 2026-01-01  
**Version**: 1.0  
**Maintainer**: Economist Agents Team
