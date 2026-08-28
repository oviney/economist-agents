#!/usr/bin/env python3
"""Tests for the editorial review gate calibration harness (B-040).

Spec: docs/specs/review-gate-calibration.md
Reference: 'Demystifying evals for AI agents' (Anthropic).

All tests are deterministic and offline: the model judge is stubbed so tests
exercise the harness, agreement arithmetic, case validation, and reporting.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.calibrate_review_gate as crg


@pytest.fixture
def sample_case_dir(tmp_path: Path) -> Path:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir(parents=True)

    (cases_dir / "c1_pos.yaml").write_text(
        "id: c1\n"
        "gate: G1\n"
        "expected: fail\n"
        "source: test-article\n"
        "passage: An unreferenced 50% claim.\n"
        "why: Missing attribution.\n"
    )
    (cases_dir / "c2_neg.yaml").write_text(
        "id: c2\n"
        "gate: G1\n"
        "expected: pass\n"
        "source: test-article\n"
        "passage: According to Gartner (2024), 50% of teams test daily.\n"
        "why: Accurately cited.\n"
    )
    (cases_dir / "c3_neg.yaml").write_text(
        "id: c3\n"
        "gate: G2\n"
        "expected: pass\n"
        "source: test-article\n"
        "passage: The DORA report notes 20% faster lead times.\n"
        "why: High fidelity quote.\n"
    )
    return cases_dir


class TestLoadCases:
    """Case files are parsed and validated strictly."""

    def test_load_valid_case(self, sample_case_dir: Path) -> None:
        case = crg.load_case_file(sample_case_dir / "c1_pos.yaml")
        assert case.id == "c1"
        assert case.gate == "G1"
        assert case.expected == "fail"
        assert case.source == "test-article"
        assert "50%" in case.passage
        assert "attribution" in case.why

    def test_load_all_cases_in_directory(self, sample_case_dir: Path) -> None:
        cases = crg.load_all_cases(sample_case_dir)
        assert len(cases) == 3
        ids = {c.id for c in cases}
        assert ids == {"c1", "c2", "c3"}

    def test_missing_expected_raises(self, tmp_path: Path) -> None:
        bad_case = tmp_path / "bad.yaml"
        bad_case.write_text("id: bad\ngate: G1\npassage: text\nwhy: reason\n")
        with pytest.raises(ValueError, match="missing required field 'expected'"):
            crg.load_case_file(bad_case)

    def test_invalid_expected_value_raises(self, tmp_path: Path) -> None:
        bad_case = tmp_path / "bad.yaml"
        bad_case.write_text(
            "id: bad\ngate: G1\nexpected: maybe\npassage: text\nwhy: reason\n"
        )
        with pytest.raises(ValueError, match="expected must be 'pass' or 'fail'"):
            crg.load_case_file(bad_case)

    def test_missing_why_raises(self, tmp_path: Path) -> None:
        bad_case = tmp_path / "bad.yaml"
        bad_case.write_text("id: bad\ngate: G1\nexpected: pass\npassage: text\n")
        with pytest.raises(ValueError, match="missing required field 'why'"):
            crg.load_case_file(bad_case)


class TestArithmetic:
    """Agreement arithmetic, false-positive, and false-negative calculation."""

    def test_perfect_agreement(self) -> None:
        c_pos = crg.TestCase("1", "G1", "fail", "src", "text", "why", Path("f1"))
        c_neg = crg.TestCase("2", "G1", "pass", "src", "text", "why", Path("f2"))

        results = [
            crg.EvaluationResult(c_pos, actual="fail"),
            crg.EvaluationResult(c_neg, actual="pass"),
        ]

        metrics = crg.compute_calibration_metrics(results)
        assert metrics.total_cases == 2
        assert metrics.agreed_cases == 2
        assert metrics.accuracy == 1.0
        assert metrics.false_positives == 0
        assert metrics.fp_rate == 0.0
        assert metrics.false_negatives == 0
        assert metrics.fn_rate == 0.0
        assert metrics.negative_percentage == 50.0

    def test_false_positive_and_false_negative_rates_separated(self) -> None:
        # 2 true negatives (pass), 2 true positives (fail)
        # Model predicts:
        # - neg1: fail (FP)
        # - neg2: pass (TN)
        # - pos1: pass (FN)
        # - pos2: fail (TP)
        c_neg1 = crg.TestCase("1", "G1", "pass", "src", "text", "why", Path("f1"))
        c_neg2 = crg.TestCase("2", "G1", "pass", "src", "text", "why", Path("f2"))
        c_pos1 = crg.TestCase("3", "G2", "fail", "src", "text", "why", Path("f3"))
        c_pos2 = crg.TestCase("4", "G2", "fail", "src", "text", "why", Path("f4"))

        results = [
            crg.EvaluationResult(c_neg1, actual="fail"),
            crg.EvaluationResult(c_neg2, actual="pass"),
            crg.EvaluationResult(c_pos1, actual="pass"),
            crg.EvaluationResult(c_pos2, actual="fail"),
        ]

        metrics = crg.compute_calibration_metrics(results)
        assert metrics.total_cases == 4
        assert metrics.positives == 2
        assert metrics.negatives == 2
        assert metrics.false_positives == 1
        assert metrics.fp_rate == 0.5  # 1 FP out of 2 negatives
        assert metrics.false_negatives == 1
        assert metrics.fn_rate == 0.5  # 1 FN out of 2 positives
        assert metrics.accuracy == 0.5

    def test_per_gate_breakdown(self) -> None:
        c1 = crg.TestCase("1", "G1", "pass", "src", "text", "why", Path("f1"))
        c2 = crg.TestCase("2", "G1", "fail", "src", "text", "why", Path("f2"))
        c3 = crg.TestCase("3", "G2", "fail", "src", "text", "why", Path("f3"))

        results = [
            crg.EvaluationResult(c1, actual="pass"),  # G1 correct
            crg.EvaluationResult(c2, actual="pass"),  # G1 FN
            crg.EvaluationResult(c3, actual="fail"),  # G2 correct
        ]

        metrics = crg.compute_calibration_metrics(results)
        g1_stats = metrics.by_gate["G1"]
        assert g1_stats.total == 2
        assert g1_stats.agreed == 1
        assert g1_stats.agreement_rate == 0.5
        assert g1_stats.false_negatives == 1

        g2_stats = metrics.by_gate["G2"]
        assert g2_stats.total == 1
        assert g2_stats.agreed == 1
        assert g2_stats.agreement_rate == 1.0

    def test_empty_results(self) -> None:
        metrics = crg.compute_calibration_metrics([])
        assert metrics.total_cases == 0
        assert metrics.fp_rate == 0.0
        assert metrics.fn_rate == 0.0
        assert metrics.accuracy == 0.0
        assert metrics.is_provisional is True

    def test_provisional_flag_below_twenty_cases(self) -> None:
        cases = [
            crg.EvaluationResult(
                crg.TestCase(str(i), "G1", "pass", "src", "text", "why", Path("f")),
                actual="pass",
            )
            for i in range(19)
        ]
        assert crg.compute_calibration_metrics(cases).is_provisional is True

        cases_20 = [
            crg.EvaluationResult(
                crg.TestCase(str(i), "G1", "pass", "src", "text", "why", Path("f")),
                actual="pass",
            )
            for i in range(20)
        ]
        assert crg.compute_calibration_metrics(cases_20).is_provisional is False


class TestReportGeneration:
    """Terminal and JSON report generation."""

    def test_format_terminal_report_includes_rates_and_counts(self) -> None:
        c1 = crg.TestCase("1", "G1", "pass", "src", "text", "why", Path("f1"))
        c2 = crg.TestCase("2", "G1", "fail", "src", "text", "why", Path("f2"))
        results = [
            crg.EvaluationResult(c1, actual="pass"),
            crg.EvaluationResult(c2, actual="fail"),
        ]
        metrics = crg.compute_calibration_metrics(results)
        report = crg.format_terminal_report(metrics)

        assert "False-Positive Rate (FPR)" in report
        assert "False-Negative Rate (FNR)" in report
        assert "PROVISIONAL" in report  # n=2 < 20
        assert "Gate G1" in report

    def test_to_dict_serializable(self) -> None:
        c1 = crg.TestCase("1", "G1", "pass", "src", "text", "why", Path("f1"))
        results = [crg.EvaluationResult(c1, actual="pass")]
        metrics = crg.compute_calibration_metrics(results)
        data = crg.metrics_to_dict(metrics)
        assert data["total_cases"] == 1
        assert "by_gate" in data
        assert "G1" in data["by_gate"]


class TestRunnerWithStubbedJudge:
    """Running calibration evaluation with stubbed LLM judge."""

    def test_run_calibration_with_custom_judge(self, sample_case_dir: Path) -> None:
        def stub_judge(case: crg.TestCase) -> str:
            # Deterministic stub: always match expectation
            return case.expected

        results = crg.evaluate_cases(sample_case_dir, judge_fn=stub_judge)
        assert len(results) == 3
        assert all(r.is_correct for r in results)

    def test_filter_by_gate(self, sample_case_dir: Path) -> None:
        results = crg.evaluate_cases(
            sample_case_dir,
            gate_filter="G1",
            judge_fn=lambda c: "pass",
        )
        assert len(results) == 2
        assert all(r.case.gate == "G1" for r in results)


class TestRealEvalSet:
    """Validate the production evaluation set in docs/evals/review-gate/cases."""

    def test_eval_set_meets_balance_and_count_requirements(self) -> None:
        cases = crg.load_all_cases(crg.DEFAULT_CASES_DIR)
        assert len(cases) >= 20, f"Expected at least 20 cases, found {len(cases)}"

        negatives = [c for c in cases if c.expected == "pass"]
        positives = [c for c in cases if c.expected == "fail"]
        neg_pct = (len(negatives) / len(cases)) * 100.0

        assert neg_pct >= 40.0, f"Expected >= 40% negative cases, got {neg_pct:.1f}%"
        assert len(positives) >= 8, (
            f"Expected >= 8 positive cases, got {len(positives)}"
        )

        # Assert all 5 gates are represented
        gates = {c.gate for c in cases}
        assert gates == {"G1", "G2", "G3", "G4", "G5"}


class TestMainCLI:
    """Test CLI argument handling and execution."""

    def test_main_report_missing_log_returns_one(self, tmp_path: Path) -> None:
        missing_log = tmp_path / "missing.json"
        rc = crg.main(["--report", "--out", str(missing_log)])
        assert rc == 1

    def test_main_report_existing_log_returns_zero(self, tmp_path: Path) -> None:
        log_file = tmp_path / "existing.json"
        log_file.write_text('{"total_cases": 1, "accuracy": 1.0}')
        rc = crg.main(["--report", "--out", str(log_file)])
        assert rc == 0

    def test_main_empty_cases_dir_returns_zero(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_cases"
        empty_dir.mkdir()
        rc = crg.main(["--cases", str(empty_dir)])
        assert rc == 0

    def test_main_runs_evaluation_and_writes_output(
        self, sample_case_dir: Path, tmp_path: Path
    ) -> None:
        out_file = tmp_path / "out.json"
        with patch.object(crg, "_default_llm_judge", return_value="pass"):
            rc = crg.main(["--cases", str(sample_case_dir), "--out", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        assert "total_cases" in out_file.read_text()
