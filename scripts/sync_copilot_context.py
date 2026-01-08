#!/usr/bin/env python3
"""Sync learned patterns from skills and docs into Copilot instructions.

This script reads patterns from:
- skills/*.json (defect tracker, blog QA skills, etc.)
- docs/ARCHITECTURE_PATTERNS.md (architectural anti-patterns)

And updates .github/copilot-instructions.md with a "Learned Anti-Patterns"
section that Copilot can use to enforce quality rules in real-time.

Usage:
    python3 scripts/sync_copilot_context.py
    python3 scripts/sync_copilot_context.py --dry-run
"""

import argparse
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extract learned patterns from various sources."""

    def __init__(self, root_dir: Path):
        """Initialize extractor.

        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = root_dir
        self.skills_dir = root_dir / "skills"
        self.docs_dir = root_dir / "docs"
        self.copilot_file = root_dir / ".github" / "copilot-instructions.md"

    def extract_defect_patterns(self) -> list[dict[str, Any]]:
        """Extract patterns from defect tracker.

        Returns:
            List of defect patterns with root causes and prevention strategies
        """
        patterns = []
        tracker_file = self.skills_dir / "defect_tracker.json"

        if not tracker_file.exists():
            logger.warning(f"Defect tracker not found: {tracker_file}")
            return patterns

        try:
            with open(tracker_file, "rb") as f:
                data = orjson.loads(f.read())

            for bug in data.get("bugs", []):
                if bug.get("status") == "fixed" and bug.get("root_cause"):
                    pattern = {
                        "id": bug["id"],
                        "severity": bug["severity"],
                        "component": bug.get("component", "unknown"),
                        "description": bug["description"],
                        "root_cause": bug["root_cause"],
                        "prevention_actions": bug.get("prevention_actions", []),
                        "test_gap": bug.get("missed_by_test_type"),
                    }
                    patterns.append(pattern)

            logger.info(f"Extracted {len(patterns)} defect patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to extract defect patterns: {e}")
            return patterns

    def extract_qa_skills(self) -> list[dict[str, Any]]:
        """Extract patterns from blog QA skills.

        Returns:
            List of QA skill patterns
        """
        patterns = []
        qa_file = self.skills_dir / "blog_qa_skills.json"

        if not qa_file.exists():
            logger.warning(f"QA skills file not found: {qa_file}")
            return patterns

        try:
            with open(qa_file, "rb") as f:
                data = orjson.loads(f.read())

            for category, category_data in data.get("skills", {}).items():
                for pattern in category_data.get("patterns", []):
                    patterns.append(
                        {
                            "id": pattern["id"],
                            "category": category,
                            "severity": pattern.get("severity", "medium"),
                            "pattern": pattern["pattern"],
                            "check": pattern["check"],
                            "auto_fix": pattern.get("auto_fix"),
                        }
                    )

            logger.info(f"Extracted {len(patterns)} QA skill patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to extract QA skills: {e}")
            return patterns

    def extract_architecture_patterns(self) -> list[dict[str, Any]]:
        """Extract patterns from ARCHITECTURE_PATTERNS.md.

        Returns:
            List of architectural patterns
        """
        patterns = []
        arch_file = self.docs_dir / "ARCHITECTURE_PATTERNS.md"

        if not arch_file.exists():
            logger.warning(f"Architecture patterns not found: {arch_file}")
            return patterns

        try:
            content = arch_file.read_text()
            current_category = None
            current_pattern = {}

            for line in content.split("\n"):
                line = line.strip()

                # Category detection (## heading)
                if line.startswith("## ") and not line.startswith("###"):
                    current_category = line[3:].strip()
                    continue

                # Pattern name (### heading)
                if line.startswith("### "):
                    # Save previous pattern
                    if current_pattern and current_category:
                        current_pattern["category"] = current_category
                        patterns.append(current_pattern)

                    # Start new pattern
                    current_pattern = {"name": line[4:].strip()}
                    continue

                # Extract pattern details
                if line.startswith("**Pattern:**"):
                    current_pattern["pattern"] = line.split("**Pattern:**")[1].strip()
                elif line.startswith("**Quality Check:**"):
                    current_pattern["check"] = line.split("**Quality Check:**")[
                        1
                    ].strip()
                elif line.startswith("**Rationale:**"):
                    current_pattern["rationale"] = line.split("**Rationale:**")[
                        1
                    ].strip()
                elif line.startswith("*Severity:"):
                    severity_text = line.split("*Severity:")[1].strip()
                    current_pattern["severity"] = severity_text.rstrip("*")

            # Save last pattern
            if current_pattern and current_category:
                current_pattern["category"] = current_category
                patterns.append(current_pattern)

            logger.info(f"Extracted {len(patterns)} architecture patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to extract architecture patterns: {e}")
            return patterns

    def format_anti_patterns_section(
        self,
        defects: list[dict[str, Any]],
        qa_skills: list[dict[str, Any]],
        arch_patterns: list[dict[str, Any]],
    ) -> str:
        """Format all patterns into markdown section.

        Args:
            defects: Defect patterns
            qa_skills: QA skill patterns
            arch_patterns: Architecture patterns

        Returns:
            Formatted markdown section
        """
        sections = []
        sections.append("## Learned Anti-Patterns")
        sections.append("")
        sections.append(
            f"*Auto-generated from skills/*.json and docs/ARCHITECTURE_PATTERNS.md "
            f"on {datetime.now().strftime('%Y-%m-%d')}*"
        )
        sections.append("")

        # Group defects by root cause
        if defects:
            sections.append("### Defect Prevention Patterns")
            sections.append("")

            by_root_cause = defaultdict(list)
            for defect in defects:
                by_root_cause[defect["root_cause"]].append(defect)

            for root_cause in sorted(by_root_cause.keys()):
                bugs = by_root_cause[root_cause]
                sections.append(f"#### {root_cause.replace('_', ' ').title()}")
                sections.append("")

                for bug in bugs:
                    sections.append(
                        f"**{bug['id']}** ({bug['severity']}) - {bug['component']}"
                    )
                    sections.append(f"- **Issue**: {bug['description']}")
                    if bug.get("test_gap"):
                        sections.append(f"- **Missed By**: {bug['test_gap']}")
                    if bug.get("prevention_actions"):
                        sections.append("- **Prevention**:")
                        for action in bug["prevention_actions"]:
                            sections.append(f"  - {action}")
                    sections.append("")

        # QA Skills by category
        if qa_skills:
            sections.append("### Content Quality Patterns")
            sections.append("")

            by_category = defaultdict(list)
            for skill in qa_skills:
                by_category[skill["category"]].append(skill)

            for category in sorted(by_category.keys()):
                skills = by_category[category]
                sections.append(f"#### {category.replace('_', ' ').title()}")
                sections.append("")

                for skill in skills:
                    sections.append(f"**{skill['id']}** ({skill['severity']})")
                    sections.append(f"- **Pattern**: {skill['pattern']}")
                    sections.append(f"- **Check**: {skill['check']}")
                    if skill.get("auto_fix"):
                        sections.append(f"- **Auto-fix**: {skill['auto_fix']}")
                    sections.append("")

        # Architecture patterns by category
        if arch_patterns:
            sections.append("### Architectural Patterns")
            sections.append("")

            by_category = defaultdict(list)
            for pattern in arch_patterns:
                by_category[pattern["category"]].append(pattern)

            for category in sorted(by_category.keys()):
                patterns = by_category[category]
                sections.append(f"#### {category}")
                sections.append("")

                for pattern in patterns:
                    sections.append(
                        f"**{pattern['name']}** ({pattern.get('severity', 'medium')})"
                    )
                    if pattern.get("pattern"):
                        sections.append(f"- **Pattern**: {pattern['pattern']}")
                    if pattern.get("rationale"):
                        sections.append(f"- **Rationale**: {pattern['rationale']}")
                    if pattern.get("check"):
                        sections.append(f"- **Check**: {pattern['check']}")
                    sections.append("")

        return "\n".join(sections)

    def update_copilot_instructions(
        self, anti_patterns_section: str, dry_run: bool = False
    ) -> bool:
        """Update copilot instructions with anti-patterns section.

        Args:
            anti_patterns_section: Formatted anti-patterns markdown
            dry_run: If True, only show what would be changed

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.copilot_file.exists():
            logger.error(f"Copilot instructions not found: {self.copilot_file}")
            return False

        try:
            content = self.copilot_file.read_text()

            # Find insertion point (before "## Additional Resources" or at end)
            if "## Additional Resources" in content:
                parts = content.split("## Additional Resources")
                updated_content = (
                    parts[0].rstrip()
                    + "\n\n"
                    + anti_patterns_section
                    + "\n\n"
                    + "## Additional Resources"
                    + parts[1]
                )
            else:
                updated_content = (
                    content.rstrip() + "\n\n" + anti_patterns_section + "\n"
                )

            if dry_run:
                logger.info("DRY RUN - Would update copilot instructions with:")
                logger.info(anti_patterns_section)
                return True

            # Write updated content
            self.copilot_file.write_text(updated_content)
            logger.info(f"Updated {self.copilot_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to update copilot instructions: {e}")
            return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Sync learned patterns into Copilot instructions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Root directory of the project",
    )
    args = parser.parse_args()

    # Initialize extractor
    extractor = PatternExtractor(args.root)

    # Extract patterns
    logger.info("Extracting patterns from skills and docs...")
    defects = extractor.extract_defect_patterns()
    qa_skills = extractor.extract_qa_skills()
    arch_patterns = extractor.extract_architecture_patterns()

    total_patterns = len(defects) + len(qa_skills) + len(arch_patterns)
    logger.info(f"Total patterns extracted: {total_patterns}")

    if total_patterns == 0:
        logger.warning("No patterns extracted - nothing to sync")
        return 1

    # Format anti-patterns section
    logger.info("Formatting anti-patterns section...")
    anti_patterns_section = extractor.format_anti_patterns_section(
        defects, qa_skills, arch_patterns
    )

    # Update copilot instructions
    logger.info("Updating Copilot instructions...")
    success = extractor.update_copilot_instructions(
        anti_patterns_section, dry_run=args.dry_run
    )

    if success:
        if args.dry_run:
            logger.info("DRY RUN complete - no files modified")
        else:
            logger.info(
                f"✅ Successfully synced {total_patterns} patterns to Copilot instructions"
            )
        return 0
    else:
        logger.error("❌ Failed to sync patterns")
        return 1


if __name__ == "__main__":
    exit(main())
