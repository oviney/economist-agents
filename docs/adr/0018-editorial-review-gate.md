# ADR-0018: Editorial Review Gate for Generated Articles

**Status:** Accepted
**Date:** 2026-07-29 · **Accepted:** 2026-07-31
**Decision Maker:** Ouray Viney (owner)
**Supersedes:** *(none)*
**Superseded by:** *(none)*

## Context

The pipeline's quality checks are deterministic by design. `skills/article-evaluation`
states it plainly: "All scoring is deterministic — regex, dictionary lookups, and
counting. No LLM calls." That buys speed, reproducibility and zero marginal cost, and it
catches a real class of defect: banned openings, American spellings, missing frontmatter,
word-count drift, absent references sections.

It cannot catch whether a cited source says what the article claims it says.

On 2026-07-29 the second article of the run, `review-queue-throughput-tax`, was reviewed
against the `blog-post-review` rubric while sitting in the B-013 review stage at
`/review/review-queue-throughput-tax-42d2fbb4/`. All six of its citations resolved to
real documents. Both arXiv papers were real, correctly titled, correctly attributed, and
accurate to the decimal place. Every recomputable figure reproduced, and the rounding ran
*against* the thesis rather than for it.

The review still returned **BLOCK at a weighted 51.0 out of 100**, on ten distinct
findings. The defects were not sourcing defects; they were fidelity defects. A 9-hour
baseline described as measuring something it does not measure. A predictor ("author
seniority") attributed to a ranking that does not contain it. An organisation-level
conclusion imported into a paper that reports no organisation-level outcome. A quoted
statistic with its offsetting second clause deleted ("AI PRs wait 4.6x longer before
review, **but are reviewed 2x faster once picked up**"). A chart referenced as showing two
figures it does not contain, positioned three sections from its reference.

**The existing deterministic evaluator passes this article at 88%.** This is measured, not
inferred: `scripts/article_evaluator.py` run against `output/posts/review-queue-throughput-tax.md`
returns

```
opening_quality      6/10   Opening has 1 data tokens
evidence_sourcing    9/10   6 references cited, 0 placeholders; fresh citations (2026/2025): 1
voice_consistency    9/10   Clean voice
structure           10/10   4 headings, 981 words, references: yes
visual_engagement   10/10   image: yes, chart embedded: yes
TOTAL               44/50 = 88%
```

The same article scores **51.0 out of 100 and BLOCK** on the `blog-post-review` rubric. A
37-point spread between two evaluators on one article is the whole argument for this ADR.

Read the two highest scores against what the rubric found. `visual_engagement` awards 10/10
for "image: yes, chart embedded: yes" to the chart that plots neither of the two figures the
prose says it shows and sits three sections from its reference. `evidence_sourcing` awards
9/10 for "6 references cited, 0 placeholders" to the reference list carrying ten fidelity
defects. A counting check cannot distinguish "cited" from "cited correctly", and here it
awards near-full marks to the exact defects. That gap is not closeable by adding more
deterministic rules.

Note the freshness sub-signal in `evidence_sourcing`: it counted only **1** fresh citation
and docked exactly **1 point out of 10**. So the corpus-level freshness heuristic did fire,
and shrugged. That is the concrete case for G5 below: a ratio noticing that a reference list
skews old is not the same instrument as checking whether a specific load-bearing finding has
been reversed.

A second finding sits one level up, in the reviewer rather than the article. The single
most damaging defect was that the article's load-bearing throughput statistic (DORA 2024
via RedMonk: a 25% adoption rise associated with a 1.5% throughput decrease) had been
reversed by DORA 2025, published 2025-12-18 and analysed by the same author at the same
publication, seven months before the article. **That defect passed all four existing
gates.** G1 resolves, G2 is faithful to the 2024 source, G3 and G4 are clean.

It is also not caught by `research-sourcing`, which enforces freshness as a ratio over
the reference list (`_STALE_CUTOFF_YEAR = _CURRENT_YEAR - 2`, and the
`source_freshness_summary` the Research Agent emits: "X of Y references are from
2025-2026"). This article cites two 2026 arXiv papers and a 2026 vendor report, so it
passes a ratio test comfortably. One superseded load-bearing citation hides among fresh
companions. Freshness is per-corpus; supersession is per-claim.

Related open work: **B-028** already proposes that the unreviewed publish path stop being
the default, after the RCA found `deploy_to_blog.py` sets `default="post"` and silently
bypasses the B-013 review stage. This ADR decides what runs *in* that stage; B-028
decides that the stage cannot be skipped.

## Acceptance note (2026-07-31)

Accepted as written. The decisive evidence is the **37-point spread on one article**: the
deterministic evaluator returns 88% PASS where the rubric returns 51.0 BLOCK, and it awards
its two *highest* sub-scores to the exact defects — 10/10 `visual_engagement` to a chart
plotting neither figure the prose claims, 9/10 `evidence_sourcing` to a reference list
carrying ten fidelity defects. A counting check cannot distinguish "cited" from "cited
correctly", so that gap does not close by adding deterministic rules.

Decision 3 (**advisory first, blocking later**) is the reason this is cheap to accept: the
gate informs the human who already approves at the B-013 review stage rather than acquiring
a veto of its own. It is an instrument for that reviewer, not a replacement for them.

Keyless per Operating Constraint #3 — it runs on the Claude subscription via the Agent SDK.

## Decision

**1. Adopt `skills/blog-post-review` as a distinct review stage, not an extension of
`article-evaluation`.** The two skills are kept separate because their methods are
incompatible: one is deterministic and free, the other requires live source fetching and
judgment. Merging them would either make the cheap checks expensive or dilute the
rubric into countable proxies. `article-evaluation` keeps scoring form; `blog-post-review`
scores substance.

**2. Add a fifth gate, G5 Evidence Currency.** For every load-bearing citation, check
whether the same publisher has issued a later edition that revises, reverses, or narrows
the finding. Per claim, not per reference list. Amended into `SKILL.md` and
`REVIEW_PROMPT.md` with the reasoning, and into the machine-readable verdict block.

**3. Run the gate in advisory mode first, blocking later.** The stage runs, emits its
verdict block, and records it. The owner still approves. It does not automatically block
a publish until calibration data exists.

The reason is measured, not precautionary. During this review, a summarised fetch of the
Graphite source returned an incomplete answer, and had it been trusted the review would
have reported a **false G2 failure** on a figure that is in fact correct and is Graphite's
own published number. Only re-reading the raw page text corrected it. That is one
near-false-positive out of five gates on a single run. The rubric's own calibration
section warns that thresholds cannot be validated at n=1 and that scores clustering above
85 would mean the rubric is broken rather than the pipeline. Promote to blocking once a
false-positive rate is known.

**4. Route the four classes of review output to the skills that already own them.** The
anti-pattern is feeding the whole review report back to the Writer Agent, which teaches
it to fix one article rather than to stop producing a class of defect. The generator
receives rules; the article receives fixes.

| Output class | Destination | Lifetime |
|---|---|---|
| Article-specific fixes | Writer Agent revision brief | Dies with the article |
| Recurring defect patterns | `skills/defect-prevention` | Permanent rule |
| Rubric gaps | `skills/blog-post-review` | Permanent gate or anchor |
| Scores, gate results, confidence, cost | `skills/observability`, one row per run | Permanent trend data |

**5. Shift the mechanisable subset upstream.** Per `skills/ci-cd-and-automation`, the
review stage is the most expensive place to discover that a currency figure has no
citation. The following are lint-tier and belong in generation plus CI, and would have
caught roughly half of this run's findings at near-zero cost:

- a currency token must appear within N characters of a citation marker
- the currency symbol must match the article's locale (this article priced a US-sourced
  argument in pounds)
- "the chart below" must resolve to a chart within N paragraphs whose data series the
  surrounding prose names
- required sections must be present: a falsification condition, and a named action

The last item maps to scored dimensions 2 and 4, which came in at 2 and 1, the two lowest
scores of the run. Cheapest available points.

Reserve the expensive review for what only judgment catches: citation fidelity,
supersession, and the strongest published objection.

## Alternatives Considered

**Extend `article-evaluation` with new deterministic rules instead.** Rejected on
evidence. The defects found are semantic: a source that exists but is misdescribed, a
denominator that measures a different population, a quotation truncated at its
qualifying clause. No regex distinguishes a faithful citation from an unfaithful one. The
repo's own contributing rule prefers extending an existing skill over adding a
near-duplicate, and that rule is satisfied here by measuring the gap rather than asserting
it: the existing evaluator passes this article at 88%, scoring 10/10 and 9/10 on the two
dimensions the rubric review found most defective.

**Make the gate blocking immediately.** Rejected for now on the measured false-positive
above. A gate that blocks correct articles will be disabled by whoever is trying to
publish, which is strictly worse than an advisory gate that is trusted. Revisit once the
observability ledger holds enough rows to estimate the rate.

**Fold G5 into `research-sourcing`.** Rejected. That skill's charter is the research
stage and its mechanism is corpus-level ratios. G5 is a per-claim check performed at
review time against the finished argument, when it is known which citations are actually
load-bearing. That information does not exist at research time.

**Run the review post-publish only.** Rejected. The B-013 review stage already renders an
unlisted `noindex` draft at a live URL, which is what made the chart defect visible at
all (it required a rendered page, not markdown). Reviewing there costs nothing extra and
happens before the article is public.

**Keep the skill in `~/.claude/skills/` and invoke it ad hoc.** Rejected. It was
previously copied into an unrelated repository during this session, which produced a fork
with no single source of truth. Consolidated into `skills/` beside the other pipeline
skills, and the global copy removed.

## Consequences

**Positive.**

- A class of defect currently invisible to the pipeline becomes visible before publish.
- G5 closes a gap that all four prior gates missed, on the most damaging finding of the run.
- Feedback routing means each review compounds: rules accumulate in `defect-prevention`,
  calibration accumulates in `observability`.
- The mechanisable subset moving upstream reduces what the expensive stage has to do.

**Negative and accepted.**

- The review stage costs real tokens and wall-clock. This run took roughly fifteen tool
  calls including a browser render, a redirect follow, and two raw page reads, because
  summarised fetching proved unreliable on exactly the claim it mattered most for.
- Advisory mode means a defective article can still ship if the owner approves past the
  verdict. That is the deliberate trade against false positives blocking good work.
- Two of this run's findings could not be fully resolved because the figures sit behind a
  vendor download. The gate will produce UNVERIFIED verdicts on gated sources, and that
  will be a recurring friction rather than a one-off.

**Risks.**

- Grade inflation. If scores cluster high, the rubric has been captured. The
  observability ledger is the control, and it only works if every run appends a row,
  including runs the owner overrides.
- Rubric drift toward whatever the generator happens to produce. Mitigated by ADR-0008
  skill governance and by keeping the calibration anchors in
  `references/rubric.md` under review.

**Follow-up work (not decided here).** Wiring the stage into `deploy_to_blog --mode
review`, authoring the deterministic pre-checks, adding the `defect-prevention` rules
from this run, and defining the observability row schema. Tracked separately alongside
B-028.
