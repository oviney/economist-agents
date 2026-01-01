#!/usr/bin/env python3
"""
Chart Metrics Reporting Tool

Generate detailed reports on chart quality metrics.
Supports multiple export formats (console, markdown, JSON).

Usage:
    python3 metrics_report.py                    # Console report
    python3 metrics_report.py --format markdown  # Markdown export
    python3 metrics_report.py --sessions         # Include session details
    python3 metrics_report.py --top-patterns 20  # Show top 20 failure patterns
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from chart_metrics import ChartMetricsCollector


def generate_console_report(collector: ChartMetricsCollector, include_sessions: bool = False):
    """Generate console-friendly report"""
    print(collector.export_report(include_sessions=include_sessions))


def generate_markdown_report(collector: ChartMetricsCollector, output_file: str = None):
    """Generate markdown report"""
    summary = collector.get_summary()
    top_patterns = collector.get_top_failure_patterns(10)
    
    report_lines = [
        "# Chart Quality Metrics Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Last Updated:** {collector.metrics.get('last_updated', 'Unknown')}",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Charts Generated | {summary['total_charts_generated']} |",
        f"| Visual QA Runs | {summary['total_visual_qa_runs']} |",
        f"| Visual QA Pass Rate | {summary['visual_qa_pass_rate']:.1f}% |",
        f"| Visual QA Passed | {summary['visual_qa_pass_count']} |",
        f"| Visual QA Failed | {summary['visual_qa_fail_count']} |",
        f"| Total Zone Violations | {summary['total_zone_violations']} |",
        f"| Avg Zone Violations/Chart | {summary['avg_zone_violations_per_chart']:.2f} |",
        f"| Total Regenerations | {summary['total_regenerations']} |",
        f"| Avg Generation Time | {summary['avg_generation_time_seconds']:.2f}s |",
        "",
        "## Top Failure Patterns",
        "",
    ]
    
    if top_patterns:
        report_lines.append("| Rank | Count | Type | Issue |")
        report_lines.append("|------|-------|------|-------|")
        
        for i, pattern in enumerate(top_patterns, 1):
            issue_preview = pattern['issue'][:80] + "..." if len(pattern['issue']) > 80 else pattern['issue']
            report_lines.append(f"| {i} | {pattern['count']} | {pattern['type']} | {issue_preview} |")
    else:
        report_lines.append("*No failure patterns recorded yet*")
    
    report_lines.extend([
        "",
        "## Trend Analysis",
        "",
    ])
    
    # Calculate trends from recent sessions
    sessions = collector.metrics.get("sessions", [])
    if len(sessions) >= 2:
        recent = sessions[-5:]
        qa_rates = [
            (s['visual_qa_passed'] / s['visual_qa_runs'] * 100) if s['visual_qa_runs'] > 0 else 0
            for s in recent
        ]
        
        if len(qa_rates) >= 2:
            trend = "improving" if qa_rates[-1] > qa_rates[0] else "declining"
            report_lines.append(f"- Visual QA pass rate is **{trend}** over last {len(recent)} sessions")
            report_lines.append(f"- Current pass rate: {qa_rates[-1]:.1f}%")
            report_lines.append(f"- Previous pass rate: {qa_rates[0]:.1f}%")
    else:
        report_lines.append("*Insufficient data for trend analysis (need 2+ sessions)*")
    
    report_lines.extend([
        "",
        "## Recommendations",
        "",
    ])
    
    # Generate actionable recommendations
    if summary['visual_qa_pass_rate'] < 80:
        report_lines.append("- ⚠️  **Low QA Pass Rate**: Visual QA pass rate below 80% - review agent prompts")
    
    if summary['avg_zone_violations_per_chart'] > 0.5:
        report_lines.append("- ⚠️  **Zone Violations**: High rate of zone violations - strengthen layout rules in prompt")
    
    if summary['total_regenerations'] > summary['total_charts_generated'] * 0.3:
        report_lines.append("- ⚠️  **High Regeneration Rate**: >30% regeneration rate - improve first-attempt quality")
    
    if top_patterns:
        most_common = top_patterns[0]
        report_lines.append(f"- 🎯 **Top Issue**: '{most_common['type']}' ({most_common['count']}x) - prioritize fix")
    
    if not report_lines[-1].startswith("-"):
        report_lines.append("- ✅ **Quality Metrics Good**: No major issues detected")
    
    markdown_content = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(markdown_content)
        print(f"✅ Markdown report saved to {output_file}")
    else:
        print(markdown_content)


def generate_json_export(collector: ChartMetricsCollector, output_file: str = None):
    """Export metrics as JSON"""
    export_data = {
        "generated_at": datetime.now().isoformat(),
        "summary": collector.get_summary(),
        "top_failure_patterns": collector.get_top_failure_patterns(20),
        "total_sessions": len(collector.metrics.get("sessions", []))
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"✅ JSON export saved to {output_file}")
    else:
        print(json.dumps(export_data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Generate chart quality metrics reports',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--format',
        choices=['console', 'markdown', 'json'],
        default='console',
        help='Report format (default: console)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file (default: stdout)'
    )
    
    parser.add_argument(
        '--sessions',
        action='store_true',
        help='Include session details in report'
    )
    
    parser.add_argument(
        '--top-patterns',
        type=int,
        default=10,
        help='Number of top failure patterns to show (default: 10)'
    )
    
    parser.add_argument(
        '--metrics-file',
        help='Path to metrics file (default: skills/chart_metrics.json)'
    )
    
    args = parser.parse_args()
    
    # Load metrics
    collector = ChartMetricsCollector(args.metrics_file)
    
    # Check if metrics exist
    if collector.metrics['summary']['total_charts_generated'] == 0:
        print("⚠️  No metrics data found. Generate some charts first!")
        return
    
    # Generate report based on format
    if args.format == 'console':
        generate_console_report(collector, include_sessions=args.sessions)
    
    elif args.format == 'markdown':
        output_file = args.output or 'docs/CHART_METRICS_REPORT.md'
        generate_markdown_report(collector, output_file)
    
    elif args.format == 'json':
        generate_json_export(collector, args.output)


if __name__ == "__main__":
    main()
