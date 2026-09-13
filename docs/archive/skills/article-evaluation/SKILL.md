---
name: article-evaluation
description: Score articles on 5 quality dimensions with deterministic metrics and persist for trend tracking. Use when evaluating a generated article, when tuning scoring rubrics, when adding a new quality dimension.
---

# Article Evaluation

## Overview

Scores every generated article on 5 quality dimensions (opening, evidence, voice, structure, visuals) using deterministic checks. Persists scores to JSON for trend analysis via the observability dashboard.

## When to Use

- After Stage 4 quality gate to score the article (pass or revision)
- After deployment via the editorial judge for deployed-article scoring
- When tuning scoring rubrics or adjusting dimension weights
- When adding a new quality dimension to the evaluation

### When NOT to Use

- For trend analysis across articles over time — that's `observability`
- For codifying recurring failure patterns as rules — that's `defect-prevention`
- For checking source freshness or diversity — that's `research-sourcing`

## Core Process

```
1. Receive article text + metadata from pipeline
   ↓
2. Score each of 5 dimensions (1-10) using deterministic checks
   ↓
3. Compute total (max 50) and percentage
   ↓
4. Generate per-dimension detail strings explaining the score
   ↓
5. Append evaluation record to logs/article_evals.json
   ↓
6. Return scores to caller (quality gate or editorial judge)
```

### Scoring Dimensions

| Dimension | 10 (Excellent) | 7-9 (Good) | 4-6 (Acceptable) | 1-3 (Poor) |
|-----------|---------------|------------|-------------------|------------|
| **Opening Quality** | Striking data in first sentence, zero banned patterns | Good hook, not data-led | Generic but not banned | Contains banned opening |
| **Evidence Sourcing** | All stats sourced, ≥5 refs, zero placeholders | All sourced, 3-4 refs | Some unsourced stats | Multiple unsourced or no refs section |
| **Voice Consistency** | Zero American spellings, banned phrases, exclamation points | 1-2 minor American spellings | Mixed spelling or 1 banned phrase | Multiple banned phrases |
| **Structure** | All frontmatter, 3+ headings, 800-1200 words, refs, strong ending | Missing 1 optional field or 1200-1500 words | Missing required field or <800 words | No frontmatter or <500 words |
| **Visual Engagement** | Image, chart embedded and referenced, visual breaks | Image + chart but not referenced naturally | Image missing or chart not embedded | No image, no chart, wall of text |

### Implementation Approach

All scoring is deterministic — regex, dictionary lookups, and counting. No LLM calls.

| Dimension | Technique | Reusable Code |
|-----------|-----------|---------------|
| Opening | Regex banned patterns, count data tokens in first sentence | `stage4_crew._BANNED_PHRASES` |
| Evidence | Regex for placeholders, count References items, scan vague attribution | `publication_validator.py` |
| Voice | Dictionary lookup American→British spelling, regex banned phrases | `stage4_crew._BRITISH_SPELLING` |
| Structure | `FrontmatterSchema.validate_article()`, regex headings, word count | `frontmatter_schema.py` |
| Visuals | Check `image:` frontmatter, regex `![` syntax, heading distribution | `editorial_judge.py` |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "The quality gate already checks this" | The gate makes a pass/fail decision; evaluation provides granular scores for trend analysis |
| "LLM-based evaluation would be more nuanced" | LLM scores are non-deterministic and can't be compared across runs; deterministic scoring enables trends |
| "5 dimensions is too few" | Start with 5 measurable dimensions; add more when you have data showing gaps |
| "Scoring is subjective" | These rubrics are deliberately mechanical — regex matches and counts, not taste |

## Red Flags

- Evaluation uses LLM calls instead of deterministic checks
- Scores not persisted to `logs/article_evals.json` after each run
- Missing dimension detail strings (scores without explanations are unauditable)
- Same article evaluated multiple times without dedup (inflates trend data)
- Scoring rubric drifts from what the code actually checks

## Verification

- [ ] All 5 dimensions scored for every article — **evidence**: no null scores in `logs/article_evals.json`
- [ ] Total score = sum of dimensions, max 50 — **evidence**: arithmetic check on latest entry
- [ ] Detail strings present for every dimension — **evidence**: no empty `details` fields
- [ ] Evaluation appended (not overwritten) to log file — **evidence**: file length grows monotonically
- [ ] Uses `orjson` for serialization — **evidence**: import check in evaluator module

### Output Schema

```json
{
  "article_filename": "2026-04-04-article-slug.md",
  "timestamp": "2026-04-04T12:00:00Z",
  "scores": {
    "opening_quality": 8,
    "evidence_sourcing": 9,
    "voice_consistency": 10,
    "structure": 9,
    "visual_engagement": 7
  },
  "total_score": 43,
  "max_score": 50,
  "percentage": 86,
  "details": {
    "opening_quality": "Strong data hook in first sentence",
    "evidence_sourcing": "7 references cited, all stats sourced",
    "voice_consistency": "British spelling consistent, no banned phrases",
    "structure": "4 headings, 1138 words, references present",
    "visual_engagement": "Image present, no chart embedded"
  }
}
```

### Integration Points

- Called after Stage 4 quality gate in `flow.py`
- Called by editorial judge post-deployment
- Scores feed into observability dashboard for trend analysis
- `scripts/publication_validator.py` — banned phrases, word count, references
- `scripts/editorial_judge.py` — frontmatter, image, categories, structure
- `scripts/frontmatter_schema.py` — schema validation
