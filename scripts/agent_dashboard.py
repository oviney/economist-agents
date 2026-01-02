#!/usr/bin/env python3
"""
Agent Performance Dashboard

Generates comprehensive reports on agent quality, efficiency, and trends.
Identifies underperforming agents and provides actionable insights.

Usage:
    python3 scripts/agent_dashboard.py
    python3 scripts/agent_dashboard.py --export dashboard_report.md
    python3 scripts/agent_dashboard.py --alert-threshold 70
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class AgentDashboard:
    """Generate comprehensive agent performance reports"""

    def __init__(self, metrics_file: str = None):
        if metrics_file is None:
            script_dir = Path(__file__).parent.parent
            metrics_file = script_dir / "skills" / "agent_metrics.json"

        self.metrics_file = Path(metrics_file)
        self.metrics = self._load_metrics()

        # Alert thresholds
        self.CRITICAL_PASS_RATE = 50  # Below this = CRITICAL
        self.WARNING_PASS_RATE = 70  # Below this = WARNING
        self.TARGET_PASS_RATE = 80  # Target performance
        self.MAX_COST_MULTIPLIER = 2.0  # Cost/Q > 2x baseline = WARNING

    def _load_metrics(self) -> dict[str, Any]:
        """Load metrics from file"""
        if not self.metrics_file.exists():
            return {"version": "1.0", "runs": [], "summary": {"agents": {}}}

        with open(self.metrics_file) as f:
            return json.load(f)

    def generate_dashboard(self) -> str:
        """Generate full performance dashboard"""
        report = []

        # Header
        report.append("=" * 70)
        report.append("AGENT PERFORMANCE DASHBOARD")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Runs: {len(self.metrics.get('runs', []))}")
        report.append("")

        # Summary table
        report.extend(self._generate_summary_table())

        # Alerts
        alerts = self._generate_alerts()
        if alerts:
            report.append("\n" + "=" * 70)
            report.append("⚠️  ALERTS")
            report.append("=" * 70)
            for alert in alerts:
                report.append(f"  {alert}")

        # Detailed agent reports
        report.append("\n" + "=" * 70)
        report.append("DETAILED AGENT ANALYSIS")
        report.append("=" * 70)

        for agent_name in [
            "research_agent",
            "writer_agent",
            "editor_agent",
            "graphics_agent",
        ]:
            report.append("")
            report.extend(self._generate_agent_detail(agent_name))

        # Recommendations
        report.append("\n" + "=" * 70)
        report.append("RECOMMENDATIONS")
        report.append("=" * 70)
        report.extend(self._generate_recommendations())

        report.append("\n" + "=" * 70)
        return "\n".join(report)

    def _generate_summary_table(self) -> list[str]:
        """Generate summary table with all agents"""
        summary = self.metrics.get("summary", {}).get("agents", {})

        if not summary or all(not v for v in summary.values()):
            return ["No agent data available yet.\n"]

        # Table header
        lines = []
        lines.append("Agent             | Runs | Pass Rate | Quality | Rework | Cost/Q")
        lines.append(
            "------------------+------+-----------+---------+--------+--------"
        )

        # Calculate baseline cost (median cost_per_quality_unit across all agents)
        all_costs = []
        for agent_name in summary:
            agent_runs = [
                run["agents"].get(agent_name)
                for run in self.metrics["runs"]
                if agent_name in run["agents"]
            ]
            costs = [
                r.get("cost_per_quality_unit", 0)
                for r in agent_runs
                if r.get("cost_per_quality_unit", 0) > 0
                and r.get("cost_per_quality_unit", 0) != float("inf")
            ]
            all_costs.extend(costs)

        baseline_cost = sorted(all_costs)[len(all_costs) // 2] if all_costs else 0

        # Table rows
        for agent_name, stats in summary.items():
            if not stats:
                continue

            display_name = agent_name.replace("_", " ").title()[:17].ljust(17)
            runs = stats.get("total_runs", 0)

            # Pass rate (validation_pass_rate or gate_pass_rate)
            pass_rate = stats.get(
                "validation_pass_rate", stats.get("avg_gate_pass_rate", 0)
            )

            # Quality score
            quality = stats.get("avg_quality_score", 0)

            # Rework rate
            rework = stats.get("rework_rate", 0)

            # Cost per quality unit (calculate from recent runs)
            agent_runs = [
                run["agents"].get(agent_name)
                for run in self.metrics["runs"]
                if agent_name in run["agents"]
            ]
            costs = [
                r.get("cost_per_quality_unit", 0)
                for r in agent_runs
                if r.get("cost_per_quality_unit", 0) > 0
                and r.get("cost_per_quality_unit", 0) != float("inf")
            ]
            avg_cost = round(sum(costs) / len(costs)) if costs else 0

            # Alert indicators
            alert = ""
            if pass_rate < self.CRITICAL_PASS_RATE:
                alert = " 🔴"
            elif pass_rate < self.WARNING_PASS_RATE or (
                baseline_cost > 0
                and avg_cost > baseline_cost * self.MAX_COST_MULTIPLIER
            ):
                alert = " ⚠️"

            lines.append(
                f"{display_name} | {runs:4} | {pass_rate:6.0f}%   | {quality:4.0f}/100 | "
                f"{rework:4.0f}% | {avg_cost:5}{alert}"
            )

        if baseline_cost > 0:
            lines.append("")
            lines.append(
                f"Baseline Cost/Quality: {baseline_cost:.0f} tokens per quality unit"
            )
            lines.append(
                f"⚠️  = Warning (pass rate <{self.WARNING_PASS_RATE}% or cost >{self.MAX_COST_MULTIPLIER}x baseline)"
            )
            lines.append(f"🔴 = Critical (pass rate <{self.CRITICAL_PASS_RATE}%)")

        lines.append("")
        return lines

    def _generate_alerts(self) -> list[str]:
        """Generate alert messages for concerning metrics"""
        alerts = []
        summary = self.metrics.get("summary", {}).get("agents", {})

        # Calculate baseline cost
        all_costs = []
        for agent_name in summary:
            agent_runs = [
                run["agents"].get(agent_name)
                for run in self.metrics["runs"]
                if agent_name in run["agents"]
            ]
            costs = [
                r.get("cost_per_quality_unit", 0)
                for r in agent_runs
                if r.get("cost_per_quality_unit", 0) > 0
                and r.get("cost_per_quality_unit", 0) != float("inf")
            ]
            all_costs.extend(costs)

        baseline_cost = sorted(all_costs)[len(all_costs) // 2] if all_costs else 0

        for agent_name, stats in summary.items():
            if not stats:
                continue

            display_name = agent_name.replace("_", " ").title()

            # Pass rate alerts
            pass_rate = stats.get(
                "validation_pass_rate", stats.get("avg_gate_pass_rate", 0)
            )
            if pass_rate < self.CRITICAL_PASS_RATE:
                alerts.append(
                    f"🔴 CRITICAL: {display_name} pass rate {pass_rate:.0f}% "
                    f"(below {self.CRITICAL_PASS_RATE}%) - REQUIRES IMMEDIATE ATTENTION"
                )
            elif pass_rate < self.WARNING_PASS_RATE:
                alerts.append(
                    f"⚠️  WARNING: {display_name} pass rate {pass_rate:.0f}% "
                    f"(below {self.WARNING_PASS_RATE}%) - needs prompt review"
                )

            # Cost efficiency alerts
            agent_runs = [
                run["agents"].get(agent_name)
                for run in self.metrics["runs"]
                if agent_name in run["agents"]
            ]
            costs = [
                r.get("cost_per_quality_unit", 0)
                for r in agent_runs
                if r.get("cost_per_quality_unit", 0) > 0
                and r.get("cost_per_quality_unit", 0) != float("inf")
            ]
            avg_cost = sum(costs) / len(costs) if costs else 0

            if (
                baseline_cost > 0
                and avg_cost > baseline_cost * self.MAX_COST_MULTIPLIER
            ):
                multiplier = avg_cost / baseline_cost
                alerts.append(
                    f"⚠️  WARNING: {display_name} cost efficiency {avg_cost:.0f} tokens/quality "
                    f"({multiplier:.1f}x baseline) - excessive token usage"
                )

            # Rework rate alerts
            rework = stats.get("rework_rate", 0)
            if rework > 30:
                alerts.append(
                    f"⚠️  WARNING: {display_name} rework rate {rework:.0f}% "
                    f"(>30%) - enhance self-validation prompts"
                )

            # Quality trend alerts
            trend = stats.get("trend", "")
            if "declining" in trend.lower():
                alerts.append(
                    f"⚠️  WARNING: {display_name} quality trending downward - investigate"
                )

        return alerts

    def _generate_agent_detail(self, agent_name: str) -> list[str]:
        """Generate detailed analysis for specific agent"""
        summary = self.metrics.get("summary", {}).get("agents", {}).get(agent_name, {})

        if not summary:
            return [f"{agent_name.replace('_', ' ').title()}: No data"]

        lines = []
        lines.append(f"\n### {agent_name.replace('_', ' ').title()}")
        lines.append("-" * 70)

        # Core metrics
        lines.append(f"Total Runs: {summary.get('total_runs', 0)}")
        lines.append(f"Quality Score: {summary.get('avg_quality_score', 0):.1f}/100")

        # Agent-specific metrics
        if agent_name == "research_agent":
            lines.append(
                f"Verification Rate: {summary.get('avg_verification_rate', 0):.1f}%"
            )
            lines.append(
                f"Validation Pass Rate: {summary.get('validation_pass_rate', 0):.1f}%"
            )
            lines.append(f"Trend: {summary.get('trend', 'N/A')}")

        elif agent_name == "writer_agent":
            lines.append(f"Clean Draft Rate: {summary.get('clean_draft_rate', 0):.1f}%")
            lines.append(
                f"Validation Pass Rate: {summary.get('validation_pass_rate', 0):.1f}%"
            )
            lines.append(f"Rework Rate: {summary.get('rework_rate', 0):.1f}%")
            lines.append(
                f"Avg Regenerations: {summary.get('avg_regenerations', 0):.1f}"
            )

        elif agent_name == "editor_agent":
            lines.append(f"Gate Pass Rate: {summary.get('avg_gate_pass_rate', 0):.1f}%")
            lines.append(
                f"Quality Score: {summary.get('avg_quality_score', 0):.1f}/100"
            )
            lines.append(f"Trend: {summary.get('trend', 'N/A')}")

        elif agent_name == "graphics_agent":
            lines.append(
                f"Visual QA Pass Rate: {summary.get('avg_qa_pass_rate', 0):.1f}%"
            )
            lines.append(f"Avg Violations: {summary.get('avg_violations', 0):.1f}")

        # Recent performance (last 5 runs)
        agent_runs = [
            run["agents"].get(agent_name)
            for run in self.metrics["runs"]
            if agent_name in run["agents"]
        ]

        if len(agent_runs) >= 3:
            recent = agent_runs[-5:]
            recent_quality = [
                r.get("quality_score", 0) for r in recent if "quality_score" in r
            ]
            if recent_quality:
                lines.append(f"\nRecent Performance (last {len(recent)} runs):")
                lines.append(
                    f"  Quality Scores: {', '.join([str(int(q)) for q in recent_quality])}"
                )

                # Trend indicator
                if len(recent_quality) >= 3:
                    first_half = sum(recent_quality[: len(recent_quality) // 2]) / (
                        len(recent_quality) // 2
                    )
                    second_half = sum(recent_quality[len(recent_quality) // 2 :]) / (
                        len(recent_quality) - len(recent_quality) // 2
                    )

                    if second_half > first_half + 5:
                        lines.append(
                            f"  Trend: Improving ⬆️ (+{second_half - first_half:.1f} points)"
                        )
                    elif second_half < first_half - 5:
                        lines.append(
                            f"  Trend: Declining ⬇️ ({second_half - first_half:.1f} points)"
                        )
                    else:
                        lines.append("  Trend: Stable ➡️")

        return lines

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []
        summary = self.metrics.get("summary", {}).get("agents", {})

        # Identify worst performer
        agent_scores = {}
        for agent_name, stats in summary.items():
            if stats:
                pass_rate = stats.get(
                    "validation_pass_rate", stats.get("avg_gate_pass_rate", 0)
                )
                agent_scores[agent_name] = pass_rate

        if agent_scores:
            worst_agent = min(agent_scores, key=agent_scores.get)
            worst_score = agent_scores[worst_agent]

            if worst_score < self.WARNING_PASS_RATE:
                recommendations.append(
                    f"1. PRIORITY: Fix {worst_agent.replace('_', ' ').title()} "
                    f"(pass rate: {worst_score:.0f}%)"
                )
                recommendations.append("   - Review agent prompt for clarity")
                recommendations.append("   - Add explicit quality gate checks")
                recommendations.append("   - Enhance self-validation logic")

        # Check for high rework rates
        high_rework_agents = []
        for agent_name, stats in summary.items():
            rework = stats.get("rework_rate", 0)
            if rework > 30:
                high_rework_agents.append((agent_name, rework))

        if high_rework_agents:
            recommendations.append("")
            recommendations.append(
                "2. Reduce rework for agents with >30% regeneration rate:"
            )
            for agent_name, rework in high_rework_agents:
                recommendations.append(
                    f"   - {agent_name.replace('_', ' ').title()}: {rework:.0f}% rework rate"
                )

        # General recommendations
        if not recommendations:
            recommendations.append("✅ All agents performing within acceptable ranges")
            recommendations.append("")
            recommendations.append("Continuous improvement opportunities:")
            recommendations.append("  - Monitor trends over next 10 runs")
            recommendations.append("  - Target pass rates >80% for all agents")
            recommendations.append("  - Optimize cost per quality unit")

        recommendations.append("")
        return recommendations

    def export_report(self, output_file: str):
        """Export dashboard to markdown file"""
        report = self.generate_dashboard()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(report)

        print(f"✅ Dashboard exported to {output_file}")

    def check_alerts(self) -> bool:
        """Check if any alerts are triggered"""
        alerts = self._generate_alerts()
        return len(alerts) > 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Agent Performance Dashboard")
    parser.add_argument("--export", help="Export dashboard to markdown file")
    parser.add_argument(
        "--alert-threshold",
        type=int,
        default=70,
        help="Warning threshold for pass rate (default: 70)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for alerts, exit with code 1 if found",
    )

    args = parser.parse_args()

    dashboard = AgentDashboard()
    dashboard.WARNING_PASS_RATE = args.alert_threshold

    if args.check_only:
        has_alerts = dashboard.check_alerts()
        if has_alerts:
            print("⚠️  Alerts detected - run without --check-only to see details")
            sys.exit(1)
        else:
            print("✅ No alerts")
            sys.exit(0)

    if args.export:
        dashboard.export_report(args.export)
    else:
        print(dashboard.generate_dashboard())


if __name__ == "__main__":
    main()
