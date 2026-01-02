#!/usr/bin/env python3
"""
Chart Metrics Collection System

Tracks visual quality metrics for Economist-style charts:
- Charts generated count
- Visual QA pass rate
- Zone violations detected
- Regeneration attempts
- Common failure patterns
- Time per chart

Integrates with skills_manager for persistent metrics storage.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class ChartMetricsCollector:
    """Collects and persists chart generation metrics"""

    def __init__(self, metrics_file: str = None):
        if metrics_file is None:
            # Default to skills directory
            script_dir = Path(__file__).parent.parent
            metrics_file = script_dir / "skills" / "chart_metrics.json"

        self.metrics_file = Path(metrics_file)
        self.metrics = self._load_metrics()
        self.current_session = {"start_time": time.time(), "charts": []}

    def _load_metrics(self) -> dict[str, Any]:
        """Load existing metrics or create new"""
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                return json.load(f)
        else:
            return self._create_default_metrics()

    def _create_default_metrics(self) -> dict[str, Any]:
        """Create initial metrics structure"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "summary": {
                "total_charts_generated": 0,
                "total_visual_qa_runs": 0,
                "visual_qa_pass_count": 0,
                "visual_qa_fail_count": 0,
                "total_zone_violations": 0,
                "total_regenerations": 0,
                "total_generation_time_seconds": 0.0,
            },
            "failure_patterns": {},
            "sessions": [],
        }

    def start_chart(
        self, chart_title: str, chart_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Start tracking a new chart generation"""
        chart_record = {
            "title": chart_title,
            "timestamp": datetime.now().isoformat(),
            "start_time": time.time(),
            "chart_type": chart_spec.get("type", "unknown"),
            "generation_success": None,
            "generation_time_seconds": None,
            "visual_qa_run": False,
            "visual_qa_passed": None,
            "zone_violations": [],
            "regeneration_count": 0,
            "errors": [],
        }
        self.current_session["charts"].append(chart_record)
        return chart_record

    def record_generation(
        self, chart_record: dict[str, Any], success: bool, error: str = None
    ):
        """Record chart generation result"""
        chart_record["generation_time_seconds"] = (
            time.time() - chart_record["start_time"]
        )
        chart_record["generation_success"] = success

        if success:
            self.metrics["summary"]["total_charts_generated"] += 1
            self.metrics["summary"]["total_generation_time_seconds"] += chart_record[
                "generation_time_seconds"
            ]
        else:
            if error:
                chart_record["errors"].append(
                    {
                        "type": "generation_error",
                        "message": error,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    def record_visual_qa(self, chart_record: dict[str, Any], qa_result: dict[str, Any]):
        """Record Visual QA results"""
        chart_record["visual_qa_run"] = True
        chart_record["visual_qa_passed"] = qa_result.get("overall_pass", False)

        self.metrics["summary"]["total_visual_qa_runs"] += 1

        if qa_result.get("overall_pass"):
            self.metrics["summary"]["visual_qa_pass_count"] += 1
        else:
            self.metrics["summary"]["visual_qa_fail_count"] += 1

        # Extract zone violations
        gates = qa_result.get("gates", {})
        zone_gate = gates.get("zone_integrity", {})
        if not zone_gate.get("pass", True):
            violations = zone_gate.get("issues", [])
            chart_record["zone_violations"] = violations
            self.metrics["summary"]["total_zone_violations"] += len(violations)

            # Track failure patterns
            for violation in violations:
                self._track_failure_pattern("zone_violation", violation)

        # Track other failure patterns
        if not qa_result.get("overall_pass"):
            for issue in qa_result.get("critical_issues", []):
                self._track_failure_pattern("critical_issue", issue)

    def record_regeneration(self, chart_record: dict[str, Any], reason: str):
        """Record a chart regeneration attempt"""
        chart_record["regeneration_count"] += 1
        self.metrics["summary"]["total_regenerations"] += 1

        chart_record["errors"].append(
            {
                "type": "regeneration",
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _track_failure_pattern(self, pattern_type: str, issue: str):
        """Track recurring failure patterns"""
        if pattern_type not in self.metrics["failure_patterns"]:
            self.metrics["failure_patterns"][pattern_type] = {}

        patterns = self.metrics["failure_patterns"][pattern_type]

        # Normalize issue for counting
        normalized_issue = issue.lower().strip()

        if normalized_issue not in patterns:
            patterns[normalized_issue] = {
                "count": 0,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }

        patterns[normalized_issue]["count"] += 1
        patterns[normalized_issue]["last_seen"] = datetime.now().isoformat()

    def end_session(self):
        """Finalize current session and save metrics"""
        session_duration = time.time() - self.current_session["start_time"]

        session_summary = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": session_duration,
            "charts_generated": len(
                [
                    c
                    for c in self.current_session["charts"]
                    if c.get("generation_success")
                ]
            ),
            "visual_qa_runs": len(
                [c for c in self.current_session["charts"] if c.get("visual_qa_run")]
            ),
            "visual_qa_passed": len(
                [c for c in self.current_session["charts"] if c.get("visual_qa_passed")]
            ),
            "charts": self.current_session["charts"],
        }

        self.metrics["sessions"].append(session_summary)
        self.metrics["last_updated"] = datetime.now().isoformat()
        self.save()

    def save(self):
        """Persist metrics to disk"""
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def get_summary(self) -> dict[str, Any]:
        """Get summary metrics"""
        summary = self.metrics["summary"].copy()

        # Calculate derived metrics
        if summary["total_charts_generated"] > 0:
            summary["avg_generation_time_seconds"] = (
                summary["total_generation_time_seconds"]
                / summary["total_charts_generated"]
            )
        else:
            summary["avg_generation_time_seconds"] = 0.0

        if summary["total_visual_qa_runs"] > 0:
            summary["visual_qa_pass_rate"] = (
                summary["visual_qa_pass_count"] / summary["total_visual_qa_runs"]
            ) * 100
        else:
            summary["visual_qa_pass_rate"] = 0.0

        if summary["total_charts_generated"] > 0:
            summary["avg_zone_violations_per_chart"] = (
                summary["total_zone_violations"] / summary["total_charts_generated"]
            )
        else:
            summary["avg_zone_violations_per_chart"] = 0.0

        return summary

    def get_top_failure_patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most common failure patterns"""
        all_patterns = []

        for pattern_type, patterns in self.metrics["failure_patterns"].items():
            for issue, data in patterns.items():
                all_patterns.append(
                    {
                        "type": pattern_type,
                        "issue": issue,
                        "count": data["count"],
                        "first_seen": data["first_seen"],
                        "last_seen": data["last_seen"],
                    }
                )

        # Sort by count descending
        all_patterns.sort(key=lambda x: x["count"], reverse=True)
        return all_patterns[:limit]

    def export_report(self, include_sessions: bool = False) -> str:
        """Generate human-readable metrics report"""
        summary = self.get_summary()
        top_patterns = self.get_top_failure_patterns(10)

        report_lines = [
            "=" * 70,
            "CHART METRICS REPORT",
            "=" * 70,
            f"Last Updated: {self.metrics.get('last_updated', 'Unknown')}",
            "",
            "SUMMARY METRICS:",
            "-" * 70,
            f"  Total Charts Generated: {summary['total_charts_generated']}",
            f"  Visual QA Runs: {summary['total_visual_qa_runs']}",
            f"  Visual QA Pass Rate: {summary['visual_qa_pass_rate']:.1f}%",
            f"    - Passed: {summary['visual_qa_pass_count']}",
            f"    - Failed: {summary['visual_qa_fail_count']}",
            f"  Total Zone Violations: {summary['total_zone_violations']}",
            f"  Avg Zone Violations/Chart: {summary['avg_zone_violations_per_chart']:.2f}",
            f"  Total Regenerations: {summary['total_regenerations']}",
            f"  Avg Generation Time: {summary['avg_generation_time_seconds']:.2f}s",
            "",
            "TOP FAILURE PATTERNS:",
            "-" * 70,
        ]

        if top_patterns:
            for i, pattern in enumerate(top_patterns, 1):
                report_lines.append(f"  #{i} [{pattern['count']}x] {pattern['type']}")
                report_lines.append(f"      {pattern['issue'][:100]}...")
                report_lines.append(
                    f"      First: {pattern['first_seen'][:10]}, Last: {pattern['last_seen'][:10]}"
                )
        else:
            report_lines.append("  No failure patterns recorded yet")

        if include_sessions and self.metrics["sessions"]:
            report_lines.extend(["", "RECENT SESSIONS:", "-" * 70])

            for session in self.metrics["sessions"][-5:]:  # Last 5 sessions
                report_lines.append(f"  Session: {session['timestamp'][:19]}")
                report_lines.append(f"    Duration: {session['duration_seconds']:.1f}s")
                report_lines.append(f"    Charts: {session['charts_generated']}")
                report_lines.append(
                    f"    Visual QA: {session['visual_qa_passed']}/{session['visual_qa_runs']} passed"
                )

        report_lines.append("=" * 70)
        return "\n".join(report_lines)


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> ChartMetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = ChartMetricsCollector()
    return _metrics_collector


if __name__ == "__main__":
    # Test the metrics collector
    collector = ChartMetricsCollector()
    print(collector.export_report())
