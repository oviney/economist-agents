# ADR-0012: Keyless `claude_web` Research (LLM in the research path, subscription-only)

**Status:** Accepted
**Date:** 2026-07-14
**Decision Maker:** Ouray Viney (Engineering Lead)
**Supersedes:** —

## Context

The pipeline's two existing research paths both require a paid key:
`build_research_brief` (`deterministic`, default) and Deep Research (`deep`,
ADR-0011) both drive the Serper API and so depend on `SERPER_API_KEY`. The
writer and graphics stages already run on the Claude subscription via the Agent
SDK (`claude_agent_sdk.query()`), needing no `ANTHROPIC_API_KEY`. The gap: a
full end-to-end run still could not complete without at least one paid key
(Serper for research; optionally OpenAI for a hero image).

B-006 requires a run that needs **no paid API keys at all** — usable by an owner
who has a Claude subscription but will not provision or pay for per-token API
keys. Research is the last coupling. The question is how to do research keyless.

ADR-0011 deliberately kept research LLM-free to prevent source hallucination.
The keyless requirement is in direct tension with that principle.

## Decision

We add a third **opt-in** research mode, `claude_web`, alongside
`deterministic` (default) and `deep`. It has Claude do its own live web research
through the Agent SDK's built-in `WebSearch`/`WebFetch` tools — on the Claude
subscription, with no Serper key and no `anthropic` client. It lives in
`src/agent_sdk/research/claude_web.py`, is selected via the same `research_mode`
argument / `RESEARCH_MODE` env override threaded through `run_stage3` /
`run_pipeline`, and returns the same brief string contract (anti-fabrication
guardrail header + sourced findings) so the writer and stat audit are unchanged.

This is a **deliberate, scoped departure from ADR-0011's "no LLM in the research
path"** — confined to the `claude_web` mode. `deterministic` remains the default
and remains LLM-free; nothing about the default path changes.

The vision-refinement helper (`refine_image_metadata`) is likewise rerouted off
the raw `anthropic` client onto `query()` so the hero path is keyless too.

## Alternatives Considered

1. **Keep requiring `SERPER_API_KEY` for all research** — Rejected: fails the
   zero-key requirement; the owner has ruled out provisioning any paid key.
2. **Supply a static, pre-written research brief (fixture)** — Rejected: keyless
   but not live; grounding is only as good as a hand-authored file, and it adds
   an authoring burden per article. Claude's own web tools are both keyless and
   live.
3. **Make `claude_web` the default** — Rejected: it is non-deterministic and
   puts an LLM in the research path; that must be an explicit opt-in, not the
   default, per ADR-0011.

## Consequences

- **Positive:** A genuinely keyless end-to-end run on the subscription;
  live, sourced research without Serper; brief contract preserved so downstream
  stages are unchanged; removing `anthropic` from the vision helper also clears
  a standing ADR-0002 concern there.
- **Negative:** When opted in, research is **non-deterministic** and departs from
  the LLM-free principle; source quality depends on the model's search behaviour.
- **Mitigation:** The downstream `citation_verifier` / `publication_validator`
  citation gates stay enforced, so fabricated or weak sources are still caught.
- **Revisit if:** subscription web-tool availability or quality shifts, or a
  cheaper deterministic keyless option becomes viable.

## References

- Spec: `docs/specs/B-006-keyless-subscription-pipeline.md`
- Plan: `tasks/plan.md`; `BACKLOG.md` B-006
- Related: ADR-0011 (opt-in Deep Research), ADR-0002 (LLM-client factory)
- Defects surfaced + fixed under B-006: BUG-038, BUG-039
