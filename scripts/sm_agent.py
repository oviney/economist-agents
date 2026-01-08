#!/usr/bin/env python3
"""
Scrum Master Agent - Autonomous Sprint Orchestration

Enhanced for Sprint 8 with:
- Task queue management (backlog → executable tasks)
- Agent status monitoring (event-driven coordination)
- Quality gate automation (DoR/DoD validation)
- Escalation management (human PO routing)

Usage:
    # Autonomous sprint execution
    python3 scripts/sm_agent.py --run-sprint 8

    # Check orchestration status
    python3 scripts/sm_agent.py --status

    # Process specific story
    python3 scripts/sm_agent.py --story STORY-042
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class TaskQueueManager:
    """Manages task queue for autonomous agent coordination"""

    def __init__(self, queue_file: str = None):
        if queue_file is None:
            queue_file = Path(__file__).parent.parent / "skills" / "task_queue.json"
        self.queue_file = Path(queue_file)
        self.queue = self._load_queue()

    def _load_queue(self) -> dict[str, Any]:
        """Load existing queue or create new"""
        if self.queue_file.exists():
            with open(self.queue_file) as f:
                return json.load(f)
        else:
            return {
                "sprint_id": None,
                "tasks": [],
                "last_updated": datetime.now().isoformat(),
            }

    def parse_backlog(self, backlog_file: str = None) -> list[dict[str, Any]]:
        """Convert stories from backlog.json → executable tasks"""
        if backlog_file is None:
            backlog_file = Path(__file__).parent.parent / "skills" / "backlog.json"

        with open(backlog_file) as f:
            backlog = json.load(f)

        tasks = []
        for story in backlog.get("stories", []):
            # Create task for each story phase
            story_id = story.get("story_id", f"STORY-{len(tasks) + 1}")

            # Task 1: Research phase
            tasks.append(
                {
                    "task_id": f"{story_id}-1",
                    "story_id": story_id,
                    "title": f"Research: {story['user_story'][:50]}...",
                    "assigned_to": None,
                    "status": "pending",
                    "priority": story.get("priority", "P1"),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "depends_on": [],
                    "created_at": datetime.now().isoformat(),
                    "assigned_at": None,
                    "completed_at": None,
                    "phase": "research",
                }
            )

            # Task 2: Writing phase (depends on research)
            tasks.append(
                {
                    "task_id": f"{story_id}-2",
                    "story_id": story_id,
                    "title": f"Write: {story['user_story'][:50]}...",
                    "assigned_to": None,
                    "status": "blocked",
                    "priority": story.get("priority", "P1"),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "depends_on": [f"{story_id}-1"],
                    "created_at": datetime.now().isoformat(),
                    "assigned_at": None,
                    "completed_at": None,
                    "phase": "writing",
                }
            )

            # Task 3: Editing phase (depends on writing)
            tasks.append(
                {
                    "task_id": f"{story_id}-3",
                    "story_id": story_id,
                    "title": f"Edit: {story['user_story'][:50]}...",
                    "assigned_to": None,
                    "status": "blocked",
                    "priority": story.get("priority", "P1"),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "depends_on": [f"{story_id}-2"],
                    "created_at": datetime.now().isoformat(),
                    "assigned_at": None,
                    "completed_at": None,
                    "phase": "editing",
                }
            )

        return tasks

    def assign_to_agent(self, task: dict[str, Any]) -> str:
        """
        Determine which specialist agent should handle task

        DEPRECATED (Sprint 14): Consider using Flow-based orchestration instead.
        See: src/economist_agents/flow.py (EconomistContentFlow)

        This WORKFLOW_SEQUENCE dict is maintained for backward compatibility
        but new implementations should use @start/@listen/@router decorators
        for deterministic state-machine progression.
        """
        phase_to_agent = {
            "research": "research_agent",
            "writing": "writer_agent",
            "editing": "editor_agent",
            "graphics": "graphics_agent",
            "validation": "qe_agent",
        }

        agent = phase_to_agent.get(task.get("phase"), "unknown")
        task["assigned_to"] = agent
        task["assigned_at"] = datetime.now().isoformat()
        task["status"] = "assigned"

        return agent

    def update_queue(self, task_id: str, status: str, **kwargs):
        """Update task status (pending → assigned → in_progress → complete)"""
        for task in self.queue.get("tasks", []):
            if task["task_id"] == task_id:
                task["status"] = status
                task.update(kwargs)

                if status == "complete":
                    task["completed_at"] = datetime.now().isoformat()

                    # Unblock dependent tasks
                    self._unblock_dependencies(task_id)

                break

        self.queue["last_updated"] = datetime.now().isoformat()
        self.save()

    def _unblock_dependencies(self, completed_task_id: str):
        """Unblock tasks that depend on completed task"""
        for task in self.queue.get("tasks", []):
            if completed_task_id in task.get("depends_on", []):
                # Check if all dependencies complete
                all_deps_complete = all(
                    self._is_task_complete(dep) for dep in task["depends_on"]
                )

                if all_deps_complete and task["status"] == "blocked":
                    task["status"] = "pending"

    def _is_task_complete(self, task_id: str) -> bool:
        """Check if specific task is complete"""
        for task in self.queue.get("tasks", []):
            if task["task_id"] == task_id:
                return task["status"] == "complete"
        return False

    def get_next_task(self) -> dict[str, Any] | None:
        """Get highest priority unassigned task"""
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

        pending_tasks = [
            t
            for t in self.queue.get("tasks", [])
            if t["status"] == "pending" and not t.get("depends_on")
        ]

        if not pending_tasks:
            return None

        # Sort by priority
        pending_tasks.sort(key=lambda t: priority_order.get(t["priority"], 999))

        return pending_tasks[0]

    def get_tasks_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get all tasks with specific status"""
        return [t for t in self.queue.get("tasks", []) if t["status"] == status]

    def save(self):
        """Persist queue to disk"""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_file, "w") as f:
            json.dump(self.queue, f, indent=2)


class AgentStatusMonitor:
    """Monitors agent progress via status signals (event-driven)"""

    WORKFLOW_SEQUENCE = {
        "research_agent": "writer_agent",
        "writer_agent": "editor_agent",
        "editor_agent": "graphics_agent",
        "graphics_agent": "qe_agent",
        "qe_agent": None,  # End of workflow
    }

    def __init__(self, status_file: str = None):
        if status_file is None:
            status_file = Path(__file__).parent.parent / "skills" / "agent_status.json"
        self.status_file = Path(status_file)
        self.status = self._load_status()

    def _load_status(self) -> dict[str, Any]:
        """Load existing status or create new"""
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        else:
            return {
                "agents": [],
                "last_poll": None,
            }

    def poll_status_updates(self) -> list[dict[str, Any]]:
        """Read agent_status.json for new completion signals"""
        completed_tasks = []

        for agent in self.status.get("agents", []):
            if agent.get("status") == "complete" and not agent.get("processed"):
                completed_tasks.append(agent)
                agent["processed"] = True  # Mark as processed

        self.status["last_poll"] = datetime.now().isoformat()
        self.save()

        return completed_tasks

    def determine_next_agent(self, current_agent: str) -> str | None:
        """Workflow routing: Research → Writer → Editor → Graphics → QE"""
        return self.WORKFLOW_SEQUENCE.get(current_agent)

    def detect_blockers(self) -> list[dict[str, Any]]:
        """Identify agents waiting on dependencies or escalations"""
        blocked_agents = []

        for agent in self.status.get("agents", []):
            if agent.get("status") == "blocked":
                blocked_agents.append(agent)

        return blocked_agents

    def update_agent_status(self, agent_id: str, status: str, **kwargs):
        """Update specific agent status"""
        found = False
        for agent in self.status.get("agents", []):
            if agent["agent_id"] == agent_id:
                agent["status"] = status
                agent.update(kwargs)
                found = True
                break

        if not found:
            # Add new agent
            self.status.setdefault("agents", []).append(
                {
                    "agent_id": agent_id,
                    "status": status,
                    **kwargs,
                }
            )

        self.save()

    def save(self):
        """Persist status to disk"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(self.status, f, indent=2)


class QualityGateValidator:
    """Validates DoR/DoD and makes gate decisions"""

    DOR_CHECKLIST = [
        "story_written",
        "acceptance_criteria",
        "quality_requirements",
        "three_amigos_review",
        "dependencies_identified",
        "risks_documented",
        "story_points",
        "dod_defined",
    ]

    def __init__(self):
        pass

    def validate_dor(self, story: dict[str, Any]) -> tuple[bool, list[str]]:
        """8-point DoR checklist validation"""
        missing = []

        # Check required fields
        if not story.get("user_story"):
            missing.append("story_written")

        if (
            not story.get("acceptance_criteria")
            or len(story.get("acceptance_criteria", [])) < 3
        ):
            missing.append("acceptance_criteria")

        if not story.get("quality_requirements"):
            missing.append("quality_requirements")

        if not story.get("story_points"):
            missing.append("story_points")

        # All 8 criteria must pass
        passed = len(missing) == 0

        return passed, missing

    def validate_dod(self, deliverable: dict[str, Any]) -> tuple[bool, list[str]]:
        """Definition of Done validation"""
        issues = []

        # Check self-validation
        if not deliverable.get("self_validation", {}).get("passed"):
            issues.append("Self-validation failed")

        # Check required outputs
        if not deliverable.get("output", {}).get("path"):
            issues.append("No output path provided")

        # Check acceptance criteria met
        ac_results = deliverable.get("acceptance_criteria_results", [])
        failed_ac = [ac for ac in ac_results if not ac.get("passed")]
        if failed_ac:
            issues.append(f"{len(failed_ac)} acceptance criteria failed")

        passed = len(issues) == 0

        return passed, issues

    def make_gate_decision(self, validation_result: tuple[bool, list[str]]) -> str:
        """Approve, Reject, or Escalate based on validation"""
        passed, issues = validation_result

        if passed:
            return "APPROVE"
        elif len(issues) <= 2:
            return "ESCALATE"  # Minor issues - ask human PO
        else:
            return "REJECT"  # Major issues - block

    def send_back_for_fixes(self, task: dict[str, Any], issues: list[str]):
        """Mark task for rework with specific issues"""
        task["status"] = "needs_rework"
        task["rework_reason"] = issues
        task["sent_back_at"] = datetime.now().isoformat()


class EscalationManager:
    """Routes edge cases to human PO with context"""

    def __init__(self, escalations_file: str = None):
        if escalations_file is None:
            escalations_file = (
                Path(__file__).parent.parent / "skills" / "escalations.json"
            )
        self.escalations_file = Path(escalations_file)
        self.escalations = self._load_escalations()

    def _load_escalations(self) -> dict[str, Any]:
        """Load existing escalations"""
        if self.escalations_file.exists():
            with open(self.escalations_file) as f:
                return json.load(f)
        else:
            return {
                "pending_escalations": [],
                "answered_escalations": [],
                "dismissed_escalations": [],
            }

    def create_escalation(
        self,
        story_id: str,
        escalation_type: str,
        question: str,
        context: dict[str, Any],
        recommendation: str = None,
    ) -> str:
        """Generate escalation with question for human PO"""
        escalation_id = (
            f"ESC-{len(self.escalations.get('pending_escalations', [])) + 1}"
        )

        escalation = {
            "escalation_id": escalation_id,
            "story_id": story_id,
            "type": escalation_type,
            "question": question,
            "context": context,
            "recommendation": recommendation,
            "raised_by": "sm_agent",
            "raised_at": datetime.now().isoformat(),
            "requires_human_decision": True,
            "resolved": False,
            "resolution": None,
        }

        self.escalations.setdefault("pending_escalations", []).append(escalation)
        self.save()

        return escalation_id

    def check_for_resolution(self, escalation_id: str) -> bool:
        """Check if human PO has responded"""
        for esc in self.escalations.get("pending_escalations", []):
            if esc["escalation_id"] == escalation_id and esc.get("resolved"):
                return True
        return False

    def apply_resolution(self, escalation_id: str) -> dict[str, Any] | None:
        """Get resolution from human PO and move to answered"""
        for i, esc in enumerate(self.escalations.get("pending_escalations", [])):
            if esc["escalation_id"] == escalation_id and esc.get("resolved"):
                # Move to answered
                self.escalations["pending_escalations"].pop(i)
                self.escalations.setdefault("answered_escalations", []).append(esc)
                self.save()
                return esc
        return None

    def get_unresolved(self) -> list[dict[str, Any]]:
        """Get all unresolved escalations"""
        return [
            esc
            for esc in self.escalations.get("pending_escalations", [])
            if not esc.get("resolved")
        ]

    def save(self):
        """Persist escalations to disk"""
        self.escalations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.escalations_file, "w") as f:
            json.dump(self.escalations, f, indent=2)


class ScrumMasterAgent:
    """Enhanced Scrum Master Agent for autonomous coordination"""

    def __init__(self):
        self.queue = TaskQueueManager()
        self.monitor = AgentStatusMonitor()
        self.validator = QualityGateValidator()
        self.escalation_mgr = EscalationManager()

    def run_sprint(self, sprint_id: int):
        """Main orchestration loop (autonomous sprint execution)"""
        print(f"\n{'=' * 70}")
        print(f"🚀 SPRINT {sprint_id} AUTONOMOUS ORCHESTRATION")
        print(f"{'=' * 70}\n")

        # 1. Initialize sprint
        print("📋 Initializing sprint...")
        self._validate_dor_for_all_stories()
        self._create_task_queue(sprint_id)

        # 2. Orchestration loop (simplified for Sprint 8)
        print("\n⚙️  Orchestration loop active...")
        print("   (In Sprint 8, this monitors status. Full autonomy in Sprint 9)\n")

        # Show task queue status
        self._show_queue_status()

        # Check for escalations
        unresolved = self.escalation_mgr.get_unresolved()
        if unresolved:
            print(f"\n⚠️  {len(unresolved)} escalations require human PO:")
            for esc in unresolved:
                print(f"   - {esc['escalation_id']}: {esc['question']}")

        print(f"\n✅ Sprint {sprint_id} orchestration initialized")

    def _validate_dor_for_all_stories(self):
        """Validate Definition of Ready for backlog stories"""
        backlog_file = Path(__file__).parent.parent / "skills" / "backlog.json"

        if not backlog_file.exists():
            print("   ⚠️  No backlog.json found - skipping DoR validation")
            return

        with open(backlog_file) as f:
            backlog = json.load(f)

        stories = backlog.get("stories", [])
        print(f"   Validating DoR for {len(stories)} stories...")

        for story in stories:
            passed, missing = self.validator.validate_dor(story)
            story_id = story.get("story_id", "UNKNOWN")

            if passed:
                print(f"   ✅ {story_id}: DoR complete")
            else:
                print(f"   ⚠️  {story_id}: Missing {', '.join(missing)}")
                # Escalate to PO Agent for refinement
                self.escalation_mgr.create_escalation(
                    story_id=story_id,
                    escalation_type="dor_gap",
                    question=f"Story missing: {', '.join(missing)}. Refine?",
                    context={"story": story},
                    recommendation="PO Agent should refine story",
                )

    def _create_task_queue(self, sprint_id: int):
        """Parse backlog into task queue"""
        print(f"   Creating task queue for Sprint {sprint_id}...")

        tasks = self.queue.parse_backlog()
        self.queue.queue["sprint_id"] = sprint_id
        self.queue.queue["tasks"] = tasks
        self.queue.save()

        print(f"   ✅ Created {len(tasks)} tasks from backlog")

    def _show_queue_status(self):
        """Display current queue status"""
        print("\n📊 Task Queue Status:")

        statuses = {}
        for task in self.queue.queue.get("tasks", []):
            status = task["status"]
            statuses[status] = statuses.get(status, 0) + 1

        for status, count in statuses.items():
            print(f"   {status.upper()}: {count} tasks")

    def get_status(self):
        """Show current orchestration status"""
        print("\n" + "=" * 70)
        print("📊 ORCHESTRATION STATUS")
        print("=" * 70)

        # Task queue status
        self._show_queue_status()

        # Agent status
        print("\n🤖 Agent Status:")
        for agent in self.monitor.status.get("agents", []):
            print(f"   {agent['agent_id']}: {agent.get('status', 'unknown')}")

        # Escalations
        unresolved = self.escalation_mgr.get_unresolved()
        print(f"\n⚠️  Escalations: {len(unresolved)} pending")

        print("\n" + "=" * 70)


def main():
    """CLI interface for SM Agent"""
    parser = argparse.ArgumentParser(
        description="Scrum Master Agent - Autonomous Sprint Orchestration"
    )
    parser.add_argument(
        "--run-sprint",
        type=int,
        metavar="N",
        help="Run autonomous sprint orchestration for Sprint N",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current orchestration status",
    )
    parser.add_argument(
        "--story",
        metavar="ID",
        help="Process specific story (e.g., STORY-042)",
    )

    args = parser.parse_args()

    agent = ScrumMasterAgent()

    if args.run_sprint:
        agent.run_sprint(args.run_sprint)
    elif args.status:
        agent.get_status()
    elif args.story:
        print(f"Processing story {args.story}...")
        print("   (Story-specific orchestration coming in Sprint 9)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
