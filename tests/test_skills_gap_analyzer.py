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
