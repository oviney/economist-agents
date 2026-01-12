#!/usr/bin/env python3
"""
Direct Git Operations Test - Test git-operator agent without heavy embeddings

This script directly tests the git-operator agent capabilities by creating a minimal
environment focused solely on git operations validation.

Usage:
    python3 scripts/test_git_operations_direct.py
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


def create_git_operations_crew():
    """Create a minimal crew focused on git operations testing."""
    registry = AgentRegistry()

    # Get git-operator configuration with only bash tools (no heavy search tools)
    git_operator_config = registry.get_agent("git-operator")

    # Create git-operator agent with only bash tools to avoid embedding issues
    git_operator = Agent(
        role=git_operator_config["role"],
        goal="Execute actual git operations with real repository changes",
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

    # Create comprehensive git workflow task that mimics a real story completion
    git_task = Task(
        description="""
        **REAL GIT OPERATIONS TEST**: Execute actual git operations for a completed story.

        **Scenario**: You've just completed implementing "Add input validation utility function"
        and need to commit the changes to the repository.

        **Your Task**:
        1. **Check git status** to see current repository state
        2. **Create actual implementation file** `src/utils/validation.py` with input validation function:
           ```python
           from typing import Any, Dict

           def run_research_agent(client: Any, topic: str, research_brief: Dict[str, Any]) -> bool:
               if not isinstance(topic, str) or len(topic.strip()) < 3:
                   raise ValueError("Invalid topic: Must be a non-empty string with at least 3 characters.")
               if not research_brief:
                   raise ValueError("Empty research_brief")
               research_brief['status'] = 'completed'
               research_brief['data'] = 'Research data'
               return True
           ```
        3. **Stage the new file** using `git add`
        4. **Create commit** with proper message format: "Story N: Add input validation utility function"
        5. **Verify commit** was created using `git log`
        6. **Show the diff** to confirm what was committed

        **Critical Requirements**:
        - Use REAL git commands that modify the repository
        - Follow "Story N:" commit message format exactly
        - Create actual files in proper directory structure
        - This is NOT a simulation - make actual changes

        **Success Criteria**:
        - New file created and committed to repository
        - Proper commit message format used
        - Git history shows the new commit
        """,
        agent=git_operator,
        expected_output="Completed git operations with actual file creation and commit",
    )

    crew = Crew(
        agents=[git_operator],
        tasks=[git_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def main():
    """Execute direct git operations test."""
    print("\n🚀 DIRECT GIT OPERATIONS TEST")
    print("=" * 70)
    print("Testing real git operations with actual repository changes")
    print("=" * 70)

    try:
        crew = create_git_operations_crew()

        print("\n⚡ Starting real git operations test...")
        result = crew.kickoff()

        # Save test result
        output_path = Path("output/git_operations_direct_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        test_report = {
            "execution_timestamp": datetime.now().isoformat(),
            "test_type": "direct_git_operations",
            "result": str(result),
            "status": "completed",
        }

        with open(output_path, "w") as f:
            json.dump(test_report, f, indent=2)

        print("\n✅ Direct git operations test completed!")
        print(f"📄 Test report saved to {output_path}")
        print(f"\n🎯 Result: {result}")

        # Verify the actual file was created
        validation_file = Path("src/utils/validation.py")
        if validation_file.exists():
            print(f"\n🎉 SUCCESS: File {validation_file} was actually created!")
        else:
            print(f"\n⚠️  Note: File {validation_file} not found - check git operations")

        return True

    except Exception as e:
        logger.error(f"Git operations test failed: {e}")
        print(f"❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
