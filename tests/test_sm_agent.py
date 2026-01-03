#!/usr/bin/env python3
"""
Test Suite for Scrum Master Agent

Tests autonomous coordination capabilities:
- Task queue management
- Agent status monitoring
- Quality gate validation
- Escalation management
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sm_agent import (
    AgentStatusMonitor,
    EscalationManager,
    QualityGateValidator,
    ScrumMasterAgent,
    TaskQueueManager,
)


class TestTaskQueueManager:
    """Test task queue management"""

    @pytest.fixture
    def temp_queue(self, tmp_path):
        """Temporary queue file"""
        queue_file = tmp_path / "test_queue.json"
        return str(queue_file)

    def test_initialization(self, temp_queue):
        """Test queue manager initialization"""
        manager = TaskQueueManager(temp_queue)
        assert manager.queue_file == Path(temp_queue)
        assert manager.queue["sprint_id"] is None
        assert manager.queue["tasks"] == []

    def test_parse_backlog(self, temp_queue, tmp_path):
        """Test backlog parsing into tasks"""
        # Create test backlog
        backlog_file = tmp_path / "test_backlog.json"
        backlog_data = {
            "stories": [
                {
                    "story_id": "STORY-001",
                    "user_story": "As a user, I need feature X",
                    "acceptance_criteria": ["AC1", "AC2", "AC3"],
                    "priority": "P0",
                    "story_points": 3,
                }
            ]
        }
        backlog_file.write_text(json.dumps(backlog_data))

        manager = TaskQueueManager(temp_queue)
        tasks = manager.parse_backlog(str(backlog_file))

        # Should create 3 tasks per story (research, writing, editing)
        assert len(tasks) == 3
        assert tasks[0]["task_id"] == "STORY-001-1"
        assert tasks[0]["phase"] == "research"
        assert tasks[1]["task_id"] == "STORY-001-2"
        assert tasks[1]["phase"] == "writing"
        assert tasks[1]["status"] == "blocked"  # Depends on task 1

    def test_assign_to_agent(self, temp_queue):
        """Test agent assignment"""
        manager = TaskQueueManager(temp_queue)

        task = {"phase": "research", "task_id": "TEST-1"}
        agent = manager.assign_to_agent(task)

        assert agent == "research_agent"
        assert task["assigned_to"] == "research_agent"
        assert task["status"] == "assigned"
        assert task["assigned_at"] is not None

    def test_update_queue_and_unblock(self, temp_queue):
        """Test task update and dependency unblocking"""
        manager = TaskQueueManager(temp_queue)

        # Create tasks with dependency
        manager.queue["tasks"] = [
            {"task_id": "TASK-1", "status": "in_progress"},
            {
                "task_id": "TASK-2",
                "status": "blocked",
                "depends_on": ["TASK-1"],
            },
        ]

        # Complete TASK-1
        manager.update_queue("TASK-1", "complete")

        # TASK-2 should be unblocked
        task2 = next(t for t in manager.queue["tasks"] if t["task_id"] == "TASK-2")
        assert task2["status"] == "pending"

    def test_get_next_task(self, temp_queue):
        """Test priority-based task selection"""
        manager = TaskQueueManager(temp_queue)

        manager.queue["tasks"] = [
            {"task_id": "LOW", "status": "pending", "priority": "P2"},
            {"task_id": "HIGH", "status": "pending", "priority": "P0"},
            {"task_id": "MED", "status": "pending", "priority": "P1"},
        ]

        next_task = manager.get_next_task()
        assert next_task["task_id"] == "HIGH"  # P0 is highest priority


class TestAgentStatusMonitor:
    """Test agent status monitoring"""

    @pytest.fixture
    def temp_status(self, tmp_path):
        """Temporary status file"""
        status_file = tmp_path / "test_status.json"
        return str(status_file)

    def test_initialization(self, temp_status):
        """Test monitor initialization"""
        monitor = AgentStatusMonitor(temp_status)
        assert monitor.status_file == Path(temp_status)
        assert monitor.status["agents"] == []

    def test_poll_status_updates(self, temp_status):
        """Test polling for completed tasks"""
        monitor = AgentStatusMonitor(temp_status)

        # Add completed agent
        monitor.status["agents"] = [
            {
                "agent_id": "writer_agent",
                "status": "complete",
                "current_task": "TASK-1",
            }
        ]
        monitor.save()

        # Poll should return completed tasks
        completed = monitor.poll_status_updates()

        assert len(completed) == 1
        assert completed[0]["agent_id"] == "writer_agent"
        assert completed[0]["processed"] is True

    def test_determine_next_agent(self, temp_status):
        """Test workflow routing"""
        monitor = AgentStatusMonitor(temp_status)

        assert monitor.determine_next_agent("research_agent") == "writer_agent"
        assert monitor.determine_next_agent("writer_agent") == "editor_agent"
        assert monitor.determine_next_agent("editor_agent") == "graphics_agent"
        assert monitor.determine_next_agent("qe_agent") is None  # End of workflow

    def test_detect_blockers(self, temp_status):
        """Test blocked agent detection"""
        monitor = AgentStatusMonitor(temp_status)

        monitor.status["agents"] = [
            {"agent_id": "agent1", "status": "in_progress"},
            {"agent_id": "agent2", "status": "blocked"},
            {"agent_id": "agent3", "status": "complete"},
        ]

        blocked = monitor.detect_blockers()
        assert len(blocked) == 1
        assert blocked[0]["agent_id"] == "agent2"


class TestQualityGateValidator:
    """Test quality gate validation"""

    def test_validate_dor_complete(self):
        """Test DoR validation with complete story"""
        validator = QualityGateValidator()

        story = {
            "user_story": "As a user, I need X",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "quality_requirements": {"performance": "<2s"},
            "story_points": 3,
        }

        passed, missing = validator.validate_dor(story)
        assert passed is True
        assert len(missing) == 0

    def test_validate_dor_incomplete(self):
        """Test DoR validation with incomplete story"""
        validator = QualityGateValidator()

        story = {
            "user_story": "As a user, I need X",
            # Missing acceptance_criteria, quality_requirements, story_points
        }

        passed, missing = validator.validate_dor(story)
        assert passed is False
        assert "acceptance_criteria" in missing
        assert "quality_requirements" in missing
        assert "story_points" in missing

    def test_validate_dod_success(self):
        """Test DoD validation with passing deliverable"""
        validator = QualityGateValidator()

        deliverable = {
            "self_validation": {"passed": True},
            "output": {"path": "output/article.md"},
            "acceptance_criteria_results": [
                {"ac": "AC1", "passed": True},
                {"ac": "AC2", "passed": True},
            ],
        }

        passed, issues = validator.validate_dod(deliverable)
        assert passed is True
        assert len(issues) == 0

    def test_validate_dod_failure(self):
        """Test DoD validation with failing deliverable"""
        validator = QualityGateValidator()

        deliverable = {
            "self_validation": {"passed": False},
            "output": {},
            "acceptance_criteria_results": [
                {"ac": "AC1", "passed": False},
            ],
        }

        passed, issues = validator.validate_dod(deliverable)
        assert passed is False
        assert "Self-validation failed" in issues

    def test_make_gate_decision(self):
        """Test gate decision logic"""
        validator = QualityGateValidator()

        # No issues → APPROVE
        decision = validator.make_gate_decision((True, []))
        assert decision == "APPROVE"

        # 1-2 issues → ESCALATE
        decision = validator.make_gate_decision((False, ["issue1", "issue2"]))
        assert decision == "ESCALATE"

        # >2 issues → REJECT
        decision = validator.make_gate_decision((False, ["issue1", "issue2", "issue3"]))
        assert decision == "REJECT"


class TestEscalationManager:
    """Test escalation management"""

    @pytest.fixture
    def temp_escalations(self, tmp_path):
        """Temporary escalations file"""
        esc_file = tmp_path / "test_escalations.json"
        return str(esc_file)

    def test_initialization(self, temp_escalations):
        """Test escalation manager initialization"""
        manager = EscalationManager(temp_escalations)
        assert manager.escalations_file == Path(temp_escalations)
        assert manager.escalations["pending_escalations"] == []

    def test_create_escalation(self, temp_escalations):
        """Test escalation creation"""
        manager = EscalationManager(temp_escalations)

        esc_id = manager.create_escalation(
            story_id="STORY-001",
            escalation_type="ambiguous_ac",
            question="Define measurable criteria for 'high quality'?",
            context={"story": "..."},
            recommendation="Suggest: 95%+ Visual QA pass rate",
        )

        assert esc_id == "ESC-1"
        assert len(manager.escalations["pending_escalations"]) == 1

        esc = manager.escalations["pending_escalations"][0]
        assert esc["story_id"] == "STORY-001"
        assert esc["resolved"] is False

    def test_get_unresolved(self, temp_escalations):
        """Test unresolved escalation retrieval"""
        manager = EscalationManager(temp_escalations)

        manager.escalations["pending_escalations"] = [
            {"escalation_id": "ESC-1", "resolved": False},
            {"escalation_id": "ESC-2", "resolved": True},
        ]

        unresolved = manager.get_unresolved()
        assert len(unresolved) == 1
        assert unresolved[0]["escalation_id"] == "ESC-1"


class TestScrumMasterAgent:
    """Test full SM Agent integration"""

    @pytest.fixture
    def mock_components(self, tmp_path):
        """Mock all component managers"""
        queue_file = tmp_path / "queue.json"
        status_file = tmp_path / "status.json"
        esc_file = tmp_path / "escalations.json"
        backlog_file = tmp_path / "backlog.json"

        # Create minimal backlog
        backlog_data = {
            "stories": [
                {
                    "story_id": "STORY-TEST",
                    "user_story": "Test story",
                    "acceptance_criteria": ["AC1", "AC2", "AC3"],
                    "quality_requirements": {"test": "value"},
                    "story_points": 2,
                }
            ]
        }
        backlog_file.write_text(json.dumps(backlog_data))

        return {
            "queue_file": str(queue_file),
            "status_file": str(status_file),
            "esc_file": str(esc_file),
            "backlog_file": str(backlog_file),
        }

    @patch("sm_agent.TaskQueueManager")
    @patch("sm_agent.AgentStatusMonitor")
    @patch("sm_agent.EscalationManager")
    def test_agent_initialization(self, mock_esc, mock_monitor, mock_queue):
        """Test SM Agent initialization"""
        agent = ScrumMasterAgent()

        assert agent.queue is not None
        assert agent.monitor is not None
        assert agent.validator is not None
        assert agent.escalation_mgr is not None


def run_tests():
    """Run all tests"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
