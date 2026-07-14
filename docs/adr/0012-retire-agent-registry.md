# ADR-0012: Retire the AgentRegistry Pattern

**Status:** Accepted
**Date:** 2026-07-14
**Deciders:** Ouray Viney (Agentic AI Architect)
**Supersedes:** [ADR-0002](0002-agent-registry-pattern.md)

## Context

[ADR-0002](0002-agent-registry-pattern.md) introduced an **AgentRegistry** that discovered
"agent" personas from `.github/agents/*.agent.md`, wrapped an LLM provider abstraction
(`OpenAIProvider` / `AnthropicProvider`), and was meant to be the single funnel for all LLM
instantiation ("no Agent Sprawl"). It belonged to the autonomous multi-agent / Scrum-team
model documented in the (now retired) `AGENTS.md`.

That model is dead. The content pipeline moved to the Anthropic Agent SDK
(`src/agent_sdk/`) in the CrewAI removal (ADR-0006), and LLM clients are created through the
`scripts/llm_client.py` factory. In practice:

- **Nothing in the product used the registry.** `AgentRegistry` had exactly one `src/`
  importer, `src/manager.py`, which was itself dead code (no entrypoint referenced it). The
  `OpenAIProvider` / `AnthropicProvider` classes had no product consumers — only the registry
  and their own unit tests.
- **The personas were documentation, not runtime.** The 10 `.github/agents/*.agent.md` files
  described Scrum/dev roles; the pipeline never dispatched them.
- **The guardrail pointed at the wrong thing.** `test_architecture_compliance.py` and the
  `pre_commit_arch_check.py` hook told authors to "use `AgentRegistry.get_agent()`", but the
  sanctioned path is already the `llm_client.py` factory.

This is the `W2-A` step of the process consolidation
(`docs/specs/repo-process-consolidation.md`).

## Decision

Retire the AgentRegistry pattern and everything that only existed to serve it:

- Delete `scripts/agent_registry.py` (registry + the unused provider abstraction),
  `src/manager.py` (dead), and `AGENTS.md`.
- Delete the 10 `.github/agents/*.agent.md` personas.
- Delete the registry-only tests (`test_llm_providers.py`,
  `test_agent_registry_enhancement.py`, `test_architect_agent.py`) and the SM-agent benchmark
  (`scripts/benchmarks/measure_sm_effectiveness.py`, its test, and `nightly-eval.yml`).
- **Keep** the "no direct `openai`/`anthropic`/`crewai` imports" guardrail — it is still
  valuable — but re-anchor it on the `scripts/llm_client.py` factory instead of the registry
  (`test_architecture_compliance.py`, `pre_commit_arch_check.py`), and keep the crewai-import
  guard untouched.

The **content-crew agent system is unaffected**: `scripts/agent_loader.py` (which loads the
`agents/*.yaml` writer/research/editor/graphics prompts used by the live pipeline) is a
different mechanism and stays.

## Consequences

- **Positive:** removes a dead architectural layer and the misleading "use AgentRegistry"
  guidance; the single LLM-instantiation path is now unambiguously the `llm_client.py`
  factory; ~19 files of unused code/personas/tests gone.
- **Negative / risk:** any future desire for a persona-dispatch layer would need a fresh
  design rather than reviving this one. Acceptable — the Agent SDK covers current needs.
- **Neutral:** ADR-0002 is marked Superseded (not deleted); git history preserves the
  retired code.
