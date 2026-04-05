# Observability Skill

## Purpose
Track article quality metrics over time so degradation is detected early
and improvement is measurable.  The observability pipeline reads from
evaluation logs and produces a dashboard JSON updated after each pipeline run.

## Metrics to Track

### 1. Article Pass Rate
- Percentage of articles that publish on first attempt (no revision)
- Percentage that publish after revision
- Percentage that fail completely (needs_revision after max retries)
- Tracked per week and as rolling 4-week average

### 2. Common Failure Modes
- Count of each failure type (missing frontmatter, banned phrases, unsourced stats, etc.)
- Top 3 failure modes per week
- Trend: are specific failures increasing or decreasing?

### 3. Quality Score Trends
- Average total eval score per week (from `logs/article_evals.json`)
- Average per-dimension scores (opening, evidence, voice, structure, engagement)
- Min/max scores per week
- Trend direction: improving, stable, or degrading

### 4. Revision Loop Frequency
- Average retries per article
- Percentage of articles needing 0, 1, or 2 revisions
- What triggers revisions most (gate failures, validation failures, or both)

## Data Sources

- `logs/article_evals.json` — per-article evaluation scores (Story #116)
- `logs/pipeline_runs.json` — pipeline execution metadata (to be created)
- GitHub Issues labeled `editorial-judge` — post-deployment failures

## Dashboard Schema

Output to `logs/quality_dashboard.json`:

```json
{
  "generated_at": "2026-04-04T12:00:00Z",
  "summary": {
    "total_articles": 15,
    "first_attempt_publish_rate": 0.80,
    "overall_publish_rate": 0.93,
    "avg_eval_score": 43.2,
    "avg_eval_percentage": 86.4
  },
  "weekly_trends": [
    {
      "week": "2026-W14",
      "articles_generated": 3,
      "published": 3,
      "failed": 0,
      "avg_score": 44.0,
      "avg_retries": 0.33,
      "top_failure_modes": []
    }
  ],
  "dimension_trends": {
    "opening_quality": [8.0, 8.5, 9.0],
    "evidence_sourcing": [7.0, 8.0, 8.5],
    "voice_consistency": [9.5, 9.5, 10.0],
    "structure": [8.0, 9.0, 9.0],
    "visual_engagement": [6.0, 7.0, 7.5]
  },
  "failure_mode_counts": {
    "missing_references": 3,
    "banned_phrases": 2,
    "missing_layout": 1,
    "image_not_found": 1
  },
  "alerts": [
    {
      "type": "degradation",
      "dimension": "visual_engagement",
      "message": "Visual engagement scores dropped 20% over 3 weeks",
      "severity": "warn"
    }
  ]
}
```

## Alert Thresholds

| Metric | Warn | Critical |
|--------|------|----------|
| First-attempt publish rate | <70% | <50% |
| Avg eval score | <35/50 | <25/50 |
| Any dimension avg | <6/10 | <4/10 |
| Same failure mode 3+ times in a row | warn | critical if 5+ |

## Integration Points

- Run after each pipeline execution in `content-pipeline.yml`
- Reads from `logs/article_evals.json` (Story #116 output)
- Alerts create GitHub issues on economist-agents
- Dashboard JSON can be rendered by any frontend (future)

## Existing Code to Reuse

- `scripts/quality_dashboard.py` — existing quality scoring (code metrics, not article metrics)
- `skills/quality_history.json` — historical quality scores (infrastructure, not content)
- `scripts/defect_tracker.py` — defect logging patterns

## Design Principles

- All metrics are deterministic — derived from evaluation logs, not LLM
- Dashboard is append-only — never delete historical data
- Use `orjson` for serialization
- File-based storage (JSON) — no database dependency
- Fail gracefully if log files don't exist yet (empty dashboard)
