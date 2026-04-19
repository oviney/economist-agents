---
name: editorial-illustration
description: Define visual standards for featured images and charts in the content pipeline. Use when generating a DALL-E featured image, when creating chart specifications, when reviewing visual quality of a generated article.
---

# Editorial Illustration

## Overview

Every featured image must look like it was commissioned by The Economist's art department. Every chart must follow Economist data visualisation standards. This skill is the visual standard for the Graphics Agent and the visual engagement evaluator.

## When to Use

- Generating an image prompt for manual generation (default, ADR-0009)
- Generating a DALL-E 3 featured image for an article (opt-in, `IMAGE_GENERATION_MODE=api`)
- Creating chart specifications for data-driven articles
- Evaluating visual engagement scoring dimension
- Debugging why images look generic or chart formatting is wrong

### When NOT to Use

- For article text quality — that's `economist-writing`
- For article scoring — that's `article-evaluation`
- For non-editorial images (screenshots, diagrams, architecture charts)

## Workflow Modes (ADR-0009)

| Mode | Env Var | Behaviour | Cost |
|------|---------|-----------|------|
| Prompt-only (default) | `IMAGE_GENERATION_MODE` unset or `prompt` | Emits `image_prompt:` in article frontmatter; user generates image manually via ChatGPT UI / Midjourney before merging PR | $0.00 |
| API (opt-in) | `IMAGE_GENERATION_MODE=api` | Calls DALL-E 3 via `generate_featured_image()`; saves PNG to `output/images/` | ~$0.08/image |

### Manual Generation Steps (Prompt-Only Mode)

1. Pipeline produces article PR with `image_prompt: \|` block in frontmatter and `image: /assets/images/pending-generation.svg`.
2. Copy the `image_prompt:` value from frontmatter.
3. Paste into ChatGPT UI (or Midjourney, etc.) to generate the image.
4. Save the generated image to `assets/images/<slug>.png`.
5. Update the frontmatter `image:` field to point to the new asset.
6. Remove the `image_prompt:` field (optional — informational only).
7. Merge the PR.

## Core Process

### Featured Image Generation (Prompt-Only — ADR-0009 default)

```
1. Read article title, thesis, and tone
   ↓
2. Construct editorial prompt using template below
   ↓
3. Emit prompt in frontmatter as `image_prompt: |` block
   ↓
4. Set frontmatter `image:` to /assets/images/pending-generation.svg
   ↓
5. User pastes prompt into ChatGPT UI / Midjourney to generate image
   ↓
6. User verifies: no text, human element, Economist palette,
   then replaces placeholder with uploaded asset before merge
```

### Featured Image Generation (API — opt-in)

```
1. Set IMAGE_GENERATION_MODE=api
   ↓
2. Read article title, thesis, and tone
   ↓
3. Construct DALL-E 3 prompt using template below
   ↓
4. Generate at 1792x1024 (landscape, HD)
   ↓
5. Verify: no text in image, human element present, Economist palette
   ↓
6. Save to assets/images/ and set frontmatter image field
```

### Chart Generation

```
1. Identify if article is data-driven (quantitative trends → YES)
   ↓
2. Select chart type by data shape (see table below)
   ↓
3. Apply Economist chart style: navy primary, minimal grid, inline labels
   ↓
4. Embed in article body with natural text reference
```

### DALL-E 3 Prompt Template

```
Create an editorial illustration in the style of The Economist magazine's
bold, graphic cover art and editorial imagery.

STYLE: Bold, high-contrast graphic editorial illustration.
Strong geometric compositions with confident lines and shapes.
Conceptual metaphor: human figures or symbolic objects representing ideas.
NOT watercolour, NOT oil painting, NOT photorealism, NOT soft brushstrokes.

SCENE: [Describe a specific scene that embodies the article's argument.
Include at least one human figure. Use a minimal or abstract background.]

COLOUR: Bold, limited palette. Economist red (#E3120B) accent.
Strong blues, navy, high-contrast darks. Colour blocking.
Clean white or off-white background.

MOOD: [Satirical / contemplative / urgent / ironic — match the article's tone]

COMPOSITION: Strong geometric composition with clear visual hierarchy.
Clear dominant foreground subject. Minimal background.
Use scale exaggeration to make the editorial point.
Generous negative space on one side for text overlay.

CRITICAL: No text, words, letters, numbers, or symbols anywhere in the image.
```

### Colour Palette

| Purpose | Colours |
|---------|---------|
| Primary accent | Economist red (#E3120B) |
| Strong blues | #3b6d8f, #17648d, navy |
| High-contrast darks | Charcoal (#333333), deep navy (#1a1a2e) |
| Accent | Dusty red (#a34054), ochre (#c4953a) |
| Background | White, off-white (#f4f0e6), flat colour blocks |

### Chart Type Selection

| Data Shape | Chart Type | Never |
|-----------|-----------|-------|
| Time series | Line chart | — |
| Comparison | Horizontal bar chart | — |
| Composition | Stacked bar or treemap | Pie charts |
| Correlation | Scatter plot | — |
| Any | — | 3D effects, radar charts, pie charts |

### Chart Style

- Navy (#17648d) primary, burgundy (#843844) accent
- Horizontal grid lines only, no vertical grid
- Inline labels, not separate legend box
- Small source attribution at bottom
- White background, clean and uncluttered

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "The minimalist vector style is clean" | It looks like a tech blog, not The Economist — editorial quality requires bold compositions with human figures |
| "We don't need a human in every image" | Humans make illustrations relatable; without them, images feel cold and generic |
| "Just use the default DALL-E style" | Default DALL-E produces photorealistic or painterly output; editorial illustration requires deliberate style constraints |
| "Charts are optional" | For data-driven articles, an unreferenced chart is a missed opportunity; no chart at all loses visual engagement score |
| "Any colour palette works" | Brand-consistent palette (Economist red, navy, high contrast) is what separates editorial from clip art |

## Red Flags

- Image contains text, letters, numbers, or labels (DALL-E text artifacts)
- No human element in the featured image (silhouette, hands, figure)
- Flat minimalist vectors or icon-like simplicity instead of editorial composition
- Chart uses pie chart, 3D effects, or radar chart
- Chart has no source attribution at bottom
- Chart embedded in article but not referenced in prose ("As the chart shows...")
- Image generated at wrong aspect ratio (should be 1792x1024)

## Verification

- [ ] Featured image present in frontmatter `image:` field — **evidence**: YAML field exists and file exists on disk
- [ ] Image contains human element — **evidence**: visual inspection
- [ ] Zero text artifacts in image — **evidence**: visual inspection
- [ ] Image uses Economist colour palette — **evidence**: dominant colours match palette table
- [ ] If data-driven article: chart embedded and referenced in prose — **evidence**: `![` syntax present and surrounding text references it
- [ ] Chart follows style rules (navy primary, no 3D, inline labels) — **evidence**: visual inspection

### Integration Points

- `scripts/featured_image_agent.py` — DALL-E prompt uses this template
- `src/crews/stage3_crew.py` — graphics task references chart standards
- `scripts/article_evaluator.py` — visual engagement dimension scoring
