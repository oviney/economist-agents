---
name: observability
description: Track article quality metrics over time and alert on degradation. Use when adding a new metric to the quality dashboard, when investigating a quality trend, when configuring alert thresholds.
---

# Observability

## Overview

Reads from evaluation logs and produces a dashboard JSON after each pipeline run. Tracks article pass rates, failure modes, quality scores, and revision frequency so degradation is detected early and improvement is measurable.

## When to Use

- After each pipeline run to update the quality dashboard
- When investigating why article quality has changed over time
- When adding a new tracked metric or alert threshold
- When the editorial judge flags a recurring failure pattern

### When NOT to Use

- For infrastructure/code quality metrics — that's `scripts/quality_dashboard.py`
- For individual article scoring — that's `article-evaluation`
- For defect root-cause analysis — that's `defect-prevention`

## Core Process

```
1. Pipeline run completes (success or failure)
   ↓
2. Read evaluation logs from logs/article_evals.json
   ↓
3. Compute weekly aggregates: pass rate, failure modes, dimension scores
   ↓
4. Append to logs/quality_dashboard.json
   ↓
5. Check alert thresholds
   ↓
6. If threshold breached → create GitHub issue with severity
```

### Metrics Tracked

| Category | Metrics |
|----------|---------|
| Article pass rate | First-attempt publish %, publish-after-revision %, total fail % |
| Failure modes | Count per type, top 3 per week, trend direction |
| Quality scores | Avg total per week, per-dimension averages, min/max |
| Revision loops | Avg retries per article, distribution (0/1/2 revisions) |

### Alert Thresholds

| Metric | Warn | Critical |
|--------|------|----------|
| First-attempt publish rate | <70% | <50% |
| Avg eval score | <35/50 | <25/50 |
| Any dimension avg | <6/10 | <4/10 |
| Same failure mode 3+ times in a row | warn | critical if 5+ |

### Dashboard Output Schema

Output to `logs/quality_dashboard.json` — append-only, never delete historical data.

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "We can eyeball quality from the articles" | Degradation is gradual — you won't notice a 5% weekly decline until it's 30% down |
| "The eval scores are good enough" | Scores without trends are snapshots; only trends reveal whether you're improving or decaying |
| "Alerts are noisy, let's remove them" | Tune thresholds, don't remove alerting — silent failures are the most expensive |
| "We'll check the dashboard when something breaks" | By then you've shipped 3 bad articles; proactive monitoring catches the first one |

## Red Flags

- Dashboard JSON not updated after a pipeline run
- Alert thresholds never triggered (too lenient) or always triggered (too strict)
- Metrics computed from LLM calls instead of deterministic log parsing
- Historical data deleted or overwritten instead of appended
- No weekly trend computation — only point-in-time snapshots

## Verification

- [ ] `logs/quality_dashboard.json` updated after each pipeline run — **evidence**: timestamp matches latest run
- [ ] Weekly aggregates computed from `logs/article_evals.json` — **evidence**: article count matches eval log entries
- [ ] Alert thresholds configured and tested with synthetic data
- [ ] Dashboard uses `orjson` for serialization, file-based storage only
- [ ] Graceful handling when log files don't exist (empty dashboard, no crash)

### Data Sources

- `logs/article_evals.json` — per-article evaluation scores
- `logs/pipeline_runs.json` — pipeline execution metadata
- GitHub Issues labeled `editorial-judge` — post-deployment failures

### Integration Points

- Runs after each pipeline execution in `content-pipeline.yml`
- Alerts create GitHub issues on economist-agents
- `scripts/quality_dashboard.py` — existing code-quality scoring (separate concern)
- `data/skills_state/quality_history.json` — historical quality scores (infrastructure)
