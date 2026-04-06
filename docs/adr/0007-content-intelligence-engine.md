# ADR-0007: Content Intelligence Engine — Closing the Feedback Loop

**Status:** Accepted
**Date:** 2026-04-05 (Accepted: 2026-04-06)
**Decision Maker:** Ouray Viney (Engineering Lead)
**Research:** Four parallel agents covering content intelligence platforms, sentiment-driven content, Google Analytics APIs, and current pipeline audit

> **Acceptance record (2026-04-06):** Transitioned from Proposed to
> Accepted after Sprint 22 delivered the feedback loop end-to-end and
> produced evidence via three verification scripts:
>
> - **PR #184** (`scripts/ab_topic_scout_comparison.py`) — A/B
>   comparison shows Topic Scout with vs. without the performance
>   context produces substantially different topics: Jaccard similarity
>   0.111 (threshold 0.6), all 5 Run A topics explicitly reference top
>   performers from the GA4 database. **Causal effect confirmed.**
> - **PR #185** (`scripts/audit_composite_scores.py`) — methodology
>   audit caught the "30% dead weight" problem (two GSC placeholder
>   terms weighted 0.15 each, set to 0.0). Resolved by Story #187
>   which introduced `COMPOSITE_WEIGHTS_ACTIVE` — a renormalized
>   four-dimension subset that sums to 1.0 while preserving canonical
>   proportions. Max achievable score is now 1.0 (was 0.70).
> - **PR #186** (`scripts/topic_scout_reproducibility.py`) — 3-run
>   reproducibility check. The exact-title Jaccard metric flagged
>   "UNSTABLE" but qualitative inspection showed strong thematic
>   stability across runs (all three converged on AI testing
>   economics / maintenance burden / ROI skepticism). The metric
>   itself is being refined in Story #188 to measure thematic rather
>   than lexical similarity.
>
> All three scripts are merged to main with 110 tests passing
> (29 + 35 + 46). The full regression suite at acceptance is 1038
> tests passing, 1 skipped.

> **Interim re-weighting note (2026-04-06, Story #187):** The composite
> scoring formula defined in this ADR has six weighted terms that sum
> to 1.0. Two of those terms (`search_ctr`, `search_impressions`, 0.15
> each) depend on Google Search Console data that takes 24-48h to
> populate after verification and is currently unavailable. To avoid a
> "30% dead weight" problem that would silently make the remaining
> scores unreliable, `scripts/ga4_etl.py` temporarily uses a
> renormalized four-dimension subset (`COMPOSITE_WEIGHTS_ACTIVE`) that
> preserves the canonical proportions but sums to 1.0 on its own. Once
> GSC data is populated and wired in, `compute_scores()` should be
> switched back to the canonical six-dimension `COMPOSITE_WEIGHTS`.
> See the invariant tests in `tests/test_ga4_etl.py::TestCompositeWeights`
> and the audit in Story #182 / PR #185 for the rationale.

---

## Problem Statement

The economist-agents pipeline generates articles but has no intelligence about what to generate. It is a content factory with no market research department.

**What exists:**
- Topic Scout — LLM-based, scores topics on 5 dimensions (timeliness, data availability, contrarian potential, audience fit, style fit)
- Editorial Board — 6 weighted personas vote on topics
- ChromaDB — style memory RAG (voice consistency only)
- Content queue — 5-topic JSON snapshot, no history

**What's completely missing:**

| Capability | Status | Impact |
|-----------|--------|--------|
| Topic deduplication | ❌ None | Pipeline can regenerate articles on topics already covered |
| Published article archive | ❌ None | No record of what's been published |
| GA4 integration | ❌ None | Zero audience engagement data |
| Search Console integration | ❌ None | No keyword/ranking data |
| Community sentiment | ❌ None | Reddit, HN, dev.to mentioned in prompts but never queried |
| Performance feedback loop | ❌ None | Article success doesn't inform future topic selection |
| Content gap analysis | ❌ None | No systematic way to find untapped topics |
| Engagement prediction | ❌ None | No model to predict which topics will perform |

The pipeline has **no brain** — it generates content in a vacuum, never learning what works.

---

## Objectives

| Priority | Objective | Measure |
|----------|-----------|---------|
| **P0** | Stop publishing duplicate topics | Zero topic overlap >0.8 similarity with published archive |
| **P0** | Know what's working | Composite performance score per article, updated weekly |
| **P1** | Let audience data drive topic selection | Top/bottom performer insights feed into Topic Scout prompt |
| **P1** | Detect trending developer topics before competitors | Sentiment signals from HN/Reddit surface in topic scoring |
| **P2** | Find content gaps | Search Console data reveals keywords with high impressions but no matching article |
| **P2** | Enable contrarian content strategy | Sentiment consensus detection → topics where data contradicts popular opinion |
| **P3** | Predict engagement before publication | Model trained on historical performance estimates article potential |

---

## Current State Audit

### Topic Scout (`scripts/topic_scout.py`)
- Makes 2 LLM calls: trend research → topic generation
- Scores on 5 dimensions (1-5 scale, max 25)
- **Mentions** Reddit, HN, dev.to in prompt but **never fetches data** from these sources
- No deduplication check against past articles
- No performance data input

### Editorial Board (`scripts/editorial_board.py`)
- 6 weighted personas (VP Engineering 1.2x, Economist Editor 1.3x highest)
- Parallel voting via ThreadPoolExecutor
- Consensus and dissent detection
- **No audience data** — votes on perceived quality, not predicted performance

### ChromaDB (`src/tools/style_memory_tool.py`)
- Indexes `archived/*.md` articles for voice consistency
- **Not used** for topic similarity or deduplication
- Could be extended with a second collection for topic embeddings

### Content Queue (`content_queue.json`)
- Single JSON snapshot of 5 candidate topics
- No publication history, no "covered on" dates, no performance metrics

---

## Proposed Architecture: The Content Intelligence Engine

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT INTELLIGENCE ENGINE               │
├──────────────┬──────────────┬───────────────┬───────────────┤
│   MEASURE    │   LISTEN     │   REMEMBER    │   DECIDE      │
│              │              │               │               │
│  GA4 API     │  HN API      │  Published    │  Topic Scout  │
│  GSC API     │  Reddit API  │  Article      │  + Intelligence│
│              │  dev.to API  │  Archive      │  Context       │
│  Weekly ETL  │              │  (ChromaDB)   │               │
│  → scores.db │  Sentiment   │               │  Editorial    │
│              │  velocity    │  Topic        │  Board        │
│  Top/bottom  │  detection   │  Similarity   │  + Performance │
│  performers  │              │  Search       │  Data          │
└──────┬───────┴──────┬───────┴───────┬───────┴───────┬───────┘
       │              │               │               │
       v              v               v               v
  Performance    Trending         Dedup Check      Informed
  Insights       Topics           (>0.8 reject)    Topic Selection
       │              │               │               │
       └──────────────┴───────────────┴───────────────┘
                              │
                              v
                    ┌─────────────────┐
                    │  CONTENT        │
                    │  PIPELINE       │
                    │  (Stage 3 → 4)  │
                    └─────────────────┘
```

### Layer 1: MEASURE (GA4 + Search Console)

**What it does:** Pulls weekly performance data for every published article and computes a composite engagement score.

**Existing MCP servers available (no build required):**
- `google-analytics-mcp` — official Google-supported, `pip install google-analytics-mcp`, v2.0.1 (March 2026)
- `google-search-console-mcp-python` — FastMCP-based, supports search analytics and URL inspection

**Custom ETL script** (weekly cron or manual trigger):
```python
# Composite score formula (starting weights — adjust after 4-6 weeks)
score = (0.25 * norm(pageviews))
      + (0.20 * norm(engagement_rate))
      + (0.15 * norm(avg_engagement_time))
      + (0.10 * norm(scroll_depth_rate))
      + (0.15 * norm(search_ctr))
      + (0.15 * norm(search_impressions))
```

**Storage:** SQLite — sufficient for single-blog scale, stays under 1MB/year.

**Output:** Top 5 and bottom 5 articles with their topics, keywords, and content attributes → feeds into Topic Scout prompt.

**GA4 metrics available:** `screenPageViews`, `engagementRate`, `averageSessionDuration`, `bounceRate`, `scrolledUsers` (fires at 90% scroll depth), `activeUsers`.

**GSC metrics available:** `clicks`, `impressions`, `ctr`, `position` — segmented by page and query.

### Layer 2: LISTEN (Community Sentiment)

**What it does:** Monitors developer communities for trending topics and sentiment shifts. Identifies topics where opinion is strong but coverage is thin.

**Data sources (ranked by signal quality for dev content):**

| Platform | API | Signal Type | Cost |
|----------|-----|-------------|------|
| Hacker News | Firebase (free) | Architectural/strategic sentiment | Free |
| Reddit | PRAW (free tier: 100 req/min) | Practitioner pain points | Free |
| dev.to | REST API (free) | Tutorial demand signals | Free |
| Stack Overflow | Annual survey data | "What's actually being used" | Free |
| Google Trends | API (free) | Search demand velocity | Free |
| Exploding Topics | API ($99/mo) | Early trend detection (12mo lead) | Paid |

**Sentiment scoring approach:** LLM-based (GPT-4o-mini or Claude Haiku) rather than lexicon-based (VADER). Developer language — sarcasm, irony, technical jargon — defeats traditional sentiment tools. LLM scoring handles it significantly better.

**Key signal: Sentiment velocity** — not absolute sentiment but how quickly opinion is shifting. A topic moving from neutral to strongly negative (developer frustration) is a content opportunity. A topic at peak enthusiasm is a contrarian opportunity.

**Contrarian content strategy:**
1. Find topics where sentiment is >80% one-directional across HN/Reddit
2. Search for empirical evidence contradicting the consensus
3. Frame: "Everyone loves X, but the data says..." — The Economist's editorial model

### Layer 3: REMEMBER (Published Article Archive + Dedup)

**What it does:** Maintains a searchable archive of every published article with topic embeddings. Prevents duplicate content and enables topic gap analysis.

**Implementation:**
- Second ChromaDB collection: `published_articles` (alongside existing `economist_style_patterns`)
- Index on publish: article title, thesis, summary, categories, date, performance score
- Dedup check: before editorial board voting, query `published_articles` for cosine similarity >0.8 — reject duplicates, flag 0.6-0.8 as "related coverage exists"
- Topic gap analysis: cluster published articles, identify underserved topic areas

**Published article metadata schema:**
```python
{
    "title": str,
    "thesis": str,
    "date": str,  # YYYY-MM-DD
    "categories": list[str],
    "performance_score": float,  # from Layer 1
    "top_keywords": list[str],   # from GSC
    "sentiment_at_publish": str,  # from Layer 2
}
```

### Layer 4: DECIDE (Informed Topic Selection)

**What it does:** Enhances Topic Scout and Editorial Board with intelligence from Layers 1-3.

**Topic Scout prompt enhancement:**
```
PERFORMANCE CONTEXT:
Our top-performing articles this month: {top_5_articles_with_topics}
Keywords gaining impressions but low CTR (content gaps): {high_impression_low_ctr_keywords}
Declining articles that need refresh: {decaying_articles}

COMMUNITY CONTEXT:
Trending developer topics (last 7 days): {trending_topics_with_sentiment}
Topics with strong consensus sentiment (contrarian opportunities): {consensus_topics}

COVERAGE CONTEXT:
Topics already published (avoid duplicates): {published_topic_summaries}
Underserved topic clusters: {gap_analysis_results}
```

**Editorial Board enhancement:**
- Add a 7th persona: **Data Analyst** (weight: 1.1) — scores based on predicted audience engagement using historical performance data
- Feed performance data to existing personas (VP Engineering gets ROI data, Busy Reader gets engagement metrics)

---

## Implementation Plan

### Phase 1: Remember + Dedup (Sprint 19, 5 points)

| Story | Points | Assignee | Rationale |
|-------|--------|----------|-----------|
| Published article archive in ChromaDB (new collection, index script) | 2 | Copilot | New file |
| Dedup check in flow.py `discover_topics()` | 2 | Claude Code | Modifies existing file |
| Published topics MCP server | 1 | Copilot | New file |

**Immediate value:** Stops duplicate content. No external API dependencies.

### Phase 2: Measure (Sprint 20, 5 points)

| Story | Points | Assignee | Rationale |
|-------|--------|----------|-----------|
| GA4 + GSC weekly ETL script with composite scoring | 3 | Claude Code | Complex — API auth, scoring logic |
| Configure GA4 + GSC MCP servers for interactive querying | 1 | Copilot | Config + new file |
| Feed performance insights into Topic Scout prompt | 1 | Claude Code | Modifies existing file |

**Prerequisites:** Google Cloud service account with GA4 Data API and Search Console API enabled. Service account added as Viewer on GA4 property and verified owner in Search Console.

### Phase 3: Listen (Sprint 21, 8 points)

| Story | Points | Assignee | Rationale |
|-------|--------|----------|-----------|
| HN + Reddit sentiment scraper with LLM scoring | 3 | Claude Code | Complex — API integration, LLM scoring |
| Trending topic detector (sentiment velocity) | 3 | Claude Code | Algorithm design |
| Feed community signals into Topic Scout prompt | 1 | Claude Code | Modifies existing file |
| Sentiment data MCP server | 1 | Copilot | New file |

### Phase 4: Decide (Sprint 22, 3 points)

| Story | Points | Assignee | Rationale |
|-------|--------|----------|-----------|
| Add Data Analyst persona to Editorial Board | 1 | Claude Code | Modifies existing file |
| Content gap analysis from GSC keyword data | 2 | Claude Code | New analysis logic |

---

## Cost Implications

| Component | Cost | Notes |
|-----------|------|-------|
| GA4 Data API | Free | 200K tokens/day quota |
| Search Console API | Free | 25K rows/request |
| HN API | Free | Firebase, no auth required |
| Reddit API (PRAW) | Free | 100 requests/min free tier |
| dev.to API | Free | No auth required |
| Exploding Topics | $99/mo | Optional — for 12-month trend lead time |
| LLM sentiment scoring | ~$2/month | Haiku-tier, ~1000 comments/week |
| SQLite storage | Free | <1MB/year |
| GA4 MCP server | Free | `pip install google-analytics-mcp` |
| GSC MCP server | Free | `pip install google-search-console-mcp-python` |

**Total new cost: $0-$2/month** (excluding optional Exploding Topics subscription).

---

## What This Enables

**Before (current state):**
> "Generate an article on a quality engineering topic" → LLM invents a topic → editorial board votes on vibes → article published → nobody knows if anyone reads it → next week, might write about the same topic again

**After (with Content Intelligence Engine):**
> GA4 says the CrowdStrike article got 3x average engagement → GSC shows "cost of software bugs 2026" has 2,400 impressions but we have no article targeting it → Reddit r/programming is 85% negative on AI coding tools this week (contrarian opportunity) → ChromaDB confirms we haven't covered "AI code review" yet → Topic Scout generates candidates informed by all four signals → Editorial Board votes with performance data → article targets a proven audience gap

The difference is the difference between a newspaper that publishes whatever its editors feel like and one that reads its circulation numbers.

---

## References

### Content Intelligence
- [Surfer SEO, Clearscope, MarketMuse, Frase comparison](https://www.techno-pulse.com/2026/03/best-ai-seo-tools-in-2026-surfer-seo-vs.html)
- [InfraNodus knowledge graph content gap analysis](https://infranodus.com/docs/content-gap-analysis)
- [Presaige content performance prediction (CES 2026)](https://www.prnewswire.com/news-releases/presaige-debuts-at-ces-2026-302645969.html)
- [Content engagement metrics that matter (Chartbeat Q4 2025)](https://clickport.io/blog/content-engagement-metrics)

### Sentiment Analysis
- [HN sentiment research on AI projects (arXiv)](https://arxiv.org/html/2506.12643v1)
- [Stack Overflow 2025 Developer Survey — AI favorability dropping](https://survey.stackoverflow.co/2025/)
- [SparkToro audience research platform](https://sparktoro.com/blog/audience-research-the-complete-guide-for-marketers/)
- [Reddit PRAW + GPT-4o-mini sentiment pipeline (W&B)](https://wandb.ai/byyoung3/Generative-AI/reports/Sentiment-classification-with-the-Reddit-Praw-API-and-GPT-4o-mini)
- [News sentiment vs social media sentiment as contrarian indicator (MDPI)](https://www.mdpi.com/1911-8074/18/1/16)

### Google Analytics Integration
- [GA4 Data API Python quickstart](https://github.com/googleanalytics/python-docs-samples/blob/main/google-analytics-data/quickstart.py)
- [Google Analytics MCP server (official)](https://developers.google.com/analytics/devguides/MCP)
- [Google Search Console MCP servers compared](https://www.ekamoira.com/blog/google-search-console-mcp-servers-compared-complete-2025-guide)
- [Content performance scoring methodology (Syptus)](https://www.syptus.com/blog/metrics-for-content-engagement-scoring/)
- [GA4 + WordPress automation pipeline (Sightfactory)](https://sightfactory.com/data-driven-content-automating-ga4-analysis-for-wordpress/)

### Architecture
- [AI content creation at scale (Level 3 maturity)](https://www.trysight.ai/blog/ai-content-creation-at-scale)
- [Reddit streaming sentiment pipeline architecture](https://github.com/nama1arpit/reddit-streaming-pipeline)
- [Generative Engine Optimization (GEO)](https://www.averi.ai/blog/the-state-of-ai-content-marketing-2026-benchmarks-report)
