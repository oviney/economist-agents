#!/usr/bin/env python3
"""
Agent Performance Metrics Tracker

Tracks per-agent predictions vs actuals to identify improvement opportunities.
Stores metrics in skills/agent_metrics.json with historical trends.

Usage:
    from agent_metrics import AgentMetrics

    metrics = AgentMetrics()
    metrics.track_research_agent(data_points=10, verified=8, unverified=2)
    metrics.track_writer_agent(banned_phrases=0, validation_passed=True, regenerations=0)
    metrics.save()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AgentMetrics:
    """Tracks and analyzes agent performance over time"""

    def __init__(self, metrics_file: str = None):
        if metrics_file is None:
            # Default to skills directory
            script_dir = Path(__file__).parent.parent
            metrics_file = script_dir / "skills" / "agent_metrics.json"

        self.metrics_file = Path(metrics_file)
        self.metrics = self._load_metrics()
        self.current_run = {"timestamp": datetime.now().isoformat(), "agents": {}}

    def _load_metrics(self) -> dict[str, Any]:
        """Load existing metrics or create new structure"""
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                return json.load(f)
        else:
            return {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "runs": [],
                "summary": {
                    "total_runs": 0,
                    "agents": {
                        "research_agent": {},
                        "writer_agent": {},
                        "editor_agent": {},
                        "graphics_agent": {},
                    },
                },
            }

    def track_research_agent(
        self,
        data_points: int,
        verified: int,
        unverified: int,
        sources: list[str] = None,
        validation_passed: bool = True,
        token_usage: int = 0,
    ):
        """Track Research Agent performance"""
        verification_rate = (verified / data_points * 100) if data_points > 0 else 0

        # Calculate quality score (0-100)
        quality_score = (
            verification_rate if validation_passed else verification_rate * 0.5
        )

        self.current_run["agents"]["research_agent"] = {
            "data_points": data_points,
            "verified": verified,
            "unverified": unverified,
            "verification_rate": round(verification_rate, 1),
            "sources": sources or [],
            "validation_passed": validation_passed,
            "quality_score": round(quality_score, 1),
            "token_usage": token_usage,
            "cost_per_quality_unit": round(token_usage / quality_score, 2)
            if quality_score > 0
            else 0,
            "prediction": "High verification rate (>80%)",
            "actual": "Pass" if verification_rate >= 80 else "Needs improvement",
        }

    def track_writer_agent(
        self,
        word_count: int,
        banned_phrases: int,
        validation_passed: bool,
        regenerations: int,
        chart_embedded: bool = True,
        token_usage: int = 0,
    ):
        """Track Writer Agent performance"""

        # Calculate quality score (0-100)
        quality_score = 100
        if banned_phrases > 0:
            quality_score -= banned_phrases * 10  # -10 per banned phrase
        if not chart_embedded:
            quality_score -= 20  # -20 if chart missing
        if not validation_passed:
            quality_score -= 30  # -30 if validation failed
        quality_score = max(0, quality_score)  # Floor at 0

        # Calculate total token cost (including regenerations)
        total_tokens = token_usage * (regenerations + 1)

        self.current_run["agents"]["writer_agent"] = {
            "word_count": word_count,
            "banned_phrases": banned_phrases,
            "validation_passed": validation_passed,
            "regenerations": regenerations,
            "chart_embedded": chart_embedded,
            "quality_score": round(quality_score, 1),
            "token_usage": total_tokens,
            "cost_per_quality_unit": round(total_tokens / quality_score, 2)
            if quality_score > 0
            else float("inf"),
            "prediction": "Clean draft (0 banned phrases, chart embedded)",
            "actual": "Pass"
            if (banned_phrases == 0 and chart_embedded)
            else "Needs improvement",
        }

    def track_editor_agent(
        self,
        gates_passed: int,
        gates_failed: int,
        edits_made: int,
        quality_issues: list[str] = None,
        token_usage: int = 0,
    ):
        """Track Editor Agent performance"""
        total_gates = gates_passed + gates_failed
        pass_rate = (gates_passed / total_gates * 100) if total_gates > 0 else 0

        # Calculate quality score (0-100)
        quality_score = pass_rate
        if quality_issues:
            quality_score -= len(quality_issues) * 5  # -5 per issue
        quality_score = max(0, quality_score)

        self.current_run["agents"]["editor_agent"] = {
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "gate_pass_rate": round(pass_rate, 1),
            "edits_made": edits_made,
            "quality_issues": quality_issues or [],
            "quality_score": round(quality_score, 1),
            "token_usage": token_usage,
            "cost_per_quality_unit": round(token_usage / quality_score, 2)
            if quality_score > 0
            else 0,
            "prediction": "All gates pass (5/5)",
            "actual": "Pass" if gates_failed == 0 else f"Failed {gates_failed} gates",
        }

    def track_graphics_agent(
        self,
        charts_generated: int,
        visual_qa_passed: int,
        zone_violations: int,
        regenerations: int,
        token_usage: int = 0,
        validation_passed: bool = True,
    ):
        """Track Graphics Agent performance"""
        qa_pass_rate = (
            (visual_qa_passed / charts_generated * 100) if charts_generated > 0 else 0
        )

        # Calculate quality score (0-100)
        quality_score = qa_pass_rate
        if zone_violations > 0:
            quality_score -= zone_violations * 15  # -15 per violation
        quality_score = max(0, quality_score)

        # Calculate total token cost (including regenerations)
        total_tokens = token_usage * (regenerations + 1)

        self.current_run["agents"]["graphics_agent"] = {
            "charts_generated": charts_generated,
            "visual_qa_passed": visual_qa_passed,
            "visual_qa_pass_rate": round(qa_pass_rate, 1),
            "zone_violations": zone_violations,
            "regenerations": regenerations,
            "validation_passed": validation_passed,
            "quality_score": round(quality_score, 1),
            "token_usage": total_tokens,
            "cost_per_quality_unit": round(total_tokens / quality_score, 2)
            if quality_score > 0
            else float("inf"),
            "prediction": "Pass Visual QA (100%)",
            "actual": "Pass"
            if zone_violations == 0
            else f"{zone_violations} violations",
        }

    def finalize_run(self):
        """Calculate run summary and prepare for save"""
        # Count successful agents (prediction == actual)
        agents = self.current_run["agents"]
        successful = sum(
            1 for a in agents.values() if a.get("actual", "").startswith("Pass")
        )
        total = len(agents)

        self.current_run["summary"] = {
            "agents_tracked": total,
            "agents_successful": successful,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
        }

    def save(self):
        """Persist metrics to disk"""
        self.finalize_run()

        # Add current run to history
        self.metrics["runs"].append(self.current_run)
        self.metrics["summary"]["total_runs"] = len(self.metrics["runs"])

        # Update per-agent summaries
        self._update_agent_summaries()

        # Save to file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def _update_agent_summaries(self):
        """Calculate aggregate statistics for each agent"""
        for agent_name in [
            "research_agent",
            "writer_agent",
            "editor_agent",
            "graphics_agent",
        ]:
            agent_runs = [
                run["agents"].get(agent_name)
                for run in self.metrics["runs"]
                if agent_name in run["agents"]
            ]

            if not agent_runs:
                continue

            # Calculate trends and quality metrics
            quality_scores = [
                r.get("quality_score", 0) for r in agent_runs if "quality_score" in r
            ]
            validation_passed = sum(
                1 for r in agent_runs if r.get("validation_passed", True)
            )
            validation_pass_rate = (
                round(validation_passed / len(agent_runs) * 100, 1) if agent_runs else 0
            )

            if agent_name == "research_agent":
                rates = [
                    r["verification_rate"]
                    for r in agent_runs
                    if "verification_rate" in r
                ]
                self.metrics["summary"]["agents"][agent_name] = {
                    "total_runs": len(agent_runs),
                    "avg_verification_rate": round(sum(rates) / len(rates), 1)
                    if rates
                    else 0,
                    "avg_quality_score": round(
                        sum(quality_scores) / len(quality_scores), 1
                    )
                    if quality_scores
                    else 0,
                    "validation_pass_rate": validation_pass_rate,
                    "trend": self._calculate_trend(rates),
                }

            elif agent_name == "writer_agent":
                clean_drafts = sum(
                    1 for r in agent_runs if r.get("banned_phrases", 1) == 0
                )
                regen_counts = [r.get("regenerations", 0) for r in agent_runs]
                self.metrics["summary"]["agents"][agent_name] = {
                    "total_runs": len(agent_runs),
                    "clean_draft_rate": round(clean_drafts / len(agent_runs) * 100, 1),
                    "avg_regenerations": round(sum(regen_counts) / len(regen_counts), 1)
                    if regen_counts
                    else 0,
                    "avg_quality_score": round(
                        sum(quality_scores) / len(quality_scores), 1
                    )
                    if quality_scores
                    else 0,
                    "validation_pass_rate": validation_pass_rate,
                    "rework_rate": round(
                        sum(1 for r in regen_counts if r > 0) / len(regen_counts) * 100,
                        1,
                    )
                    if regen_counts
                    else 0,
                }

            elif agent_name == "editor_agent":
                pass_rates = [
                    r["gate_pass_rate"] for r in agent_runs if "gate_pass_rate" in r
                ]
                self.metrics["summary"]["agents"][agent_name] = {
                    "total_runs": len(agent_runs),
                    "avg_gate_pass_rate": round(sum(pass_rates) / len(pass_rates), 1)
                    if pass_rates
                    else 0,
                    "avg_quality_score": round(
                        sum(quality_scores) / len(quality_scores), 1
                    )
                    if quality_scores
                    else 0,
                    "trend": self._calculate_trend(pass_rates),
                }

            elif agent_name == "graphics_agent":
                qa_rates = [
                    r["visual_qa_pass_rate"]
                    for r in agent_runs
                    if "visual_qa_pass_rate" in r
                ]
                violations = [r.get("zone_violations", 0) for r in agent_runs]
                self.metrics["summary"]["agents"][agent_name] = {
                    "total_runs": len(agent_runs),
                    "avg_qa_pass_rate": round(sum(qa_rates) / len(qa_rates), 1)
                    if qa_rates
                    else 0,
                    "avg_quality_score": round(
                        sum(quality_scores) / len(quality_scores), 1
                    )
                    if quality_scores
                    else 0,
                    "avg_violations": round(sum(violations) / len(violations), 1)
                    if violations
                    else 0,
                    "validation_pass_rate": validation_pass_rate,
                }

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend direction from list of values"""
        if len(values) < 2:
            return "stable"

        # Compare first half vs second half
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)

        diff = second_half - first_half
        if diff > 5:
            return "improving ⬆️"
        elif diff < -5:
            return "declining ⬇️"
        else:
            return "stable ➡️"

    def get_latest_run(self) -> dict[str, Any] | None:
        """Get most recent run data"""
        if self.metrics["runs"]:
            return self.metrics["runs"][-1]
        return None

    def get_agent_history(
        self, agent_name: str, last_n: int = 10
    ) -> list[dict[str, Any]]:
        """Get last N runs for specific agent"""
        agent_runs = []
        for run in reversed(self.metrics["runs"]):
            if agent_name in run["agents"]:
                agent_runs.append(
                    {"timestamp": run["timestamp"], **run["agents"][agent_name]}
                )
                if len(agent_runs) >= last_n:
                    break
        return agent_runs

    def export_summary_report(self) -> str:
        """Generate human-readable summary report"""
        report = []
        report.append("=" * 70)
        report.append("AGENT PERFORMANCE SUMMARY")
        report.append("=" * 70)
        report.append("")
        report.append(f"Total Runs: {self.metrics['summary']['total_runs']}")
        report.append("")

        for agent_name, stats in self.metrics["summary"]["agents"].items():
            if not stats:
                continue

            report.append(f"\n{agent_name.replace('_', ' ').title()}:")
            report.append("-" * 70)

            # Common metrics
            report.append(f"  Quality Score: {stats.get('avg_quality_score', 0)}/100")
            report.append(
                f"  Validation Pass Rate: {stats.get('validation_pass_rate', 0)}%"
            )

            if agent_name == "research_agent":
                report.append(
                    f"  Average Verification Rate: {stats.get('avg_verification_rate', 0)}%"
                )
                report.append(f"  Trend: {stats.get('trend', 'N/A')}")

            elif agent_name == "writer_agent":
                report.append(
                    f"  Clean Draft Rate: {stats.get('clean_draft_rate', 0)}%"
                )
                report.append(f"  Rework Rate: {stats.get('rework_rate', 0)}%")
                report.append(
                    f"  Average Regenerations: {stats.get('avg_regenerations', 0)}"
                )

            elif agent_name == "editor_agent":
                report.append(
                    f"  Average Gate Pass Rate: {stats.get('avg_gate_pass_rate', 0)}%"
                )
                report.append(f"  Trend: {stats.get('trend', 'N/A')}")

            elif agent_name == "graphics_agent":
                report.append(
                    f"  Average Visual QA Pass Rate: {stats.get('avg_qa_pass_rate', 0)}%"
                )
                report.append(f"  Average Violations: {stats.get('avg_violations', 0)}")

        report.append("\n" + "=" * 70)
        return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    metrics = AgentMetrics()

    # Track a sample run
    metrics.track_research_agent(
        data_points=10,
        verified=9,
        unverified=1,
        sources=["Gartner 2024", "TestGuild Survey"],
    )

    metrics.track_writer_agent(
        word_count=1200,
        banned_phrases=0,
        validation_passed=True,
        regenerations=0,
        chart_embedded=True,
    )

    metrics.track_editor_agent(
        gates_passed=5, gates_failed=0, edits_made=12, quality_issues=[]
    )

    metrics.track_graphics_agent(
        charts_generated=1, visual_qa_passed=1, zone_violations=0, regenerations=0
    )

    metrics.save()

    print(metrics.export_summary_report())
