#!/usr/bin/env python3
"""Chart data provenance (B-023, BUG-061).

The published chart plotted "Google: genuine defects 16%" and "Jira Frontend:
genuine defects 79%". Neither appears in any source. Both were derived by
subtracting the flaky-test share from 100 — and 100 minus a
*flaky-involvement* rate is not a defect rate, so the derivation was not merely
undeclared but meaningless.

Worse, the 16% collided with a real but unrelated Google figure (the share of
tests carrying some flakiness), so an invented number looked corroborated. That
is why the complement check fires even when the value *is* present in the brief:
a coincidental match is the most dangerous case, not the safest one.

Two checks:

``chart_value_unsourced``  a plotted value that appears nowhere in the brief
``chart_value_derived``    a value that is the complement of another series and
                           is not declared as derived

Declaring a derivation is enough to pass. Deriving is legitimate; passing a
derived quantity off as a sourced measurement is not.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

Verdict = Literal["PASS", "FAIL", "UNRESOLVED"]

# Complements are checked against these wholes, in the chart's own unit.
_WHOLES = (100.0, 1.0)
_TOLERANCE = 0.51


@dataclass(frozen=True)
class Finding:
    """One verdict about one chart series."""

    check: str
    verdict: Verdict
    metric: str
    message: str


def _brief_numbers(brief: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", brief))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalise(value: float) -> str:
    """Render a value the way it would appear in prose: 84.0 -> "84"."""
    return str(int(value)) if value == int(value) else str(value)


def check_chart_provenance(spec: dict, research_brief: str) -> list[Finding]:
    """Verify every plotted value against the research brief.

    Returns ``UNRESOLVED`` when there is no brief to check against — an
    unperformed check is never a pass.
    """
    series = spec.get("data") or []
    if not series:
        return []

    if not research_brief.strip():
        return [
            Finding(
                check="chart_value_provenance",
                verdict="UNRESOLVED",
                metric=str(item.get("metric", "?")),
                message=(
                    "No research brief supplied — chart value "
                    f"{item.get('value')} could not be checked."
                ),
            )
            for item in series
        ]

    numbers = _brief_numbers(research_brief)
    findings: list[Finding] = []

    for item in series:
        metric = str(item.get("metric", "?"))
        value = _as_float(item.get("value"))
        if value is None:
            continue
        if item.get("derived_from"):
            # A declared derivation is not expected to appear in the brief —
            # that is what declaring it means.
            continue
        if _normalise(value) not in numbers:
            findings.append(
                Finding(
                    check="chart_value_unsourced",
                    verdict="FAIL",
                    metric=metric,
                    message=(
                        f"Chart series {metric!r} plots {_normalise(value)}, which "
                        f"does not appear in the research brief."
                    ),
                )
            )

    findings.extend(_check_complements(series))
    return findings


def _check_complements(series: list[dict]) -> list[Finding]:
    """Flag any undeclared series that is another series subtracted from a whole.

    Fires even when the value happens to appear in the brief. The published
    chart's 16% *was* a real Google figure — for an entirely different
    quantity — and that coincidence is what made the fabrication persuasive.
    """
    findings: list[Finding] = []
    values: list[tuple[str, float, dict]] = []
    for item in series:
        value = _as_float(item.get("value"))
        if value is not None:
            values.append((str(item.get("metric", "?")), value, item))

    for metric, value, item in values:
        if item.get("derived_from"):
            continue
        for other_metric, other_value, other_item in values:
            if other_metric == metric:
                continue
            if other_item.get("derived_from"):
                # Don't accuse a base series of being the complement of the
                # series that was openly derived from it.
                continue
            for whole in _WHOLES:
                if abs((whole - other_value) - value) <= _TOLERANCE:
                    findings.append(
                        Finding(
                            check="chart_value_derived",
                            verdict="FAIL",
                            metric=metric,
                            message=(
                                f"Chart series {metric!r} plots "
                                f"{_normalise(value)}, which is "
                                f"{_normalise(whole)} minus "
                                f"{_normalise(other_value)} ({other_metric!r}). "
                                f"A complement is a derivation, not a "
                                f"measurement — declare it with 'derived_from' "
                                f"or cite it."
                            ),
                        )
                    )
                    break
            else:
                continue
            break
    return findings


def summarise(findings: list[Finding]) -> dict[str, int]:
    """Counts by verdict, keeping UNRESOLVED distinct from PASS."""
    return {
        "pass": sum(1 for f in findings if f.verdict == "PASS"),
        "fail": sum(1 for f in findings if f.verdict == "FAIL"),
        "unresolved": sum(1 for f in findings if f.verdict == "UNRESOLVED"),
    }
