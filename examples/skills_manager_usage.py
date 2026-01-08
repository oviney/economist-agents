#!/usr/bin/env python3
"""Example usage of role-aware SkillsManager.

Demonstrates how to use SkillsManager with different agent roles
to maintain separate skills databases for each agent type.
"""

import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.skills_manager import SkillsManager


def example_role_aware_usage():
    """Demonstrate role-aware initialization."""
    print("=" * 60)
    print("Role-Aware Skills Manager Usage Examples")
    print("=" * 60)
    print()

    # Example 1: Product Owner Agent
    print("1. Product Owner Agent")
    po_manager = SkillsManager(role_name="po_agent")
    print(f"   Role: {po_manager.role_name}")
    print(f"   Skills file: {po_manager.skills_file}")

    # Learn a pattern specific to PO Agent
    po_manager.learn_pattern(
        "story_validation",
        "missing_acceptance_criteria",
        {
            "severity": "high",
            "pattern": "User story missing acceptance criteria",
            "check": "Verify story has 3-7 testable AC",
            "learned_from": "Sprint 8 backlog review",
        },
    )
    print(f"   Patterns learned: {len(po_manager.get_patterns())}")
    print()

    # Example 2: Blog QA Agent
    print("2. Blog QA Agent")
    qa_manager = SkillsManager(role_name="blog_qa")
    print(f"   Role: {qa_manager.role_name}")
    print(f"   Skills file: {qa_manager.skills_file}")

    # Learn a pattern specific to Blog QA Agent
    qa_manager.learn_pattern(
        "seo_validation",
        "missing_meta_description",
        {
            "severity": "medium",
            "pattern": "Blog post missing meta description",
            "check": "Verify front matter has description field",
            "learned_from": "SEO audit",
        },
    )
    print(f"   Patterns learned: {len(qa_manager.get_patterns())}")
    print()

    # Example 3: Default (backward compatibility)
    print("3. Default Initialization (backward compatible)")
    default_manager = SkillsManager()
    print(f"   Role: {default_manager.role_name}")
    print(f"   Skills file: {default_manager.skills_file}")
    print()

    # Example 4: Explicit file path
    print("4. Explicit File Path")
    custom_manager = SkillsManager(skills_file="skills/custom_skills.json")
    print(f"   Role: {custom_manager.role_name}")
    print(f"   Skills file: {custom_manager.skills_file}")
    print()

    print("=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)


def example_pattern_categories():
    """Demonstrate pattern categorization."""
    print("\n" + "=" * 60)
    print("Pattern Categorization Example")
    print("=" * 60)
    print()

    manager = SkillsManager(role_name="blog_qa")

    # Learn patterns in different categories
    categories = {
        "seo_validation": [
            ("missing_title", "Page missing title tag"),
            ("placeholder_url", "Placeholder URL detected"),
        ],
        "content_quality": [
            ("missing_frontmatter", "YAML front matter missing"),
            ("ai_disclosure", "AI-generated content not disclosed"),
        ],
        "link_validation": [
            ("broken_internal", "Broken internal link"),
            ("dead_asset", "Asset file not found"),
        ],
    }

    for category, patterns in categories.items():
        for pattern_id, description in patterns:
            manager.learn_pattern(
                category,
                pattern_id,
                {
                    "severity": "medium",
                    "pattern": description,
                    "check": f"Check for {description.lower()}",
                },
            )

    # Get patterns by category
    print("SEO Validation Patterns:")
    for pattern in manager.get_patterns("seo_validation"):
        print(f"  - {pattern['id']}: {pattern['pattern']}")
    print()

    print("Content Quality Patterns:")
    for pattern in manager.get_patterns("content_quality"):
        print(f"  - {pattern['id']}: {pattern['pattern']}")
    print()

    print("All Patterns:")
    all_patterns = manager.get_patterns()
    print(f"  Total: {len(all_patterns)} patterns across {len(categories)} categories")
    print()


def example_statistics():
    """Demonstrate statistics tracking."""
    print("\n" + "=" * 60)
    print("Statistics Tracking Example")
    print("=" * 60)
    print()

    manager = SkillsManager(role_name="po_agent")

    # Record validation runs
    manager.record_run(issues_found=5, issues_fixed=3)
    manager.record_run(issues_found=2, issues_fixed=2)
    manager.record_run(issues_found=0, issues_fixed=0)

    # Get statistics
    stats = manager.get_stats()
    print("Validation Statistics:")
    print(f"  Total Runs: {stats['total_runs']}")
    print(f"  Issues Found: {stats['issues_found']}")
    print(f"  Issues Fixed: {stats['issues_fixed']}")
    print(f"  Last Run: {stats['last_run']}")
    print()


if __name__ == "__main__":
    example_role_aware_usage()
    example_pattern_categories()
    example_statistics()
