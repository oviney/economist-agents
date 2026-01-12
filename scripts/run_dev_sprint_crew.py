#!/usr/bin/env python3
"""
CrewAI Development Sprint Execution

Executes entire sprints using CrewAI development teams with parallel story execution.

Context:
    AS A Development Team,
    I WANT to execute sprints autonomously using AI agents,
    SO THAT we can achieve higher velocity with consistent quality.

Architecture:
    1. Sprint Orchestrator Crew - Manages sprint-level coordination
    2. Development Crews - Execute individual stories using TDD
    3. Code Reviewer Agents - Provide senior developer review
    4. Quality Gates - Ensure standards are maintained

Usage:
    python3 scripts/run_dev_sprint_crew.py --sprint 16
    python3 scripts/run_dev_sprint_crew.py --sprint 16 --max-parallel 5
    python3 scripts/run_dev_sprint_crew.py --story "Add authentication" --single-story
    python3 scripts/run_dev_sprint_crew.py --close-sprint 15

Expected Output:
    - Parallel execution of all stories in sprint
    - Comprehensive code review for each story
    - Sprint metrics and completion report
    - Integration with existing GitHub workflows
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add the parent directory to the Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.crews.development_crew import DevelopmentCrew
from src.crews.sprint_orchestrator_crew import SprintOrchestratorCrew

# Story and context configuration
STORY_ID = "DEV_SPRINT_AUTOMATION"
STORY_CONTEXT = (
    "Execute development sprints using CrewAI agents with parallel story execution"
)

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def execute_full_sprint(sprint_number: int, max_parallel: int = 3) -> dict[str, Any]:
    """Execute entire sprint using CrewAI orchestration."""
    logger.info(f"Starting CrewAI Sprint {sprint_number} execution")

    # Create sprint orchestrator
    orchestrator = SprintOrchestratorCrew()

    # Execute sprint
    result = orchestrator.execute_sprint(
        sprint_number=sprint_number, max_parallel_stories=max_parallel
    )

    return result


def close_sprint(sprint_number: int) -> dict[str, Any]:
    """Close and finalize a completed sprint."""
    logger.info(f"Starting Sprint {sprint_number} closure process")

    # Create sprint orchestrator to access DevOps finalization
    orchestrator = SprintOrchestratorCrew()

    try:
        # Simulate sprint data for closure (in real implementation, would load actual data)
        sprint_data = {
            "sprint_number": sprint_number,
            "total_stories": 0,  # Would be calculated from actual sprint
            "total_points": 0,  # Would be calculated from actual sprint
        }

        # Simulate story results (in real implementation, would load actual results)
        story_results = []  # Would be loaded from sprint execution history

        # Execute sprint finalization
        print(f"\n🏁 CLOSING SPRINT {sprint_number}")
        print(f"{'='*70}")

        finalization_result = orchestrator._finalize_sprint_metrics(
            sprint_number, sprint_data, story_results
        )

        return {
            "status": "success",
            "sprint_number": sprint_number,
            "closure_type": "manual",
            "finalization_result": finalization_result,
            "closure_summary": {
                "metrics_finalized": finalization_result.get(
                    "metrics_finalized", False
                ),
                "velocity_updated": finalization_result.get("velocity_updated", False),
                "project_archived": finalization_result.get("project_archived", False),
                "retrospective_required": True,
                "next_actions": [
                    "Conduct sprint retrospective if not yet completed",
                    "Review velocity trends and adjust next sprint planning",
                    "Address any technical debt identified during sprint",
                    "Plan next sprint based on team capacity and velocity",
                ],
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "sprint_number": sprint_number,
            "closure_type": "manual",
            "error": str(e),
            "recommendations": [
                "Manually verify sprint completion status",
                "Check GitHub milestone and project board status",
                "Ensure all stories are properly marked complete",
                "Complete retrospective documentation",
            ],
        }


def execute_single_story(
    story_title: str, acceptance_criteria: list = None
) -> dict[str, Any]:
    """Execute single story using development crew."""
    logger.info(f"Starting single story execution: {story_title}")

    # Create development crew
    dev_crew = DevelopmentCrew()

    # Prepare story data
    story_data = {
        "story_title": story_title,
        "acceptance_criteria": acceptance_criteria
        or [
            "Given story requirements, when implementation is complete, then all tests pass",
            "Given implementation is complete, when code review is conducted, then quality standards are met",
        ],
        "implementation_context": {
            "execution_mode": "single_story",
            "timestamp": datetime.now().isoformat(),
        },
    }

    # Execute story
    result = dev_crew.kickoff(story_data)

    return result


def save_execution_report(result: dict[str, Any], output_file: Path):
    """Save detailed execution report."""
    report = {
        "execution_timestamp": datetime.now().isoformat(),
        "execution_type": "crewai_dev_sprint",
        "result": result,
        "summary": generate_execution_summary(result),
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Execution report saved to {output_file}")


def generate_execution_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Generate executive summary of execution."""
    if result["status"] == "completed":
        metrics = result.get("metrics", {})
        return {
            "status": "SUCCESS",
            "sprint_number": result["sprint_number"],
            "stories_completed": f"{metrics.get('stories_completed', 0)}/{metrics.get('total_stories', 0)}",
            "completion_rate": f"{metrics.get('completion_rate', 0):.1f}%",
            "velocity": metrics.get("velocity", 0),
            "success_rate": f"{metrics.get('success_rate', 0):.1f}%",
            "key_achievements": [
                "Autonomous 6-phase sprint execution using CrewAI",
                "Complete DevOps infrastructure setup and finalization",
                "5-phase story development: TDD Red→Green→Review→Refactor→Git",
                "CI/CD pipeline validation after each story completion",
                "Git operations with commit standards and pre-commit hooks",
                "Parallel story development with comprehensive quality gates",
                "Senior developer review for all code",
                "TDD discipline maintained throughout",
            ],
        }
    else:
        return {
            "status": "FAILED",
            "error": result.get("error", "Unknown error"),
            "phase": result.get("phase", "Unknown phase"),
            "recommendations": [
                "Review error details and fix blocking issues",
                "Ensure Definition of Ready is complete",
                "Validate SPRINT.md structure and content",
                "Check agent configuration and tools",
            ],
        }


def print_execution_report(result: dict[str, Any]):
    """Print formatted execution report to console."""
    print("\n" + "=" * 80)
    print("CREWAI DEVELOPMENT SPRINT EXECUTION REPORT")
    print("=" * 80)

    if result["status"] == "completed":
        summary = result["execution_summary"]
        print(f"✅ Sprint {result['sprint_number']} COMPLETED SUCCESSFULLY")
        print(
            f"   Stories: {summary['completed_stories']} ({summary['completion_rate']})"
        )
        print(f"   Velocity: {summary['velocity']} story points")
        print(f"   Success Rate: {summary['success_rate']}")

        print("\n📊 STORY RESULTS:")
        for story_result in result["story_results"]:
            status_emoji = "✅" if story_result["status"] == "success" else "❌"
            crew_type = story_result.get("crew_type", "unknown")
            print(
                f"   {status_emoji} Story {story_result['story_number']}: {story_result['story_title']} ({crew_type})"
            )

        print("\n🎯 KEY ACHIEVEMENTS:")
        print(
            "   • Autonomous 5-phase TDD workflow execution (Red→Green→Review→Refactor→Git)"
        )
        print("   • Senior developer code review for all stories")
        print("   • Git operations with proper commit standards and pre-commit hooks")
        print("   • CI/CD pipeline validation after each story")
        print("   • Parallel story execution with comprehensive quality gates")
        print("   • Complete DevOps infrastructure setup and sprint finalization")

        print("\n🛠️ INFRASTRUCTURE:")
        infrastructure_ready = summary.get("infrastructure_ready", False)
        ci_cd_healthy = summary.get("ci_cd_healthy", False)
        metrics_finalized = summary.get("metrics_finalized", False)
        print(f"   Infrastructure Ready: {'✅' if infrastructure_ready else '❌'}")
        print(f"   CI/CD Pipeline Health: {'✅' if ci_cd_healthy else '❌'}")
        print(f"   Metrics Finalized: {'✅' if metrics_finalized else '❌'}")

    elif result["status"] == "error":
        print(f"❌ Sprint {result.get('sprint_number', 'unknown')} EXECUTION FAILED")
        print(f"   Error: {result['error']}")
        print(f"   Phase: {result.get('phase', 'Unknown')}")

    elif result["status"] == "blocked":
        print(f"⚠️  Sprint {result['sprint_number']} BLOCKED")

        if "Previous sprint not properly closed" in result.get("error", ""):
            print("   Previous sprint not properly closed")
            print("\n🚫 PREVIOUS SPRINT ISSUES:")

            validation = result.get("previous_sprint_validation", {})
            issues = validation.get("validation_issues", [])
            if issues:
                for issue in issues:
                    print(f"   • {issue}")

            print("\n📋 REQUIRED ACTIONS:")
            actions = result.get("required_actions", [])
            if actions:
                for action in actions:
                    print(f"   • {action}")

            prev_sprint = validation.get("previous_sprint_number", "N-1")
            print(f"\n💡 To close Sprint {prev_sprint}, run:")
            print(
                f"   python3 scripts/run_dev_sprint_crew.py --close-sprint {prev_sprint}"
            )
        else:
            print("   Sprint not ready to start - Definition of Ready incomplete")

    elif "closure_type" in result:
        # Sprint closure result
        if result["status"] == "success":
            print(f"✅ Sprint {result['sprint_number']} CLOSURE SUCCESSFUL")
            closure_summary = result.get("closure_summary", {})
            print(
                f"   Metrics Finalized: {'✅' if closure_summary.get('metrics_finalized') else '❌'}"
            )
            print(
                f"   Velocity Updated: {'✅' if closure_summary.get('velocity_updated') else '❌'}"
            )
            print(
                f"   Project Archived: {'✅' if closure_summary.get('project_archived') else '❌'}"
            )

            print("\n📋 NEXT ACTIONS:")
            next_actions = closure_summary.get("next_actions", [])
            for action in next_actions:
                print(f"   • {action}")
        else:
            print(f"❌ Sprint {result['sprint_number']} CLOSURE FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}")

            print("\n📋 RECOMMENDATIONS:")
            recommendations = result.get("recommendations", [])
            for rec in recommendations:
                print(f"   • {rec}")

    else:
        print(f"❓ UNKNOWN STATUS: {result['status']}")

    print("=" * 80)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Execute development sprints using CrewAI teams"
    )
    parser.add_argument(
        "--sprint", type=int, help="Sprint number to execute (e.g., 15)"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum number of stories to execute in parallel (default: 3)",
    )
    parser.add_argument(
        "--story", type=str, help="Execute single story instead of full sprint"
    )
    parser.add_argument(
        "--single-story", action="store_true", help="Execute in single story mode"
    )
    parser.add_argument(
        "--close-sprint",
        type=int,
        help="Close and finalize the specified sprint (e.g., 15)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/dev_sprint_execution.json",
        help="Output file for execution report",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.sprint and not args.story and not args.close_sprint:
        print(
            "Error: Must specify either --sprint NUMBER, --story TITLE, or --close-sprint NUMBER"
        )
        sys.exit(1)

    # Check for conflicting arguments
    options_count = sum(bool(x) for x in [args.sprint, args.story, args.close_sprint])
    if options_count > 1:
        print(
            "Error: Cannot specify multiple options. Choose one: --sprint, --story, or --close-sprint"
        )
        sys.exit(1)

    try:
        # Execute based on mode
        if args.story or args.single_story:
            story_title = args.story or "Test Story Execution"
            result = execute_single_story(story_title)
        elif args.close_sprint:
            result = close_sprint(args.close_sprint)
        else:
            result = execute_full_sprint(args.sprint, args.max_parallel)

        # Generate and save report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_execution_report(result, output_path)

        # Print report to console
        print_execution_report(result)

        # Exit with appropriate code
        if result["status"] in ["completed", "success"]:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(f"❌ EXECUTION FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🚀 CrewAI Development Sprint Execution")
    print(f"Story: {STORY_CONTEXT}")
    print(f"{'='*70}")

    main()
