"""Tests for the B-040 review-gate calibration harness.

Deterministic and keyless by construction: the judge is stubbed everywhere, so
the suite exercises the harness and its arithmetic, never Claude. This mirrors
the spec's testing strategy — `docs/specs/review-gate-calibration.md`.
"""

from __future__ import annotations

import pytest

from scripts.calibrate_review_gate import CaseResult, summarise


def _result(expected: str, judged: str, gate: str = "G2") -> CaseResult:
    """Build a result whose id is derived from its verdicts, for readability."""
    return CaseResult(
        case_id=f"{gate}-{expected}-{judged}",
        gate=gate,
        expected=expected,
        judged=judged,
    )


class TestFalsePositiveRate:
    """A false positive is a negative case the gate flagged: expected pass, judged fail."""

    def test_counts_only_negatives_judged_fail(self) -> None:
        results = [
            _result("pass", "fail"),  # false positive
            _result("pass", "pass"),  # correct
            _result("fail", "fail"),  # correct, and NOT a false positive
        ]

        report = summarise(results)

        assert report["false_positive"]["count"] == 1

    def test_denominator_is_the_negatives_not_the_whole_set(self) -> None:
        results = [
            _result("pass", "fail"),
            _result("pass", "pass"),
            _result("fail", "fail"),
            _result("fail", "fail"),
        ]

        report = summarise(results)

        # Two negatives, one flagged — 50%, not 25% of all four cases.
        assert report["false_positive"]["n"] == 2
        assert report["false_positive"]["rate_pct"] == 50.0

    def test_unverified_on_a_negative_is_not_a_false_positive(self) -> None:
        """`unverified` is its own outcome; folding it into FP would inflate the
        number ADR-0018 Decision 3 turns on."""
        results = [_result("pass", "unverified"), _result("pass", "pass")]

        report = summarise(results)

        assert report["false_positive"]["count"] == 0


class TestFalseNegativeRate:
    """A false negative is a positive case the gate missed: expected fail, judged pass."""

    def test_counts_only_positives_judged_pass(self) -> None:
        results = [
            _result("fail", "pass"),  # false negative
            _result("fail", "fail"),  # correct
            _result("pass", "pass"),  # correct, and NOT a false negative
        ]

        report = summarise(results)

        assert report["false_negative"]["count"] == 1

    def test_denominator_is_the_positives(self) -> None:
        results = [
            _result("fail", "pass"),
            _result("fail", "pass"),
            _result("fail", "fail"),
            _result("fail", "fail"),
            _result("pass", "pass"),
        ]

        report = summarise(results)

        assert report["false_negative"]["n"] == 4
        assert report["false_negative"]["rate_pct"] == 50.0


class TestRatesAreNeverAveraged:
    """The spec's Boundaries list averaging the two error rates as a **Never**."""

    def test_report_exposes_no_combined_accuracy_figure(self) -> None:
        results = [_result("pass", "fail"), _result("fail", "pass")]

        report = summarise(results)

        forbidden = {"accuracy", "error_rate", "overall_rate", "combined_rate", "f1"}
        assert forbidden.isdisjoint(report.keys())

    def test_the_two_rates_are_reported_under_separate_keys(self) -> None:
        results = [_result("pass", "fail"), _result("fail", "pass")]

        report = summarise(results)

        assert report["false_positive"]["rate_pct"] == 100.0
        assert report["false_negative"]["rate_pct"] == 100.0


class TestUnverified:
    """`unverified` is a third outcome with its own denominator (spec, LGTM 2026-08-05)."""

    def test_counted_separately_over_the_whole_set(self) -> None:
        results = [
            _result("pass", "unverified"),
            _result("fail", "unverified"),
            _result("fail", "fail"),
            _result("pass", "pass"),
        ]

        report = summarise(results)

        assert report["unverified"]["count"] == 2
        assert report["unverified"]["n"] == 4
        assert report["unverified"]["rate_pct"] == 50.0


class TestEveryRateCarriesN:
    """ "Report a rate without `n`" is a **Never** in the spec's Boundaries."""

    @pytest.mark.parametrize(
        "section", ["false_positive", "false_negative", "unverified"]
    )
    def test_n_accompanies_every_rate(self, section: str) -> None:
        report = summarise([_result("pass", "pass"), _result("fail", "fail")])

        assert "n" in report[section]
        assert "rate_pct" in report[section]


class TestProvisionalLabelling:
    """A rate from fewer than 20 cases is labelled provisional in the output itself."""

    def test_small_denominator_is_marked_provisional(self) -> None:
        report = summarise([_result("pass", "pass")] * 3)

        assert report["false_positive"]["provisional"] is True

    def test_denominator_of_twenty_is_not_provisional(self) -> None:
        report = summarise([_result("pass", "pass")] * 20)

        assert report["false_positive"]["provisional"] is False

    def test_the_real_set_size_still_yields_provisional_rates(self) -> None:
        """23 cases split 12/11 means *both* error rates are provisional — the
        headline number ADR-0018 wants cannot be non-provisional at this n."""
        results = [_result("pass", "pass")] * 12 + [_result("fail", "fail")] * 11

        report = summarise(results)

        assert report["false_positive"]["provisional"] is True
        assert report["false_negative"]["provisional"] is True


class TestBalance:
    """The set's positive/negative balance is reported on every run."""

    def test_reports_counts_and_percentage(self) -> None:
        results = [_result("pass", "pass")] * 12 + [_result("fail", "fail")] * 11

        report = summarise(results)

        assert report["balance"]["negatives"] == 12
        assert report["balance"]["positives"] == 11
        assert report["balance"]["negative_pct"] == 52.2


class TestPerGateAgreement:
    """Per-gate agreement, so a gate that is wrong in one direction is visible."""

    def test_agreement_is_per_gate_with_its_own_n(self) -> None:
        results = [
            _result("fail", "fail", gate="G1"),
            _result("pass", "pass", gate="G1"),
            _result("fail", "pass", gate="G2"),
        ]

        report = summarise(results)

        assert report["per_gate"]["G1"]["agreed"] == 2
        assert report["per_gate"]["G1"]["n"] == 2
        assert report["per_gate"]["G1"]["agreement_pct"] == 100.0
        assert report["per_gate"]["G2"]["agreement_pct"] == 0.0

    def test_gates_are_ordered_so_reports_diff_cleanly(self) -> None:
        results = [
            _result("pass", "pass", gate="G5"),
            _result("pass", "pass", gate="G1"),
            _result("pass", "pass", gate="G3"),
        ]

        report = summarise(results)

        assert list(report["per_gate"]) == ["G1", "G3", "G5"]


class TestDegenerateCases:
    """All-pass, all-fail and empty, per the spec's testing strategy."""

    def test_empty_set_yields_no_rates_rather_than_zero(self) -> None:
        """A rate of 0.0 from zero cases is a claim; None is the honest value."""
        report = summarise([])

        assert report["n_cases"] == 0
        assert report["false_positive"]["rate_pct"] is None
        assert report["false_negative"]["rate_pct"] is None

    def test_all_negative_set_has_no_false_negative_rate(self) -> None:
        report = summarise([_result("pass", "pass")] * 5)

        assert report["false_negative"]["n"] == 0
        assert report["false_negative"]["rate_pct"] is None
        assert report["false_positive"]["rate_pct"] == 0.0

    def test_gate_that_fails_everything_is_visible_as_a_full_false_positive_rate(
        self,
    ) -> None:
        """The failure mode the balance rule exists to catch."""
        results = [_result("pass", "fail")] * 6 + [_result("fail", "fail")] * 6

        report = summarise(results)

        assert report["false_positive"]["rate_pct"] == 100.0
        assert report["false_negative"]["rate_pct"] == 0.0


class TestDeterminism:
    """Re-running with a fixed stubbed verdict reproduces byte-identical arithmetic."""

    def test_same_input_yields_equal_reports(self) -> None:
        results = [
            _result("pass", "fail", gate="G2"),
            _result("fail", "fail", gate="G4"),
            _result("pass", "unverified", gate="G1"),
        ]

        assert summarise(results) == summarise(list(reversed(results)))
