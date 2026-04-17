---
name: agent-traceability
description: Log every agent's inputs, outputs, and decisions as structured JSON for end-to-end auditing. Use when adding trace logging to a pipeline stage, when diagnosing a failed article, when the editorial judge needs pipeline context in a GitHub issue.
---

# Agent Traceability

## Overview

Produces structured trace records for every pipeline stage so any article can be audited end-to-end. When the editorial judge creates a GitHub issue, trace data provides the diagnostic context.

## When to Use

- Adding a new pipeline stage that needs trace logging
- Diagnosing why a specific article failed or scored low
- Including pipeline context in editorial judge GitHub issues
- Analyzing stage durations for performance optimization

### When NOT to Use

- For article quality scoring — that's `article-evaluation`
- For quality trend analysis — that's `observability`
- For defect pattern codification — that's `defect-prevention`
- For logging API keys, article full text, or sensitive data (never log these)

## Core Process

```
1. Pipeline stage begins
   ↓
2. Record inputs (topic, focus_area, config — never full article text)
   ↓
3. Execute stage logic
   ↓
4. Record outputs (scores, counts, decisions) and duration_ms
   ↓
5. Buffer trace record in memory
   ↓
6. After all stages complete → flush all records to logs/pipeline_traces.json
   ↓
7. If editorial judge creates issue → include trace summary table in body
```

### Per-Stage Trace Matrix

| Stage | Agent | Key Inputs | Key Outputs | Key Decisions |
|-------|-------|-----------|-------------|---------------|
| Topic Discovery | Topic Scout | focus_area | topic count, top topic | — |
| Editorial Review | Editorial Board | topics | top_pick, consensus, votes | Winner, dissents |
| Content Generation | Stage3Crew | topic | word count, chart_data | — |
| Quality Gate | Stage4Crew | article | editorial_score, gates_passed | publish vs revision |
| Schema Validation | FrontmatterSchema | article | is_valid, errors | — |
| Publication Validator | PublicationValidator | article | is_valid, issues | — |
| Editorial Judge | EditorialJudge | deployed article | check results | pass/warn/fail |

### Trace Record Schema

```json
{
  "trace_id": "uuid",
  "pipeline_run_id": "uuid",
  "stage": "topic_discovery",
  "agent": "topic_scout",
  "timestamp": "2026-04-04T12:00:00Z",
  "inputs": { "focus_area": null },
  "outputs": { "topic_count": 5, "top_topic": "AI Testing Paradox" },
  "decisions": {},
  "duration_ms": 4500,
  "status": "success"
}
```

### Implementation

For v1, add trace logging directly in `flow.py` using a simple helper:

```python
def _log_trace(self, stage: str, agent: str, inputs: dict, outputs: dict,
               decisions: dict = None, duration_ms: int = 0) -> None:
    """Append a trace record to logs/pipeline_traces.json."""
```

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "We can debug from the logs" | Unstructured logs require manual correlation; structured traces give instant stage-by-stage audit |
| "Tracing adds too much overhead" | Performance budget is <50ms/stage — JSON serialization is negligible |
| "We'll add tracing later when we need it" | You need it the first time a deployed article fails and you can't explain why |
| "Just log everything" | Logging full article text wastes storage and creates privacy risk; log summaries only |

## Red Flags

- Trace records missing for any pipeline stage (gap in audit trail)
- Full article text logged in trace records (privacy/storage risk)
- Traces written per-stage instead of buffered and flushed once at end
- No `pipeline_run_id` linking stages within the same run
- Trace logging adds >50ms per stage or >250ms per pipeline run
- API keys or tokens appearing in trace inputs/outputs

## Verification

- [ ] Every pipeline stage produces a trace record — **evidence**: `logs/pipeline_traces.json` has one record per stage per run
- [ ] Records contain `pipeline_run_id` linking all stages — **evidence**: group by run_id shows complete stage sequences
- [ ] No full article text in any trace record — **evidence**: grep for common article patterns returns empty
- [ ] Flush happens once at pipeline end, not per-stage — **evidence**: single file write in flow.py
- [ ] Performance budget met (<250ms total) — **evidence**: sum of trace overhead in a test run

### Integration Points

- `src/economist_agents/flow.py` — add trace logging to each stage method
- `scripts/editorial_judge.py` — include trace summary in GitHub issues
- `logs/pipeline_traces.json` — append-only trace storage
- Observability dashboard — reads traces for duration metrics
