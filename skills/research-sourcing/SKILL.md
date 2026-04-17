---
name: research-sourcing
description: Enforce source freshness, diversity, and attribution standards for article research. Use when configuring the Research Agent, when evaluating source quality in articles, when adding new source discovery integrations.
---

# Research Sourcing

## Overview

Defines the research standard for every article. The Research Agent must find current, authoritative, and diverse sources — not recycled analyst reports from years ago.

## When to Use

- Configuring or updating the Research Agent's source requirements
- Evaluating an article's evidence quality during review
- Adding a new source discovery tool (arXiv, Scholar, Serper)
- Diagnosing why articles keep citing the same stale sources

### When NOT to Use

- For article structure or voice issues — that's `economist-writing`
- For scoring articles quantitatively — that's `article-evaluation`
- For post-deployment source verification — that's `citation-verification` (future)

## Core Process

```
1. Research Agent receives topic from editorial board
   ↓
2. Search fresh sources: arXiv (past 12 months), Google Scholar, company blogs
   ↓
3. Apply freshness filter: ≥3/5 refs from current/previous year
   ↓
4. Apply diversity filter: ≥3 of 5 source types represented
   ↓
5. Verify each statistic has: WHO collected, WHEN, HOW, WHAT
   ↓
6. Pass sourced brief to Content Generation stage
```

### Freshness Requirements

- At least 3 of 5 references from current or previous year
- No more than 1 reference older than 2 years
- Zero references older than 5 years (unless foundational study)

### Source Type Diversity

Each article needs at least 3 of these 5 types:

1. **Primary research** — surveys, empirical studies, original analysis
2. **Named company case study** — specific outcomes with measurable results
3. **Academic/conference paper** — IEEE, ACM, arXiv from past 2 years
4. **Industry practitioner content** — engineering blogs from Netflix, Google, Spotify, etc.
5. **Analyst report** — Gartner, Forrester, McKinsey (max 1 per article)

### Banned Attribution Patterns

- "Studies show" without naming the study
- "Experts say" without naming the expert
- "Research indicates" without citing the paper
- "According to a recent report" without name or year
- Same report cited in more than 2 articles across the blog

### Source Discovery Tools

| Tool | Purpose | Enabled By |
|------|---------|-----------|
| `scripts/arxiv_search.py` | Academic preprints, past 12 months | Always available |
| `scripts/google_search.py` | Web + Scholar via Serper API | `SERPER_API_KEY` env var |
| `mcp_servers/web_researcher_server.py` | MCP tool for Scholar | `SERPER_API_KEY` env var |

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "The Capgemini report is the standard reference" | It's a good report, not the only report — readers who see it in every article lose trust |
| "2023 data is still relevant in 2026" | Markets move fast; 3-year-old data needs at minimum an "as of" qualifier |
| "We can't find fresh sources on this topic" | arXiv has preprints months ahead of analyst reports; company blogs publish weekly |
| "Analyst reports are the most credible" | Primary research and named case studies are more credible than vendor-commissioned surveys |
| "Adding source diversity slows down the pipeline" | The Research Agent searches in parallel; diversity is a filter, not an extra step |

## Red Flags

- Same 5 sources appearing across multiple articles
- All references from analyst reports (no primary research or practitioner content)
- Statistics cited without named source, year, or methodology
- References section has fewer than 3 entries
- `[NEEDS SOURCE]` or `[UNVERIFIED]` placeholders remaining in published article
- arXiv/Scholar search disabled because API key not configured

## Verification

- [ ] Article has ≥3 references from current/previous year — **evidence**: check publication dates in References section
- [ ] Article uses ≥3 of 5 source types — **evidence**: categorize each reference
- [ ] Zero banned attribution patterns — **evidence**: regex scan for "studies show", "experts say", etc.
- [ ] Every statistic has WHO, WHEN, HOW, WHAT — **evidence**: spot-check 3 statistics in article
- [ ] No `[NEEDS SOURCE]` or `[UNVERIFIED]` placeholders remain

### Integration Points

- `src/crews/stage3_crew.py` — Research Agent backstory references these rules
- `scripts/article_evaluator.py` — evidence sourcing dimension checks freshness
- `scripts/arxiv_search.py` — tool for discovering recent academic sources
- `scripts/editorial_judge.py` — post-deployment check for source diversity
