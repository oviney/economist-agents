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

from crewai import Crew, Task

# Use AgentFactory from crewai_agents (ADR-002 compliant)
from crewai_agents import AgentFactory

# ============================================================================
# CONFIGURATION
# ============================================================================

STORY_ID = "10"
STORY_CONTEXT = (
    "AS A Migration Engineer, I WANT to migrate Stage 3 Content Generation to CrewAI "
    "using TDD, SO THAT we have testable confidence in the migration."
)
REQUIRED_AGENTS = ["migration-engineer"]

# TDD Configuration
TDD_VERIFICATION_SCRIPT = "tests/verify_stage3_migration.py"
STAGE3_CREW_MODULE = "agents/stage3_crew.py"

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
# TASKS - TDD Red-Green-Refactor Cycle
# ============================================================================


def define_tasks(agents: dict) -> list[Task]:
    """Define tasks enforcing Red-Green-Refactor TDD discipline.

    Args:
        agents: Dictionary of loaded CrewAI agents

    Returns:
        List of Task objects for the TDD mission

    TDD Flow:
        Task 1 (RED): Create failing reproduction script
        Task 2 (GREEN): Implement code to pass test
        Task 3 (REFACTOR): Clean up while maintaining green
    """
    tasks = []

    # ========================================================================
    # TASK 1: RED STATE - Create Failing Test
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## RED PHASE: Create Failing Reproduction Script\n\n"
                f"Create `{TDD_VERIFICATION_SCRIPT}` that:\n"
                "1. Mocks the input (topic, research data)\n"
                "2. Asserts expected CrewAI output structure:\n"
                "   - Research findings with sources\n"
                "   - Article draft in Economist style\n"
                "   - Editor feedback with quality gates\n"
                "3. Attempts to import and run Stage3Crew\n"
                "4. MUST FAIL because Stage3Crew doesn't exist yet\n\n"
                "**CRITICAL**: Run this script immediately after creation.\n"
                "The output MUST show:\n"
                "- ModuleNotFoundError or ImportError for Stage3Crew\n"
                "- OR AssertionError showing expected structure missing\n"
                "- EXIT CODE: 1 (failure)\n\n"
                "**Evidence Required**:\n"
                "- pytest output showing FAILED\n"
                "- Error traceback proving code is missing\n"
                "- Clear assertion of what SHOULD exist but DOESN'T\n\n"
                "Include in script:\n"
                "```python\n"
                "# Test: Stage 3 CrewAI Migration\n"
                "def test_stage3_crew_exists():\n"
                "    from agents.stage3_crew import Stage3Crew\n"
                "    assert Stage3Crew is not None\n"
                "\n"
                "def test_content_creator_agent():\n"
                "    crew = Stage3Crew()\n"
                "    assert crew.content_creator is not None\n"
                "    assert crew.content_creator.role == 'content-creator'\n"
                "\n"
                "def test_stage3_pipeline():\n"
                "    crew = Stage3Crew()\n"
                "    result = crew.run(topic='Self-Healing Tests')\n"
                "    assert 'article' in result\n"
                "    assert 'chart_data' in result\n"
                "```\n"
            ),
            agent=agents["migration-engineer"],
            expected_output=(
                f"File created: {TDD_VERIFICATION_SCRIPT}\n"
                "Test execution output showing:\n"
                "- RED STATE CONFIRMED: Tests FAIL\n"
                "- ModuleNotFoundError or ImportError\n"
                "- Exit code: 1\n"
                "- Proof that expected code does NOT exist\n\n"
                "Example output:\n"
                "```\n"
                "$ pytest tests/verify_stage3_migration.py\n"
                "FAILED tests/verify_stage3_migration.py::test_stage3_crew_exists\n"
                "ModuleNotFoundError: No module named 'agents.stage3_crew'\n"
                "=== 3 failed in 0.12s ===\n"
                "```"
            ),
        )
    )

    # ========================================================================
    # TASK 2: GREEN STATE - Implement Minimum Code
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## GREEN PHASE: Implement Stage3Crew Class\n\n"
                f"Create `{STAGE3_CREW_MODULE}` with:\n"
                "1. Stage3Crew class with CrewAI agents:\n"
                "   - researcher (web search, arxiv tools)\n"
                "   - writer (Economist style constraints)\n"
                "   - editor (quality gates)\n"
                "2. Sequential task pipeline:\n"
                "   - Research task → JSON with sources\n"
                "   - Write task → Markdown article\n"
                "   - Edit task → Final polished article\n"
                "3. run() method that accepts topic and returns result\n\n"
                "**Reference**: ADR-003 CrewAI Migration Strategy\n"
                "- Use agents.yaml definitions from docs/ADR-003\n"
                "- Use tasks.yaml structure from docs/ADR-003\n"
                "- Maintain backward compatibility with economist_agent.py\n\n"
                "**CRITICAL**: After implementing, run the verification script again.\n"
                "Iterate until:\n"
                "- All import errors resolved\n"
                "- All assertions pass\n"
                "- EXIT CODE: 0 (success)\n\n"
                "**Evidence Required**:\n"
                "- pytest output showing PASSED\n"
                "- All 3 tests green\n"
                "- No errors or warnings\n\n"
                "Expected iteration cycle:\n"
                "1. Implement Stage3Crew skeleton → run test → see assertion failures\n"
                "2. Add researcher agent → run test → see partial success\n"
                "3. Add writer agent → run test → see more passing\n"
                "4. Add editor agent → run test → ALL GREEN\n"
            ),
            agent=agents["migration-engineer"],
            expected_output=(
                f"File created: {STAGE3_CREW_MODULE}\n"
                "Test execution output showing:\n"
                "- GREEN STATE CONFIRMED: Tests PASS\n"
                "- All assertions successful\n"
                "- Exit code: 0\n"
                "- Proof that code NOW exists and works\n\n"
                "Example output:\n"
                "```\n"
                "$ pytest tests/verify_stage3_migration.py\n"
                "PASSED tests/verify_stage3_migration.py::test_stage3_crew_exists\n"
                "PASSED tests/verify_stage3_migration.py::test_content_creator_agent\n"
                "PASSED tests/verify_stage3_migration.py::test_stage3_pipeline\n"
                "=== 3 passed in 2.45s ===\n"
                "```\n\n"
                "Implementation includes:\n"
                "- Stage3Crew class with __init__ and run() methods\n"
                "- CrewAI agents: researcher, writer, editor\n"
                "- CrewAI tasks with sequential dependencies\n"
                "- Integration with existing economist_agent.py API"
            ),
        )
    )

    # ========================================================================
    # TASK 3: REFACTOR STATE - Clean Up While Green
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## REFACTOR PHASE: Improve Code Quality\n\n"
                "With tests GREEN, refactor for quality:\n"
                "1. Add type hints to all methods\n"
                "2. Extract configuration to constants\n"
                "3. Add docstrings (Google style)\n"
                "4. Split large methods (>20 lines)\n"
                "5. Add error handling with logging\n\n"
                "**CONSTRAINT**: Tests MUST stay GREEN during refactoring.\n"
                "Run `pytest tests/verify_stage3_migration.py` after EACH change.\n"
                "If tests fail → revert last change → try different approach.\n\n"
                "**Refactoring Checklist**:\n"
                "- [ ] Type hints on all methods\n"
                "- [ ] Docstrings on all classes/methods\n"
                "- [ ] Magic numbers → named constants\n"
                "- [ ] Long methods → smaller functions\n"
                "- [ ] Try/except blocks for external calls\n"
                "- [ ] Logging for debugging\n"
                "- [ ] Tests still pass (run after each item)\n\n"
                "**Evidence Required**:\n"
                "- pytest output showing PASSED (after refactoring)\n"
                "- Diff showing improved code quality\n"
                "- No functionality changes (output identical)\n"
            ),
            agent=agents["migration-engineer"],
            expected_output=(
                "Refactored code with:\n"
                "- Type hints: Fully typed Stage3Crew class\n"
                "- Docstrings: All public methods documented\n"
                "- Configuration: Extracted to module constants\n"
                "- Error handling: try/except with logging\n"
                "- Tests: Still 100% passing (proof of no regression)\n\n"
                "Final test output:\n"
                "```\n"
                "$ pytest tests/verify_stage3_migration.py -v\n"
                "test_stage3_crew_exists PASSED\n"
                "test_content_creator_agent PASSED\n"
                "test_stage3_pipeline PASSED\n"
                "=== 3 passed in 2.41s ===\n"
                "```\n\n"
                "Code quality metrics:\n"
                "- mypy: 0 type errors\n"
                "- ruff: 0 linting errors\n"
                "- Readability: Hemingway < 10\n"
                "- Test coverage: 100% of Stage3Crew class"
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

    # Load agents using AgentFactory
    agents = load_agents()

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
