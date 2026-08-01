# ADR-0019: A sensor's setpoint is a decision about who decides

**Status:** Accepted
**Date:** 2026-08-01
**Decision Maker:** Ouray Viney (owner)
**Supersedes:** *(none — amends Operating Constraint #4 and answers open question 3 of `docs/specs/sensor-proof-of-teeth.md`)*
**Superseded by:**

## Context

B-043 shipped a standing check that no sensor ships without a proof it can fail,
and left one question open, deliberately:

> A sensor with the wrong setpoint is neither inert nor inaccurate; it works, and
> the system is worse for it. Boeckeler's framework does not name it, and a proof
> of teeth cannot catch it — `missing_chart` **fires correctly**.

B-042 is the worked example. `publication_validator.py` required a chart in every
article at **CRITICAL** severity, with the justification "Charts are mandatory per
Economist editorial standards". The check was correct: it fired exactly when no
chart reference was present. On 2026-08-01 a research brief containing one number
produced an article whose chart carried four invented percentages — 62 / 46 / 28 /
12% — with an axis and a measured-sounding subtitle. The evaluator scored the
article 76 and the validator passed it.

**Nothing malfunctioned.** A gate demanded a chart, the research could not supply
one, and the pipeline complied the only way it could. The rule meant to enforce
evidence produced fabricated evidence.

The instinct is to tune: make the requirement conditional, add an audit that
checks chart figures against the brief, downgrade the severity. Each of those
treats the number as the problem. Investigating instead turned up the shape of
the real defect, and two adjacent findings that make the case:

- A **working** `orphaned_chart` — the HIGH check that fires when an embedded
  chart is never mentioned in prose — would have made things *worse*. Its only
  available remedy is "add a sentence about the chart", which is exactly what
  wrote *"As the chart below illustrates, undetected defects do not flow
  linearly into rework"* about a static four-bar comparison.
- `orphaned_chart` could never fire at all. `missing_chart` returns early unless
  a `/assets/charts/….png` reference exists, so by the time the orphan scan ran,
  the content provably contained the substring "chart" — in the embed URL. A
  passing test documented this as intended behaviour.

The forcing question was not "what should the threshold be" but **"is this the
machine's call at all?"** Whether an article warrants a chart is an editorial
judgment made against the research. The validator runs on a markdown file and
never sees the research. It was not holding a mistuned threshold; it was holding
a decision that was never its to make.

## Decision

**We will treat a sensor's setpoint as a statement about who owns the decision,
and check that ownership before tuning the value.**

Concretely, when a sensor fires correctly and the outcome is still bad, the first
question is *whose judgment is this?* — not *what should the number be?* If the
sensor lacks the evidence the judgment requires, the answer is to **remove its
authority**, not to adjust its threshold. A sensor may only enforce decisions it
has the inputs to make.

Applied to B-042: `missing_chart` and `orphaned_chart` are **deleted**, not
retuned. Art presence moves to the deploy boundary (ADR-0017), which is where
"publishable" becomes true and where the files can actually be inspected. The
owner decides whether an article warrants a chart, and the pipeline's role is
reduced to *extracting* candidate figures from the brief with their provenance —
a report, not a judgment.

This also amends Operating Constraint #4: the owner makes every image.

## Alternatives Considered

1. **Make the requirement conditional on chartable data existing.** The obvious
   fix, and the one the first draft of the spec designed in detail. Rejected
   because the validator cannot evaluate the condition: it has the article, not
   the research. Any signal it could read — a frontmatter declaration, a sidecar
   flag — would have to be written by the same pipeline the gate constrains,
   which makes it an escape hatch controlled by the actor with the motive to use
   it. The fabricated chart *was* the pipeline satisfying a gate.

2. **Audit chart figures against the brief after generation.** Also designed and
   discarded. It works — the machinery is a near-copy of `audit_article_stats`,
   which already deletes prose sentences whose numbers are not in the brief. But
   auditing a model's output for fabrication is strictly worse than never asking
   it for the numbers. The audit would be a permanent tax defending against a
   generative step with no independent reason to exist.

3. **Downgrade `missing_chart` from CRITICAL to advisory.** Rejected as the worst
   of both: it keeps a sensor that cannot make the judgment, while removing the
   only thing that made it honest — its teeth. A gate nobody must satisfy is a
   guide, and this repo was graded guide-maximal.

4. **Repair `orphaned_chart` so it can fire.** Rejected on evidence. Its only
   remedy pushes the writer toward describing a chart, and nothing verifies the
   description is true. Making it work would make B-042 worse. What it reached
   for — *is the description true?* — is inferential, and ADR-0018 already
   decided judgment is advisory here.

## Consequences

**Easier.** A whole class of gate can now be diagnosed rather than tuned. "Fires
correctly, outcome is bad" has a name and a first question. B-043's taxonomy gap
is closed: a wrong setpoint is not an inert sensor, not an inaccurate one, but a
sensor holding someone else's decision.

The pipeline also gets simpler. Deleting the graphics stage and the hero author
removed a model call, a retry loop, a budget, three failure modes (BUG-042,
BUG-063, BUG-064), and the 600s hero-draw timeouts that dominated run duration —
which moots **B-041** entirely.

**Harder.** Every article now needs the owner before it can publish. That is the
point, but it is real: there is no unattended path to a finished post any more,
and a run ends with a review packet rather than a publishable file.

**The risk we accept.** A gate removed is a gate that cannot catch a regression.
An article can now reach the deploy step with no chart when it should have had
one, and nothing will object. We accept this because the failure it replaces was
worse and was *actually observed*: a chart that should not have existed, carrying
numbers that were never measured, on a permanent public URL. A missing chart is
visible to the reader as an absence. A fabricated one is not visible at all.

**What this does NOT license.** This is not an argument for deleting gates that
are merely inconvenient. It applies where a sensor *lacks the evidence* its
judgment requires. A sensor with the right inputs and an awkward threshold is a
tuning problem, and should be tuned.
