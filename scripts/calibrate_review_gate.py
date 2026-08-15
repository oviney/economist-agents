#!/usr/bin/env python3
"""Measure how well the `blog-post-review` gate agrees with the owner's labels.

B-040. ADR-0018 Decision 3 keeps the gate advisory until a false-positive rate
exists; nothing has ever produced that number. This harness produces it, by
running the gate over `docs/evals/review-gate/cases/` — passages whose correct
verdict the owner has labelled — and reporting agreement.

Two properties are load-bearing, and both come from the spec's Boundaries
(`docs/specs/review-gate-calibration.md`):

- **The error rates are never averaged.** A false positive (the gate blocks a
  good article) and a false negative (it misses a defect) have different costs,
  and a single "accuracy" hides which direction the gate errs in. They are
  reported separately, each with its own denominator and its own ``n``.
- **The harness never edits the instrument it measures.** Gate definitions are
  read out of `skills/blog-post-review/REVIEW_PROMPT.md` at run time rather than
  restated here, so a rubric change cannot leave this file silently measuring a
  stale copy.

Case selection, bookkeeping and arithmetic are plain Python. The judge is the
only model-based component, invoked keyless via the Agent SDK per Operating
Constraint #3.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

#: Below this many cases a rate is labelled provisional in the output itself.
#: The spec's reasoning: 25 cases distinguishes "fires on nothing" from "fires
#: on everything", but is not enough for a confidence interval.
PROVISIONAL_BELOW_N = 20

#: `expected: pass` means "the gate should NOT flag this passage" — a negative.
PASS = "pass"
FAIL = "fail"
UNVERIFIED = "unverified"


@dataclass(frozen=True)
class CaseResult:
    """One case, its labelled verdict, and what the judge actually returned.

    Attributes:
        case_id: The case's ``id`` field, for tracing a rate back to a passage.
        gate: Which gate (G1..G5) the case exercises.
        expected: The owner-labelled verdict — ``pass`` or ``fail``.
        judged: What the judge returned — ``pass``, ``fail`` or ``unverified``.

    """

    case_id: str
    gate: str
    expected: str
    judged: str


def _rate_block(count: int, n: int) -> dict[str, object]:
    """Package a count and its denominator as a reportable rate.

    Args:
        count: Numerator — how many cases showed this outcome.
        n: Denominator — how many cases could have.

    Returns:
        A block carrying ``count``, ``n``, ``rate_pct`` and ``provisional``.
        ``rate_pct`` is ``None`` when ``n`` is zero: a rate of 0.0 out of zero
        cases is a claim the data does not support.

    """
    return {
        "count": count,
        "n": n,
        "rate_pct": round(100 * count / n, 1) if n else None,
        "provisional": n < PROVISIONAL_BELOW_N,
    }


def _per_gate(results: list[CaseResult]) -> dict[str, dict[str, object]]:
    """Agreement per gate, ordered by gate name so reports diff cleanly."""
    totals: Counter[str] = Counter(r.gate for r in results)
    agreed: Counter[str] = Counter(r.gate for r in results if r.judged == r.expected)

    return {
        gate: {
            "agreed": agreed[gate],
            "n": totals[gate],
            "agreement_pct": round(100 * agreed[gate] / totals[gate], 1),
            "provisional": totals[gate] < PROVISIONAL_BELOW_N,
        }
        for gate in sorted(totals)
    }


def summarise(results: list[CaseResult]) -> dict[str, object]:
    """Compute the calibration report from judged cases.

    Args:
        results: One entry per case run.

    Returns:
        The report. Deliberately contains no combined accuracy figure — the
        spec lists averaging the two error rates as a **Never**, because the
        promotion decision in ADR-0018 turns on the false-positive rate alone.

    """
    negatives = [r for r in results if r.expected == PASS]
    positives = [r for r in results if r.expected == FAIL]

    false_positives = sum(1 for r in negatives if r.judged == FAIL)
    false_negatives = sum(1 for r in positives if r.judged == PASS)
    unverified = sum(1 for r in results if r.judged == UNVERIFIED)

    return {
        "n_cases": len(results),
        "balance": {
            "negatives": len(negatives),
            "positives": len(positives),
            "negative_pct": (
                round(100 * len(negatives) / len(results), 1) if results else None
            ),
        },
        "false_positive": _rate_block(false_positives, len(negatives)),
        "false_negative": _rate_block(false_negatives, len(positives)),
        "unverified": _rate_block(unverified, len(results)),
        "per_gate": _per_gate(results),
    }
