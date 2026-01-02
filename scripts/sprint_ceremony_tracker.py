#!/usr/bin/env python3
"""
Sprint Ceremony Tracker

Enforces Definition of Ready and tracks sprint ceremony completion.
Prevents DoR violations by blocking sprint planning without proper ceremonies.

Usage:
    # End current sprint
    python3 sprint_ceremony_tracker.py --end-sprint 6

    # Check if can start new sprint
    python3 sprint_ceremony_tracker.py --can-start 7

    # Complete retrospective (generates template)
    python3 sprint_ceremony_tracker.py --retrospective 6

    # Complete backlog refinement
    python3 sprint_ceremony_tracker.py --refine-backlog 7

    # Validate Definition of Ready
    python3 sprint_ceremony_tracker.py --validate-dor 7

    # Generate ceremony status report
    python3 sprint_ceremony_tracker.py --report
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SprintCeremonyTracker:
    """Tracks sprint ceremony completion and enforces Definition of Ready"""

    # 8-point Definition of Ready checklist (from SCRUM_MASTER_PROTOCOL.md)
    DOR_CHECKLIST = [
        "story_written",  # Story exists with clear goal
        "acceptance_criteria",  # AC defined in Given/When/Then
        "three_amigos_review",  # Dev, QA, Product perspectives
        "dependencies_identified",  # Upstream/downstream dependencies
        "risks_documented",  # Technical, time, dependency risks
        "story_points_estimated",  # Fibonacci estimate
        "definition_of_done",  # DoD criteria defined
        "user_approval",  # Product Owner approval obtained
    ]

    def __init__(self, tracker_file: str = None):
        if tracker_file is None:
            script_dir = Path(__file__).parent.parent
            tracker_file = script_dir / "skills" / "sprint_tracker.json"

        self.tracker_file = Path(tracker_file)
        self.tracker = self._load_tracker()

    def _load_tracker(self) -> dict[str, Any]:
        """Load existing tracker or create new"""
        if self.tracker_file.exists():
            with open(self.tracker_file) as f:
                return json.load(f)
        else:
            return {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "current_sprint": None,
                "sprints": {},
            }

    def end_sprint(self, sprint_number: int) -> None:
        """Mark sprint as complete"""
        sprint_key = f"sprint_{sprint_number}"

        if sprint_key not in self.tracker["sprints"]:
            self.tracker["sprints"][sprint_key] = {}

        self.tracker["sprints"][sprint_key].update(
            {
                "status": "complete",
                "end_date": datetime.now().isoformat(),
                "retrospective_done": False,
                "backlog_refined": False,
                "next_sprint_dor_met": False,
            }
        )

        self.tracker["current_sprint"] = sprint_number
        self.save()

        print(f"✅ Sprint {sprint_number} marked complete")
        print(
            f"⚠️  Next: Complete retrospective before starting Sprint {sprint_number + 1}"
        )

    def can_start_sprint(self, sprint_number: int) -> bool:
        """Check if sprint can start (previous sprint ceremonies complete)"""
        if sprint_number == 1:
            return True  # First sprint, no previous ceremonies needed

        prev_sprint_key = f"sprint_{sprint_number - 1}"

        if prev_sprint_key not in self.tracker["sprints"]:
            print(f"❌ BLOCKED: Sprint {sprint_number - 1} not found in tracker")
            print(
                f"   Run: python3 sprint_ceremony_tracker.py --end-sprint {sprint_number - 1}"
            )
            return False

        prev_sprint = self.tracker["sprints"][prev_sprint_key]

        # Check required ceremonies
        if not prev_sprint.get("retrospective_done", False):
            print(f"❌ BLOCKED: Sprint {sprint_number - 1} retrospective not complete")
            print(
                f"   Run: python3 sprint_ceremony_tracker.py --retrospective {sprint_number - 1}"
            )
            return False

        if not prev_sprint.get("backlog_refined", False):
            print(f"❌ BLOCKED: Sprint {sprint_number} backlog not refined")
            print(
                f"   Run: python3 sprint_ceremony_tracker.py --refine-backlog {sprint_number}"
            )
            return False

        if not prev_sprint.get("next_sprint_dor_met", False):
            print(f"❌ BLOCKED: Sprint {sprint_number} Definition of Ready not met")
            print(
                f"   Run: python3 sprint_ceremony_tracker.py --validate-dor {sprint_number}"
            )
            return False

        print(f"✅ Sprint {sprint_number} ready to start - all ceremonies complete")
        return True

    def complete_retrospective(self, sprint_number: int) -> str:
        """Complete retrospective and generate template"""
        sprint_key = f"sprint_{sprint_number}"

        if sprint_key not in self.tracker["sprints"]:
            print(f"❌ Sprint {sprint_number} not found. Run --end-sprint first.")
            return None

        # Generate retrospective template
        template_path = self._generate_retrospective_template(sprint_number)

        # Update tracker
        self.tracker["sprints"][sprint_key]["retrospective_done"] = True
        self.tracker["sprints"][sprint_key]["retrospective_date"] = (
            datetime.now().isoformat()
        )
        self.save()

        print(f"✅ Sprint {sprint_number} retrospective complete")
        print(f"📝 Template generated: {template_path}")
        print(f"   Edit template, then run: --refine-backlog {sprint_number + 1}")

        return str(template_path)

    def _generate_retrospective_template(self, sprint_number: int) -> Path:
        """Generate retrospective markdown template"""
        docs_dir = self.tracker_file.parent.parent / "docs"
        docs_dir.mkdir(exist_ok=True)  # Ensure docs directory exists
        template_path = docs_dir / f"RETROSPECTIVE_S{sprint_number}.md"

        template = f"""# Sprint {sprint_number} Retrospective

**Date**: {datetime.now().strftime("%Y-%m-%d")}  
**Participants**: Team

---

## What Went Well ✅

1. [Add positive outcome]
2. [Add positive outcome]
3. [Add positive outcome]

**Metrics**:
- Velocity: [X points planned / Y points delivered]
- Quality: [Defects found, prevention effectiveness]
- Process: [DoD compliance, ceremony adherence]

---

## What Needs Improvement ⚠️

1. [Add improvement area]
2. [Add improvement area]
3. [Add improvement area]

**Root Causes**:
- [Why did this happen?]
- [What patterns emerged?]

---

## Action Items 🎯

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| [Action item] | Team | Sprint {sprint_number + 1} | P0 |
| [Action item] | Team | Sprint {sprint_number + 1} | P1 |

---

## Insights for Next Sprint 💡

**Continue**:
- [Practice to keep]

**Stop**:
- [Practice to discontinue]

**Start**:
- [New practice to try]

---

## Sprint {sprint_number} Summary

**Completed Stories**: [List story IDs or titles]

**Blocked/Incomplete**: [List any incomplete work]

**Technical Debt**: [Any debt incurred or paid down]

**Learning**: [Key lessons from this sprint]
"""

        with open(template_path, "w") as f:
            f.write(template)

        return template_path

    def complete_backlog_refinement(self, sprint_number: int) -> str:
        """Complete backlog refinement and generate story templates"""
        sprint_key = f"sprint_{sprint_number}"

        if sprint_key not in self.tracker["sprints"]:
            self.tracker["sprints"][sprint_key] = {}

        # Generate story template
        template_path = self._generate_story_template(sprint_number)

        # Update tracker
        self.tracker["sprints"][sprint_key]["backlog_refined"] = True
        self.tracker["sprints"][sprint_key]["refinement_date"] = (
            datetime.now().isoformat()
        )
        self.save()

        print(f"✅ Sprint {sprint_number} backlog refinement complete")
        print(f"📝 Story template generated: {template_path}")
        print(f"   Fill in stories, then run: --validate-dor {sprint_number}")

        return str(template_path)

    def _generate_story_template(self, sprint_number: int) -> Path:
        """Generate story template for sprint planning"""
        docs_dir = self.tracker_file.parent.parent / "docs"
        docs_dir.mkdir(exist_ok=True)  # Ensure docs directory exists
        template_path = docs_dir / f"SPRINT_{sprint_number}_BACKLOG.md"

        template = f"""# Sprint {sprint_number} Backlog

**Sprint Goal**: [Clear, concise sprint objective]

**Capacity**: [Team capacity in story points or hours]

---

## Story 1: [Story Title]

**User Story**:
As a [role], I need [capability], so that [benefit].

**Acceptance Criteria**:
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]

**Definition of Done**:
- [ ] Code complete with unit tests
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Product Owner acceptance

**Story Points**: [Fibonacci: 1, 2, 3, 5, 8, 13]

**Priority**: P0 | P1 | P2

**Dependencies**: [Upstream/downstream dependencies]

**Risks**:
- [Technical risk and mitigation]
- [Time risk and mitigation]

**Task Breakdown**:
1. [Task 1] (X min)
2. [Task 2] (Y min)
3. [Task 3] (Z min)

Total Estimate: [Sum of tasks]

---

## Story 2: [Story Title]

[Repeat structure above]

---

## Three Amigos Review Notes

**Developer Perspective**:
- [Implementation concerns, technical approach]

**QA Perspective**:
- [Testing strategy, test cases needed]

**Product Perspective**:
- [Business value, user impact, acceptance criteria]

**Decisions Made**:
- [Key decisions from review]

**Open Questions**:
- [Questions needing resolution before sprint start]

---

## Sprint {sprint_number} Scope

**In Scope**:
- Story 1: [Title] (X points)
- Story 2: [Title] (Y points)

**Total Points**: [Sum]

**Out of Scope** (moved to backlog):
- [Story title] (reason)

**Stretch Goals** (if time permits):
- [Story title]
"""

        with open(template_path, "w") as f:
            f.write(template)

        return template_path

    def validate_dor(self, sprint_number: int) -> tuple[bool, list[str]]:
        """Validate Definition of Ready for sprint"""
        sprint_key = f"sprint_{sprint_number}"

        if sprint_key not in self.tracker["sprints"]:
            return False, [f"Sprint {sprint_number} not in tracker"]

        sprint = self.tracker["sprints"][sprint_key]

        # Check 8-point DoR checklist
        missing = []

        if not sprint.get("backlog_refined", False):
            missing.append("Backlog not refined")

        # Check if stories exist (backlog file created)
        docs_dir = self.tracker_file.parent.parent / "docs"
        backlog_file = docs_dir / f"SPRINT_{sprint_number}_BACKLOG.md"

        if not backlog_file.exists():
            missing.append("Stories not written (SPRINT_X_BACKLOG.md missing)")
        else:
            # Read backlog and check for placeholders
            with open(backlog_file) as f:
                content = f.read()

            if "[Story Title]" in content:
                missing.append("Stories have placeholder titles")
            if "[role]" in content or "[capability]" in content:
                missing.append("User stories not filled in")
            if "[ ] Given [context]" in content:
                missing.append("Acceptance criteria not defined")
            if "[Fibonacci:" in content:
                missing.append("Story points not estimated")
            if "[Task 1]" in content:
                missing.append("Task breakdown not complete")

        # Check if previous sprint retro done
        if sprint_number > 1:
            prev_sprint_key = f"sprint_{sprint_number - 1}"
            if prev_sprint_key in self.tracker["sprints"]:
                if not self.tracker["sprints"][prev_sprint_key].get(
                    "retrospective_done", False
                ):
                    missing.append(
                        f"Sprint {sprint_number - 1} retrospective not complete"
                    )

        # If all checks pass
        if not missing:
            sprint["next_sprint_dor_met"] = True
            # Update previous sprint if exists
            if sprint_number > 1:
                prev_sprint_key = f"sprint_{sprint_number - 1}"
                if prev_sprint_key in self.tracker["sprints"]:
                    self.tracker["sprints"][prev_sprint_key]["next_sprint_dor_met"] = (
                        True
                    )
            self.save()
            return True, []

        return False, missing

    def generate_report(self) -> str:
        """Generate ceremony status report"""
        report = [
            "=" * 60,
            "SPRINT CEREMONY STATUS REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if not self.tracker.get("sprints"):
            report.append("No sprints tracked yet.")
            return "\n".join(report)

        current = self.tracker.get("current_sprint")
        if current:
            report.append(f"Current Sprint: {current}")
            report.append("")

        # List all sprints
        for sprint_key in sorted(
            self.tracker["sprints"].keys(), key=lambda x: int(x.split("_")[1])
        ):
            sprint_num = sprint_key.split("_")[1]
            sprint = self.tracker["sprints"][sprint_key]

            report.append(f"Sprint {sprint_num}")
            report.append("-" * 40)

            status = sprint.get("status", "unknown")
            report.append(f"  Status: {status}")

            if sprint.get("end_date"):
                report.append(f"  Ended: {sprint['end_date'][:10]}")

            # Ceremony status
            retro = sprint.get("retrospective_done", False)
            backlog = sprint.get("backlog_refined", False)
            dor = sprint.get("next_sprint_dor_met", False)

            report.append(f"  Retrospective: {'✅ Done' if retro else '❌ Not done'}")
            if sprint.get("retrospective_date"):
                report.append(f"    Completed: {sprint['retrospective_date'][:10]}")

            report.append(
                f"  Backlog Refined: {'✅ Done' if backlog else '❌ Not done'}"
            )
            if sprint.get("refinement_date"):
                report.append(f"    Completed: {sprint['refinement_date'][:10]}")

            report.append(f"  Next Sprint DoR: {'✅ Met' if dor else '❌ Not met'}")

            report.append("")

        # Next actions
        if current:
            report.append("NEXT ACTIONS")
            report.append("-" * 40)

            current_sprint = self.tracker["sprints"].get(f"sprint_{current}")
            if current_sprint:
                if not current_sprint.get("retrospective_done", False):
                    report.append(f"  1. Complete Sprint {current} retrospective")
                    report.append(
                        f"     Run: python3 sprint_ceremony_tracker.py --retrospective {current}"
                    )
                elif not current_sprint.get("backlog_refined", False):
                    report.append(f"  1. Refine Sprint {current + 1} backlog")
                    report.append(
                        f"     Run: python3 sprint_ceremony_tracker.py --refine-backlog {current + 1}"
                    )
                elif not current_sprint.get("next_sprint_dor_met", False):
                    report.append(
                        f"  1. Validate Sprint {current + 1} Definition of Ready"
                    )
                    report.append(
                        f"     Run: python3 sprint_ceremony_tracker.py --validate-dor {current + 1}"
                    )
                else:
                    report.append(
                        f"  ✅ All ceremonies complete - Sprint {current + 1} ready to start"
                    )

        report.append("=" * 60)

        return "\n".join(report)

    def save(self) -> None:
        """Persist tracker to disk"""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracker_file, "w") as f:
            json.dump(self.tracker, f, indent=2)


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sprint Ceremony Tracker - Enforce Definition of Ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # End sprint
  python3 sprint_ceremony_tracker.py --end-sprint 6
  
  # Check if can start new sprint
  python3 sprint_ceremony_tracker.py --can-start 7
  
  # Complete retrospective
  python3 sprint_ceremony_tracker.py --retrospective 6
  
  # Refine backlog
  python3 sprint_ceremony_tracker.py --refine-backlog 7
  
  # Validate DoR
  python3 sprint_ceremony_tracker.py --validate-dor 7
  
  # Status report
  python3 sprint_ceremony_tracker.py --report
        """,
    )

    parser.add_argument(
        "--end-sprint", type=int, metavar="N", help="Mark sprint N as complete"
    )
    parser.add_argument(
        "--can-start", type=int, metavar="N", help="Check if sprint N can start"
    )
    parser.add_argument(
        "--retrospective",
        type=int,
        metavar="N",
        help="Complete retrospective for sprint N",
    )
    parser.add_argument(
        "--refine-backlog",
        type=int,
        metavar="N",
        help="Complete backlog refinement for sprint N",
    )
    parser.add_argument(
        "--validate-dor",
        type=int,
        metavar="N",
        help="Validate Definition of Ready for sprint N",
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate ceremony status report"
    )
    parser.add_argument("--test", action="store_true", help="Run self-tests")

    args = parser.parse_args()

    if args.test:
        run_self_tests()
        return

    tracker = SprintCeremonyTracker()

    if args.end_sprint:
        tracker.end_sprint(args.end_sprint)

    elif args.can_start:
        can_start = tracker.can_start_sprint(args.can_start)
        exit(0 if can_start else 1)

    elif args.retrospective:
        tracker.complete_retrospective(args.retrospective)

    elif args.refine_backlog:
        tracker.complete_backlog_refinement(args.refine_backlog)

    elif args.validate_dor:
        is_valid, missing = tracker.validate_dor(args.validate_dor)

        if is_valid:
            print(f"✅ Sprint {args.validate_dor} Definition of Ready MET")
            print("   All 8 DoR criteria passed")
            print(f"   Sprint {args.validate_dor} ready to start")
        else:
            print(f"❌ Sprint {args.validate_dor} Definition of Ready NOT MET")
            print(f"   {len(missing)} criteria missing:\n")
            for item in missing:
                print(f"   • {item}")
            exit(1)

    elif args.report:
        print(tracker.generate_report())

    else:
        parser.print_help()


def run_self_tests():
    """Self-test the tracker"""
    import shutil
    import tempfile

    print("\n" + "=" * 60)
    print("SPRINT CEREMONY TRACKER - SELF-TESTS")
    print("=" * 60 + "\n")

    # Create temp directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    tracker_file = temp_dir / "sprint_tracker.json"

    try:
        # Test 1: End sprint and check blocking
        print("Test 1: Sprint end and blocking logic")
        print("-" * 40)

        tracker = SprintCeremonyTracker(str(tracker_file))
        tracker.end_sprint(6)

        # Should block Sprint 7 start
        can_start = tracker.can_start_sprint(7)
        if not can_start:
            print("✅ Test 1 PASSED - Sprint 7 blocked without ceremonies")
        else:
            print("❌ Test 1 FAILED - Sprint 7 should be blocked")

        print()

        # Test 2: Complete ceremonies and validate DoR
        print("Test 2: Ceremony completion and DoR validation")
        print("-" * 40)

        # Create docs dir for templates
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()

        # Mock the docs directory
        original_docs = tracker.tracker_file.parent.parent / "docs"
        tracker.tracker_file = tracker_file

        # Complete retrospective
        tracker.complete_retrospective(6)

        # Complete backlog refinement
        tracker.complete_backlog_refinement(7)

        # Check DoR (should fail - backlog has placeholders)
        is_valid, missing = tracker.validate_dor(7)
        if not is_valid and missing:
            print(f"✅ Test 2 PASSED - DoR validation caught {len(missing)} issues")
        else:
            print("❌ Test 2 FAILED - DoR should detect placeholder issues")

        print()

        # Test 3: Full ceremony flow
        print("Test 3: Full ceremony completion flow")
        print("-" * 40)

        # Manually mark DoR as met (simulating completed backlog)
        sprint_key = "sprint_7"
        tracker.tracker["sprints"][sprint_key]["next_sprint_dor_met"] = True
        tracker.tracker["sprints"]["sprint_6"]["next_sprint_dor_met"] = True
        tracker.save()

        # Now Sprint 7 should be able to start
        can_start = tracker.can_start_sprint(7)
        if can_start:
            print("✅ Test 3 PASSED - Sprint 7 can start after ceremonies")
        else:
            print("❌ Test 3 FAILED - Sprint 7 should be able to start")

        print()

        # Test 4: Report generation
        print("Test 4: Report generation")
        print("-" * 40)

        report = tracker.generate_report()
        if "Sprint 6" in report and "Retrospective" in report:
            print("✅ Test 4 PASSED - Report generated successfully")
        else:
            print("❌ Test 4 FAILED - Report missing expected content")

        print()
        print("=" * 60)
        print("SELF-TESTS COMPLETE")
        print("=" * 60)

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
