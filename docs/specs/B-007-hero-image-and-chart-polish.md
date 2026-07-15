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

Claude cannot generate raster images, so the hero comes from one of two tiers,
chosen automatically:

1. **Gemini image model** (`gemini-2.5-flash-image` / Imagen via `google-genai`)
   — used when a `GEMINI_API_KEY`/`GOOGLE_API_KEY` is present (free AI-Studio
   tier). Produces a real conceptual editorial illustration.
2. **Keyless programmatic editorial hero** (PIL) — the always-on fallback:
   a typographic "cover" in the Economist palette (red tab, bold serif title,
   a deterministic geometric motif, off-white ground). Needs no key, renders
   every run, so a themed hero is *never* missing.

Every run therefore ships **hero + chart**. Zero-key runs get the programmatic
hero; adding a free Gemini key upgrades the hero to a generated illustration.

## Scope

- `src/agent_sdk/hero_image.py` — keyless PIL editorial hero (`render_editorial_hero`).
- `src/agent_sdk/gemini_image.py` — Gemini hero (`generate_gemini_hero`), returns
  None on missing key / any failure so the caller falls back.
- `generate_hero(...)` — unified entrypoint: Gemini → else editorial hero.
- Pipeline wiring: new default so the keyless end-to-end path emits a hero
  (sets `image:` + keeps `image_alt`/`image_caption`), replacing the OpenAI-only
  `featured_image_agent` path for this flow.
- `src/agent_sdk/chart_renderer.py` — dynamic left margin (fix label truncation);
  chart title discipline (never the article headline).

## Boundaries

- Never require a paid key; never block a run on a missing image key (fall back).
- Keep the chart-only capability; hero is additive.
- Prove the keyless path live; Gemini path is unit-tested (mocked) + documented
  (activates when the owner adds a free key).
