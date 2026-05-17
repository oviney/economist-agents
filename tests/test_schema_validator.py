#!/usr/bin/env python3
"""Direct unit tests for src/quality/schema_validator.py (Issue #358, 2/5).

Targets the FrontMatterValidator class and module-level validate_front_matter
entry point. Asserts on the (is_valid, issues) tuple contract and on the
CRITICAL/WARNING severity prefixes used throughout the module.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.quality.schema_validator import (
    FRONT_MATTER_SCHEMA,
    FrontMatterValidator,
    validate_front_matter,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

EXPECTED_DATE = "2026-01-15"


def _article(
    *,
    layout: str = "post",
    title: str = "Self-Healing Tests: The 80% Maintenance Gap",
    date: str = EXPECTED_DATE,
    categories: list[str] | None = None,
    author: str | None = None,
    ai_assisted: bool | None = True,
    body: str = "Some neutral body text without disclosure triggers.",
    include_closing_marker: bool = True,
    extra_fields: dict[str, object] | None = None,
) -> str:
    """Build a minimal article string with controllable front matter."""
    if categories is None:
        categories = ["Quality Engineering"]

    lines = ["---", f"layout: {layout}", f'title: "{title}"', f"date: {date}"]

    cats_yaml = "[" + ", ".join(f'"{c}"' for c in categories) + "]"
    lines.append(f"categories: {cats_yaml}")

    if author is not None:
        lines.append(f'author: "{author}"')
    if ai_assisted is not None:
        lines.append(f"ai_assisted: {str(ai_assisted).lower()}")
    if extra_fields:
        for k, v in extra_fields.items():
            lines.append(f"{k}: {v}")

    if include_closing_marker:
        lines.append("---")
        lines.append("")
        lines.append(body)

    return "\n".join(lines) + "\n"


@pytest.fixture
def validator() -> FrontMatterValidator:
    """Validator pinned to a deterministic expected date."""
    return FrontMatterValidator(expected_date=EXPECTED_DATE)


# ═══════════════════════════════════════════════════════════════════════════
# Module constants
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaConstant:
    """The exported FRONT_MATTER_SCHEMA shape is part of the public API."""

    def test_schema_declares_required_fields(self) -> None:
        assert FRONT_MATTER_SCHEMA["required"] == [
            "layout",
            "title",
            "date",
            "categories",
        ]

    def test_schema_allows_additional_properties(self) -> None:
        assert FRONT_MATTER_SCHEMA["additionalProperties"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Constructor / defaults
# ═══════════════════════════════════════════════════════════════════════════


class TestConstructor:
    """FrontMatterValidator construction defaults."""

    def test_default_expected_date_is_today(self) -> None:
        v = FrontMatterValidator()
        assert v.expected_date == datetime.now().strftime("%Y-%m-%d")

    def test_custom_expected_date_is_stored(self) -> None:
        v = FrontMatterValidator(expected_date="2026-12-31")
        assert v.expected_date == "2026-12-31"

    def test_schema_reference_attached(self) -> None:
        v = FrontMatterValidator()
        assert v.schema is FRONT_MATTER_SCHEMA


# ═══════════════════════════════════════════════════════════════════════════
# Happy path
# ═══════════════════════════════════════════════════════════════════════════


class TestHappyPath:
    """Well-formed content validates cleanly with zero issues."""

    def test_minimal_valid_article_passes(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article()
        is_valid, issues = validator.validate(content)
        assert is_valid is True
        assert issues == []

    def test_valid_with_correct_author_passes(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(author="Ouray Viney")
        is_valid, issues = validator.validate(content)
        assert is_valid is True
        assert issues == []

    def test_all_allowed_layouts_accepted(
        self,
    ) -> None:
        for layout in ("post", "page", "default"):
            v = FrontMatterValidator(expected_date=EXPECTED_DATE)
            is_valid, issues = v.validate(_article(layout=layout))
            assert is_valid is True, f"layout '{layout}' should be valid: {issues}"


# ═══════════════════════════════════════════════════════════════════════════
# Front matter structural failures
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontMatterStructure:
    """Documents that the YAML envelope itself is enforced."""

    def test_no_front_matter_marker_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        is_valid, issues = validator.validate("Just a body, no front matter.\n")
        assert is_valid is False
        assert any("No YAML front matter" in i for i in issues)

    def test_missing_closing_marker_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        # Starts with --- but never closes
        content = "---\nlayout: post\ntitle: Foo\n"
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("Incomplete YAML front matter" in i for i in issues)

    def test_invalid_yaml_syntax_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = "---\nlayout: post\ntitle: 'unterminated\n---\n\nBody\n"
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("Invalid YAML syntax" in i for i in issues)

    def test_front_matter_must_be_object_not_scalar(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = "---\njust a string\n---\n\nBody\n"
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("must be a YAML object" in i for i in issues)


# ═══════════════════════════════════════════════════════════════════════════
# Required field enforcement
# ═══════════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    """Each required field reports a CRITICAL missing-field error."""

    @pytest.mark.parametrize(
        "missing_field",
        ["layout", "title", "date", "categories"],
    )
    def test_each_required_field_enforced(
        self,
        validator: FrontMatterValidator,
        missing_field: str,
    ) -> None:
        # Build a full article then strip the target line by key
        full = _article()
        stripped_lines = [
            line
            for line in full.splitlines()
            if not line.startswith(f"{missing_field}:")
        ]
        content = "\n".join(stripped_lines) + "\n"

        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(f"Missing required field '{missing_field}'" in i for i in issues), (
            f"Missing required field '{missing_field}' not surfaced: {issues}"
        )

    def test_missing_required_short_circuits_other_validation(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        # Strip layout AND title; we should still get back early
        content = (
            '---\ndate: 2026-01-15\ncategories: ["Quality Engineering"]\n---\n\nBody\n'
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        # Only the two missing-field issues; no downstream validation noise
        assert all("Missing required field" in i for i in issues), (
            f"Expected only missing-field issues, got: {issues}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Layout validation
# ═══════════════════════════════════════════════════════════════════════════


class TestLayoutValidation:
    """layout must be one of post/page/default."""

    def test_invalid_layout_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(layout="custom_layout")
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(
            "Invalid layout 'custom_layout'" in i and "CRITICAL" in i for i in issues
        )


# ═══════════════════════════════════════════════════════════════════════════
# Title validation
# ═══════════════════════════════════════════════════════════════════════════


class TestTitleValidation:
    """Title type, length, and generic-pattern checks."""

    def test_short_title_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(title="Short")
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("Title too short" in i for i in issues)

    def test_non_string_title_currently_raises(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        """Documents a known SUT defect (out of scope for #358 to fix).

        When ``title`` parses as a non-string (e.g. integer), the validator
        appends a "Title must be a string" issue but does NOT short-circuit
        before the subsequent ``title.lower()`` call, raising AttributeError.

        See follow-up suggestion in PR description.
        """
        content = (
            "---\n"
            "layout: post\n"
            "title: 12345\n"
            f"date: {EXPECTED_DATE}\n"
            'categories: ["Quality Engineering"]\n'
            "---\n\nBody\n"
        )
        with pytest.raises(AttributeError):
            validator.validate(content)

    @pytest.mark.parametrize(
        "generic_title",
        [
            "Myth vs Reality of Self-Healing Tests",
            "The Ultimate Guide to Test Automation",
            "Everything You Need to Know About QA",
            "5 Tips for Better Engineering Hires",
        ],
    )
    def test_generic_title_warned(
        self,
        validator: FrontMatterValidator,
        generic_title: str,
    ) -> None:
        content = _article(title=generic_title)
        is_valid, issues = validator.validate(content)
        # Warnings make the result invalid (any issues -> not valid)
        assert is_valid is False
        assert any(
            i.startswith("WARNING") and "Generic title pattern" in i for i in issues
        ), f"Expected generic-title WARNING for {generic_title!r}: {issues}"


# ═══════════════════════════════════════════════════════════════════════════
# Date validation
# ═══════════════════════════════════════════════════════════════════════════


class TestDateValidation:
    """Date format and expected-match logic."""

    def test_malformed_date_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = (
            "---\n"
            "layout: post\n"
            'title: "A Sufficiently Long Title Here"\n'
            "date: January 1st 2026\n"
            'categories: ["Quality Engineering"]\n'
            "---\n\nBody\n"
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("Invalid date format" in i and "CRITICAL" in i for i in issues)

    def test_date_mismatch_warns(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(date="2026-02-01")  # validator expects 2026-01-15
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(
            i.startswith("WARNING") and "doesn't match expected" in i for i in issues
        )

    def test_yaml_native_date_accepted(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        # YAML parses 'date: 2026-01-15' (unquoted) as a datetime.date.
        # The validator must stringify it via strftime, not crash.
        content = (
            "---\n"
            "layout: post\n"
            'title: "A Sufficiently Long Title Here"\n'
            "date: 2026-01-15\n"
            'categories: ["Quality Engineering"]\n'
            "ai_assisted: true\n"
            "---\n\nNeutral body.\n"
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is True, f"unexpected issues: {issues}"


# ═══════════════════════════════════════════════════════════════════════════
# Categories validation
# ═══════════════════════════════════════════════════════════════════════════


class TestCategoriesValidation:
    """Categories must be a non-empty array of ≤3 allowed strings."""

    def test_non_list_categories_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = (
            "---\n"
            "layout: post\n"
            'title: "A Sufficiently Long Title Here"\n'
            f"date: {EXPECTED_DATE}\n"
            'categories: "Quality Engineering"\n'  # scalar, not array
            "---\n\nBody\n"
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("categories must be an array" in i for i in issues)

    def test_empty_categories_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = (
            "---\n"
            "layout: post\n"
            'title: "A Sufficiently Long Title Here"\n'
            f"date: {EXPECTED_DATE}\n"
            "categories: []\n"
            "---\n\nBody\n"
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any("categories array is empty" in i for i in issues)

    def test_too_many_categories_warns(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        cats = [
            "Quality Engineering",
            "Software Engineering",
            "Test Automation",
            "Security",
        ]
        content = _article(categories=cats)
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(
            i.startswith("WARNING") and "Too many categories" in i for i in issues
        )

    def test_unknown_category_warns(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(categories=["Not A Real Category"])
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(i.startswith("WARNING") and "Unknown category" in i for i in issues)


# ═══════════════════════════════════════════════════════════════════════════
# Author + AI disclosure
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthorAndAIDisclosure:
    """Author whitelist and AI-mention disclosure rule."""

    def test_wrong_author_rejected(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        content = _article(author="Somebody Else")
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(
            'author must be "Ouray Viney"' in i and "CRITICAL" in i for i in issues
        )

    def test_ai_mention_without_flag_warns(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        # ai_assisted omitted, body mentions Claude
        content = _article(
            ai_assisted=None,
            body="This piece was drafted with Claude as a writing partner.",
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is False
        assert any(
            "missing 'ai_assisted: true' flag" in i and i.startswith("WARNING")
            for i in issues
        )

    def test_no_ai_mention_no_flag_passes(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        # ai_assisted omitted; body has no AI-related token
        content = _article(
            ai_assisted=None,
            body="A neutral paragraph about engineering economics.",
        )
        is_valid, issues = validator.validate(content)
        assert is_valid is True, f"unexpected issues: {issues}"


# ═══════════════════════════════════════════════════════════════════════════
# validate_file
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateFile:
    """validate_file reads from disk and delegates to validate()."""

    def test_valid_file_passes(
        self,
        tmp_path: Path,
        validator: FrontMatterValidator,
    ) -> None:
        article = tmp_path / "ok.md"
        article.write_text(_article(), encoding="utf-8")
        is_valid, issues = validator.validate_file(str(article))
        assert is_valid is True
        assert issues == []

    def test_missing_file_returns_critical_error(
        self,
        tmp_path: Path,
        validator: FrontMatterValidator,
    ) -> None:
        missing = tmp_path / "nope.md"
        is_valid, issues = validator.validate_file(str(missing))
        assert is_valid is False
        assert len(issues) == 1
        assert issues[0].startswith("CRITICAL: Error reading file:")


# ═══════════════════════════════════════════════════════════════════════════
# format_report
# ═══════════════════════════════════════════════════════════════════════════


class TestFormatReport:
    """format_report shapes the human-readable summary."""

    def test_passed_report_when_valid(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        report = validator.format_report(is_valid=True, issues=[])
        assert "PASSED" in report
        assert "Issues: 0" in report
        assert "meets all schema requirements" in report

    def test_failed_report_groups_critical_and_warning(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        issues = [
            "CRITICAL: Missing required field 'layout'",
            "WARNING: Date doesn't match expected",
        ]
        report = validator.format_report(is_valid=False, issues=issues)
        assert "FAILED" in report
        assert "Issues: 2" in report
        assert "CRITICAL (must fix):" in report
        assert "WARNINGS (review):" in report
        assert "Missing required field 'layout'" in report
        assert "Date doesn't match expected" in report

    def test_failed_report_with_only_warnings(
        self,
        validator: FrontMatterValidator,
    ) -> None:
        report = validator.format_report(
            is_valid=False,
            issues=["WARNING: Too many categories"],
        )
        assert "WARNINGS (review):" in report
        assert "CRITICAL (must fix):" not in report


# ═══════════════════════════════════════════════════════════════════════════
# Module-level entry point
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateFrontMatterEntryPoint:
    """Module-level convenience wrapper prints a report and returns tuple."""

    def test_returns_tuple_and_prints_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        content = _article()
        is_valid, issues = validate_front_matter(content, expected_date=EXPECTED_DATE)
        assert is_valid is True
        assert issues == []
        captured = capsys.readouterr()
        assert "FRONT MATTER SCHEMA VALIDATION" in captured.out
        assert "PASSED" in captured.out

    def test_failure_path_prints_failed_report(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        is_valid, issues = validate_front_matter(
            "no front matter here\n",
            expected_date=EXPECTED_DATE,
        )
        assert is_valid is False
        assert any("No YAML front matter" in i for i in issues)
        captured = capsys.readouterr()
        assert "FAILED" in captured.out

    def test_default_expected_date_uses_today(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        content = _article(date=today)
        is_valid, issues = validate_front_matter(content)
        assert is_valid is True, f"unexpected issues: {issues}"
        capsys.readouterr()  # drain
