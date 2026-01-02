#!/usr/bin/env python3
"""
Front Matter Schema Validator

Enforces strict schema validation for Jekyll blog post front matter.
This is a "BLOCK" in the quality framework - hard validation that
cannot be bypassed.

Based on Nick Tune's approach of preventing AI from violating rules.
"""

import re
from datetime import datetime

import yaml

# JSON Schema for blog post front matter
FRONT_MATTER_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["layout", "title", "date", "categories"],
    "properties": {
        "layout": {
            "type": "string",
            "enum": ["post", "page", "default"],
            "description": "Jekyll layout to use",
        },
        "title": {
            "type": "string",
            "minLength": 10,
            "description": "Article title (must be specific, ≥10 chars)",
        },
        "date": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "Publication date (YYYY-MM-DD)",
        },
        "categories": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "string",
                "enum": [
                    "quality-engineering",
                    "test-automation",
                    "performance",
                    "ai-testing",
                    "software-engineering",
                    "devops",
                ],
            },
            "description": "Category tags (1-3 allowed)",
        },
        "author": {"type": "string", "description": "Author name (optional)"},
        "ai_assisted": {
            "type": "boolean",
            "description": "Whether AI was used in creation (optional)",
        },
    },
    "additionalProperties": True,  # Allow other fields like 'excerpt'
}


class FrontMatterValidator:
    """Validates blog post front matter against strict schema"""

    def __init__(self, expected_date: str = None):
        self.schema = FRONT_MATTER_SCHEMA
        self.expected_date = expected_date or datetime.now().strftime("%Y-%m-%d")

    def validate(self, content: str) -> tuple[bool, list[str]]:
        """
        Validate article front matter.

        Returns:
            (is_valid, issues_list)
        """
        issues = []

        # Extract front matter
        if not content.startswith("---"):
            issues.append("CRITICAL: No YAML front matter found (must start with ---)")
            return False, issues

        parts = content.split("---", 2)
        if len(parts) < 3:
            issues.append(
                "CRITICAL: Incomplete YAML front matter (missing closing ---)"
            )
            return False, issues

        front_matter_text = parts[1].strip()

        # Parse YAML
        try:
            front_matter = yaml.safe_load(front_matter_text)
        except yaml.YAMLError as e:
            issues.append(f"CRITICAL: Invalid YAML syntax: {e}")
            return False, issues

        if not isinstance(front_matter, dict):
            issues.append("CRITICAL: Front matter must be a YAML object/dictionary")
            return False, issues

        # Validate required fields
        required_fields = self.schema["required"]
        for field in required_fields:
            if field not in front_matter:
                issues.append(f"CRITICAL: Missing required field '{field}'")

        # If missing required fields, stop here
        if any("Missing required field" in issue for issue in issues):
            return False, issues

        # Validate field types and constraints

        # Layout validation
        if "layout" in front_matter:
            layout = front_matter["layout"]
            allowed_layouts = self.schema["properties"]["layout"]["enum"]
            if layout not in allowed_layouts:
                issues.append(
                    f"CRITICAL: Invalid layout '{layout}'. "
                    f"Allowed: {', '.join(allowed_layouts)}"
                )

        # Title validation
        if "title" in front_matter:
            title = front_matter["title"]
            if not isinstance(title, str):
                issues.append("CRITICAL: Title must be a string")
            elif len(title) < 10:
                issues.append(
                    f"CRITICAL: Title too short ({len(title)} chars, ≥10 required)"
                )

            # Check for generic titles
            generic_patterns = [
                r"\bmyth vs reality\b",
                r"\bultimate guide\b",
                r"\beverything you need\b",
                r"\b\d+ tips for\b",
            ]
            title_lower = title.lower()
            for pattern in generic_patterns:
                if re.search(pattern, title_lower):
                    issues.append(
                        f"WARNING: Generic title pattern detected: '{pattern}' "
                        f"(title should be specific)"
                    )

        # Date validation
        if "date" in front_matter:
            date = front_matter["date"]
            if isinstance(date, datetime):
                date_str = date.strftime("%Y-%m-%d")
            else:
                date_str = str(date)

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                issues.append(
                    f"CRITICAL: Invalid date format '{date_str}' (expected YYYY-MM-DD)"
                )

            # Check if date matches expected date
            if self.expected_date and date_str != self.expected_date:
                issues.append(
                    f"WARNING: Date '{date_str}' doesn't match expected '{self.expected_date}'"
                )

        # Categories validation
        if "categories" in front_matter:
            categories = front_matter["categories"]

            if not isinstance(categories, list):
                issues.append("CRITICAL: categories must be an array")
            elif len(categories) == 0:
                issues.append("CRITICAL: categories array is empty (need ≥1)")
            elif len(categories) > 3:
                issues.append(
                    f"WARNING: Too many categories ({len(categories)}, ≤3 recommended)"
                )
            else:
                # Validate each category
                allowed_categories = self.schema["properties"]["categories"]["items"][
                    "enum"
                ]
                for cat in categories:
                    if cat not in allowed_categories:
                        issues.append(
                            f"WARNING: Unknown category '{cat}'. "
                            f"Allowed: {', '.join(allowed_categories)}"
                        )

        # AI disclosure check
        if "ai_assisted" not in front_matter:
            # Check if content mentions AI
            body = parts[2].lower()
            ai_mentions = [
                "ai",
                "llm",
                "gpt",
                "claude",
                "generated",
                "artificial intelligence",
            ]
            if any(mention in body for mention in ai_mentions):
                issues.append(
                    "WARNING: Content mentions AI but missing 'ai_assisted: true' flag"
                )

        return len(issues) == 0, issues

    def validate_file(self, file_path: str) -> tuple[bool, list[str]]:
        """Validate front matter in a file"""
        try:
            with open(file_path) as f:
                content = f.read()
            return self.validate(content)
        except Exception as e:
            return False, [f"CRITICAL: Error reading file: {e}"]

    def format_report(self, is_valid: bool, issues: list[str]) -> str:
        """Format validation report"""
        status = "✅ PASSED" if is_valid else "❌ FAILED"

        report = [
            "\n" + "=" * 60,
            "FRONT MATTER SCHEMA VALIDATION",
            "=" * 60,
            f"Status: {status}",
            f"Issues: {len(issues)}",
        ]

        if issues:
            report.append("\nVALIDATION ERRORS:")
            critical = [i for i in issues if "CRITICAL" in i]
            warnings = [i for i in issues if "WARNING" in i]

            if critical:
                report.append("\n  CRITICAL (must fix):")
                for issue in critical:
                    report.append(f"    • {issue}")

            if warnings:
                report.append("\n  WARNINGS (review):")
                for issue in warnings:
                    report.append(f"    • {issue}")
        else:
            report.append("\n  ✅ Front matter meets all schema requirements")

        report.append("=" * 60 + "\n")

        return "\n".join(report)


def validate_front_matter(
    content: str, expected_date: str = None
) -> tuple[bool, list[str]]:
    """
    Main entry point for front matter validation.

    Args:
        content: Full article content including front matter
        expected_date: Expected date (YYYY-MM-DD), defaults to today

    Returns:
        (is_valid, issues_list)
    """
    validator = FrontMatterValidator(expected_date)
    is_valid, issues = validator.validate(content)

    # Print report
    report = validator.format_report(is_valid, issues)
    print(report)

    return is_valid, issues


if __name__ == "__main__":

    # Test the validator

    # Test 1: Valid front matter
    print("Test 1: Valid front matter")
    valid_content = """---
layout: post
title: "Self-Healing Tests: The 80% Maintenance Gap"
date: 2026-01-01
categories: [quality-engineering, test-automation]
author: "The Economist"
ai_assisted: true
---

Self-healing tests promise an 80% cut in maintenance costs. Only 10% achieve it.
"""
    validate_front_matter(valid_content, "2026-01-01")

    # Test 2: Missing categories (Issue #15 pattern)
    print("\nTest 2: Missing categories (Issue #15 pattern)")
    missing_categories = """---
layout: post
title: "Self-Healing Tests"
date: 2026-01-01
---

Article content here.
"""
    validate_front_matter(missing_categories, "2026-01-01")

    # Test 3: Missing layout (production bug pattern)
    print("\nTest 3: Missing layout field")
    missing_layout = """---
title: "Self-Healing Tests"
date: 2026-01-01
categories: [quality-engineering]
---

Article content here.
"""
    validate_front_matter(missing_layout, "2026-01-01")

    # Test 4: Generic title
    print("\nTest 4: Generic title pattern")
    generic_title = """---
layout: post
title: "Myth vs Reality"
date: 2026-01-01
categories: [quality-engineering]
---

Article content here.
"""
    validate_front_matter(generic_title, "2026-01-01")

    print("\n✅ Schema validator tests complete")
