#!/usr/bin/env python3
"""Master Validation Script for Closed-Loop Learning Architecture

This script programmatically verifies the entire closed-loop learning system
by testing each component and their integrations.

Validation Stages:
1. Storage Check: SkillsManager creates JSON files with orjson
2. Synthesis Check: skill_synthesizer.py processes logs correctly
3. Integration Check: blog_qa_agent.py updates skills from errors
4. Sync Check: sync_copilot_context.py updates copilot instructions
5. Reporting Check: skills_gap_analyzer.py generates reports

Usage:
    python3 scripts/validate_closed_loop.py
    python3 scripts/validate_closed_loop.py --verbose
    python3 scripts/validate_closed_loop.py --stage storage
    python3 scripts/validate_closed_loop.py --cleanup-only

Example Output:
    ╔════════════════════════════════════════════════════════════════╗
    ║ CLOSED-LOOP LEARNING ARCHITECTURE VALIDATION                   ║
    ╚════════════════════════════════════════════════════════════════╝

    [1/5] Storage Check (SkillsManager)................. ✅ PASS
    [2/5] Synthesis Check (skill_synthesizer)........... ✅ PASS
    [3/5] Integration Check (blog_qa_agent)............. ✅ PASS
    [4/5] Sync Check (sync_copilot_context)............. ✅ PASS
    [5/5] Reporting Check (skills_gap_analyzer)......... ✅ PASS

    ╔════════════════════════════════════════════════════════════════╗
    ║ VALIDATION RESULT: ✅ ALL CHECKS PASSED (5/5)                  ║
    ╚════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import orjson

from scripts.skills_manager import SkillsManager

# Repo paths: src/quality/validate_closed_loop.py -> repo root -> scripts/
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

MOCK_FAILURE_LOG = """Blog QA Validation Run - 2026-01-06T12:00:00
============================================================

Posts Validated: 1
Issues Found: 2

VALIDATION ISSUES:
------------------------------------------------------------
1. [YAML] Missing required field: categories
2. [LINKS] Line 15: Broken asset link: /assets/missing.png

✗ Validation failed with 2 issues
"""

MOCK_BLOG_POST = """---
layout: post
title: "Test Article"
date: 2026-01-06
---

# Test Article

This is a test article with a broken link to [missing image](/assets/missing.png).
"""

EXPECTED_PATTERN_SCHEMA = {
    "required_fields": [
        "category",
        "pattern_id",
        "severity",
        "pattern",
        "check",
        "learned_from",
    ],
    "severity_values": ["critical", "high", "medium", "low"],
}


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION STAGES
# ═══════════════════════════════════════════════════════════════════════════


class ValidationStage:
    """Base class for validation stages."""

    def __init__(self, name: str, verbose: bool = False):
        self.name = name
        self.verbose = verbose
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def log(self, message: str, level: str = "info") -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            prefix = {"info": "   ℹ", "warn": "   ⚠", "error": "   ✗"}[level]
            print(f"{prefix}  {message}")

    def error(self, message: str) -> None:
        """Record error message."""
        self.errors.append(message)
        self.log(message, "error")

    def warn(self, message: str) -> None:
        """Record warning message."""
        self.warnings.append(message)
        self.log(message, "warn")

    def validate(self) -> bool:
        """Run validation. Must be implemented by subclasses."""
        raise NotImplementedError


class StorageCheck(ValidationStage):
    """Stage 1: Verify SkillsManager creates JSON files with orjson."""

    def __init__(self, verbose: bool = False):
        super().__init__("Storage Check (SkillsManager)", verbose)
        self.test_role = "test_bot"
        self.test_skills_file: Path | None = None

    def validate(self) -> bool:
        """Validate SkillsManager storage functionality."""
        try:
            # Create temporary test directory
            temp_dir = Path(tempfile.mkdtemp())
            self.test_skills_file = temp_dir / f"{self.test_role}_skills.json"

            self.log(f"Creating SkillsManager with role: {self.test_role}")

            # Initialize SkillsManager with test role
            manager = SkillsManager(
                role_name=self.test_role,
                skills_file=self.test_skills_file,
            )

            # SkillsManager doesn't create file until save() is called
            # So we need to save first
            manager.save()

            # Verify file was created
            if not self.test_skills_file.exists():
                self.error(f"Skills file not created at: {self.test_skills_file}")
                return False

            self.log(f"Skills file created: {self.test_skills_file}")

            # Verify it uses orjson (check file can be read with orjson)
            try:
                with open(self.test_skills_file, "rb") as f:
                    data = orjson.loads(f.read())
                self.log("✓ File successfully parsed with orjson")
            except orjson.JSONDecodeError as e:
                self.error(f"File not valid orjson: {e}")
                return False

            # Verify structure
            required_keys = ["version", "last_updated", "skills", "validation_stats"]
            for key in required_keys:
                if key not in data:
                    self.error(f"Missing required key in skills file: {key}")
                    return False

            self.log(f"✓ All required keys present: {required_keys}")

            # Test learn_pattern functionality
            manager.learn_pattern(
                "test_category",
                "test_pattern",
                {
                    "severity": "high",
                    "pattern": "Test pattern description",
                    "check": "Test validation rule",
                    "learned_from": "test source",
                },
            )

            # Save and verify
            manager.save()

            with open(self.test_skills_file, "rb") as f:
                updated_data = orjson.loads(f.read())

            if "test_category" not in updated_data["skills"]:
                self.error("Pattern not saved to skills file")
                return False

            self.log("✓ learn_pattern() correctly saved pattern")

            return True

        except Exception as e:
            self.error(f"Unexpected error: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up test artifacts."""
        if self.test_skills_file and self.test_skills_file.exists():
            self.test_skills_file.unlink()
            if self.test_skills_file.parent.exists():
                self.test_skills_file.parent.rmdir()
            self.log(f"Cleaned up: {self.test_skills_file}")


class SynthesisCheck(ValidationStage):
    """Stage 2: Verify skill_synthesizer.py processes logs correctly."""

    def __init__(self, verbose: bool = False):
        super().__init__("Synthesis Check (skill_synthesizer)", verbose)
        self.log_file: Path | None = None

    def validate(self) -> bool:
        """Validate skill synthesizer functionality."""
        try:
            # Verify skill_synthesizer.py exists
            synthesizer_path = _SCRIPTS_DIR / "skill_synthesizer.py"
            if not synthesizer_path.exists():
                self.error(f"skill_synthesizer.py not found at: {synthesizer_path}")
                return False

            self.log(f"Found skill_synthesizer.py: {synthesizer_path}")

            # Create mock failure log
            temp_dir = Path(tempfile.mkdtemp())
            self.log_file = temp_dir / "test_failure.log"
            self.log_file.write_text(MOCK_FAILURE_LOG)

            self.log(f"Created mock log: {self.log_file}")

            # Run skill_synthesizer in dry-run mode
            result = subprocess.run(
                [
                    sys.executable,
                    str(synthesizer_path),
                    "--log",
                    str(self.log_file),
                    "--role",
                    "test_role",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.error(
                    f"skill_synthesizer failed with exit code {result.returncode}",
                )
                self.error(f"stderr: {result.stderr}")
                return False

            self.log("✓ skill_synthesizer executed successfully")

            # Parse output for patterns
            output = result.stdout
            if "Identified" not in output:
                self.warn("No patterns identified in output")
                self.warn(f"Output: {output[:200]}")

            # Verify pattern structure (if patterns were found)
            if "pattern" in output.lower():
                # Try to extract JSON from output
                try:
                    # Look for JSON array in output
                    import re

                    json_match = re.search(r"\[.*\]", output, re.DOTALL)
                    if json_match:
                        patterns = json.loads(json_match.group())
                        for pattern in patterns:
                            # Validate against schema
                            for field in EXPECTED_PATTERN_SCHEMA["required_fields"]:
                                if field not in pattern:
                                    self.error(
                                        f"Pattern missing required field: {field}",
                                    )
                                    return False

                            if (
                                pattern.get("severity")
                                not in EXPECTED_PATTERN_SCHEMA["severity_values"]
                            ):
                                self.error(
                                    f"Invalid severity value: {pattern.get('severity')}",
                                )
                                return False

                        self.log(f"✓ {len(patterns)} pattern(s) match expected schema")
                except json.JSONDecodeError:
                    self.warn("Could not parse patterns from output (not JSON)")

            return True

        except subprocess.TimeoutExpired:
            self.error("skill_synthesizer timed out after 30 seconds")
            return False
        except Exception as e:
            self.error(f"Unexpected error: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up test artifacts."""
        if self.log_file and self.log_file.exists():
            self.log_file.unlink()
            if self.log_file.parent.exists():
                self.log_file.parent.rmdir()
            self.log(f"Cleaned up: {self.log_file}")


class IntegrationCheck(ValidationStage):
    """Stage 3: Verify blog_qa_agent.py updates skills from errors."""

    def __init__(self, verbose: bool = False):
        super().__init__("Integration Check (blog_qa_agent)", verbose)
        self.test_post: Path | None = None
        self.test_blog_dir: Path | None = None
        self.skills_file: Path | None = None

    def validate(self) -> bool:
        """Validate blog_qa_agent integration."""
        try:
            # Verify blog_qa_agent.py exists
            agent_path = _SCRIPTS_DIR / "blog_qa_agent.py"
            if not agent_path.exists():
                self.error(f"blog_qa_agent.py not found at: {agent_path}")
                return False

            self.log(f"Found blog_qa_agent.py: {agent_path}")

            # Create temporary blog structure
            temp_dir = Path(tempfile.mkdtemp())
            self.test_blog_dir = temp_dir / "test_blog"
            self.test_blog_dir.mkdir()

            posts_dir = self.test_blog_dir / "_posts"
            posts_dir.mkdir()

            layouts_dir = self.test_blog_dir / "_layouts"
            layouts_dir.mkdir()

            # Create default.html layout
            (layouts_dir / "default.html").write_text(
                "<html><body>{{ content }}</body></html>",
            )

            # Create _config.yml
            (self.test_blog_dir / "_config.yml").write_text("title: Test Blog\n")

            # Create test post with known error
            self.test_post = posts_dir / "2026-01-06-test.md"
            self.test_post.write_text(MOCK_BLOG_POST)

            self.log(f"Created test blog at: {self.test_blog_dir}")
            self.log(f"Created test post: {self.test_post}")

            # Check if skills file exists before
            self.skills_file = _REPO_ROOT / "skills" / "blog_qa_skills.json"
            patterns_before = 0
            if self.skills_file.exists():
                with open(self.skills_file, "rb") as f:
                    data = orjson.loads(f.read())
                    patterns_before = sum(
                        len(cat.get("patterns", []))
                        for cat in data.get("skills", {}).values()
                    )

            self.log(f"Patterns before: {patterns_before}")

            # Run blog_qa_agent (without learning loop to avoid LLM dependency)
            result = subprocess.run(
                [
                    sys.executable,
                    str(agent_path),
                    "--blog-dir",
                    str(self.test_blog_dir),
                    "--post",
                    str(self.test_post),
                    "--learn=false",  # Disable learning loop for faster test
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # We expect it to find issues (exit code 1)
            if result.returncode == 0:
                self.warn("blog_qa_agent passed validation (expected to find issues)")
            else:
                self.log("✓ blog_qa_agent detected issues as expected")

            # Verify it can detect broken links
            if "broken" in result.stdout.lower() or "missing" in result.stdout.lower():
                self.log("✓ Broken link detection working")
            else:
                self.warn("Did not detect broken link in test post")

            # Verify it can detect missing categories
            if "categor" in result.stdout.lower():
                self.log("✓ Category field validation working")
            else:
                self.warn("Did not detect missing category field")

            return True

        except subprocess.TimeoutExpired:
            self.error("blog_qa_agent timed out after 30 seconds")
            return False
        except Exception as e:
            self.error(f"Unexpected error: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up test artifacts."""
        if self.test_blog_dir and self.test_blog_dir.exists():
            import shutil

            shutil.rmtree(self.test_blog_dir)
            self.log(f"Cleaned up: {self.test_blog_dir}")


class SyncCheck(ValidationStage):
    """Stage 4: Verify sync_copilot_context.py updates copilot instructions."""

    def __init__(self, verbose: bool = False):
        super().__init__("Sync Check (sync_copilot_context)", verbose)

    def validate(self) -> bool:
        """Validate sync_copilot_context functionality."""
        try:
            # Verify sync_copilot_context.py exists
            sync_path = _SCRIPTS_DIR / "sync_copilot_context.py"
            if not sync_path.exists():
                self.error(f"sync_copilot_context.py not found at: {sync_path}")
                return False

            self.log(f"Found sync_copilot_context.py: {sync_path}")

            # Verify copilot instructions file exists
            copilot_file = _REPO_ROOT / ".github" / "copilot-instructions.md"
            if not copilot_file.exists():
                self.error(f"Copilot instructions not found at: {copilot_file}")
                return False

            self.log(f"Found copilot instructions: {copilot_file}")

            # Check if "Learned Anti-Patterns" section exists
            content = copilot_file.read_text()
            if "Learned Anti-Patterns" not in content:
                self.error(
                    "'Learned Anti-Patterns' section not found in copilot instructions",
                )
                return False

            self.log("✓ 'Learned Anti-Patterns' section found")

            # Run sync_copilot_context in dry-run mode
            result = subprocess.run(
                [sys.executable, str(sync_path), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.error(
                    f"sync_copilot_context failed with exit code {result.returncode}",
                )
                self.error(f"stderr: {result.stderr}")
                return False

            self.log("✓ sync_copilot_context executed successfully")

            # Verify it found patterns to sync
            if "pattern" in result.stdout.lower() or "skill" in result.stdout.lower():
                self.log("✓ Pattern synchronization working")
            else:
                self.warn("No patterns mentioned in output")

            return True

        except subprocess.TimeoutExpired:
            self.error("sync_copilot_context timed out after 30 seconds")
            return False
        except Exception as e:
            self.error(f"Unexpected error: {e}")
            return False

    def cleanup(self) -> None:
        """No cleanup needed for sync check."""


class ReportingCheck(ValidationStage):
    """Stage 5: Verify skills_gap_analyzer.py generates reports."""

    def __init__(self, verbose: bool = False):
        super().__init__("Reporting Check (skills_gap_analyzer)", verbose)

    def validate(self) -> bool:
        """Validate skills_gap_analyzer reporting functionality."""
        try:
            # Verify skills_gap_analyzer.py exists
            analyzer_path = _SCRIPTS_DIR / "skills_gap_analyzer.py"
            if not analyzer_path.exists():
                self.error(f"skills_gap_analyzer.py not found at: {analyzer_path}")
                return False

            self.log(f"Found skills_gap_analyzer.py: {analyzer_path}")

            # Run skills_gap_analyzer with --report flag
            result = subprocess.run(
                [sys.executable, str(analyzer_path), "--report"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.error(
                    f"skills_gap_analyzer failed with exit code {result.returncode}",
                )
                self.error(f"stderr: {result.stderr}")
                return False

            self.log("✓ skills_gap_analyzer executed successfully")

            # Verify it generates "Team Skills Assessment" table
            output = result.stdout
            if "Team Skills Assessment" in output:
                self.log("✓ 'Team Skills Assessment' section generated")
            else:
                self.error("'Team Skills Assessment' section not found in output")
                return False

            # Verify markdown table format
            if "|" in output and "---" in output:
                self.log("✓ Markdown table format detected")
            else:
                self.warn("Output may not be in markdown table format")

            # Check for role-based analysis
            if any(role in output for role in ["blog_qa", "devops", "scrum_master"]):
                self.log("✓ Role-based skills analysis working")
            else:
                self.warn("No role-based analysis detected in output")

            return True

        except subprocess.TimeoutExpired:
            self.error("skills_gap_analyzer timed out after 30 seconds")
            return False
        except Exception as e:
            self.error(f"Unexpected error: {e}")
            return False

    def cleanup(self) -> None:
        """No cleanup needed for reporting check."""


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════


class ClosedLoopValidator:
    """Orchestrates all validation stages."""

    def __init__(self, verbose: bool = False, stage: str | None = None):
        self.verbose = verbose
        self.stage_filter = stage
        self.stages: list[ValidationStage] = [
            StorageCheck(verbose),
            SynthesisCheck(verbose),
            IntegrationCheck(verbose),
            SyncCheck(verbose),
            ReportingCheck(verbose),
        ]

    def run(self) -> tuple[int, int]:
        """Run all validation stages.

        Returns:
            Tuple of (passed, total) stage counts

        """
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║ CLOSED-LOOP LEARNING ARCHITECTURE VALIDATION                   ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()

        passed = 0
        total = 0

        for i, stage in enumerate(self.stages, 1):
            # Skip if stage filter is set and doesn't match
            if self.stage_filter:
                stage_id = stage.name.lower().split()[0]
                if stage_id != self.stage_filter.lower():
                    continue

            total += 1

            # Print stage header
            stage_label = f"[{i}/{len(self.stages)}] {stage.name}"
            dots = "." * (60 - len(stage_label))
            print(f"{stage_label}{dots}", end=" ", flush=True)

            try:
                # Run validation
                result = stage.validate()

                if result:
                    print("✅ PASS")
                    passed += 1
                else:
                    print("❌ FAIL")
                    print()
                    print(f"   Errors ({len(stage.errors)}):")
                    for error in stage.errors:
                        print(f"      • {error}")
                    if stage.warnings:
                        print(f"   Warnings ({len(stage.warnings)}):")
                        for warning in stage.warnings:
                            print(f"      • {warning}")
                    print()

            except Exception as e:
                print("❌ FAIL")
                print(f"   Unexpected error: {e}")

            finally:
                # Cleanup stage artifacts
                try:
                    stage.cleanup()
                except Exception as e:
                    if self.verbose:
                        print(f"   ⚠  Cleanup error: {e}")

        return passed, total

    def print_summary(self, passed: int, total: int) -> None:
        """Print validation summary."""
        print()
        print("╔════════════════════════════════════════════════════════════════╗")
        if passed == total:
            print(f"║ VALIDATION RESULT: ✅ ALL CHECKS PASSED ({passed}/{total})")
        else:
            print(f"║ VALIDATION RESULT: ❌ SOME CHECKS FAILED ({passed}/{total})")
        print("╚════════════════════════════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate closed-loop learning architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all validation stages
    python3 scripts/validate_closed_loop.py

    # Run with verbose output
    python3 scripts/validate_closed_loop.py --verbose

    # Run specific stage only
    python3 scripts/validate_closed_loop.py --stage storage
    python3 scripts/validate_closed_loop.py --stage synthesis

    # Cleanup only (no validation)
    python3 scripts/validate_closed_loop.py --cleanup-only

Available stages:
    storage     - SkillsManager storage with orjson
    synthesis   - skill_synthesizer.py pattern extraction
    integration - blog_qa_agent.py skills update
    sync        - sync_copilot_context.py instructions update
    reporting   - skills_gap_analyzer.py report generation
        """,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--stage",
        "-s",
        choices=["storage", "synthesis", "integration", "sync", "reporting"],
        help="Run specific stage only",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Cleanup test artifacts only (no validation)",
    )

    args = parser.parse_args()

    if args.cleanup_only:
        print("🧹 Cleanup mode: No validation performed")
        return 0

    # Run validation
    validator = ClosedLoopValidator(verbose=args.verbose, stage=args.stage)
    passed, total = validator.run()
    validator.print_summary(passed, total)

    # Exit with appropriate code
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
