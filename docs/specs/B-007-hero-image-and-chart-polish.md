# SPEC: Hero-image prompt surfacing + chart polish (B-007)

**Status**: IMPLEMENTED — prompt-surfacing + chart polish shipped via PR #447
**Date**: 2026-07-14
**Branch**: `claude/pipeline-status-check-mwptdh`

## Objective

The pipeline must **not** generate the hero image. Per CLAUDE.md Operating
Constraint #4, the hero is human-in-the-loop at PR-review time: the pipeline
produces a hero-image **prompt** and **surfaces it** so the owner can generate
the image themselves during review and drop it in. Also polish the data chart.

## Design

- **Prompt generation** already exists (`image_prompt_synth.compose_prompt` →
  `Stage3Result.image_prompt` + `output/posts/<slug>.image_prompt.md` sidecar).
- **Surface it**: in the keyless end-to-end (`chart_only`) path, inject the
  prompt as a review-visible HTML comment at the top of the post body
  (`_inject_hero_prompt_comment`) — invisible when rendered, visible in the PR
  diff and raw markdown, exactly where the hero belongs. The sidecar is kept.
- **Chart polish**: dynamic left margin sized to the longest label (fixes
  y-axis truncation) + long-label ellipsis; chart title is data-descriptive,
  never the article headline.

## Rejected / removed

- **Procedural (PIL) hero generation** and a **Gemini image tier** were
  prototyped and **removed**. The pipeline generates no image (Constraint #4);
  a keyed image API is forbidden (Constraint #1). Do not reintroduce either.

## Boundaries

- No key, no paid service, no image generation of any kind.
- Chart-only post ships with the prompt surfaced; the owner adds the hero at PR
  review time.
