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

> **Six of the ten are here, not ten — and the reason is worth recording.** Until 2026-08-05
> this section described cases that did not exist: every file on disk carried
> `source: testing-shortcuts-migration-deadline`, and this article had contributed **none**.
> The six added on 2026-08-05 were reconstructed from ADR-0018's prose, which describes five
> findings verbatim plus the G5 supersession. **The review report itself was never persisted.**
> Only `docs/reviews/review-queue-throughput-tax-42d2fbb4.html` — the rendered draft page, not
> the verdict — and the ADR's summary survive. The remaining findings (among them an
> organisation-level conclusion imported into a paper reporting no organisation-level outcome)
> cannot be turned into cases without guessing which passage each refers to, and a
> mislabelled ground-truth case is worse than a missing one (rule 3 below).
>
> **The operating consequence:** a review whose verdict block is not saved is a review whose
> findings are only as durable as whatever prose someone wrote about it afterwards. Every
> future run should append its verdict block to `logs/`, per ADR-0018 Decision 4's
> observability row.

**`testing-shortcuts-migration-deadline`** — generated 2026-08-01 from an owner artifact that
contained **zero citations**. The writer sourced the piece itself and fabricated freely; the
deterministic evaluator scored it **76** and the publication validator **passed** it. It
reproduced ADR-0018's chart finding exactly, one day after the ADR was accepted. Unplanned,
and better material than anything designed on purpose.

## Set status — 2026-08-05

**23 cases · 12 negatives (52%) · 4 source articles.** Both spec criteria met: ≥20 cases,
≥40% negatives.

| Gate | fail | pass |
|---|---|---|
| G1 Source resolvability | 1 | 1 |
| G2 Citation fidelity | 7 | 5 |
| G3 Arithmetic integrity | **0** | 2 |
| G4 No fabrication | 2 | 2 |
| G5 Evidence currency | 1 | 2 |

**G3 has no positive case, and one must not be invented to fill the row.** No arithmetic
defect has ever been recorded in this repo — ADR-0018 found G3 clean on the one real review,
and B-042's fabricated chart figures were a G4 fabrication, not a computation that failed to
reproduce. The consequence must be stated in the report rather than hidden: **G3's
false-negative rate is unmeasurable in v1.** The set can show G3 does not over-fire; it cannot
show G3 fires at all. That is the same defect class as B-031 and B-043 — a sensor with no
proof it can fail — and the honest fix is a real G3 failure when one occurs, not a
manufactured one now.

Two adjacent notes on what these numbers do and do not support. **`n=23` does not carry a
confidence interval**, and the runner is required to label rates from fewer than 20 cases
provisional; 23 clears that bar only just. And **6 of the 12 negatives come from a single
article**, so a judge that happens to suit one author's register will look better calibrated
than it is. Both are arguments for the set continuing to grow as reviews accrue, not for
treating this snapshot as finished.

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
