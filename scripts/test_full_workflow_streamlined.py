#!/usr/bin/env python3
"""
Streamlined Full 5-Phase Workflow Test

Demonstrates the complete TDD workflow without heavy embedding operations
that cause OpenAI context limit issues.

Phases:
1. TDD Red - Write failing tests
2. TDD Green - Implement code
3. Senior Review - Code review
4. TDD Refactor - Code cleanup
5. Git Operations - Commit changes

Usage:
    python3 scripts/test_full_workflow_streamlined.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from crewai import Agent, Crew, Task
from crewai.process import Process

from scripts.agent_registry import AgentRegistry

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_streamlined_development_crew():
    """Create development crew with minimal tool configuration to avoid embedding issues."""
    registry = AgentRegistry()

    # Load agent configurations with only essential tools
    test_specialist_config = registry.get_agent("test-specialist")
    code_quality_config = registry.get_agent("code-quality-specialist")
    code_reviewer_config = registry.get_agent("code-reviewer")
    git_operator_config = registry.get_agent("git-operator")

    # Create agents with only CodeInterpreterTool (bash) to avoid heavy embeddings
    agents = {
        "test_specialist": Agent(
            role="Senior QA Test Engineer",
            goal="Write comprehensive failing tests following TDD Red phase",
            backstory="Expert in pytest and TDD methodology with focus on comprehensive test coverage",
            verbose=True,
            allow_delegation=False,
            llm=test_specialist_config["llm_client"],
            tools=[
                tool
                for tool in test_specialist_config["tools"]
                if tool.__class__.__name__ == "CodeInterpreterTool"
            ],
        ),
        "code_quality_specialist": Agent(
            role="Senior Python Developer",
            goal="Implement code to make tests pass following TDD Green phase",
            backstory="Expert Python developer focused on clean code and quality standards",
            verbose=True,
            allow_delegation=False,
            llm=code_quality_config["llm_client"],
            tools=[
                tool
                for tool in code_quality_config["tools"]
                if tool.__class__.__name__ == "CodeInterpreterTool"
            ],
        ),
        "code_reviewer": Agent(
            role="Senior Code Reviewer",
            goal="Conduct thorough code review with architecture and security focus",
            backstory="Senior developer with extensive experience in code review and architecture",
            verbose=True,
            allow_delegation=False,
            llm=code_reviewer_config["llm_client"],
            tools=[
                tool
                for tool in code_reviewer_config["tools"]
                if tool.__class__.__name__ == "CodeInterpreterTool"
            ],
        ),
        "git_operator": Agent(
            role="Git Operations Specialist",
            goal="Execute git operations with proper commit standards",
            backstory="Expert in git workflows, commit standards, and repository management",
            verbose=True,
            allow_delegation=False,
            llm=git_operator_config["llm_client"],
            tools=[
                tool
                for tool in git_operator_config["tools"]
                if tool.__class__.__name__ == "CodeInterpreterTool"
            ],
        ),
    }

    return agents


def create_workflow_tasks():
    """Create the 5-phase TDD workflow tasks."""

    # Phase 1: TDD Red
    phase1_task = Task(
        description="""
        **PHASE 1 - TDD RED**: Write failing tests for data sanitization utility.

        Create comprehensive tests for a data sanitization function that should:
        - Remove HTML tags from strings
        - Sanitize SQL injection attempts
        - Handle empty/null inputs gracefully
        - Validate email format
        - Sanitize file paths

        Write tests in /tmp/test_sanitization.py that will initially fail.
        Use pytest and include edge cases, security scenarios, and validation tests.

        Expected output: Failing test suite that defines requirements.
        """,
        expected_output="Complete failing test suite for data sanitization utility",
    )

    # Phase 2: TDD Green
    phase2_task = Task(
        description="""
        **PHASE 2 - TDD GREEN**: Implement minimum code to make tests pass.

        Based on the failing tests created in Phase 1, implement a data sanitization
        utility function in /tmp/sanitization.py that makes all tests pass.

        Focus on:
        - Minimal implementation that passes tests
        - Proper error handling
        - Type hints and docstrings
        - Following Python best practices

        Expected output: Working implementation that passes all tests.
        """,
        expected_output="Implementation code that makes all tests pass",
    )

    # Phase 3: Senior Review
    phase3_task = Task(
        description="""
        **PHASE 3 - SENIOR REVIEW**: Comprehensive code review.

        Review the implementation from Phase 2 focusing on:
        - Architecture and design patterns
        - Security vulnerabilities
        - Performance considerations
        - Code quality and maintainability
        - Test coverage adequacy

        Provide specific feedback and approval status:
        ✅ Approved | ⚠️ Conditional | ❌ Rejected

        Expected output: Detailed code review with approval status.
        """,
        expected_output="Complete code review with architectural feedback and approval status",
    )

    # Phase 4: TDD Refactor
    phase4_task = Task(
        description="""
        **PHASE 4 - TDD REFACTOR**: Improve code quality while keeping tests green.

        Based on the senior review feedback, refactor the implementation to:
        - Improve code structure and readability
        - Optimize performance where needed
        - Add additional security measures
        - Enhance documentation

        Ensure all tests continue to pass after refactoring.

        Expected output: Refactored code with improved quality and maintained functionality.
        """,
        expected_output="Refactored implementation with improved quality",
    )

    # Phase 5: Git Operations
    phase5_task = Task(
        description="""
        **PHASE 5 - GIT OPERATIONS**: Commit the completed work.

        Create actual git commit with the sanitization utility:
        1. Create src/utils/sanitization.py with the final implementation
        2. Create tests/test_sanitization.py with the test suite
        3. Stage the files using git add
        4. Commit with proper message: "Story 2: Add data sanitization utility function"
        5. Verify commit was created

        This creates REAL repository changes.

        Expected output: Completed git commit with actual files in repository.
        """,
        expected_output="Git commit completed with sanitization utility in repository",
    )

    return [phase1_task, phase2_task, phase3_task, phase4_task, phase5_task]


def main():
    """Execute complete 5-phase TDD workflow."""
    print("\n🚀 COMPLETE 5-PHASE TDD WORKFLOW TEST")
    print("=" * 70)
    print("Red → Green → Review → Refactor → Git")
    print("=" * 70)

    try:
        agents = create_streamlined_development_crew()
        tasks = create_workflow_tasks()

        # Assign agents to tasks
        tasks[0].agent = agents["test_specialist"]  # Phase 1: Red
        tasks[1].agent = agents["code_quality_specialist"]  # Phase 2: Green
        tasks[2].agent = agents["code_reviewer"]  # Phase 3: Review
        tasks[3].agent = agents["code_quality_specialist"]  # Phase 4: Refactor
        tasks[4].agent = agents["git_operator"]  # Phase 5: Git

        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        print("\n⚡ Starting complete 5-phase workflow...")
        result = crew.kickoff()

        # Save execution results
        output_path = Path("output/full_workflow_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workflow_report = {
            "execution_timestamp": datetime.now().isoformat(),
            "workflow_type": "complete_5_phase_tdd",
            "phases_completed": 5,
            "result": str(result),
            "status": "completed",
        }

        with open(output_path, "w") as f:
            json.dump(workflow_report, f, indent=2)

        print("\n✅ Complete 5-phase workflow finished!")
        print(f"📄 Results saved to {output_path}")
        print(f"\n🎯 Final Result: {result}")

        # Check if actual files were created
        sanitization_file = Path("src/utils/sanitization.py")
        test_file = Path("tests/test_sanitization.py")

        if sanitization_file.exists():
            print(f"\n🎉 SUCCESS: {sanitization_file} was created!")
        if test_file.exists():
            print(f"🎉 SUCCESS: {test_file} was created!")

        return True

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        print(f"❌ WORKFLOW FAILED: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
