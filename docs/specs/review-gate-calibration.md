# Spec — Calibrating the editorial review gate (B-040)

**Status:** APPROVED — owner LGTM 2026-08-05 · **Opened:** 2026-08-01
**Blocks:** ADR-0018 Decision 3 (advisory → blocking)
**Reference:** [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Anthropic, engineering blog)

## Objective

ADR-0018 adopted `skills/blog-post-review` and deliberately kept it **advisory**:

> Run the gate in advisory mode first, blocking later. … It does not automatically block a
> publish until calibration data exists. … Promote to blocking once a false-positive rate is
> known.

**Nothing has ever produced that number.** The gate has been executed exactly once, by hand,
on one article. So the most capable instrument in the pipeline — the only one that catches
fidelity defects the deterministic evaluator provably cannot — is frozen in advisory mode by
a measurement nobody has taken.

This spec defines that measurement. **It is not a plan to make the gate blocking.** It
produces the evidence that decision needs; the decision stays the owner's.

### Why this and not something else

Reviewing the repo against the Anthropic evals guide, the eval surface is lopsided in a
specific way:

| Guide's requirement | This repo |
|---|---|
| Code-based graders | **Strong** — `article_evaluator` (5 dimensions, 841 records), `publication_validator`, `_shared.py` gates, `skill_eval` |
| Model-based grader | Exists — `blog-post-review`, 5 gates + 6 weighted dimensions |
| "LLM-as-judge graders should be closely calibrated with human experts" | **Absent.** n=1, and that run contained a near-false-positive |
| A fixed eval set with known verdicts | **Absent.** `logs/article_evals.json` is 841 rows of *production monitoring*, not an eval set |
| Balanced positive **and** negative cases | Present in exactly one file (`skills/economist-writing/eval.yaml`) |
| Capability vs regression evals | Not distinguished |

The gap is not "we need more graders". It is that the one judgment-based grader has no ground
truth to be checked against, so it cannot be trusted, improved, or promoted.

## What "calibration" means here, precisely

Not "does the rubric score articles well." That is unfalsifiable. Calibration is **agreement
between the rubric's verdict and the owner's verdict, per gate, on the same input.**

Ground truth is the owner's judgement. The guide is explicit that human graders establish
ground truth and that model graders must be checked against them — a rubric cannot calibrate
itself, and an LLM cannot supply the ground truth for an LLM judge (that is the ADR-0018
failure mode one level up).

Two numbers come out, and they are not symmetric in cost:

- **False-positive rate** — the gate fails something the owner would have passed. This is the
  number ADR-0018 blocks on, because a blocking gate with false positives stops good articles
  and trains the owner to override it, which destroys the gate.
- **False-negative rate** — the gate passes something the owner would have failed. Cheaper
  today, because a human still approves every publish. It becomes the important number only
  *after* promotion to blocking.

## Design

### The unit of work is a finding, not an article

This is the load-bearing design decision. The obvious approach — collect 20–50 articles with
verdicts — is not available: the repo has 2 generated articles and 26 published ones, and
producing more costs a pipeline run each.

But the guide's actual instruction is **"20-50 simple tasks drawn from real failures"** — and
real failures already exist at finding granularity:

- **10 labelled fidelity defects** from the one real review (ADR-0018 enumerates them: a
  9-hour baseline described as measuring something it does not, a predictor attributed to a
  ranking that does not contain it, an organisation-level conclusion imported into a paper
  reporting no organisation-level outcome, a statistic with its offsetting clause deleted, a
  chart referenced as showing figures it does not contain, …)
- **1 labelled near-false-positive** — the summarised Graphite fetch that would have produced
  a false G2 failure on a figure that is correct and is Graphite's own published number. This
  one case is worth more than the ten positives, because it is the only direct evidence about
  the failure mode that actually blocks promotion.

Each becomes a case: **passage + gate + expected verdict + why**. A case is small, unambiguous
and cheap, and one article yields ten of them.

### Balance is not optional

The guide's web-search example makes the point: a set containing only cases where the agent
*should* fire optimises a one-sided detector. A gate evaluated only on real defects will
appear excellent right up until it blocks everything.

So roughly **half the set must be negatives** — correct passages, mined from the 26 published
articles, where the expected verdict is *pass*. These are the cases that detect an over-eager
judge, and they are the ones today's evidence base has exactly one of.

Target: **~25 cases, ~10 positive / ~15 negative.** The guide notes small sets suffice early
because effect sizes are large. Twenty-five is enough to distinguish "fires on nothing" from
"fires on everything"; it is not enough for a confidence interval, and the report must say so.

### Isolated judge per gate

The guide recommends grading "each dimension with an isolated LLM-as-judge rather than using
one to grade all dimensions." `REVIEW_PROMPT.md` currently grades 5 gates and 6 weighted
dimensions in one 99-line pass.

**v1 does not change the rubric.** It runs the gate **as accepted on 2026-07-31**, so the
baseline measures the artefact the owner approved. Splitting into isolated per-gate judges is
a *second* experiment, run against that baseline, and it is the natural first use of the
harness rather than a precondition for it. Changing the instrument and measuring it in the
same step would leave neither result interpretable.

### Deterministic where possible, model-based where necessary

Case selection, bookkeeping, agreement arithmetic and the report are plain Python — no LLM.
The judge is the only model-based component, invoked keyless via the Agent SDK per Operating
Constraint #3. This keeps the harness re-runnable at zero marginal cost, which is the
property that decides whether it gets run twice.

## Commands

```bash
# Run the whole calibration set and write a report
python scripts/calibrate_review_gate.py --cases docs/evals/review-gate/cases --out logs/review_gate_calibration.json

# Re-run a single gate's cases while iterating on the rubric
python scripts/calibrate_review_gate.py --gate G5

# Report only, from the last run (no model calls)
python scripts/calibrate_review_gate.py --report
```

## Project structure

```
docs/evals/review-gate/cases/*.yaml   # one file per case: passage, gate, expected, why
docs/evals/review-gate/README.md      # how to add a case; the balance rule
scripts/calibrate_review_gate.py      # runner + agreement arithmetic + report
tests/test_calibrate_review_gate.py   # tests of the harness, with the judge stubbed
logs/review_gate_calibration.json     # append-only; one row per calibration run
```

Case format:

```yaml
id: g2-baseline-measures-something-else
gate: G2
expected: fail
source: review-queue-throughput-tax   # provenance — a real failure, not an invention
passage: >-
  The 9-hour baseline shows review latency is dominated by queue depth.
why: >-
  The cited study's 9-hour figure measures time-to-first-comment, not total latency.
  The claim overstates the source's scope. ADR-0018 finding 3.
```

## Testing strategy

TDD per `agent-skills:test-driven-development`. `tests/test_calibrate_review_gate.py`,
deterministic, **no model calls in the test suite** — the judge is stubbed, so the tests
exercise the harness and the arithmetic, not Claude:

- Agreement arithmetic is correct for hand-computed fixtures, including the degenerate cases
  (all-pass, all-fail, empty)
- False-positive and false-negative rates are reported **separately**, never averaged into a
  single "accuracy" that hides which direction the gate errs in
- A case file missing `expected` or `why` is rejected loudly rather than skipped
- The set's positive/negative balance is reported on every run, so drifting to one-sided is
  visible
- `n` is reported alongside every rate; a rate from fewer than 20 cases is labelled
  provisional in the output itself
- Re-running with the judge stubbed to a fixed verdict reproduces byte-identical arithmetic

## Boundaries

- **Always:** report false positives and false negatives separately, with `n`; keep case
  provenance (a case is drawn from a real failure or a real published article, never invented);
  keep the harness keyless and re-runnable.
- **Ask first:** any change to `rubric.md` or `REVIEW_PROMPT.md` scoring — those are the
  instrument under test, and ADR-0018 is one day old; promoting the gate to blocking.
- **Never:** use an LLM to generate ground-truth verdicts (that is the failure mode this
  measures); average the two error rates into one number; report a rate without `n`; let the
  harness edit the rubric it is measuring.

## Success criteria

- [ ] `python scripts/calibrate_review_gate.py` runs the full set keyless and writes a report
- [ ] The report states, separately and with `n`: false-positive rate, false-negative rate,
      per-gate agreement, and the positive/negative balance of the set
- [ ] ≥20 cases, ≥40% of them negatives, every one traceable to a real article or a real finding
- [ ] The output is sufficient to answer ADR-0018 Decision 3 — i.e. the owner can read it and
      decide promote / do not promote / fix the rubric first
- [ ] `make ci-local` green; ≥80% coverage on the new module
- [ ] No new dependency, no key, no network beyond the judge's own source fetching

## Not in scope for v1

- **pass@k / pass^k.** The guide positions these for mature agents measuring small
  improvements. Five recorded pipeline runs and one gate execution is not that.
- **Promoting the gate to blocking.** This produces the evidence; ADR-0018 Decision 3 stays
  the owner's call.
- **Splitting the rubric into isolated per-gate judges.** The obvious first experiment *after*
  a baseline exists, not before.
- **A dashboard.** `logs/review_gate_calibration.json` is append-only; reading it is a
  one-liner. `skills/observability` already claims a `quality_dashboard.json` that does not
  exist — adding a second unread artefact is the wrong direction.
- **Re-measuring the deterministic evaluator.** The 88%-vs-51 spread is measured, documented
  and accepted. Nothing further to learn.

## Sequencing — why this is specced now and built later

The harness design depends on data the repo does not yet have. If the gate BLOCKs everything,
the useful work is threshold tuning. If it passes everything, ADR-0018's own warning applies —
"scores clustering above 85 would mean the rubric is broken rather than the pipeline" — and
the useful work is anchor revision. Those are different tools.

**Build after n≈5 real reviews.** Those accrue for free: every article already goes to the
unlisted review URL for owner approval (B-013 / B-028), so the only added cost is the owner
recording, per gate, whether they agreed. One line per run. Shipping becomes data collection
instead of a separate project.

Until then this spec sits here, and the two prerequisites below ship immediately because
waiting on them corrupts the data the baseline is made of.

## Prerequisites shipped alongside this spec (2026-08-01)

1. **G5 added to the machine-readable verdict block in `REVIEW_PROMPT.md` and the rubric
   card.** ADR-0018 Decision 2 states G5 was amended "into the machine-readable verdict
   block"; it reached `SKILL.md:165` but **not** `REVIEW_PROMPT.md:85`, which is the file
   actually pasted into a review session. Every review run until now would have silently
   dropped G5's result — the gate that exists precisely because a reversed DORA statistic
   passed the other four.
2. **The runbook's cost/duration figures replaced with the recorded range.** `HANDOFF.md` and
   the runbook said "~$1 and ~35 minutes"; `logs/agent_sdk_costs.jsonl` has recorded
   `wall_seconds` per run since April and no run has exceeded **15.4 minutes**. The instrument
   existed and went unread while its folklore contradiction got repeated in two documents.

## Open questions — both ANSWERED at LGTM, 2026-08-05

1. **Who writes the negative cases?** Mining ~15 correct passages from the 26 published
   articles is mechanical but needs judgement about what "correct" means. Proposed: the agent
   drafts them with provenance, the owner spot-checks a sample rather than all fifteen.

   **ANSWERED — proposal accepted.** The agent drafts with `source:` provenance; the owner
   spot-checks a sample. Note the residual risk this accepts: the agent both drafts the
   negative cases *and* is the same model family as the judge under test, so a case the agent
   finds obviously-correct may be one the judge also finds obviously-correct for the same
   wrong reason. The spot-check is the control on that, which is why it cannot be skipped.

2. **Does a G1 UNVERIFIED count as a false positive** when the source is real but unreachable
   at review time? The rubric says "unverified is not false, but this blog cannot ship an
   unverified number" — defensible as policy, but it will inflate the false-positive rate
   against a human who would fetch the source a second time. Proposed: count it as a distinct
   third outcome, `unverified`, and report it separately rather than folding it either way.

   **ANSWERED — proposal accepted.** `unverified` is a third outcome, reported with its own
   `n`, never folded into either error rate. The Boundaries rule "never average the two error
   rates" extends to it: three counts, three denominators.
