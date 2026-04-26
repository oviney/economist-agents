"""Tests for the continuous burn-down coordinator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.continuous_burndown import ContinuousBurndownCoordinator


def _write(path: Path, payload: dict) -> None:
    """Write JSON helper."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_collects_open_sources_and_blockers(tmp_path: Path) -> None:
    """Coordinator should merge backlog sources and escalations."""
    repo_root = tmp_path
    _write(
        repo_root / "data/skills_state/sprint_tracker.json",
        {
            "current_sprint": 15,
            "sprints": {
                "sprint_15": {
                    "stories": [
                        {
                            "id": 1,
                            "name": "Open sprint story",
                            "priority": "P0",
                            "status": "in_progress",
                        },
                        {
                            "id": 2,
                            "name": "Done story",
                            "priority": "P1",
                            "status": "complete",
                        },
                    ]
                }
            },
        },
    )
    _write(
        repo_root / "data/skills_state/backlog.json",
        {
            "stories": [
                {
                    "id": "STORY-1",
                    "request": "Backlog item",
                    "priority": "P2",
                    "status": "backlog",
                },
                {
                    "id": "STORY-2",
                    "request": "Blocked item",
                    "priority": "P1",
                    "status": "blocked",
                },
            ]
        },
    )
    _write(
        repo_root / "data/skills_state/task_queue.json",
        {
            "tasks": [
                {
                    "task_id": "TASK-1",
                    "title": "Queued task",
                    "priority": "P1",
                    "status": "assigned",
                }
            ]
        },
    )
    _write(
        repo_root / "data/skills_state/escalations.json",
        {
            "pending_escalations": [
                {
                    "escalation_id": "ESC-1",
                    "question": "Need human decision",
                    "recommendation": "Ask the PO",
                }
            ]
        },
    )
    (repo_root / "SPRINT.md").write_text(
        "**Active Sprint**: Sprint 15\n## Sprint 15: Test\n### Sprint Goal\nGoal\n"
    )
    (repo_root / "README.md").write_text("Sprint 15 IN PROGRESS\n")
    (repo_root / "docs").mkdir(exist_ok=True)
    (repo_root / "docs/CHANGELOG.md").write_text("No entries\n")

    coordinator = ContinuousBurndownCoordinator(repo_root=repo_root, runtime="codex")
    report = coordinator.collect_once(include_github=False)

    actionable_titles = {item["title"] for item in report["actionable"]}
    blocker_titles = {item["title"] for item in report["blockers"]}

    assert "Open sprint story" in actionable_titles
    assert any("Backlog item" in title for title in actionable_titles)
    assert "Queued task" in actionable_titles
    assert "Need human decision" in blocker_titles


def test_collect_once_returns_blocked_when_no_active_sprint(tmp_path: Path) -> None:
    """Missing sprint metadata should become a hard blocker."""
    repo_root = tmp_path
    _write(
        repo_root / "data/skills_state/sprint_tracker.json",
        {"current_sprint": None, "sprints": {}},
    )
    _write(repo_root / "data/skills_state/backlog.json", {"stories": []})
    _write(repo_root / "data/skills_state/task_queue.json", {"tasks": []})
    _write(
        repo_root / "data/skills_state/escalations.json", {"pending_escalations": []}
    )
    (repo_root / "SPRINT.md").write_text("# Empty sprint file\n")
    (repo_root / "README.md").write_text("README\n")
    (repo_root / "docs").mkdir(exist_ok=True)
    (repo_root / "docs/CHANGELOG.md").write_text("CHANGELOG\n")

    coordinator = ContinuousBurndownCoordinator(repo_root=repo_root, runtime="codex")
    report = coordinator.collect_once(include_github=False)

    blocker_ids = {item["id"] for item in report["blockers"]}
    assert "validator-no-active-sprint" in blocker_ids
