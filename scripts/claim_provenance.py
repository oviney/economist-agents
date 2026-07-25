#!/usr/bin/env python3
"""Claim provenance and unit preservation (B-021, BUG-059).

Two production errors shared one root cause: the research brief stores numeric
*values* stripped of their unit and of the sentence that produced them, and
Stage 3 re-associates a bare number with whatever claim it happens to be
writing.

- ``0.02 cents`` in the source became ``$0.02`` in the article. A 100x error
  that then propagated into a stated "280-fold gap" where the real ratio is
  roughly 28,000.
- ``45%`` of *projects containing a cluster* was re-served as ``45%`` of
  *root causes* — a figure the cited paper does not report at all, and which
  carried the article's only actionable recommendation.

The existing stat audit (``_shared.audit_article_stats``) passes both, because
it only asserts ``stat in research_brief``. It has never asserted that the brief
entry is correctly united or correctly scoped, so it passed a fabricated
statistic while working exactly as specified. That is a specification defect to
correct, not an implementation bug to patch — which is why this lives beside it
rather than inside it.

Three checks, all deterministic and offline:

``figure_unit``       a number carried into the article under a different unit
``figure_scope``      a number re-attached to a different subject
``figure_unsourced``  a number in the article that is not in the brief at all
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

Verdict = Literal["PASS", "FAIL", "UNRESOLVED"]

Unit = Literal["usd", "cents", "percent", "bare"]

# Words either side of a figure that we treat as its subject.
_CONTEXT_WINDOW = 90
# Share of the brief context's significant words that must reappear around the
# figure in the article before we accept it as the same claim.
_SCOPE_MATCH_MIN = 1

_STOPWORDS = {
    "about",
    "after",
    "against",
    "almost",
    "also",
    "another",
    "around",
    "because",
    "been",
    "being",
    "between",
    "both",
    "contained",
    "could",
    "from",
    "have",
    "into",
    "least",
    "more",
    "most",
    "much",
    "nearly",
    "only",
    "other",
    "over",
    "roughly",
    "single",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "until",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}

# A figure is a number optionally preceded by "$" and optionally followed by
# "%" or the word "cents". Years are excluded — they are not claims.
_FIGURE = re.compile(
    r"(?P<dollar>\$)?"
    r"(?P<number>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?P<pct>\s*%)?"
    r"(?P<cents>\s*cents?\b)?",
    re.IGNORECASE,
)

_YEAR = re.compile(r"^(19|20)\d{2}$")


@dataclass(frozen=True)
class Figure:
    """A number, the unit it was written with, and the words around it."""

    number: str
    unit: Unit
    context: str


@dataclass(frozen=True)
class Finding:
    """One verdict about one figure."""

    check: str
    verdict: Verdict
    number: str
    message: str


def _unit_of(match: re.Match[str]) -> Unit:
    if match.group("cents"):
        return "cents"
    if match.group("dollar"):
        return "usd"
    if match.group("pct"):
        return "percent"
    return "bare"


def _significant(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z]{4,}", text.lower())
        if w not in _STOPWORDS
    }


def extract_figures(text: str) -> list[Figure]:
    """Pull every quantitative figure out of ``text`` with its unit and context."""
    figures: list[Figure] = []
    for match in _FIGURE.finditer(text):
        number = match.group("number")
        unit = _unit_of(match)
        # A bare four-digit number is a year or a page reference, not a claim.
        if unit == "bare" and _YEAR.match(number.replace(",", "")):
            continue
        start = max(0, match.start() - _CONTEXT_WINDOW)
        end = min(len(text), match.end() + _CONTEXT_WINDOW)
        figures.append(
            Figure(number=number, unit=unit, context=text[start:end])
        )
    return figures


def _body_of(article: str) -> str:
    """Strip frontmatter and the References section — neither carries claims."""
    text = article
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    refs = re.search(r"^##\s+References\s*$", text, re.MULTILINE)
    if refs:
        text = text[: refs.start()]
    return text


def check_claim_provenance(article: str, research_brief: str) -> list[Finding]:
    """Verify every figure in the article against the research brief.

    Returns ``UNRESOLVED`` findings when there is no brief to check against —
    an unperformed check is never a pass.
    """
    body = _body_of(article)
    article_figures = extract_figures(body)
    if not article_figures:
        return []

    if not research_brief.strip():
        return [
            Finding(
                check="figure_provenance",
                verdict="UNRESOLVED",
                number=fig.number,
                message=(
                    f"No research brief supplied — {fig.number} could not be "
                    f"checked. Not verified, not a pass."
                ),
            )
            for fig in article_figures
        ]

    brief_figures = extract_figures(research_brief)
    by_number: dict[str, list[Figure]] = {}
    for fig in brief_figures:
        by_number.setdefault(fig.number, []).append(fig)

    findings: list[Finding] = []
    for fig in article_figures:
        sources = by_number.get(fig.number)
        if not sources:
            findings.append(
                Finding(
                    check="figure_unsourced",
                    verdict="FAIL",
                    number=fig.number,
                    message=(
                        f"The figure {fig.number} does not appear in the "
                        f"research brief at all."
                    ),
                )
            )
            continue

        findings.extend(_check_unit(fig, sources))
        findings.extend(_check_scope(fig, sources))

    return findings


def _check_unit(fig: Figure, sources: list[Figure]) -> list[Finding]:
    """A number must keep the unit its source gave it."""
    source_units = {s.unit for s in sources}
    if fig.unit in source_units:
        return []
    # A bare number in the article beside a united source is a formatting
    # choice, not a unit error — only a *conflicting* unit is a defect.
    if fig.unit == "bare":
        return []
    concrete = {u for u in source_units if u != "bare"}
    if not concrete:
        return []
    return [
        Finding(
            check="figure_unit",
            verdict="FAIL",
            number=fig.number,
            message=(
                f"The figure {fig.number} is written as {fig.unit} in the "
                f"article but the source gives it as {sorted(concrete)}. "
                f"Unit lost in transit."
            ),
        )
    ]


def _check_scope(fig: Figure, sources: list[Figure]) -> list[Finding]:
    """A number must stay attached to the subject its source attached it to."""
    article_words = _significant(fig.context)
    if not article_words:
        return []

    for source in sources:
        shared = article_words & _significant(source.context)
        if len(shared) >= _SCOPE_MATCH_MIN:
            return []

    return [
        Finding(
            check="figure_scope",
            verdict="FAIL",
            number=fig.number,
            message=(
                f"The figure {fig.number} appears in the brief but attached to a "
                f"different subject. Article context: "
                f"{fig.context.strip()[:110]!r}. No shared subject with the "
                f"source. A number re-attached to a new claim is not a sourced "
                f"claim."
            ),
        )
    ]


def summarise(findings: list[Finding]) -> dict[str, int]:
    """Counts by verdict, keeping UNRESOLVED distinct from PASS."""
    return {
        "pass": sum(1 for f in findings if f.verdict == "PASS"),
        "fail": sum(1 for f in findings if f.verdict == "FAIL"),
        "unresolved": sum(1 for f in findings if f.verdict == "UNRESOLVED"),
    }
