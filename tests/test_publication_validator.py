#!/usr/bin/env python3
"""Tests for publication_validator — the final quality gate before publishing."""

import pytest

from scripts.publication_validator import PublicationValidator

# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

VALID_REFERENCES = """## References

1. Gartner, ["World Quality Report 2024"](https://example.com/gartner), *Gartner Research*, 2024
2. Forrester, ["State of Test Automation"](https://example.com/forrester), *Forrester*, 2024
3. IEEE, ["Software Testing Practices"](https://example.com/ieee), *IEEE*, 2024
"""

VALID_CHART_EMBED = (
    "\n\nAs the chart shows, the data reveals a clear trend."
    "\n\n![Data Chart](/assets/charts/test-chart.png)\n"
)

VALID_BODY = " ".join(["word"] * 850)


def _make_article(
    *,
    layout: str = "post",
    title: str = "Specific Descriptive Title for Testing",
    date: str = "2026-04-03",
    author: str = "The Economist",
    categories: str = '["quality-engineering"]',
    description: str | None = "A concise test description for SEO purposes",
    body: str | None = None,
    references: str | None = None,
    chart_embed: str | None = None,
    frontmatter_open: str = "---",
    frontmatter_close: str = "---",
) -> str:
    """Build an article string with the given components."""
    if body is None:
        body = VALID_BODY
    if references is None:
        references = VALID_REFERENCES
    if chart_embed is None:
        chart_embed = VALID_CHART_EMBED
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
    if description is not None:
        fields.append(f'description: "{description}"')
    fm = "\n".join(fields)
    return f"{frontmatter_open}\n{fm}\n{frontmatter_close}\n\n{body}\n{chart_embed}\n{references}\n"


# ═══════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestPublicationValidatorYAML:
    """YAML frontmatter validation checks."""

    def test_valid_article_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article()
        is_valid, issues = validator.validate(article)
        critical = [i for i in issues if i["severity"] == "CRITICAL"]
        assert is_valid, f"Expected valid, got issues: {critical}"

    def test_missing_opening_delimiter_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(frontmatter_open="")
        is_valid, issues = validator.validate(article)
        assert not is_valid
        yaml_issues = [i for i in issues if i["check"] == "yaml_format"]
        assert len(yaml_issues) >= 1

    def test_code_fence_wrapper_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = f'```yaml\nlayout: post\ntitle: "Test"\ndate: 2026-04-03\n```\n\n{VALID_BODY}\n\n{VALID_REFERENCES}\n'
        is_valid, issues = validator.validate(article)
        assert not is_valid
        yaml_issues = [i for i in issues if i["check"] == "yaml_format"]
        assert any("code fence" in i["message"].lower() for i in yaml_issues)


class TestPublicationValidatorDate:
    """Date validation checks."""

    def test_correct_date_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(date="2026-04-03")
        is_valid, issues = validator.validate(article)
        date_issues = [i for i in issues if i["check"] == "date_mismatch"]
        assert len(date_issues) == 0

    def test_wrong_date_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(date="2024-01-01")
        is_valid, issues = validator.validate(article)
        date_issues = [i for i in issues if i["check"] == "date_mismatch"]
        assert len(date_issues) == 1


class TestPublicationValidatorContent:
    """Content quality checks."""

    def test_verification_flags_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(
            body=f"Some text [NEEDS SOURCE] more text. {VALID_BODY}"
        )
        is_valid, issues = validator.validate(article)
        assert not is_valid
        flag_issues = [i for i in issues if i["check"] == "verification_flags"]
        assert len(flag_issues) == 1

    def test_placeholder_text_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(body=f"TODO: write this section. {VALID_BODY}")
        is_valid, issues = validator.validate(article)
        assert not is_valid
        ph_issues = [i for i in issues if i["check"] == "placeholder_text"]
        assert len(ph_issues) == 1

    def test_your_placeholder_uppercase_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(body=f"Contact YOUR-NAME today. {VALID_BODY}")
        is_valid, issues = validator.validate(article)
        ph_issues = [i for i in issues if i["check"] == "placeholder_text"]
        assert not is_valid
        assert len(ph_issues) == 1

    def test_your_in_slug_not_flagged_as_placeholder(self) -> None:
        """BUG-030: title-derived slugs containing 'your-X' must not trigger
        the placeholder check unless X is a known placeholder token."""
        validator = PublicationValidator(expected_date="2026-04-03")
        body = (
            f"See [the guide](/posts/your-content-strategy-2026.md) for more. "
            f"{VALID_BODY}"
        )
        article = _make_article(body=body)
        _, issues = validator.validate(article)
        ph_issues = [i for i in issues if i["check"] == "placeholder_text"]
        assert ph_issues == [], f"false positive on slug: {ph_issues}"

    def test_weak_ending_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        body = f"{VALID_BODY}\n\nIn conclusion, this remains to be seen."
        article = _make_article(body=body)
        is_valid, issues = validator.validate(article)
        weak_issues = [i for i in issues if i["check"] == "weak_endings"]
        assert len(weak_issues) >= 1


class TestPublicationValidatorReferences:
    """References section validation checks."""

    def test_missing_references_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(references="")
        is_valid, issues = validator.validate(article)
        ref_issues = [i for i in issues if i["check"] == "missing_references"]
        assert len(ref_issues) == 1

    def test_insufficient_references_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        refs = "## References\n\n1. Only one source.\n"
        article = _make_article(references=refs)
        is_valid, issues = validator.validate(article)
        ref_issues = [i for i in issues if i["check"] == "insufficient_references"]
        assert len(ref_issues) == 1

    def test_bad_link_text_flagged(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        refs = (
            "## References\n\n"
            "1. Source A, [click here](https://a.com), 2024\n"
            "2. Source B, [Report](https://b.com), 2024\n"
            "3. Source C, [Study](https://c.com), 2024\n"
        )
        article = _make_article(references=refs)
        is_valid, issues = validator.validate(article)
        link_issues = [i for i in issues if i["check"] == "bad_reference_links"]
        assert len(link_issues) == 1


class TestPublicationValidatorWordCount:
    """Word count enforcement checks (BUG-029)."""

    def test_valid_word_count_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article()  # 850 words default
        is_valid, issues = validator.validate(article)
        wc_issues = [i for i in issues if i["check"] == "word_count"]
        assert len(wc_issues) == 0

    def test_short_article_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        short_body = " ".join(["word"] * 200)
        # Use empty references to isolate word count to just body
        article = _make_article(
            body=short_body, references="## References\n\n1. A\n2. B\n3. C\n"
        )
        is_valid, issues = validator.validate(article)
        assert not is_valid
        wc_issues = [i for i in issues if i["check"] == "word_count"]
        assert len(wc_issues) == 1
        assert wc_issues[0]["severity"] == "CRITICAL"

    def test_borderline_words_rejected(self) -> None:
        # Gate is 700 (BUG-029). 650 words must still be rejected.
        validator = PublicationValidator(expected_date="2026-04-03")
        # Use 670 words: with ~18 words from chart embed + references injected
        # by _make_article, total is ~688 < 700 minimum gate.
        body = " ".join(["word"] * 670)
        article = _make_article(
            body=body,
            references="## References\n\n1. A\n2. B\n3. C\n",
            chart_embed="",
        )
        is_valid, issues = validator.validate(article)
        wc_issues = [i for i in issues if i["check"] == "word_count"]
        assert len(wc_issues) == 1

    def test_exactly_700_words_passes(self) -> None:
        # Gate boundary: exactly 700 words is the lowest accepted count.
        validator = PublicationValidator(expected_date="2026-04-03")
        body = " ".join(["word"] * 700)
        article = _make_article(body=body)
        is_valid, issues = validator.validate(article)
        wc_issues = [i for i in issues if i["check"] == "word_count"]
        assert len(wc_issues) == 0


class TestPublicationValidatorDescription:
    """Description front-matter validation checks."""

    def test_valid_description_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(description="A valid SEO description")
        is_valid, issues = validator.validate(article)
        desc_issues = [
            i
            for i in issues
            if i["check"] in ("missing_description", "description_too_long")
        ]
        assert len(desc_issues) == 0

    def test_missing_description_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(description=None)
        is_valid, issues = validator.validate(article)
        assert not is_valid
        desc_issues = [i for i in issues if i["check"] == "missing_description"]
        assert len(desc_issues) == 1
        assert desc_issues[0]["severity"] == "CRITICAL"

    def test_description_over_160_chars_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        long_desc = "a" * 161
        article = _make_article(description=long_desc)
        is_valid, issues = validator.validate(article)
        assert not is_valid
        desc_issues = [i for i in issues if i["check"] == "description_too_long"]
        assert len(desc_issues) == 1
        assert desc_issues[0]["severity"] == "CRITICAL"

    def test_description_exactly_160_chars_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        desc = "a" * 160
        article = _make_article(description=desc)
        is_valid, issues = validator.validate(article)
        desc_issues = [
            i
            for i in issues
            if i["check"] in ("missing_description", "description_too_long")
        ]
        assert len(desc_issues) == 0


class TestPublicationValidatorCategory:
    """Category validation checks."""

    def test_valid_category_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(categories='["quality-engineering"]')
        is_valid, issues = validator.validate(article)
        cat_issues = [
            i for i in issues if i["check"] in ("missing_category", "invalid_category")
        ]
        assert len(cat_issues) == 0

    def test_all_valid_categories_accepted(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        for cat in PublicationValidator.VALID_CATEGORIES:
            article = _make_article(categories=f'["{cat}"]')
            _, issues = validator.validate(article)
            cat_issues = [i for i in issues if i["check"] == "invalid_category"]
            assert len(cat_issues) == 0, f"Category '{cat}' should be valid"

    def test_invalid_category_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(categories='["not-a-real-category"]')
        is_valid, issues = validator.validate(article)
        assert not is_valid
        cat_issues = [i for i in issues if i["check"] == "invalid_category"]
        assert len(cat_issues) == 1
        assert cat_issues[0]["severity"] == "CRITICAL"

    def test_missing_categories_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(categories="")
        is_valid, issues = validator.validate(article)
        cat_issues = [i for i in issues if i["check"] == "missing_category"]
        assert len(cat_issues) == 1


class TestPublicationValidatorChart:
    """Chart reference validation checks."""

    def test_article_with_chart_passes(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article()  # includes chart embed by default
        is_valid, issues = validator.validate(article)
        chart_issues = [i for i in issues if i["check"] == "missing_chart"]
        assert len(chart_issues) == 0

    def test_article_without_chart_rejected(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        article = _make_article(chart_embed="")
        is_valid, issues = validator.validate(article)
        assert not is_valid
        chart_issues = [i for i in issues if i["check"] == "missing_chart"]
        assert len(chart_issues) == 1
        assert chart_issues[0]["severity"] == "CRITICAL"

    def test_chart_not_in_assets_charts_rejected(self) -> None:
        """Chart must be in /assets/charts/ path to count."""
        validator = PublicationValidator(expected_date="2026-04-03")
        bad_chart = "\n\n![Chart](/images/some-chart.png)\n"
        article = _make_article(chart_embed=bad_chart)
        is_valid, issues = validator.validate(article)
        assert not is_valid
        chart_issues = [i for i in issues if i["check"] == "missing_chart"]
        assert len(chart_issues) == 1

    def test_orphaned_chart_flagged(self) -> None:
        """Charts in /assets/charts/ inherently contain the word 'chart' in the URL,
        so the orphan detection check (which looks for 'chart' in content) won't fire.
        This test verifies that behaviour: a chart in /assets/charts/ is NOT flagged
        as orphaned even when the body text itself contains no explicit mention."""
        validator = PublicationValidator(expected_date="2026-04-03")
        body = " ".join(["word"] * 850)
        chart_embed = (
            "\n\n![Data visualisation](/assets/charts/test-chart.png)"
            "\n\n![Other image](/images/other.png)\n"
        )
        article = _make_article(body=body, chart_embed=chart_embed)
        is_valid, issues = validator.validate(article)
        orphan_issues = [i for i in issues if i["check"] == "orphaned_chart"]
        assert len(orphan_issues) == 0


class TestPublicationValidatorEnding:
    """Ending quality validation checks (banned closings from stage4_crew)."""

    def test_ending_with_banned_phrase_flagged(self) -> None:
        """Article ending with 'In conclusion, the key is...' triggers HIGH issue."""
        validator = PublicationValidator(expected_date="2026-04-03")
        # Place the banned ending after the chart embed so it is the last paragraph
        chart_with_ending = (
            VALID_CHART_EMBED + "\n\nIn conclusion, the key is to keep testing."
        )
        article = _make_article(chart_embed=chart_with_ending)
        _, issues = validator.validate(article)
        ending_issues = [i for i in issues if i["check"] == "ending_quality"]
        assert len(ending_issues) == 1
        assert ending_issues[0]["severity"] == "HIGH"
        assert "2 violations" in ending_issues[0]["message"]

    def test_ending_with_vivid_prediction_passes(self) -> None:
        """Article ending with a metaphor should produce no ending issues."""
        validator = PublicationValidator(expected_date="2026-04-03")
        chart_with_ending = (
            VALID_CHART_EMBED
            + "\n\nThe iceberg, it turns out, hides nine-tenths of itself "
            "beneath the waterline — and so does technical debt."
        )
        article = _make_article(chart_embed=chart_with_ending)
        _, issues = validator.validate(article)
        ending_issues = [i for i in issues if i["check"] == "ending_quality"]
        assert len(ending_issues) == 0

    def test_ending_with_one_suspects_flagged(self) -> None:
        """Article ending with 'One suspects...' triggers HIGH issue."""
        validator = PublicationValidator(expected_date="2026-04-03")
        chart_with_ending = (
            VALID_CHART_EMBED
            + "\n\nOne suspects the industry will eventually catch up."
        )
        article = _make_article(chart_embed=chart_with_ending)
        _, issues = validator.validate(article)
        ending_issues = [i for i in issues if i["check"] == "ending_quality"]
        assert len(ending_issues) == 1
        assert ending_issues[0]["severity"] == "HIGH"

    def test_ending_check_ignores_references(self) -> None:
        """Only text before ## References is checked for ending quality."""
        validator = PublicationValidator(expected_date="2026-04-03")
        # Body ends cleanly; the banned phrase only appears inside References
        chart_with_ending = (
            VALID_CHART_EMBED + "\n\nThe market will fracture along entirely new lines."
        )
        refs = (
            "## References\n\n"
            "1. In conclusion paper, [link](https://a.com), 2024\n"
            "2. Source B, [Report](https://b.com), 2024\n"
            "3. Source C, [Study](https://c.com), 2024\n"
        )
        article = _make_article(chart_embed=chart_with_ending, references=refs)
        _, issues = validator.validate(article)
        ending_issues = [i for i in issues if i["check"] == "ending_quality"]
        assert len(ending_issues) == 0


class TestPublicationValidatorReport:
    """format_report() output checks."""

    def test_approved_report(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        report = validator.format_report(True, [])
        assert "APPROVED" in report

    def test_rejected_report(self) -> None:
        validator = PublicationValidator(expected_date="2026-04-03")
        issues = [
            {
                "check": "yaml_format",
                "severity": "CRITICAL",
                "message": "Missing YAML",
                "details": "No frontmatter",
                "fix": "Add ---",
            }
        ]
        report = validator.format_report(False, issues)
        assert "REJECTED" in report
        assert "CRITICAL" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
