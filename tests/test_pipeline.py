"""Tests for pipeline.py — run_pipeline and cost log append (issue #325)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import orjson
import pytest

from src.agent_sdk.pipeline import PipelineResult, run_pipeline

# ── helpers ───────────────────────────────────────────────────────────────────


def _fake_stage3():
    m = MagicMock()
    m.article = "---\ntitle: Test\n---\n\nBody text here."
    m.chart_data = {"title": "Chart"}
    m.total_cost_usd = 0.05
    m.writer_cost_usd = 0.04
    m.graphics_cost_usd = 0.01
    m.research_cost_usd = 0.0
    m.writer_model = "claude-sonnet-4-6"
    m.graphics_model = "claude-sonnet-4-6"
    m.wall_seconds = 1.2
    m.research_brief_chars = 500
    m.article_chars = 200
    m.stat_audit_removed = 0
    return m


def _fake_stage4(article: str):
    m = MagicMock()
    m.article = article
    m.editorial_score = 82
    m.gates_passed = 4
    m.publication_ready = True
    m.publication_validator_passed = True
    m.publication_validator_issues = []
    m.wall_seconds = 0.05
    return m


# ── tests ─────────────────────────────────────────────────────────────────────


class TestRunPipeline:
    def test_returns_pipeline_result_with_correct_field_types(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.COST_LOG_PATH", tmp_path / "costs.jsonl"
        )
        stage3 = _fake_stage3()

        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
        ):
            result = asyncio.run(run_pipeline("AI Testing"))

        assert isinstance(result, PipelineResult)
        assert isinstance(result.total_cost_usd, float)
        assert isinstance(result.article, str)
        assert isinstance(result.gates_passed, int)
        assert isinstance(result.publication_validator_passed, bool)

    def test_appends_valid_jsonl_entry_to_cost_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "costs.jsonl"
        monkeypatch.setattr("src.agent_sdk.pipeline.COST_LOG_PATH", log_path)
        stage3 = _fake_stage3()

        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
        ):
            asyncio.run(run_pipeline("AI Testing"))

        assert log_path.exists(), "Cost log was not created"
        lines = log_path.read_bytes().splitlines()
        assert len(lines) == 1, f"Expected 1 log entry, got {len(lines)}"
        entry = orjson.loads(lines[0])
        for key in ("timestamp", "total_cost_usd", "topic", "gates_passed"):
            assert key in entry, f"Missing key '{key}' in log entry"
        assert entry["topic"] == "AI Testing"
        assert entry["total_cost_usd"] == pytest.approx(0.05)

    def test_cost_log_written_once_per_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "costs.jsonl"
        monkeypatch.setattr("src.agent_sdk.pipeline.COST_LOG_PATH", log_path)
        stage3 = _fake_stage3()

        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
        ):
            asyncio.run(run_pipeline("Topic One"))
            asyncio.run(run_pipeline("Topic Two"))

        lines = log_path.read_bytes().splitlines()
        assert len(lines) == 2, (
            f"Expected 2 log entries (one per run), got {len(lines)}"
        )

    def test_returns_result_even_when_cost_log_write_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.COST_LOG_PATH", tmp_path / "costs.jsonl"
        )
        stage3 = _fake_stage3()

        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
            patch(
                "src.agent_sdk.pipeline._append_cost_log",
                side_effect=PermissionError("read-only"),
            ),
        ):
            result = asyncio.run(run_pipeline("AI Testing"))

        assert isinstance(result, PipelineResult)
        assert result.total_cost_usd == pytest.approx(0.05)


class TestRoiTelemetryWiring:
    """Issue #333 AC2: run_pipeline records cost via ROITracker."""

    def test_pipeline_records_writer_and_graphics_cost_in_roi_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Writer + graphics costs from PipelineResult land in execution_roi.json."""
        from src.telemetry.roi_tracker import ROITracker

        # Isolate the cost log and the ROI tracker singleton.
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.COST_LOG_PATH", tmp_path / "costs.jsonl"
        )
        roi_log = tmp_path / "execution_roi.json"
        isolated_tracker = ROITracker(log_file=str(roi_log))
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.get_tracker", lambda: isolated_tracker
        )

        stage3 = _fake_stage3()
        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
        ):
            asyncio.run(run_pipeline("AI Testing"))

        executions = isolated_tracker.log["executions"]
        assert len(executions) == 1, "Expected one pipeline execution in ROI log"
        execution = executions[0]
        assert execution["agent"] == "pipeline"
        # Total recorded cost equals writer + graphics from the SDK, not a
        # token-times-pricing recomputation.
        assert execution["total_cost_usd"] == pytest.approx(
            stage3.writer_cost_usd + stage3.graphics_cost_usd
        )
        # Both calls are individually recorded so per-model attribution holds.
        models = [call["model"] for call in execution["llm_calls"]]
        assert stage3.writer_model in models
        assert stage3.graphics_model in models

    def test_pipeline_returns_result_when_roi_logging_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ROI telemetry failure is non-fatal — pipeline still returns a result."""
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.COST_LOG_PATH", tmp_path / "costs.jsonl"
        )
        monkeypatch.setattr(
            "src.agent_sdk.pipeline._record_roi",
            MagicMock(side_effect=RuntimeError("disk full")),
        )

        stage3 = _fake_stage3()
        with (
            patch("src.agent_sdk.pipeline.run_stage3", return_value=stage3),
            patch(
                "src.agent_sdk.pipeline.run_stage4",
                return_value=_fake_stage4(stage3.article),
            ),
        ):
            result = asyncio.run(run_pipeline("AI Testing"))

        assert isinstance(result, PipelineResult)
        assert result.total_cost_usd == pytest.approx(0.05)
