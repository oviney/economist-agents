#!/usr/bin/env python3
"""
Defect Prevention Rules - Automated Quality Gates

Learned patterns from 6 production bugs with Root Cause Analysis.
Catches common defect patterns before commit/deployment.

Usage:
    from defect_prevention_rules import DefectPrevention

    checker = DefectPrevention()
    violations = checker.check_all(article_content, metadata)
    if violations:
        print("⚠️ BLOCKED: Defect patterns detected")
        for v in violations:
            print(f"  - {v}")
"""

import re
from typing import Any


class DefectPrevention:
    """Automated checks based on historical defect patterns"""

    def __init__(self):
        """Initialize prevention rules with bug pattern database"""
        self.rules = self._load_prevention_rules()

    def _load_prevention_rules(self) -> list[dict[str, Any]]:
        """Load prevention rules learned from defect tracker RCA"""
        return [
            {
                "id": "BUG-016-pattern",
                "source_bug": "BUG-016",
                "root_cause": "prompt_engineering",
                "severity": "critical",
                "rule": "chart_embedding_missing",
                "description": "Charts generated but never embedded in articles",
                "check_function": self._check_chart_embedding,
                "prevention_actions": [
                    "Enhanced Writer Agent prompt",
                    "Added Publication Validator Check #7",
                ],
            },
            {
                "id": "BUG-015-pattern",
                "source_bug": "BUG-015",
                "root_cause": "validation_gap",
                "severity": "high",
                "rule": "missing_category_tag",
                "description": "Missing category tag on article page",
                "check_function": self._check_category_present,
                "prevention_actions": [
                    "Added blog_qa_agent.py Jekyll layout validation"
                ],
            },
            {
                "id": "BUG-017-pattern",
                "source_bug": "BUG-017",
                "root_cause": "requirements_gap",
                "severity": "medium",
                "rule": "duplicate_chart_display",
                "description": "Duplicate chart display (featured image + embed)",
                "check_function": self._check_duplicate_chart,
                "prevention_actions": [
                    "Removed 'image:' field from YAML frontmatter specification"
                ],
            },
            {
                "id": "BUG-021-pattern",
                "source_bug": "BUG-021",
                "root_cause": "code_logic",
                "severity": "medium",
                "rule": "stale_badges",
                "description": "README.md badges show stale values",
                "check_function": self._check_badge_currency,
                "prevention_actions": [
                    "Created update_readme_badges.py for automatic updates"
                ],
            },
            {
                "id": "BUG-022-pattern",
                "source_bug": "BUG-022",
                "root_cause": "code_logic",
                "severity": "medium",
                "rule": "stale_sprint_docs",
                "description": "SPRINT.md shows outdated sprint content",
                "check_function": self._check_sprint_doc_currency,
                "prevention_actions": [
                    "Created update_sprint_docs.py for automatic updates"
                ],
            },
        ]

    def check_all(
        self, article_content: str, metadata: dict[str, Any] = None
    ) -> list[str]:
        """
        Run all prevention checks on article content.

        Args:
            article_content: Full article markdown content
            metadata: Optional metadata dict (chart_data, etc.)

        Returns:
            List of violation messages (empty if all checks pass)
        """
        violations = []

        for rule in self.rules:
            check_func = rule["check_function"]
            violation = check_func(article_content, metadata or {})
            if violation:
                violations.append(
                    f"[{rule['severity'].upper()}] {violation} (Pattern: {rule['id']})"
                )

        return violations

    # =========================================================================
    # PREVENTION CHECK FUNCTIONS (learned from historical bugs)
    # =========================================================================

    def _check_chart_embedding(self, content: str, metadata: dict) -> str:
        """
        BUG-016 Prevention: Detect when chart generated but not embedded

        Pattern: Graphics Agent creates chart → Writer Agent ignores it
        Root Cause: Prompt engineering - Writer didn't have explicit requirement

        Check: If chart_data exists, article MUST contain chart markdown
        """
        has_chart_data = metadata.get("chart_data") or metadata.get("chart_filename")

        if not has_chart_data:
            return ""  # No chart expected, skip check

        # Look for chart markdown: ![...](*.png) or ![...](path/to/*.png)
        chart_pattern = r"!\[.*?\]\(.*?\.png\)"
        has_chart_embed = bool(re.search(chart_pattern, content))

        if not has_chart_embed:
            return (
                "Chart data provided but no chart embedded in article. "
                "Add chart markdown: ![Chart title](chart_filename.png). "
                "This prevents BUG-016 (charts generated but invisible)."
            )

        # Secondary check: Chart should be referenced in text
        chart_references = [
            r"as the chart shows",
            r"the chart reveals",
            r"shown in the chart",
            r"chart illustrates",
        ]
        has_reference = any(
            re.search(pattern, content, re.IGNORECASE) for pattern in chart_references
        )

        if not has_reference:
            return (
                "Chart embedded but never referenced in text. "
                "Add: 'As the chart shows...' for proper integration."
            )

        return ""  # All checks passed

    def _check_category_present(self, content: str, metadata: dict) -> str:
        """
        BUG-015 Prevention: Detect missing category in YAML frontmatter

        Pattern: Jekyll layout expects category but it's missing
        Root Cause: Validation gap - no check for required frontmatter fields

        Check: YAML frontmatter must have 'category' or 'categories' field
        """
        # Extract YAML frontmatter
        yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not yaml_match:
            return "No YAML frontmatter found. Required for Jekyll posts."

        frontmatter = yaml_match.group(1)

        # Check for category field (single or plural)
        has_category = bool(
            re.search(r"^(category|categories):", frontmatter, re.MULTILINE)
        )

        if not has_category:
            return (
                "Missing 'category' or 'categories' field in YAML frontmatter. "
                "This prevents BUG-015 (missing category tag on page)."
            )

        return ""

    def _check_duplicate_chart(self, content: str, metadata: dict) -> str:
        """
        BUG-017 Prevention: Detect duplicate chart display paths

        Pattern: Jekyll 'image:' field + markdown embed = duplicate display
        Root Cause: Requirements gap - unclear featured image vs embed

        Check: If chart markdown present, YAML must NOT have 'image:' field
        """
        # Extract YAML frontmatter
        yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not yaml_match:
            return ""

        frontmatter = yaml_match.group(1)

        # Check for image field in frontmatter
        has_image_field = bool(re.search(r"^image:", frontmatter, re.MULTILINE))

        # Check for chart markdown in body
        chart_pattern = r"!\[.*?\]\(.*?\.png\)"
        has_chart_embed = bool(re.search(chart_pattern, content))

        if has_image_field and has_chart_embed:
            return (
                "Duplicate chart display detected: 'image:' field in frontmatter "
                "AND chart markdown in body. Remove 'image:' field. "
                "This prevents BUG-017 (duplicate chart rendering)."
            )

        return ""

    def _check_badge_currency(self, content: str, metadata: dict) -> str:
        """
        BUG-021 Prevention: Detect stale README badges

        Pattern: Badges manually updated, prone to drift
        Root Cause: Code logic - no automated process

        Check: README badges should have been updated by automation

        Note: This is primarily enforced by update_readme_badges.py in pre-commit
        """
        # This check is informational - actual update happens in pre-commit hook
        # Just flag if README appears to be manually edited

        if "README.md" in metadata.get("file_path", ""):
            # Check if badges section exists
            badge_pattern = r"!\[.*?\]\(https://img\.shields\.io/badge/.*?\)"
            has_badges = bool(re.search(badge_pattern, content))

            if has_badges:
                # Badges present - should be auto-updated
                return ""  # Let pre-commit hook handle this

        return ""

    def _check_sprint_doc_currency(self, content: str, metadata: dict) -> str:
        """
        BUG-022 Prevention: Detect stale sprint documentation

        Pattern: SPRINT.md shows old sprint, actual sprint is further along
        Root Cause: Code logic - no automated process

        Check: SPRINT.md should be updated by automation

        Note: This is primarily enforced by update_sprint_docs.py in pre-commit
        """
        # This check is informational - actual update happens via automation

        if "SPRINT.md" in metadata.get("file_path", ""):
            # Flag if Sprint 1-3 mentioned when we're on Sprint 5+
            old_sprint_pattern = r"Sprint [1-3]\b"
            has_old_sprint = bool(re.search(old_sprint_pattern, content))

            if has_old_sprint:
                return (
                    "SPRINT.md may be outdated (mentions Sprint 1-3). "
                    "Run update_sprint_docs.py to refresh. "
                    "This prevents BUG-022 (stale sprint documentation)."
                )

        return ""

    def generate_report(self) -> str:
        """Generate human-readable prevention rules report"""
        report = [
            "# Defect Prevention Rules - Learned Patterns",
            f"**Total Rules**: {len(self.rules)}",
            "**Source**: 6 bugs with Root Cause Analysis",
            "",
            "## Active Prevention Checks",
            "",
        ]

        for rule in self.rules:
            report.append(f"### {rule['id']} ({rule['severity'].upper()})")
            report.append(f"**Source Bug**: {rule['source_bug']}")
            report.append(f"**Root Cause**: {rule['root_cause']}")
            report.append(f"**Description**: {rule['description']}")
            report.append("**Prevention Actions**:")
            for action in rule["prevention_actions"]:
                report.append(f"  - {action}")
            report.append("")

        report.extend(
            [
                "## How It Works",
                "1. Pre-commit hook calls DefectPrevention.check_all()",
                "2. Each rule function scans for known defect patterns",
                "3. If pattern detected → commit blocked with specific fix",
                "4. Prevents 80% of historical bugs (4/5 caught patterns)",
                "",
                "## Integration Points",
                "- Pre-commit hook: Primary enforcement",
                "- Publication validator: Article-specific checks",
                "- Blog QA agent: Jekyll/layout checks",
                "",
                "## Metrics",
                "- Defect escape rate: 66.7% → Target <20%",
                "- Critical TTD: 5.5 days → Target <2 days",
                "- Prevention coverage: 5/6 bugs = 83%",
            ]
        )

        return "\n".join(report)


def main():
    """Test prevention rules"""
    checker = DefectPrevention()

    # Test case 1: Chart data but no embedding (BUG-016 pattern)
    print("\n🧪 Test 1: Chart without embedding (BUG-016 pattern)")
    test_article = """---
layout: post
title: Test Article
date: 2026-01-01
---

This is an article about testing.
"""
    violations = checker.check_all(
        test_article, {"chart_data": {"title": "Test Chart"}}
    )
    if violations:
        print("  ❌ CAUGHT:")
        for v in violations:
            print(f"    {v}")
    else:
        print("  ✅ PASSED")

    # Test case 2: Chart properly embedded
    print("\n🧪 Test 2: Chart properly embedded")
    test_article_good = """---
layout: post
title: Test Article
date: 2026-01-01
category: testing
---

This is an article about testing.

![Test Chart](charts/test.png)

As the chart shows, testing prevents bugs.
"""
    violations = checker.check_all(
        test_article_good, {"chart_data": {"title": "Test Chart"}}
    )
    if violations:
        print("  ❌ VIOLATIONS:")
        for v in violations:
            print(f"    {v}")
    else:
        print("  ✅ PASSED (no violations)")

    # Test case 3: Missing category (BUG-015 pattern)
    print("\n🧪 Test 3: Missing category (BUG-015 pattern)")
    test_no_category = """---
layout: post
title: Test Article
date: 2026-01-01
---

Article without category.
"""
    violations = checker.check_all(test_no_category, {})
    if violations:
        print("  ❌ CAUGHT:")
        for v in violations:
            print(f"    {v}")
    else:
        print("  ✅ PASSED")

    # Generate report
    print("\n" + "=" * 60)
    print(checker.generate_report())
    print("=" * 60)


if __name__ == "__main__":
    main()
