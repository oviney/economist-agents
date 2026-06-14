# ADR-0011: Opt-In Recursive Deep Research

**Status:** Accepted
**Date:** 2026-06-13
**Decision Maker:** Ouray Viney (Engineering Lead)
**Supersedes:** —

## Context

The research phase (`build_research_brief`) is a one-shot, deterministic, no-LLM
search burst (~$0.30, ~5s). It was kept LLM-free by design to prevent source
hallucination. Issue #390 proposes a recursive planner→search→extract→synthesise loop
(the Deep Research pattern) that produces report-grade briefs, but at materially higher
cost and latency (5–10× cost, $1.50–3.00 vs ~$0.30; 30–60s vs ~5s) and — critically —
introduces LLM calls into a path that was deliberately deterministic. The decision is
whether to adopt Deep Research, and if so, how to bound its cost and contain its
non-determinism without regressing the cheap, safe default.

## Decision

We will add Deep Research as an **opt-in mode, not a replacement** for the deterministic
research path. A `research_mode` parameter (`deterministic` default | `deep`, with a
`RESEARCH_MODE` env override) is threaded through `run_stage3` / `run_pipeline`. Deep
Research lives in a new `src/agent_sdk/research/` package that reuses the existing search
providers. It is bounded by a hard iteration cap (2) and a `research_budget_usd` ceiling
($2.50), with model tiering (planner/synthesizer on Sonnet, extractor on Haiku). The
brief keeps the same string contract, so the writer and stat-audit stages are unchanged;
research spend is recorded in the cost log.

## Alternatives Considered

1. **Replace the deterministic path with Deep Research** — Rejected: 5–10× cost and
   30–60s latency on every run, and it injects non-determinism / hallucination risk into
   a path that was deliberately LLM-free. Unacceptable as the default.
2. **Do not adopt Deep Research at all** — Rejected: there is genuine demand for
   report-grade briefs; refusing the capability outright forecloses a useful tier.
3. **Adopt unbounded recursion** — Rejected: cost and latency become unpredictable
   without a hard iteration cap and a per-run budget ceiling.

## Consequences

- **Positive:** Report-grade briefs available on demand without sacrificing the cheap,
  deterministic default; cost is bounded and observable via the cost log; the brief's
  string contract is preserved so downstream stages need no changes.
- **Negative:** When opted in, the path is non-deterministic and expensive; v1 extracts
  from search snippets only (full-page fetch deferred).
- **Follow-up:** production trigger for `deep` mode; cross-article research cache;
  full-page fetch in the extractor.
- **Revisit if:** Deep Research cost/quality shifts materially, or demand makes `deep`
  the sensible default.

## References

- Issue #390 (Deep Research); companion #389
- Spec: `docs/specs/390-deep-research.md`
- Migrated from closed issue #428 / `BACKLOG.md` B-003
