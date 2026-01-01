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
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class DefectTracker:
    """Tracks bugs and quality metrics"""
    
    SEVERITIES = ["critical", "high", "medium", "low"]
    STAGES = ["development", "staging", "production"]
    
    def __init__(self, tracker_file: str = None):
        if tracker_file is None:
            script_dir = Path(__file__).parent.parent
            tracker_file = script_dir / "skills" / "defect_tracker.json"
        
        self.tracker_file = Path(tracker_file)
        self.tracker = self._load_tracker()
    
    def _load_tracker(self) -> Dict[str, Any]:
        """Load existing tracker or create new"""
        if self.tracker_file.exists():
            with open(self.tracker_file, 'r') as f:
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
                    "by_severity": {s: 0 for s in self.SEVERITIES},
                    "by_stage": {s: 0 for s in self.STAGES}
                }
            }
    
    def log_bug(self, bug_id: str, severity: str, discovered_in: str,
                description: str, github_issue: int = None,
                component: str = None) -> None:
        """Log a new bug"""
        if severity not in self.SEVERITIES:
            raise ValueError(f"Severity must be one of {self.SEVERITIES}")
        if discovered_in not in self.STAGES:
            raise ValueError(f"Stage must be one of {self.STAGES}")
        
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
            "status": "open",
            "fixed_date": None,
            "fix_commit": None,
            "is_production_escape": discovered_in == "production"
        }
        
        self.tracker["bugs"].append(bug)
        self._update_summary()
        print(f"✅ Logged {severity} bug: {bug_id}")
    
    def fix_bug(self, bug_id: str, fix_commit: str, notes: str = None) -> None:
        """Mark a bug as fixed"""
        bug = next((b for b in self.tracker["bugs"] if b["id"] == bug_id), None)
        if not bug:
            print(f"❌ Bug {bug_id} not found")
            return
        
        bug["status"] = "fixed"
        bug["fixed_date"] = datetime.now().isoformat()
        bug["fix_commit"] = fix_commit
        if notes:
            bug["fix_notes"] = notes
        
        self._update_summary()
        print(f"✅ Marked bug {bug_id} as fixed (commit {fix_commit})")
    
    def _update_summary(self) -> None:
        """Recalculate summary metrics"""
        total = len(self.tracker["bugs"])
        fixed = sum(1 for b in self.tracker["bugs"] if b["status"] == "fixed")
        production = sum(1 for b in self.tracker["bugs"] if b["is_production_escape"])
        
        # Calculate defect escape rate (production bugs / total bugs)
        escape_rate = (production / total * 100) if total > 0 else 0
        
        # Count by severity
        by_severity = {s: 0 for s in self.SEVERITIES}
        for bug in self.tracker["bugs"]:
            by_severity[bug["severity"]] += 1
        
        # Count by stage
        by_stage = {s: 0 for s in self.STAGES}
        for bug in self.tracker["bugs"]:
            by_stage[bug["discovered_in"]] += 1
        
        self.tracker["summary"] = {
            "total_bugs": total,
            "fixed_bugs": fixed,
            "production_bugs": production,
            "defect_escape_rate": round(escape_rate, 1),
            "by_severity": by_severity,
            "by_stage": by_stage,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        return self.tracker["summary"]
    
    def get_production_bugs(self) -> List[Dict[str, Any]]:
        """Get all bugs found in production"""
        return [b for b in self.tracker["bugs"] if b["is_production_escape"]]
    
    def get_open_bugs(self) -> List[Dict[str, Any]]:
        """Get all open bugs"""
        return [b for b in self.tracker["bugs"] if b["status"] == "open"]
    
    def save(self) -> None:
        """Persist tracker to disk"""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracker_file, 'w') as f:
            json.dump(self.tracker, f, indent=2)
        print(f"💾 Saved defect tracker to {self.tracker_file}")
    
    def generate_report(self) -> str:
        """Generate human-readable defect report"""
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
        
        report.extend([
            "",
            "## By Discovery Stage",
        ])
        
        for stage, count in metrics["by_stage"].items():
            if count > 0:
                report.append(f"- **{stage.title()}**: {count}")
        
        if production_bugs:
            report.extend([
                "",
                "## 🚨 Production Escapes",
            ])
            for bug in production_bugs:
                status = "✅ Fixed" if bug["status"] == "fixed" else "🔴 Open"
                report.append(f"- **{bug['id']}** ({status}): {bug['description']}")
                if bug.get("github_issue"):
                    report.append(f"  - GitHub Issue: #{bug['github_issue']}")
        
        if open_bugs:
            report.extend([
                "",
                "## 🔴 Open Bugs",
            ])
            for bug in open_bugs:
                escape = " [PRODUCTION]" if bug["is_production_escape"] else ""
                report.append(f"- **{bug['id']}** ({bug['severity']}){escape}: {bug['description']}")
        
        return "\n".join(report)


def main():
    """Example usage and testing"""
    tracker = DefectTracker()
    
    # Log known bugs from recent issues
    tracker.log_bug(
        bug_id="BUG-015",
        severity="high",
        discovered_in="production",
        description="Missing category tag on article page",
        github_issue=15,
        component="jekyll_layout"
    )
    
    tracker.log_bug(
        bug_id="BUG-016",
        severity="critical",
        discovered_in="development",
        description="Charts generated but never embedded in articles",
        github_issue=16,
        component="writer_agent"
    )
    
    tracker.log_bug(
        bug_id="BUG-017",
        severity="medium",
        discovered_in="production",
        description="Duplicate chart display (featured image + embed)",
        github_issue=17,
        component="writer_agent"
    )
    
    tracker.log_bug(
        bug_id="BUG-020",
        severity="critical",
        discovered_in="development",
        description="GitHub integration broken - issues not auto-closing",
        github_issue=20,
        component="git_workflow"
    )
    
    # Mark fixed bugs
    tracker.fix_bug("BUG-015", "5d97545", "Added category tag to post.html layout")
    tracker.fix_bug("BUG-016", "469f402", "Enhanced Writer Agent prompt + Publication Validator")
    tracker.fix_bug("BUG-017", "5509dec", "Removed image: field from front matter")
    
    # Save and report
    tracker.save()
    
    print("\n" + "="*60)
    print(tracker.generate_report())
    print("="*60)


if __name__ == "__main__":
    main()
