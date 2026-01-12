#!/usr/bin/env python3
"""
Development Crew - Feature Implementation with Senior Developer Review

Implements feature development using TDD pattern with comprehensive code review.

Architecture:
    1. TDD Red Phase - Write failing tests first
    2. TDD Green Phase - Implement minimum code to pass
    3. Senior Review Phase - Architecture and quality review
    4. TDD Refactor Phase - Clean up while keeping tests green

Usage:
    from src.crews.development_crew import DevelopmentCrew

    crew = DevelopmentCrew()
    result = crew.kickoff({
        "story_title": "Add user authentication",
        "acceptance_criteria": ["AC1", "AC2", "AC3"],
        "implementation_context": {...}
    })
"""

from typing import Any

from crewai import Agent, Crew, Task
from crewai.process import Process

from scripts.agent_registry import AgentRegistry


class DevelopmentCrew:
    """Feature development crew using TDD with senior developer review."""

    def __init__(self):
        """Initialize development crew with required agents."""
        self.registry = AgentRegistry()
        self.agents = self._create_agents()
        self.crew = self._create_crew()

    def _create_agents(self) -> dict[str, Agent]:
        """Create agents for the development crew."""
        # Load agent configurations
        code_quality_config = self.registry.get_agent("code-quality-specialist")
        test_specialist_config = self.registry.get_agent("test-specialist")
        code_reviewer_config = self.registry.get_agent("code-reviewer")
        git_operator_config = self.registry.get_agent("git-operator")

        # Create CrewAI Agent instances
        agents = {
            "code_quality_specialist": Agent(
                role=code_quality_config["role"],
                goal=code_quality_config["goal"],
                backstory=code_quality_config["backstory"],
                verbose=True,
                allow_delegation=False,
                llm=code_quality_config["llm_client"],
                tools=code_quality_config["tools"],
            ),
            "test_specialist": Agent(
                role=test_specialist_config["role"],
                goal=test_specialist_config["goal"],
                backstory=test_specialist_config["backstory"],
                verbose=True,
                allow_delegation=False,
                llm=test_specialist_config["llm_client"],
                tools=test_specialist_config["tools"],
            ),
            "code_reviewer": Agent(
                role=code_reviewer_config["role"],
                goal="Conduct comprehensive code review with architecture and quality focus",
                backstory=code_reviewer_config["backstory"],
                verbose=True,
                allow_delegation=False,
                llm=code_reviewer_config["llm_client"],
                tools=code_reviewer_config["tools"],
            ),
            "git_operator": Agent(
                role=git_operator_config["role"],
                goal="Execute git operations with proper commit standards and pre-commit handling",
                backstory=git_operator_config["backstory"],
                verbose=True,
                allow_delegation=False,
                llm=git_operator_config["llm_client"],
                tools=git_operator_config["tools"],
            ),
        }

        return agents

    def _create_tasks(self, story_data: dict[str, Any]) -> list[Task]:
        """Create TDD workflow tasks for story implementation."""

        # Task 1: TDD Red Phase - Write failing tests
        tdd_red_task = Task(
            description=f"""
            **TDD RED PHASE**: Write failing tests for story implementation.

            **Story**: {story_data.get('story_title', 'No title provided')}

            **Acceptance Criteria**:
            {chr(10).join(f'- {ac}' for ac in story_data.get('acceptance_criteria', []))}

            **Your Task**:
            1. Analyze the acceptance criteria and break down into testable scenarios
            2. Write comprehensive test cases that will fail initially (RED phase)
            3. Cover happy path, edge cases, and error scenarios
            4. Follow Test Pyramid principles (unit > integration > e2e)
            5. Use pytest fixtures and parametrization where appropriate

            **Critical Rule**: Tests MUST fail initially - you're defining what success looks like.

            **Output Required**:
            - Test files saved to tests/ directory
            - All tests failing (RED state confirmed)
            - Test coverage plan documented
            """,
            agent=self.agents["test_specialist"],
            expected_output="Test files created in tests/ directory with failing tests that define success criteria. Tests cover all acceptance criteria and edge cases.",
        )

        # Task 2: TDD Green Phase - Implement minimum code
        implementation_task = Task(
            description=f"""
            **TDD GREEN PHASE**: Implement minimum code to make tests pass.

            **Story**: {story_data.get('story_title', 'No title provided')}

            **Context**: You have failing tests that define the requirements. Your job is to implement the MINIMUM code needed to make those tests pass.

            **Your Task**:
            1. Analyze the failing tests to understand requirements
            2. Implement code that makes tests pass (GREEN phase)
            3. Follow Python quality standards (type hints, docstrings, error handling)
            4. Use orjson instead of json, logger instead of print
            5. Keep implementation simple and focused

            **Critical Rules**:
            - Make tests pass with minimum viable implementation
            - Don't over-engineer - just make it work
            - Follow established patterns from codebase
            - All type hints mandatory

            **Output Required**:
            - Implementation files in appropriate directories
            - All tests passing (GREEN state confirmed)
            - Code follows quality standards
            """,
            agent=self.agents["code_quality_specialist"],
            context=[tdd_red_task],
            expected_output="Implementation code that makes all tests pass. Code follows quality standards with type hints, docstrings, and proper error handling.",
        )

        # Task 3: Senior Developer Review
        code_review_task = Task(
            description=f"""
            **SENIOR DEVELOPER REVIEW**: Comprehensive code review with architecture focus.

            **Story**: {story_data.get('story_title', 'No title provided')}

            **Context**: Implementation is complete and tests are passing. Conduct a thorough senior developer review.

            **Your Review Focus**:
            1. **Architecture & Design**: Clean abstractions, proper separation of concerns
            2. **Code Quality**: Readability, maintainability, reusability
            3. **Security**: Input validation, error handling, security boundaries
            4. **Performance**: Efficiency, scalability considerations
            5. **Standards**: Team conventions, documentation, testing

            **Review Process**:
            1. Assess change impact and risk level
            2. Line-by-line code review with specific feedback
            3. Architecture review and design pattern evaluation
            4. Provide approval status and recommendations

            **Output Required**:
            - Detailed code review with specific line-by-line feedback
            - Architecture assessment and recommendations
            - Approval status (✅ Approved | ⚠️ Conditional | ❌ Rejected)
            - List of any blocking issues that must be addressed
            """,
            agent=self.agents["code_reviewer"],
            context=[tdd_red_task, implementation_task],
            expected_output="Comprehensive code review with architectural feedback, specific suggestions, and approval status. Any critical issues are clearly identified.",
        )

        # Task 4: TDD Refactor Phase - Clean up code
        refactor_task = Task(
            description=f"""
            **TDD REFACTOR PHASE**: Improve code quality while keeping tests green.

            **Story**: {story_data.get('story_title', 'No title provided')}

            **Context**: Code review feedback has been provided. Address any issues and improve code quality while maintaining all passing tests.

            **Your Task**:
            1. Address all critical issues from code review
            2. Implement suggested improvements where appropriate
            3. Refactor for better readability and maintainability
            4. Extract reusable components if patterns emerge
            5. Update documentation and comments
            6. Ensure all tests continue passing throughout

            **Critical Rules**:
            - Tests must remain green throughout refactoring
            - Address all blocking issues from review
            - Don't change functionality - only improve structure
            - Run quality checks continuously

            **Final Validation**:
            - Run full test suite and confirm 100% pass rate
            - Run quality tools (ruff, mypy) and confirm no violations
            - Verify story acceptance criteria are met
            - Update any relevant documentation

            **Output Required**:
            - Refactored code addressing review feedback
            - All tests passing with maintained coverage
            - Quality tools showing zero violations
            - Story marked as implementation complete
            """,
            agent=self.agents["code_quality_specialist"],
            context=[tdd_red_task, implementation_task, code_review_task],
            expected_output="Refactored code that addresses all review feedback while maintaining passing tests. Quality tools show zero violations and story is implementation complete.",
        )

        # Task 5: Git Operations - Commit and push changes
        git_operations_task = Task(
            description=f"""
            **GIT OPERATIONS PHASE**: Commit and push completed story to repository.

            **Story**: {story_data.get('story_title', 'No title provided')}

            **Context**: Code has been implemented, reviewed, and refactored. All tests are passing and quality standards are met. Time to commit the changes.

            **Your Task**:
            1. Check git status to see all changed files
            2. Stage all relevant files for commit (exclude any temp/generated files)
            3. Create commit message following the exact template:
               ```
               Story {story_data.get('story_number', 'N')}: {story_data.get('story_title', 'Story Title')}

               - Implemented story requirements with TDD approach
               - All tests passing and code review approved
               - Quality standards met and refactoring complete

               Progress: Story {story_data.get('story_number', 'N')} Complete
               ```
            4. Execute the Double Commit Protocol:
               - Initial commit attempt
               - If pre-commit hooks modify files: stage changes and amend commit
            5. Push changes to repository
            6. Verify push was successful

            **Critical Rules**:
            - ALWAYS follow the "Story N:" commit message format
            - ALWAYS use the Double Commit Protocol for pre-commit hooks
            - NEVER use --no-verify unless explicitly required
            - Verify all files are properly committed before pushing

            **Output Required**:
            - All story changes committed to git with proper message format
            - Changes successfully pushed to remote repository
            - Commit hash and push confirmation provided
            - Story marked as complete in git history
            """,
            agent=self.agents["git_operator"],
            context=[
                tdd_red_task,
                implementation_task,
                code_review_task,
                refactor_task,
            ],
            expected_output="All story code changes committed to git with proper format and successfully pushed to remote repository. Commit hash and push confirmation provided.",
        )

        return [
            tdd_red_task,
            implementation_task,
            code_review_task,
            refactor_task,
            git_operations_task,
        ]

    def _create_crew(self) -> Crew:
        """Create the development crew with sequential TDD process."""
        return Crew(
            agents=list(self.agents.values()),
            tasks=[],  # Tasks created per story
            process=Process.sequential,
            verbose=True,
            memory=False,  # Disable memory to avoid embeddings requirement
        )

    def kickoff(self, story_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute TDD workflow for story implementation.

        Args:
            story_data: Dictionary containing story details:
                - story_title: Story title
                - acceptance_criteria: List of acceptance criteria
                - implementation_context: Additional context

        Returns:
            Dictionary with implementation results and metrics
        """
        # Create tasks for this specific story
        tasks = self._create_tasks(story_data)

        # Update crew with story-specific tasks
        self.crew.tasks = tasks

        # Execute the TDD workflow
        try:
            result = self.crew.kickoff()

            return {
                "status": "success",
                "story_title": story_data.get("story_title"),
                "implementation_result": result,
                "phases_completed": [
                    "TDD Red (Tests Written)",
                    "TDD Green (Implementation)",
                    "Senior Review (Architecture)",
                    "TDD Refactor (Quality)",
                    "Git Operations (Committed & Pushed)",
                ],
                "quality_metrics": {
                    "tests_passing": True,
                    "code_review_approved": True,
                    "quality_standards_met": True,
                    "git_committed": True,
                    "changes_pushed": True,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "story_title": story_data.get("story_title"),
                "error": str(e),
                "phase_failed": "TDD Workflow Execution",
            }


# Example usage for testing
if __name__ == "__main__":
    # Test story data
    test_story = {
        "story_title": "Add user authentication validation",
        "acceptance_criteria": [
            "Given user provides email and password, when credentials are valid, then user is authenticated",
            "Given user provides invalid credentials, when login attempted, then error message is displayed",
            "Given user is authenticated, when accessing protected resource, then access is granted",
        ],
        "implementation_context": {
            "module": "scripts/auth_validator.py",
            "test_location": "tests/test_auth_validator.py",
        },
    }

    # Create and execute crew
    dev_crew = DevelopmentCrew()
    result = dev_crew.kickoff(test_story)

    print("\n" + "=" * 70)
    print("DEVELOPMENT CREW EXECUTION COMPLETE")
    print("=" * 70)
    print(f"Story: {result['story_title']}")
    print(f"Status: {result['status']}")

    if result["status"] == "success":
        print(f"Phases: {', '.join(result['phases_completed'])}")
        print(f"Quality: {result['quality_metrics']}")
    else:
        print(f"Error: {result['error']}")
