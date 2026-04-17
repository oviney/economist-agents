#!/usr/bin/env python3
"""Tests for frontmatter schema validation (Story #117).

Validates that Stage 3 Writer Agent output meets the required YAML
frontmatter schema before reaching the quality gate.
"""

import pytest

from scripts.frontmatter_schema import FrontmatterSchema

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

VALID_FRONTMATTER = {
    "layout": "post",
    "title": "The Economics of Test Automation",
    "date": "2026-04-04",
    "author": "Ouray Viney",
    "categories": ["quality-engineering"],
    "image": "/assets/images/test-automation.png",
    "description": "How test automation reshapes engineering economics",
}


@pytest.fixture
def schema() -> FrontmatterSchema:
    """Default frontmatter schema instance."""
    return FrontmatterSchema()


# ═══════════════════════════════════════════════════════════════════════════
# AC1: Required fields present
# ═══════════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    """Given YAML frontmatter, When processed, Then includes required fields."""

    def test_valid_frontmatter_passes(self, schema: FrontmatterSchema) -> None:
        result = schema.validate(VALID_FRONTMATTER)
        assert result.is_valid

    def test_all_required_fields_checked(self, schema: FrontmatterSchema) -> None:
        result = schema.validate(VALID_FRONTMATTER)
        assert result.is_valid
        assert len(result.errors) == 0

    @pytest.mark.parametrize(
        "missing_field",
        ["layout", "title", "date", "categories", "image", "description"],
    )
    def test_each_required_field_enforced(
        self, schema: FrontmatterSchema, missing_field: str
    ) -> None:
        fm = {**VALID_FRONTMATTER}
        del fm[missing_field]
        result = schema.validate(fm)
        assert not result.is_valid
        assert any(missing_field in e for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════
# AC2: Malformed frontmatter rejected
# ═══════════════════════════════════════════════════════════════════════════


class TestMalformedRejection:
    """Given malformed YAML frontmatter, When processed, Then rejected."""

    def test_empty_dict_rejected(self, schema: FrontmatterSchema) -> None:
        result = schema.validate({})
        assert not result.is_valid
        assert len(result.errors) >= 5  # All 5 fields missing

    def test_none_rejected(self, schema: FrontmatterSchema) -> None:
        result = schema.validate(None)
        assert not result.is_valid

    def test_wrong_layout_value_rejected(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "layout": "page"}
        result = schema.validate(fm)
        assert not result.is_valid
        assert any("layout" in e for e in result.errors)

    def test_empty_title_rejected(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "title": ""}
        result = schema.validate(fm)
        assert not result.is_valid

    def test_empty_categories_rejected(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "categories": []}
        result = schema.validate(fm)
        assert not result.is_valid

    def test_invalid_date_format_rejected(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "date": "April 4, 2026"}
        result = schema.validate(fm)
        assert not result.is_valid
        assert any("date" in e for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════
# AC3: Performance — validation under 100ms
# ═══════════════════════════════════════════════════════════════════════════


class TestPerformance:
    """Validation must not add more than 100ms."""

    def test_validation_under_100ms(self, schema: FrontmatterSchema) -> None:
        import time

        start = time.perf_counter()
        for _ in range(1000):
            schema.validate(VALID_FRONTMATTER)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 100, f"Validation took {avg_ms:.2f}ms (max 100ms)"


# ═══════════════════════════════════════════════════════════════════════════
# AC4: Well-formed frontmatter passes without modification
# ═══════════════════════════════════════════════════════════════════════════


class TestPassthrough:
    """Given well-formed frontmatter, Then accepted without modification."""

    def test_valid_passes_cleanly(self, schema: FrontmatterSchema) -> None:
        result = schema.validate(VALID_FRONTMATTER)
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


# ═══════════════════════════════════════════════════════════════════════════
# AC5: Extra fields accepted
# ═══════════════════════════════════════════════════════════════════════════


class TestExtraFields:
    """Given extra non-required fields, Then still accepted."""

    def test_extra_fields_accepted(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "author": "The Economist", "summary": "A summary"}
        result = schema.validate(fm)
        assert result.is_valid

    def test_unknown_fields_accepted(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "custom_field": "custom_value"}
        result = schema.validate(fm)
        assert result.is_valid


# ═══════════════════════════════════════════════════════════════════════════
# AC6: Security — no sensitive data
# ═══════════════════════════════════════════════════════════════════════════


class TestSecurity:
    """Ensure no sensitive information in frontmatter."""

    def test_api_key_in_value_warned(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "config": "sk-proj-abc123def456ghi789jkl012mno"}
        result = schema.validate(fm)
        assert len(result.warnings) > 0
        assert any(
            "sensitive" in w.lower() or "secret" in w.lower() for w in result.warnings
        )

    def test_password_field_warned(self, schema: FrontmatterSchema) -> None:
        fm = {**VALID_FRONTMATTER, "password": "hunter2"}
        result = schema.validate(fm)
        assert len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════
# Integration: validate_article() parses raw article text
# ═══════════════════════════════════════════════════════════════════════════


class TestArticleValidation:
    """End-to-end: validate a raw article string."""

    def test_valid_article_passes(self, schema: FrontmatterSchema) -> None:
        article = '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-04\nauthor: "Ouray Viney"\ncategories: ["QE"]\nimage: /assets/images/test.png\ndescription: "A short summary"\n---\n\nBody'
        result = schema.validate_article(article)
        assert result.is_valid

    def test_article_missing_layout_rejected(self, schema: FrontmatterSchema) -> None:
        article = '---\ntitle: "Test"\ndate: 2026-04-04\ncategories: ["QE"]\nimage: /assets/images/test.png\n---\n\nBody'
        result = schema.validate_article(article)
        assert not result.is_valid

    def test_article_no_frontmatter_rejected(self, schema: FrontmatterSchema) -> None:
        article = "Just plain text"
        result = schema.validate_article(article)
        assert not result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
