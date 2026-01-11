#!/usr/bin/env python3
"""Skill Synthesizer - Automated Learning from Failure Logs

Parses failure logs (generation.log, pytest output, error traces) and uses LLM
analysis to identify root causes. Generates structured patterns matching the
SkillsManager.learn_pattern schema to ensure no learning is lost.

Usage:
    # Analyze generation.log
    python3 scripts/skill_synthesizer.py --log generation.log --role blog_qa

    # Analyze pytest output
    python3 scripts/skill_synthesizer.py --log pytest_output.txt --role test_automation

    # Analyze custom error log
    python3 scripts/skill_synthesizer.py --log error.log --role agent_orchestration --category integration_errors

    # Dry run (no save)
    python3 scripts/skill_synthesizer.py --log generation.log --dry-run

Example:
    $ python3 scripts/skill_synthesizer.py --log generation.log --role writer_agent
    📊 Analyzing log: generation.log (1,234 bytes)
    🤖 Using LLM to synthesize patterns...
    ✅ Identified 2 patterns:
       - quality_gates.editorial_gate_failure (HIGH severity)
       - data_verification.unverified_claims (MEDIUM severity)
    💾 Saved patterns to skills/writer_agent_skills.json
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from llm_client import call_llm, create_llm_client
from skills_manager import SkillsManager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

PATTERN_ANALYSIS_PROMPT = """You are an expert at analyzing software failures and extracting learnable patterns.

Your task: Analyze the following log output and identify root causes that can be prevented in future runs.

CRITICAL REQUIREMENTS:
1. Focus on ACTIONABLE patterns (things that can be detected automatically)
2. Ignore transient issues (network timeouts, API rate limits)
3. Extract the ROOT CAUSE, not just symptoms
4. Provide SPECIFIC detection rules (not vague descriptions)

For each pattern identified, provide:
- category: Type of issue (e.g., "quality_gates", "data_verification", "integration_errors")
- pattern_id: Unique identifier (lowercase_with_underscores)
- severity: "critical", "high", "medium", or "low"
- pattern: Human-readable description of what went wrong
- check: Specific validation rule to detect this pattern
- learned_from: Source of the failure (e.g., "generation.log line 23")
- prevention_strategy: How to prevent this in future (1-2 sentences)

LOG OUTPUT:
{log_content}

OUTPUT FORMAT (JSON array):
[
  {{
    "category": "quality_gates",
    "pattern_id": "editorial_gate_failure",
    "severity": "high",
    "pattern": "Editor Agent failed 3/5 quality gates on draft content",
    "check": "Verify editor_agent response has 'Quality gates: X passed, Y failed' and X >= 4",
    "learned_from": "generation.log editorial review section",
    "prevention_strategy": "Add pre-editor validation to catch common issues before Editor Agent runs, reducing gate failures by catching problems earlier in pipeline."
  }},
  {{
    "category": "data_verification",
    "pattern_id": "unverified_claims_present",
    "severity": "medium",
    "pattern": "Research Agent produced unverified claims flagged in output",
    "check": "Scan research output for '[UNVERIFIED]' markers and count > 0",
    "learned_from": "generation.log research phase",
    "prevention_strategy": "Enhance Research Agent prompt to require source verification before including statistics, with explicit instructions to skip unverifiable claims."
  }}
]

Return ONLY the JSON array. No markdown fences, no explanations.
"""


# ═══════════════════════════════════════════════════════════════════════════
# LOG PARSER
# ═══════════════════════════════════════════════════════════════════════════


class LogParser:
    """Parses different log formats to extract failure information."""

    @staticmethod
    def parse_generation_log(content: str) -> dict[str, Any]:
        """Parse generation.log format.

        Args:
            content: Raw log file content

        Returns:
            Dictionary with structured failure information
        """
        failures = []

        # Extract quality gate failures
        gate_match = re.search(
            r"Quality gates:\s*(\d+)\s*passed,\s*(\d+)\s*failed", content, re.IGNORECASE
        )
        if gate_match:
            passed = int(gate_match.group(1))
            failed = int(gate_match.group(2))
            if failed > 0:
                failures.append(
                    {
                        "type": "quality_gate_failure",
                        "passed": passed,
                        "failed": failed,
                        "location": f"line {content[: gate_match.start()].count(chr(10)) + 1}",
                    }
                )

        # Extract unverified claims
        unverified_match = re.search(
            r"(\d+)\s+unverified claims flagged", content, re.IGNORECASE
        )
        if unverified_match:
            count = int(unverified_match.group(1))
            if count > 0:
                failures.append(
                    {
                        "type": "unverified_claims",
                        "count": count,
                        "location": f"line {content[: unverified_match.start()].count(chr(10)) + 1}",
                    }
                )

        # Extract Visual QA failures
        visual_qa_match = re.search(
            r"Visual gates:\s*(\d+)/(\d+)\s*passed", content, re.IGNORECASE
        )
        if visual_qa_match:
            passed = int(visual_qa_match.group(1))
            total = int(visual_qa_match.group(2))
            if passed < total:
                failures.append(
                    {
                        "type": "visual_qa_failure",
                        "passed": passed,
                        "total": total,
                        "location": f"line {content[: visual_qa_match.start()].count(chr(10)) + 1}",
                    }
                )

        # Extract word count issues
        word_match = re.search(r"Draft complete \((\d+) words\)", content)
        if word_match:
            words = int(word_match.group(1))
            if words < 800:  # Target is 800+ words
                failures.append(
                    {
                        "type": "low_word_count",
                        "count": words,
                        "target": 800,
                        "location": f"line {content[: word_match.start()].count(chr(10)) + 1}",
                    }
                )

        return {
            "format": "generation_log",
            "failures": failures,
            "raw_content": content,
        }

    @staticmethod
    def parse_pytest_output(content: str) -> dict[str, Any]:
        """Parse pytest output format.

        Args:
            content: Raw pytest output

        Returns:
            Dictionary with structured failure information
        """
        failures = []

        # Extract test failures
        failed_match = re.search(r"(\d+)\s+failed", content)
        if failed_match:
            count = int(failed_match.group(1))
            failures.append(
                {"type": "test_failures", "count": count, "location": "pytest summary"}
            )

        # Extract specific test errors
        error_pattern = re.compile(
            r"FAILED\s+([\w/:.]+)\s*-\s*(.+?)(?=\n|$)", re.MULTILINE
        )
        for match in error_pattern.finditer(content):
            test_name = match.group(1)
            error_msg = match.group(2).strip()
            failures.append(
                {
                    "type": "test_error",
                    "test": test_name,
                    "error": error_msg,
                    "location": f"line {content[: match.start()].count(chr(10)) + 1}",
                }
            )

        return {"format": "pytest_output", "failures": failures, "raw_content": content}

    @staticmethod
    def parse_generic_error(content: str) -> dict[str, Any]:
        """Parse generic error logs.

        Args:
            content: Raw log content

        Returns:
            Dictionary with structured failure information
        """
        failures = []

        # Extract Python tracebacks
        traceback_pattern = re.compile(
            r"Traceback \(most recent call last\):(.+?)(?:^[A-Z]\w+Error:.+?$)",
            re.MULTILINE | re.DOTALL,
        )
        for match in traceback_pattern.finditer(content):
            failures.append(
                {
                    "type": "python_traceback",
                    "traceback": match.group(0),
                    "location": f"line {content[: match.start()].count(chr(10)) + 1}",
                }
            )

        # Extract error keywords
        error_keywords = ["ERROR", "FAILED", "CRITICAL", "EXCEPTION"]
        for keyword in error_keywords:
            pattern = re.compile(f"\\b{keyword}\\b.*", re.IGNORECASE)
            for match in pattern.finditer(content):
                failures.append(
                    {
                        "type": "error_message",
                        "severity": keyword.lower(),
                        "message": match.group(0).strip(),
                        "location": f"line {content[: match.start()].count(chr(10)) + 1}",
                    }
                )

        return {"format": "generic_error", "failures": failures, "raw_content": content}

    @classmethod
    def auto_parse(cls, content: str) -> dict[str, Any]:
        """Automatically detect log format and parse accordingly.

        Args:
            content: Raw log content

        Returns:
            Parsed log data with failure information
        """
        # Detect generation.log format
        if "Research Agent:" in content or "Writer Agent:" in content:
            return cls.parse_generation_log(content)

        # Detect pytest format
        elif "passed" in content and "failed" in content and "test" in content.lower():
            return cls.parse_pytest_output(content)

        # Default to generic
        else:
            return cls.parse_generic_error(content)


# ═══════════════════════════════════════════════════════════════════════════
# SKILL SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════════


class SkillSynthesizer:
    """Synthesizes learnable patterns from failure logs using LLM analysis."""

    def __init__(self, llm_client=None):
        """Initialize synthesizer.

        Args:
            llm_client: Optional pre-configured LLM client
        """
        self.llm_client = llm_client or create_llm_client()

    def synthesize_patterns(
        self, log_content: str, role_name: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Synthesize learnable patterns from log content.

        Args:
            log_content: Raw log file content
            role_name: Agent role name (for SkillsManager context)
            category: Optional category filter

        Returns:
            List of pattern dictionaries ready for SkillsManager.learn_pattern()
        """
        logger.info(f"Synthesizing patterns from {len(log_content)} bytes of log data")

        # Use LLM to analyze and extract patterns
        prompt = PATTERN_ANALYSIS_PROMPT.format(log_content=log_content[:4000])

        try:
            response = call_llm(
                self.llm_client,
                "",  # System prompt embedded in user prompt
                prompt,
                max_tokens=2000,
                temperature=0.0,  # Deterministic analysis
            )

            # Parse JSON response
            try:
                # Remove markdown fences if present
                response_clean = response.strip()
                if response_clean.startswith("```"):
                    response_clean = re.sub(r"^```(?:json)?\n", "", response_clean)
                    response_clean = re.sub(r"\n```$", "", response_clean)

                patterns = json.loads(response_clean)

                # Filter by category if specified
                if category:
                    patterns = [p for p in patterns if p.get("category") == category]

                logger.info(f"✅ Identified {len(patterns)} patterns")
                return patterns

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response was: {response[:500]}")
                return []

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return []

    def apply_patterns(
        self,
        patterns: list[dict[str, Any]],
        skills_manager: SkillsManager,
        dry_run: bool = False,
    ) -> int:
        """Apply synthesized patterns to SkillsManager.

        Args:
            patterns: List of pattern dictionaries
            skills_manager: Target SkillsManager instance
            dry_run: If True, don't actually save patterns

        Returns:
            Number of patterns successfully applied
        """
        applied = 0

        for pattern in patterns:
            category = pattern.get("category", "uncategorized")
            pattern_id = pattern.get("pattern_id", "unknown")

            # Validate required fields
            required_fields = ["severity", "pattern", "check", "learned_from"]
            missing = [f for f in required_fields if f not in pattern]
            if missing:
                logger.warning(
                    f"Skipping pattern {pattern_id}: missing fields {missing}"
                )
                continue

            if not dry_run:
                skills_manager.learn_pattern(category, pattern_id, pattern)
                logger.info(
                    f"   - {category}.{pattern_id} ({pattern['severity']} severity)"
                )
            else:
                logger.info(f"   [DRY RUN] Would learn: {category}.{pattern_id}")

            applied += 1

        if not dry_run and applied > 0:
            skills_manager.save()
            logger.info(f"💾 Saved {applied} patterns to {skills_manager.skills_file}")

        return applied


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """Main entry point for skill synthesizer CLI."""
    parser = argparse.ArgumentParser(
        description="Synthesize learnable patterns from failure logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze generation.log
  python3 scripts/skill_synthesizer.py --log generation.log --role blog_qa

  # Analyze pytest output with category filter
  python3 scripts/skill_synthesizer.py --log tests.txt --role test_automation --category integration_errors

  # Dry run (no save)
  python3 scripts/skill_synthesizer.py --log error.log --role writer_agent --dry-run

  # Verbose output
  python3 scripts/skill_synthesizer.py --log generation.log --role editor_agent -v
        """,
    )

    parser.add_argument(
        "--log", required=True, type=Path, help="Path to log file to analyze"
    )
    parser.add_argument(
        "--role",
        required=True,
        help="Agent role name (e.g., 'blog_qa', 'writer_agent')",
    )
    parser.add_argument("--category", help="Optional category filter for patterns")
    parser.add_argument(
        "--dry-run", action="store_true", help="Analyze but don't save patterns"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    # Validate log file
    if not args.log.exists():
        logger.error(f"❌ Log file not found: {args.log}")
        sys.exit(1)

    # Read log content
    try:
        log_content = args.log.read_text()
        logger.info(f"📊 Analyzing log: {args.log} ({len(log_content)} bytes)")
    except Exception as e:
        logger.error(f"❌ Failed to read log file: {e}")
        sys.exit(1)

    # Parse log to extract structured failures
    parsed = LogParser.auto_parse(log_content)
    logger.debug(f"   Log format: {parsed['format']}")
    logger.debug(f"   Failures detected: {len(parsed['failures'])}")

    if not parsed["failures"]:
        logger.warning("⚠️  No failures detected in log - nothing to learn")
        sys.exit(0)

    # Synthesize patterns using LLM
    logger.info("🤖 Using LLM to synthesize patterns...")
    synthesizer = SkillSynthesizer()
    patterns = synthesizer.synthesize_patterns(log_content, args.role, args.category)

    if not patterns:
        logger.warning(
            "⚠️  No patterns identified - log may not contain actionable failures"
        )
        sys.exit(0)

    logger.info(f"✅ Identified {len(patterns)} patterns:")

    # Apply patterns to SkillsManager
    skills_manager = SkillsManager(role_name=args.role)
    applied = synthesizer.apply_patterns(patterns, skills_manager, args.dry_run)

    if args.dry_run:
        logger.info(f"\n[DRY RUN] Would have saved {applied} patterns")
    else:
        logger.info(f"\n✅ Successfully learned {applied} new patterns")
        logger.info(f"   Skills file: {skills_manager.skills_file}")


if __name__ == "__main__":
    main()
