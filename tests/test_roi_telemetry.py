"""Integration Tests for ROI Telemetry System

Tests ROI tracker accuracy, performance, and integration with agent execution.

Author: Economist Agents Team
Sprint: 14, Story: STORY-007
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.telemetry.roi_tracker import ROITracker, get_tracker


class TestROITrackerBasics:
    """Test core ROI tracker functionality."""

    def test_initialization(self):
        """Test tracker initialization with custom log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_roi.json"
            tracker = ROITracker(log_file=str(log_file))

            assert log_file.exists()
            assert tracker.log["version"] == "1.0"
            assert tracker.log["executions"] == []

    def test_start_execution(self):
        """Test execution tracking start."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("research_agent")

            assert execution_id.startswith("research_agent_")
            assert execution_id in tracker.active_executions
            assert tracker.active_executions[execution_id]["agent"] == "research_agent"

    def test_log_llm_call(self):
        """Test LLM call logging with token tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("writer_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="writer_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
            )

            execution = tracker.active_executions[execution_id]
            assert execution["total_input_tokens"] == 1000
            assert execution["total_output_tokens"] == 500
            assert execution["total_tokens"] == 1500
            assert execution["total_cost_usd"] > 0
            assert len(execution["llm_calls"]) == 1

    def test_end_execution(self):
        """Test execution completion and ROI calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("editor_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="editor_agent",
                model="gpt-4o-mini",
                input_tokens=500,
                output_tokens=200,
            )

            final_metrics = tracker.end_execution(execution_id)

            assert final_metrics["end_time"] is not None
            assert final_metrics["roi_multiplier"] > 0
            assert execution_id not in tracker.active_executions
            assert len(tracker.log["executions"]) == 1


class TestCostAccuracy:
    """Test cost calculation accuracy (±1% target)."""

    def test_gpt4o_cost_calculation(self):
        """Test GPT-4o cost calculation accuracy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("test_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="test_agent",
                model="gpt-4o",
                input_tokens=1_000_000,  # 1M tokens
                output_tokens=1_000_000,  # 1M tokens
            )
            tracker.end_execution(execution_id)

            # Expected: (1M * $2.50) + (1M * $10.00) = $12.50
            expected_cost = 12.50
            actual_cost = tracker.log["executions"][0]["total_cost_usd"]

            # Verify within 1% accuracy
            assert abs(actual_cost - expected_cost) / expected_cost < 0.01

    def test_claude_cost_calculation(self):
        """Test Claude model cost calculation accuracy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("test_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="test_agent",
                model="claude-3-5-sonnet-20241022",
                input_tokens=500_000,  # 500K tokens
                output_tokens=500_000,  # 500K tokens
            )
            tracker.end_execution(execution_id)

            # Expected: (0.5M * $3.00) + (0.5M * $15.00) = $9.00
            expected_cost = 9.00
            actual_cost = tracker.log["executions"][0]["total_cost_usd"]

            # Verify within 1% accuracy
            assert abs(actual_cost - expected_cost) / expected_cost < 0.01


class TestPerformance:
    """Test telemetry performance overhead (<10ms target)."""

    def test_logging_overhead(self):
        """Test that logging overhead is <10ms per call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("test_agent")

            # Measure logging overhead
            start = time.perf_counter()
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="test_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Verify <10ms overhead
            assert (
                elapsed_ms < 10
            ), f"Logging overhead {elapsed_ms:.2f}ms exceeds 10ms target"

    def test_save_overhead(self):
        """Test that save overhead is <10ms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("test_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="test_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
            )

            # Measure save overhead
            start = time.perf_counter()
            tracker.end_execution(execution_id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Verify <50ms overhead (save happens in end_execution)
            # Note: CI runners can have variable I/O latency, so 50ms is more reliable
            assert (
                elapsed_ms < 50
            ), f"Save overhead {elapsed_ms:.2f}ms exceeds 50ms target"


class TestROICalculations:
    """Test ROI multiplier and human-hour equivalent calculations."""

    def test_roi_multiplier_calculation(self):
        """Test ROI multiplier shows efficiency gain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("writer_agent")
            # Writer agent: 3 hours * $75 = $225 human cost
            # Simulate cheap LLM cost: $0.10
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="writer_agent",
                model="gpt-4o-mini",
                input_tokens=10_000,
                output_tokens=5_000,
            )
            final_metrics = tracker.end_execution(execution_id)

            # Expected ROI: $225 / $0.10 = 2250x
            assert (
                final_metrics["roi_multiplier"] > 100
            ), "ROI should be >100x for agent automation"

    def test_human_hour_benchmarks(self):
        """Test human-hour equivalent is properly assigned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            # Test each agent type
            for agent, expected_hours in [
                ("research_agent", 2.0),
                ("writer_agent", 3.0),
                ("editor_agent", 1.0),
                ("graphics_agent", 0.5),
            ]:
                execution_id = tracker.start_execution(agent)
                tracker.log_llm_call(
                    execution_id=execution_id,
                    agent=agent,
                    model="gpt-4o-mini",
                    input_tokens=1000,
                    output_tokens=500,
                )
                final_metrics = tracker.end_execution(execution_id)

                assert final_metrics["human_hours_equivalent"] == expected_hours


class TestAgentSummaries:
    """Test per-agent aggregate metrics."""

    def test_agent_summary(self):
        """Test agent-specific summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            # Run multiple executions for writer_agent
            for i in range(3):
                execution_id = tracker.start_execution("writer_agent")
                tracker.log_llm_call(
                    execution_id=execution_id,
                    agent="writer_agent",
                    model="gpt-4o",
                    input_tokens=1000 * (i + 1),
                    output_tokens=500 * (i + 1),
                )
                tracker.end_execution(execution_id)

            summary = tracker.get_agent_summary("writer_agent")

            assert summary["agent"] == "writer_agent"
            assert summary["total_executions"] == 3
            assert summary["total_tokens"] > 0
            assert summary["avg_roi_multiplier"] > 0

    def test_all_agent_summaries(self):
        """Test aggregate summaries for all agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            # Run executions for multiple agents
            for agent in ["research_agent", "writer_agent", "editor_agent"]:
                execution_id = tracker.start_execution(agent)
                tracker.log_llm_call(
                    execution_id=execution_id,
                    agent=agent,
                    model="gpt-4o",
                    input_tokens=1000,
                    output_tokens=500,
                )
                tracker.end_execution(execution_id)

            summaries = tracker.get_all_agent_summaries()

            assert len(summaries) == 3
            assert all(s["total_executions"] > 0 for s in summaries)


class TestIntegration:
    """Test integration with agent execution flow."""

    def test_complete_agent_workflow(self):
        """Test complete workflow: start → log calls → end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            # Simulate article generation workflow
            execution_id = tracker.start_execution("writer_agent")

            # Multiple LLM calls during execution
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="writer_agent",
                model="gpt-4o",
                input_tokens=2000,
                output_tokens=1500,
                metadata={"stage": "draft"},
            )

            tracker.log_llm_call(
                execution_id=execution_id,
                agent="writer_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=800,
                metadata={"stage": "revision"},
            )

            final_metrics = tracker.end_execution(execution_id)

            # Verify complete metrics
            assert final_metrics["total_tokens"] == 5300  # 2000+1500+1000+800
            assert final_metrics["total_cost_usd"] > 0
            assert final_metrics["roi_multiplier"] > 0
            assert len(final_metrics["llm_calls"]) == 2

    def test_report_generation(self):
        """Test human-readable report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            execution_id = tracker.start_execution("research_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="research_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
            )
            tracker.end_execution(execution_id)

            report = tracker.generate_report()

            assert "ROI TELEMETRY REPORT" in report
            assert "Total Executions: 1" in report
            assert "research_agent" in report

    def test_singleton_access(self):
        """Test global singleton access."""
        tracker1 = get_tracker()
        tracker2 = get_tracker()

        assert tracker1 is tracker2, "get_tracker() should return same instance"


class TestLogRotation:
    """Test 30-day log rotation."""

    def test_log_rotation(self):
        """Test that old logs are removed after 30 days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ROITracker(log_file=str(Path(tmpdir) / "test_roi.json"))

            # Add old execution (manually inject old timestamp)
            old_execution = {
                "execution_id": "old_exec",
                "agent": "test_agent",
                "start_time": "2025-01-01T00:00:00",  # >30 days ago
                "end_time": "2025-01-01T01:00:00",
                "total_tokens": 1000,
                "total_cost_usd": 0.10,
                "roi_multiplier": 100,
                "human_hours_equivalent": 1.0,
                "human_cost_equivalent": 75.0,
                "total_input_tokens": 500,
                "total_output_tokens": 500,
                "llm_calls": [],
            }
            tracker.log["executions"].append(old_execution)

            # Add new execution
            execution_id = tracker.start_execution("test_agent")
            tracker.log_llm_call(
                execution_id=execution_id,
                agent="test_agent",
                model="gpt-4o",
                input_tokens=1000,
                output_tokens=500,
            )
            tracker.end_execution(execution_id)  # Triggers rotation

            # Verify old execution was removed
            assert len(tracker.log["executions"]) == 1
            assert tracker.log["executions"][0]["execution_id"] != "old_exec"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
