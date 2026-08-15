"""Tests for the B-040 review-gate calibration harness.

Deterministic and keyless by construction: the judge is stubbed everywhere, so
the suite exercises the harness and its arithmetic, never Claude. This mirrors
the spec's testing strategy — `docs/specs/review-gate-calibration.md`.
"""

from __future__ import annotations

import pytest

from scripts.calibrate_review_gate import (
    CaseResult,
    build_judge_prompt,
    parse_gate_definitions,
    parse_verdict,
    run_cases,
    select_cases,
    summarise,
)


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


REVIEW_PROMPT_EXCERPT = """\
## Step 1: Gates (five binary checks, any failure blocks publication)

- **G1 Source resolvability.** Every statistic resolves to a real locatable
  document. If you cannot reach a source, mark the claim UNVERIFIED.
- **G2 Citation fidelity.** Each cited source actually supports the specific claim
  attached to it, without overstating its sample, scope, or confidence.
- **G3 Arithmetic integrity.** Recompute every calculation.

## Step 2: Score six dimensions, 0 to 5
"""


class TestParseGateDefinitions:
    """Gate text is read out of the instrument, never restated in the harness.

    The spec's Boundaries forbid the harness editing the rubric it measures;
    reading the definitions at run time is the other half of that — a rubric
    change must not leave this file measuring a stale copy.
    """

    def test_finds_every_gate_in_the_prompt(self) -> None:
        gates = parse_gate_definitions(REVIEW_PROMPT_EXCERPT)

        assert list(gates) == ["G1", "G2", "G3"]

    def test_definition_carries_the_gate_name_and_body(self) -> None:
        gates = parse_gate_definitions(REVIEW_PROMPT_EXCERPT)

        assert "Citation fidelity" in gates["G2"]
        assert "without overstating its sample" in gates["G2"]

    def test_a_definition_does_not_bleed_into_the_next_gate(self) -> None:
        gates = parse_gate_definitions(REVIEW_PROMPT_EXCERPT)

        assert "Arithmetic integrity" not in gates["G2"]

    def test_the_last_gate_stops_at_the_next_heading(self) -> None:
        gates = parse_gate_definitions(REVIEW_PROMPT_EXCERPT)

        assert "Score six dimensions" not in gates["G3"]

    def test_a_prompt_with_no_gates_is_rejected_loudly(self) -> None:
        """Silently returning {} would report a perfect score over zero cases."""
        with pytest.raises(ValueError, match="no gate definitions"):
            parse_gate_definitions("# A prompt that has lost its gates\n")

    def test_reads_the_real_review_prompt(self) -> None:
        """Guards against the shipped prompt drifting out of the parsed shape."""
        from pathlib import Path

        text = Path("skills/blog-post-review/REVIEW_PROMPT.md").read_text(
            encoding="utf-8"
        )

        gates = parse_gate_definitions(text)

        assert list(gates) == ["G1", "G2", "G3", "G4", "G5"]


class TestBuildJudgePrompt:
    """The judge sees one gate and one passage — not the whole 99-line rubric."""

    def test_includes_the_gate_definition_and_the_passage(self) -> None:
        prompt = build_judge_prompt(
            "**G2 Citation fidelity.** Sources support claims.",
            "The nine-hour baseline.",
        )

        assert "Citation fidelity" in prompt
        assert "The nine-hour baseline." in prompt

    def test_offers_all_three_verdicts(self) -> None:
        """`unverified` must be available, or the judge is forced into a
        pass/fail it cannot support and the rate becomes uninterpretable."""
        prompt = build_judge_prompt("**G1 Source resolvability.**", "A passage.")

        assert "unverified" in prompt
        assert "pass" in prompt
        assert "fail" in prompt


class TestParseVerdict:
    """The judge answers in JSON; anything else is an error, not an `unverified`."""

    @pytest.mark.parametrize("verdict", ["pass", "fail", "unverified"])
    def test_reads_each_verdict(self, verdict: str) -> None:
        raw = f'{{"verdict": "{verdict}", "why": "x"}}'

        assert parse_verdict(raw) == verdict

    def test_tolerates_a_code_fence_and_surrounding_prose(self) -> None:
        raw = 'Here is my answer:\n```json\n{"verdict": "fail"}\n```\nHope that helps.'

        assert parse_verdict(raw) == "fail"

    def test_is_case_insensitive(self) -> None:
        assert parse_verdict('{"verdict": "FAIL"}') == "fail"

    def test_unparseable_output_raises_rather_than_counting_as_unverified(self) -> None:
        """Folding a broken judge into `unverified` would inflate a reported
        rate with what is actually a harness failure."""
        with pytest.raises(ValueError):
            parse_verdict("I could not determine a verdict.")

    def test_an_unknown_verdict_word_raises(self) -> None:
        with pytest.raises(ValueError, match="maybe"):
            parse_verdict('{"verdict": "maybe"}')


class TestSelectCases:
    """`--gate` re-runs one gate's cases while iterating."""

    CASES = [
        {"id": "a", "gate": "G1", "expected": "pass"},
        {"id": "b", "gate": "G2", "expected": "fail"},
        {"id": "c", "gate": "G2", "expected": "pass"},
    ]

    def test_no_filter_returns_everything(self) -> None:
        assert len(select_cases(self.CASES, gate=None)) == 3

    def test_filters_to_one_gate(self) -> None:
        assert [c["id"] for c in select_cases(self.CASES, gate="G2")] == ["b", "c"]

    def test_is_case_insensitive_about_the_gate_name(self) -> None:
        assert len(select_cases(self.CASES, gate="g2")) == 2

    def test_a_gate_with_no_cases_is_rejected_loudly(self) -> None:
        """An empty selection would otherwise report a flawless 0/0."""
        with pytest.raises(ValueError, match="G9"):
            select_cases(self.CASES, gate="G9")


class TestRunCases:
    """The judge is injected, so the suite never makes a model call."""

    CASES = [
        {
            "id": "case-a",
            "gate": "G2",
            "expected": "fail",
            "passage": "p1",
            "why": "w",
        },
        {
            "id": "case-b",
            "gate": "G1",
            "expected": "pass",
            "passage": "p2",
            "why": "w",
        },
    ]
    GATES = {"G1": "**G1 def**", "G2": "**G2 def**"}

    def test_returns_one_result_per_case_preserving_labels(self) -> None:
        results = run_cases(self.CASES, self.GATES, judge=lambda _g, _p: "fail")

        assert [(r.case_id, r.expected, r.judged) for r in results] == [
            ("case-a", "fail", "fail"),
            ("case-b", "pass", "fail"),
        ]

    def test_passes_the_matching_gate_definition_to_the_judge(self) -> None:
        seen: list[tuple[str, str]] = []

        def judge(gate_definition: str, passage: str) -> str:
            seen.append((gate_definition, passage))
            return "pass"

        run_cases(self.CASES, self.GATES, judge=judge)

        assert seen == [("**G2 def**", "p1"), ("**G1 def**", "p2")]

    def test_a_case_naming_an_unknown_gate_is_rejected_loudly(self) -> None:
        cases = [{"id": "x", "gate": "G7", "expected": "pass", "passage": "p"}]

        with pytest.raises(ValueError, match="G7"):
            run_cases(cases, self.GATES, judge=lambda _g, _p: "pass")

    def test_a_fixed_stub_reproduces_identical_arithmetic(self) -> None:
        """The spec's determinism criterion, end to end through the runner."""
        first = summarise(
            run_cases(self.CASES, self.GATES, judge=lambda _g, _p: "pass")
        )
        second = summarise(
            run_cases(self.CASES, self.GATES, judge=lambda _g, _p: "pass")
        )

        assert first == second
