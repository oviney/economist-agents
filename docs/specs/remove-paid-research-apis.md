# Spec: Remove pay-per-use search APIs from the research path

## Objective

Eliminate every pay-per-use third-party search API (Serper/Google, Brave, Tavily)
from the blog's research path. The owner does not want metered external APIs for
research. After this change the pipeline researches using **free, keyless sources
only — arXiv + Semantic Scholar** — preserving the project's core promise of
"Economist-style articles with **verified sources**" (CLAUDE.md) at zero
marginal cost and with no API keys to manage.

**Success looks like:** a fresh pipeline run assembles a research brief and
reaches the publication validator using only arXiv + Semantic Scholar; no code
path references `SERPER_API_KEY`, `BRAVE_API_KEY`, or `TAVILY_API_KEY`; the suite
is green.

## Assumptions (confirm at LGTM)

1. "No pay-per-use research APIs" excludes Serper/Google, Brave, **and** Tavily,
   **and** Anthropic's built-in `web_search` server tool (it is also metered).
   The replacement is free keyless academic search: **arXiv + Semantic Scholar**
   (both already implemented in `scripts/`).
2. Comprehensive removal ("get it out"): the three paid provider modules and
   their tests are **deleted**, not just unwired.
3. Accepted tradeoff: academic-only coverage is narrower. Non-academic /
   current-events topics may return **zero sources**; the existing
   `SearchProvidersEmptyError` gate then correctly **refuses to write an
   unsourced article**. We are choosing correctness-over-coverage, not loosening
   the gate.

## Scope — three consumers of the paid providers

| # | Consumer | Path | Change |
|---|----------|------|--------|
| 1 | `src/agent_sdk/_shared.py::_run_web_searches` | deterministic research (default) | drop google/brave/tavily branches; keep arXiv + Semantic Scholar; update diagnostics dicts + docstring |
| 2 | `src/agent_sdk/tools/research_tools.py::build_search_tool` | deep research (`RESEARCH_MODE=deep`) | repoint the search tool from brave→google to arXiv + Semantic Scholar |
| 3 | `scripts/topic_trend_grounding.py` (via `scripts/topic_scout.py`) | topic selection | remove the Serper-backed trend-grounding call; topic scout proceeds without paid web grounding |

## Files to change / delete

**Edit**
- `src/agent_sdk/_shared.py` — remove google/brave/tavily fan-out, `provider_failed`/`source_counts` keys, and docstring mentions.
- `src/agent_sdk/tools/research_tools.py` — repoint `build_search_tool` to free providers.
- `scripts/topic_trend_grounding.py` — drop the `google_search` dependency (remove the grounding step, or no-op it).
- `src/economist_agents/flow.py`, `src/agent_sdk/pipeline.py` — replace user-facing error strings that name `SERPER_API_KEY` with free-provider wording.
- `.env`, `.env.example` (if present) — remove `SERPER_API_KEY`, `BRAVE_API_KEY`, `TAVILY_API_KEY`.
- `CLAUDE.md` — update the "Research: Deterministic web search (arXiv + Google Scholar via Serper)" line and the `SERPER_API_KEY` env-var row.

**Delete**
- `scripts/google_search.py`, `scripts/brave_search.py`, `scripts/tavily_search.py`
- `tests/test_google_search.py`, `tests/test_brave_search.py`, `tests/test_tavily_search.py`
- `tests/test_topic_trend_grounding.py` only if topic-trend grounding is removed wholesale (else update it).

**Keep (unchanged)**
- `scripts/arxiv_search.py`, `scripts/semantic_scholar_search.py` — the free backbone.
- The empty-brief safety gate (`SearchProvidersEmptyError` / `SearchProvidersFailedError`).

**Out of scope / flag**
- The `web-researcher` MCP server (`mcp__web-researcher__*`) may expose paid
  providers independently — note for a follow-up; not part of the article
  pipeline.
- `scripts/archived/web_research.py` — archived; leave as-is.

## Tech Stack

Python 3.x, `pytest`. No new dependencies (removes reliance on three paid keys).

## Commands

```
Test (suite):  pytest -q
Test (research): pytest tests/test_empty_research_guard.py tests/test_stage3_hybrid_research.py -q
Lint:          ruff check src/agent_sdk/_shared.py src/agent_sdk/tools/research_tools.py scripts/topic_trend_grounding.py
Grep gate:     ! grep -rn "SERPER_API_KEY\|BRAVE_API_KEY\|TAVILY_API_KEY" src/ scripts/ --include='*.py'  # expect no hits (archived/ excluded)
```

## Project Structure

```
src/agent_sdk/_shared.py            → deterministic research fan-out (edit)
src/agent_sdk/tools/research_tools.py → deep research search tool (edit)
scripts/topic_trend_grounding.py    → topic-trend grounding (edit)
scripts/arxiv_search.py             → free provider (keep)
scripts/semantic_scholar_search.py  → free provider (keep)
scripts/{google,brave,tavily}_search.py → DELETE
tests/test_{google,brave,tavily}_search.py → DELETE
```

## Code Style

`_run_web_searches` after the change keeps only the two free branches:

```python
source_counts = {"arxiv": 0, "semantic_scholar": 0}
provider_failed = {"arxiv": False, "semantic_scholar": False}
# arXiv branch … Semantic Scholar branch … (google/brave/tavily branches deleted)
```

Type hints + docstrings mandatory; `logger` not `print()`; `orjson` per repo standards.

## Testing Strategy

`pytest`. TDD/regression-first:
1. Update `tests/test_empty_research_guard.py` and any research test that asserts
   on the 5-provider `provider_failed`/`source_counts` shape to the 2-provider
   shape (RED → GREEN).
2. Delete the three paid-provider test modules.
3. Add/confirm a test that `_run_web_searches` assembles a brief from arXiv +
   Semantic Scholar alone (mock both clients) and never references the deleted
   modules.
4. Full suite green; the grep gate above returns no hits.

## Boundaries

- **Always:** keep the empty-brief safety gate; mock provider HTTP in tests;
  preserve "verified sources" (real citations only).
- **Ask first:** loosening the zero-source refusal; adding any new external
  search provider (free or paid); changing topic-scout behaviour beyond removing
  the paid grounding call.
- **Never:** re-introduce a paid/metered search API; let the writer invent
  sources to compensate for thinner research.

## Success Criteria

1. `grep -rn "SERPER_API_KEY\|BRAVE_API_KEY\|TAVILY_API_KEY" src/ scripts/`
   (excluding `archived/`) returns **no hits**.
2. `scripts/{google,brave,tavily}_search.py` and their tests are gone; nothing
   imports them.
3. Full `pytest` suite passes; ruff clean.
4. A pipeline run on an academic-friendly topic (e.g. an arXiv-covered subject)
   assembles a brief from arXiv + Semantic Scholar and reaches the publication
   validator — **no paid key set**.

## Open Questions

1. **Topic-trend grounding:** remove the Serper step entirely (simplest), or
   repoint topic scout to a free academic-trend signal? Recommendation: remove
   the paid step now; revisit a free trend signal separately.
2. Should `.env.example` / docs gain a note that research is now academic-only
   so future contributors don't re-add a paid key? Recommendation: yes (one line).
