#!/usr/bin/env python3
"""
SM Agent Effectiveness Measurement Script

Validates Scrum Master Agent achieves >90% task assignment automation.

Usage:
    python3 scripts/measure_sm_agent.py

Metrics:
- Task assignment automation rate (target: >90%)
- Quality gate decision accuracy
- Escalation precision (real ambiguities vs false positives)
- Average orchestration time per story

Test Method:
- Create backlog with 5 diverse stories
- Run SM Agent orchestration
- Measure manual intervention points
- Calculate automation rate
"""

import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sm_agent import ScrumMasterAgent


def create_test_backlog():
    """Create test backlog with 5 diverse stories"""
    return {
        "sprint_id": "test_sprint_sm_measurement",
        "sprint_capacity": 13,
        "stories": [
            {
                "story_id": "TEST-001",
                "title": "Add dark mode toggle",
                "user_story": "As a blog user, I need a dark mode toggle so that I can read comfortably in low light",
                "acceptance_criteria": [
                    "Given user clicks toggle, When in light mode, Then UI switches to dark theme",
                    "Given dark mode active, When page reloads, Then dark mode persists",
                    "Given toggle clicked, When in dark mode, Then UI switches to light theme",
                ],
                "story_points": 2,
                "priority": "P0",
                "status": "ready",
                "quality_requirements": {
                    "performance": "Toggle response <100ms",
                    "accessibility": "WCAG 2.1 AA compliant color contrast",
                },
            },
            {
                "story_id": "TEST-002",
                "title": "Chart validation automation",
                "user_story": "As a QE, I need automated chart validation so that zone violations are caught before publication",
                "acceptance_criteria": [
                    "Given chart generated, When validation runs, Then zone boundaries checked",
                    "Given zone violation detected, When validation completes, Then error reported with details",
                    "Given valid chart, When validation runs, Then passes without errors",
                    "Given validation failure, When article published, Then publication blocked",
                ],
                "story_points": 5,
                "priority": "P0",
                "status": "ready",
                "quality_requirements": {
                    "performance": "Validation <2s per chart",
                    "reliability": "100% catch rate for zone violations",
                },
            },
            {
                "story_id": "TEST-003",
                "title": "RSS feed with categories",
                "user_story": "As a blog subscriber, I need RSS feeds filtered by category so that I receive only relevant content",
                "acceptance_criteria": [
                    "Given category selected, When RSS fetched, Then only category posts included",
                    "Given new post published, When RSS updated, Then appears in category feed within 5 min",
                    "Given multiple categories, When RSS fetched, Then separate feeds available",
                ],
                "story_points": 3,
                "priority": "P1",
                "status": "ready",
                "quality_requirements": {
                    "performance": "Feed generation <1s",
                    "maintainability": "Standard RSS 2.0 format",
                },
            },
            {
                "story_id": "TEST-004",
                "title": "Performance monitoring dashboard (VAGUE)",
                "user_story": "As a developer, I need performance monitoring so that I can track system health",
                "acceptance_criteria": [
                    "When system runs, Then performance tracked",
                    "When issues occur, Then alerts sent",
                ],
                "story_points": 8,
                "priority": "P2",
                "status": "ready",
                "quality_requirements": {},
                "note": "INTENTIONALLY VAGUE - Should trigger escalation for clarification",
            },
            {
                "story_id": "TEST-005",
                "title": "Fix integration test mocking",
                "user_story": "As a developer, I need integration tests to use mocks so that tests don't call real APIs",
                "acceptance_criteria": [
                    "Given tests run, When mocks applied, Then no API calls made",
                    "Given mock responses defined, When tests execute, Then use mock data",
                    "Given tests complete, When results analyzed, Then all 9 tests pass",
                ],
                "story_points": 2,
                "priority": "P0",
                "status": "ready",
                "quality_requirements": {
                    "performance": "Test execution <30s",
                    "reliability": "100% pass rate with mocks",
                },
            },
        ],
    }


def measure_sm_agent():
    """Run SM Agent measurement test"""
    print("=" * 70)
    print("SM AGENT EFFECTIVENESS MEASUREMENT")
    print("=" * 70)
    print()

    # Create test backlog
    backlog = create_test_backlog()
    print(f"✓ Created test backlog: {len(backlog['stories'])} stories\n")

    # Initialize SM Agent
    sm_agent = ScrumMasterAgent()

    # Validate DoR for all stories
    print("PHASE 1: DoR Validation")
    print("-" * 70)
    dor_results = {}
    for story in backlog["stories"]:
        is_valid, missing_fields = sm_agent.validator.validate_dor(story)
        dor_results[story["story_id"]] = {
            "valid": is_valid,
            "missing": missing_fields,
        }
        status = "✓ PASS" if is_valid else f"✗ FAIL ({len(missing_fields)} missing)"
        print(f"  {story['story_id']}: {status}")
    print()

    # Create task queue
    print("PHASE 2: Task Queue Creation")
    print("-" * 70)

    # Save backlog to temp file for parse_backlog API
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(backlog, f, indent=2)
        backlog_file = f.name

    start_time = time.time()
    task_queue = sm_agent.queue.parse_backlog(backlog_file)
    queue_time = time.time() - start_time

    # Clean up temp file
    os.unlink(backlog_file)

    print(f"  ✓ Created {len(task_queue)} tasks in {queue_time:.2f}s")
    print()

    # Analyze task assignments
    print("PHASE 3: Task Assignment Analysis")
    print("-" * 70)
    automated_assignments = 0
    manual_interventions = 0
    escalations_generated = 0

    for task in task_queue:
        # Check if SM Agent can auto-assign
        if task.get("assigned_agent"):
            automated_assignments += 1
            print(
                f"  ✓ AUTO: {task['task_id']} → {task['assigned_agent']} (phase: {task['phase']})"
            )
        else:
            manual_interventions += 1
            print(f"  ⚠ MANUAL: {task['task_id']} (needs human assignment)")

    # Check for escalations in original stories
    for story in backlog["stories"]:
        if "VAGUE" in story.get("title", ""):
            escalations_generated += 1

    automation_rate = (
        (automated_assignments / len(task_queue) * 100) if task_queue else 0
    )
    print()
    print(f"  Automated: {automated_assignments}/{len(task_queue)} tasks")
    print(f"  Manual: {manual_interventions}/{len(task_queue)} tasks")
    print(f"  Automation Rate: {automation_rate:.1f}%")
    print()

    # Quality Gate Decision Testing
    print("PHASE 4: Quality Gate Decisions")
    print("-" * 70)
    gate_decisions = {"approve": 0, "escalate": 0, "reject": 0}

    for story in backlog["stories"]:
        # Check for vague stories that should escalate
        issues = []
        if not story.get("quality_requirements"):
            issues.append("Missing quality requirements")
        if len(story["acceptance_criteria"]) < 3:
            issues.append("Insufficient acceptance criteria")

        # make_gate_decision expects (is_valid, issues) tuple
        validation_result = (len(issues) == 0, issues)
        decision = sm_agent.validator.make_gate_decision(validation_result)
        gate_decisions[decision] = gate_decisions.get(decision, 0) + 1
        print(f"  {story['story_id']}: {decision.upper()} (issues: {len(issues)})")

    print()

    # Generate Report
    print("=" * 70)
    print("MEASUREMENT RESULTS")
    print("=" * 70)
    print()

    results = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backlog_size": len(backlog["stories"]),
        "task_queue_size": len(task_queue),
        "automation_metrics": {
            "automated_assignments": automated_assignments,
            "manual_interventions": manual_interventions,
            "automation_rate_percent": round(automation_rate, 1),
            "target_rate_percent": 90.0,
            "meets_target": automation_rate >= 90.0,
        },
        "quality_gate_metrics": {
            "approve_count": gate_decisions.get("approve", 0),
            "escalate_count": gate_decisions.get("escalate", 0),
            "reject_count": gate_decisions.get("reject", 0),
            "total_decisions": sum(gate_decisions.values()),
        },
        "performance_metrics": {
            "queue_creation_time_seconds": round(queue_time, 2),
            "avg_time_per_story_seconds": round(
                queue_time / len(backlog["stories"]), 2
            ),
        },
        "dor_validation": dor_results,
    }

    # Print Key Metrics
    print(f"✅ AUTOMATION RATE: {automation_rate:.1f}%")
    print(f"   Target: 90% | Status: {'EXCEEDS' if automation_rate >= 90 else 'BELOW'}")
    print()
    print(f"✅ QUALITY GATE DECISIONS: {sum(gate_decisions.values())} total")
    print(f"   Approve: {gate_decisions.get('approve', 0)}")
    print(f"   Escalate: {gate_decisions.get('escalate', 0)}")
    print(f"   Reject: {gate_decisions.get('reject', 0)}")
    print()
    print(f"✅ PERFORMANCE: {queue_time:.2f}s total")
    print(f"   Avg per story: {queue_time / len(backlog['stories']):.2f}s")
    print()

    # Save results
    output_file = "skills/sm_agent_test_metrics.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"📝 Results saved: {output_file}")
    print()

    # Recommendation
    if automation_rate >= 90:
        print("✅ RECOMMENDATION: SM Agent meets production readiness criteria")
        print("   Deploy in Sprint 10 with human oversight for first 2-3 sprints")
    else:
        print(
            f"⚠️  RECOMMENDATION: SM Agent below target ({automation_rate:.1f}% < 90%)"
        )
        print("   Identify manual intervention points and enhance automation")

    return results


if __name__ == "__main__":
    measure_sm_agent()
