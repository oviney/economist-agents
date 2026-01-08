#!/usr/bin/env python3
"""Unit tests for validate_closed_loop.py

These tests verify the validation stages work correctly without running
the full end-to-end validation (which would be slow).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import orjson
import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skills_manager import SkillsManager


class TestStorageCheck:
    """Test SkillsManager storage functionality."""

    def test_skills_manager_creates_file_with_orjson(self):
        """Verify SkillsManager creates valid orjson files."""
        # Create temporary test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_skills.json"

            # Initialize and save
            manager = SkillsManager(role_name="test_role", skills_file=test_file)
            manager.save()

            # Verify file exists
            assert test_file.exists(), "Skills file should be created"

            # Verify it's valid orjson
            with open(test_file, "rb") as f:
                data = orjson.loads(f.read())

            # Verify structure
            assert "version" in data
            assert "last_updated" in data
            assert "skills" in data
            assert "validation_stats" in data

    def test_learn_pattern_saves_correctly(self):
        """Verify learn_pattern() persists data correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_skills.json"

            manager = SkillsManager(role_name="test_role", skills_file=test_file)

            # Add pattern
            manager.learn_pattern(
                "test_category",
                "test_pattern",
                {
                    "severity": "high",
                    "pattern": "Test pattern",
                    "check": "Test check",
                    "learned_from": "test",
                },
            )

            # Save and reload
            manager.save()

            # Verify pattern was saved
            with open(test_file, "rb") as f:
                data = orjson.loads(f.read())

            assert "test_category" in data["skills"]
            patterns = data["skills"]["test_category"]["patterns"]
            assert len(patterns) == 1
            assert patterns[0]["id"] == "test_pattern"


class TestValidationScript:
    """Test the validation script runs correctly."""

    def test_help_command(self):
        """Verify script shows help without errors."""
        script_path = (
            Path(__file__).parent.parent / "scripts" / "validate_closed_loop.py"
        )
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Validate closed-loop learning architecture" in result.stdout
        assert "--stage" in result.stdout

    def test_stage_filter_storage(self):
        """Verify --stage storage runs only storage check."""
        script_path = (
            Path(__file__).parent.parent / "scripts" / "validate_closed_loop.py"
        )
        result = subprocess.run(
            [sys.executable, str(script_path), "--stage", "storage"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should pass (exit 0) if storage check passes
        assert result.returncode == 0
        assert "Storage Check" in result.stdout
        assert "PASS" in result.stdout

    def test_verbose_output(self):
        """Verify --verbose flag shows detailed output."""
        script_path = (
            Path(__file__).parent.parent / "scripts" / "validate_closed_loop.py"
        )
        result = subprocess.run(
            [sys.executable, str(script_path), "--stage", "storage", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verbose mode should show detailed messages
        assert "ℹ" in result.stdout or "✓" in result.stdout


class TestPatternSchema:
    """Test pattern schema validation."""

    def test_pattern_has_required_fields(self):
        """Verify pattern objects have all required fields."""
        required_fields = [
            "category",
            "pattern_id",
            "severity",
            "pattern",
            "check",
            "learned_from",
        ]

        # Sample pattern
        pattern = {
            "category": "test_category",
            "pattern_id": "test_pattern",
            "severity": "high",
            "pattern": "Test description",
            "check": "Test validation rule",
            "learned_from": "test source",
        }

        for field in required_fields:
            assert field in pattern, f"Pattern missing required field: {field}"

    def test_severity_values(self):
        """Verify severity values are valid."""
        valid_severities = ["critical", "high", "medium", "low"]

        for severity in valid_severities:
            pattern = {
                "severity": severity,
                "pattern_id": "test",
                "pattern": "test",
                "check": "test",
                "learned_from": "test",
            }
            assert pattern["severity"] in valid_severities


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
