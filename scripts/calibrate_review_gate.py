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

import logging
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import orjson

logger = logging.getLogger(__name__)

#: A judge takes a gate definition and a passage, and returns one verdict.
#: Injected so the test suite can exercise the harness without a model call.
Judge = Callable[[str, str], str]

#: Below this many cases a rate is labelled provisional in the output itself.
#: The spec's reasoning: 25 cases distinguishes "fires on nothing" from "fires
#: on everything", but is not enough for a confidence interval.
PROVISIONAL_BELOW_N = 20

#: `expected: pass` means "the gate should NOT flag this passage" — a negative.
PASS = "pass"
FAIL = "fail"
UNVERIFIED = "unverified"


#: Matches one gate bullet in REVIEW_PROMPT.md, stopping at the next gate or the
#: next heading so a definition cannot bleed into its neighbour.
_GATE_BULLET = re.compile(
    r"^- \*\*(?P<gate>G\d)\b(?P<body>.*?)(?=^- \*\*G\d|^#|\Z)",
    re.MULTILINE | re.DOTALL,
)

_VERDICTS = frozenset({PASS, FAIL, UNVERIFIED})


def parse_gate_definitions(prompt_text: str) -> dict[str, str]:
    """Read the gate definitions out of the review prompt.

    The gates are extracted rather than restated so that this harness measures
    the instrument as shipped. The spec's Boundaries forbid the harness editing
    the rubric it measures; reading the text at run time is the other half of
    that guarantee.

    Args:
        prompt_text: Contents of `skills/blog-post-review/REVIEW_PROMPT.md`.

    Returns:
        Gate id (``G1``..``G5``) to its full bullet text, in document order.

    Raises:
        ValueError: If the prompt contains no gate definitions. Returning an
            empty mapping would let a run report a flawless score over zero
            cases, which is the failure this whole harness exists to prevent.

    """
    definitions = {
        match.group("gate"): f"- **{match.group('gate')}{match.group('body')}".strip()
        for match in _GATE_BULLET.finditer(prompt_text)
    }
    if not definitions:
        raise ValueError("no gate definitions found in the review prompt")
    return definitions


def build_judge_prompt(gate_definition: str, passage: str) -> str:
    """Ask the judge to apply one gate to one passage.

    Args:
        gate_definition: The gate's text, as shipped in the review prompt.
        passage: The case's passage.

    Returns:
        The prompt. ``unverified`` is offered explicitly: without it the judge
        is forced into a pass/fail it cannot support, and the resulting rate
        stops meaning anything.

    """
    return (
        "You are applying a single publication gate to a single passage from a "
        "draft article. Apply only this gate; ignore every other quality "
        "consideration.\n\n"
        f"{gate_definition}\n\n"
        "Passage under review:\n"
        f"---\n{passage}\n---\n\n"
        "Do the verification work yourself. Return JSON only, no prose:\n"
        '{"verdict": "pass" | "fail" | "unverified", '
        '"why": "<one sentence>"}\n\n'
        'Use "pass" if the passage satisfies the gate, "fail" if it violates '
        'the gate, and "unverified" if you cannot reach a source needed to '
        "decide."
    )


def parse_verdict(raw: str) -> str:
    """Extract the verdict from the judge's reply.

    Args:
        raw: The judge's raw text, which may wrap the JSON in prose or a fence.

    Returns:
        One of ``pass``, ``fail`` or ``unverified``.

    Raises:
        ValueError: If no verdict can be read. A broken judge is deliberately
            *not* folded into ``unverified`` — that would report a harness
            failure as though it were a property of the gate under test.

    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in judge output: {raw[:120]!r}")
    try:
        payload = orjson.loads(match.group(0))
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"judge output is not valid JSON: {exc}") from exc

    verdict = str(payload.get("verdict", "")).strip().lower()
    if verdict not in _VERDICTS:
        raise ValueError(f"unrecognised verdict: {verdict!r}")
    return verdict


def select_cases(
    cases: Sequence[dict[str, Any]], gate: str | None = None
) -> list[dict[str, Any]]:
    """Filter cases to one gate, for re-running while iterating on the rubric.

    Args:
        cases: Loaded cases.
        gate: Gate id to keep, case-insensitive. ``None`` keeps everything.

    Returns:
        The selected cases, in their original order.

    Raises:
        ValueError: If the filter matches nothing — an empty selection would
            otherwise be summarised as a flawless zero-out-of-zero.

    """
    if gate is None:
        return list(cases)

    wanted = gate.upper()
    selected = [c for c in cases if str(c["gate"]).upper() == wanted]
    if not selected:
        raise ValueError(f"no calibration cases for gate {gate}")
    return selected


def run_cases(
    cases: Sequence[dict[str, Any]],
    gate_definitions: dict[str, str],
    judge: Judge,
) -> list[CaseResult]:
    """Run the judge over each case, preserving the owner's labels.

    Args:
        cases: Loaded cases.
        gate_definitions: As returned by :func:`parse_gate_definitions`.
        judge: Callable invoked once per case.

    Returns:
        One result per case, in input order.

    Raises:
        ValueError: If a case names a gate the prompt does not define — a sign
            the case set and the rubric have drifted apart.

    """
    results: list[CaseResult] = []
    for case in cases:
        gate = str(case["gate"])
        definition = gate_definitions.get(gate)
        if definition is None:
            raise ValueError(f"case {case['id']!r} names unknown gate {gate}")
        results.append(
            CaseResult(
                case_id=str(case["id"]),
                gate=gate,
                expected=str(case["expected"]),
                judged=judge(definition, str(case["passage"])),
            )
        )
    return results


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
