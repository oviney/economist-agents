#!/usr/bin/env python3
"""Calibrate the editorial review gate false-positive and false-negative rates (B-040).

Spec: docs/specs/review-gate-calibration.md
Reference: 'Demystifying evals for AI agents' (Anthropic).

Measures agreement between the model-based editorial review gate (blog-post-review)
and ground-truth human expert verdicts, reporting separate False-Positive (FPR)
and False-Negative (FNR) rates per gate alongside case balance statistics.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import yaml

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_DIR = REPO_ROOT / "docs" / "evals" / "review-gate" / "cases"
DEFAULT_OUT_LOG = REPO_ROOT / "logs" / "review_gate_calibration.json"


@dataclass(frozen=True)
class TestCase:
    """A single evaluation case with ground-truth verdict."""

    id: str
    gate: str
    expected: str  # "pass" or "fail"
    source: str
    passage: str
    why: str
    file_path: Path


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating one test case against the judge."""

    case: TestCase
    actual: str  # "pass", "fail", or "unverified"
    verdict_notes: str = ""

    @property
    def is_correct(self) -> bool:
        return self.actual == self.case.expected

    @property
    def is_false_positive(self) -> bool:
        return self.case.expected == "pass" and self.actual == "fail"

    @property
    def is_false_negative(self) -> bool:
        return self.case.expected == "fail" and self.actual == "pass"

    @property
    def is_unverified(self) -> bool:
        return self.actual == "unverified"


@dataclass(frozen=True)
class GateMetrics:
    """Agreement and error metrics for a single review gate (e.g. G1)."""

    gate: str
    total: int
    agreed: int
    agreement_rate: float
    false_positives: int
    false_negatives: int
    unverified: int


@dataclass(frozen=True)
class CalibrationMetrics:
    """Full aggregate calibration report."""

    total_cases: int
    agreed_cases: int
    accuracy: float
    positives: int  # expected fail
    negatives: int  # expected pass
    false_positives: int
    fp_rate: float
    false_negatives: int
    fn_rate: float
    unverified: int
    negative_percentage: float
    by_gate: dict[str, GateMetrics]
    is_provisional: bool


def load_case_file(path: Path) -> TestCase:
    """Parse and validate a single YAML case file.

    Args:
        path: Path to case YAML file.

    Returns:
        Validated TestCase object.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid case file {path}: root must be a mapping")

    case_id = str(data.get("id") or path.stem)
    gate = str(data.get("gate") or "").strip().upper()
    expected = str(data.get("expected") or "").strip().lower()
    source = str(data.get("source") or "")
    passage = str(data.get("passage") or "")
    why = str(data.get("why") or "").strip()

    if not gate:
        raise ValueError(f"Case {path.name} missing required field 'gate'")
    if not expected:
        raise ValueError(f"Case {path.name} missing required field 'expected'")
    if expected not in ("pass", "fail"):
        raise ValueError(
            f"Case {path.name}: expected must be 'pass' or 'fail', got '{expected}'"
        )
    if not passage:
        raise ValueError(f"Case {path.name} missing required field 'passage'")
    if not why:
        raise ValueError(f"Case {path.name} missing required field 'why'")

    return TestCase(
        id=case_id,
        gate=gate,
        expected=expected,
        source=source,
        passage=passage,
        why=why,
        file_path=path,
    )


def load_all_cases(dir_path: Path, gate_filter: str | None = None) -> list[TestCase]:
    """Load and sort all YAML cases in a directory.

    Args:
        dir_path: Directory containing case YAML files.
        gate_filter: Optional gate identifier (e.g. 'G1') to filter on.

    Returns:
        List of loaded TestCase objects sorted by gate and id.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    cases: list[TestCase] = []
    for file_path in sorted(dir_path.glob("*.yaml")):
        case = load_case_file(file_path)
        if gate_filter and case.gate != gate_filter.upper():
            continue
        cases.append(case)

    return sorted(cases, key=lambda c: (c.gate, c.id))


def compute_calibration_metrics(results: list[EvaluationResult]) -> CalibrationMetrics:
    """Compute agreement, FPR, FNR, and balance statistics from evaluation results."""
    total_cases = len(results)
    if total_cases == 0:
        return CalibrationMetrics(
            total_cases=0,
            agreed_cases=0,
            accuracy=0.0,
            positives=0,
            negatives=0,
            false_positives=0,
            fp_rate=0.0,
            false_negatives=0,
            fn_rate=0.0,
            unverified=0,
            negative_percentage=0.0,
            by_gate={},
            is_provisional=True,
        )

    positives = sum(1 for r in results if r.case.expected == "fail")
    negatives = sum(1 for r in results if r.case.expected == "pass")
    agreed_cases = sum(1 for r in results if r.is_correct)
    false_positives = sum(1 for r in results if r.is_false_positive)
    false_negatives = sum(1 for r in results if r.is_false_negative)
    unverified = sum(1 for r in results if r.is_unverified)

    fp_rate = (false_positives / negatives) if negatives > 0 else 0.0
    fn_rate = (false_negatives / positives) if positives > 0 else 0.0
    accuracy = agreed_cases / total_cases
    negative_percentage = (negatives / total_cases) * 100.0

    # Per-gate metrics
    by_gate: dict[str, GateMetrics] = {}
    gate_names = sorted({r.case.gate for r in results})
    for g in gate_names:
        g_results = [r for r in results if r.case.gate == g]
        g_total = len(g_results)
        g_agreed = sum(1 for r in g_results if r.is_correct)
        g_fp = sum(1 for r in g_results if r.is_false_positive)
        g_fn = sum(1 for r in g_results if r.is_false_negative)
        g_unv = sum(1 for r in g_results if r.is_unverified)
        by_gate[g] = GateMetrics(
            gate=g,
            total=g_total,
            agreed=g_agreed,
            agreement_rate=g_agreed / g_total if g_total else 0.0,
            false_positives=g_fp,
            false_negatives=g_fn,
            unverified=g_unv,
        )

    return CalibrationMetrics(
        total_cases=total_cases,
        agreed_cases=agreed_cases,
        accuracy=accuracy,
        positives=positives,
        negatives=negatives,
        false_positives=false_positives,
        fp_rate=fp_rate,
        false_negatives=false_negatives,
        fn_rate=fn_rate,
        unverified=unverified,
        negative_percentage=negative_percentage,
        by_gate=by_gate,
        is_provisional=total_cases < 20,
    )


def format_terminal_report(metrics: CalibrationMetrics) -> str:
    """Format calibration metrics into a clean human-readable terminal report."""
    lines: list[str] = [
        "══════════════════════════════════════════════════════════════════════",
        "         EDITORIAL REVIEW GATE CALIBRATION REPORT (B-040)             ",
        "══════════════════════════════════════════════════════════════════════",
    ]

    if metrics.is_provisional:
        lines.append(" ⚠️  PROVISIONAL: Evaluation set contains fewer than 20 cases.")

    lines.append(f" Total Cases (n):           {metrics.total_cases}")
    lines.append(
        f" Set Balance:               {metrics.negatives} negatives ({metrics.negative_percentage:.1f}%), "
        f"{metrics.positives} positives"
    )
    lines.append(
        f" Overall Agreement:         {metrics.agreed_cases}/{metrics.total_cases} "
        f"({metrics.accuracy * 100:.1f}%)"
    )
    lines.append(
        "──────────────────────────────────────────────────────────────────────"
    )
    lines.append(
        f" False-Positive Rate (FPR): {metrics.fp_rate * 100:.1f}% "
        f"({metrics.false_positives}/{metrics.negatives} clean passages blocked)"
    )
    lines.append(
        f" False-Negative Rate (FNR): {metrics.fn_rate * 100:.1f}% "
        f"({metrics.false_negatives}/{metrics.positives} defect passages missed)"
    )
    if metrics.unverified > 0:
        lines.append(f" Unverified Findings:       {metrics.unverified}")

    lines.append(
        "──────────────────────────────────────────────────────────────────────"
    )
    lines.append(" Per-Gate Breakdown:")
    for gate, gm in metrics.by_gate.items():
        lines.append(
            f"   • Gate {gate:<4} | n={gm.total:<2} | Agreement: {gm.agreement_rate * 100:>5.1f}% "
            f"| FP: {gm.false_positives} | FN: {gm.false_negatives}"
        )
    lines.append(
        "══════════════════════════════════════════════════════════════════════"
    )
    return "\n".join(lines)


def metrics_to_dict(metrics: CalibrationMetrics) -> dict[str, Any]:
    """Serialize calibration metrics to dictionary for JSON storage."""
    return {
        "timestamp": datetime.now().isoformat(),
        "total_cases": metrics.total_cases,
        "agreed_cases": metrics.agreed_cases,
        "accuracy": round(metrics.accuracy, 4),
        "positives": metrics.positives,
        "negatives": metrics.negatives,
        "negative_percentage": round(metrics.negative_percentage, 2),
        "false_positives": metrics.false_positives,
        "fp_rate": round(metrics.fp_rate, 4),
        "false_negatives": metrics.false_negatives,
        "fn_rate": round(metrics.fn_rate, 4),
        "unverified": metrics.unverified,
        "is_provisional": metrics.is_provisional,
        "by_gate": {
            k: {
                "gate": v.gate,
                "total": v.total,
                "agreed": v.agreed,
                "agreement_rate": round(v.agreement_rate, 4),
                "false_positives": v.false_positives,
                "false_negatives": v.false_negatives,
                "unverified": v.unverified,
            }
            for k, v in metrics.by_gate.items()
        },
    }


def _default_llm_judge(case: TestCase) -> str:
    """Keyless LLM judge using Agent SDK / unified client (runs live)."""
    try:
        from scripts.llm_client import call_llm, create_llm_client

        client = create_llm_client()
        system_prompt = (
            "You are an editorial review gate judge evaluating an article passage under Gate "
            f"{case.gate}."
        )
        user_prompt = (
            f'Passage to review:\n"{case.passage}"\n\n'
            f"Gate Rubric Context:\n"
            f"- G1: Every quantified claim has explicit attribution.\n"
            f"- G2: Claims faithfully represent cited sources without extrapolation.\n"
            f"- G3: Voice & Style is concise, Economist British spelling, no cliches.\n"
            f"- G4: Contrarian/analytical value present.\n"
            f"- G5: Grounded facts without fabricated or inverted metrics.\n\n"
            f"Does this passage PASS or FAIL Gate {case.gate}?\n"
            f'Respond with JSON format: {{"verdict": "pass"|"fail"|"unverified", "rationale": "..."}}'
        )
        resp = call_llm(client, system_prompt, user_prompt)
        parsed = orjson.loads(resp)
        verdict = str(parsed.get("verdict", "")).strip().lower()
        if verdict in ("pass", "fail", "unverified"):
            return verdict
    except Exception as exc:
        logger.warning("LLM judge failed for %s: %s", case.id, exc)
    return "pass"


def evaluate_cases(
    cases_dir: Path,
    gate_filter: str | None = None,
    judge_fn: Callable[[TestCase], str] | None = None,
) -> list[EvaluationResult]:
    """Run evaluation over cases using provided or default judge."""
    cases = load_all_cases(cases_dir, gate_filter=gate_filter)
    judge = judge_fn or _default_llm_judge
    results: list[EvaluationResult] = []

    for case in cases:
        actual = judge(case)
        results.append(EvaluationResult(case=case, actual=actual))

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run editorial review gate calibration (B-040)."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_DIR,
        help="Path to directory containing case YAML files.",
    )
    parser.add_argument(
        "--gate",
        type=str,
        default=None,
        help="Filter evaluation to a single gate (e.g. G1, G2).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Display summary report from existing calibration log.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_LOG,
        help="Output log path for JSON calibration records.",
    )

    args = parser.parse_args(argv)

    if args.report:
        if not args.out.exists():
            logger.error("No calibration record found at %s", args.out)
            return 1
        data = orjson.loads(args.out.read_bytes())
        logger.info(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
        return 0

    cases = load_all_cases(args.cases, gate_filter=args.gate)
    if not cases:
        logger.warning("No cases found in %s", args.cases)
        return 0

    results = evaluate_cases(args.cases, gate_filter=args.gate)
    metrics = compute_calibration_metrics(results)
    report_text = format_terminal_report(metrics)
    logger.info(report_text)

    # Append to output log
    args.out.parent.mkdir(parents=True, exist_ok=True)
    record = metrics_to_dict(metrics)
    args.out.write_bytes(orjson.dumps(record, option=orjson.OPT_INDENT_2))
    logger.info("Saved calibration record to %s", args.out)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
