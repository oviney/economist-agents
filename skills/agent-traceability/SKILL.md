# Agent Traceability Skill

## Purpose
Log every agent's inputs, outputs, and decisions as structured JSON so that
any article can be audited end-to-end.  When the editorial judge creates a
GitHub issue, include the relevant agent logs for diagnosis.

## What to Log

### Per-Stage Trace Record

Each stage in the flow produces a trace record:

| Stage | Agent | Inputs | Outputs | Decisions |
|-------|-------|--------|---------|-----------|
| 1. Topic Discovery | Topic Scout | focus_area | 5 topics with scores | - |
| 2. Editorial Review | Editorial Board (6 personas) | 5 topics | top_pick, consensus, votes | Which topic won, dissenting views |
| 3. Content Generation | Stage3Crew (4 agents) | topic | article, chart_data | - |
| 4. Quality Gate | Stage4Crew Reviewer | article | editorial_score, gates_passed | publish vs revision |
| 4b. Schema Validation | FrontmatterSchema | article | is_valid, errors | - |
| 4c. Publication Validator | PublicationValidator | article | is_valid, issues | - |
| 5. Editorial Judge | EditorialJudge | deployed article | 6 check results | pass/warn/fail |

### Trace Record Schema

```json
{
  "trace_id": "uuid",
  "pipeline_run_id": "uuid",
  "stage": "topic_discovery",
  "agent": "topic_scout",
  "timestamp": "2026-04-04T12:00:00Z",
  "inputs": {
    "focus_area": null
  },
  "outputs": {
    "topic_count": 5,
    "top_topic": "AI Testing Paradox",
    "top_score": 9.2
  },
  "decisions": {},
  "duration_ms": 4500,
  "status": "success"
}
```

## Where to Log

### File: `logs/pipeline_traces.json`
Append-only JSON array.  Each pipeline run produces 4-6 trace records
(one per stage).  Use `orjson` for serialization.

### GitHub Issue Comments
When the editorial judge creates an issue, include a summary of the
pipeline trace in the issue body:

```markdown
## Pipeline Trace

| Stage | Agent | Duration | Status | Key Output |
|-------|-------|----------|--------|------------|
| Topic Discovery | topic_scout | 4.5s | success | 5 topics |
| Editorial Review | editorial_board | 8.2s | success | "AI Testing" (8.3/10) |
| Content Generation | stage3_crew | 45.1s | success | 1138 words |
| Quality Gate | stage4_reviewer | 12.3s | success | 98/100, 5/5 gates |
| Publication Validator | pub_validator | 0.1s | success | valid |
| Editorial Judge | editorial_judge | 3.2s | fail | image not found |
```

## Implementation

### Tracing Decorator
Create a `@trace` decorator or context manager that wraps each flow stage:

```python
from scripts.trace_logger import TraceLogger

logger = TraceLogger(run_id="uuid")

with logger.trace("topic_discovery", agent="topic_scout") as t:
    t.log_input("focus_area", None)
    topics = scout_topics(client)
    t.log_output("topic_count", len(topics))
    t.log_output("top_topic", topics[0]["topic"])
```

### Lightweight Approach (Recommended for v1)
Don't over-engineer.  For v1, add trace logging directly in `flow.py`
methods using a simple helper:

```python
def _log_trace(self, stage: str, agent: str, inputs: dict, outputs: dict,
               decisions: dict = None, duration_ms: int = 0) -> None:
    """Append a trace record to logs/pipeline_traces.json."""
    ...
```

## Existing Patterns to Follow

- `scripts/defect_tracker.py` — structured JSON logging with timestamps
- `src/telemetry/roi_tracker.py` — per-session logging to JSON files
- `scripts/editorial_judge.py` — GitHub issue creation with structured body

## Privacy and Security

- Never log article full text in traces (too large, may contain sensitive data)
- Log summaries: word count, title, score — not content
- Never log API keys or tokens
- Trace files should be gitignored (runtime data, not source)

## Integration Points

- `src/economist_agents/flow.py` — add trace logging to each stage method
- `scripts/editorial_judge.py` — include trace summary in GitHub issues
- `logs/pipeline_traces.json` — append-only trace storage
- Observability dashboard (Story #119) — reads traces for duration metrics

## Performance Budget

- Trace logging must add <50ms per stage (<250ms total per pipeline run)
- Use buffered writes — flush once at end of pipeline, not per stage
- File I/O only, no network calls for tracing
