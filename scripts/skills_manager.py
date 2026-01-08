#!/usr/bin/env python3
"""Skills Manager for Multi-Agent System.

Implements Claude-style learning and skill improvement with role-aware
configuration. Each agent role maintains its own skills database.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson

logger = logging.getLogger(__name__)


class SkillsManager:
    """Manages learned validation patterns and continuous improvement.

    Attributes:
        role_name: The name of the agent role (e.g., "blog_qa", "po_agent").
        skills_file: Path to the role-specific skills JSON file.
        skills: Loaded skills data including patterns and statistics.
    """

    def __init__(
        self, role_name: str | None = None, skills_file: str | Path | None = None
    ) -> None:
        """Initialize the SkillsManager for a specific role.

        Args:
            role_name: Name of the agent role. If provided, automatically
                constructs path as skills/{role_name}_skills.json.
            skills_file: Optional explicit path to skills file. Overrides
                role_name if both are provided. If neither is provided,
                defaults to "blog_qa".

        Example:
            >>> # Role-aware initialization
            >>> manager = SkillsManager(role_name="po_agent")
            >>> # Explicit file path
            >>> manager = SkillsManager(skills_file="custom/path.json")
            >>> # Default (blog_qa)
            >>> manager = SkillsManager()
        """
        if skills_file is not None:
            self.skills_file = Path(skills_file)
            self.role_name = Path(skills_file).stem.replace("_skills", "")
        elif role_name is not None:
            script_dir = Path(__file__).parent.parent
            self.skills_file = script_dir / "skills" / f"{role_name}_skills.json"
            self.role_name = role_name
        else:
            # Default to blog_qa for backward compatibility
            script_dir = Path(__file__).parent.parent
            self.skills_file = script_dir / "skills" / "blog_qa_skills.json"
            self.role_name = "blog_qa"

        logger.info(f"Initializing SkillsManager for role: {self.role_name}")
        logger.debug(f"Skills file path: {self.skills_file}")
        self.skills = self._load_skills()

    def _load_skills(self) -> dict[str, Any]:
        """Load existing skills or create new skill set.

        Returns:
            Dictionary containing skills, patterns, and validation statistics.

        Raises:
            orjson.JSONDecodeError: If skills file contains invalid JSON.
        """
        if self.skills_file.exists():
            try:
                with open(self.skills_file, "rb") as f:
                    return orjson.loads(f.read())
            except orjson.JSONDecodeError as e:
                logger.error(f"Failed to parse skills file: {e}")
                logger.warning("Creating new skills database")
                return self._create_default_skills()
        else:
            logger.info("Skills file not found, creating new database")
            return self._create_default_skills()

    def _create_default_skills(self) -> dict[str, Any]:
        """Create initial skill set with default structure.

        Returns:
            Dictionary with default skills structure including version,
            empty skills categories, and zero validation statistics.
        """
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "skills": {},
            "validation_stats": {
                "total_runs": 0,
                "issues_found": 0,
                "issues_fixed": 0,
                "last_run": None,
            },
        }

    def get_patterns(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get validation patterns, optionally filtered by category.

        Args:
            category: Optional category name to filter patterns.
                If None, returns all patterns from all categories.

        Returns:
            List of pattern dictionaries matching the category filter,
            or all patterns if no category specified.

        Example:
            >>> manager = SkillsManager(role_name="blog_qa")
            >>> seo_patterns = manager.get_patterns("seo_validation")
            >>> all_patterns = manager.get_patterns()
        """
        if category and category in self.skills.get("skills", {}):
            return self.skills["skills"][category].get("patterns", [])

        # Return all patterns across all categories
        all_patterns = []
        for cat_data in self.skills.get("skills", {}).values():
            all_patterns.extend(cat_data.get("patterns", []))
        return all_patterns

    def learn_pattern(
        self, category: str, pattern_id: str, pattern_data: dict[str, Any]
    ) -> None:
        """Add a new learned pattern to the skills database.

        Args:
            category: Category name for the pattern (e.g., "seo_validation").
            pattern_id: Unique identifier for the pattern.
            pattern_data: Dictionary containing pattern details including
                severity, check description, and learned_from context.

        Example:
            >>> manager = SkillsManager(role_name="blog_qa")
            >>> manager.learn_pattern(
            ...     "content_quality",
            ...     "missing_frontmatter",
            ...     {
            ...         "severity": "critical",
            ...         "pattern": "Post missing YAML front matter",
            ...         "check": "Verify file starts with ---",
            ...         "learned_from": "BUG-015"
            ...     }
            ... )
        """
        if "skills" not in self.skills:
            self.skills["skills"] = {}

        if category not in self.skills["skills"]:
            self.skills["skills"][category] = {
                "description": pattern_data.get("description", ""),
                "patterns": [],
            }

        # Check if pattern already exists
        existing = next(
            (
                p
                for p in self.skills["skills"][category]["patterns"]
                if p["id"] == pattern_id
            ),
            None,
        )

        if existing:
            # Update existing pattern
            existing.update(pattern_data)
            existing["last_seen"] = datetime.now().isoformat()
        else:
            # Add new pattern
            pattern_data["id"] = pattern_id
            pattern_data["learned_on"] = datetime.now().isoformat()
            self.skills["skills"][category]["patterns"].append(pattern_data)

        self.skills["last_updated"] = datetime.now().isoformat()

    def record_run(self, issues_found: int, issues_fixed: int = 0) -> None:
        """Record validation run statistics.

        Args:
            issues_found: Number of issues discovered in this run.
            issues_fixed: Number of issues fixed (default: 0).

        Example:
            >>> manager = SkillsManager(role_name="blog_qa")
            >>> manager.record_run(issues_found=3, issues_fixed=2)
        """
        stats = self.skills.get("validation_stats", {})
        stats["total_runs"] = stats.get("total_runs", 0) + 1
        stats["issues_found"] = stats.get("issues_found", 0) + issues_found
        stats["issues_fixed"] = stats.get("issues_fixed", 0) + issues_fixed
        stats["last_run"] = datetime.now().isoformat()
        self.skills["validation_stats"] = stats

    def save(self) -> None:
        """Persist skills to disk using orjson for fast serialization.

        Raises:
            OSError: If directory creation or file write fails.
        """
        self.skills_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.skills_file, "wb") as f:
            f.write(orjson.dumps(self.skills, option=orjson.OPT_INDENT_2))
        logger.info(f"Saved skills to {self.skills_file}")

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary containing total_runs, issues_found, issues_fixed,
            and last_run timestamp.
        """
        return self.skills.get("validation_stats", {})

    def suggest_improvements(self, validation_results: dict[str, Any]) -> list[str]:
        """Analyze results and suggest new patterns to learn.

        Args:
            validation_results: Dictionary containing validation results with
                keys like yaml_issues, style_issues, link_issues.

        Returns:
            List of improvement suggestions based on detected patterns.
        """
        suggestions = []

        # Check for recurring issues
        if validation_results.get("yaml_issues"):
            suggestions.append(
                "Consider adding pattern for: recurring YAML validation failures"
            )

        if validation_results.get("style_issues"):
            suggestions.append("Consider adding pattern for: common style violations")

        if validation_results.get("link_issues"):
            suggestions.append("Consider adding pattern for: broken link patterns")

        return suggestions

    def export_report(self) -> str:
        """Generate human-readable skills report.

        Returns:
            Formatted string report containing validation statistics,
            learned patterns by category, and severity information.
        """
        report_lines = [
            f"=== {self.role_name.replace('_', ' ').title()} Skills Report ===",
            f"Last Updated: {self.skills.get('last_updated', 'Unknown')}",
            "",
            "Validation Statistics:",
        ]

        stats = self.get_stats()
        report_lines.append(f"  Total Runs: {stats.get('total_runs', 0)}")
        report_lines.append(f"  Issues Found: {stats.get('issues_found', 0)}")
        report_lines.append(f"  Issues Fixed: {stats.get('issues_fixed', 0)}")
        report_lines.append(f"  Last Run: {stats.get('last_run', 'Never')}")
        report_lines.append("")

        report_lines.append("Learned Skills:")
        for category, cat_data in self.skills.get("skills", {}).items():
            report_lines.append(f"\n  {category.replace('_', ' ').title()}:")
            report_lines.append(f"    {cat_data.get('description', '')}")
            for pattern in cat_data.get("patterns", []):
                report_lines.append(
                    f"    - {pattern['id']}: {pattern.get('pattern', '')}"
                )
                report_lines.append(
                    f"      Severity: {pattern.get('severity', 'unknown')}"
                )

        return "\n".join(report_lines)


if __name__ == "__main__":
    # Test the skills manager
    manager = SkillsManager()
    print(manager.export_report())
