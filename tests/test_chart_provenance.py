#!/usr/bin/env python3
"""B-023 · Chart data provenance (BUG-061).

The published chart plotted "Google: genuine defects 16%" and "Jira Frontend:
genuine defects 79%". Neither figure appears in any source. Both were produced
by subtracting the flaky-test share from 100 — and the 16% then collided with an
unrelated real Google figure (the share of tests carrying some flakiness), which
made an invented number look corroborated.

The chart asserted the article's strongest false claim more baldly than the
prose did, and the external prose review missed it entirely. Reading the
rendered PNG found it. This makes that a gate rather than a habit.
"""

from __future__ import annotations

from scripts.chart_provenance import check_chart_provenance

_BRIEF = """
Micco (Google, 2016): about 84% of transitions from pass to fail involve a
flaky test, against roughly 1.5% of all test runs returning a flaky result.
Around 16% of Google's tests carry some degree of flakiness.

Atlassian: flakiness has been responsible for as much as 21% of master build
failures in the Jira Frontend repository.
"""

# The chart exactly as it shipped.
_PUBLISHED_CHART = {
    "title": "A Red Build Is Probably Lying",
    "subtitle": "Share of failing builds attributable to flaky tests rather than defective code, %",
    "source": "Google Testing Blog; Atlassian engineering blog",
    "data": [
        {"metric": "Google: flaky tests", "value": 84, "unit": "%"},
        {"metric": "Google: genuine defects", "value": 16, "unit": "%"},
        {"metric": "Jira Frontend: flaky tests", "value": 21, "unit": "%"},
        {"metric": "Jira Frontend: genuine defects", "value": 79, "unit": "%"},
    ],
}


class TestValueProvenance:
    def test_value_absent_from_the_brief_fails(self) -> None:
        spec = {
            "title": "t",
            "data": [{"metric": "Invented", "value": 63, "unit": "%"}],
        }
        findings = check_chart_provenance(spec, _BRIEF)
        unsourced = [f for f in findings if f.check == "chart_value_unsourced"]

        assert unsourced and unsourced[0].verdict == "FAIL"
        assert "63" in unsourced[0].message

    def test_value_present_in_the_brief_passes(self) -> None:
        spec = {
            "title": "t",
            "data": [{"metric": "Google: flaky tests", "value": 84, "unit": "%"}],
        }
        findings = check_chart_provenance(spec, _BRIEF)

        assert not [f for f in findings if f.verdict == "FAIL"]

    def test_no_brief_is_unresolved_not_pass(self) -> None:
        spec = {"title": "t", "data": [{"metric": "m", "value": 84, "unit": "%"}]}
        findings = check_chart_provenance(spec, "")

        assert findings
        assert all(f.verdict == "UNRESOLVED" for f in findings)


class TestComplementDerivation:
    def test_series_derived_by_subtracting_from_100_is_named(self) -> None:
        """The BUG-061 signature: 100 - 84 = 16, presented as a source figure."""
        findings = check_chart_provenance(_PUBLISHED_CHART, _BRIEF)
        derived = [f for f in findings if f.check == "chart_value_derived"]

        assert derived, "expected the complement check to fire"
        messages = " ".join(f.message for f in derived)
        assert "79" in messages
        assert "21" in messages

    def test_a_declared_derived_series_is_allowed(self) -> None:
        """Deriving is fine when it is declared. Passing it off as sourced is not."""
        spec = {
            "title": "t",
            "data": [
                {"metric": "Flaky", "value": 21, "unit": "%"},
                {
                    "metric": "Remainder",
                    "value": 79,
                    "unit": "%",
                    "derived_from": "100 - 21",
                },
            ],
        }
        findings = check_chart_provenance(spec, _BRIEF)

        assert not [f for f in findings if f.verdict == "FAIL"]

    def test_unrelated_values_that_happen_to_sum_to_100_are_not_flagged(self) -> None:
        """Both sourced, so neither is a fabricated complement."""
        spec = {
            "title": "t",
            "data": [
                {"metric": "A", "value": 84, "unit": "%"},
                {"metric": "B", "value": 16, "unit": "%"},
            ],
        }
        # 16 IS in this brief (share of Google tests carrying flakiness), so the
        # value check passes — but the collision is exactly what made the
        # invented number look corroborated, so the derived check must still
        # speak up.
        findings = check_chart_provenance(spec, _BRIEF)
        derived = [f for f in findings if f.check == "chart_value_derived"]

        assert derived, "a sourced-looking complement still needs flagging"
        assert derived[0].verdict in {"FAIL", "UNRESOLVED"}


class TestCorpusAcceptance:
    def test_the_published_chart_would_not_have_shipped(self) -> None:
        findings = check_chart_provenance(_PUBLISHED_CHART, _BRIEF)

        assert [f for f in findings if f.verdict == "FAIL"], (
            "the chart that shipped must not pass the gate"
        )

    def test_an_honest_single_source_chart_passes(self) -> None:
        spec = {
            "title": "Flaky tests in Google's CI",
            "data": [
                {"metric": "Pass-to-fail transitions involving a flake", "value": 84, "unit": "%"},
                {"metric": "Test runs returning a flaky result", "value": 1.5, "unit": "%"},
            ],
        }
        findings = check_chart_provenance(spec, _BRIEF)

        assert not [f for f in findings if f.verdict == "FAIL"]
