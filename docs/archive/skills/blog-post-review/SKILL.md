---
name: blog-post-review
description: Review a draft or published blog post for viney.ca before it ships, applying the empirical-skeptic editorial rubric. Use this skill whenever a post, article, draft, or piece of long-form content produced by the economist-agents pipeline needs review, critique, scoring, fact-checking, QA, or a publish/hold decision. Trigger it even when the user just says "look at this post", "is this any good", "check this draft", or pastes a URL or markdown file from the blog, and trigger it for any request to grade, gate, or sanity-check generated editorial content.
---

# Blog Post Review

Review generated editorial content against a fixed rubric so every post gets the same
scrutiny, and so the publish decision is reproducible rather than a matter of mood.

The audience for viney.ca is QE practitioners and enterprise IT buyers. The editorial
voice is the empirical skeptic. Both facts matter for how you review: this audience
checks numbers, and the brand's only real asset is that its claims hold up. A single
fabricated statistic does more damage than ten dull paragraphs.

## Why this rubric is shaped the way it is

AI content pipelines fail in predictable ways. They invent plausible statistics. They
cite a real source that does not actually support the claim being made. They build a
cost model whose arithmetic does not close. They produce consensus mush when a
multi-persona board averages away the sharp edges of an argument. They hedge every
conclusion until nothing falsifiable remains. The gates and weights below are aimed at
those specific failure modes, not at general writing quality.

## Workflow

1. **Acquire the text.** If given a URL, fetch it. If the fetch fails (viney.ca
   disallows automated access), say so plainly and ask for the markdown or pasted text.
   Never review from a title, a summary, or a guess about what the post probably says.
2. **Run the gates.** Five binary checks. Any failure blocks publication regardless of
   the weighted score.
3. **Score the six dimensions.** 0 to 5 each, then weight.
4. **Verify independently.** Re-derive every number. Attempt to resolve every source.
   For every load-bearing citation, check whether a newer edition supersedes it (G5).
   Search for the strongest published counter-evidence to the post's central claim.
5. **Write the report** in the required output format.
6. **Emit the machine-readable verdict block** so the pipeline can gate automatically.

Do the verification work yourself. Do not hand the author a list of things to go check.

## Gates (binary, blocking)

| ID | Gate | Fails when |
|----|------|-----------|
| G1 | Source resolvability | Any statistic, dollar figure, percentage, or named study lacks a source that can be resolved to a real, locatable document |
| G2 | Citation fidelity | A cited source exists but does not support the specific claim attached to it, or the claim overstates the source's scope, sample, or confidence |
| G3 | Arithmetic integrity | Any calculation, cost model, extrapolation, or per-unit figure does not reproduce when recomputed |
| G4 | No fabrication | Any quote, person, company anecdote, internal metric, or study appears to be invented, or cannot be distinguished from invention |
| G5 | Evidence currency | A load-bearing citation has been superseded by a newer edition from the same publisher that revises, reverses, or materially narrows the finding, and the post does not acknowledge the revision |

For G1 and G2, when a source cannot be reached, mark the claim **UNVERIFIED** and treat
it as a gate failure for publication purposes. Unverified is not the same as false, but
an empirical-skeptic blog cannot ship an unverified number. Say which it is.

For G3, show the recomputation. Do not assert that the math checks out; display the
arithmetic so the author can see it.

### G5, and why it is not the same check as source freshness

G5 exists because a post can pass G1 through G4 cleanly and still be wrong about the
current state of the evidence. For every claim the argument actually rests on, ask
whether the citing organisation has published a later edition, and whether that edition
still says what the post needs it to say. Annual reports are the common case: DORA,
Stack Overflow, JetBrains, Accelerate, and most vendor benchmark reports re-run yearly
and sometimes reverse themselves.

This is **not** covered by `research-sourcing`, which enforces freshness as a *ratio*
over the reference list (see its `_STALE_CUTOFF_YEAR`, and the
`source_freshness_summary` the Research Agent emits: "X of Y references are from
2025-2026"). A corpus-level ratio cannot see a single superseded load-bearing citation
sitting among fresh companions. Freshness asks "is this list recent enough." G5 asks
"is this specific finding still your publisher's position." Run G5 per claim, not per
reference list.

Check the newest edition even when the cited one is recent. A report published this year
can already have been revised. Two searches settle it in most cases: the publisher name
plus the current year, and the publisher name plus the specific finding.

A G5 failure is not automatically fatal to the thesis and should not be written up as
though it were. The useful output is usually a stronger post: state what the newer
edition changed, what survived it, and rebuild the argument on the part that survived.
Say explicitly which half of the original finding still holds.

## Scored dimensions

| # | Dimension | Weight | What earns a 5 |
|---|-----------|--------|----------------|
| 1 | Evidence density and quality | 25% | Central claims rest on primary sources (papers, filings, telemetry, published incident data), not on vendor blogs or aggregator listicles. Sample sizes and study limits are stated. |
| 2 | Falsifiability and honesty | 20% | The post states what would prove it wrong, gives the strongest counter-case fairly, and attaches explicit confidence to contested claims. |
| 3 | Thesis originality and structure | 15% | A non-obvious argument that a well-read practitioner has not seen before, developed in a line rather than a list. Each section advances the case. |
| 4 | Practitioner actionability | 15% | A QE lead or IT buyer can name a specific action for Monday, and can tell whether it worked. |
| 5 | Voice fidelity | 15% | Skeptical without cynicism. Vendor-neutral. Quantitative by default. No hype register, no false balance either. |
| 6 | Craft and packaging | 10% | Clean prose free of LLM tells. Title claims exactly what the body delivers. Length matches substance. |

Score anchors: **5** exemplary, **4** solid with minor gaps, **3** adequate but
unremarkable, **2** materially weak, **1** actively harmful to the brand, **0** absent.

Weighted score = sum of (dimension score / 5 x weight x 100).

## Verdicts

| Weighted score | Gates | Verdict |
|---|---|---|
| 80 or above | all pass | **PUBLISH** |
| 65 to 79 | all pass | **REVISE** (targeted fixes, no re-generation) |
| below 65 | all pass | **REWORK** (return to the Editorial Board; thesis or evidence base is the problem) |
| any | any fail | **BLOCK** (fix the gate failure first, then re-score) |

## LLM tells to flag under dimension 6

These are symptomatic, not decisive. Flag them, quote the instance, and suggest the fix.

- Opening with scene-setting abstraction ("In today's fast-paced engineering
  organizations...")
- The negation-elevation construction ("This is not just a testing problem, it is a
  trust problem")
- Rule-of-three padding where two items or four would be more honest
- Register words that add nothing: leverage, delve, landscape, realm, tapestry,
  underscore, crucial, robust, seamless
- Symmetrical section lengths, which usually mean the outline drove the content rather
  than the argument
- A conclusion that restates the introduction without having moved
- Hedging stacked on hedging ("may potentially contribute to")
- Fake precision, where a rounded estimate is presented to two decimal places

## Output format

Produce HTML for human reading, since the author reads these in a browser. Use no em
dashes. Structure it exactly as follows.

```
1. VERDICT
   Verdict, weighted score, gate results table. Nothing else. This has to be readable
   in five seconds.

2. GATE FINDINGS
   One row per gate. For failures: the exact quoted text, what is wrong, the
   recomputation or the source check that establishes it, and confidence as a
   percentage.

3. DIMENSION SCORES
   Table of the six dimensions with score, weighted contribution, and a one-line
   justification citing specific text.

4. THE STRONGEST OBJECTION
   The single best argument against the post's central claim, sourced. If the post
   already handles it, say so and credit it. This section is mandatory even for a
   PUBLISH verdict, because it is the section that keeps the brand honest.

5. FIXES, RANKED
   Ordered by score impact. Each fix names the location, the problem, and the specific
   replacement. Write the replacement text; do not describe it.

6. WHAT IS WORKING
   Brief. Only what is genuinely above the pipeline's baseline, so the author knows
   what to keep doing.
```

Then append the verdict block for the pipeline, as a fenced JSON code block:

```json
{
  "verdict": "PUBLISH | REVISE | REWORK | BLOCK",
  "weighted_score": 0,
  "gates": {"G1": "pass|fail", "G2": "pass|fail", "G3": "pass|fail", "G4": "pass|fail", "G5": "pass|fail"},
  "dimensions": {"evidence": 0, "falsifiability": 0, "thesis": 0, "actionability": 0, "voice": 0, "craft": 0},
  "blocking_findings": [],
  "reviewer_confidence_pct": 0
}
```

## Calibration discipline

Grade inflation destroys the point of a rubric. If most posts score above 85, the rubric
is broken, not the pipeline. A competent, publishable post that breaks no new ground
should land near 70. Reserve 90 and above for a post that would be cited by someone
else.

Be specific about your own uncertainty. When you cannot verify a claim, say so and give
a percentage rather than implying either confirmation or doubt. Two claims you flagged
at 60% confidence and 95% confidence should not read the same way to the author.

See `references/rubric.md` for the full scoring anchors on each dimension, including
worked examples of what a 2 versus a 4 looks like on evidence and falsifiability.
