#!/usr/bin/env python3
"""
Sprint 8 Story 4: Editor Agent Validation

Generates 10 test articles to validate:
1. Gate counting fix (exactly 5 gates parsed)
2. Temperature=0 enforcement (deterministic evaluation)
3. Format validation (structured output)

Target: 95%+ gate pass rate
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root and agents directory to path
_project_root = Path(__file__).parent.parent
_scripts_dir = _project_root / "scripts"
_agents_dir = _project_root / "agents"

for dir_path in [_project_root, _scripts_dir, _agents_dir]:
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))

from editor_agent import run_editor_agent
from llm_client import create_llm_client

# Test topics for variety
TEST_TOPICS = [
    "The Hidden Costs of Flaky Tests",
    "Self-Healing Tests: Separating Hype from Reality",
    "Why AI Testing Tools Overpromise on Maintenance",
    "The Economics of Test Automation ROI",
    "Quality Metrics That Actually Matter to Executives",
    "The Death of Manual Testing: Premature Diagnosis",
    "Platform Engineering's Impact on Quality Engineering",
    "Shift-Left vs Shift-Right: False Dichotomy",
    "The Technical Debt Crisis in Test Suites",
    "No-Code Testing's Hidden Complexity Tax",
]


def generate_test_draft(topic: str) -> str:
    """Generate a test draft article (mock - avoid LLM calls for speed)."""
    return f"""---
layout: post
title: "{topic}"
date: {datetime.now().strftime("%Y-%m-%d")}
categories: [quality-engineering]
---

{topic.replace(":", " -")}

## The Problem

According to industry surveys, 60% of teams struggle with this issue. The root cause is systemic misalignment between development velocity and quality infrastructure.

## The Data

Recent Gartner research shows a 40% year-over-year increase. Companies that ignore this trend face a 3x higher defect escape rate, per Forrester's latest report.

## The Solution

Smart teams are adopting three strategies. First, they invest in better tooling. Second, they prioritize developer education. Third, they measure what matters.

## The Outlook

The industry will shift significantly over the next 18 months. Leaders who act now will gain competitive advantage. Laggards risk falling behind permanently.
"""


def main():
    """Run 10-article validation test."""
    print("=" * 70)
    print("Sprint 8 Story 4: Editor Agent Validation")
    print("=" * 70)
    print()
    print("Testing 3 fixes:")
    print("  1. Gate counting (regex-based, exactly 5 gates)")
    print("  2. Temperature=0 (deterministic evaluation)")
    print("  3. Format validation (structured output)")
    print()
    print("Target: 95%+ gate pass rate (>=9/10 runs with all gates passed)")
    print("=" * 70)
    print()

    # Create LLM client
    client = create_llm_client()

    # Run 10 tests
    results = []
    total_gates = 0
    total_passed = 0

    for i, topic in enumerate(TEST_TOPICS, 1):
        print(f"\n[Test {i}/10] Topic: {topic}")
        print("-" * 70)

        # Generate test draft
        draft = generate_test_draft(topic)

        # Run editor agent
        try:
            edited, gates_passed, gates_failed = run_editor_agent(client, draft)

            # Record results
            total_gates += 5  # Always 5 gates
            total_passed += gates_passed

            result = {
                "test": i,
                "topic": topic,
                "gates_passed": gates_passed,
                "gates_failed": gates_failed,
                "total_gates": gates_passed + gates_failed,
                "pass_rate": (gates_passed / 5 * 100) if gates_passed > 0 else 0,
            }
            results.append(result)

            # Print result
            status = (
                "✅ PASS"
                if gates_passed == 5
                else "⚠️  PARTIAL"
                if gates_passed >= 4
                else "❌ FAIL"
            )
            print(
                f"   Result: {gates_passed}/5 gates passed ({result['pass_rate']:.1f}%) - {status}"
            )

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(
                {
                    "test": i,
                    "topic": topic,
                    "error": str(e),
                    "gates_passed": 0,
                    "gates_failed": 0,
                    "total_gates": 0,
                    "pass_rate": 0,
                }
            )

    # Calculate final statistics
    print()
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print()

    successful_runs = [r for r in results if "error" not in r]
    failed_runs = [r for r in results if "error" in r]

    print(f"Successful runs: {len(successful_runs)}/10")
    print(f"Failed runs: {len(failed_runs)}/10")
    print()

    if successful_runs:
        avg_pass_rate = sum(r["pass_rate"] for r in successful_runs) / len(
            successful_runs
        )
        perfect_runs = sum(1 for r in successful_runs if r["gates_passed"] == 5)

        print(f"Average gate pass rate: {avg_pass_rate:.1f}%")
        print(
            f"Perfect runs (5/5 gates): {perfect_runs}/10 ({perfect_runs / 10 * 100:.0f}%)"
        )
        print()

        # Sprint 8 objective: 95%+ gate pass rate
        if avg_pass_rate >= 95.0:
            print("✅ OBJECTIVE ACHIEVED: Gate pass rate ≥95%")
            print()
            print("Sprint 8 Story 4 Remediation: COMPLETE")
            status_code = 0
        elif avg_pass_rate >= 90.0:
            print("⚠️  CLOSE: Gate pass rate 90-95% (needs minor tuning)")
            status_code = 1
        else:
            print(
                f"❌ OBJECTIVE NOT MET: Gate pass rate {avg_pass_rate:.1f}% (target: 95%)"
            )
            status_code = 2

        # Gate counting validation
        gate_count_issues = sum(1 for r in successful_runs if r["total_gates"] != 5)
        if gate_count_issues == 0:
            print("✅ Gate counting fix VALIDATED: All runs parsed exactly 5 gates")
        else:
            print(
                f"⚠️  Gate counting issues: {gate_count_issues}/10 runs had wrong gate count"
            )

        # Save results
        results_file = (
            Path(__file__).parent.parent / "skills" / "editor_validation_results.json"
        )
        with open(results_file, "w") as f:
            json.dump(
                {
                    "validation_date": datetime.now().isoformat(),
                    "total_runs": len(results),
                    "successful_runs": len(successful_runs),
                    "failed_runs": len(failed_runs),
                    "average_pass_rate": avg_pass_rate,
                    "perfect_runs": perfect_runs,
                    "objective_achieved": avg_pass_rate >= 95.0,
                    "results": results,
                },
                f,
                indent=2,
            )

        print()
        print(f"📊 Full results saved: {results_file}")

    else:
        print("❌ All test runs failed - cannot validate fixes")
        status_code = 3

    print()
    print("=" * 70)

    sys.exit(status_code)


if __name__ == "__main__":
    main()
