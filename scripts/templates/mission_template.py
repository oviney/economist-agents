#!/usr/bin/env python3
"""
Autonomous Pod Mission Template

Standardized pattern for executing CrewAI missions with dynamic agent loading.
Implements ADR-002 (Agent Registry Pattern) for Agile discipline.

Usage:
    1. Copy this template to a new file (e.g., story_042_mission.py)
    2. Update the configuration section with your story details
    3. Define your tasks in the tasks list
    4. Run: python3 scripts/story_042_mission.py
"""

from pathlib import Path

from crewai import Crew, Task

from scripts.agent_registry import AgentRegistry

# ============================================================================
# CONFIGURATION - Update these for your mission
# ============================================================================

STORY_ID = "TODO"  # Example: "STORY-042"
STORY_CONTEXT = "TODO"  # Example: "Implement autonomous backlog refinement"
REQUIRED_AGENTS = ["role_name"]  # Example: ["product-owner", "scrum-master"]

# ============================================================================
# SETUP - Dynamic Agent Loading
# ============================================================================


def load_agents(registry: AgentRegistry) -> dict:
    """Load required agents from registry.

    Args:
        registry: Initialized AgentRegistry instance

    Returns:
        Dictionary mapping role names to CrewAI Agent instances
    """
    agents = {}
    for role in REQUIRED_AGENTS:
        agent = registry.get_agent(role)
        if agent is None:
            raise ValueError(
                f"Agent '{role}' not found. "
                f"Available: {', '.join(registry.list_agents())}"
            )
        agents[role] = agent
    return agents


# ============================================================================
# TASKS - Define mission objectives
# ============================================================================


def define_tasks(agents: dict) -> list[Task]:
    """Define tasks for the mission.

    Args:
        agents: Dictionary of loaded CrewAI agents

    Returns:
        List of Task objects for the mission
    """
    tasks = []

    # Example Task 1: Analysis
    # tasks.append(
    #     Task(
    #         description=f"Analyze requirements for {STORY_CONTEXT}",
    #         agent=agents["analyst"],
    #         expected_output="Requirements document with acceptance criteria",
    #     )
    # )

    # Example Task 2: Implementation
    # tasks.append(
    #     Task(
    #         description=f"Implement solution for {STORY_CONTEXT}",
    #         agent=agents["developer"],
    #         expected_output="Working code with tests",
    #     )
    # )

    # TODO: Add your tasks here
    raise NotImplementedError(
        "Define your tasks in define_tasks(). "
        "Remove this exception when tasks are ready."
    )

    return tasks


# ============================================================================
# EXECUTION - Run the mission
# ============================================================================


def run_mission():
    """Execute the autonomous pod mission."""
    print(f"\n{'=' * 70}")
    print(f"Starting Mission for Story {STORY_ID}...")
    print(f"Context: {STORY_CONTEXT}")
    print(f"Required Agents: {', '.join(REQUIRED_AGENTS)}")
    print(f"{'=' * 70}\n")

    # Initialize registry and load agents
    registry = AgentRegistry()
    agents = load_agents(registry)

    # Define tasks
    tasks = define_tasks(agents)

    # Create and execute crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,  # Show detailed execution logs
    )

    # Run the mission
    result = crew.kickoff()

    # Log results
    log_path = Path(f"docs/sprint_logs/story_{STORY_ID}_log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as f:
        f.write(f"# Mission Log: Story {STORY_ID}\n\n")
        f.write(f"**Context:** {STORY_CONTEXT}\n\n")
        f.write(f"**Agents:** {', '.join(REQUIRED_AGENTS)}\n\n")
        f.write("## Execution Output\n\n")
        f.write(f"{result}\n")

    print(f"\n{'=' * 70}")
    print(f"Mission Complete: Story {STORY_ID}")
    print(f"Log saved to: {log_path}")
    print(f"{'=' * 70}\n")

    return result


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        run_mission()
    except NotImplementedError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("Next Steps:")
        print("  1. Update STORY_ID, STORY_CONTEXT, REQUIRED_AGENTS")
        print("  2. Implement define_tasks() with your mission tasks")
        print("  3. Run again to execute the mission\n")
    except Exception as e:
        print(f"\n❌ Mission Failed: {e}\n")
        raise
