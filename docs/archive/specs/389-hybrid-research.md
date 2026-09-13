# Spec: Hybrid Research — Deterministic Seed + Writer On-Demand Source Fetch (#389)

**Status:** DRAFT — awaiting human LGTM (do not implement until approved)
**Issue:** [#389](https://github.com/oviney/economist-agents/issues/389)
**Author:** Claude (spec-driven-development)
**Date:** 2026-06-13

---

## Assumptions

> Correct any of these before I proceed to PLAN.

1. The production writer path is `src/agent_sdk/stage3_runner.py` (`run_stage3` → `_collect_text`), which today runs the writer with **`ClaudeAgentOptions(allowed_tools=[])`** (line 296) — i.e. tools are disabled. Enabling one search tool is the core change.
2. The **multi-provider research fallback the issue lists as a dependency already exists** — `build_research_brief()` in `_shared.py` already fans out across arXiv, Google, Semantic Scholar, Brave (and Tavily). **#389 is therefore unblocked**; the search tool will reuse these existing provider functions, not build new ones.
3. The stat audit (`audit_article_stats(article, research_brief)`, `_shared.py:341`) strips any article sentence whose statistics are absent from the **research-brief text**. So writer-fetched sources must be **appended to the brief text that the audit sees**, or the writer's newly-cited stats get stripped. This is the single most important integration point.
4. We accept that enabling a tool makes the writer turn a **tool-use loop** (the Claude Agent SDK drives the back-and-forth); `_collect_text` must tolerate multiple turns and tool results, not just a single completion.
5. Scope is the **writer** search tool only. The recursive Deep Research pattern is explicitly out of scope (that is #390).

## Objective

Let the Stage 3 writer fetch additional sources mid-draft for specific claims it wants to support, instead of being locked into the one-shot seed brief. Keep the deterministic pre-research as the **primary, pre-vetted seed**; add an opt-in `search_for_source` tool the writer calls **sparingly (0–3×)** to strengthen weak claims, pull counter-evidence, or anchor an opening hook.

**Quality floor is unchanged** — the stat audit and Stage 4 validators still catch fabrications. Only the ceiling moves: fewer `[NEEDS SOURCE]` stubs, fewer stripped claims, more complete drafts.

**User:** the pipeline operator (and ultimately the blog reader, via better-sourced articles).

## Tech Stack

- Python 3.11/3.12, Claude via `claude-agent-sdk` (existing).
- Reuses existing search providers in `scripts/*_search.py` (no new providers).
- `orjson`, `logging` per project standards.

## Commands

```
Test (targeted):   .venv/bin/python -m pytest tests/test_research_tools.py tests/test_stage3_writer_skill.py -q
Full suite:        env MPLBACKEND=Agg .venv/bin/pytest tests/ -q
Lint:              .venv/bin/ruff check src/agent_sdk tests
Arch gate:         pre-commit run arch-review --all-files
```

## Project Structure

```
src/agent_sdk/tools/__init__.py        → new package
src/agent_sdk/tools/research_tools.py  → new: search_for_source tool + in-run dedupe cache
src/agent_sdk/stage3_runner.py         → edit: wire tool into writer ClaudeAgentOptions; thread fetched
                                          sources into the brief passed to the stat audit
src/agent_sdk/_shared.py               → NOT edited (pre-existing ADR-002 gate; see #420). If brief
                                          augmentation must live here, that constraint must be resolved first.
tests/test_research_tools.py           → new
tests/test_stage3_writer_skill.py      → extend (writer-with-tool paths)
```

> **Open structural question:** the cleanest place to append on-demand sources to the brief before the audit is the `run_stage3` body (which already holds `research_brief`), so we can likely avoid editing `_shared.py` and its ADR-002 gate. To confirm in PLAN.

## Code Style

```python
@tool(
    "search_for_source",
    "Find sources for a specific claim. Returns title/url/snippet for each. "
    "Call sparingly (max 3/article) — each call adds latency. Prefer the seed brief.",
    {"query": str, "max_results": int},
)
async def search_for_source(args: dict) -> dict:
    """Writer-callable source fetch, budget- and dedupe-guarded."""
    ...
```

(Exact decorator/registration form to be confirmed against the `claude-agent-sdk` docs during PLAN — see Boundaries → source-driven-development.)

## Testing Strategy

- `pytest`, providers **mocked** (no live API calls), per project standard.
- Required cases:
  - Writer happy path: tool offered, writer calls it once, fetched source integrated, draft well-formed.
  - **Budget exhaustion**: 4th call in one article is refused gracefully; writer still finalises.
  - **Tool failure**: provider raises → tool returns empty/marked result → writer does not crash.
  - **Stat survival**: a stat from a writer-fetched source is NOT stripped by the audit (the key regression).
  - **Dedupe**: identical query within one run hits the cache, not the provider.
- Coverage > 80% on `research_tools.py`.

## Boundaries

- **Always:** mock providers in tests; keep the seed brief primary; route the tool through the existing provider functions; verify the SDK tool-wiring against official `claude-agent-sdk` docs (`source-driven-development`) before coding.
- **Ask first:** any edit to `_shared.py` (ADR-002 gate, see #420); raising the default call budget above 3; adding a new search provider.
- **Never:** let writer-fetched stats bypass the stat audit; commit provider API keys; remove the determinism of the seed brief.

## Success Criteria

1. With the tool mocked to return a source, the writer can cite a claim **not in the seed brief**, and that claim **survives the stat audit** (regression-tested).
2. The writer never exceeds **3** search calls/article; the cap is enforced deterministically and the count is recorded in the cost log alongside `writer_cost_usd`.
3. Tool failure or budget exhaustion **never** breaks the writer turn — it always produces a well-formed article (existing `MalformedArticleError` path stays green).
4. Identical queries within one article run are deduped (≤1 provider hit per distinct query).
5. Full suite green; `ruff` + arch-review pass; new code > 80% covered.

## Resolved Design Questions (from the issue)

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Call budget | **Hard cap = 3/article**, recorded in cost log. Simple, cheap insurance; revisit only with data. |
| 2 | Determinism | **Accept run-to-run variation.** The stat audit + Stage 4 gates hold the floor; determinism is not worth the ceiling we'd lose. |
| 3 | Provider routing | **Reuse the existing stack, Brave-first for latency.** No leaner bespoke path in v1 — keep one code path. |
| 4 | Cache | **In-run, in-memory dedupe** keyed by normalised query. No cross-article persistence in v1. |
| 5 | Attribution | **Seed brief stays primary** (pre-vetted); on-demand sources get "supporting, if relevant" treatment in the prompt. |

## Open Questions (need human input)

1. **Brief augmentation site:** confirm we can append on-demand sources to the brief inside `run_stage3` (avoiding `_shared.py` / the ADR-002 gate). If not, #420 must land first.
2. **SDK tool mechanism:** the exact `claude-agent-sdk` API for exposing a custom tool to the writer (in-process `@tool` + sdk MCP server, vs. `allowed_tools`) — to be pinned in PLAN via official docs.
3. **Latency budget:** is +6–9s worst case (3 calls) acceptable for the article SLA?

## Estimate

Per the issue: ~3 files added, ~3 edited, ~8 tests, **2–3 hours**. Concur.
