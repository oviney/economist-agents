#!/usr/bin/env python3
"""
Quality Dashboard Validation Tests

Sprint 12 Story 1 Task 3: Comprehensive validation tests for dashboard accuracy.

Tests validate:
1. Metrics accuracy against source data
2. Sprint trends rendering with 3-sprint comparison
3. Quality score calculation correctness
4. NO DATA handling when metrics unavailable
5. End-to-end dashboard generation
"""

import json

# Add parent directory to path for imports
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.quality_dashboard import QualityDashboard


class TestDashboardMetricsAccuracy:
    """Test that dashboard accurately reflects source data"""

    def test_agent_metrics_from_real_data(self, tmp_path):
        """Test that agent metrics are extracted from actual run data"""
        # Create test metrics file with real data structure
        metrics_file = tmp_path / "agent_metrics.json"
        test_data = {
            "runs": [
                {
                    "timestamp": "2026-01-04T10:00:00",
                    "agents": {
                        "writer_agent": {
                            "word_count": 1200,
                            "banned_phrases": 0,
                            "chart_embedded": True,
                        },
                        "editor_agent": {"gates_passed": 4, "gate_pass_rate": 80.0},
                        "graphics_agent": {
                            "visual_qa_pass_rate": 90.0,
                            "zone_violations": 0,
                        },
                        "research_agent": {
                            "verification_rate": 85.5,
                            "data_points": 12,
                        },
                    },
                }
            ]
        }
        metrics_file.write_text(json.dumps(test_data))

        # Mock the metrics file location
        with patch("agent_metrics.AgentMetrics._load_metrics", return_value=test_data):
            dashboard = QualityDashboard()
            summary = dashboard._build_agent_summary()

            # Validate real data is used (not baseline values)
            assert summary["writer"]["clean_rate"] == 100, (
                "Writer clean rate should be 100% (0 banned phrases)"
            )
            assert summary["writer"]["avg_word_count"] > 0, (
                "Word count should be greater than 0"
            )
            assert summary["editor"]["accuracy"] == 80.0, (
                "Editor accuracy should match gate_pass_rate"
            )
            assert summary["editor"]["avg_gates_passed"] == 4, (
                "Gates passed should match actual"
            )
            assert summary["graphics"]["visual_qa_pass_rate"] == 90.0, (
                "Visual QA should match actual"
            )
            assert summary["research"]["verification_rate"] == 85.5, (
                "Verification rate should match actual"
            )

    def test_no_data_handling(self, tmp_path):
        """Test that NO DATA is displayed when metrics unavailable"""
        # Create empty metrics file
        metrics_file = tmp_path / "agent_metrics.json"
        test_data = {"runs": []}
        metrics_file.write_text(json.dumps(test_data))

        with patch("agent_metrics.AgentMetrics._load_metrics", return_value=test_data):
            dashboard = QualityDashboard()
            summary = dashboard._build_agent_summary()

            # All percentages should be None when no data
            assert summary["writer"]["clean_rate"] is None, (
                "Should be None when no data"
            )
            assert summary["editor"]["accuracy"] is None, "Should be None when no data"
            assert summary["graphics"]["visual_qa_pass_rate"] is None, (
                "Should be None when no data"
            )
            assert summary["writer"]["avg_word_count"] is None, (
                "Word count should be None when no data"
            )

    def test_no_baseline_fallback(self, tmp_path):
        """Test that baseline values (75%, 60%, etc.) are NOT used"""
        # Empty data
        test_data = {"runs": []}

        with patch("agent_metrics.AgentMetrics._load_metrics", return_value=test_data):
            dashboard = QualityDashboard()
            summary = dashboard._build_agent_summary()

            # Ensure NO baseline values are present
            assert summary["writer"]["clean_rate"] != 75, "Should not use baseline 75%"
            assert summary["editor"]["accuracy"] != 60, "Should not use baseline 60%"
            assert summary["graphics"]["visual_qa_pass_rate"] != 75, (
                "Should not use baseline 75%"
            )
            assert summary["research"]["verification_rate"] != 80, (
                "Should not use baseline 80%"
            )


class TestSprintTrendsRendering:
    """Test that sprint trends render correctly with multi-sprint data"""

    def test_sprint_trends_with_three_sprints(self, tmp_path):
        """Test that sprint trends table renders with 3 sprints"""
        history_file = tmp_path / "sprint_history.json"
        test_history = {
            "baseline_sprint": 5,
            "sprints": [
                {
                    "sprint_id": 5,
                    "metrics": {
                        "quality_score": 67,
                        "defect_escape_rate": 50.0,
                        "points_delivered": 14,
                    },
                },
                {
                    "sprint_id": 10,
                    "metrics": {
                        "quality_score": 72,
                        "defect_escape_rate": 45.0,
                        "points_delivered": 8,
                    },
                },
                {
                    "sprint_id": 11,
                    "metrics": {
                        "quality_score": 75,
                        "defect_escape_rate": 40.0,
                        "points_delivered": 13,
                    },
                },
            ],
        }
        history_file.write_text(json.dumps(test_history))

        with patch(
            "scripts.quality_dashboard.QualityDashboard._load_sprint_history",
            return_value=test_history,
        ):
            dashboard = QualityDashboard()
            trends = dashboard._render_sprint_trends()

            # Should contain table with 3 sprints
            assert "Sprint 5" in trends, "Should include Sprint 5"
            assert "Sprint 10" in trends, "Should include Sprint 10"
            assert "Sprint 11" in trends, "Should include Sprint 11"
            assert "67" in trends, "Should show Sprint 5 quality score"
            assert "72" in trends, "Should show Sprint 10 quality score"
            assert "75" in trends, "Should show Sprint 11 quality score"

    def test_sprint_trends_insufficient_data(self, tmp_path):
        """Test that helpful message shown when <2 sprints available"""
        history_file = tmp_path / "sprint_history.json"
        test_history = {"sprints": [{"sprint_id": 5, "metrics": {"quality_score": 67}}]}
        history_file.write_text(json.dumps(test_history))

        with patch(
            "scripts.quality_dashboard.QualityDashboard._load_sprint_history",
            return_value=test_history,
        ):
            dashboard = QualityDashboard()
            trends = dashboard._render_sprint_trends()

            # Should show helpful message
            assert "Need at least 2 sprints" in trends, (
                "Should explain minimum requirement"
            )
            assert "1 sprint" in trends, "Should show current count"

    def test_sprint_trends_no_history(self):
        """Test that helpful message shown when no sprint history exists"""
        with patch(
            "scripts.quality_dashboard.QualityDashboard._load_sprint_history",
            return_value={"sprints": []},
        ):
            dashboard = QualityDashboard()
            trends = dashboard._render_sprint_trends()

            assert "No sprint history available" in trends, (
                "Should show no data message"
            )
            assert "--save-sprint" in trends, "Should suggest how to start tracking"


class TestQualityScoreCalculation:
    """Test that quality score calculation is correct"""

    def test_quality_score_formula(self):
        """Test quality score calculation against known values"""
        # Mock defect tracker with known data
        mock_defects = {
            "summary": {
                "defect_escape_rate": 40.0,
                "avg_time_to_detect_days": 3.5,
                "avg_time_to_resolve_days": 2.0,
            }
        }

        with patch(
            "scripts.defect_tracker.DefectTracker.get_metrics",
            return_value=mock_defects,
        ):
            dashboard = QualityDashboard()
            agent_summary = {
                "writer": {"clean_rate": 85.0},
                "editor": {"accuracy": 90.0},
                "graphics": {"visual_qa_pass_rate": 85.0},
            }
            score = dashboard._calculate_quality_score(
                mock_defects["summary"], agent_summary
            )

            # Actual formula uses threshold-based penalties:
            # Defect escape: 40% > 20% → penalty = min(30, (40-20)*1.5) = 30
            # TTD: 3.5 days < 7 days → no penalty
            # Score: 100 - 30 = 70
            expected = 70

            assert score == expected, f"Quality score should be {expected}"

    def test_quality_score_with_missing_metrics(self):
        """Test quality score when some metrics are missing"""
        mock_defects = {
            "summary": {
                "defect_escape_rate": 30.0,
                "avg_time_to_detect_days": None,  # Missing
                "avg_time_to_resolve_days": 1.5,
            }
        }

        with patch(
            "scripts.defect_tracker.DefectTracker.get_metrics",
            return_value=mock_defects,
        ):
            dashboard = QualityDashboard()
            agent_summary = {
                "writer": {"clean_rate": 85.0},
                "editor": {"accuracy": 90.0},
                "graphics": {"visual_qa_pass_rate": 85.0},
            }
            score = dashboard._calculate_quality_score(
                mock_defects["summary"], agent_summary
            )

            # Actual formula with None TTD:
            # Defect escape: 30% > 20% → penalty = min(30, (30-20)*1.5) = 15
            # TTD: None → no penalty
            # TTR: 1.5 days → no penalty (threshold not in formula)
            # Score: 100 - 15 = 85
            expected = 85

            assert score == expected, "Should handle missing metrics"


class TestDashboardGeneration:
    """End-to-end dashboard generation tests"""

    def test_dashboard_generates_without_errors(self, tmp_path):
        """Test that dashboard generates successfully"""
        # Mock minimal data
        with (
            patch(
                "agent_metrics.AgentMetrics._load_metrics",
                return_value={"runs": []},
            ),
            patch(
                "scripts.defect_tracker.DefectTracker.get_metrics",
                return_value={
                    "summary": {"defect_escape_rate": 40.0, "total_bugs": 10}
                },
            ),
        ):
            dashboard = QualityDashboard()
            output = dashboard.generate_dashboard()

            # Should contain key sections
            assert "Quality Engineering Dashboard" in output
            assert "## 🐛 Defect Metrics" in output
            assert "## 🤖 Agent Performance" in output
            assert "Sprint-Over-Sprint Trends" in output

    def test_dashboard_validation_against_source_files(self):
        """Test that dashboard data matches source JSON files"""
        # Load actual files
        project_root = Path(__file__).parent.parent

        # Load agent metrics
        metrics_file = project_root / "skills" / "agent_metrics.json"
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics_data = json.load(f)

            # Verify dashboard uses this data
            dashboard = QualityDashboard()
            summary = dashboard._build_agent_summary()

            # If runs exist, verify they're being used
            if metrics_data.get("runs"):
                latest = metrics_data["runs"][-1]
                if "agents" in latest and "writer_agent" in latest["agents"]:
                    # Dashboard should reflect actual data, not baseline
                    assert summary["writer"]["articles"] == len(metrics_data["runs"]), (
                        "Article count should match runs array length"
                    )


# Fixtures
@pytest.fixture
def tmp_path():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
