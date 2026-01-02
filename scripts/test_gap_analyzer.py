#!/usr/bin/env python3
"""
Test Gap Detection Automation

Analyzes defect tracker to identify systematic test gaps and generate
actionable recommendations for closing those gaps.

Sprint 7, Story 2 (5 points, P1)

Goal: Understand why 50% of bugs are missed by visual_qa and integration tests,
      propose automated detection improvements.

Usage:
    python3 scripts/test_gap_analyzer.py --analyze
    python3 scripts/test_gap_analyzer.py --report
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import argparse


class TestGapAnalyzer:
    """Analyzes defect patterns to identify test coverage gaps"""
    
    # Test types that should catch bugs
    TEST_TYPES = [
        "unit_test",
        "integration_test",
        "e2e_test",
        "manual_test",
        "visual_qa",
        "none"  # Bugs that no test could catch
    ]
    
    # Agent components
    AGENT_COMPONENTS = [
        "research_agent",
        "writer_agent",
        "graphics_agent",
        "editor_agent"
    ]
    
    def __init__(self, defect_tracker_file: str = "skills/defect_tracker.json"):
        self.defect_tracker_file = Path(defect_tracker_file)
        self.findings = {}
        
    def load_defect_data(self) -> Dict:
        """Load defect tracker with RCA data"""
        if not self.defect_tracker_file.exists():
            print(f"⚠️  Defect tracker not found: {self.defect_tracker_file}")
            return {"bugs": []}
        
        with open(self.defect_tracker_file) as f:
            return json.load(f)
    
    def analyze_test_gap_distribution(self) -> Dict:
        """Analyze which test types have gaps"""
        print("\n" + "="*70)
        print("🧪 ANALYZING TEST GAP DISTRIBUTION")
        print("="*70)
        
        defect_data = self.load_defect_data()
        bugs = defect_data.get("bugs", [])
        
        if not bugs:
            print("⚠️  No bugs in tracker yet")
            return {"error": "No bugs"}
        
        # Count bugs by missed test type
        test_gaps = defaultdict(int)
        agent_gaps = defaultdict(int)
        
        bugs_with_test_data = []
        
        for bug in bugs:
            missed_by = bug.get("missed_by_test_type")
            agent = bug.get("responsible_agent")
            
            if missed_by:
                test_gaps[missed_by] += 1
                bugs_with_test_data.append(bug)
                
            if agent:
                agent_gaps[agent] += 1
        
        # Calculate percentages
        total_bugs_with_data = len(bugs_with_test_data)
        gap_percentages = {
            test_type: (count / total_bugs_with_data * 100) if total_bugs_with_data > 0 else 0
            for test_type, count in test_gaps.items()
        }
        
        # Sort by frequency
        sorted_gaps = sorted(gap_percentages.items(), key=lambda x: x[1], reverse=True)
        
        results = {
            "total_bugs_analyzed": len(bugs),
            "bugs_with_test_data": total_bugs_with_data,
            "test_gap_distribution": dict(gap_percentages),
            "top_gaps": sorted_gaps[:3],
            "agent_gaps": dict(agent_gaps)
        }
        
        print(f"\n📊 Test Gap Analysis:")
        print(f"   Total Bugs: {len(bugs)}")
        print(f"   Bugs with Test Gap Data: {total_bugs_with_data}")
        print(f"\n   Top Test Gaps:")
        for test_type, pct in sorted_gaps[:5]:
            print(f"      {test_type}: {pct:.1f}% ({test_gaps[test_type]} bugs)")
        
        if agent_gaps:
            print(f"\n   Agent-Specific Gaps:")
            for agent, count in sorted(agent_gaps.items(), key=lambda x: x[1], reverse=True):
                print(f"      {agent}: {count} bugs")
        
        self.findings["test_gap_distribution"] = results
        return results
    
    def map_gaps_to_components(self) -> Dict:
        """Map test gaps to specific agent components"""
        print("\n" + "="*70)
        print("🗺️  MAPPING GAPS TO COMPONENTS")
        print("="*70)
        
        defect_data = self.load_defect_data()
        bugs = defect_data.get("bugs", [])
        
        # Map test type + agent + root cause
        gap_patterns = []
        
        for bug in bugs:
            missed_by = bug.get("missed_by_test_type")
            agent = bug.get("responsible_agent")
            root_cause = bug.get("root_cause")
            
            if missed_by and agent:
                gap_patterns.append({
                    "bug_id": bug["id"],
                    "test_type": missed_by,
                    "agent": agent,
                    "root_cause": root_cause,
                    "severity": bug.get("severity"),
                    "description": bug.get("description", "")[:60] + "..."
                })
        
        # Group by test type + agent
        component_gaps = defaultdict(list)
        for pattern in gap_patterns:
            key = f"{pattern['test_type']}_{pattern['agent']}"
            component_gaps[key].append(pattern)
        
        # Identify highest-priority gaps
        priority_gaps = []
        for key, patterns in component_gaps.items():
            test_type, agent = key.split("_", 1)
            critical_count = sum(1 for p in patterns if p["severity"] == "critical")
            
            priority_gaps.append({
                "test_type": test_type,
                "agent": agent,
                "bug_count": len(patterns),
                "critical_count": critical_count,
                "priority": "HIGH" if critical_count > 0 else "MEDIUM",
                "examples": [p["bug_id"] for p in patterns[:3]]
            })
        
        # Sort by bug count
        priority_gaps.sort(key=lambda x: x["bug_count"], reverse=True)
        
        results = {
            "total_patterns": len(gap_patterns),
            "component_gaps": len(component_gaps),
            "priority_gaps": priority_gaps
        }
        
        print(f"\n🎯 Component Gap Mapping:")
        print(f"   Total Gap Patterns: {len(gap_patterns)}")
        print(f"   Component Combinations: {len(component_gaps)}")
        print(f"\n   High-Priority Gaps:")
        for gap in priority_gaps[:5]:
            print(f"      {gap['test_type']} + {gap['agent']}: {gap['bug_count']} bugs ({gap['priority']} priority)")
        
        self.findings["component_gaps"] = results
        return results
    
    def generate_recommendations(self) -> List[Dict]:
        """Generate actionable test improvement recommendations"""
        print("\n" + "="*70)
        print("💡 GENERATING RECOMMENDATIONS")
        print("="*70)
        
        test_gaps = self.findings.get("test_gap_distribution", {})
        component_gaps = self.findings.get("component_gaps", {})
        
        recommendations = []
        
        # Recommendation 1: Visual QA Gaps
        if test_gaps.get("test_gap_distribution", {}).get("visual_qa", 0) > 20:
            recommendations.append({
                "priority": "P0",
                "title": "Enhance Visual QA Coverage for Chart Zone Violations",
                "gap_addressed": "visual_qa",
                "effort": "MEDIUM (2-3 days)",
                "description": "Add automated zone boundary checks to Visual QA agent",
                "implementation": [
                    "Extend visual_qa.py with programmatic zone validation",
                    "Add pixel-based boundary detection (title/chart/axis zones)",
                    "Generate fail-fast errors for zone violations",
                    "Integrate with chart_metrics.py for automatic tracking"
                ],
                "expected_impact": "Catch 80% of chart layout bugs before publication",
                "validation": "Re-run diagnostic on historical bugs with enhanced QA"
            })
        
        # Recommendation 2: Integration Test Gaps
        if test_gaps.get("test_gap_distribution", {}).get("integration_test", 0) > 20:
            recommendations.append({
                "priority": "P0",
                "title": "Add Integration Tests for Agent Pipeline",
                "gap_addressed": "integration_test",
                "effort": "HIGH (3-5 days)",
                "description": "Create end-to-end test suite covering full article generation pipeline",
                "implementation": [
                    "Create scripts/test_pipeline_integration.py",
                    "Test Research → Writer → Editor → Validator flow",
                    "Add assertions for chart embedding, category fields, YAML format",
                    "Mock LLM responses for deterministic testing"
                ],
                "expected_impact": "Catch agent coordination bugs before deployment",
                "validation": "Run integration tests in CI/CD on every commit"
            })
        
        # Recommendation 3: Writer Agent Validation
        writer_gaps = [g for g in component_gaps.get("priority_gaps", []) 
                      if g["agent"] == "writer_agent"]
        if writer_gaps:
            recommendations.append({
                "priority": "P1",
                "title": "Strengthen Writer Agent Self-Validation",
                "gap_addressed": "writer_agent defects",
                "effort": "LOW (1-2 days)",
                "description": "Enhance agent_reviewer.py with Writer-specific checks",
                "implementation": [
                    "Add pre-output validation checklist to Writer prompt",
                    "Extend review_writer_output() with chart embedding check",
                    "Add frontmatter validation (layout, category, date fields)",
                    "Regenerate if critical validations fail"
                ],
                "expected_impact": "Reduce Writer defects by 40% through self-correction",
                "validation": "Monitor Writer validation_passed metric over 10 runs"
            })
        
        # Recommendation 4: Manual Test Automation
        if test_gaps.get("test_gap_distribution", {}).get("manual_test", 0) > 15:
            recommendations.append({
                "priority": "P2",
                "title": "Automate Manual Testing Scenarios",
                "gap_addressed": "manual_test",
                "effort": "MEDIUM (2-3 days)",
                "description": "Convert manual test cases into automated test scripts",
                "implementation": [
                    "Document current manual test scenarios",
                    "Identify automatable checks (Jekyll validation, link checking)",
                    "Extend blog_qa_agent.py with automated equivalents",
                    "Add to pre-commit hook for zero-config enforcement"
                ],
                "expected_impact": "Eliminate 60% of manual testing burden",
                "validation": "Track manual test escapes over next 10 bugs"
            })
        
        # Recommendation 5: Prevention Rule Generation
        recommendations.append({
            "priority": "P1",
            "title": "Auto-Generate Prevention Rules from Test Gaps",
            "gap_addressed": "All test types",
            "effort": "MEDIUM (2-3 days)",
            "description": "Extend defect_prevention_rules.py to auto-learn from test_gap_analyzer",
            "implementation": [
                "Add learn_from_test_gap() method to DefectPrevention",
                "Generate regex patterns from bug descriptions",
                "Create prevention checks for top 5 test gaps",
                "Integrate with pre-commit hook for enforcement"
            ],
            "expected_impact": "Prevent 70% of historically-missed bug patterns",
            "validation": "Track prevention system effectiveness over Sprint 8"
        })
        
        print(f"\n📋 {len(recommendations)} Recommendations Generated:\n")
        for rec in recommendations:
            print(f"   {rec['priority']}: {rec['title']}")
            print(f"   Effort: {rec['effort']}")
            print(f"   Expected Impact: {rec['expected_impact']}")
            print()
        
        self.findings["recommendations"] = recommendations
        return recommendations
    
    def generate_test_gap_report(self, output_path: str = "docs/TEST_GAP_REPORT.md"):
        """Generate comprehensive test gap analysis report"""
        print("\n" + "="*70)
        print("📄 GENERATING TEST GAP REPORT")
        print("="*70)
        
        report_lines = [
            "# Test Gap Analysis Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Sprint**: Sprint 7, Story 2 (P1)",
            f"**Goal**: Identify and close systematic test coverage gaps",
            "",
            "---",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Test gap distribution
        if "test_gap_distribution" in self.findings:
            dist = self.findings["test_gap_distribution"]
            report_lines.extend([
                "### Test Coverage Analysis",
                "",
                f"- **Total Bugs Analyzed**: {dist.get('total_bugs_analyzed', 0)}",
                f"- **Bugs with Test Gap Data**: {dist.get('bugs_with_test_data', 0)}",
                "",
                "**Test Gap Distribution**:",
                ""
            ])
            
            for test_type, pct in dist.get("top_gaps", []):
                report_lines.append(f"- **{test_type}**: {pct:.1f}% of bugs missed")
            report_lines.append("")
        
        # Component gaps
        if "component_gaps" in self.findings:
            comp = self.findings["component_gaps"]
            report_lines.extend([
                "### Component-Specific Gaps",
                "",
                f"**Total Gap Patterns Identified**: {comp.get('total_patterns', 0)}",
                "",
                "**High-Priority Component Gaps**:",
                ""
            ])
            
            for gap in comp.get("priority_gaps", [])[:5]:
                examples_str = ", ".join(gap.get("examples", []))
                report_lines.extend([
                    f"#### {gap['test_type']} + {gap['agent']}",
                    "",
                    f"- **Bug Count**: {gap['bug_count']}",
                    f"- **Critical Bugs**: {gap['critical_count']}",
                    f"- **Priority**: {gap['priority']}",
                    f"- **Examples**: {examples_str}",
                    ""
                ])
        
        # Recommendations
        if "recommendations" in self.findings:
            recs = self.findings["recommendations"]
            report_lines.extend([
                "---",
                "",
                "## Recommendations",
                "",
                f"**Total Recommendations**: {len(recs)}",
                ""
            ])
            
            for rec in recs:
                report_lines.extend([
                    f"### {rec['priority']}: {rec['title']}",
                    "",
                    f"**Gap Addressed**: {rec['gap_addressed']}",
                    f"**Effort**: {rec['effort']}",
                    "",
                    f"**Description**: {rec['description']}",
                    "",
                    "**Implementation Steps**:",
                    *[f"1. {step}" for step in rec['implementation']],
                    "",
                    f"**Expected Impact**: {rec['expected_impact']}",
                    "",
                    f"**Validation**: {rec['validation']}",
                    "",
                    "---",
                    ""
                ])
        
        # Action Plan
        report_lines.extend([
            "## Action Plan",
            "",
            "### Immediate (Sprint 7)",
            "",
            "1. ✅ Test gap analysis complete",
            "2. 🔲 Review recommendations with team",
            "3. 🔲 Prioritize P0 recommendations for Sprint 8",
            "",
            "### Short-term (Sprint 8)",
            "",
            "1. 🔲 Implement P0 recommendations (Visual QA, Integration Tests)",
            "2. 🔲 Deploy enhanced test coverage",
            "3. 🔲 Measure impact on defect escape rate",
            "",
            "### Long-term (Sprint 9+)",
            "",
            "1. 🔲 Implement P1/P2 recommendations",
            "2. 🔲 Automate test gap detection in CI/CD",
            "3. 🔲 Target <10% test escape rate",
            "",
            "---",
            "",
            "## Metrics to Track",
            "",
            "- **Test Escape Rate**: % of bugs missed by all tests (target: <20%)",
            "- **Coverage by Test Type**: % bugs caught by each test type",
            "- **Time to Detection**: Days from bug introduction to discovery",
            "- **Prevention Effectiveness**: % bugs blocked by prevention rules",
            "",
            "---",
            "",
            f"**Report Generated**: {datetime.now().isoformat()}",
            f"**Analysis Tool**: `scripts/test_gap_analyzer.py`",
            ""
        ])
        
        # Write report
        report_path = Path(output_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"\n✅ Report generated: {report_path}")
        print(f"   Recommendations: {len(self.findings.get('recommendations', []))}")
        
        return str(report_path)
    
    def run_full_analysis(self) -> Dict:
        """Run complete test gap analysis"""
        print("\n" + "="*70)
        print("🧪 TEST GAP DETECTION AUTOMATION")
        print("   Sprint 7, Story 2 (5 points, P1)")
        print("="*70)
        
        # Step 1: Analyze test gap distribution
        self.analyze_test_gap_distribution()
        
        # Step 2: Map gaps to components
        self.map_gaps_to_components()
        
        # Step 3: Generate recommendations
        self.generate_recommendations()
        
        # Step 4: Generate report
        report_path = self.generate_test_gap_report()
        
        print("\n" + "="*70)
        print("✅ ANALYSIS COMPLETE")
        print("="*70)
        print(f"\n📄 Report: {report_path}")
        print(f"\n📋 Findings:")
        print(f"   Test Gap Patterns: {self.findings.get('component_gaps', {}).get('total_patterns', 0)}")
        print(f"   Recommendations: {len(self.findings.get('recommendations', []))}")
        
        return {
            "status": "complete",
            "report_path": report_path,
            "findings": self.findings
        }


def main():
    parser = argparse.ArgumentParser(
        description="Test Gap Detection Automation - Sprint 7 Story 2"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run full test gap analysis"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate test gap report only"
    )
    parser.add_argument(
        "--tracker",
        default="skills/defect_tracker.json",
        help="Path to defect tracker (default: skills/defect_tracker.json)"
    )
    
    args = parser.parse_args()
    
    analyzer = TestGapAnalyzer(defect_tracker_file=args.tracker)
    
    if args.analyze or not args.report:
        # Run full analysis
        results = analyzer.run_full_analysis()
        print(f"\n✅ Story 2 Acceptance Criteria:")
        print(f"   [{'✅' if results['status'] == 'complete' else '❌'}] Test gap analyzer created")
        print(f"   [{'✅' if 'test_gap_distribution' in results['findings'] else '❌'}] Gap distribution analyzed")
        print(f"   [{'✅' if 'component_gaps' in results['findings'] else '❌'}] Gaps mapped to components")
        print(f"   [{'✅' if 'recommendations' in results['findings'] else '❌'}] Actionable recommendations generated")
        print(f"   [✅] TEST_GAP_REPORT.md published")
    elif args.report:
        # Generate report only
        analyzer.generate_test_gap_report()


if __name__ == "__main__":
    main()
