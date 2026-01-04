#!/usr/bin/env python3
"""
Story 7: Sprint 9 Planning & Close-Out

Autonomous Sprint Closure with CrewAI orchestration.
Calculates velocity, generates retrospective, and closes Sprint 9.

Context:
    AS A Scrum Master,
    I WANT to close Sprint 9,
    SO THAT we can calculate velocity for Sprint 10.

Usage:
    python3 scripts/run_story7_crew.py
"""

from pathlib import Path

from crewai import Crew, Task

# Use AgentFactory from crewai_agents (ADR-002 compliant)
from crewai_agents import AgentFactory

# ============================================================================
# CONFIGURATION
# ============================================================================

STORY_ID = "7"
STORY_CONTEXT = (
    "AS A Scrum Master, I WANT to close Sprint 9 and generate the Retrospective, "
    "SO THAT we have clear metrics for Sprint 10."
)
REQUIRED_AGENTS = ["scrum-master"]

# ============================================================================
# SETUP - Dynamic Agent Loading
# ============================================================================


def load_agents() -> dict:
    """Load required agents using AgentFactory (ADR-002 compliant).

    Returns:
        Dictionary mapping role names to CrewAI Agent instances
    """
    factory = AgentFactory()
    agents = {}

    for role in REQUIRED_AGENTS:
        agent = factory.create_agent(role, verbose=True, allow_delegation=False)
        if agent is None:
            raise ValueError(
                f"Agent '{role}' not found in schemas/agents.yaml. "
                f"Check agent configuration."
            )
        agents[role] = agent
    return agents


# ============================================================================
# TASKS - Sprint 9 Closure
# ============================================================================


def define_tasks(agents: dict) -> list[Task]:
    """Define tasks for Sprint 9 closure.

    Args:
        agents: Dictionary of loaded CrewAI agents

    Returns:
        List of Task objects for the mission
    """
    tasks = []

    # Task 1: Analyze Sprint Completion
    tasks.append(
        Task(
            description=(
                "Read `SPRINT.md` and `BACKLOG.md`. "
                "Summarize completed points vs. planned."
            ),
            agent=agents["scrum-master"],
            expected_output=(
                "Summary of completed points vs. planned points for Sprint 9."
            ),
        )
    )

    # Task 2: Generate Retrospective Report
    tasks.append(
        Task(
            description=(
                "Generate a markdown Retrospective including: "
                "'Executive Summary', 'Velocity (Points Delivered)', "
                "'What went well (Autonomous Agents)', and 'Next Steps'. "
                "Return the Full Markdown content."
            ),
            agent=agents["scrum-master"],
            expected_output=(
                "Complete markdown document with Sprint 9 Retrospective "
                "containing Executive Summary, Velocity, What went well, and Next Steps."
            ),
        )
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

    # Load agents using AgentFactory
    agents = load_agents()

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
    log_path = Path(f"docs/sprint_logs/story_{STORY_ID.lower()}_log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as f:
        f.write(f"# Mission Log: Story {STORY_ID}\n\n")
        f.write(f"**Context:** {STORY_CONTEXT}\n\n")
        f.write(f"**Agents:** {', '.join(REQUIRED_AGENTS)}\n\n")
        f.write("## Execution Output\n\n")
        f.write(f"{result}\n")

    # Save Sprint 9 Retrospective
    retrospective_path = Path("docs/sprints/sprint_9_retrospective.md")
    retrospective_path.parent.mkdir(parents=True, exist_ok=True)

    with open(retrospective_path, "w") as f:
        f.write(f"{result}\n")

    print(f"\n{'=' * 70}")
    print(f"Mission Complete: Story {STORY_ID}")
    print(f"Log saved to: {log_path}")
    print(f"Retrospective saved to: {retrospective_path}")
    print(f"{'=' * 70}\n")

    return result


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        run_mission()
    except Exception as e:
        print(f"\n❌ Mission Failed: {e}\n")
        raise
