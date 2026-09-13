# Story 1 Spike Report — Stage 3 on Agent SDK

**Issue:** #309
**Epic:** #308
**Branch:** `feat/309-agent-sdk-stage3-spike`
**Date:** 2026-04-25
**Topic:** "the productivity paradox of AI coding assistants"

## Result

| Metric | Agent SDK | CrewAI baseline |
|---|---|---|
| Total cost | **$0.1475** | _Could not run_ |
| Wall time | 154.5 s | _Could not run_ |
| Article length | 15,902 chars (~2,500 words) | _Could not run_ |
| Stat audit removals | 4 sentences | _Could not run_ |
| Tooling dependency | Claude subscription only | OpenAI API + working quota |

**Cost breakdown (Agent SDK):**
- Writer: $0.1133 (Sonnet 4.5)
- Graphics: $0.0343 (Sonnet 4.5)
- Includes Claude Code CLI subprocess overhead per call

## Why no CrewAI baseline number

OpenAI billing is exhausted (`insufficient_quota` 429). The existing
production pipeline cannot currently generate articles. This was logged
as an open item in the 2026-04-21 sprint memo and remains unresolved.

`ANTHROPIC_API_KEY` is also not set in the local `.env`, so the CrewAI
fallback to Claude (`_get_crewai_llm`) cannot run either. The Agent SDK
path uses the user's existing Claude Code subscription auth — no
additional API key configuration was required.

This is itself decision-relevant: Option B removes the OpenAI dependency
that currently blocks the pipeline.

## Functional findings (positive)

- Reused `Stage3Crew._build_research_brief` unchanged — the deterministic
  research path is framework-agnostic, as ADR-0006 anticipated.
- Reused `_audit_article_stats` unchanged — caught 4 fabricated stats in
  the Agent SDK output. The deterministic gate works regardless of the
  agent runtime above it.
- Article quality on the surface is comparable to recent CrewAI output:
  British spelling throughout, named studies cited (5 references, all
  from research brief), no banned hedging phrases, vivid ending, no
  numbered/bulleted lists in the body.
- Chart JSON parsed cleanly without the JSON-fence stripping fallback.

## Functional findings (issues to fix in Story 2)

1. **Doubled article output.** The Writer emitted two complete articles
   in one response (frontmatter appears twice, References section twice).
   Likely caused by the system prompt phrase "validate your work against
   all 10 rules above before submission" — the model interpreted that as
   "emit, then re-emit refined." Fix: remove the validation instruction
   from the system prompt; rely on the deterministic gates downstream.
2. **Lost paragraph breaks.** Headings appear glued to the prose without
   the blank lines markdown requires. Either the SDK is collapsing
   newlines on assembly or the model is omitting them. Fix: explicit
   formatting instruction + a post-processor to re-insert blank lines
   around headings.
3. **One concatenated-word artefact** ("OrganisationsDoubleDown"). Likely
   a streaming-chunk join bug. Investigate `_collect_text` whitespace
   handling.
4. **Tool-rejection crash.** First spike attempt died because the model
   tried to `Read` `skills/economist-writing/SKILL.md` (referenced in the
   prompt) but `allowed_tools=[]` rejected the call, killing the CLI
   subprocess. Fixed in this spike by removing the file reference from
   the prompt. Story 2 should decide: inline rules vs. allow Read access
   to skill files.

## Decision evidence

The spike validated the core hypothesis from ADR-0006:

- ✅ Agent SDK can run the Writer + Graphics roles end-to-end against the
  existing Phase 1 deterministic infrastructure.
- ✅ Deterministic quality gates (`_build_research_brief`,
  `_audit_article_stats`) port over with zero changes.
- ✅ Cost tracking via `ResultMessage.total_cost_usd` works per call,
  enabling the `max_budget_usd` story (Story 3).
- ✅ MCP integration is available but was not exercised in this spike —
  Writer and Graphics did not need tools. Story 2 will exercise it via
  the Editor stage and `web-researcher` for Stage 4 quality checks.
- ⚠️ The 4 issues above must be resolved before parity is claimed.

## Recommendation for Stories 2-5

Proceed with the migration. The Phase 1 MCP investment compounds, the
deterministic gates are runtime-agnostic, and Option B removes the
blocking OpenAI dependency. The 4 issues above are all addressable in
Story 2 (port Stage 4 + fix Writer issues).

## Artefacts

- `logs/spike/agent_sdk_article.md` — Agent SDK output (with both copies)
- `logs/spike/agent_sdk_chart.json` — chart spec
- `logs/spike/agent_sdk_metrics.json` — cost / time / size
- `src/agent_sdk/stage3_runner.py` — spike implementation
- `scripts/spike_crewai_baseline.py` — baseline runner (failed on quota)
