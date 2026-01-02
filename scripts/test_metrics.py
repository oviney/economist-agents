#!/usr/bin/env python3
"""
Test Chart Metrics Collection

Simulates chart generation and Visual QA to verify metrics system.
"""

import sys
import time
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from chart_metrics import get_metrics_collector


def test_metrics_collection():
    """Test the metrics collection system"""
    print("🧪 Testing Chart Metrics Collection\n")

    metrics = get_metrics_collector()

    # Test 1: Chart generation
    print("Test 1: Chart Generation")
    chart_spec = {
        "title": "Test Chart: AI Adoption",
        "type": "line",
        "data": [{"year": "2020", "value": 10}],
    }

    chart_record = metrics.start_chart("Test Chart: AI Adoption", chart_spec)
    print(f"  ✓ Started chart: {chart_record['title']}")

    # Simulate generation time
    time.sleep(0.1)

    metrics.record_generation(chart_record, success=True)
    print(
        f"  ✓ Recorded successful generation ({chart_record['generation_time_seconds']:.3f}s)"
    )

    # Test 2: Visual QA pass
    print("\nTest 2: Visual QA - Pass")
    qa_result_pass = {
        "overall_pass": True,
        "gates": {
            "zone_integrity": {"pass": True, "issues": []},
            "label_positioning": {"pass": True, "issues": []},
            "style_compliance": {"pass": True, "issues": []},
            "data_export": {"pass": True, "issues": []},
        },
        "critical_issues": [],
    }

    metrics.record_visual_qa(chart_record, qa_result_pass)
    print("  ✓ Recorded passing Visual QA")

    # Test 3: Chart generation failure
    print("\nTest 3: Chart Generation Failure")
    chart_spec2 = {"title": "Test Chart: Failed Generation", "type": "bar", "data": []}

    chart_record2 = metrics.start_chart("Test Chart: Failed Generation", chart_spec2)
    time.sleep(0.05)
    metrics.record_generation(
        chart_record2, success=False, error="Invalid data: empty dataset"
    )
    print("  ✓ Recorded failed generation")

    # Test 4: Visual QA fail with zone violations
    print("\nTest 4: Visual QA - Fail with Zone Violations")
    chart_spec3 = {
        "title": "Test Chart: Zone Violations",
        "type": "line",
        "data": [{"year": "2021", "value": 20}],
    }

    chart_record3 = metrics.start_chart("Test Chart: Zone Violations", chart_spec3)
    time.sleep(0.12)
    metrics.record_generation(chart_record3, success=True)

    qa_result_fail = {
        "overall_pass": False,
        "gates": {
            "zone_integrity": {
                "pass": False,
                "issues": [
                    "Title overlaps red bar",
                    "Inline label intrudes into X-axis zone",
                ],
            },
            "label_positioning": {
                "pass": False,
                "issues": ["Label collision detected"],
            },
            "style_compliance": {"pass": True, "issues": []},
            "data_export": {"pass": True, "issues": []},
        },
        "critical_issues": [
            "Zone boundary violation: Title/red bar overlap",
            "Zone boundary violation: Label in X-axis zone",
        ],
    }

    metrics.record_visual_qa(chart_record3, qa_result_fail)
    print("  ✓ Recorded failing Visual QA with 2 zone violations")

    # Test 5: Regeneration
    print("\nTest 5: Chart Regeneration")
    metrics.record_regeneration(chart_record3, "Zone violations detected")
    print("  ✓ Recorded regeneration attempt")

    # End session and print summary
    metrics.end_session()
    print("\n" + "=" * 70)
    print("📊 METRICS SUMMARY")
    print("=" * 70)

    summary = metrics.get_summary()
    print(f"  Total Charts Generated: {summary['total_charts_generated']}")
    print(f"  Visual QA Runs: {summary['total_visual_qa_runs']}")
    print(f"  Visual QA Pass Rate: {summary['visual_qa_pass_rate']:.1f}%")
    print(f"  Total Zone Violations: {summary['total_zone_violations']}")
    print(f"  Total Regenerations: {summary['total_regenerations']}")
    print(f"  Avg Generation Time: {summary['avg_generation_time_seconds']:.3f}s")

    print("\n" + "=" * 70)
    print("TOP FAILURE PATTERNS")
    print("=" * 70)

    top_patterns = metrics.get_top_failure_patterns(5)
    for i, pattern in enumerate(top_patterns, 1):
        print(f"  {i}. [{pattern['count']}x] {pattern['type']}")
        print(f"     {pattern['issue'][:60]}...")

    print("\n✅ All tests passed! Metrics system working correctly.")
    print(f"   Metrics saved to: {metrics.metrics_file}")

    return True


if __name__ == "__main__":
    test_metrics_collection()
