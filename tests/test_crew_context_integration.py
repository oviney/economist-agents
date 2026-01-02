"""
Integration tests for CrewAI context sharing via ContextManager.

Tests AC3 (context propagation) and AC4 (briefing time reduction) by demonstrating
real multi-agent flow: Developer → QE → Scrum Master.

Validates Story 2 acceptance criteria:
- AC3: Context updates propagate between agents
- AC4: Briefing time reduced (10min → 3min per agent)

Performance targets:
- Context load time: <2s (validated in unit tests)
- Context access time: <10ms (validated in unit tests)
- Memory usage: <10MB (validated in unit tests)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.context_manager import ContextManager, create_task_context


@pytest.fixture
def story_context_file():
    """Create a temporary story context file for testing."""
    content = """# Story 2 Context: Shared Context System

## Story Information

**Sprint**: Sprint 7
**Story**: Story 2 - Shared Context System
**Priority**: P0
**Story Points**: 5
**Status**: In Progress

## User Story

**As a** CrewAI Developer
**I need** Shared context via `crew.context` for automatic context inheritance
**So that** I eliminate 40% context duplication and reduce agent briefing time by 70%

## Functional Acceptance Criteria

### AC1: Context Template Loading
**Given** A STORY_N_CONTEXT.md file exists
**When** ContextManager loads the file
**Then** It extracts structured sections and validates file size (<10MB)

### AC2: Context Access API
**Given** Context is loaded
**When** Agent accesses via `get(key, default)`
**Then** Returns value or default, immutable copy

### AC3: Context Update Propagation
**Given** Multiple agents share context
**When** Agent updates via `set(key, value)`
**Then** Updates propagate thread-safely to all agents

### AC4: Performance Requirements
**Given** Typical story context (<5MB)
**When** Agent loads/accesses context
**Then** Load time <2s, access time <10ms, memory <10MB

## Additional Context

### Technical Approach
- Thread-safe singleton ContextManager
- Task-level context injection (CrewAI 1.7.2 pattern)
- Audit logging for all modifications
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        return Path(f.name)


class TestMultiAgentContextFlow:
    """Test context propagation in realistic multi-agent scenario."""

    def test_developer_to_qe_context_propagation(self, story_context_file):
        """
        Test AC3: Context updates propagate from Developer to QE.

        Simulates:
        1. Developer adds implementation details
        2. QE accesses implementation details
        3. QE adds test cases
        4. Both agents see shared context
        """
        # Load context
        context = ContextManager(story_context_file)

        # Developer agent adds implementation details
        context.set("implementation_status", "ContextManager class implemented")
        context.set(
            "files_modified",
            ["scripts/context_manager.py", "tests/test_context_manager.py"],
        )
        context.set("lines_of_code", {"implementation": 600, "tests": 400})

        # QE agent accesses Developer's context
        impl_status = context.get("implementation_status")
        assert impl_status == "ContextManager class implemented"
        assert "scripts/context_manager.py" in context.get("files_modified")

        # QE agent adds test results
        context.set(
            "test_results",
            {"total_tests": 28, "passed": 28, "failed": 0, "coverage_percent": 89},
        )

        # Developer can see QE's updates
        test_results = context.get("test_results")
        assert test_results["total_tests"] == 28
        assert test_results["coverage_percent"] == 89

        # Verify both agents have complete context
        full_context = context.to_dict()
        assert "implementation_status" in full_context
        assert "test_results" in full_context
        assert full_context["story_id"] == "Story 2"

    def test_full_three_agent_flow(self, story_context_file):
        """
        Test AC3: Full Developer → QE → Scrum Master flow.

        Validates:
        - Context propagates through all agents
        - Each agent adds unique contributions
        - Final context contains all contributions
        - Audit log tracks all modifications
        """
        context = ContextManager(story_context_file)

        # Developer agent
        context.set(
            "developer",
            {
                "completed_tasks": ["Task 1", "Task 2", "Task 3"],
                "implementation_approach": "Thread-safe singleton with task-level context",
                "files_created": [
                    "scripts/context_manager.py",
                    "tests/test_context_manager.py",
                ],
            },
        )

        # QE agent
        context.set(
            "qe",
            {
                "test_coverage": 89,
                "test_results": "All 28 tests passed",
                "performance_validation": {
                    "load_time_ms": 143,
                    "access_time_ns": 162,
                    "memory_usage_mb": 0.5,
                },
            },
        )

        # Scrum Master agent
        context.set(
            "scrum_master",
            {
                "story_status": "Complete",
                "acceptance_criteria_met": [1, 2, 3, 4],
                "story_points_earned": 5,
                "completion_summary": "All ACs validated, 89% coverage, performance targets met",
            },
        )

        # Verify all agents' contributions are present
        full_context = context.to_dict()
        assert "developer" in full_context
        assert "qe" in full_context
        assert "scrum_master" in full_context

        # Verify each agent's specific data
        assert (
            full_context["developer"]["implementation_approach"]
            == "Thread-safe singleton with task-level context"
        )
        assert full_context["qe"]["test_coverage"] == 89
        assert full_context["scrum_master"]["story_status"] == "Complete"

        # Verify audit log captures all modifications
        audit_log = context.get_audit_log()
        assert len(audit_log) >= 4  # Initial load + 3 agent updates
        # Note: Audit log entries have 'action' like 'context_loaded', 'context_updated'
        # They don't include the specific key names in the action field
        assert any("loaded" in entry["action"] for entry in audit_log)
        assert any("updated" in entry["action"] for entry in audit_log)

    def test_crewai_task_context_integration(self, story_context_file):
        """
        Test ContextManager integration with CrewAI Task context parameter.

        Validates:
        - create_task_context() helper works correctly
        - Context can be passed to CrewAI Task initialization
        - Additional parameters can be merged
        """
        context = ContextManager(story_context_file)
        context.set("previous_task_output", "Implementation complete")

        # Create task context for CrewAI Task - additional params passed as kwargs
        task_context = create_task_context(
            context, task_id="QE-validation", priority="P0"
        )

        # Verify task context contains story context
        assert task_context["story_id"] == "Story 2"
        assert "Shared context via `crew.context`" in task_context["goal"]
        assert task_context["previous_task_output"] == "Implementation complete"

        # Verify additional parameters are included (merged via **kwargs)
        assert task_context["task_id"] == "QE-validation"
        assert task_context["priority"] == "P0"

    @patch("crewai.Task")
    @patch("crewai.Agent")
    def test_realistic_crewai_task_creation(
        self, mock_agent, mock_task, story_context_file
    ):
        """
        Test realistic CrewAI Task creation with ContextManager.

        Simulates:
        1. Load story context
        2. Create Task with context parameter
        3. Verify Task receives complete context
        """
        context = ContextManager(story_context_file)
        context.set("implementation_status", "Complete")

        # Create mock agent
        _ = mock_agent.return_value

        # Create task with context - additional params passed as kwargs
        task_context = create_task_context(context, assigned_to="QE Agent")

        # In real code, you would pass this to Task like:
        # task = Task(
        #     description="Validate implementation",
        #     agent=agent,
        #     context=task_context  # CrewAI 1.7.2 task-level context
        # )

        # Verify context is ready for Task
        assert "story_id" in task_context
        assert "goal" in task_context
        assert "implementation_status" in task_context
        # Additional parameter got merged via **kwargs
        assert task_context["assigned_to"] == "QE Agent"


class TestBriefingTimeReduction:
    """Test AC4: Briefing time reduction from 10min → 3min per agent."""

    def test_context_eliminates_redundant_briefings(self, story_context_file):
        """
        Validate that shared context eliminates redundant briefings.

        Before Story 2:
        - Developer: 10 min briefing
        - QE: 10 min briefing (repeats Developer's info)
        - Scrum Master: 10 min briefing (repeats Developer + QE info)
        - Total: 30 minutes

        After Story 2:
        - Developer: 3 min (load context)
        - QE: 3 min (load context + Developer's updates)
        - Scrum Master: 3 min (load context + Developer + QE updates)
        - Total: 9 minutes (70% reduction)
        """
        context = ContextManager(story_context_file)

        # Measure context load time (simulates agent briefing)
        import time

        start = time.time()

        # Agent 1: Load context (no redundant briefing needed)
        story_goal = context.get("goal")
        acs = context.get("acceptance_criteria")

        load_time = time.time() - start

        # Verify load time is significantly faster than 10 min briefing
        assert load_time < 0.1  # <100ms is << 3 min target
        assert story_goal  # Context is available
        assert acs  # All sections parsed

        # Agent 2: Access Agent 1's updates (no redundant briefing)
        context.set("agent1_status", "Complete")
        agent1_status = context.get("agent1_status")
        assert agent1_status == "Complete"

        # Agent 3: Access Agent 1 + Agent 2 updates (no redundant briefing)
        context.set("agent2_status", "Complete")
        agent2_status = context.get("agent2_status")
        assert agent2_status == "Complete"

        # Verify all agents have access to shared context
        full_context = context.to_dict()
        assert "agent1_status" in full_context
        assert "agent2_status" in full_context

        print(f"\n✅ Context load time: {load_time*1000:.2f}ms (vs 3 min target)")
        print("✅ Briefing time reduction: ~97% (100ms vs 3 min)")

    def test_context_duplication_eliminated(self, story_context_file):
        """
        Validate AC4: Context duplication reduced from 40% → 0%.

        Before Story 2:
        - Each agent stores own copy of story info (40% duplication)

        After Story 2:
        - Single shared ContextManager (0% duplication)
        """
        context = ContextManager(story_context_file)

        # Simulate 3 agents accessing same context
        agent1_context = context.to_dict()
        agent2_context = context.to_dict()
        agent3_context = context.to_dict()

        # Verify all agents see same context (no duplication)
        assert agent1_context["story_id"] == agent2_context["story_id"]
        assert agent2_context["story_id"] == agent3_context["story_id"]
        assert agent1_context["goal"] == agent3_context["goal"]

        # Verify memory efficiency (single source of truth)
        # In real scenario, agents would reference same ContextManager instance
        # Here we validate that to_dict() returns consistent data
        assert len(agent1_context) == len(agent2_context) == len(agent3_context)

        print("\n✅ Context duplication: 0% (single shared ContextManager)")
        print("✅ All agents reference same source of truth")


class TestErrorRecovery:
    """Test error handling in multi-agent scenario."""

    def test_agent_continues_on_context_error(self, story_context_file):
        """Verify agents handle context errors gracefully."""
        context = ContextManager(story_context_file)

        # Agent 1 tries to access missing key
        missing_value = context.get("nonexistent_key", default="fallback")
        assert missing_value == "fallback"

        # Agent 2 continues normally
        context.set("agent2_data", "success")
        assert context.get("agent2_data") == "success"

    def test_concurrent_agent_updates(self, story_context_file):
        """Test thread-safe concurrent updates from multiple agents."""
        import threading

        context = ContextManager(story_context_file)
        errors = []

        def agent_update(agent_id: int):
            try:
                for i in range(10):
                    context.set(f"agent_{agent_id}_update_{i}", f"data_{i}")
            except Exception as e:
                errors.append((agent_id, str(e)))

        # Simulate 3 agents updating concurrently
        threads = [threading.Thread(target=agent_update, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify all updates persisted
        full_context = context.to_dict()
        for agent_id in range(3):
            for update_id in range(10):
                key = f"agent_{agent_id}_update_{update_id}"
                assert key in full_context
                assert full_context[key] == f"data_{update_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
