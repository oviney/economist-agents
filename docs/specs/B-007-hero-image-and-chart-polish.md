# SPEC: Hero image (keyless + Gemini) and chart polish (B-007)

**Status**: IN PROGRESS (owner delegated: "figure it out, work within constraints")
**Date**: 2026-07-14
**Branch**: `claude/pipeline-status-check-mwptdh`

## Objective

Restore a professional themed **hero image** to every generated post (regressed
when keyless `chart_only` dropped it) and **polish the chart**, within the
owner's constraints: **no paid API keys, no ChatGPT**; available assets are the
**Claude subscription** (this pipeline's auth; cannot generate images) and
**Google Gemini** (can generate images).

## Constraints → design

Per CLAUDE.md **Operating Constraints**: NO API keys of any kind (including
free-tier), no paid services, no image-generation API. Claude cannot generate
raster images, so the hero is **drawn procedurally in Python** — a keyless
editorial "cover" (PIL): red tab, bold serif title, thin rule, editorial dek,
and a deterministic geometric motif in the Economist palette. It renders every
run in milliseconds and needs nothing installed beyond Pillow.

Every run ships **hero + chart**, fully keyless.

> **Rejected:** a Gemini/Imagen image-generation tier was prototyped and
> **removed** — it requires an API key, which violates Operating Constraint #1.
> Do not reintroduce it.

## Scope

- `src/agent_sdk/hero_image.py` — keyless PIL editorial hero
  (`render_editorial_hero`) + `generate_hero(...)` entrypoint (keyless-only).
- Pipeline wiring: `image_mode="auto"` (+ CLI `--image-mode auto`) emits a hero
  (sets `image:` + guarantees `image_alt`/`image_caption`) and embeds the chart,
  replacing the OpenAI-only `featured_image_agent` path for this flow.
- `src/agent_sdk/chart_renderer.py` — dynamic left margin (fix label truncation);
  chart title discipline (never the article headline).

## Boundaries

- Never require a key or paid service (Operating Constraints #1–#2); the hero is
  keyless and always renders.
- Keep the chart-only capability; hero is additive.
- Prove the keyless path live.
