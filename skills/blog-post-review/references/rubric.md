# Scoring anchors

Read this when assigning a dimension score and the 0 to 5 choice is not obvious. The
purpose of the anchors is inter-rater reliability: the same post reviewed twice, or
reviewed by a different agent in the pipeline, should score within about 5 points.

## Contents

- [1. Evidence density and quality (25%)](#1-evidence-density-and-quality-25)
- [2. Falsifiability and honesty (20%)](#2-falsifiability-and-honesty-20)
- [3. Thesis originality and structure (15%)](#3-thesis-originality-and-structure-15)
- [4. Practitioner actionability (15%)](#4-practitioner-actionability-15)
- [5. Voice fidelity (15%)](#5-voice-fidelity-15)
- [6. Craft and packaging (10%)](#6-craft-and-packaging-10)
- [Source tier reference](#source-tier-reference)
- [Cost model review checklist](#cost-model-review-checklist)

---

## 1. Evidence density and quality (25%)

| Score | Anchor |
|---|---|
| 5 | Central claims rest on Tier 1 sources. Sample sizes, study populations, and stated limitations appear in the text. Where evidence is thin, the post says so. |
| 4 | Mostly Tier 1 and 2. One or two claims lean on weaker sources but are not load-bearing. |
| 3 | Argument holds together but rests substantially on Tier 3. Numbers are sourced but not interrogated. |
| 2 | Load-bearing claims rest on vendor content or unattributed industry-consensus figures. |
| 1 | Numbers appear with no provenance and are treated as settled. |
| 0 | No evidence offered. |

**Worked example, evidence at 2 versus 4.**

At 2: "Flaky tests cost enterprises an estimated 15% of engineering capacity." No
source, no definition of enterprise, no method. The figure is doing all the work in the
argument and cannot be checked.

At 4: "In a study of 200 open-source projects, Luo et al. found 4.56% of test failures
were non-deterministic in origin. That is a lower bound for CI-heavy commercial
codebases, where the study's exclusion of proprietary integration suites likely
understates the rate." Sourced, bounded, and the post is explicit about the direction of
its own error.

The distinguishing move at 4 is not having a citation. It is knowing which way the
citation is wrong.

---

## 2. Falsifiability and honesty (20%)

| Score | Anchor |
|---|---|
| 5 | States the conditions under which the thesis fails. Presents the strongest opposing view in its own best form. Attaches explicit confidence to contested claims. |
| 4 | Acknowledges counter-arguments substantively, though perhaps not the strongest one. |
| 3 | Gestures at limitations in a closing paragraph. |
| 2 | Presents a contested claim as settled, or strawmans the opposition. |
| 1 | Hedges everything so that no claim can be wrong. This scores as low as overclaiming, because it is the same failure of nerve. |
| 0 | Pure advocacy. |

**The nerve test.** A post that cannot be wrong is not skeptical, it is evasive.
Empirical skepticism means committing to a claim and naming the evidence that would
retract it. Score down both the post that overclaims and the post that refuses to claim.

**Worked example.** "Teams should probably consider whether quarantining may be
appropriate in some contexts" scores 1. "Quarantine flaky tests rather than fixing them
immediately. I would abandon this position if quarantine rates exceeded roughly 3% of
the suite, at which point the quarantine has become the test strategy" scores 5.

---

## 3. Thesis originality and structure (15%)

| Score | Anchor |
|---|---|
| 5 | A claim a well-read practitioner has not encountered, argued in a line where each section is load-bearing. |
| 4 | Familiar territory, genuinely new angle or new evidence. |
| 3 | Competent synthesis of known material. This is the honest ceiling for most pipeline output. |
| 2 | Restates consensus. The reader learns nothing they could not have predicted from the title. |
| 1 | Listicle with a thesis bolted on. |
| 0 | No argument. |

**Structure diagnostic.** Delete any section. If the argument still stands, that section
was decoration. Report which sections fail this test.

---

## 4. Practitioner actionability (15%)

| Score | Anchor |
|---|---|
| 5 | A named action, a named owner role, and a named measurement that would show whether it worked. |
| 4 | Specific actions, vague on measurement. |
| 3 | Directionally useful, requires the reader to do the translation work. |
| 2 | Advice at the level of "invest in test quality". |
| 1 | Implies action without offering any. |
| 0 | Purely descriptive. |

Enterprise IT buyers and QE leads read for decisions. Ask: could a QE lead take this
into a Monday planning session and change something? Could they tell in six weeks
whether it helped?

---

## 5. Voice fidelity (15%)

The empirical skeptic voice, as practiced on viney.ca:

- Quantitative by default. Reaches for a number before an adjective.
- Vendor-neutral. Names tools when the specifics matter, never as endorsement.
- Skeptical of consensus, including its own priors, and says so.
- Unimpressed by novelty for its own sake, but not reflexively dismissive of new methods.
- Direct. Short sentences carry the claims.

| Score | Anchor |
|---|---|
| 5 | Indistinguishable from the author's best work. Vendor-neutral, quantitative, sharp. |
| 4 | Consistent voice, occasional slip into generic tech-blog register. |
| 3 | Recognizable but flat. |
| 2 | Reads as marketing, or as reflexive contrarianism, which is skepticism's cheap imitation. |
| 1 | Actively off-brand. |
| 0 | No discernible voice. |

**Note on the failure mode specific to a skeptic brand.** Contrarianism is not
skepticism. A post that doubts the consensus because doubting is on-brand has abandoned
empiricism. Score it at 2 even though it sounds correct.

---

## 6. Craft and packaging (10%)

| Score | Anchor |
|---|---|
| 5 | Clean prose, zero LLM tells, title claims exactly what the body delivers, length matched to substance. |
| 4 | One or two tells, otherwise clean. |
| 3 | Several tells, readable. |
| 2 | Pervasive tells, or title overclaims relative to body. |
| 1 | Padded to length. |
| 0 | Unpublishable as prose. |

**Punctuation consistency.** Em dashes are permitted: the house register targets The
Economist, which uses them freely. What costs a point here is inconsistency within a
single post, or dash-stacking that substitutes punctuation for sentence structure (three
or more em-dash asides in one paragraph). This is a craft observation and never a gate.

**Title fidelity check.** Read the title, write down what it promises, then check the
body delivers exactly that. A title promising a ledger of costs must contain a ledger of
costs. Over-promise is a craft failure, not a style quibble, because it spends reader
trust that the brand runs on.

---

## Source tier reference

| Tier | Examples |
|---|---|
| 1 | Peer-reviewed papers, regulatory filings, published telemetry or incident data, primary survey instruments with disclosed methodology, standards bodies |
| 2 | Reputable engineering blogs from the org that ran the experiment, conference talks with data, government statistics |
| 3 | Analyst reports behind the abstract, trade press, textbooks |
| 4 | Vendor marketing, aggregator listicles, unattributed industry-consensus figures, other AI-generated content |

Tier 4 sources cannot support a load-bearing claim. If one does, that is a dimension 1
score of 2 or below, and depending on how the citation is presented it may also trip
gate G2.

---

## Cost model review checklist

Posts that build a financial argument need arithmetic review, not just plausibility
review. Work through this list and show the numbers.

1. Recompute every stated figure from its inputs. Show the arithmetic.
2. Check unit consistency: per developer versus per team, annual versus monthly, fully
   loaded cost versus salary.
3. Check that percentages have a stated denominator.
4. Test the extrapolation. A figure derived from one organization applied to an industry
   needs the post to justify the leap, or to present it as illustrative rather than
   estimated.
5. Sanity-check the magnitude against an independent route to the same number. If the two
   routes differ by more than a factor of two, the post owes the reader an explanation.
6. Check the direction of every rounding. Rounding that consistently favors the thesis is
   a finding in itself, and worth reporting under gate G3 even when each individual
   rounding is defensible.
