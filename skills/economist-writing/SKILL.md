---
name: economist-writing
description: Define the writing standard for every article in the content pipeline. Use when configuring the Writer Agent, when reviewing article prose quality, when tuning the deterministic polish stage.
---

# Economist Writing Style

## Overview

The definitive reference for the Stage 3 Writer Agent, Stage 4 Editorial Reviewer, and Article Evaluator. Every article must meet these standards before publication. The gold standard is editorial prose combining data-driven reporting with sharp, opinionated analysis in a confident, conversational tone.

## When to Use

- Configuring or updating the Writer Agent system prompt
- Reviewing article quality during Stage 4 editorial review
- Tuning deterministic polish rules for banned patterns
- Evaluating opening, voice, and structure scoring dimensions

### When NOT to Use

- For source freshness and diversity — that's `research-sourcing`
- For visual standards — that's `editorial-illustration`
- For article scoring mechanics — that's `article-evaluation`
- For defect pattern codification — that's `defect-prevention`

## Core Process: The 10 Rules

### 1. Open with a striking, concrete claim
First sentence must make the reader stop — specific fact, surprising statistic, or provocative assertion.

**Banned openings:** "In today's world", "It's no secret", "The arrival/emergence/rise of", "When it comes to", "Amidst", any sentence starting with "The" + abstract noun.

### 2. Argue a thesis, not a topic
Every article must have a **specific, debatable argument** stated in the first two paragraphs. "AI tools overpromise" is a topic. "AI test generators make maintenance worse because they optimise for coverage metrics that don't correlate with quality" is a thesis.

### 3. Never use numbered or bulleted lists in prose
Lists belong in infographics, not editorial writing. Each point argued in its own paragraph with transitions.

### 4. Write with authority, not hedging
**Banned:** "it would be misguided", "one might", "it is worth noting", "it should be noted", "it is important to", "further complicating matters", "invites closer scrutiny", "in practical terms".

### 5. Name names — use real companies and people
At least 2 named companies or individuals with specific anecdotes. **Banned generic attributions:** "organisations", "professionals", "studies show", "experts say", "research indicates".

### 6. Cut ruthlessly — no padding
Remove: throat-clearing ("It goes without saying"), redundant attribution ("As mentioned earlier"), weak intensifiers ("very", "quite", "rather", "fairly").

### 7. End with a vivid prediction or provocation
**Banned closings:** "will rest on" / "depends on" / "the key is", "In conclusion" / "To summarise", "Only time will tell", "remains to be seen".

### 8. Use 3-4 headings maximum
One heading per 250-350 words. Headings should be **noun phrases that advance the argument**, not questions or descriptions.

### 9. Integrate data, don't catalogue it
Make the claim first, attribute second. Never start a sentence with a source name + reporting verb.

### 10. Title must be provocative and memorable
Use a colon to add a surprising twist. **Banned:** starting with "Why"/"How", starting with "The Impact/Role of", longer than 10 words without a twist.

### Length and Density

- **Minimum:** 600 words
- **Sweet spot:** 700-1000 words
- **Maximum:** 1200 words
- Every paragraph must advance the argument — if removing it doesn't weaken the thesis, cut it.

### Voice Reference

The Economist voice is: **confident** (states opinions as observations), **witty** (dry humour, understated irony), **British** (organisation, analyse, colour), **active** ("Companies are racing" not "it is being observed"), **conversational** (brilliant dinner companion, not textbook), **precise** (every word chosen deliberately).

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Lists make content more scannable" | Scannable is for blog posts; editorial prose argues through connected paragraphs |
| "We need to hedge to be accurate" | Hedging signals uncertainty; The Economist states opinions as observations and lets the evidence do the qualifying |
| "The opening needs context before the hook" | Context is throat-clearing; the hook IS the context — a striking fact frames the whole piece |
| "Longer articles are more thorough" | Density beats length; a tight 700-word argument outperforms a padded 1200-word survey |
| "Generic attribution is safer" | It's lazier — "Microsoft's testing team found" is both more credible and more engaging than "organisations report" |
| "Summary endings are expected" | Expected by whom? The reader already knows the thesis; end with a provocation that extends the argument |

## Red Flags

- Article opens with an abstract noun ("The emergence of", "The rise of")
- Bulleted or numbered lists appear in prose body (outside References)
- Hedging phrases: "it is worth noting", "one might argue"
- Generic attribution: "studies show", "experts say", "organisations"
- More than 4 headings in a 1000-word article
- Sentence starts with a source name + reporting verb ("Gartner found...")
- Ending summarises instead of provoking
- American spellings (organization, analyze, color)
- Exclamation points anywhere in the article

## Verification

- [ ] First sentence contains a striking fact or statistic — **evidence**: data-bearing token (number, percentage, currency) in sentence 1
- [ ] Debatable thesis stated in first two paragraphs — **evidence**: can be phrased as "The article argues that..."
- [ ] Zero bulleted/numbered lists in prose body — **evidence**: regex `^[-*\d+\.]` returns no matches outside References
- [ ] Zero banned opening/hedging/closing patterns — **evidence**: regex scan against all banned pattern lists
- [ ] At least 2 named companies or individuals — **evidence**: proper noun count ≥2
- [ ] Word count 600-1200 — **evidence**: `wc -w` on body after frontmatter
- [ ] British spelling throughout — **evidence**: spellcheck against American→British dictionary
- [ ] 3-4 headings maximum — **evidence**: `##` count ≤4

### Integration Points

- **Stage 3 Writer Agent** — primary consumer of this skill
- **Stage 4 Editorial Reviewer** — evaluates against these rules
- **Article Evaluator** — scores opening, voice, structure
- **Deterministic Polish** — strips banned phrases listed here
- **Editorial Judge** — post-deployment check against writing quality
