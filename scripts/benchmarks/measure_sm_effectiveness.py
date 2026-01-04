#!/usr/bin/env python3
"""
Scrum Master Agent Effectiveness Benchmark (Story 4)

Measures Scrum Master agent's routing intelligence using the new Registry pattern.
Tests real LLM responses (no mocking) across 10 diverse request scenarios.

Metrics:
- DoR Compliance Rate (Target: >90%)
- Escalation Rate (appropriate vs unnecessary)
- Routing Accuracy (correct destination for each request type)

Usage:
    python3 scripts/benchmarks/measure_sm_effectiveness.py

Output:
    docs/metrics/sm_effectiveness_report.json
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.agent_registry import AgentRegistry
from scripts.llm_client import call_llm


class SMEffectivenessBenchmark:
    """Benchmark suite for Scrum Master agent routing intelligence."""

    def __init__(self):
        """Initialize benchmark with agent registry."""
        registry = AgentRegistry()
        self.sm_agent = registry.get_agent("scrum-master")
        self.results: list[dict[str, Any]] = []
        self.test_scenarios = self._define_test_scenarios()

    def _define_test_scenarios(self) -> list[dict[str, Any]]:
        """Define 10 diverse test scenarios ranging from clear to vague.

        Scenarios test:
        - Clear tasks (should accept)
        - DoR-compliant requests (should accept)
        - Vague requests (should escalate/ask for clarification)
        - Out-of-scope requests (should refuse)
        - Edge cases (should handle gracefully)
        """
        return [
            {
                "id": 1,
                "category": "clear_task",
                "request": "Create a story for adding a dark mode toggle to the blog. "
                "Users want to read comfortably in low light. It should persist "
                "across sessions and respond within 100ms.",
                "expected_routing": "accept_to_backlog",
                "expected_dor_compliance": True,
                "rationale": "Clear goal, user story format, performance requirement specified",
            },
            {
                "id": 2,
                "category": "clear_task",
                "request": "We need automated chart validation to catch zone violations "
                "before publication. Must check title/data/axis zones and block "
                "publication if violations found. Should validate in under 2 seconds.",
                "expected_routing": "accept_to_backlog",
                "expected_dor_compliance": True,
                "rationale": "Clear technical requirement with measurable criteria",
            },
            {
                "id": 3,
                "category": "vague_request",
                "request": "Make the blog better.",
                "expected_routing": "escalate_for_clarification",
                "expected_dor_compliance": False,
                "rationale": "Completely vague - no specific goal, user, or success criteria",
            },
            {
                "id": 4,
                "category": "vague_request",
                "request": "Add some monitoring so we know if things break.",
                "expected_routing": "escalate_for_clarification",
                "expected_dor_compliance": False,
                "rationale": "Lacks specifics: what to monitor, what constitutes 'break', success metrics",
            },
            {
                "id": 5,
                "category": "clear_task",
                "request": "Add RSS feed support filtered by category. Users should be able "
                "to subscribe to only the topics they care about. Feed should update "
                "within 5 minutes of new post publication. Use standard RSS 2.0 format.",
                "expected_routing": "accept_to_backlog",
                "expected_dor_compliance": True,
                "rationale": "Clear user benefit, specific format, performance requirement",
            },
            {
                "id": 6,
                "category": "out_of_scope",
                "request": "Rewrite the entire codebase in Rust for better performance.",
                "expected_routing": "refuse_or_escalate",
                "expected_dor_compliance": False,
                "rationale": "Massive scope, no business justification, no user story format",
            },
            {
                "id": 7,
                "category": "needs_clarification",
                "request": "The charts look weird sometimes. Can you fix that?",
                "expected_routing": "escalate_for_clarification",
                "expected_dor_compliance": False,
                "rationale": "Vague problem description - no specifics on 'weird' or reproduction steps",
            },
            {
                "id": 8,
                "category": "clear_task",
                "request": "Create a pre-commit hook that validates commit message format. "
                "It should enforce 'Story X: Title' format and block commits that don't "
                "match. Should run in under 1 second and provide clear error messages.",
                "expected_routing": "accept_to_backlog",
                "expected_dor_compliance": True,
                "rationale": "Clear requirement with format specification and performance criteria",
            },
            {
                "id": 9,
                "category": "ambiguous_priority",
                "request": "We need better error handling. Not sure if this is urgent or "
                "can wait. Also might need logging improvements.",
                "expected_routing": "escalate_for_clarification",
                "expected_dor_compliance": False,
                "rationale": "Unclear priority, scope creep (error handling + logging), no specifics",
            },
            {
                "id": 10,
                "category": "clear_task",
                "request": "Implement search functionality for blog posts. Users should be "
                "able to search by title, content, and tags. Results should appear "
                "within 500ms for queries under 1000 posts. Highlight matching text "
                "in search results.",
                "expected_routing": "accept_to_backlog",
                "expected_dor_compliance": True,
                "rationale": "Clear user need with specific search criteria and performance target",
            },
        ]

    def _send_request_to_sm(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Send request to Scrum Master agent and capture response.

        Args:
            scenario: Test scenario with request text

        Returns:
            Dict with agent response and metadata
        """
        start_time = time.time()

        # Build prompt for SM agent
        prompt = f"""
{self.sm_agent["system_message"]}

## Current Request

User says: "{scenario["request"]}"

Your task: Analyze this request and decide:
1. Is it clear enough to create a story? (DoR compliant)
2. Should you:
   a) Accept it and create a backlog item
   b) Ask for clarification (what's missing?)
   c) Refuse it (out of scope or unreasonable)

Respond in JSON format:
{{
    "decision": "accept" | "escalate" | "refuse",
    "reasoning": "Brief explanation of your decision",
    "missing_information": ["list", "of", "missing", "details"],
    "dor_compliant": true | false,
    "suggested_story_title": "Story title if accepting",
    "questions_for_user": ["clarifying", "questions"] if escalating
}}
"""

        try:
            response_text = call_llm(
                self.sm_agent["llm_client"],
                "",  # System message in prompt
                prompt,
                max_tokens=1000,
                temperature=0.3,  # Some creativity for questions, but mostly deterministic
            )

            duration = time.time() - start_time

            # Parse JSON response
            # Find JSON block in response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx <= start_idx:
                raise ValueError("No JSON found in response")

            json_text = response_text[start_idx:end_idx]
            parsed_response = json.loads(json_text)

            return {
                "success": True,
                "response": parsed_response,
                "raw_response": response_text,
                "duration_seconds": round(duration, 2),
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "response": None,
                "raw_response": response_text if "response_text" in locals() else None,
                "duration_seconds": round(time.time() - start_time, 2),
                "error": str(e),
            }

    def _evaluate_response(
        self, scenario: dict[str, Any], agent_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate if agent's response matches expected routing.

        Args:
            scenario: Test scenario with expected behavior
            agent_result: Agent's actual response

        Returns:
            Evaluation results with correctness flags
        """
        if not agent_result["success"]:
            return {
                "routing_correct": False,
                "dor_compliance_correct": False,
                "overall_correct": False,
                "notes": f"Agent call failed: {agent_result['error']}",
            }

        response = agent_result["response"]

        # Map decision to routing
        decision_to_routing = {
            "accept": "accept_to_backlog",
            "escalate": "escalate_for_clarification",
            "refuse": "refuse_or_escalate",
        }

        actual_routing = decision_to_routing.get(
            response.get("decision", ""), "unknown"
        )
        expected_routing = scenario["expected_routing"]

        # Check routing correctness
        routing_correct = actual_routing == expected_routing

        # For flexible routing (refuse_or_escalate), accept either
        if expected_routing == "refuse_or_escalate" and actual_routing in [
            "refuse_or_escalate",
            "escalate_for_clarification",
        ]:
            routing_correct = True

        # Check DoR compliance correctness
        actual_dor = response.get("dor_compliant", False)
        expected_dor = scenario["expected_dor_compliance"]
        dor_correct = actual_dor == expected_dor

        # Overall correctness
        overall_correct = routing_correct and dor_correct

        notes = []
        if not routing_correct:
            notes.append(
                f"Expected routing '{expected_routing}', got '{actual_routing}'"
            )
        if not dor_correct:
            notes.append(f"Expected DoR {expected_dor}, got {actual_dor}")

        return {
            "routing_correct": routing_correct,
            "dor_compliance_correct": dor_correct,
            "overall_correct": overall_correct,
            "actual_routing": actual_routing,
            "actual_dor_compliant": actual_dor,
            "notes": " | ".join(notes) if notes else "All correct",
        }

    def run_benchmark(self) -> dict[str, Any]:
        """Execute benchmark across all test scenarios.

        Returns:
            Complete benchmark results with metrics
        """
        print(f"\n{'=' * 70}")
        print("SM Agent Effectiveness Benchmark (Story 4)")
        print(f"{'=' * 70}\n")
        print(f"Using agent: {self.sm_agent['name']}")
        print(f"Provider: {self.sm_agent['llm_client'].provider}")
        print(f"Model: {self.sm_agent['llm_client'].model}")
        print(f"Test scenarios: {len(self.test_scenarios)}\n")

        results = []
        correct_routing = 0
        correct_dor = 0
        escalations = 0
        accepts = 0
        refusals = 0
        total_duration = 0

        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"[{i}/{len(self.test_scenarios)}] Testing: {scenario['category']}")
            print(f"   Request: {scenario['request'][:60]}...")

            # Send request to agent
            agent_result = self._send_request_to_sm(scenario)

            # Evaluate response
            evaluation = self._evaluate_response(scenario, agent_result)

            # Count successes
            if evaluation["routing_correct"]:
                correct_routing += 1
            if evaluation["dor_compliance_correct"]:
                correct_dor += 1

            if agent_result["success"]:
                decision = agent_result["response"].get("decision", "unknown")
                if decision == "accept":
                    accepts += 1
                elif decision == "escalate":
                    escalations += 1
                elif decision == "refuse":
                    refusals += 1

                total_duration += agent_result["duration_seconds"]

            # Print result
            status = "✅" if evaluation["overall_correct"] else "❌"
            print(f"   {status} {evaluation['notes']}")
            print(f"   Duration: {agent_result['duration_seconds']}s\n")

            # Store result
            result = {
                "scenario_id": scenario["id"],
                "category": scenario["category"],
                "request": scenario["request"],
                "expected_routing": scenario["expected_routing"],
                "expected_dor_compliance": scenario["expected_dor_compliance"],
                "agent_result": agent_result,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat(),
            }
            results.append(result)

        # Calculate metrics
        total_tests = len(self.test_scenarios)
        routing_accuracy = (correct_routing / total_tests) * 100
        dor_compliance_rate = (correct_dor / total_tests) * 100
        escalation_rate = (escalations / total_tests) * 100
        avg_response_time = total_duration / total_tests if total_tests > 0 else 0

        # Overall pass/fail
        passed = dor_compliance_rate >= 90.0

        print(f"\n{'=' * 70}")
        print("BENCHMARK RESULTS")
        print(f"{'=' * 70}\n")
        print(f"Total Tests:           {total_tests}")
        print(
            f"Routing Accuracy:      {routing_accuracy:.1f}% ({correct_routing}/{total_tests})"
        )
        print(
            f"DoR Compliance Rate:   {dor_compliance_rate:.1f}% ({correct_dor}/{total_tests}) {'✅' if dor_compliance_rate >= 90 else '❌'}"
        )
        print(
            f"Escalation Rate:       {escalation_rate:.1f}% ({escalations}/{total_tests})"
        )
        print(f"Accepts:               {accepts}")
        print(f"Refusals:              {refusals}")
        print(f"Avg Response Time:     {avg_response_time:.2f}s")
        print("\nTarget: DoR Compliance Rate >90%")
        print(f"Status: {'PASS ✅' if passed else 'FAIL ❌'}\n")

        return {
            "benchmark_name": "SM Agent Effectiveness",
            "story_id": "Story 4",
            "timestamp": datetime.now().isoformat(),
            "agent_config": {
                "name": self.sm_agent["name"],
                "provider": self.sm_agent["llm_client"].provider,
                "model": self.sm_agent["llm_client"].model,
            },
            "test_scenarios": self.test_scenarios,
            "results": results,
            "metrics": {
                "total_tests": total_tests,
                "routing_accuracy_percent": round(routing_accuracy, 1),
                "dor_compliance_rate_percent": round(dor_compliance_rate, 1),
                "escalation_rate_percent": round(escalation_rate, 1),
                "accepts_count": accepts,
                "refusals_count": refusals,
                "escalations_count": escalations,
                "avg_response_time_seconds": round(avg_response_time, 2),
                "total_duration_seconds": round(total_duration, 2),
            },
            "targets": {
                "dor_compliance_rate_percent": 90.0,
            },
            "overall_result": "PASS" if passed else "FAIL",
        }

    def save_report(self, results: dict[str, Any], output_path: Path) -> None:
        """Save benchmark results to JSON file.

        Args:
            results: Benchmark results dictionary
            output_path: Path to save report
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"📊 Report saved to: {output_path}")


def main():
    """Execute SM agent effectiveness benchmark."""
    benchmark = SMEffectivenessBenchmark()
    results = benchmark.run_benchmark()

    # Save report
    output_path = Path("docs/metrics/sm_effectiveness_report.json")
    benchmark.save_report(results, output_path)

    # Exit with appropriate code
    sys.exit(0 if results["overall_result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
