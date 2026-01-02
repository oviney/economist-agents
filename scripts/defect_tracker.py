#!/usr/bin/env python3
"""
Defect Tracking & Bug Metrics

Tracks bugs discovered, fixed, and leaked to production.
Provides quality metrics and defect escape rate analysis.

Usage:
    from defect_tracker import DefectTracker

    tracker = DefectTracker()

    # Log a bug found in development
    tracker.log_bug(
        bug_id="BUG-001",
        severity="critical",
        discovered_in="development",
        description="Charts not embedded in articles"
    )

    # Mark bug as fixed
    tracker.fix_bug("BUG-001", fix_commit="abc1234")

    # Log production bug
    tracker.log_bug(
        bug_id="BUG-002",
        severity="high",
        discovered_in="production",
        description="Missing category tags"
    )

    # Get metrics
    metrics = tracker.get_metrics()
    print(f"Defect Escape Rate: {metrics['defect_escape_rate']}%")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class DefectTracker:
    """Tracks bugs and quality metrics"""

    SEVERITIES = ["critical", "high", "medium", "low"]
    STAGES = ["development", "staging", "production"]

    # Root cause categories
    ROOT_CAUSES = [
        "validation_gap",  # Missing validation/check
        "prompt_engineering",  # LLM prompt issue
        "integration_error",  # Component integration problem
        "requirements_gap",  # Unclear/missing requirements
        "code_logic",  # Logic bug in code
        "configuration",  # Config/env issue
        "data_issue",  # Bad/unexpected data
        "race_condition",  # Timing/concurrency bug
        "dependency",  # Third-party/external issue
        "other",  # Uncategorized
    ]

    # Test types that should have caught the bug
    TEST_TYPES = [
        "unit_test",  # Unit test gap
        "integration_test",  # Integration test gap
        "e2e_test",  # End-to-end test gap
        "manual_test",  # Manual testing gap
        "visual_qa",  # Visual QA gap
        "none",  # No test could catch it
    ]

    # Prevention strategies
    PREVENTION_STRATEGIES = [
        "new_validation",  # Added new validation
        "enhanced_prompt",  # Improved LLM prompt
        "new_test",  # Added test coverage
        "process_change",  # Changed workflow/process
        "documentation",  # Improved docs
        "code_review",  # Enhanced review process
        "automation",  # Automated prevention
    ]

    def __init__(self, tracker_file: str = None):
        if tracker_file is None:
            script_dir = Path(__file__).parent.parent
            tracker_file = script_dir / "skills" / "defect_tracker.json"

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
                "bugs": [],
                "summary": {
                    "total_bugs": 0,
                    "fixed_bugs": 0,
                    "production_bugs": 0,
                    "defect_escape_rate": 0.0,
                    "by_severity": dict.fromkeys(self.SEVERITIES, 0),
                    "by_stage": dict.fromkeys(self.STAGES, 0),
                },
            }

    def log_bug(
        self,
        bug_id: str,
        severity: str,
        discovered_in: str,
        description: str,
        github_issue: int = None,
        component: str = None,
        responsible_agent: str = None,
        root_cause: str = None,
        root_cause_notes: str = None,
        introduced_in_commit: str = None,
        introduced_date: str = None,
        missed_by_test_type: str = None,
        test_gap_description: str = None,
        prevention_strategy: list[str] = None,
        prevention_actions: list[str] = None,
    ) -> None:
        """Log a new bug with optional RCA and prevention data

        Args:
            responsible_agent: Which agent produced buggy output
                             (research_agent, writer_agent, graphics_agent, editor_agent)
        """
        if severity not in self.SEVERITIES:
            raise ValueError(f"Severity must be one of {self.SEVERITIES}")
        if discovered_in not in self.STAGES:
            raise ValueError(f"Stage must be one of {self.STAGES}")
        if root_cause and root_cause not in self.ROOT_CAUSES:
            raise ValueError(f"Root cause must be one of {self.ROOT_CAUSES}")
        if missed_by_test_type and missed_by_test_type not in self.TEST_TYPES:
            raise ValueError(f"Test type must be one of {self.TEST_TYPES}")

        # Check if bug already exists
        existing = next((b for b in self.tracker["bugs"] if b["id"] == bug_id), None)
        if existing:
            print(f"⚠️  Bug {bug_id} already exists")
            return

        bug = {
            "id": bug_id,
            "severity": severity,
            "discovered_in": discovered_in,
            "discovered_date": datetime.now().isoformat(),
            "description": description,
            "github_issue": github_issue,
            "component": component,
            "responsible_agent": responsible_agent,  # NEW: Track which agent caused bug
            "status": "open",
            "fixed_date": None,
            "fix_commit": None,
            "is_production_escape": discovered_in == "production",
            # Root Cause Analysis
            "root_cause": root_cause,
            "root_cause_notes": root_cause_notes,
            "introduced_in_commit": introduced_in_commit,
            "introduced_date": introduced_date,
            "time_to_detect_days": None,  # Calculated if introduced_date provided
            "time_to_resolve_days": None,  # Calculated when fixed
            # Test Gap Analysis
            "missed_by_test_type": missed_by_test_type,
            "test_gap_description": test_gap_description,
            "prevention_test_added": False,
            "prevention_test_file": None,
            # Prevention Tracking
            "prevention_strategy": prevention_strategy or [],
            "prevention_actions": prevention_actions or [],
        }

        # Calculate time to detect if introduced_date provided
        if introduced_date:
            from datetime import datetime as dt

            intro = dt.fromisoformat(introduced_date)
            discovered = dt.fromisoformat(bug["discovered_date"])
            bug["time_to_detect_days"] = (discovered - intro).days

        self.tracker["bugs"].append(bug)
        self._update_summary()
        print(f"✅ Logged {severity} bug: {bug_id}")

    def fix_bug(
        self,
        bug_id: str,
        fix_commit: str,
        notes: str = None,
        prevention_test_added: bool = False,
        prevention_test_file: str = None,
    ) -> None:
        """Mark a bug as fixed and calculate resolution time"""
        bug = next((b for b in self.tracker["bugs"] if b["id"] == bug_id), None)
        if not bug:
            print(f"❌ Bug {bug_id} not found")
            return

        bug["status"] = "fixed"
        bug["fixed_date"] = datetime.now().isoformat()
        bug["fix_commit"] = fix_commit
        if notes:
            bug["fix_notes"] = notes

        # Update prevention test info
        if prevention_test_added:
            bug["prevention_test_added"] = True
            if prevention_test_file:
                bug["prevention_test_file"] = prevention_test_file

        # Calculate time to resolve
        from datetime import datetime as dt

        discovered = dt.fromisoformat(bug["discovered_date"])
        fixed = dt.fromisoformat(bug["fixed_date"])
        bug["time_to_resolve_days"] = (fixed - discovered).days

        self._update_summary()
        print(f"✅ Marked bug {bug_id} as fixed (commit {fix_commit})")

    def update_bug_rca(
        self,
        bug_id: str,
        root_cause: str = None,
        root_cause_notes: str = None,
        introduced_in_commit: str = None,
        introduced_date: str = None,
        missed_by_test_type: str = None,
        test_gap_description: str = None,
        prevention_strategy: list[str] = None,
        prevention_actions: list[str] = None,
    ) -> None:
        """Update RCA data for existing bug (for backfilling)"""
        bug = next((b for b in self.tracker["bugs"] if b["id"] == bug_id), None)
        if not bug:
            print(f"❌ Bug {bug_id} not found")
            return

        # Validate enums
        if root_cause and root_cause not in self.ROOT_CAUSES:
            raise ValueError(f"Root cause must be one of {self.ROOT_CAUSES}")
        if missed_by_test_type and missed_by_test_type not in self.TEST_TYPES:
            raise ValueError(f"Test type must be one of {self.TEST_TYPES}")

        # Update fields if provided
        if root_cause:
            bug["root_cause"] = root_cause
        if root_cause_notes:
            bug["root_cause_notes"] = root_cause_notes
        if introduced_in_commit:
            bug["introduced_in_commit"] = introduced_in_commit
        if introduced_date:
            bug["introduced_date"] = introduced_date
            # Recalculate TTD
            from datetime import datetime as dt

            intro = dt.fromisoformat(introduced_date)
            discovered = dt.fromisoformat(bug["discovered_date"])
            bug["time_to_detect_days"] = (discovered - intro).days
        if missed_by_test_type:
            bug["missed_by_test_type"] = missed_by_test_type
        if test_gap_description:
            bug["test_gap_description"] = test_gap_description
        if prevention_strategy:
            bug["prevention_strategy"] = prevention_strategy
        if prevention_actions:
            bug["prevention_actions"] = prevention_actions

        self._update_summary()
        print(f"✅ Updated RCA data for {bug_id}")

    def _update_summary(self) -> None:
        """Recalculate summary metrics including RCA insights"""
        total = len(self.tracker["bugs"])
        fixed = sum(1 for b in self.tracker["bugs"] if b["status"] == "fixed")
        production = sum(1 for b in self.tracker["bugs"] if b["is_production_escape"])

        # Calculate defect escape rate (production bugs / total bugs)
        escape_rate = (production / total * 100) if total > 0 else 0

        # Count by severity
        by_severity = dict.fromkeys(self.SEVERITIES, 0)
        for bug in self.tracker["bugs"]:
            by_severity[bug["severity"]] += 1

        # Count by stage
        by_stage = dict.fromkeys(self.STAGES, 0)
        for bug in self.tracker["bugs"]:
            by_stage[bug["discovered_in"]] += 1

        # NEW: Root cause distribution
        root_causes = {}
        for bug in self.tracker["bugs"]:
            rc = bug.get("root_cause")
            if rc:
                root_causes[rc] = root_causes.get(rc, 0) + 1

        # NEW: Test gap analysis
        test_gaps = {}
        for bug in self.tracker["bugs"]:
            tt = bug.get("missed_by_test_type")
            if tt:
                test_gaps[tt] = test_gaps.get(tt, 0) + 1

        # NEW: Time metrics (for fixed bugs with RCA data)
        bugs_with_ttd = [
            b for b in self.tracker["bugs"] if b.get("time_to_detect_days") is not None
        ]
        bugs_with_ttr = [
            b for b in self.tracker["bugs"] if b.get("time_to_resolve_days") is not None
        ]

        avg_ttd = (
            (sum(b["time_to_detect_days"] for b in bugs_with_ttd) / len(bugs_with_ttd))
            if bugs_with_ttd
            else None
        )
        avg_ttr = (
            (sum(b["time_to_resolve_days"] for b in bugs_with_ttr) / len(bugs_with_ttr))
            if bugs_with_ttr
            else None
        )

        # NEW: Critical bug TTD
        critical_ttd = [
            b["time_to_detect_days"]
            for b in bugs_with_ttd
            if b["severity"] == "critical"
        ]
        avg_critical_ttd = (
            (sum(critical_ttd) / len(critical_ttd)) if critical_ttd else None
        )

        # NEW: Agent-specific defect distribution
        agent_defects = {}
        for bug in self.tracker["bugs"]:
            agent = bug.get("responsible_agent")
            if agent:
                agent_defects[agent] = agent_defects.get(agent, 0) + 1

        self.tracker["summary"] = {
            "total_bugs": total,
            "fixed_bugs": fixed,
            "production_bugs": production,
            "defect_escape_rate": round(escape_rate, 1),
            "by_severity": by_severity,
            "by_stage": by_stage,
            "root_cause_distribution": root_causes,
            "test_gap_distribution": test_gaps,
            "agent_defect_distribution": agent_defects,
            "avg_time_to_detect_days": round(avg_ttd, 1) if avg_ttd else None,
            "avg_time_to_resolve_days": round(avg_ttr, 1) if avg_ttr else None,
            "avg_critical_ttd_days": round(avg_critical_ttd, 1)
            if avg_critical_ttd
            else None,
            "last_updated": datetime.now().isoformat(),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics summary"""
        return self.tracker["summary"]

    def get_production_bugs(self) -> list[dict[str, Any]]:
        """Get all bugs found in production"""
        return [b for b in self.tracker["bugs"] if b["is_production_escape"]]

    def get_open_bugs(self) -> list[dict[str, Any]]:
        """Get all open bugs"""
        return [b for b in self.tracker["bugs"] if b["status"] == "open"]

    def get_bugs_by_agent(self, agent_name: str) -> list[dict[str, Any]]:
        """Get all bugs attributed to a specific agent"""
        return [
            b for b in self.tracker["bugs"] if b.get("responsible_agent") == agent_name
        ]

    def get_agent_defect_rate(self, agent_name: str) -> float:
        """Calculate defect rate for specific agent (bugs per run)"""
        agent_bugs = len(self.get_bugs_by_agent(agent_name))
        # Note: This requires agent metrics to calculate actual rate
        # For now, just return bug count
        return agent_bugs

    def save(self) -> None:
        """Persist tracker to disk"""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracker_file, "w") as f:
            json.dump(self.tracker, f, indent=2)
        print(f"💾 Saved defect tracker to {self.tracker_file}")

    def generate_report(self) -> str:
        """Generate human-readable defect report with RCA insights"""
        metrics = self.get_metrics()
        production_bugs = self.get_production_bugs()
        open_bugs = self.get_open_bugs()

        report = [
            "# Defect Tracking Report",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary Metrics",
            f"- **Total Bugs**: {metrics['total_bugs']}",
            f"- **Fixed Bugs**: {metrics['fixed_bugs']}",
            f"- **Production Escapes**: {metrics['production_bugs']}",
            f"- **Defect Escape Rate**: {metrics['defect_escape_rate']}%",
            "",
            "## By Severity",
        ]

        for severity, count in metrics["by_severity"].items():
            if count > 0:
                report.append(f"- **{severity.title()}**: {count}")

        report.extend(
            [
                "",
                "## By Discovery Stage",
            ]
        )

        for stage, count in metrics["by_stage"].items():
            if count > 0:
                report.append(f"- **{stage.title()}**: {count}")

        # NEW: Root Cause Analysis
        if metrics.get("root_cause_distribution"):
            report.extend(
                [
                    "",
                    "## 🔍 Root Cause Analysis",
                ]
            )
            sorted_causes = sorted(
                metrics["root_cause_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for cause, count in sorted_causes:
                pct = (
                    (count / metrics["total_bugs"] * 100)
                    if metrics["total_bugs"] > 0
                    else 0
                )
                report.append(
                    f"- **{cause.replace('_', ' ').title()}**: {count} ({pct:.0f}%)"
                )

        # NEW: Test Gap Analysis
        if metrics.get("test_gap_distribution"):
            report.extend(
                [
                    "",
                    "## 🧪 Test Gap Analysis",
                ]
            )
            sorted_gaps = sorted(
                metrics["test_gap_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for gap, count in sorted_gaps:
                pct = (
                    (count / metrics["total_bugs"] * 100)
                    if metrics["total_bugs"] > 0
                    else 0
                )
                report.append(
                    f"- **{gap.replace('_', ' ').title()}**: {count} ({pct:.0f}%)"
                )

        # NEW: Time Metrics
        if metrics.get("avg_time_to_detect_days") is not None:
            report.extend(
                [
                    "",
                    "## ⏱️ Time Metrics",
                    f"- **Avg Time to Detect**: {metrics['avg_time_to_detect_days']} days",
                ]
            )
            if metrics.get("avg_critical_ttd_days") is not None:
                report.append(
                    f"- **Avg Critical Bug TTD**: {metrics['avg_critical_ttd_days']} days"
                )
            if metrics.get("avg_time_to_resolve_days") is not None:
                report.append(
                    f"- **Avg Time to Resolve**: {metrics['avg_time_to_resolve_days']} days"
                )

        if production_bugs:
            report.extend(
                [
                    "",
                    "## 🚨 Production Escapes",
                ]
            )
            for bug in production_bugs:
                status = "✅ Fixed" if bug["status"] == "fixed" else "🔴 Open"
                report.append(f"- **{bug['id']}** ({status}): {bug['description']}")
                if bug.get("github_issue"):
                    report.append(f"  - GitHub Issue: #{bug['github_issue']}")
                if bug.get("root_cause"):
                    report.append(
                        f"  - Root Cause: {bug['root_cause'].replace('_', ' ')}"
                    )
                if bug.get("time_to_detect_days") is not None:
                    report.append(
                        f"  - Time to Detect: {bug['time_to_detect_days']} days"
                    )

        if open_bugs:
            report.extend(
                [
                    "",
                    "## 🔴 Open Bugs",
                ]
            )
            for bug in open_bugs:
                escape = " [PRODUCTION]" if bug["is_production_escape"] else ""
                report.append(
                    f"- **{bug['id']}** ({bug['severity']}){escape}: {bug['description']}"
                )

        return "\n".join(report)


def main():
    """Example usage and backfill RCA data"""
    tracker = DefectTracker()

    # Log known bugs from recent issues (if not already logged)
    tracker.log_bug(
        bug_id="BUG-015",
        severity="high",
        discovered_in="production",
        description="Missing category tag on article page",
        github_issue=15,
        component="jekyll_layout",
    )

    tracker.log_bug(
        bug_id="BUG-016",
        severity="critical",
        discovered_in="development",
        description="Charts generated but never embedded in articles",
        github_issue=16,
        component="writer_agent",
    )

    tracker.log_bug(
        bug_id="BUG-017",
        severity="medium",
        discovered_in="production",
        description="Duplicate chart display (featured image + embed)",
        github_issue=17,
        component="writer_agent",
    )

    tracker.log_bug(
        bug_id="BUG-020",
        severity="critical",
        discovered_in="development",
        description="GitHub integration broken - issues not auto-closing",
        github_issue=20,
        component="git_workflow",
    )

    # Mark fixed bugs with TTR calculation
    tracker.fix_bug(
        "BUG-015",
        "5d97545",
        "Added category tag to post.html layout",
        prevention_test_added=True,
        prevention_test_file="scripts/blog_qa_agent.py",
    )
    tracker.fix_bug(
        "BUG-016",
        "469f402",
        "Enhanced Writer Agent prompt + Publication Validator",
        prevention_test_added=True,
        prevention_test_file="scripts/publication_validator.py",
    )
    tracker.fix_bug("BUG-017", "5509dec", "Removed image: field from front matter")

    # BACKFILL: Add RCA data for BUG-015
    tracker.update_bug_rca(
        "BUG-015",
        root_cause="validation_gap",
        root_cause_notes="Jekyll layout validation missing - no check for category tag display",
        introduced_in_commit="unknown",
        introduced_date="2025-12-30",  # Best estimate
        missed_by_test_type="visual_qa",
        test_gap_description="No visual validation of article page layout elements",
        prevention_strategy=["new_validation", "process_change"],
        prevention_actions=[
            "Added blog_qa_agent.py Jekyll layout validation",
            "Created pre-commit hook for blog structure checks",
        ],
    )

    # BACKFILL: Add RCA data for BUG-016
    tracker.update_bug_rca(
        "BUG-016",
        root_cause="prompt_engineering",
        root_cause_notes="Writer Agent prompt didn't explicitly require chart embedding. Graphics Agent created charts but Writer didn't reference them.",
        introduced_in_commit="a1b2c3d",  # Writer Agent initial commit
        introduced_date="2025-12-25",
        missed_by_test_type="integration_test",
        test_gap_description="No test verifying chart markdown exists in article body when chart_data provided",
        prevention_strategy=["enhanced_prompt", "new_validation"],
        prevention_actions=[
            "Enhanced Writer Agent prompt with explicit chart embedding requirements",
            "Added Publication Validator Check #7: Chart Embedding",
            "Added agent_reviewer.py validation for Writer Agent outputs",
        ],
    )

    # BACKFILL: Add RCA data for BUG-017
    tracker.update_bug_rca(
        "BUG-017",
        root_cause="requirements_gap",
        root_cause_notes="Unclear requirements: featured image vs embedded chart. Jekyll 'image:' field rendered as hero image, causing duplication.",
        introduced_in_commit="469f402",  # Same commit as BUG-016 fix
        introduced_date="2026-01-01",
        missed_by_test_type="visual_qa",
        test_gap_description="No visual regression test for article rendering with charts",
        prevention_strategy=["documentation", "process_change"],
        prevention_actions=[
            "Removed 'image:' field from YAML frontmatter specification",
            "Documented chart embedding pattern: use markdown only, not frontmatter",
            "Updated Writer Agent to use single chart embedding method",
        ],
    )

    # BUG-020 still open - partial RCA
    tracker.update_bug_rca(
        "BUG-020",
        root_cause="integration_error",
        root_cause_notes="GitHub close syntax in bullet list format not recognized. Sprint 4 regression.",
        introduced_in_commit="unknown",
        introduced_date="2025-12-28",
        missed_by_test_type="integration_test",
        test_gap_description="No test for GitHub webhook integration or commit message validation",
    )

    # Save and report
    tracker.save()

    print("\n" + "=" * 60)
    print(tracker.generate_report())
    print("=" * 60)


if __name__ == "__main__":
    main()
