#!/usr/bin/env python3
"""
Metrics Dashboard

Visualizes quality trends and agent performance over time.
Combines quality_history.json and agent_metrics.json for comprehensive reporting.

Usage:
    python3 scripts/metrics_dashboard.py
    python3 scripts/metrics_dashboard.py --agent research_agent
    python3 scripts/metrics_dashboard.py --trend
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class MetricsDashboard:
    """Visualize quality and agent performance metrics"""
    
    def __init__(self):
        self.skills_dir = Path(__file__).parent.parent / "skills"
        self.quality_history = self._load_json("quality_history.json")
        self.agent_metrics = self._load_json("agent_metrics.json")
    
    def _load_json(self, filename):
        """Load JSON file from skills directory"""
        file_path = self.skills_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def show_quality_trend(self):
        """Display quality score trend over time"""
        if not self.quality_history or not self.quality_history.get("runs"):
            print("❌ No quality history found. Run calculate_quality_score.py first.")
            return
        
        runs = self.quality_history["runs"]
        print("\n" + "="*70)
        print("QUALITY SCORE TREND")
        print("="*70 + "\n")
        
        # Show last 10 runs
        recent_runs = runs[-10:]
        
        print(f"Total Runs: {len(runs)}")
        print(f"Trend: {self.quality_history.get('trend', 'N/A')}\n")
        
        print("Recent History:")
        print("-" * 70)
        
        for i, run in enumerate(recent_runs, 1):
            timestamp = run["timestamp"][:10]  # Just date
            score = run["quality_score"]
            grade = run["grade"]
            
            # Visual bar
            bar_length = int(score / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            
            print(f"  {timestamp} │ {score:3d}/100 ({grade:2s}) │ {bar}")
        
        print("-" * 70)
        
        # Component breakdown for latest run
        latest = runs[-1]
        components = latest["components"]
        
        print("\nLatest Run Breakdown:")
        print(f"  Test Coverage:   {components['test_coverage']:5.1f}% (40% weight)")
        print(f"  Test Pass Rate:  {components['test_pass_rate']:5.1f}% (30% weight)")
        print(f"  Documentation:   {components['documentation']:5.1f}% (20% weight)")
        print(f"  Code Style:      {components['code_style']:5.1f}% (10% weight)")
        
        print("\n" + "="*70 + "\n")
    
    def show_agent_performance(self, agent_name=None):
        """Display agent performance metrics"""
        if not self.agent_metrics:
            print("❌ No agent metrics found. Run with agent tracking enabled.")
            return
        
        agents = self.agent_metrics["summary"]["agents"]
        
        if agent_name:
            # Show specific agent
            if agent_name not in agents or not agents[agent_name]:
                print(f"❌ No data for agent: {agent_name}")
                return
            
            self._show_agent_detail(agent_name, agents[agent_name])
        else:
            # Show all agents
            print("\n" + "="*70)
            print("AGENT PERFORMANCE SUMMARY")
            print("="*70 + "\n")
            
            print(f"Total Runs: {self.agent_metrics['summary']['total_runs']}\n")
            
            for agent, stats in agents.items():
                if not stats:
                    continue
                
                print(f"\n{agent.replace('_', ' ').title()}:")
                print("-" * 70)
                
                if agent == "research_agent":
                    print(f"  Average Verification Rate: {stats.get('avg_verification_rate', 0)}%")
                    print(f"  Trend: {stats.get('trend', 'N/A')}")
                
                elif agent == "writer_agent":
                    print(f"  Clean Draft Rate: {stats.get('clean_draft_rate', 0)}%")
                    print(f"  Average Regenerations: {stats.get('avg_regenerations', 0)}")
                
                elif agent == "editor_agent":
                    print(f"  Average Gate Pass Rate: {stats.get('avg_gate_pass_rate', 0)}%")
                    print(f"  Trend: {stats.get('trend', 'N/A')}")
                
                elif agent == "graphics_agent":
                    print(f"  Average Visual QA Pass Rate: {stats.get('avg_qa_pass_rate', 0)}%")
                    print(f"  Average Violations: {stats.get('avg_violations', 0)}")
            
            print("\n" + "="*70 + "\n")
    
    def _show_agent_detail(self, agent_name, stats):
        """Show detailed metrics for specific agent"""
        print("\n" + "="*70)
        print(f"{agent_name.replace('_', ' ').title().upper()} - DETAILED METRICS")
        print("="*70 + "\n")
        
        runs = [run for run in self.agent_metrics["runs"] 
                if agent_name in run["agents"]]
        
        print(f"Total Runs: {len(runs)}\n")
        
        # Show recent runs
        recent_runs = runs[-10:]
        print("Recent Performance:")
        print("-" * 70)
        
        for run in recent_runs:
            timestamp = run["timestamp"][:10]
            agent_data = run["agents"][agent_name]
            
            prediction = agent_data.get("prediction", "N/A")
            actual = agent_data.get("actual", "N/A")
            match = "✅" if "Pass" in actual else "❌"
            
            print(f"  {timestamp} │ {match} │ Predicted: {prediction}")
            print(f"             │   │ Actual:    {actual}")
        
        print("-" * 70)
        
        # Summary stats
        print("\nSummary Statistics:")
        for key, value in stats.items():
            if key == "total_runs":
                continue
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "="*70 + "\n")
    
    def show_prediction_accuracy(self):
        """Show prediction vs actual accuracy across all agents"""
        if not self.agent_metrics:
            print("❌ No agent metrics found.")
            return
        
        print("\n" + "="*70)
        print("PREDICTION vs ACTUAL ACCURACY")
        print("="*70 + "\n")
        
        runs = self.agent_metrics["runs"]
        
        agent_accuracy = {
            "research_agent": {"matches": 0, "total": 0},
            "writer_agent": {"matches": 0, "total": 0},
            "editor_agent": {"matches": 0, "total": 0},
            "graphics_agent": {"matches": 0, "total": 0}
        }
        
        for run in runs:
            for agent_name, agent_data in run["agents"].items():
                if agent_name in agent_accuracy:
                    agent_accuracy[agent_name]["total"] += 1
                    if "Pass" in agent_data.get("actual", ""):
                        agent_accuracy[agent_name]["matches"] += 1
        
        for agent_name, stats in agent_accuracy.items():
            if stats["total"] == 0:
                continue
            
            accuracy = (stats["matches"] / stats["total"]) * 100
            bar_length = int(accuracy / 2)
            bar = "█" * bar_length
            
            print(f"{agent_name.replace('_', ' ').title():20s} │ {accuracy:5.1f}% │ {bar}")
            print(f"{'':20s} │ {stats['matches']}/{stats['total']} predictions correct")
            print()
        
        print("="*70 + "\n")
    
    def show_full_dashboard(self):
        """Show comprehensive dashboard"""
        self.show_quality_trend()
        self.show_agent_performance()
        self.show_prediction_accuracy()
    
    def export_report(self, output_file="metrics_report.md"):
        """Export dashboard to markdown file"""
        report = []
        report.append("# Metrics Dashboard Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Quality Trend
        if self.quality_history:
            report.append("## Quality Score Trend\n")
            runs = self.quality_history["runs"]
            report.append(f"- Total Runs: {len(runs)}")
            report.append(f"- Current Score: {runs[-1]['quality_score']}/100")
            report.append(f"- Trend: {self.quality_history.get('trend', 'N/A')}\n")
        
        # Agent Performance
        if self.agent_metrics:
            report.append("## Agent Performance\n")
            for agent, stats in self.agent_metrics["summary"]["agents"].items():
                if not stats:
                    continue
                report.append(f"\n### {agent.replace('_', ' ').title()}")
                for key, value in stats.items():
                    if key != "total_runs":
                        report.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        # Write to file
        output_path = Path(__file__).parent.parent / output_file
        with open(output_path, 'w') as f:
            f.write("\n".join(report))
        
        print(f"\n✅ Report exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="View quality and agent performance metrics")
    parser.add_argument('--trend', action='store_true', help='Show quality score trend')
    parser.add_argument('--agent', type=str, help='Show specific agent metrics')
    parser.add_argument('--accuracy', action='store_true', help='Show prediction accuracy')
    parser.add_argument('--export', type=str, help='Export report to file')
    
    args = parser.parse_args()
    
    dashboard = MetricsDashboard()
    
    if args.trend:
        dashboard.show_quality_trend()
    elif args.agent:
        dashboard.show_agent_performance(args.agent)
    elif args.accuracy:
        dashboard.show_prediction_accuracy()
    elif args.export:
        dashboard.export_report(args.export)
    else:
        # Show full dashboard
        dashboard.show_full_dashboard()


if __name__ == "__main__":
    main()
