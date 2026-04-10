"""Tests for scripts/token_usage.py — token usage logging and cost estimation."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from token_usage import (
    MODEL_COSTS,
    estimate_cost,
    log_token_usage,
    print_ci_summary,
    read_usage_log,
    summarise_usage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write a list of dicts as JSONL to *path*."""
    import orjson

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for rec in records:
            fh.write(orjson.dumps(rec) + b"\n")


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_gpt4o_known_rates(self):
        """gpt-4o: $2.50/1M prompt, $10.00/1M completion."""
        cost = estimate_cost("gpt-4o", 1_000_000, 0)
        assert cost == pytest.approx(2.50, rel=1e-6)

        cost = estimate_cost("gpt-4o", 0, 1_000_000)
        assert cost == pytest.approx(10.00, rel=1e-6)

    def test_gpt4o_mini_known_rates(self):
        cost = estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.15 + 0.60, rel=1e-6)

    def test_gpt4_turbo_known_rates(self):
        cost = estimate_cost("gpt-4-turbo", 1_000_000, 0)
        assert cost == pytest.approx(10.00, rel=1e-6)

    def test_unknown_model_uses_default(self):
        """Unknown model falls back to gpt-4o rates."""
        default_prompt_rate, default_completion_rate = MODEL_COSTS["default"]
        expected = (
            500 * default_prompt_rate + 200 * default_completion_rate
        ) / 1_000_000
        assert estimate_cost("gpt-unknown-xyz", 500, 200) == pytest.approx(
            expected, rel=1e-6
        )

    def test_zero_tokens(self):
        assert estimate_cost("gpt-4o", 0, 0) == 0.0

    def test_typical_call(self):
        """Smoke-test the example from the issue: 1240 prompt + 387 completion."""
        cost = estimate_cost("gpt-4o", 1240, 387)
        # 1240 * 2.50/1M + 387 * 10.00/1M = 0.0031 + 0.00387 = 0.00697
        assert cost == pytest.approx(0.00697, rel=1e-3)


# ---------------------------------------------------------------------------
# log_token_usage
# ---------------------------------------------------------------------------


class TestLogTokenUsage:
    def test_returns_estimated_cost(self, tmp_path):
        log_file = tmp_path / "usage.jsonl"
        cost = log_token_usage("gpt-4o", 1000, 500, 1500, log_file=log_file)
        assert cost == pytest.approx(estimate_cost("gpt-4o", 1000, 500), rel=1e-6)

    def test_appends_jsonl_record(self, tmp_path):
        import orjson

        log_file = tmp_path / "usage.jsonl"
        log_token_usage("gpt-4o", 100, 50, 150, log_file=log_file)

        lines = log_file.read_bytes().splitlines()
        assert len(lines) == 1
        rec = orjson.loads(lines[0])
        assert rec["model"] == "gpt-4o"
        assert rec["prompt_tokens"] == 100
        assert rec["completion_tokens"] == 50
        assert rec["total_tokens"] == 150
        assert rec["estimated_cost_usd"] == pytest.approx(
            estimate_cost("gpt-4o", 100, 50), rel=1e-6
        )
        assert "timestamp" in rec

    def test_multiple_calls_append(self, tmp_path):
        log_file = tmp_path / "usage.jsonl"
        log_token_usage("gpt-4o", 100, 50, 150, log_file=log_file)
        log_token_usage("gpt-4o-mini", 200, 80, 280, log_file=log_file)

        lines = log_file.read_bytes().splitlines()
        assert len(lines) == 2

    def test_prints_summary_to_stdout(self, tmp_path, capsys):
        log_file = tmp_path / "usage.jsonl"
        log_token_usage("gpt-4o", 1240, 387, 1627, log_file=log_file)

        captured = capsys.readouterr()
        assert "[token-usage]" in captured.out
        assert "gpt-4o" in captured.out
        assert "prompt=1240" in captured.out
        assert "completion=387" in captured.out
        assert "total=1627" in captured.out
        assert "est_cost=$" in captured.out

    def test_creates_parent_directory(self, tmp_path):
        log_file = tmp_path / "deep" / "nested" / "usage.jsonl"
        log_token_usage("gpt-4o", 10, 5, 15, log_file=log_file)
        assert log_file.exists()

    def test_warns_on_write_failure(self, tmp_path, caplog):
        """OSError during write should log a warning, not raise."""
        import logging

        log_file = tmp_path / "usage.jsonl"
        with (
            patch("token_usage.Path.open", side_effect=OSError("disk full")),
            caplog.at_level(logging.WARNING, logger="token_usage"),
        ):
            # Should not raise
            log_token_usage("gpt-4o", 10, 5, 15, log_file=log_file)


# ---------------------------------------------------------------------------
# read_usage_log
# ---------------------------------------------------------------------------


class TestReadUsageLog:
    def test_returns_empty_list_when_file_missing(self, tmp_path):
        records = read_usage_log(log_file=tmp_path / "nonexistent.jsonl")
        assert records == []

    def test_reads_records(self, tmp_path):
        log_file = tmp_path / "usage.jsonl"
        sample = [
            {
                "timestamp": "2026-04-10T00:00:00+00:00",
                "model": "gpt-4o",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.00075,
            }
        ]
        _write_jsonl(log_file, sample)

        records = read_usage_log(log_file=log_file)
        assert len(records) == 1
        assert records[0]["model"] == "gpt-4o"

    def test_reads_multiple_records(self, tmp_path):
        log_file = tmp_path / "usage.jsonl"
        _write_jsonl(
            log_file,
            [
                {
                    "model": "gpt-4o",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "estimated_cost_usd": 0.0,
                },
                {
                    "model": "gpt-4o-mini",
                    "prompt_tokens": 200,
                    "completion_tokens": 80,
                    "total_tokens": 280,
                    "estimated_cost_usd": 0.0,
                },
            ],
        )
        records = read_usage_log(log_file=log_file)
        assert len(records) == 2

    def test_skips_blank_lines(self, tmp_path):
        log_file = tmp_path / "usage.jsonl"
        import orjson

        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("wb") as fh:
            fh.write(orjson.dumps({"model": "gpt-4o", "prompt_tokens": 1}) + b"\n")
            fh.write(b"\n")
            fh.write(orjson.dumps({"model": "gpt-4o", "prompt_tokens": 2}) + b"\n")

        records = read_usage_log(log_file=log_file)
        assert len(records) == 2


# ---------------------------------------------------------------------------
# summarise_usage
# ---------------------------------------------------------------------------


class TestSummariseUsage:
    def test_empty_records(self):
        assert summarise_usage([]) == {}

    def test_single_record(self):
        records = [
            {
                "model": "gpt-4o",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.00075,
            }
        ]
        summary = summarise_usage(records)
        assert "gpt-4o" in summary
        assert summary["gpt-4o"]["calls"] == 1
        assert summary["gpt-4o"]["prompt_tokens"] == 100
        assert summary["gpt-4o"]["completion_tokens"] == 50
        assert summary["gpt-4o"]["total_tokens"] == 150

    def test_aggregates_multiple_records(self):
        records = [
            {
                "model": "gpt-4o",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.0005,
            },
            {
                "model": "gpt-4o",
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300,
                "estimated_cost_usd": 0.001,
            },
        ]
        summary = summarise_usage(records)
        assert summary["gpt-4o"]["calls"] == 2
        assert summary["gpt-4o"]["prompt_tokens"] == 300
        assert summary["gpt-4o"]["completion_tokens"] == 150
        assert summary["gpt-4o"]["total_tokens"] == 450
        assert summary["gpt-4o"]["estimated_cost_usd"] == pytest.approx(
            0.0015, rel=1e-6
        )

    def test_separates_models(self):
        records = [
            {
                "model": "gpt-4o",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.0005,
            },
            {
                "model": "gpt-4o-mini",
                "prompt_tokens": 200,
                "completion_tokens": 80,
                "total_tokens": 280,
                "estimated_cost_usd": 0.0001,
            },
        ]
        summary = summarise_usage(records)
        assert "gpt-4o" in summary
        assert "gpt-4o-mini" in summary
        assert summary["gpt-4o"]["calls"] == 1
        assert summary["gpt-4o-mini"]["calls"] == 1


# ---------------------------------------------------------------------------
# print_ci_summary
# ---------------------------------------------------------------------------


class TestPrintCiSummary:
    def test_no_op_when_env_var_not_set(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        log_file = tmp_path / "usage.jsonl"
        # Should not raise and should not create any file
        print_ci_summary(log_file=log_file)

    def test_no_op_when_log_file_empty(self, tmp_path, monkeypatch):
        summary_file = tmp_path / "summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        log_file = tmp_path / "usage.jsonl"
        print_ci_summary(log_file=log_file)
        # Summary file should not be created / written
        assert not summary_file.exists()

    def test_writes_markdown_table(self, tmp_path, monkeypatch):
        summary_file = tmp_path / "summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

        log_file = tmp_path / "usage.jsonl"
        _write_jsonl(
            log_file,
            [
                {
                    "model": "gpt-4o",
                    "prompt_tokens": 1240,
                    "completion_tokens": 387,
                    "total_tokens": 1627,
                    "estimated_cost_usd": 0.00697,
                }
            ],
        )

        print_ci_summary(log_file=log_file)

        content = summary_file.read_text()
        assert "## OpenAI Token Usage (this run)" in content
        assert "gpt-4o" in content
        assert "1,240" in content
        assert "387" in content
        assert "0.0070" in content

    def test_appends_to_existing_summary(self, tmp_path, monkeypatch):
        summary_file = tmp_path / "summary.md"
        summary_file.write_text("# Existing content\n")
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

        log_file = tmp_path / "usage.jsonl"
        _write_jsonl(
            log_file,
            [
                {
                    "model": "gpt-4o",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "estimated_cost_usd": 0.001,
                }
            ],
        )

        print_ci_summary(log_file=log_file)
        content = summary_file.read_text()
        assert "# Existing content" in content
        assert "## OpenAI Token Usage" in content


# ---------------------------------------------------------------------------
# Integration: llm_client._call_openai logs usage
# ---------------------------------------------------------------------------


class TestLLMClientLogsUsage:
    """Ensure _call_openai feeds usage to log_token_usage."""

    def test_call_openai_logs_usage(self, tmp_path, capsys):
        from unittest.mock import Mock, patch

        import llm_client

        log_file = tmp_path / "usage.jsonl"

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="hello"))]
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15
        mock_response.usage = mock_usage
        mock_client.chat.completions.create.return_value = mock_response

        with patch("token_usage._DEFAULT_LOG_FILE", log_file):
            result = llm_client._call_openai(
                mock_client, "gpt-4o", "sys", "usr", 100, 0.5
            )

        assert result == "hello"

        records = read_usage_log(log_file=log_file)
        assert len(records) == 1
        assert records[0]["model"] == "gpt-4o"
        assert records[0]["prompt_tokens"] == 10
