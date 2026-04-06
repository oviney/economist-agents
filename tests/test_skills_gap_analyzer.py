#!/usr/bin/env python3
"""
Test suite for Skills Gap Analyzer

Validates that agent performance analysis produces accurate
skill assessments, hiring recommendations, and training priorities.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.skills_gap_analyzer import SkillsGapAnalyzer


class TestSkillsGapAnalyzer:
    """Test skills gap analysis functionality"""

    def setup_method(self):
        """Create test fixtures"""
        self.test_tracker_data = {
            "version": "1.0",
            "bugs": [
                {
                    "id": "BUG-TEST-001",
                    "severity": "critical",
                    "component": "writer_agent",
                    "responsible_agent": "writer_agent",
                    "status": "open",
                    "root_cause": "prompt_engineering",
                    "description": "Test bug for requirements adherence",
                },
                {
                    "id": "BUG-TEST-002",
                    "severity": "high",
                    "component": "writer_agent",
                    "responsible_agent": "writer_agent",
                    "status": "open",
                    "root_cause": "validation_gap",
                    "description": "Test bug for CMS knowledge",
                },
                {
                    "id": "BUG-TEST-003",
                    "severity": "low",
                    "component": "research_agent",
                    "responsible_agent": "research_agent",
                    "status": "open",
                    "root_cause": "code_logic",
                    "description": "Test bug for research agent",
                },
            ],
        }

    def test_initialization(self):
        """Test analyzer initializes with defect tracker"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assert len(analyzer.bugs) == 3
            assert analyzer.tracker_data["version"] == "1.0"
            print("✓ test_initialization PASSED")
        finally:
            Path(temp_path).unlink()

    def test_role_mapping(self):
        """Test agent-to-role mapping"""
        analyzer = SkillsGapAnalyzer.__new__(SkillsGapAnalyzer)

        assert analyzer.ROLE_MAPPING["writer_agent"] == "Content Writer"
        assert analyzer.ROLE_MAPPING["research_agent"] == "Research Analyst"
        assert analyzer.ROLE_MAPPING["editor_agent"] == "Senior Editor"
        assert analyzer.ROLE_MAPPING["graphics_agent"] == "Data Visualization Designer"

        print("✓ test_role_mapping PASSED")

    def test_skills_rubric(self):
        """Test skills rubric structure"""
        analyzer = SkillsGapAnalyzer.__new__(SkillsGapAnalyzer)

        # Check Content Writer rubric
        content_writer = analyzer.SKILLS_RUBRIC["Content Writer"]
        assert "requirements_adherence" in content_writer
        assert content_writer["requirements_adherence"]["weight"] == 0.4
        assert content_writer["requirements_adherence"]["junior"] == 50
        assert content_writer["requirements_adherence"]["mid"] == 75
        assert content_writer["requirements_adherence"]["senior"] == 95

        # Check all rubrics have weights that sum to 1.0
        for role, skills in analyzer.SKILLS_RUBRIC.items():
            total_weight = sum(skill["weight"] for skill in skills.values())
            assert abs(total_weight - 1.0) < 0.01, f"{role} weights don't sum to 1.0"

        print("✓ test_skills_rubric PASSED")

    def test_analyze_agent_performance(self):
        """Test single agent analysis"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            result = analyzer.analyze_agent_performance("writer_agent")

            # Validate structure
            assert "role" in result
            assert "bugs_count" in result
            assert "critical_bugs" in result
            assert "skill_scores" in result
            assert "overall_score" in result
            assert "skill_level" in result
            assert "top_gap" in result
            assert "recommendation" in result

            # Validate data
            assert result["role"] == "Content Writer"
            assert result["bugs_count"] == 2
            assert result["critical_bugs"] == 1
            assert result["skill_level"] in ["junior", "mid", "senior"]

            print("✓ test_analyze_agent_performance PASSED")
        finally:
            Path(temp_path).unlink()

    def test_skill_level_determination(self):
        """Test skill level classification"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)

            # Test boundaries
            assert analyzer._determine_skill_level(95) == "senior"
            assert analyzer._determine_skill_level(85) == "senior"
            assert analyzer._determine_skill_level(75) == "mid"
            assert analyzer._determine_skill_level(65) == "mid"
            assert analyzer._determine_skill_level(50) == "junior"
            assert analyzer._determine_skill_level(20) == "junior"

            print("✓ test_skill_level_determination PASSED")
        finally:
            Path(temp_path).unlink()

    def test_generate_team_assessment(self):
        """Test complete team assessment generation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()

            # Validate structure
            assert "by_role" in assessment
            assert "hiring_recommendations" in assessment
            assert "training_priorities" in assessment
            assert "summary" in assessment
            assert "generated_at" in assessment

            # Validate summary
            summary = assessment["summary"]
            assert "total_agents_analyzed" in summary
            assert "total_bugs" in summary
            assert "critical_bugs" in summary
            assert "avg_skill_level" in summary

            # Validate data
            assert summary["total_bugs"] == 3
            assert summary["critical_bugs"] == 1

            print("✓ test_generate_team_assessment PASSED")
        finally:
            Path(temp_path).unlink()

    def test_hiring_recommendations(self):
        """Test hiring recommendation generation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()

            hiring_recs = assessment["hiring_recommendations"]

            # Should have recommendations for writer_agent with critical bug
            if hiring_recs:
                rec = hiring_recs[0]
                assert "priority" in rec
                assert "role" in rec
                assert "reason" in rec
                assert "current_level" in rec
                assert "target_level" in rec

                # Writer agent with 1 critical bug should be URGENT
                assert rec["priority"] in ["URGENT", "CONSIDER"]

            print("✓ test_hiring_recommendations PASSED")
        finally:
            Path(temp_path).unlink()

    def test_training_priorities(self):
        """Test training priority generation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()

            training = assessment["training_priorities"]

            # Should have training priorities for agents with bugs
            if training:
                priority = training[0]
                assert "role" in priority
                assert "skill_gap" in priority
                assert "current_score" in priority
                assert "target_score" in priority
                assert "impact_score" in priority
                assert "training_type" in priority

                # Should be sorted by impact (descending)
                if len(training) > 1:
                    assert training[0]["impact_score"] >= training[1]["impact_score"]

            print("✓ test_training_priorities PASSED")
        finally:
            Path(temp_path).unlink()

    def test_markdown_formatting(self):
        """Test markdown table formatting"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()
            markdown = analyzer.format_team_assessment_table(
                assessment, format="markdown"
            )

            # Validate markdown structure
            assert "# 👥 Team Skills Assessment" in markdown
            assert "## Executive Summary" in markdown
            assert "## By Role Performance" in markdown
            assert "## Hiring Recommendations" in markdown
            assert "## Training Priorities" in markdown
            assert "|" in markdown  # Table syntax
            assert "---" in markdown  # Table separator

            print("✓ test_markdown_formatting PASSED")
        finally:
            Path(temp_path).unlink()

    def test_text_formatting(self):
        """Test plain text formatting"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()
            text = analyzer.format_team_assessment_table(assessment, format="text")

            # Validate text structure
            assert "TEAM SKILLS ASSESSMENT" in text
            assert "Total Agents:" in text
            assert "BY ROLE PERFORMANCE" in text
            assert "HIRING RECOMMENDATIONS" in text
            assert "TRAINING PRIORITIES" in text
            assert "=" * 80 in text  # Border lines

            print("✓ test_text_formatting PASSED")
        finally:
            Path(temp_path).unlink()

    def test_calculate_velocity_impact(self):
        """Test velocity impact calculation (Critical Question #5)"""
        tracker_data = {
            "version": "1.0",
            "bugs": [
                {
                    "id": "BUG-V-001",
                    "severity": "critical",
                    "responsible_agent": "writer_agent",
                    "status": "open",
                    "root_cause": "prompt_engineering",
                    "description": "Critical velocity bug",
                    "time_to_resolve_days": None,
                },
                {
                    "id": "BUG-V-002",
                    "severity": "high",
                    "responsible_agent": "writer_agent",
                    "status": "fixed",
                    "root_cause": "validation_gap",
                    "description": "Fixed bug with TTR",
                    "time_to_resolve_days": 3,
                },
                {
                    "id": "BUG-V-003",
                    "severity": "medium",
                    "responsible_agent": "research_agent",
                    "status": "open",
                    "root_cause": "code_logic",
                    "description": "Research bug",
                    "time_to_resolve_days": None,
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            result = analyzer.calculate_velocity_impact()

            # Validate top-level structure
            assert "by_role" in result
            assert "total_velocity_loss_days" in result
            assert "total_rework_cost_points" in result
            assert "highest_impact_role" in result

            # writer_agent should have role, risk, open_bugs, etc.
            by_role = result["by_role"]
            assert "writer_agent" in by_role
            writer = by_role["writer_agent"]
            assert writer["role"] == "Content Writer"
            assert "velocity_risk" in writer
            assert writer["velocity_risk"] in ("low", "medium", "high", "critical")
            assert writer["open_bugs"] == 1  # BUG-V-001 is open
            assert writer["avg_resolution_days"] == 3.0  # from BUG-V-002

            # research_agent open bug
            assert "research_agent" in by_role
            research = by_role["research_agent"]
            assert research["open_bugs"] == 1

            # Totals should be positive
            assert result["total_velocity_loss_days"] > 0
            assert result["total_rework_cost_points"] > 0

            print("✓ test_calculate_velocity_impact PASSED")
        finally:
            Path(temp_path).unlink()

    def test_correlate_skills_with_quality(self):
        """Test skills-quality correlation (Critical Question #5)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            result = analyzer.correlate_skills_with_quality()

            # Validate structure
            assert "correlations" in result
            assert "insight" in result
            assert "data_quality" in result

            # Data quality should be 'limited' with only 3 bugs
            assert result["data_quality"] == "limited"

            # Should have correlations for agents with bugs
            corrs = result["correlations"]
            assert len(corrs) > 0

            # Validate correlation entry structure
            c = corrs[0]
            assert "agent" in c
            assert "role" in c
            assert "skill_score" in c
            assert "defect_rate" in c
            assert "fix_rate" in c
            assert "quality_grade" in c
            assert "correlation_label" in c

            # Quality grades should be valid
            for corr in corrs:
                assert corr["quality_grade"] in ("A", "B", "C", "D", "F")
                assert corr["correlation_label"] in ("strong", "moderate", "weak")
                assert 0 <= corr["skill_score"] <= 100
                assert 0 <= corr["fix_rate"] <= 100

            # Correlations sorted by skill_score ascending (worst first)
            scores = [c["skill_score"] for c in corrs]
            assert scores == sorted(scores)

            # Insight should be a non-empty string
            assert len(result["insight"]) > 0

            print("✓ test_correlate_skills_with_quality PASSED")
        finally:
            Path(temp_path).unlink()

    def test_velocity_quality_in_team_assessment(self):
        """Test that generate_team_assessment includes velocity and quality correlation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()

            # New fields should be present
            assert "velocity_impact" in assessment
            assert "quality_correlation" in assessment

            # Validate velocity_impact structure
            vi = assessment["velocity_impact"]
            assert "by_role" in vi
            assert "total_velocity_loss_days" in vi
            assert "total_rework_cost_points" in vi
            assert "highest_impact_role" in vi

            # Validate quality_correlation structure
            qc = assessment["quality_correlation"]
            assert "correlations" in qc
            assert "insight" in qc
            assert "data_quality" in qc

            print("✓ test_velocity_quality_in_team_assessment PASSED")
        finally:
            Path(temp_path).unlink()

    def test_markdown_includes_velocity_quality_sections(self):
        """Test markdown output includes velocity impact and quality correlation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()
            markdown = analyzer.format_team_assessment_table(
                assessment, format="markdown"
            )

            assert "## Velocity Impact" in markdown
            assert "## Skills-Quality Correlation" in markdown
            assert "Velocity Loss" in markdown
            assert "Defect Rate" in markdown

            print("✓ test_markdown_includes_velocity_quality_sections PASSED")
        finally:
            Path(temp_path).unlink()

    def test_text_includes_velocity_quality_sections(self):
        """Test plain text output includes velocity impact and quality correlation"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.test_tracker_data, f)
            temp_path = f.name

        try:
            analyzer = SkillsGapAnalyzer(temp_path)
            assessment = analyzer.generate_team_assessment()
            text = analyzer.format_team_assessment_table(assessment, format="text")

            assert "VELOCITY IMPACT" in text
            assert "SKILLS-QUALITY CORRELATION" in text
            assert "Velocity Loss:" in text
            assert "Defect Rate:" in text

            print("✓ test_text_includes_velocity_quality_sections PASSED")
        finally:
            Path(temp_path).unlink()


def run_tests():
    """Run all tests"""
    test_class = TestSkillsGapAnalyzer()

    tests = [
        "test_initialization",
        "test_role_mapping",
        "test_skills_rubric",
        "test_analyze_agent_performance",
        "test_skill_level_determination",
        "test_generate_team_assessment",
        "test_hiring_recommendations",
        "test_training_priorities",
        "test_markdown_formatting",
        "test_text_formatting",
        "test_calculate_velocity_impact",
        "test_correlate_skills_with_quality",
        "test_velocity_quality_in_team_assessment",
        "test_markdown_includes_velocity_quality_sections",
        "test_text_includes_velocity_quality_sections",
    ]

    print("\n" + "=" * 70)
    print("Skills Gap Analyzer Test Suite")
    print("=" * 70 + "\n")

    passed = 0
    failed = 0

    for test_name in tests:
        try:
            test_class.setup_method()
            test_method = getattr(test_class, test_name)
            test_method()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
