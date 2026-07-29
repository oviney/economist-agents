# ADR-0016: One pipeline path — retire the human-image handshake

**Status:** Accepted
**Date:** 2026-07-28
**Decision Maker:** Ouray Viney (owner)
**Supersedes:** *(none — amends the practical reading of Operating Constraint #4)*
**Superseded by:**

## Context

The CLI grew a **two-step image handshake** (#403): Stage 3 produced the article
and chart, persisted slug-keyed state, printed a paste-ready prompt, and exited
**10**. A human generated the hero image elsewhere, dropped the PNG at
`output/posts/images/<slug>.png`, and ran `--resume <slug>` to finish Stage 4
behind a deterministic PNG gate. That design was correct when it was written: the
pipeline could not produce a hero, and Operating Constraint #1 forbids paying a
raster image model to make one.

**B-016b (2026-07-27) removed the premise.** Stage 3 now draws the hero itself as
SVG on the Claude subscription — keyless, and consistent with Constraint #4's
"visuals are drawn as CODE, never generated as pixels".

That left the CLI with two modes and a lie in each name:

- `--image-mode hero` was the **default** and was dead. It ran the handshake and
  exited 10 without ever reaching Stage 4. Its operator instructions said to
  paste the prompt into `chat.openai.com` — a workflow Constraints #1–#4 forbid.
- `--image-mode chart_only` was the only mode that ran end to end, and since
  B-016b it ships a Claude-drawn hero, so "chart only" no longer described it.

`image_gate.py` (BUG-060) compounded it: PNG magic bytes, a 1792×1024 dimension
check, and a 50 KB floor — all unreachable once heroes became SVG, and reachable
only from `--resume`, itself part of the dead path.

The forcing question was not "which mode is right" but "does the pause still
serve anything". Two defects (BUG-060 and the mode naming) had one cause, and
patching them separately would have preserved a route nothing exercised.

## Decision

**We will delete the human-image handshake entirely.** The pipeline has exactly
one path: `python -m src.agent_sdk.pipeline "<topic>"` runs Stage 3 → Stage 4 and
exits 0 when the article is publish-ready.

Removed: `--image-mode`, `--resume`, `--no-image`, `image_gate.py`,
`_run_stage3_with_handshake`, `_print_handshake_message`, `_run_resume`, the
slug-keyed resume-state helpers, `HandshakeArtefacts`, and exit codes 10 and 11.
The exit codes are **retired, not reused** — older notes and scripts still refer
to them, so silently reassigning the numbers would be worse than leaving a gap.

`_prepare_for_stage4` and `_maybe_inject_hero_prompt` lose their mode gate and
keep the behaviour that was correct: always embed the chart, strip hero
frontmatter **only** when no hero exists (the B-020 run-4 defect), and inject the
drawing brief only when a reviewer would have to act on it.

**Hand-supplied art survives** as Constraint #4 requires, by a simpler route:
overwrite `output/posts/images/<slug>-hero.svg` and re-run. The
`.image_prompt.md` sidecar is still written and is the brief.

## Alternatives Considered

1. **Repair and rename both modes** — keep `--resume` as the hand-supply route,
   make the image gate format-aware instead of PNG-only (fixing BUG-060), and
   rename the modes truthfully (`auto` / `handshake`). Rejected: it preserves a
   second path that has not been exercised since B-016b, and an unexercised path
   is one that is never known to be right. The measured evidence was that every
   real run since B-016b used the end-to-end path.
2. **Leave the handshake, change only the default** — flip the default to the
   working mode and leave `hero` reachable. Rejected: it keeps live code whose
   operator instructions point at a third-party image tool the constraints
   forbid, and keeps `image_gate.py` alive for a file format the pipeline no
   longer produces.
3. **Strip the hero-prompt comment at deploy instead of pausing** — replace the
   pause with a silent cleanup. Rejected as a *substitute* for this decision: it
   answers a different question (see ADR-0017, which adopts the gate but rejects
   stripping in favour of refusing).

## Consequences

- **Positive:** one path, so the documented command is the tested command. Net
  **−773 lines**. No reachable code instructs the operator to use a third-party
  image tool. The default flag value can no longer be the broken one, because
  there is no flag.
- **Positive:** it exposed a latent regression — the deleted path had *better*
  research error messages than the surviving one, which had collapsed exit 3
  (topic too narrow) into exit 2. Fixed while removing.
- **Negative:** hand-supplying art is no longer a first-class flag. It is a
  documented manual step (overwrite the SVG, re-run), which is less discoverable
  than `--resume` was.
- **Negative:** exit codes 10 and 11 are burned. Anything that branched on them
  now sees exit 0 or a research exit code instead.
- **Follow-up:** B-022 removed `EconomistContentFlow`'s parallel DALL-E branch,
  which this decision made provably dead — executing ADR-0014 rather than
  deciding anything new.
- **Revisit if:** Constraint #4 is amended again to permit a raster image model,
  or hero drawing becomes unreliable enough that a human-supplied fallback needs
  to be a supported mode rather than a manual step.

## References

- Spec: [`docs/specs/B-021-run-safety-cleanups.md`](../specs/B-021-run-safety-cleanups.md) (slice 3)
- Spec: [`docs/specs/B-016b-automatic-hero-svg.md`](../specs/B-016b-automatic-hero-svg.md) — the change that removed the premise
- Spec: [`docs/specs/featured-image-handshake.md`](../specs/featured-image-handshake.md) — the design being retired
- [ADR-0014](0014-retire-paid-github-actions-generation.md) — retired the DALL-E path this handshake was built to work around
- [ADR-0017](0017-gate-publishable-content-at-deploy.md) — where the hero-prompt comment is now caught
- `BACKLOG.md` B-021, B-022; BUG-060
- CLAUDE.md Operating Constraints #1–#4
