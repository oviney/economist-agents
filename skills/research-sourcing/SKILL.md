# Research Sourcing Skill

## Purpose
Define the research standard for every article.  The Research Agent
must find current, authoritative, and diverse sources — not recycled
analyst reports from 2-3 years ago.

## The Problem
The pipeline consistently produces articles citing the same stale
sources: Capgemini World Quality Report 2023, Forrester 2023, Gartner
2023.  These are fine reports but they are years old and the same ones
appear in every article.  A reader who reads 3 blog posts sees the
same citations repeated — destroying credibility.

## Source Freshness Requirements

### Mandatory
- **At least 3 of 5 references must be from the current year or
  previous year** (e.g., 2025-2026 for articles written in 2026)
- **No more than 1 reference older than 2 years**
- **Zero references older than 5 years** unless citing a foundational
  study that established a field

### Source Types (Diversify)
Each article should include at least 3 of these 5 source types:
1. **Primary research** — survey data, empirical studies, original
   analysis (not a report summarising someone else's research)
2. **Named company case study** — specific outcomes at a named
   organisation with measurable results
3. **Academic/conference paper** — IEEE, ACM, arXiv, conference
   proceedings from the past 2 years
4. **Industry practitioner content** — engineering blog posts from
   Netflix, Google, Spotify, Microsoft, etc.
5. **Analyst report** — Gartner, Forrester, McKinsey, BCG (max 1
   per article to avoid over-reliance)

### Banned Source Patterns
- "Studies show" without naming the study
- "Experts say" without naming the expert
- "Research indicates" without citing the specific paper
- "According to a recent report" without naming the report or year
- Citing the same report in more than 2 articles across the blog

## Source Discovery

### Where to Find Fresh Sources
- **arXiv** (arxiv.org) — preprints in software engineering, AI, testing
- **Google Scholar** — filter by year for recent papers
- **Company engineering blogs** — Netflix, Google, Meta, Stripe, Spotify,
  Shopify, GitHub publish testing and quality research regularly
- **Conference proceedings** — ICSE, ISSTA, ASE, STARWEST, Agile Testing
  Days
- **Government/standards bodies** — NIST, ISO, IEEE standards updates
- **Venture capital reports** — CB Insights, Crunchbase for market data

### arXiv Integration
The pipeline already has `scripts/arxiv_search.py` for searching arXiv.
The Research Agent should use this tool to find papers from the past
12 months on the article's topic.  arXiv papers provide cutting-edge
data that analyst reports lag by 6-12 months.

## Verification Requirements

Every cited statistic must include:
- **Who** collected the data (named organisation)
- **When** (year, ideally month)
- **How** (survey of N respondents, analysis of N projects, etc.)
- **What** (the specific finding, with numbers)

Example of GOOD attribution:
"Capgemini surveyed 1,750 technology leaders across 32 countries in
its 2024 Quality Engineering Report and found that 42% of QA budgets
were consumed by test automation maintenance."

Example of BAD attribution:
"According to industry research, a significant portion of QA budgets
goes to automation maintenance."

## Integration Points

- **Stage 3 Research Agent** (`src/crews/stage3_crew.py`) — primary
  consumer of this skill.  Backstory should reference these rules.
- **Article Evaluator** (`scripts/article_evaluator.py`) — evidence
  sourcing dimension should check source freshness
- **arXiv search** (`scripts/arxiv_search.py`) — tool for discovering
  recent academic sources
- **Editorial Judge** (`scripts/editorial_judge.py`) — post-deployment
  check for source diversity

## Anti-Patterns

1. **The Capgemini Crutch** — citing the World Quality Report in every
   article.  It's a good report; it's not the only report.
2. **The Year-Old Survey** — using 2023 data in 2026 articles without
   acknowledging the age or checking for updates
3. **The Vendor Cite** — citing a vendor's own research to support
   claims about that vendor's product category
4. **The Missing Method** — quoting a percentage without explaining
   how it was measured or who measured it
5. **The Recycled Reference** — same 5 sources appearing across
   multiple blog posts
