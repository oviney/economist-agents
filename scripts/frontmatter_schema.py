#!/usr/bin/env python3
"""Frontmatter Schema Validation (Story #117).

Structured output validation boundary for the Stage 3 Writer Agent.
Validates YAML frontmatter against a required schema before the article
reaches the quality gate.  Deterministic, no LLM required.

Usage:
    from scripts.frontmatter_schema import FrontmatterSchema

    schema = FrontmatterSchema()
    result = schema.validate_article(article_text)
    if not result.is_valid:
        print(result.errors)
"""

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

# Required frontmatter fields and their validation rules
REQUIRED_FIELDS = ["layout", "title", "date", "categories", "image"]

# Sensitive patterns that should never appear in frontmatter values
_SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),  # API keys
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PATs
    re.compile(r"password|secret|token|credential", re.IGNORECASE),
]

# Valid date format
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ValidationResult:
    """Result of frontmatter schema validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FrontmatterSchema:
    """Validates YAML frontmatter against required schema."""

    def validate(self, frontmatter: dict[str, Any] | None) -> ValidationResult:
        """Validate a frontmatter dictionary against the schema.

        Args:
            frontmatter: Parsed YAML frontmatter dict, or None.

        Returns:
            ValidationResult with is_valid, errors, and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if frontmatter is None:
            return ValidationResult(
                is_valid=False, errors=["Frontmatter is None (no YAML found)"]
            )

        if not isinstance(frontmatter, dict):
            return ValidationResult(
                is_valid=False, errors=["Frontmatter is not a dictionary"]
            )

        # Check required fields
        for req_field in REQUIRED_FIELDS:
            if req_field not in frontmatter:
                errors.append(f"Missing required field: {req_field}")

        # Validate layout value
        layout = frontmatter.get("layout")
        if layout is not None and layout != "post":
            errors.append(f"layout must be 'post', got '{layout}'")

        # Validate title is non-empty
        title = frontmatter.get("title")
        if title is not None and (not isinstance(title, str) or not title.strip()):
            errors.append("title must be a non-empty string")

        # Validate date format (YYYY-MM-DD)
        date = frontmatter.get("date")
        if date is not None:
            date_str = str(date)
            if not _DATE_PATTERN.match(date_str):
                errors.append(f"date must be YYYY-MM-DD format, got '{date_str}'")

        # Validate categories is non-empty list
        categories = frontmatter.get("categories")
        if categories is not None:
            if isinstance(categories, list) and len(categories) == 0:
                errors.append("categories must be a non-empty list")
            elif isinstance(categories, str) and not categories.strip():
                errors.append("categories must be non-empty")

        # Security: check all values for sensitive patterns
        for key, value in frontmatter.items():
            value_str = str(value)
            for pattern in _SENSITIVE_PATTERNS:
                if pattern.search(value_str):
                    warnings.append(
                        f"Possible sensitive data in field '{key}' — "
                        f"review before publishing"
                    )
                    break
            # Check for sensitive field names
            if any(
                word in key.lower()
                for word in ["password", "secret", "token", "credential", "api_key"]
            ):
                warnings.append(
                    f"Sensitive field name '{key}' — should not be in frontmatter"
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_article(self, article: str) -> ValidationResult:
        """Validate frontmatter extracted from a raw article string.

        Args:
            article: Full article text with YAML frontmatter.

        Returns:
            ValidationResult.
        """
        if not article or not article.strip().startswith("---"):
            return ValidationResult(
                is_valid=False,
                errors=["Article does not start with YAML frontmatter (---)"],
            )

        parts = article.split("---", 2)
        if len(parts) < 3:
            return ValidationResult(
                is_valid=False,
                errors=["Malformed frontmatter — missing closing ---"],
            )

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid YAML in frontmatter: {e}"],
            )

        return self.validate(frontmatter)
