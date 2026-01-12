#!/usr/bin/env python3
"""
Simple Git Workflow Test - Minimal validation of git operations without heavy embeddings

This script tests the core git operations workflow without the heavy directory search
functionality that causes context limit issues.

Usage:
    python3 scripts/test_simple_git_workflow.py
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


def create_minimal_git_test_crew():
    """Create a minimal crew to test git operations without heavy tools."""
    registry = AgentRegistry()

    # Get git-operator configuration but with minimal tools
    git_operator_config = registry.get_agent("git-operator")

    # Create minimal agent with only bash tool (no file_search to avoid embeddings)
    git_operator = Agent(
        role=git_operator_config["role"],
        goal="Execute git operations for testing purposes",
        backstory=git_operator_config["backstory"],
        verbose=True,
        allow_delegation=False,
        llm=git_operator_config["llm_client"],
        tools=[
            tool
            for tool in git_operator_config["tools"]
            if tool.__class__.__name__ == "CodeInterpreterTool"
        ],  # Only bash tools
    )

    # Create simple git workflow task
    git_task = Task(
        description="""
        **GIT OPERATIONS TEST**: Test git functionality with a simple workflow.

        **Your Task**:
        1. Check current git status to see repository state
        2. Create a simple test file with current timestamp
        3. Stage the test file for commit
        4. Create a test commit with message: "Test: Validate git operations workflow"
        5. Show git log to verify commit was created
        6. Clean up by removing the test file and reverting the commit

        **Important**: This is a test - clean up after yourself by removing the test file
        and reverting the commit so the repository stays clean.
        """,
        agent=git_operator,
        expected_output="Complete git workflow test with cleanup",
    )

    crew = Crew(
        agents=[git_operator],
        tasks=[git_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def main():
    """Execute minimal git workflow test."""
    print("\n🧪 MINIMAL GIT WORKFLOW TEST")
    print("=" * 70)
    print("Testing git operations without heavy embedding processes")
    print("=" * 70)

    try:
        crew = create_minimal_git_test_crew()

        print("\n⚡ Starting git workflow test...")
        result = crew.kickoff()

        # Save test result
        output_path = Path("output/git_workflow_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        test_report = {
            "execution_timestamp": datetime.now().isoformat(),
            "test_type": "minimal_git_workflow",
            "result": str(result),
            "status": "completed",
        }

        with open(output_path, "w") as f:
            json.dump(test_report, f, indent=2)

        print("\n✅ Git workflow test completed!")
        print(f"📄 Test report saved to {output_path}")
        print(f"\n🎯 Result: {result}")

        return True

    except Exception as e:
        logger.error(f"Git workflow test failed: {e}")
        print(f"❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
