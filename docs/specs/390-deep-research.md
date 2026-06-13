# Spec: Recursive Multi-Hop Deep Research (#390)

**Status:** DRAFT — awaiting human LGTM (do not implement until approved)
**Issue:** [#390](https://github.com/oviney/economist-agents/issues/390)
**Author:** Claude (spec-driven-development)
**Date:** 2026-06-13

---

## Assumptions

> Correct any of these before I proceed to PLAN. The most important is #1.

1. **Deep Research is OPT-IN, not the new default.** A `research_mode` parameter
   (`"deterministic"` default | `"deep"`) selects the path. The deterministic
   `build_research_brief` stays the default so the pipeline keeps its low cost
   (~$0.30/article) and ~5s latency; Deep Research's 5–10× cost ($1.50–3.00) and
   30–60s are paid only when explicitly requested. This directly honours the
   issue's "trade away determinism only deliberately" gate.
2. The deliverable of the research phase is unchanged: a **research-brief string**
   with the same shape `build_research_brief` returns, so the writer prompt, the
   stat audit (`audit_article_stats`), and `_build_writer_prompt` need **no**
   changes. Deep Research only produces a *richer* brief.
3. The **extractor operates on search-result snippets** in v1, not full fetched
   page bodies. Full-page fetch (heavier, more provider load) is a v2 extension
   noted in Open Questions — keeping v1's cost bounded and testable.
4. Research LLM calls reuse the existing Agent SDK `query()` pattern (as
   `_collect_text` does) with per-role model tiering, not a new SDK integration.
5. This is gated, multi-phase work. **This spec is Phase 1 only.** PLAN, TASKS,
   and IMPLEMENT each return for review; nothing is built on this document alone.

## Objective

Replace the one-shot deterministic pre-research (when `research_mode="deep"`)
with a recursive **planner → search → extract → synthesise → (loop)** pipeline
matching OpenAI Deep Research / Perplexity Sonar / GPT Researcher deep mode. A
human researcher reads what they find, notices gaps, and searches again; this
gives the writer a brief built the same way. The output is report-grade source
material for long-form pieces, at materially higher cost.

**User:** the pipeline operator who opts into deeper research for a flagship
article (and the reader, via better-triangulated sourcing).

## Tech Stack

- Python 3.11/3.12, Claude via `claude-agent-sdk` (existing).
- Reuses the existing provider stack (`scripts/*_search.py`, and
  `src/agent_sdk/tools/research_tools.py::_run_provider_search` from #389).
- `orjson`, `logging`, `asyncio` (parallel sub-question fan-out).

## Commands

```
Test (targeted):  .venv/bin/python -m pytest tests/test_deep_research_*.py -q
Full suite:       env MPLBACKEND=Agg .venv/bin/pytest tests/ -q
Lint:             .venv/bin/ruff check src/agent_sdk/research tests
Arch gate:        pre-commit run arch-review --all-files
```

## Project Structure

```
src/agent_sdk/research/__init__.py          → new package
src/agent_sdk/research/deep_research.py      → orchestrator: build_deep_research_brief(topic) -> str
src/agent_sdk/research/planner.py            → topic -> 3-5 sub-questions (Sonnet)
src/agent_sdk/research/extractor.py          → (sub-question, sources) -> relevant passages + confidence (Haiku)
src/agent_sdk/research/synthesizer.py        → enough? assemble brief | identify gaps -> more sub-questions (Sonnet)
src/agent_sdk/research/_llm.py               → thin Agent SDK query helper (model-tiered, budget-capped)
src/agent_sdk/stage3_runner.py               → edit: research_mode selects build_research_brief vs build_deep_research_brief
src/agent_sdk/pipeline.py                    → edit: thread research_mode through run_pipeline; add research_cost to cost log
tests/test_deep_research_planner.py          → new (LLM mocked)
tests/test_deep_research_extractor.py        → new
tests/test_deep_research_synthesizer.py      → new
tests/test_deep_research_orchestrator.py     → new (loop, budget, failure modes)
```

## Architecture

```
build_deep_research_brief(topic):
  sub_qs = planner(topic)                      # 1 Sonnet call -> 3-5 sub-questions
  brief_parts, iteration = [], 0
  while iteration < MAX_ITERATIONS:            # hard cap (default 2)
    results = await parallel(                  # one branch per sub-question
      for q in sub_qs:
        sources = _run_provider_search(q, n)   # deterministic, reused from #389
        passages = extractor(q, sources)       # 1 Haiku call -> relevant passages + confidence
    )
    brief_parts += results
    verdict = synthesizer(topic, brief_parts)  # 1 Sonnet call -> {enough: bool, gaps: [sub-q...]}
    if verdict.enough or not verdict.gaps: break
    sub_qs = verdict.gaps                       # loop on the gaps only
    iteration += 1
  return format_brief(topic, brief_parts)      # same string shape as build_research_brief
```

Typical run: 2 iterations, ~10–20 searches, ~5–8 LLM calls. Model tiering:
planner & synthesizer = Sonnet (high-leverage reasoning); extractor = Haiku
(cheap passage selection).

## Code Style

```python
async def build_deep_research_brief(
    topic: str,
    max_iterations: int = 2,
    research_budget_usd: float = 2.50,
) -> str:
    """Recursive planner->search->extract->synthesise brief. Falls back to the
    deterministic brief if the planner yields no sub-questions."""
    ...
```

(Mirrors `build_research_brief`'s string return so callers are unchanged.)

## Testing Strategy

- `pytest`; **all LLM calls and providers mocked** — no live API calls, no spend.
- Layered:
  - planner: topic → parsed sub-questions; malformed-LLM-output fallback.
  - extractor: sources → passages; empty/garbage sources → graceful empty.
  - synthesizer: parses `{enough, gaps}`; never raises on bad LLM output.
  - orchestrator: loop terminates at `MAX_ITERATIONS`; **budget cap** halts early;
    a sub-question with **zero sources** yields "no evidence found" (no crash);
    empty planner output → deterministic fallback; output string shape matches
    `build_research_brief` so the stat audit still functions.
- Coverage > 80% across the `research/` package.

## Boundaries

- **Always:** keep `research_mode="deterministic"` the default; mock LLMs/providers
  in tests; reuse `_run_provider_search` and the existing brief string contract;
  verify the Agent SDK call pattern against `claude-agent-sdk` docs
  (`source-driven-development`) in PLAN; record research cost in the cost log.
- **Ask first:** raising `MAX_ITERATIONS` above 3; switching the default to deep;
  adding full-page fetching; editing `_shared.py` (ADR-002 gate, #420).
- **Never:** make deep research the default; let an LLM fabricate sources (the
  planner/synthesizer reason over *retrieved* sources only); spend beyond
  `research_budget_usd`; bypass the stat audit.

## Success Criteria

1. `research_mode="deterministic"` (default) behaves **exactly as today** — no
   cost, latency, or output change for existing callers (regression-tested).
2. `research_mode="deep"` produces a brief via the recursive loop; with LLMs and
   providers mocked, the orchestrator runs ≥1 planned iteration and assembles a
   brief whose string shape feeds the existing stat audit unchanged.
3. The loop **terminates** at `MAX_ITERATIONS` and halts early on
   `research_budget_usd`; both are enforced deterministically and the research
   cost is recorded in the cost log.
4. A zero-source sub-question and malformed LLM output **never crash** the run
   (graceful "no evidence" / fallback), regression-tested.
5. `> 80%` coverage on `research/`; ruff + arch-review + full suite green.

## Resolved Design Questions (from the issue)

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Iterate count | **Hard cap, default 2 (max 3).** Synthesizer may stop early ("enough"), but the cap bounds cost. No open-ended LLM-judged looping in v1. |
| 2 | Planner model | **Sonnet** — planning is high-leverage; cheap to keep quality here. |
| 3 | Extractor model | **Haiku** — "find relevant passages in this text" is well within Haiku; this is where most calls happen, so the cost saving matters. |
| 4 | Caching | **In-run dedupe only** (reuse #389's query cache shape). Cross-article persistence deferred to v2. |
| 5 | Failure modes | Zero-source sub-question → synthesizer records "no evidence found" and proceeds; never fails the run. |

## Open Questions (need human input)

1. **Budget ceiling:** `research_budget_usd` default — 2.50? This caps a deep run;
   confirm the acceptable per-article research spend.
2. **Full-page fetch:** v1 extracts from snippets only. Do you want full-page
   fetching (better extraction, more latency/load) in scope, or as v2?
3. **Surfacing the mode:** how is `research_mode="deep"` triggered in production —
   a per-topic flag from the editorial board, a CLI flag, or an env var?
4. **ADR:** this is a significant architectural addition; should it get its own
   ADR (research strategy) alongside the spec?

## Estimate

Per the issue: ~10 files added, ~5 edited, ~30 tests, **8–12 hours + prompt
tuning**. Concur. Recommend implementing as **incremental slices** behind the
opt-in flag (planner → extractor → synthesizer → orchestrator loop), each
landing green, so the deterministic default is never at risk mid-build.
