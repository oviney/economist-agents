# Spec: Visual QA Metrics Tracking

## Objective
Implement the ready backlog item "Visual QA Metrics Tracking" from `.github/BACKLOG.md`.
The system should persist chart quality metrics in the skills-state area, expose
Visual QA as a blog QA skill category, and make recurring chart failures visible
without requiring manual inspection of every chart run.

## Tech Stack
- Python 3.13 runtime used by the local test environment.
- `src/quality/chart_metrics.py` for chart quality metrics.
- `scripts/skills_manager.py` and `data/skills_state/blog_qa_skills.json` for
  skills-system persistence.
- `pytest`, `ruff` for verification.

## Commands
- Targeted tests:
  `.venv/bin/python -m pytest tests/test_chart_metrics.py tests/test_validate_skills.py -q`
- Lint:
  `ruff check src/quality/chart_metrics.py scripts/skills_manager.py tests/test_chart_metrics.py`
- Format check:
  `ruff format --check src/quality/chart_metrics.py scripts/skills_manager.py tests/test_chart_metrics.py`

## Project Structure
- `src/quality/chart_metrics.py` contains the chart metrics collector and report export.
- `scripts/skills_manager.py` contains skills database helpers used by agent roles.
- `data/skills_state/blog_qa_skills.json` contains persisted blog QA skill categories.
- `tests/test_chart_metrics.py` covers metric calculations, persistence, and reporting.

## Code Style
Use small, explicit helpers over a new abstraction layer:

```python
def get_improvement_trend(self, window: int = 5) -> dict[str, Any]:
    sessions = self.metrics.get("sessions", [])[-window:]
    pass_rates = [...]
    return {"direction": "improving", "pass_rates": pass_rates}
```

Keep JSON schemas backward-compatible by adding optional fields rather than
renaming existing keys.

## Testing Strategy
- Add tests that fail before implementation for:
  - default metrics path uses `data/skills_state/chart_metrics.json`
  - top-three failure export exists
  - Visual QA pass-rate trend is computed from sessions
  - blog QA skills include a `visual_qa_metrics` category
- Reuse existing isolated `tmp_path` collector tests for deterministic file I/O.

## Boundaries
- Always: Keep chart metrics deterministic and offline.
- Always: Preserve existing `ChartMetricsCollector` public methods.
- Ask first: Removing or rewriting legacy skills data.
- Never: Add live API calls, secrets, or LLM dependency to metrics tracking.

## Success Criteria
- `ChartMetricsCollector()` defaults to `data/skills_state/chart_metrics.json`.
- Metrics summary reports chart count, Visual QA pass rate, common failures, and trend.
- Blog QA skills file includes a `visual_qa_metrics` category with patterns for pass
  rate tracking, recurring failure tracking, and trend monitoring.
- Targeted tests and lint/format checks pass locally.

## Plan
1. Add failing tests for default path, top-three failures, trend calculation, and
   skill-category presence.
2. Extend `ChartMetricsCollector` with trend/top-failure summary helpers and update
   the default path.
3. Add the Visual QA metrics category to `data/skills_state/blog_qa_skills.json`.
4. Run targeted tests and quality checks.

## Open Questions
- `docs/BACKLOG.md` does not exist in the current repository. This spec uses
  `.github/BACKLOG.md` as the authoritative backlog source for this task.
