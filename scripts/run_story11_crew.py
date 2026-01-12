#!/usr/bin/env python3
"""
Story 11: Transplant Logic from Legacy to Crew - Stage 3 Enhancement

CrewAI migration enhancement for Stage 3, transplanting complete logic and prompts.

Context:
    AS A Migration Engineer,
    I WANT to transplant the ACTUAL logic and prompts from legacy Stage 3,
    SO THAT the new Crew has complete feature parity.

Goal:
    Transplant logic from Legacy to Crew by:
    1. Reading legacy code to identify Prompt Templates and Main Logic Loop
    2. Rewriting Stage3Crew with full CrewAI Task/Agent definitions
    3. Updating tests to validate output matches legacy format
    4. Verifying all tests pass

Usage:
    python3 scripts/run_story11_crew.py

Expected Output:
    - Enhanced src/crews/stage3_crew.py with full logic transplant
    - Updated tests/reproduce_stage3.py with format validation
    - All tests passing with comprehensive assertions
"""

from pathlib import Path

from crewai import Agent, Crew, Task

from scripts.agent_registry import AgentRegistry

# ============================================================================
# CONFIGURATION
# ============================================================================

STORY_ID = "11"
STORY_CONTEXT = "Transplant logic from Legacy to Crew for Stage 3"
REQUIRED_AGENTS = ["code-quality-specialist"]

# File paths for logic transplant
LEGACY_STAGE3_PATH = "scripts/economist_agent.py"  # Legacy Stage 3 logic location
STAGE3_CREW_MODULE = "src/crews/stage3_crew.py"
TEST_MODULE = "tests/reproduce_stage3.py"

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
# TASKS - Logic Transplant Workflow
# ============================================================================


def define_tasks(agents: dict) -> list[Task]:
    """Define tasks for logic transplant from Legacy to Crew.

    Task 1: Analysis - Identify prompts and logic from legacy
    Task 2: Injection - Rewrite Stage3Crew with full logic
    Task 3: Test Update - Add assertions for format validation
    Task 4: Verification - Run tests and ensure they pass

    Args:
        agents: Dictionary of loaded CrewAI agents

    Returns:
        List of Task objects for logic transplant workflow
    """
    tasks = []

    # ========================================================================
    # TASK 1: ANALYSIS - Read Legacy and Identify Components
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 1: ANALYSIS - Identify Prompt Templates and Logic\n\n"
                "**Goal**: Read the legacy Stage 3 code and identify the key components "
                "that need to be transplanted.\n\n"
                "**Instructions**:\n"
                f"1. Read `{LEGACY_STAGE3_PATH}` using the `file_read` tool\n"
                "2. Identify and extract:\n"
                "   - **Prompt Templates**: System prompts, instructions for agents\n"
                "   - **Main Logic Loop**: The core algorithm/workflow\n"
                "   - **Input/Output Interfaces**: Data structures used\n"
                "   - **Error Handling**: How failures are managed\n"
                "3. Document the findings in a structured format:\n"
                "   - List all prompt templates with their purposes\n"
                "   - Describe the main logic flow step-by-step\n"
                "   - Note any configuration or constants\n"
                "   - Identify dependencies on other modules\n\n"
                "**Critical Focus Areas**:\n"
                "- RESEARCH_AGENT_PROMPT: What does research agent do?\n"
                "- WRITER_AGENT_PROMPT: What are the writing instructions?\n"
                "- GRAPHICS_AGENT_PROMPT: How are charts generated?\n"
                "- EDITOR_AGENT_PROMPT: What quality gates exist?\n"
                "- Main orchestration: How do agents coordinate?\n\n"
                "**Deliverables**:\n"
                "- Comprehensive analysis document listing:\n"
                "  1. All prompt templates found\n"
                "  2. Main logic loop/workflow\n"
                "  3. Key data structures and interfaces\n"
                "  4. Dependencies and imports needed\n"
            ),
            agent=agents["code-quality-specialist"],
            expected_output=(
                "Analysis document containing:\n"
                "1. List of prompt templates with descriptions\n"
                "2. Step-by-step main logic flow\n"
                "3. Data structures and interfaces\n"
                "4. Dependencies identified\n\n"
                "Example format:\n"
                "```\n"
                "PROMPT TEMPLATES:\n"
                "1. RESEARCH_AGENT_PROMPT: 'You are a research analyst...'\n"
                "2. WRITER_AGENT_PROMPT: 'You are an Economist writer...'\n\n"
                "MAIN LOGIC LOOP:\n"
                "Step 1: Research phase (gather data)\n"
                "Step 2: Writing phase (draft article)\n"
                "Step 3: Graphics phase (generate charts)\n"
                "Step 4: Editor phase (quality gates)\n"
                "```"
            ),
        )
    )

    # ========================================================================
    # TASK 2: INJECTION - Rewrite Stage3Crew with Full Logic
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 2: INJECTION - Rewrite Stage3Crew with Transplanted Logic\n\n"
                "**Goal**: Read the current Stage3Crew and rewrite it to include all "
                "the prompts and logic identified in Task 1.\n\n"
                "**Instructions**:\n"
                f"1. Read current `{STAGE3_CREW_MODULE}` using the `file_read` tool\n"
                "2. Rewrite it using CrewAI Task and Agent definitions:\n"
                "   - Define separate agents for each phase (research, writer, graphics, editor)\n"
                "   - Create tasks with the full prompt templates\n"
                "   - Implement the main logic loop using CrewAI workflow\n"
                "   - Maintain the same input/output interface\n"
                f"3. **CRITICAL**: USE the `file_write` tool to SAVE the rewritten code to `{STAGE3_CREW_MODULE}`\n"
                "4. Ensure the new implementation:\n"
                "   - Uses proper CrewAI Agent and Task classes\n"
                "   - Includes all prompt templates as task descriptions\n"
                "   - Follows the same workflow as legacy\n"
                "   - Maintains backward compatibility (same kickoff interface)\n\n"
                "**Required Structure**:\n"
                "```python\n"
                "class Stage3Crew:\n"
                "    def __init__(self, topic: str):\n"
                "        self.topic = topic\n"
                "        self._setup_agents()\n"
                "        self._setup_tasks()\n"
                "    \n"
                "    def _setup_agents(self):\n"
                "        # Define research, writer, graphics, editor agents\n"
                "        pass\n"
                "    \n"
                "    def _setup_tasks(self):\n"
                "        # Define tasks with full prompts\n"
                "        pass\n"
                "    \n"
                "    def kickoff(self) -> dict:\n"
                "        # Execute crew and return results\n"
                "        crew = Crew(agents=self.agents, tasks=self.tasks)\n"
                "        result = crew.kickoff()\n"
                "        return {'article': result.article, 'chart_data': result.chart}\n"
                "```\n\n"
                "**Deliverables**:\n"
                f"- File `{STAGE3_CREW_MODULE}` rewritten with full logic\n"
                "- All prompt templates included as task descriptions\n"
                "- CrewAI agents and tasks properly defined\n"
                "- Same kickoff() interface maintained\n"
            ),
            agent=agents["code-quality-specialist"],
            expected_output=(
                f"1. File `{STAGE3_CREW_MODULE}` rewritten and saved\n"
                "2. Contains CrewAI Agent definitions for all phases\n"
                "3. Contains Task definitions with full prompts\n"
                "4. Implements proper workflow orchestration\n"
                "5. Maintains backward-compatible interface\n\n"
                "Implementation includes:\n"
                "- Research agent with RESEARCH_AGENT_PROMPT\n"
                "- Writer agent with WRITER_AGENT_PROMPT\n"
                "- Graphics agent with GRAPHICS_AGENT_PROMPT\n"
                "- Editor agent with EDITOR_AGENT_PROMPT\n"
                "- Orchestrated workflow matching legacy\n"
            ),
        )
    )

    # ========================================================================
    # TASK 3: TEST UPDATE - Add Format Validation Assertions
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 3: TEST UPDATE - Add Assertions for Format Validation\n\n"
                "**Goal**: Update the test to validate that output matches legacy format.\n\n"
                "**Instructions**:\n"
                f"1. Read current `{TEST_MODULE}` using the `file_read` tool\n"
                "2. Add comprehensive assertions:\n"
                "   - Check output is not empty\n"
                "   - Validate article structure (has title, body, etc.)\n"
                "   - Validate chart_data structure (has data points)\n"
                "   - Check output mimics legacy format\n"
                "   - Validate required fields are present\n"
                f"3. **CRITICAL**: USE the `file_write` tool to SAVE the updated test to `{TEST_MODULE}`\n\n"
                "**Required Assertions**:\n"
                "```python\n"
                "def test_stage3_crew_migration():\n"
                "    # Arrange\n"
                "    crew = Stage3Crew(topic='Self-Healing Tests')\n"
                "    \n"
                "    # Act\n"
                "    result = crew.kickoff()\n"
                "    \n"
                "    # Assert - Structure\n"
                "    assert 'article' in result\n"
                "    assert 'chart_data' in result\n"
                "    \n"
                "    # Assert - Not Empty\n"
                "    assert result['article'] is not None\n"
                "    assert len(result['article']) > 500\n"
                "    assert result['chart_data'] is not None\n"
                "    \n"
                "    # Assert - Format Mimics Legacy\n"
                "    # Article should contain typical Economist elements\n"
                "    article = result['article']\n"
                "    assert '---' in article  # YAML frontmatter\n"
                "    assert 'title:' in article\n"
                "    assert 'date:' in article\n"
                "    \n"
                "    # Chart data should have structure\n"
                "    chart = result['chart_data']\n"
                "    assert isinstance(chart, dict)\n"
                "    # Add specific chart structure checks based on legacy format\n"
                "```\n\n"
                "**Deliverables**:\n"
                f"- File `{TEST_MODULE}` updated with comprehensive assertions\n"
                "- Tests validate output structure\n"
                "- Tests validate output is not empty\n"
                "- Tests validate format mimics legacy\n"
            ),
            agent=agents["code-quality-specialist"],
            expected_output=(
                f"1. File `{TEST_MODULE}` updated and saved\n"
                "2. Contains comprehensive assertions:\n"
                "   - Structure validation (keys present)\n"
                "   - Non-empty validation (content exists)\n"
                "   - Format validation (mimics legacy)\n"
                "3. Tests are ready to run\n\n"
                "Updated test includes:\n"
                "- Basic structure checks\n"
                "- Length/emptiness validations\n"
                "- Legacy format mimicry checks\n"
                "- Comprehensive coverage of output\n"
            ),
        )
    )

    # ========================================================================
    # TASK 4: VERIFICATION - Run Tests and Ensure Pass
    # ========================================================================
    tasks.append(
        Task(
            description=(
                "## TASK 4: VERIFICATION - Run Tests and Ensure They Pass\n\n"
                "**Goal**: Execute the tests and verify all assertions pass.\n\n"
                "**Instructions**:\n"
                f"1. Run the test: `pytest {TEST_MODULE} -v`\n"
                "2. If tests FAIL:\n"
                f"   - Read the failure output\n"
                f"   - Fix issues in `{STAGE3_CREW_MODULE}`\n"
                f"   - Rerun tests until they PASS\n"
                "3. If tests PASS:\n"
                "   - Document the success\n"
                "   - Verify all assertions executed\n"
                "   - Confirm output matches legacy format\n\n"
                "**Success Criteria**:\n"
                "- All tests pass (no failures, no errors)\n"
                "- Output structure matches legacy\n"
                "- Output content is not empty\n"
                "- Format validation assertions all pass\n\n"
                "**Deliverables**:\n"
                "- Test execution output showing PASS\n"
                "- Verification that all assertions executed\n"
                "- Confirmation of legacy format compliance\n"
            ),
            agent=agents["code-quality-specialist"],
            expected_output=(
                "Test execution results:\n"
                "```\n"
                f"$ pytest {TEST_MODULE} -v\n"
                "test_stage3_crew_migration PASSED\n"
                "=== 1 passed in X.XXs ===\n"
                "```\n\n"
                "Verification confirms:\n"
                "1. All assertions passed\n"
                "2. Output structure correct\n"
                "3. Output not empty\n"
                "4. Format matches legacy\n"
                "5. Stage3Crew fully functional\n"
            ),
        )
    )

    return tasks


# ============================================================================
# EXECUTION - Run Logic Transplant Mission
# ============================================================================


def run_mission():
    """Execute the logic transplant mission.

    Expected Flow:
        1. ANALYSIS: Read legacy code, identify components
        2. INJECTION: Rewrite Stage3Crew with full logic
        3. TEST UPDATE: Add comprehensive assertions
        4. VERIFICATION: Run tests, ensure they pass
    """
    print(f"\n{'=' * 70}")
    print(f"🧬 Logic Transplant Mission: Story {STORY_ID}")
    print(f"{'=' * 70}")
    print(f"\nContext: {STORY_CONTEXT}")
    print(f"\nRequired Agents: {', '.join(REQUIRED_AGENTS)}")
    print("\nTransplant Protocol:")
    print(f"  1️⃣  ANALYSIS: Read {LEGACY_STAGE3_PATH}")
    print(f"  2️⃣  INJECTION: Rewrite {STAGE3_CREW_MODULE}")
    print(f"  3️⃣  TEST UPDATE: Enhance {TEST_MODULE}")
    print("  4️⃣  VERIFICATION: Run tests")
    print(f"\n{'=' * 70}\n")

    # Initialize registry and load agents
    registry = AgentRegistry()
    agents = load_agents(registry)

    # Define transplant tasks
    tasks = define_tasks(agents)

    # Create and execute crew
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,
    )

    # Run the transplant mission
    print("\n🚀 Starting Logic Transplant Mission...\n")
    result = crew.kickoff()

    # Log results
    log_path = Path("docs/sprint_logs/story_11_transplant_log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as f:
        f.write(f"# Logic Transplant Log: Story {STORY_ID}\n\n")
        f.write(f"**Context:** {STORY_CONTEXT}\n\n")
        f.write(f"**Agents:** {', '.join(REQUIRED_AGENTS)}\n\n")
        f.write("## Transplant Protocol\n\n")
        f.write("1. **ANALYSIS**: Read legacy code, identify components\n")
        f.write("2. **INJECTION**: Rewrite Stage3Crew with full logic\n")
        f.write("3. **TEST UPDATE**: Add comprehensive assertions\n")
        f.write("4. **VERIFICATION**: Run tests, ensure they pass\n\n")
        f.write("## Execution Output\n\n")
        f.write(f"{result}\n")
        f.write("\n## Verification Evidence\n\n")
        f.write("### Analysis Phase\n")
        f.write("- [ ] Legacy code analyzed\n")
        f.write("- [ ] Prompt templates identified\n")
        f.write("- [ ] Main logic loop documented\n\n")
        f.write("### Injection Phase\n")
        f.write("- [ ] Stage3Crew rewritten\n")
        f.write("- [ ] CrewAI agents defined\n")
        f.write("- [ ] Tasks include full prompts\n\n")
        f.write("### Test Update Phase\n")
        f.write("- [ ] Assertions added for structure\n")
        f.write("- [ ] Assertions added for non-empty\n")
        f.write("- [ ] Assertions added for format\n\n")
        f.write("### Verification Phase\n")
        f.write("- [ ] Tests executed\n")
        f.write("- [ ] All tests passed\n")
        f.write("- [ ] Output validated\n\n")

    print("\n✅ Logic Transplant Mission Complete")
    print(f"📝 Log saved: {log_path}")
    print(f"\n{'=' * 70}")
    print("Validation Checklist:")
    print("  📖 Analysis documented?")
    print("  💉 Logic transplanted?")
    print("  🧪 Tests enhanced?")
    print("  ✅ Tests passing?")
    print(f"{'=' * 70}\n")

    # Validate deliverables
    if Path(STAGE3_CREW_MODULE).exists():
        print(f"✅ Stage3Crew exists: {STAGE3_CREW_MODULE}")
    else:
        print(f"❌ Missing Stage3Crew: {STAGE3_CREW_MODULE}")

    if Path(TEST_MODULE).exists():
        print(f"✅ Tests exist: {TEST_MODULE}")
    else:
        print(f"❌ Missing tests: {TEST_MODULE}")

    print("\n🎯 Next Steps:")
    print(f"   1. Review transplant log: {log_path}")
    print("   2. Verify logic completeness")
    print(f"   3. Run: pytest {TEST_MODULE} -v")
    print("   4. Commit with message: 'Story 11: Stage 3 Logic Transplant Complete'")

    return result


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    run_mission()
