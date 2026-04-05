# Article Evaluation Skill

## Purpose
Score every generated article on 5 quality dimensions with deterministic
metrics.  Persist scores to JSON for trend tracking.  This is the nervous
system of the quality architecture — without evals there is no signal.

## Scoring Dimensions (1-10 each, total 50)

### 1. Opening Quality
**What to measure:**
- First sentence contains a striking fact or statistic (not throat-clearing)
- No banned openings: "In today's world", "It's no secret", "When it comes to", "Amidst"
- Opening paragraph has a clear hook within the first 30 words

**How to score:**
- 10: Striking data point in first sentence, zero banned patterns
- 7-9: Good hook but not data-led, or hook appears in second sentence
- 4-6: Generic opening but not banned
- 1-3: Contains banned opening pattern

**Implementation:** Regex match against banned patterns in first paragraph.
Count data-bearing tokens (numbers, percentages, currency) in first sentence.

### 2. Evidence Sourcing
**What to measure:**
- All statistics have named sources (not "studies show" or "experts say")
- No `[NEEDS SOURCE]` or `[UNVERIFIED]` placeholders remain
- References section exists with ≥3 numbered, cited sources

**How to score:**
- 10: All stats sourced, ≥5 references, zero placeholders
- 7-9: All stats sourced, 3-4 references, zero placeholders
- 4-6: Some unsourced stats, references present
- 1-3: Multiple unsourced stats or missing references section

**Implementation:** Regex for placeholder tags.  Count numbered items in
`## References` section.  Scan for vague attribution phrases.

### 3. Voice Consistency
**What to measure:**
- British spelling throughout (organisation, analyse, behaviour)
- No banned phrases: "game-changer", "paradigm shift", "leverage" (verb)
- Active voice dominant (no "is experiencing", "was determined")
- No exclamation points

**How to score:**
- 10: Zero American spellings, zero banned phrases, zero exclamation points
- 7-9: 1-2 minor American spellings, otherwise clean
- 4-6: Mixed spelling or 1 banned phrase
- 1-3: Multiple banned phrases or inconsistent voice

**Implementation:** Dictionary lookup for American→British spelling pairs
(same list as `stage4_crew._BRITISH_SPELLING`).  Regex for banned phrases
(same list as `stage4_crew._BANNED_PHRASES`).

### 4. Structure
**What to measure:**
- YAML frontmatter with all required fields (layout, title, date, categories, image)
- ≥2 markdown headings (## sections)
- 800-1500 words (body after frontmatter)
- References section present
- Ending is prediction/implication, not summary

**How to score:**
- 10: All frontmatter fields, 3+ headings, 800-1200 words, references, strong ending
- 7-9: Missing 1 optional field, or word count 1200-1500
- 4-6: Missing required field, or <800 words, or no references
- 1-3: No frontmatter, or <500 words, or no headings

**Implementation:** Reuse `FrontmatterSchema.validate_article()` for
frontmatter.  Regex count headings.  Word count.  Check for banned
closings in last 500 chars.

### 5. Visual Engagement
**What to measure:**
- Featured image field present and points to existing file
- Chart embedded in article body (if chart_data was generated)
- Chart referenced naturally in text ("As the chart shows...")
- Article has visual breaks (headings every 200-300 words)

**How to score:**
- 10: Image present, chart embedded and referenced, good visual breaks
- 7-9: Image present, chart embedded but not referenced naturally
- 4-6: Image missing or chart not embedded
- 1-3: No image, no chart, wall of text

**Implementation:** Check `image:` field in frontmatter.  Regex for
`![` markdown image syntax.  Measure paragraphs between headings.

## Output Schema

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

## Persistence

Append each evaluation to `logs/article_evals.json` as a JSON array.
Each entry is one article evaluation.  File grows over time for trend
analysis.  Use `orjson` for serialization.

## Existing Code to Reuse

- `scripts/publication_validator.py` — banned phrases, word count, references checks
- `scripts/editorial_judge.py` — frontmatter, image, categories, structure checks
- `scripts/frontmatter_schema.py` — schema validation
- `src/crews/stage4_crew.py` — `_BRITISH_SPELLING`, `_BANNED_PHRASES` dictionaries
- `scripts/agent_reviewer.py` — banned openings, banned closings lists

## Integration Points

- Called after Stage 4 quality gate in `flow.py` (whether published or revision)
- Called by editorial judge post-deployment for deployed article scoring
- Scores persisted for observability dashboard (Story #119)
