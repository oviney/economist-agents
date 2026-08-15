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

import argparse
import asyncio
import logging
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

# The sibling renderer already validates the case schema the way this harness
# needs — a missing field is rejected loudly rather than skipped — so the loader
# is shared rather than reimplemented.
from scripts.render_calibration_review_sheet import load_cases

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

#: A fourth outcome, and deliberately not a verdict. The judge failed and said
#: nothing, so the case is counted and reported but excluded from every rate —
#: a crash must never read as the gate having reached a conclusion.
ERROR = "error"


#: Matches one gate bullet in REVIEW_PROMPT.md, stopping at the next gate or the
#: next heading so a definition cannot bleed into its neighbour.
_GATE_BULLET = re.compile(
    r"^- \*\*(?P<gate>G\d)\b(?P<body>.*?)(?=^- \*\*G\d|^#|\Z)",
    re.MULTILINE | re.DOTALL,
)

_VERDICTS = frozenset({PASS, FAIL, UNVERIFIED})

#: Last-resort read of the one field that matters, for replies whose `why`
#: string is not valid JSON. Deliberately anchored to the key name so prose
#: mentioning a verdict cannot be mistaken for one.
_VERDICT_FIELD = re.compile(r'"verdict"\s*:\s*"([A-Za-z]+)"')


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
        "decide.\n\n"
        "Keep `why` to one sentence and do not use double quotes inside it — "
        "quote the passage with single quotes if you need to."
    )


def _first_parsable_object(raw: str) -> dict[str, Any] | None:
    """Return the first JSON object in ``raw``, tolerating surrounding prose.

    Judges reason before they answer, and that reasoning can contain braces —
    a set, an interval, a quoted snippet. Matching greedily from the first
    brace to the last then fails on text that plainly contains a verdict. So
    each opening brace is tried in turn, widest span first.

    Args:
        raw: The judge's reply.

    Returns:
        The first span that parses as a JSON object, or ``None`` if none does.

    """
    end = raw.rfind("}")
    if end == -1:
        return None

    for match in re.finditer(r"\{", raw):
        if match.start() > end:
            break
        try:
            candidate = orjson.loads(raw[match.start() : end + 1])
        except orjson.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


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
    payload = _first_parsable_object(raw)
    if payload is not None:
        verdict = str(payload.get("verdict", "")).strip().lower()
    else:
        # The object did not parse. Observed cause, live on the first real run:
        # the judge quoted the passage inside its own `why` string without
        # escaping the quotes. Quoting the text under review is the normal
        # thing for a judge to do, and `why` is not a field this function
        # returns — so read the verdict directly rather than failing a run over
        # a field nothing consumes.
        match = _VERDICT_FIELD.search(raw)
        if match is None:
            raise ValueError(f"no JSON object in judge output: {raw[:120]!r}")
        verdict = match.group(1).strip().lower()
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
        try:
            judged = judge(definition, str(case["passage"]))
        except Exception as exc:
            # A judge failure is loud but not fatal: it is counted, reported and
            # excluded from every rate. Re-raising would discard the model calls
            # already spent on preceding cases, which is exactly what happened
            # on the first real run — 14 of 23 completed, all lost.
            logger.warning("case %s failed: %s", case["id"], exc)
            judged = ERROR
        results.append(
            CaseResult(
                case_id=str(case["id"]),
                gate=gate,
                expected=str(case["expected"]),
                judged=judged,
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
    # Errored cases are excluded from every denominator. Counting a crash as a
    # case the gate "got right" would understate the rates; counting it as one
    # the gate got wrong would overstate them. It reached no verdict, so it
    # belongs in neither — and the `errors` block below makes the exclusion
    # visible rather than silent.
    judged_results = [r for r in results if r.judged != ERROR]
    negatives = [r for r in judged_results if r.expected == PASS]
    positives = [r for r in judged_results if r.expected == FAIL]

    false_positives = sum(1 for r in negatives if r.judged == FAIL)
    false_negatives = sum(1 for r in positives if r.judged == PASS)
    unverified = sum(1 for r in judged_results if r.judged == UNVERIFIED)
    errors = sum(1 for r in results if r.judged == ERROR)

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
        "unverified": _rate_block(unverified, len(judged_results)),
        "errors": _rate_block(errors, len(results)),
        "per_gate": _per_gate(judged_results),
    }


#: The instrument under test. Read, never written, per the spec's Boundaries.
REVIEW_PROMPT_PATH = Path("skills/blog-post-review/REVIEW_PROMPT.md")

#: Append-only history: one row per calibration run.
DEFAULT_OUT = Path("logs/review_gate_calibration.json")

DEFAULT_CASES = Path("docs/evals/review-gate/cases")


def judge_options() -> Any:
    """Build keyless Agent SDK options for the judge.

    Returns:
        Options granting only the two tools the judge needs to resolve a
        source, and no MCP servers. Operating Constraint #3: the only LLM auth
        is the Claude subscription, so there is no API key path here.

    """
    from claude_agent_sdk import ClaudeAgentOptions

    return ClaudeAgentOptions(
        # G1 and G5 require reaching a source, which takes a search and one or
        # more fetches before the judge can answer. Six turns was not enough:
        # the first full run died on "Reached maximum number of turns (6)".
        max_turns=20,
        permission_mode="bypassPermissions",
        allowed_tools=["WebSearch", "WebFetch"],
        mcp_servers={},
        stderr=lambda line: logger.warning("judge stderr: %s", line),
    )


async def _ask_judge(prompt: str) -> str:
    """Run one judge turn and return its raw text."""
    from claude_agent_sdk import AssistantMessage, TextBlock, query

    parts: list[str] = []
    async for message in query(prompt=prompt, options=judge_options()):
        if isinstance(message, AssistantMessage):
            parts.extend(
                block.text for block in message.content if isinstance(block, TextBlock)
            )
    return "".join(parts)


def make_sdk_judge() -> Judge:
    """Build the real, keyless judge.

    Returns:
        A :data:`Judge` that runs the gate on the Claude subscription. Kept
        behind a factory so every test can inject a stub instead — the suite
        must never make a model call.

    """

    def judge(gate_definition: str, passage: str) -> str:
        raw = asyncio.run(_ask_judge(build_judge_prompt(gate_definition, passage)))
        return parse_verdict(raw)

    return judge


def append_run(path: Path, report: dict[str, Any], *, recorded_at: str) -> None:
    """Append one run to the calibration history.

    Args:
        path: History file.
        report: As returned by :func:`summarise`.
        recorded_at: ISO-8601 timestamp, passed in so runs are reproducible.

    Raises:
        ValueError: If an existing history cannot be parsed. Overwriting it
            would destroy the baseline a re-run is meant to be compared with,
            so the harness refuses rather than silently starting over.

    """
    rows: list[dict[str, Any]] = []
    if path.exists():
        try:
            parsed = orjson.loads(path.read_bytes())
        except orjson.JSONDecodeError as exc:
            raise ValueError(
                f"{path} could not be read as JSON; refusing to overwrite prior runs"
            ) from exc
        if not isinstance(parsed, list):
            raise ValueError(
                f"{path} could not be read as a list of runs; "
                "refusing to overwrite prior runs"
            )
        rows = parsed

    rows.append({"recorded_at": recorded_at, "report": report})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(rows, option=orjson.OPT_INDENT_2))


def load_last_run(path: Path) -> dict[str, Any]:
    """Return the most recent report, for `--report`.

    Raises:
        ValueError: If no run has been recorded. An empty report would read as
            a calibration result rather than the absence of one.

    """
    if not path.exists():
        raise ValueError(f"no calibration runs recorded at {path}")
    rows = orjson.loads(path.read_bytes())
    if not rows:
        raise ValueError(f"no calibration runs recorded at {path}")
    return dict(rows[-1]["report"])


def _rate_line(label: str, block: dict[str, Any], gloss: str) -> str:
    """Format one rate with its denominator, provisional marker and meaning."""
    rate = block["rate_pct"]
    shown = "—" if rate is None else f"{rate}%"
    flag = ", provisional" if block["provisional"] else ""
    return (
        f"  {label:<16} {block['count']}/{block['n']} = {shown:<7} "
        f"(n={block['n']}{flag})   {gloss}"
    )


def format_report(report: dict[str, Any]) -> str:
    """Render a report for a human deciding ADR-0018 Decision 3.

    Args:
        report: As returned by :func:`summarise`.

    Returns:
        Plain text. Deliberately carries no combined score: the promotion
        decision turns on the false-positive rate alone, and a single headline
        number would hide which direction the gate errs in.

    """
    balance = report["balance"]
    lines = [
        f"Review-gate calibration — {report['n_cases']} cases",
        "",
        f"  Set balance      {balance['negatives']} negatives / "
        f"{balance['positives']} positives ({balance['negative_pct']}% negative)",
        "",
        _rate_line(
            "False positives",
            report["false_positive"],
            "gate blocked a passage the owner passed",
        ),
        _rate_line(
            "False negatives",
            report["false_negative"],
            "gate missed a defect the owner caught",
        ),
        _rate_line(
            "Unverified",
            report["unverified"],
            "gate could not reach a source",
        ),
        _rate_line(
            "Errors",
            report["errors"],
            "judge failed; excluded from the rates above",
        ),
        "",
        "  Per-gate agreement",
    ]
    for gate, block in report["per_gate"].items():
        flag = ", provisional" if block["provisional"] else ""
        lines.append(
            f"    {gate}   {block['agreed']}/{block['n']} = "
            f"{block['agreement_pct']}%  (n={block['n']}{flag})"
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI. `--report` re-reads the last run and makes no model call."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--gate", default=None, help="Re-run one gate, e.g. G5.")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print the last recorded run and exit. Makes no model calls.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the calibration set, or re-print the last run.

    Returns:
        Process exit code.

    """
    args = _build_parser().parse_args(argv)

    if args.report:
        logger.info("%s", format_report(load_last_run(args.out)))
        return 0

    cases = select_cases(load_cases(args.cases), gate=args.gate)
    gates = parse_gate_definitions(REVIEW_PROMPT_PATH.read_text(encoding="utf-8"))
    logger.info("running %d cases against %d gates", len(cases), len(gates))

    report = summarise(run_cases(cases, gates, judge=make_sdk_judge()))
    append_run(
        args.out,
        report,
        recorded_at=datetime.now(UTC).isoformat(),
    )
    logger.info("%s", format_report(report))
    logger.info("appended run to %s", args.out)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
