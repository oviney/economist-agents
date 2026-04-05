#!/usr/bin/env python3
"""Tests for mcp_servers/publication_validator_server.py

Validates that the MCP tool correctly wraps PublicationValidator.validate()
and returns the expected result structure.
"""

import asyncio

from mcp_servers.publication_validator_server import mcp, validate_for_publication

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
        assert result["is_valid"] is True, f"Expected is_valid=True, got issues: {critical}"

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
        tool_names = [
            t.name for t in asyncio.run(mcp.list_tools())
        ]
        assert "validate_for_publication" in tool_names

    def test_tool_has_description(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        tool = next(t for t in tools if t.name == "validate_for_publication")
        assert tool.description
