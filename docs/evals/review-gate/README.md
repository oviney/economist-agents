# Editorial Review Gate Evaluation Set (B-040)

This directory contains the ground-truth eval set for measuring the **agreement, False-Positive Rate (FPR), and False-Negative Rate (FNR)** of the `skills/blog-post-review` model-based editorial review gate.

Spec: `docs/specs/review-gate-calibration.md`  
Harness: `scripts/calibrate_review_gate.py`

## Case Schema

Each case in `cases/*.yaml` defines a single self-contained evaluation unit:

```yaml
id: g2-baseline-scope-overstatement
gate: G2                          # One of G1, G2, G3, G4, G5
expected: fail                    # "pass" or "fail"
source: review-queue-throughput-tax # Real article slug or ADR provenance
passage: >-
  The 9-hour baseline shows review latency is dominated by queue depth.
why: >-
  The cited study's 9-hour figure measures time-to-first-comment, not total latency.
```

## Set Balance Rule

To prevent training an over-eager detector that blocks valid content (creating high false positives), **at least 40% of the evaluation set must be negative (expected: `pass`) cases** drawn from published, verified articles.
