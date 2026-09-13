# Spec: B-012 · Opt-in `deep-brief` research mode

> Backlog: **B-012** (`type:feature`). Prototype validated (2026-07-22) — see
> `docs/research/ai-productivity-brief.md` (the prototype output) and the
> triage in `docs/ideas/tooling-adoption.md`.

## Objective

Give the pipeline an **opt-in** research mode that produces a verified,
adversarially-checked, cited brief via the `deep-research` harness — for
flagship/cornerstone posts where sourcing quality matters most. `claude_web`
stays the **everyday default**; deep-research is never automatic.

**Why opt-in, not default (measured, not guessed):** the prototype was
*dramatically* better — 19 claims each surviving a 3-0 verification vote, and it
**refuted the widely-cited (and walked-back) Accenture Copilot numbers** that a
single-pass researcher would ship. But one topic cost **~102 agents, ~2M tokens,
~15 minutes, and exhausted the session usage limit.** That is a special-occasion
tool, not a per-article step.

## Assumptions

1. deep-research is invoked as a **pre-generation step the owner runs manually**,
   producing a brief file the writer then consumes — *not* wired inside
   `run_pipeline`'s automatic flow (keeps the heavy cost explicit and opt-in).
2. Output format = the verified-claims markdown the prototype produced
   (`docs/research/*.md`): claim + quote + source + vote, plus a refuted list.
3. The writer can already be handed a research brief (the existing brief-building
   path) — deep-brief just supplies a *better* brief for that same slot.

## Scope

**In:**
- A documented command / thin wrapper: run `deep-research` on a topic → write
  `docs/research/<slug>.md` (verified claims + refuted + sources).
- A path to feed that brief into the writer (Stage 3) in place of the
  `claude_web`/deterministic brief — e.g. `--research-mode deep-brief
  --brief docs/research/<slug>.md`, or the writer reads the file.
- Runbook + CLAUDE.md note: deep-brief is opt-in, heavy, for flagship posts;
  `claude_web` remains the default.
- Guard: refuted claims must be clearly separated so they never reach the writer.

**Out:**
- Wiring deep-research into the automatic `run_pipeline` flow (never default).
- Re-running deep-research per article, or on a schedule.
- Fixing the harness's synthesis-on-session-limit failure (upstream; the
  unmerged verified list is usable as-is).

## Commands

```bash
# 1. Produce a verified brief (opt-in, heavy — flagship posts only):
#    invoke the deep-research skill on the topic → docs/research/<slug>.md
# 2. Generate the article from that brief:
python -m src.agent_sdk.pipeline "<topic>" --research-mode deep-brief \
    --brief docs/research/<slug>.md --image-mode chart_only
```

## Testing Strategy

- Unit: the brief-ingest path parses a `docs/research/*.md` brief and passes only
  confirmed claims to the writer prompt (refuted excluded). Mock the file.
- Manual: one real deep-brief → article run on a flagship topic; confirm the
  article's stats trace to confirmed claims, not refuted ones.
- No new coverage of the deep-research harness itself (external skill).

## Boundaries

- **Always:** keep deep-research opt-in and manual; separate refuted claims from
  the writer input.
- **Ask first:** any change that would run deep-research automatically or on a
  schedule (violates the opt-in premise and the cost finding).
- **Never:** make deep-brief the default; feed refuted claims to the writer.

## Success Criteria

1. A documented command produces `docs/research/<slug>.md` (confirmed + refuted +
   sources) from a topic.
2. `--research-mode deep-brief` generates an article whose stats come only from
   confirmed claims.
3. Docs state plainly: opt-in, heavy, flagship-only; `claude_web` is the default.
4. `make ci-local` stays green.

## Open Questions

- Brief ingestion: a new `deep-brief` research mode in `pipeline.py`, or simplest
  — the writer reads a `--brief <file>` argument? (Lean: `--brief`, least
  coupling.)
