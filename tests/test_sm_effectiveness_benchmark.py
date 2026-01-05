#!/usr/bin/env python3
"""
Tests for SM Agent Effectiveness Benchmark

Tests the benchmark infrastructure (not the SM agent itself).
Validates test scenario definitions, evaluation logic, and report generation.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmarks.measure_sm_effectiveness import SMEffectivenessBenchmark

# Skip tests if no API keys available (CI environment)
requires_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY or OPENAI_API_KEY",
)


@requires_api_key
class TestSMEffectivenessBenchmark:
    """Test suite for SM effectiveness benchmark infrastructure."""

    def test_initialization(self):
        """Test benchmark initializes with agent registry."""
        benchmark = SMEffectivenessBenchmark()

        assert benchmark.sm_agent is not None
        assert "name" in benchmark.sm_agent
        assert "llm_client" in benchmark.sm_agent
        assert len(benchmark.test_scenarios) == 10
        assert benchmark.results == []

    def test_scenario_definition_structure(self):
        """Test all scenarios have required fields."""
        benchmark = SMEffectivenessBenchmark()

        required_fields = [
            "id",
            "category",
            "request",
            "expected_routing",
            "expected_dor_compliance",
            "rationale",
        ]

        for scenario in benchmark.test_scenarios:
            for field in required_fields:
                assert field in scenario, f"Scenario {scenario['id']} missing {field}"

    def test_scenario_diversity(self):
        """Test scenarios cover diverse request types."""
        benchmark = SMEffectivenessBenchmark()

        categories = {s["category"] for s in benchmark.test_scenarios}

        # Should have at least these categories
        expected_categories = {
            "clear_task",
            "vague_request",
            "out_of_scope",
            "needs_clarification",
        }

        assert expected_categories.issubset(categories), (
            f"Missing categories: {expected_categories - categories}"
        )

        # Should have mix of expected outcomes
        routings = {s["expected_routing"] for s in benchmark.test_scenarios}
        assert "accept_to_backlog" in routings
        assert "escalate_for_clarification" in routings

    def test_evaluate_response_correct_acceptance(self):
        """Test evaluation for correctly accepted request."""
        benchmark = SMEffectivenessBenchmark()

        scenario = {
            "id": 1,
            "expected_routing": "accept_to_backlog",
            "expected_dor_compliance": True,
        }

        agent_result = {
            "success": True,
            "response": {
                "decision": "accept",
                "dor_compliant": True,
                "reasoning": "Clear requirements",
            },
            "duration_seconds": 1.5,
        }

        evaluation = benchmark._evaluate_response(scenario, agent_result)

        assert evaluation["routing_correct"] is True
        assert evaluation["dor_compliance_correct"] is True
        assert evaluation["overall_correct"] is True
        assert "All correct" in evaluation["notes"]

    def test_evaluate_response_correct_escalation(self):
        """Test evaluation for correctly escalated vague request."""
        benchmark = SMEffectivenessBenchmark()

        scenario = {
            "id": 3,
            "expected_routing": "escalate_for_clarification",
            "expected_dor_compliance": False,
        }

        agent_result = {
            "success": True,
            "response": {
                "decision": "escalate",
                "dor_compliant": False,
                "reasoning": "Missing specifics",
                "questions_for_user": ["What does 'better' mean?"],
            },
            "duration_seconds": 1.2,
        }

        evaluation = benchmark._evaluate_response(scenario, agent_result)

        assert evaluation["routing_correct"] is True
        assert evaluation["dor_compliance_correct"] is True
        assert evaluation["overall_correct"] is True

    def test_evaluate_response_incorrect_routing(self):
        """Test evaluation catches incorrect routing decision."""
        benchmark = SMEffectivenessBenchmark()

        scenario = {
            "id": 3,
            "expected_routing": "escalate_for_clarification",
            "expected_dor_compliance": False,
        }

        # Agent incorrectly accepts vague request
        agent_result = {
            "success": True,
            "response": {
                "decision": "accept",
                "dor_compliant": True,
                "reasoning": "Looks good",
            },
            "duration_seconds": 1.0,
        }

        evaluation = benchmark._evaluate_response(scenario, agent_result)

        assert evaluation["routing_correct"] is False
        assert evaluation["overall_correct"] is False
        assert "Expected routing" in evaluation["notes"]

    def test_evaluate_response_agent_failure(self):
        """Test evaluation handles agent call failures gracefully."""
        benchmark = SMEffectivenessBenchmark()

        scenario = {
            "id": 1,
            "expected_routing": "accept_to_backlog",
            "expected_dor_compliance": True,
        }

        agent_result = {
            "success": False,
            "response": None,
            "error": "API timeout",
            "duration_seconds": 30.0,
        }

        evaluation = benchmark._evaluate_response(scenario, agent_result)

        assert evaluation["routing_correct"] is False
        assert evaluation["dor_compliance_correct"] is False
        assert evaluation["overall_correct"] is False
        assert "Agent call failed" in evaluation["notes"]

    def test_evaluate_response_flexible_routing(self):
        """Test evaluation accepts flexible routing for edge cases."""
        benchmark = SMEffectivenessBenchmark()

        scenario = {
            "id": 6,
            "expected_routing": "refuse_or_escalate",
            "expected_dor_compliance": False,
        }

        # Agent escalates instead of refusing - should be acceptable
        agent_result = {
            "success": True,
            "response": {
                "decision": "escalate",
                "dor_compliant": False,
                "reasoning": "Need business justification",
            },
            "duration_seconds": 1.3,
        }

        evaluation = benchmark._evaluate_response(scenario, agent_result)

        assert evaluation["routing_correct"] is True

    def test_save_report_creates_file(self):
        """Test report generation creates valid JSON file."""
        benchmark = SMEffectivenessBenchmark()

        test_results = {
            "benchmark_name": "Test",
            "metrics": {"total_tests": 10, "dor_compliance_rate_percent": 95.0},
            "overall_result": "PASS",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.json"
            benchmark.save_report(test_results, output_path)

            assert output_path.exists()

            # Validate JSON structure
            with open(output_path) as f:
                loaded = json.load(f)

            assert loaded["benchmark_name"] == "Test"
            assert loaded["metrics"]["total_tests"] == 10
            assert loaded["overall_result"] == "PASS"

    def test_scenario_ids_unique(self):
        """Test all scenario IDs are unique."""
        benchmark = SMEffectivenessBenchmark()

        ids = [s["id"] for s in benchmark.test_scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_scenario_ids_sequential(self):
        """Test scenario IDs are sequential from 1."""
        benchmark = SMEffectivenessBenchmark()

        ids = sorted([s["id"] for s in benchmark.test_scenarios])
        expected = list(range(1, len(benchmark.test_scenarios) + 1))
        assert ids == expected, f"IDs should be 1-{len(benchmark.test_scenarios)}"

    def test_clear_task_scenarios_have_specifics(self):
        """Test clear_task scenarios include required specifics."""
        benchmark = SMEffectivenessBenchmark()

        clear_tasks = [
            s for s in benchmark.test_scenarios if s["category"] == "clear_task"
        ]

        assert len(clear_tasks) >= 4, "Should have at least 4 clear task examples"

        for scenario in clear_tasks:
            # Clear tasks should have measurable criteria in request
            request = scenario["request"].lower()
            assert any(
                keyword in request
                for keyword in [
                    "within",
                    "under",
                    "should",
                    "must",
                    "format",
                    "standard",
                ]
            ), f"Clear task {scenario['id']} lacks specific criteria"

    def test_vague_scenarios_lack_specifics(self):
        """Test vague scenarios are appropriately under-specified."""
        benchmark = SMEffectivenessBenchmark()

        vague_requests = [
            s
            for s in benchmark.test_scenarios
            if s["category"] in ["vague_request", "needs_clarification"]
        ]

        assert len(vague_requests) >= 3, "Should have at least 3 vague request examples"

        for scenario in vague_requests:
            # Vague requests should NOT be DoR compliant
            assert scenario["expected_dor_compliance"] is False, (
                f"Vague scenario {scenario['id']} incorrectly marked DoR compliant"
            )

    @patch("scripts.benchmarks.measure_sm_effectiveness.call_llm")
    def test_send_request_handles_llm_success(self, mock_call_llm):
        """Test _send_request_to_sm handles successful LLM response."""
        benchmark = SMEffectivenessBenchmark()

        mock_call_llm.return_value = json.dumps(
            {
                "decision": "accept",
                "dor_compliant": True,
                "reasoning": "Clear requirements",
                "suggested_story_title": "Add feature X",
            }
        )

        scenario = benchmark.test_scenarios[0]
        result = benchmark._send_request_to_sm(scenario)

        assert result["success"] is True
        assert result["response"]["decision"] == "accept"
        assert result["duration_seconds"] >= 0  # Mocked calls can be near-instant
        assert result["error"] is None

    @patch("scripts.benchmarks.measure_sm_effectiveness.call_llm")
    def test_send_request_handles_llm_failure(self, mock_call_llm):
        """Test _send_request_to_sm handles LLM errors gracefully."""
        benchmark = SMEffectivenessBenchmark()

        mock_call_llm.side_effect = Exception("API timeout")

        scenario = benchmark.test_scenarios[0]
        result = benchmark._send_request_to_sm(scenario)

        assert result["success"] is False
        assert result["response"] is None
        assert "timeout" in result["error"].lower()
        assert result["duration_seconds"] >= 0  # Mocked calls can be near-instant

    @patch("scripts.benchmarks.measure_sm_effectiveness.call_llm")
    def test_send_request_handles_invalid_json(self, mock_call_llm):
        """Test _send_request_to_sm handles malformed JSON responses."""
        benchmark = SMEffectivenessBenchmark()

        mock_call_llm.return_value = "This is not JSON at all"

        scenario = benchmark.test_scenarios[0]
        result = benchmark._send_request_to_sm(scenario)

        assert result["success"] is False
        assert "json" in result["error"].lower() or "no json" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
