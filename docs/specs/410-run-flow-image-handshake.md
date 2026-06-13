# Spec: Migrate run_flow() to the #403 Image-Handshake Model (#410)

**Status:** DRAFT — awaiting human LGTM (do not implement until approved)
**Issue:** [#410](https://github.com/oviney/economist-agents/issues/410)
**Author:** Claude (spec-driven-development)
**Date:** 2026-06-13

---

## Assumptions

> Correct any of these before I proceed to PLAN.

1. The CLI path (`python -m src.agent_sdk.pipeline`) is the **reference** image-handshake implementation (#403/#404): Stage 3 → persist slug-keyed state in `output/state/` + a prompt artefact → **exit code 10** (pause for human image drop) → `--resume <slug>` re-enters, validates the dropped PNG (exit 11 on gate failure), then runs Stage 4.
2. `src.economist_agents.flow.run_flow()` / `EconomistContentFlow.generate_content()` is the **Python-API** path. It currently calls `asyncio.run(run_pipeline(topic))` (which runs Stage 4) and **then** auto-attempts DALL-E (`generate_featured_image`, gated only on `OPENAI_API_KEY`).
3. The bug: after #403, Stage 4 validates that the `image:` reference resolves to a real file. In the flow path Stage 4 runs **before** the image step, so a valid draft can be routed to revision purely because its hero image does not exist yet.
4. The CLI's resume machinery (exit-10 pause, `--resume`, state file) is a **process-level** contract suited to an interactive operator. Reproducing it inside a synchronous Python API call is awkward (a library function cannot "pause the process and wait for a human" without becoming a state machine the caller must drive).

## Objective

Give `run_flow()` an explicit, documented image policy so that (a) Stage 4 never rejects a draft merely because the flow has not yet run its image step, and (b) **no paid image API is called by default**. Make chart-only and hero-image modes first-class and tested.

## Recommended design (resolves the issue's "decide 1 vs 2" fork)

The issue offers two options:
1. a resumable state-machine pause/resume inside `run_flow()` (CLI parity), or
2. a chart-only orchestration path that strips hero metadata before Stage 4.

**Recommendation: option 2 as the default, with an explicit opt-in hero mode — not a reimplementation of the CLI state machine.**

Rationale:
- The CLI already provides the human handshake. Duplicating exit-10/`--resume`/state inside a synchronous Python function would fork that machinery and invert the library/CLI relationship (a library shouldn't `sys.exit(10)` on its caller).
- The acceptance criteria emphasise "default does not auto-call a paid API" and "chart-only and hero-image modes both covered" — which option 2 satisfies directly.

Concretely, `generate_content` (or `run_flow`) takes an `image_mode` policy:
- **`"chart_only"` (default):** strip hero `image*` frontmatter *before* Stage 4 so the draft validates on its chart alone; never call DALL-E.
- **`"hero"` (explicit opt-in):** run Stage 3, then the image step (DALL-E or a supplied path), patch the resolved `image:` into frontmatter, *then* Stage 4 — so Stage 4 sees a real file.

This requires Stage 4 to run **after** the chosen image step in `hero` mode. If `run_pipeline` cannot currently be invoked Stage-3-only from the flow, PLAN must add a seam (e.g. a `run_pipeline(..., stop_before_stage4=True)` option or reuse the pipeline's Stage-3 entry) rather than the flow re-running Stage 4 itself.

## Tech Stack / Commands / Structure

- Existing: `src/economist_agents/flow.py`, `src/agent_sdk/pipeline.py`. No new deps.
- Test: `.venv/bin/python -m pytest tests/test_flow_agent_sdk.py tests/test_pipeline_handshake.py -q`
- Lint/arch: `ruff check src/economist_agents src/agent_sdk` · `pre-commit run arch-review`

## Testing Strategy

- DALL-E and `run_pipeline` **mocked** — no paid calls, no network.
- Required cases:
  - **Default (chart_only) never calls the image API** (assert `generate_featured_image` not invoked) and produces a Stage-4-valid draft with no hero `image:`.
  - **chart_only draft is not rejected by Stage 4** for a missing hero image (the core bug regression).
  - **hero mode** patches a resolved `image:` and only then runs Stage 4; Stage 4 sees the file.
  - **hero mode without `OPENAI_API_KEY`** degrades gracefully (documented fallback, no crash, no paid call).
- Coverage > 80% on changed flow code.

## Boundaries

- **Always:** mock paid APIs in tests; keep the CLI handshake the canonical interactive path; document the CLI-vs-Python-API difference in flow docs.
- **Ask first:** any change to `run_pipeline`'s public signature; making `hero` the default; editing `_shared.py` (ADR-002 gate, #420).
- **Never:** auto-call a paid image API by default; let Stage 4 reject a draft solely for a not-yet-generated hero image; `sys.exit()` from inside the library function.

## Success Criteria

1. `run_flow()` has an explicit, documented `image_mode` policy; **default execution calls no paid image API**.
2. A chart-only draft is **never** rejected by Stage 4 for a missing hero image (regression-tested).
3. Both chart-only and hero modes are covered by tests; the optional DALL-E path is explicit opt-in only.
4. Flow docs distinguish the CLI handshake from the Python-API behaviour.
5. Full suite green; ruff + arch-review pass.

## Open Questions (need human input)

1. **Confirm the fork:** option 2 (chart-only default + opt-in hero) as recommended, or do you want full CLI state-machine parity (option 1) in the Python API?
2. **Stage-3-only seam:** acceptable to add a `stop_before_stage4` option to `run_pipeline` (cleanest), or should the flow get its own Stage-3 entry?
3. Should `hero` mode support a **supplied local image path** (not just DALL-E), so automated callers can attach a pre-made hero without a paid call?

## Estimate

~2 edited (flow.py, pipeline.py), ~1 doc, ~6–8 tests. **3–4 hours**, contingent on the Stage-3-only seam.
