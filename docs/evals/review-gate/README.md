# Review-gate calibration cases (B-040)

Ground truth for `skills/blog-post-review`. Each file is one case: a passage, the gate it
tests, the verdict a domain expert would reach, and why.

**Spec:** `docs/specs/review-gate-calibration.md`. **Runner:** not built yet — these accrue
first, deliberately (see the spec's sequencing section). Adding cases costs nothing and is
the input the harness design depends on.

## The rules that make this a calibration set rather than a pile of examples

1. **Every case comes from a real article or a real review finding.** `source:` records
   which. An invented case measures the imagination of whoever wrote it.
2. **Roughly half must be negatives** — correct passages the gate must *not* flag. A set
   containing only real defects optimises a one-sided detector that looks excellent right up
   until it blocks everything. `expected: pass` cases are the ones that catch that, and they
   are the half the evidence base started with almost none of.
3. **Two domain experts must reach the same verdict independently.** If a case is arguable,
   it is noise in the metric, not a hard case. Cut it or sharpen it.
4. **`why:` is not optional.** A verdict without a reason cannot be re-adjudicated when the
   rubric changes, which is the whole point of keeping them.

## Where these came from

**`review-queue-throughput-tax`** — the 2026-07-29 review that produced ADR-0018: BLOCK at
51/100 on ten fidelity defects, against 88% PASS from the deterministic evaluator. Includes
the one labelled *near-false-positive*: a summarised fetch of the Graphite source would have
reported a false G2 failure on a figure that is correct and is Graphite's own published
number. That case is worth more than any of the true positives, because false positives are
what block promotion to blocking.

**`testing-shortcuts-migration-deadline`** — generated 2026-08-01 from an owner artifact that
contained **zero citations**. The writer sourced the piece itself and fabricated freely; the
deterministic evaluator scored it **76** and the publication validator **passed** it. It
reproduced ADR-0018's chart finding exactly, one day after the ADR was accepted. Unplanned,
and better material than anything designed on purpose.

## Format

```yaml
id: g2-baseline-measures-something-else   # kebab-case, gate-prefixed, unique
gate: G2                                  # G1..G5, or a rubric dimension name
expected: fail                            # fail | pass | unverified
source: review-queue-throughput-tax       # provenance — never "invented"
passage: >-
  The verbatim text under review.
why: >-
  What a domain expert would say, in one or two sentences.
```

`unverified` exists because of the spec's second open question: a G1 case where the source is
real but unreachable at review time is neither a clean pass nor a clean fail, and folding it
either way distorts the false-positive rate.
