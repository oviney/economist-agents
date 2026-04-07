#!/usr/bin/env python3
"""Tests for mcp_servers/publication_validator_server.py

Validates that the MCP tool correctly wraps PublicationValidator.validate()
and returns the expected result structure.
"""

import asyncio
from pathlib import Path

import pytest

from mcp_servers.publication_validator_server import (
    VALID_CATEGORIES,
    mcp,
    validate_for_publication,
    validate_post,
)

# ---------------------------------------------------------------------------
# Article helpers (mirrors test_publication_validator.py helpers)
# ---------------------------------------------------------------------------

VALID_REFERENCES = """## References

1. Gartner, ["World Quality Report 2024"](https://example.com/gartner), *Gartner Research*, 2024
2. Forrester, ["State of Test Automation"](https://example.com/forrester), *Forrester*, 2024
3. IEEE, ["Software Testing Practices"](https://example.com/ieee), *IEEE*, 2024
"""

VALID_BODY = " ".join(["word"] * 850)


def _make_article(
    *,
    layout: str = "post",
    title: str = "Specific Descriptive Title for Testing",
    date: str = "2026-04-05",
    author: str = "The Economist",
    categories: str = '["quality-engineering"]',
    body: str | None = None,
    references: str | None = None,
    frontmatter_open: str = "---",
    frontmatter_close: str = "---",
) -> str:
    """Build a minimal valid article string."""
    if body is None:
        body = VALID_BODY
    if references is None:
        references = VALID_REFERENCES
    fields = []
    if layout:
        fields.append(f"layout: {layout}")
    if title:
        fields.append(f'title: "{title}"')
    if date:
        fields.append(f"date: {date}")
    if author:
        fields.append(f'author: "{author}"')
    if categories:
        fields.append(f"categories: {categories}")
    fm = "\n".join(fields)
    return f"{frontmatter_open}\n{fm}\n{frontmatter_close}\n\n{body}\n\n{references}\n"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateForPublicationReturnShape:
    """validate_for_publication always returns a dict with is_valid and issues."""

    def test_returns_dict(self) -> None:
        result = validate_for_publication(
            content=_make_article(), expected_date="2026-04-05"
        )
        assert isinstance(result, dict)

    def test_has_is_valid_key(self) -> None:
        result = validate_for_publication(
            content=_make_article(), expected_date="2026-04-05"
        )
        assert "is_valid" in result

    def test_has_issues_key(self) -> None:
        result = validate_for_publication(
            content=_make_article(), expected_date="2026-04-05"
        )
        assert "issues" in result

    def test_issues_is_list(self) -> None:
        result = validate_for_publication(
            content=_make_article(), expected_date="2026-04-05"
        )
        assert isinstance(result["issues"], list)

    def test_is_valid_is_bool(self) -> None:
        result = validate_for_publication(
            content=_make_article(), expected_date="2026-04-05"
        )
        assert isinstance(result["is_valid"], bool)


class TestValidateForPublicationValidArticle:
    """Acceptance criteria: valid article → is_valid=True, issues=[]."""

    def test_valid_article_returns_is_valid_true(self) -> None:
        article = _make_article()
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        critical = [i for i in result["issues"] if i["severity"] == "CRITICAL"]
        assert result["is_valid"] is True, (
            f"Expected is_valid=True, got issues: {critical}"
        )

    def test_valid_article_returns_no_critical_issues(self) -> None:
        article = _make_article()
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        critical = [i for i in result["issues"] if i["severity"] == "CRITICAL"]
        assert critical == []


class TestValidateForPublicationPlaceholders:
    """Acceptance criteria: article with placeholders → CRITICAL failure."""

    def test_todo_placeholder_rejected(self) -> None:
        body = VALID_BODY + " TODO: fill this in later."
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False

    def test_placeholder_issue_has_critical_severity(self) -> None:
        body = VALID_BODY + " FIXME: replace me."
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        placeholder_issues = [
            i for i in result["issues"] if i["check"] == "placeholder_text"
        ]
        assert len(placeholder_issues) >= 1
        assert placeholder_issues[0]["severity"] == "CRITICAL"

    def test_placeholder_issue_message_populated(self) -> None:
        body = VALID_BODY + " XXX: should not be published."
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        placeholder_issues = [
            i for i in result["issues"] if i["check"] == "placeholder_text"
        ]
        assert len(placeholder_issues) >= 1
        assert placeholder_issues[0]["message"]

    def test_verification_flag_needs_source_rejected(self) -> None:
        body = VALID_BODY + " Some stat [NEEDS SOURCE] here."
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False

    def test_unverified_flag_rejected(self) -> None:
        body = VALID_BODY + " Some claim [UNVERIFIED] here."
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False

    def test_verification_issue_severity_is_critical(self) -> None:
        body = VALID_BODY + " [NEEDS SOURCE]"
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        verification_issues = [
            i for i in result["issues"] if i["check"] == "verification_flags"
        ]
        assert len(verification_issues) >= 1
        assert verification_issues[0]["severity"] == "CRITICAL"


class TestValidateForPublicationYaml:
    """YAML front matter issues are surfaced in the tool result."""

    def test_missing_yaml_delimiter_returns_critical(self) -> None:
        article = _make_article(frontmatter_open="")
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False
        yaml_issues = [i for i in result["issues"] if i["check"] == "yaml_format"]
        assert len(yaml_issues) >= 1

    def test_code_fence_yaml_returns_critical(self) -> None:
        article = (
            f'```yaml\nlayout: post\ntitle: "Test"\ndate: 2026-04-05\n```\n\n'
            f"{VALID_BODY}\n\n{VALID_REFERENCES}\n"
        )
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False


class TestValidateForPublicationDateMismatch:
    """Date mismatch is surfaced as CRITICAL."""

    def test_wrong_date_returns_critical(self) -> None:
        # Article date is 2026-01-01, expected_date is today's mocked value
        article = _make_article(date="2026-01-01")
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        assert result["is_valid"] is False
        date_issues = [i for i in result["issues"] if i["check"] == "date_mismatch"]
        assert len(date_issues) >= 1
        assert date_issues[0]["severity"] == "CRITICAL"


class TestValidateForPublicationDefaultDate:
    """expected_date defaults to today when None is passed."""

    def test_none_expected_date_accepted(self) -> None:
        # Calling without expected_date should not raise
        article = _make_article(date="2099-12-31")  # will likely fail date check
        result = validate_for_publication(content=article, expected_date=None)
        assert isinstance(result, dict)
        assert "is_valid" in result

    def test_omit_expected_date_accepted(self) -> None:
        article = _make_article(date="2099-12-31")
        result = validate_for_publication(content=article)
        assert isinstance(result, dict)


class TestValidateForPublicationIssueSchema:
    """Each issue dict contains the mandatory keys."""

    def test_issue_keys_present(self) -> None:
        body = VALID_BODY + " TODO: placeholder"
        article = _make_article(body=body)
        result = validate_for_publication(content=article, expected_date="2026-04-05")
        for issue in result["issues"]:
            assert "check" in issue, f"Issue missing 'check': {issue}"
            assert "severity" in issue, f"Issue missing 'severity': {issue}"
            assert "message" in issue, f"Issue missing 'message': {issue}"


class TestMcpToolRegistered:
    """The FastMCP server registers the tool correctly."""

    def test_tool_listed(self) -> None:
        """validate_for_publication appears in the server's tool registry."""
        tool_names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert "validate_for_publication" in tool_names

    def test_tool_has_description(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        tool = next(t for t in tools if t.name == "validate_for_publication")
        assert tool.description


# ===========================================================================
# Helpers for validate_post tests
# ===========================================================================

#: Minimal PNG magic bytes used to create stub image files in tests.
_PNG_MAGIC = b"\x89PNG\r\n"


def _write_post(
    tmp_path: Path,
    *,
    layout: str = "post",
    title: str = "A Sufficiently Long and Descriptive Title",
    date: str = "2026-04-05",
    author: str = "The Economist",
    categories: str = '["quality-engineering"]',
    image: str | None = None,
    body: str = "Article body content.",
    frontmatter_extra: str = "",
    filename: str = "post.md",
    omit_fields: list[str] | None = None,
) -> Path:
    """Write a minimal test post to *tmp_path* and return its path.

    If *image* is not provided a PNG file is created inside *tmp_path* and
    the image field is set to that absolute path so path-existence checks pass
    by default.
    """
    if omit_fields is None:
        omit_fields = []

    # Create a real image file so existence checks succeed by default
    if image is None:
        img_file = tmp_path / "chart.png"
        img_file.write_bytes(_PNG_MAGIC)
        image = str(img_file)

    lines = []
    if "layout" not in omit_fields:
        lines.append(f"layout: {layout}")
    if "title" not in omit_fields:
        lines.append(f'title: "{title}"')
    if "date" not in omit_fields:
        lines.append(f"date: {date}")
    if "author" not in omit_fields:
        lines.append(f'author: "{author}"')
    if "categories" not in omit_fields:
        lines.append(f"categories: {categories}")
    if "image" not in omit_fields:
        lines.append(f"image: {image}")
    if frontmatter_extra:
        lines.append(frontmatter_extra)

    fm = "\n".join(lines)
    content = f"---\n{fm}\n---\n\n{body}\n"
    post = tmp_path / filename
    post.write_text(content, encoding="utf-8")
    return post


# ===========================================================================
# validate_post — return shape
# ===========================================================================


class TestValidatePostReturnShape:
    """validate_post always returns a dict with valid / errors / warnings."""

    def test_returns_dict(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert isinstance(result, dict)

    def test_has_valid_key(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert "valid" in result

    def test_has_errors_key(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert "errors" in result

    def test_has_warnings_key(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert "warnings" in result

    def test_valid_is_bool(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert isinstance(result["valid"], bool)

    def test_errors_is_list(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert isinstance(result["errors"], list)

    def test_warnings_is_list(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert isinstance(result["warnings"], list)


# ===========================================================================
# validate_post — valid post
# ===========================================================================


class TestValidatePostValidPost:
    """A fully-formed valid post should return valid=True, errors=[]."""

    def test_valid_post_returns_valid_true(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert result["valid"] is True, f"Unexpected errors: {result['errors']}"

    def test_valid_post_has_no_errors(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path)
        result = validate_post(str(post))
        assert result["errors"] == []

    def test_http_image_url_accepted(self, tmp_path: Path) -> None:
        """Remote image URLs should not trigger a path-existence check."""
        post = _write_post(tmp_path, image="https://example.com/chart.png")
        result = validate_post(str(post))
        assert result["valid"] is True, f"Unexpected errors: {result['errors']}"

    def test_multiple_valid_categories_accepted(self, tmp_path: Path) -> None:
        cats = '["quality-engineering", "test-automation"]'
        post = _write_post(tmp_path, categories=cats)
        result = validate_post(str(post))
        assert result["valid"] is True, f"Unexpected errors: {result['errors']}"


# ===========================================================================
# validate_post — file I/O errors
# ===========================================================================


class TestValidatePostFileErrors:
    """Non-existent or unreadable files return valid=False immediately."""

    def test_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        result = validate_post(str(tmp_path / "does_not_exist.md"))
        assert result["valid"] is False

    def test_nonexistent_file_error_message(self, tmp_path: Path) -> None:
        result = validate_post(str(tmp_path / "does_not_exist.md"))
        assert len(result["errors"]) >= 1
        assert "not found" in result["errors"][0].lower()


# ===========================================================================
# validate_post — front-matter structure
# ===========================================================================


class TestValidatePostFrontmatter:
    """Missing or malformed YAML front-matter is surfaced as errors."""

    def test_no_frontmatter_delimiter_returns_false(self, tmp_path: Path) -> None:
        post = tmp_path / "no_fm.md"
        post.write_text("No front matter here.\n", encoding="utf-8")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_no_frontmatter_error_message(self, tmp_path: Path) -> None:
        post = tmp_path / "no_fm.md"
        post.write_text("No front matter here.\n", encoding="utf-8")
        result = validate_post(str(post))
        assert any(
            "delimiter" in e.lower() or "front" in e.lower() for e in result["errors"]
        )

    def test_missing_closing_delimiter_returns_false(self, tmp_path: Path) -> None:
        post = tmp_path / "bad_fm.md"
        post.write_text("---\nlayout: post\ntitle: Test\n", encoding="utf-8")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_invalid_yaml_returns_false(self, tmp_path: Path) -> None:
        post = tmp_path / "bad_yaml.md"
        post.write_text("---\n: bad: yaml: here\n---\nBody.\n", encoding="utf-8")
        result = validate_post(str(post))
        assert result["valid"] is False


# ===========================================================================
# validate_post — required fields
# ===========================================================================


class TestValidatePostRequiredFields:
    """Each required field is individually enforced."""

    @pytest.mark.parametrize(
        "field",
        ["layout", "title", "date", "author", "categories", "image"],
    )
    def test_missing_field_returns_false(self, field: str, tmp_path: Path) -> None:
        post = _write_post(
            tmp_path, omit_fields=[field], filename=f"missing_{field}.md"
        )
        result = validate_post(str(post))
        assert result["valid"] is False

    @pytest.mark.parametrize(
        "field",
        ["layout", "title", "date", "author", "categories", "image"],
    )
    def test_missing_field_error_mentions_field(
        self, field: str, tmp_path: Path
    ) -> None:
        post = _write_post(tmp_path, omit_fields=[field], filename=f"err_{field}.md")
        result = validate_post(str(post))
        assert any(field in e for e in result["errors"]), (
            f"Expected '{field}' in errors, got: {result['errors']}"
        )


# ===========================================================================
# validate_post — field-level validation
# ===========================================================================


class TestValidatePostLayout:
    def test_wrong_layout_returns_false(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, layout="page")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_wrong_layout_error_message(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, layout="page")
        result = validate_post(str(post))
        assert any("layout" in e for e in result["errors"])


class TestValidatePostDate:
    def test_invalid_date_format_returns_false(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, date="05-04-2026")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_invalid_date_error_message(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, date="05-04-2026")
        result = validate_post(str(post))
        assert any("date" in e for e in result["errors"])


class TestValidatePostCategories:
    def test_invalid_category_returns_false(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, categories='["not-a-real-category"]')
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_invalid_category_error_message(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, categories='["not-a-real-category"]')
        result = validate_post(str(post))
        assert any(
            "category" in e.lower() or "not-a-real-category" in e
            for e in result["errors"]
        )

    def test_categories_not_a_list_returns_false(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, categories="quality-engineering")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_all_valid_categories_accepted(self, tmp_path: Path) -> None:
        for i, cat in enumerate(VALID_CATEGORIES):
            post = _write_post(
                tmp_path,
                categories=f'["{cat}"]',
                filename=f"cat_{i}.md",
            )
            result = validate_post(str(post))
            assert result["valid"] is True, (
                f"Category '{cat}' should be valid but got errors: {result['errors']}"
            )


class TestValidatePostImagePath:
    def test_missing_image_file_returns_false(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, image="/assets/images/nonexistent.png")
        result = validate_post(str(post))
        assert result["valid"] is False

    def test_missing_image_error_message(self, tmp_path: Path) -> None:
        post = _write_post(tmp_path, image="/assets/images/nonexistent.png")
        result = validate_post(str(post))
        assert any("image" in e.lower() for e in result["errors"])

    def test_existing_image_file_accepted(self, tmp_path: Path) -> None:
        img = tmp_path / "chart.png"
        img.write_bytes(_PNG_MAGIC)
        post = _write_post(tmp_path, image=str(img))
        result = validate_post(str(post))
        # image-related errors should be absent
        image_errors = [e for e in result["errors"] if "image" in e.lower()]
        assert image_errors == [], f"Unexpected image errors: {image_errors}"


# ===========================================================================
# validate_post — MCP tool registration
# ===========================================================================


class TestValidatePostMcpRegistration:
    """validate_post is registered in the FastMCP server."""

    def test_validate_post_tool_listed(self) -> None:
        tool_names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert "validate_post" in tool_names

    def test_validate_post_has_description(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        tool = next(t for t in tools if t.name == "validate_post")
        assert tool.description
