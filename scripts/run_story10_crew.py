#!/usr/bin/env python3
"""
Story 10: Phase 2 Migration - Stage 3 Content Generation (TDD Enforced)

CrewAI migration of Stage 3 (economist_agent.py) with STRICT Red-Green-Refactor discipline.

Context:
    AS A Migration Engineer,
    I WANT to migrate Stage 3 to CrewAI using TDD,
    SO THAT we have testable confidence in the migration.

TDD Protocol:
    1. RED: Write failing test first (reproduction script)
    2. GREEN: Implement minimum code to pass test
    3. REFACTOR: Clean up while keeping tests green

Usage:
    python3 scripts/run_story10_crew.py

Expected Output:
    - tests/verify_stage3_migration.py (RED phase - must fail initially)
    - agents/stage3_crew.py (GREEN phase - makes test pass)
    - Distinct RED→GREEN log output proving TDD discipline
"""

from pathlib import Path

from crewai import Agent, Crew, Task

from scripts.agent_registry import AgentRegistry

# ============================================================================
# CONFIGURATION
# ============================================================================

STORY_ID = "10"
STORY_CONTEXT = "Migrate src/stage3.py to CrewAI Stage3Crew using strict TDD"
REQUIRED_AGENTS = ["migration-engineer"]

# TDD Configuration
TDD_VERIFICATION_SCRIPT = "tests/reproduce_stage3.py"
STAGE3_CREW_MODULE = "agents/stage3_crew.py"

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
        agent_dict = registry.get_agent(role)
        if agent_dict is None:
            raise ValueError(
                f"Agent '{role}' not found. "
                f"Available: {', '.join(registry.list_agents())}"
            )

        # Convert AgentRegistry output to CrewAI Agent instance
        # Include tools if available (now actual tool instances, not strings)
        agent_params = {
            "role": agent_dict["role"],
            "goal": agent_dict["goal"],
            "backstory": agent_dict["backstory"],
            "verbose": True,
            "allow_delegation": False,
        }

        # Add tools if available
        if agent_dict.get("tools"):
            agent_params["tools"] = agent_dict["tools"]
            print(f"✓ Loaded {len(agent_dict['tools'])} tools for {role}")

        crewai_agent = Agent(**agent_params)
        agents[role] = crewai_agent
    return agents


# ============================================================================
# TASKS - TDD Red-Green-Refactor Cycle
# ============================================================================


def define_tasks(agents: dict) -> list[Task]:
    """Define TDD-enforced tasks for Stage3 migration.

    Task 1 (The Trap): Create a failing test that captures expected behavior
    Task 2 (The Escape): Implement Stage3Crew to make the test pass

    Args:
        agents: Dictionary of loaded CrewAI agents

    Returns:
        List of Task objects enforcing TDD discipline
    """
    tasks = []

    # ========================================================================
    # TASK 1: THE TRAP - Create Failing Test
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 1: THE TRAP - Create Failing Reproduction Test\n\n"
                "**Goal**: Analyze legacy `src/stage3.py` and create a test that "
                "asserts the expected output of the NEW Crew. The test MUST FAIL.\n\n"
                "**Instructions**:\n"
                f"1. Analyze the legacy `src/stage3.py` module\n"
                "2. Understand its input/output interface and functionality\n"
                f"3. Write the reproduction code to disk using the `file_write` tool at `{TDD_VERIFICATION_SCRIPT}` that:\n"
                "   - Imports the NEW (not yet existing) Stage3Crew class\n"
                "   - Instantiates it with sample inputs\n"
                "   - Calls the kickoff method\n"
                "   - Asserts the expected output matches legacy behavior\n"
                f"4. **CRITICAL**: USE THE `file_write` TOOL to save the test to `{TDD_VERIFICATION_SCRIPT}`. DO NOT just show the code. SAVE IT.\n"
                "5. RUN THE TEST - it MUST FAIL because Stage3Crew doesn't exist yet\n\n"
                "**Critical TDD Rule**: You must run the test and confirm it FAILS.\n"
                "Show the test execution output with the failure message.\n\n"
                "**Expected Test Structure**:\n"
                "```python\n"
                "def test_stage3_crew_migration():\n"
                "    # Arrange\n"
                "    crew = Stage3Crew(topic='Self-Healing Tests')\n"
                "    \n"
                "    # Act\n"
                "    result = crew.kickoff()\n"
                "    \n"
                "    # Assert\n"
                "    assert 'article' in result\n"
                "    assert 'chart_data' in result\n"
                "    assert len(result['article']) > 500\n"
                "```\n\n"
                "**Deliverables**:\n"
                f"- File `{TDD_VERIFICATION_SCRIPT}` created\n"
                "- Test execution output showing FAILURE\n"
                "- Analysis of legacy src/stage3.py functionality\n"
                "- Clear acceptance criteria for the new Crew\n"
            ),
            agent=agents["migration-engineer"],
            expected_output=(
                f"1. File `{TDD_VERIFICATION_SCRIPT}` created\n"
                "2. Test execution output showing FAILURE (ImportError or AssertionError)\n"
                "3. Analysis document describing legacy Stage3 functionality\n"
                "4. Clear acceptance criteria for the new Stage3Crew\n\n"
                "Example failure output:\n"
                "```\n"
                f"$ pytest {TDD_VERIFICATION_SCRIPT} -v\n"
                "FAILED - ModuleNotFoundError: No module named 'agents.stage3_crew'\n"
                "=== 1 failed in 0.12s ===\n"
                "```"
            ),
        )
    )

    # ========================================================================
    # TASK 2: THE ESCAPE - Implement Solution
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 2: THE ESCAPE - Implement Stage3Crew\n\n"
                "**Goal**: Implement the Stage3Crew class to make the test pass. "
                "Run the test again. Iterate until it PASSES.\n\n"
                "**Instructions**:\n"
                f"1. Write the `Stage3Crew` class implementation and SAVE it to `{STAGE3_CREW_MODULE}` using the `file_write` tool\n"
                f"2. **CRITICAL**: USE THE `file_write` TOOL to save the implementation. DO NOT just show the code. SAVE IT.\n"
                "3. Implement the required methods to match legacy behavior\n"
                f"4. RUN `{TDD_VERIFICATION_SCRIPT}` again\n"
                "5. ITERATE on the implementation until the test PASSES\n\n"
                "**TDD Cycle**:\n"
                "- Red: Test fails (already done in Task 1) ✅\n"
                "- Green: Make minimal changes to pass the test\n"
                "- Refactor: Clean up code while keeping tests green\n\n"
                "**Implementation Requirements**:\n"
                "- Stage3Crew class with __init__ and kickoff methods\n"
                "- Match legacy src/stage3.py input/output interface\n"
                "- Use CrewAI agents and tasks pattern\n"
                "- Maintain backward compatibility\n\n"
                "**Success Criteria**:\n"
                f"- `pytest {TDD_VERIFICATION_SCRIPT} -v` shows PASS\n"
                "- New Crew produces same output structure as legacy Stage3\n"
                "- Code follows project standards (ruff, mypy clean)\n\n"
                "**Iteration Example**:\n"
                "1. Implement Stage3Crew skeleton → run test → see assertion failures\n"
                "2. Add basic kickoff method → run test → see partial success\n"
                "3. Add proper output structure → run test → ALL GREEN ✅\n\n"
                "**Deliverables**:\n"
                f"- File `{STAGE3_CREW_MODULE}` created\n"
                "- Test execution showing PASS\n"
                "- Side-by-side comparison: legacy vs new behavior\n"
            ),
            agent=agents["migration-engineer"],
            expected_output=(
                f"1. Stage3Crew class implemented in `{STAGE3_CREW_MODULE}`\n"
                "2. Test execution output showing PASS\n"
                "3. Comparison showing legacy and new behavior match\n"
                "4. Quality checks passed (ruff, mypy, pytest)\n\n"
                "Example success output:\n"
                "```\n"
                f"$ pytest {TDD_VERIFICATION_SCRIPT} -v\n"
                "PASSED - test_stage3_crew_migration\n"
                "=== 1 passed in 2.45s ===\n"
                "```\n\n"
                "Implementation includes:\n"
                "- Stage3Crew class with __init__ and kickoff methods\n"
                "- Proper output structure matching legacy\n"
                "- Clean, maintainable code\n"
            ),
        )
    )

    return tasks


# ============================================================================
# EXECUTION - Run TDD Mission
# ============================================================================


def run_mission():
    """Execute the TDD-enforced migration mission.

    Expected Flow:
        1. RED: Create failing test (import error, assertion failures)
        2. GREEN: Implement code iteratively until test passes
        3. REFACTOR: Improve quality while maintaining green state

    Logs must show distinct RED→GREEN transition to prove TDD discipline.
    """
    print(f"\n{'=' * 70}")
    print(f"🔴 TDD Mission: Story {STORY_ID} - RED-GREEN-REFACTOR")
    print(f"{'=' * 70}")
    print(f"\nContext: {STORY_CONTEXT}")
    print(f"\nRequired Agents: {', '.join(REQUIRED_AGENTS)}")
    print("\nTDD Protocol:")
    print(f"  1️⃣  RED: Create {TDD_VERIFICATION_SCRIPT} (MUST FAIL)")
    print(f"  2️⃣  GREEN: Implement {STAGE3_CREW_MODULE} (MUST PASS)")
    print("  3️⃣  REFACTOR: Clean up while keeping tests green")
    print(f"\n{'=' * 70}\n")

    # Initialize registry and load agents
    registry = AgentRegistry()
    agents = load_agents(registry)

    # Define TDD tasks
    tasks = define_tasks(agents)

    # Create and execute crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,  # Show detailed execution logs (critical for TDD evidence)
    )

    # Run the TDD mission
    print("\n🚀 Starting TDD Mission...\n")
    result = crew.kickoff()

    # Log results with TDD phase markers
    log_path = Path("docs/sprint_logs/story_10_tdd_log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as f:
        f.write(f"# TDD Mission Log: Story {STORY_ID}\n\n")
        f.write(f"**Context:** {STORY_CONTEXT}\n\n")
        f.write(f"**Agents:** {', '.join(REQUIRED_AGENTS)}\n\n")
        f.write("## TDD Protocol\n\n")
        f.write("1. **RED**: Create failing test (verification script)\n")
        f.write("2. **GREEN**: Implement minimum code to pass\n")
        f.write("3. **REFACTOR**: Improve quality while maintaining green\n\n")
        f.write("## Execution Output\n\n")
        f.write(f"{result}\n")
        f.write("\n## TDD Evidence\n\n")
        f.write("### RED Phase\n")
        f.write("- [ ] Verification script created\n")
        f.write("- [ ] Test execution shows FAILED\n")
        f.write("- [ ] Error proves expected code missing\n\n")
        f.write("### GREEN Phase\n")
        f.write("- [ ] Stage3Crew implementation created\n")
        f.write("- [ ] Test execution shows PASSED\n")
        f.write("- [ ] All assertions successful\n\n")
        f.write("### REFACTOR Phase\n")
        f.write("- [ ] Code quality improvements applied\n")
        f.write("- [ ] Tests still passing (no regression)\n")
        f.write("- [ ] Type hints, docstrings, error handling added\n\n")

    print("\n✅ TDD Mission Complete")
    print(f"📝 Log saved: {log_path}")
    print(f"\n{'=' * 70}")
    print("TDD Validation Checklist:")
    print("  🔴 Did Task 1 show FAILED tests? (RED state)")
    print("  🟢 Did Task 2 show PASSED tests? (GREEN state)")
    print("  🔵 Did Task 3 maintain PASSED tests? (REFACTOR state)")
    print(f"{'=' * 70}\n")

    # Validate TDD discipline
    if Path(TDD_VERIFICATION_SCRIPT).exists():
        print(f"✅ Verification script exists: {TDD_VERIFICATION_SCRIPT}")
    else:
        print(f"❌ Missing verification script: {TDD_VERIFICATION_SCRIPT}")

    if Path(STAGE3_CREW_MODULE).exists():
        print(f"✅ Implementation exists: {STAGE3_CREW_MODULE}")
    else:
        print(f"❌ Missing implementation: {STAGE3_CREW_MODULE}")

    print("\n🎯 Next Steps:")
    print(f"   1. Review TDD log: {log_path}")
    print("   2. Verify RED→GREEN transition in logs")
    print(f"   3. Run: pytest {TDD_VERIFICATION_SCRIPT} -v")
    print("   4. Commit with message: 'Story 10: Stage 3 Migration (TDD Complete)'")

    return result


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    run_mission()
