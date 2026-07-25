#!/usr/bin/env python3
"""B-021 · Claim provenance and units (BUG-059).

Two errors of the same root cause reached production: the research brief stores
numeric *values* stripped of their unit and the sentence that produced them, and
Stage 3 re-associates a bare number with whatever claim it is writing.

- ``0.02 cents`` in the source became ``$0.02`` in the article. 100x, and it
  propagated into a stated "280-fold gap" where the real ratio is ~28,000.
- ``45%`` of *projects containing a cluster* became ``45%`` of *root causes*,
  a figure the cited paper does not report at all.

The existing stat audit passes both, because it only asserts
``stat in research_brief``. It has never asserted that the brief entry is
correctly united or correctly scoped. Spec defect, not implementation bug.
"""

from __future__ import annotations

from scripts.claim_provenance import (
    check_claim_provenance,
    extract_figures,
)

# The brief, as the sources actually state things.
_BRIEF = """
Leinen et al. (ICST 2024): automatically rerunning a failed test case incurs a
mere cost of 0.02 cents, while a manual investigation of a pipeline failure
costs $5.67 in developer time.

Parry et al. (2025): 10 of 22 projects, 45%, contained at least one cluster of
co-failing flaky tests. The predominant causes were networking issues and
instabilities in external dependencies.

Micco (Google, 2016): about 84% of transitions from pass to fail involve a
flaky test, against roughly 1.5% of all test runs returning a flaky result.
"""


def _article(body: str) -> str:
    return f"---\nlayout: post\ntitle: t\n---\n\n{body}\n"


class TestFigureExtraction:
    def test_reads_dollars_cents_and_percentages(self) -> None:
        figures = extract_figures("It costs $5.67, or 0.02 cents, about 84%.")
        pairs = {(f.number, f.unit) for f in figures}

        assert ("5.67", "usd") in pairs
        assert ("0.02", "cents") in pairs
        assert ("84", "percent") in pairs

    def test_cents_wins_over_a_bare_number(self) -> None:
        figures = extract_figures("a mere cost of 0.02 cents")
        assert [f.unit for f in figures] == ["cents"]

    def test_captures_surrounding_context(self) -> None:
        figures = extract_figures("45%, contained at least one cluster of tests")
        assert "cluster" in figures[0].context


class TestUnitPreservation:
    def test_dollars_where_the_source_says_cents_fails(self) -> None:
        """The exact BUG-059 error that shipped."""
        article = _article(
            "manual investigation costs $5.67 in developer time, versus $0.02 "
            "for an automatic rerun."
        )
        findings = check_claim_provenance(article, _BRIEF)
        units = [f for f in findings if f.check == "figure_unit"]

        assert units, "expected a unit finding"
        assert units[0].verdict == "FAIL"
        assert "0.02" in units[0].message
        assert "cents" in units[0].message

    def test_correct_units_pass(self) -> None:
        article = _article(
            "manual investigation costs $5.67 in developer time, against 0.02 "
            "cents for an automatic rerun."
        )
        findings = check_claim_provenance(article, _BRIEF)

        assert not [
            f for f in findings if f.check == "figure_unit" and f.verdict == "FAIL"
        ]

    def test_a_figure_absent_from_the_brief_is_flagged_unsourced(self) -> None:
        article = _article("Some 73% of teams do this, apparently.")
        findings = check_claim_provenance(article, _BRIEF)
        unsourced = [f for f in findings if f.check == "figure_unsourced"]

        assert unsourced and unsourced[0].verdict == "FAIL"
        assert "73" in unsourced[0].message


class TestNumberScope:
    def test_number_reattached_to_a_different_subject_fails(self) -> None:
        """45% of projects-with-clusters, re-served as 45% of root causes."""
        article = _article(
            "More usefully, nearly half of all flakiness, 45%, traces to a "
            "single root cause: asynchronous wait errors."
        )
        findings = check_claim_provenance(article, _BRIEF)
        scope = [f for f in findings if f.check == "figure_scope"]

        assert scope, "expected a scope finding for the re-attached 45%"
        assert scope[0].verdict == "FAIL"
        assert "45" in scope[0].message

    def test_number_used_in_its_own_context_passes(self) -> None:
        article = _article(
            "A 2025 analysis found that 45% of projects contained at least one "
            "cluster of co-failing flaky tests."
        )
        findings = check_claim_provenance(article, _BRIEF)

        assert not [
            f for f in findings if f.check == "figure_scope" and f.verdict == "FAIL"
        ]

    def test_paraphrase_is_not_treated_as_a_scope_error(self) -> None:
        """Rewording must survive. A gate that fires on synonyms gets ignored."""
        article = _article(
            "Google reports that 84% of pass-to-fail transitions involve a "
            "flaky test."
        )
        findings = check_claim_provenance(article, _BRIEF)

        assert not [
            f for f in findings if f.check == "figure_scope" and f.verdict == "FAIL"
        ]


class TestBoundaries:
    def test_no_brief_means_unresolved_not_pass(self) -> None:
        article = _article("It costs $5.67 per investigation.")
        findings = check_claim_provenance(article, "")

        assert findings
        assert all(f.verdict == "UNRESOLVED" for f in findings)

    def test_frontmatter_figures_are_ignored(self) -> None:
        article = (
            "---\nlayout: post\ntitle: t\ndate: 2026-07-24\n"
            "description: 84% of things\n---\n\nBody with no figures.\n"
        )
        findings = check_claim_provenance(article, _BRIEF)

        assert not [f for f in findings if f.verdict == "FAIL"]

    def test_references_section_is_ignored(self) -> None:
        """Years and page numbers in citations are not claims."""
        article = _article(
            "Body text.\n\n## References\n\n"
            "1. Leinen, F. et al. ICST 2024, pp. 329 to 340.\n"
        )
        findings = check_claim_provenance(article, _BRIEF)

        assert not [f for f in findings if f.verdict == "FAIL"]


class TestCorpusAcceptance:
    def test_flags_both_figures_that_shipped_wrong(self) -> None:
        article = _article(
            "Manual investigation costs $5.67, versus $0.02 for an automatic "
            "rerun, a 280-fold gap. More usefully, nearly half of all "
            "flakiness, 45%, traces to a single root cause: asynchronous wait "
            "errors."
        )
        findings = check_claim_provenance(article, _BRIEF)
        failed = {f.check for f in findings if f.verdict == "FAIL"}

        assert "figure_unit" in failed, "the 100x unit error was not caught"
        assert "figure_scope" in failed, "the re-scoped 45% was not caught"
