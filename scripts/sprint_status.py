#!/usr/bin/env python3
"""
Sprint Status Report Generator

Provides comprehensive sprint status at any time during the sprint.
Answers: "Where are we in the sprint right now?"

Usage:
    python3 scripts/sprint_status.py
    python3 scripts/sprint_status.py --sprint 9
    python3 scripts/sprint_status.py --detailed
    python3 scripts/sprint_status.py --export-markdown

Features:
    - Current sprint progress and metrics
    - Story status breakdown
    - Velocity tracking
    - Risk assessment
    - Next steps recommendations
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SprintStatusReporter:
    """Generates comprehensive sprint status reports"""

    def __init__(self, tracker_file: str = None):
        if tracker_file is None:
            script_dir = Path(__file__).parent.parent
            tracker_file = script_dir / "skills" / "sprint_tracker.json"

        self.tracker_file = Path(tracker_file)
        self.tracker = self._load_tracker()
        self.current_sprint_num = self.tracker.get("current_sprint", 9)
        self.current_sprint = self._get_sprint_data()

    def _load_tracker(self) -> dict[str, Any]:
        """Load sprint tracker data"""
        if self.tracker_file.exists():
            with open(self.tracker_file) as f:
                return json.load(f)
        else:
            return {}

    def _get_sprint_data(self) -> dict[str, Any]:
        """Get current sprint data"""
        sprint_key = f"sprint_{self.current_sprint_num}"
        sprints = self.tracker.get("sprints", {})
        
        # Try both locations (sprints.sprint_N and sprint_N at root)
        if sprint_key in sprints:
            return sprints[sprint_key]
        elif sprint_key in self.tracker:
            return self.tracker[sprint_key]
        
        return {}

    def calculate_progress(self) -> dict[str, Any]:
        """Calculate sprint progress metrics"""
        stories = self.current_sprint.get("stories", [])
        
        total_points = sum(s.get("points", 0) for s in stories)
        completed_points = sum(
            s.get("points", 0) for s in stories 
            if s.get("status") == "complete"
        )
        
        completion_rate = (completed_points / total_points * 100) if total_points > 0 else 0
        
        # Calculate days elapsed
        start_date_str = self.current_sprint.get("start_date")
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            days_elapsed = (datetime.now() - start_date).days + 1
        else:
            days_elapsed = 0
        
        # Sprint is typically 7 days
        sprint_duration = 7
        expected_progress = (days_elapsed / sprint_duration * 100) if days_elapsed > 0 else 0
        
        return {
            "total_points": total_points,
            "completed_points": completed_points,
            "remaining_points": total_points - completed_points,
            "completion_rate": completion_rate,
            "days_elapsed": days_elapsed,
            "sprint_duration": sprint_duration,
            "expected_progress": expected_progress,
            "pace_variance": completion_rate - expected_progress,
            "velocity": completed_points / days_elapsed if days_elapsed > 0 else 0,
        }

    def get_story_breakdown(self) -> dict[str, list[dict]]:
        """Get stories grouped by status"""
        stories = self.current_sprint.get("stories", [])
        
        breakdown = {
            "complete": [],
            "in_progress": [],
            "ready": [],
            "not_started": [],
            "blocked": []
        }
        
        for story in stories:
            status = story.get("status", "not_started")
            if status in breakdown:
                breakdown[status].append(story)
        
        return breakdown

    def assess_risks(self, progress: dict) -> list[dict]:
        """Assess sprint risks based on metrics"""
        risks = []
        
        # Pace risk
        if progress["pace_variance"] < -10:
            risks.append({
                "level": "HIGH",
                "category": "Pace",
                "description": f"Behind pace by {abs(progress['pace_variance']):.1f}%",
                "mitigation": "Consider parallel execution or scope reduction"
            })
        elif progress["pace_variance"] < -5:
            risks.append({
                "level": "MEDIUM",
                "category": "Pace",
                "description": f"Slightly behind pace ({abs(progress['pace_variance']):.1f}%)",
                "mitigation": "Monitor closely, increase velocity if possible"
            })
        
        # Completion risk
        days_remaining = progress["sprint_duration"] - progress["days_elapsed"]
        points_per_day_needed = progress["remaining_points"] / days_remaining if days_remaining > 0 else 0
        
        if points_per_day_needed > progress["velocity"] * 1.5:
            risks.append({
                "level": "HIGH",
                "category": "Completion",
                "description": f"Need {points_per_day_needed:.1f} pts/day, current velocity is {progress['velocity']:.1f}",
                "mitigation": "Defer low-priority stories or extend sprint"
            })
        
        return risks

    def generate_recommendations(self, progress: dict, breakdown: dict) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check for ready stories
        ready_stories = breakdown.get("ready", [])
        if ready_stories:
            ready_points = sum(s.get("points", 0) for s in ready_stories)
            recommendations.append(
                f"✅ {len(ready_stories)} stories READY to start ({ready_points} points) - begin immediately"
            )
        
        # Check for blocked stories
        blocked_stories = breakdown.get("blocked", [])
        if blocked_stories:
            recommendations.append(
                f"⚠️ {len(blocked_stories)} stories BLOCKED - prioritize unblocking"
            )
        
        # Velocity recommendations
        if progress["pace_variance"] > 10:
            recommendations.append(
                "🎯 Ahead of pace - maintain quality, consider stretch goals"
            )
        elif progress["pace_variance"] < -10:
            recommendations.append(
                "⚡ Behind pace - enable parallel execution or reduce scope"
            )
        
        # Completion forecast
        if progress["completion_rate"] >= 80:
            recommendations.append(
                "🏁 Sprint on track for completion - focus on quality"
            )
        elif progress["completion_rate"] >= 50:
            recommendations.append(
                "📊 Mid-sprint - continue steady pace"
            )
        else:
            recommendations.append(
                "🔥 Early in sprint - establish momentum"
            )
        
        return recommendations

    def print_status_report(self, detailed: bool = False) -> None:
        """Print formatted status report to console"""
        progress = self.calculate_progress()
        breakdown = self.get_story_breakdown()
        risks = self.assess_risks(progress)
        recommendations = self.generate_recommendations(progress, breakdown)
        
        print("\n" + "=" * 80)
        print(f"SPRINT {self.current_sprint_num} STATUS REPORT")
        print("=" * 80)
        
        # Executive Summary
        print("\n📊 EXECUTIVE SUMMARY")
        print("-" * 80)
        status_emoji = "🟢" if progress["pace_variance"] >= 0 else "🟡" if progress["pace_variance"] > -10 else "🔴"
        print(f"Status: {status_emoji} {'ON TRACK' if progress['pace_variance'] >= -5 else 'CAUTION' if progress['pace_variance'] >= -15 else 'AT RISK'}")
        print(f"Progress: {progress['completed_points']}/{progress['total_points']} points ({progress['completion_rate']:.1f}%)")
        print(f"Day: {progress['days_elapsed']}/{progress['sprint_duration']}")
        print(f"Velocity: {progress['velocity']:.1f} points/day")
        print(f"Pace: {'+' if progress['pace_variance'] >= 0 else ''}{progress['pace_variance']:.1f}% vs expected")
        
        # Story Breakdown
        print("\n📋 STORY BREAKDOWN")
        print("-" * 80)
        
        for status, stories in breakdown.items():
            if stories:
                points = sum(s.get("points", 0) for s in stories)
                status_emoji = {
                    "complete": "✅",
                    "in_progress": "🔄",
                    "ready": "🟢",
                    "not_started": "⏸️",
                    "blocked": "🚫"
                }
                emoji = status_emoji.get(status, "❓")
                print(f"{emoji} {status.upper()}: {len(stories)} stories ({points} points)")
                
                if detailed:
                    for story in stories:
                        print(f"   - Story {story.get('id')}: {story.get('name')} ({story.get('points')} pts)")
                        if story.get("notes"):
                            print(f"     Notes: {story.get('notes')[:80]}...")
        
        # Risks
        if risks:
            print("\n⚠️  RISKS")
            print("-" * 80)
            for risk in risks:
                print(f"{risk['level']:6} | {risk['category']:12} | {risk['description']}")
                print(f"       Mitigation: {risk['mitigation']}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 80)
        for rec in recommendations:
            print(f"  {rec}")
        
        # Objectives
        objectives = self.current_sprint.get("objectives", [])
        if objectives:
            print("\n🎯 SPRINT OBJECTIVES")
            print("-" * 80)
            for obj in objectives:
                print(f"  • {obj}")
        
        print("\n" + "=" * 80)
        print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

    def export_markdown(self, output_file: str = None) -> str:
        """Export status report as markdown"""
        if output_file is None:
            output_file = f"SPRINT_{self.current_sprint_num}_STATUS.md"
        
        progress = self.calculate_progress()
        breakdown = self.get_story_breakdown()
        risks = self.assess_risks(progress)
        recommendations = self.generate_recommendations(progress, breakdown)
        
        md = []
        md.append(f"# Sprint {self.current_sprint_num} Status Report")
        md.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"**Day**: {progress['days_elapsed']}/{progress['sprint_duration']}")
        md.append("")
        
        # Executive Summary
        md.append("## Executive Summary")
        status = "ON TRACK" if progress['pace_variance'] >= -5 else "CAUTION" if progress['pace_variance'] >= -15 else "AT RISK"
        md.append(f"- **Status**: {status}")
        md.append(f"- **Progress**: {progress['completed_points']}/{progress['total_points']} points ({progress['completion_rate']:.1f}%)")
        md.append(f"- **Velocity**: {progress['velocity']:.1f} points/day")
        md.append(f"- **Pace Variance**: {progress['pace_variance']:+.1f}%")
        md.append("")
        
        # Story Breakdown
        md.append("## Story Breakdown")
        for status, stories in breakdown.items():
            if stories:
                points = sum(s.get("points", 0) for s in stories)
                md.append(f"### {status.replace('_', ' ').title()} ({len(stories)} stories, {points} points)")
                for story in stories:
                    md.append(f"- **Story {story.get('id')}**: {story.get('name')} ({story.get('points')} pts)")
                md.append("")
        
        # Risks
        if risks:
            md.append("## Risks")
            for risk in risks:
                md.append(f"- **{risk['level']}** ({risk['category']}): {risk['description']}")
                md.append(f"  - Mitigation: {risk['mitigation']}")
            md.append("")
        
        # Recommendations
        md.append("## Recommendations")
        for rec in recommendations:
            md.append(f"- {rec}")
        md.append("")
        
        markdown_content = "\n".join(md)
        
        # Write to file
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            f.write(markdown_content)
        
        print(f"✅ Markdown report exported to: {output_path}")
        return str(output_path)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate Sprint Status Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic status report
  python3 scripts/sprint_status.py
  
  # Detailed story breakdown
  python3 scripts/sprint_status.py --detailed
  
  # Export to markdown
  python3 scripts/sprint_status.py --export-markdown
  
  # Specific sprint
  python3 scripts/sprint_status.py --sprint 9 --detailed
        """
    )
    
    parser.add_argument("--sprint", type=int, help="Sprint number (default: current)")
    parser.add_argument("--detailed", action="store_true", help="Show detailed story information")
    parser.add_argument("--export-markdown", action="store_true", help="Export report as markdown")
    parser.add_argument("--output", type=str, help="Output file for markdown export")
    
    args = parser.parse_args()
    
    reporter = SprintStatusReporter()
    
    if args.sprint:
        reporter.current_sprint_num = args.sprint
        reporter.current_sprint = reporter._get_sprint_data()
    
    if args.export_markdown:
        reporter.export_markdown(args.output)
    
    reporter.print_status_report(detailed=args.detailed)


if __name__ == "__main__":
    main()
