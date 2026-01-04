#!/usr/bin/env python3
"""
Story 2 Crew Execution: Fix Integration Tests

Executes Story 2 using the qa-specialist agent to achieve 100% integration test pass rate.
"""

from datetime import datetime
from pathlib import Path

from agent_registry import AgentRegistry
from crewai import Agent, Crew, Task

# Story context with known issues
STORY_CONTEXT = """
Story 2: Fix Integration Tests
AS A Developer
I WANT 100% pass rate on integration tests (currently 56%)
SO THAT the CI/CD pipeline is reliable.

Known Issues:
1. Visual QA: Mock setup for `client.client.messages` chain is broken.
2. Defect Prevention: `check_all_patterns` API signature mismatch.
3. Publication Validator: Layout scope validation logic error.
"""


def main():
    """Execute Story 2 crew with qa-specialist agent."""

    print("=" * 70)
    print("Story 2: Fix Integration Tests")
    print("=" * 70)
    print()

    # Initialize registry and get the qa-specialist agent data
    registry = AgentRegistry()
    qa_agent_data = registry.get_agent("qa-specialist")

    # Create CrewAI Agent from registry data
    qa_agent = Agent(
        role=qa_agent_data["role"],
        goal=qa_agent_data["goal"],
        backstory=qa_agent_data["backstory"],
        verbose=True,
        allow_delegation=False,
    )

    # Create tasks
    audit_task = Task(
        description="Run `pytest tests/integration` to confirm current failures and log the output.",
        agent=qa_agent,
        expected_output="Test results showing current failures with detailed error messages",
    )

    fix_task = Task(
        description="Refactor the code to fix the 3 known issues listed in Context.",
        agent=qa_agent,
        expected_output="Fixed code with all three issues resolved",
        context=[audit_task],
    )

    verify_task = Task(
        description="Run `pytest tests/integration` again. If any fail, iterate until GREEN.",
        agent=qa_agent,
        expected_output="All integration tests passing (100% pass rate)",
        context=[fix_task],
    )

    # Create and execute crew
    crew = Crew(
        agents=[qa_agent], tasks=[audit_task, fix_task, verify_task], verbose=True
    )

    print(f"Starting Story 2 execution at {datetime.now().isoformat()}")
    print()

    result = crew.kickoff()

    # Save execution log
    log_dir = Path("docs/sprint_logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "story2_execution.md"

    with open(log_file, "w") as f:
        f.write("# Story 2 Execution Log\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n\n")
        f.write("## Story Context\n\n")
        f.write(f"{STORY_CONTEXT}\n\n")
        f.write("## Execution Results\n\n")
        f.write(f"```\n{result}\n```\n")

    print()
    print("=" * 70)
    print(f"Execution complete. Log saved to: {log_file}")
    print("=" * 70)

    return result


if __name__ == "__main__":
    main()
