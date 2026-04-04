#!/usr/bin/env python3
"""Tests for the Editorial Judge — post-deployment shift-right quality gate."""

from unittest.mock import patch

import pytest

from scripts.editorial_judge import (
    FAIL,
    PASS,
    WARN,
    CheckResult,
    EditorialJudge,
    JudgeReport,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

VALID_ARTICLE = """---
layout: post
title: "Test Article Title"
date: 2026-04-04
author: "The Economist"
categories: ["Quality Engineering"]
image: /assets/images/test-article.png
---

Software testing has long been a costly affair. According to Gartner,
organisations spend 25% of IT budgets on quality assurance.

## The Problem

Testing costs continue to rise despite automation promises.

## The Evidence

Forrester's 2024 report shows that only 40% of companies see positive ROI.

## References

1. Gartner, ["QA Budget Report"](https://example.com), 2024
2. Forrester, ["Automation ROI Study"](https://example.com), 2024
3. IEEE, ["Testing Standards"](https://example.com), 2024
""" + " ".join(["word"] * 800)  # pad to 800+ words


@pytest.fixture
def judge() -> EditorialJudge:
    """Judge instance with mocked article content."""
    j = EditorialJudge("oviney", "blog", "2026-04-04-test-article.md")
    j._article_content = VALID_ARTICLE
    return j


# ═══════════════════════════════════════════════════════════════════════════
# Frontmatter checks
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontmatter:
    def test_valid_frontmatter_passes(self, judge: EditorialJudge) -> None:
        result = judge.check_frontmatter()
        assert result.status == PASS

    def test_missing_layout_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = (
            '---\ntitle: "Test"\ndate: 2026-04-04\ncategories: ["QE"]\n---\n\nBody'
        )
        result = judge.check_frontmatter()
        assert result.status == FAIL
        assert "layout" in result.message

    def test_missing_categories_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = (
            '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-04\n---\n\nBody'
        )
        result = judge.check_frontmatter()
        assert result.status == FAIL
        assert "categories" in result.message

    def test_no_frontmatter_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = "Just plain text, no frontmatter."
        result = judge.check_frontmatter()
        assert result.status == FAIL


# ═══════════════════════════════════════════════════════════════════════════
# Image checks
# ═══════════════════════════════════════════════════════════════════════════


class TestImageExists:
    def test_image_exists_passes(self, judge: EditorialJudge) -> None:
        with patch.object(judge, "_file_exists", return_value=True):
            result = judge.check_image_exists()
            assert result.status == PASS

    def test_image_missing_fails(self, judge: EditorialJudge) -> None:
        with patch.object(judge, "_file_exists", return_value=False):
            result = judge.check_image_exists()
            assert result.status == FAIL
            assert "not found" in result.message

    def test_no_image_field_warns(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\ncategories: ["QE"]\n---\n\nBody'
        result = judge.check_image_exists()
        assert result.status == WARN


# ═══════════════════════════════════════════════════════════════════════════
# Categories checks
# ═══════════════════════════════════════════════════════════════════════════


class TestCategories:
    def test_categories_present_passes(self, judge: EditorialJudge) -> None:
        result = judge.check_categories()
        assert result.status == PASS
        assert "Quality Engineering" in result.message

    def test_empty_categories_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\ncategories: []\n---\n\nBody'
        result = judge.check_categories()
        assert result.status == FAIL

    def test_missing_categories_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = (
            '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\nBody'
        )
        result = judge.check_categories()
        assert result.status == FAIL


# ═══════════════════════════════════════════════════════════════════════════
# Duplication checks
# ═══════════════════════════════════════════════════════════════════════════


class TestDuplication:
    def test_no_past_posts_passes(self, judge: EditorialJudge) -> None:
        with patch.object(judge, "_list_posts", return_value=[]):
            result = judge.check_duplication()
            assert result.status == PASS

    def test_identical_content_fails(self, judge: EditorialJudge) -> None:
        with (
            patch.object(
                judge,
                "_list_posts",
                return_value=[{"name": "old-post.md", "path": "_posts/old-post.md"}],
            ),
            patch.object(judge, "_fetch_file_content", return_value=VALID_ARTICLE),
        ):
            result = judge.check_duplication()
            assert result.status == FAIL
            assert "100%" in result.message

    def test_different_content_passes(self, judge: EditorialJudge) -> None:
        different_article = "---\ntitle: Different\n---\n\nCompletely unrelated content about cooking recipes and gardening tips."
        with (
            patch.object(
                judge,
                "_list_posts",
                return_value=[{"name": "old-post.md", "path": "_posts/old-post.md"}],
            ),
            patch.object(judge, "_fetch_file_content", return_value=different_article),
        ):
            result = judge.check_duplication()
            assert result.status == PASS


# ═══════════════════════════════════════════════════════════════════════════
# Writing quality checks
# ═══════════════════════════════════════════════════════════════════════════


class TestWritingQuality:
    def test_clean_article_passes(self, judge: EditorialJudge) -> None:
        result = judge.check_writing_quality()
        assert result.status == PASS

    def test_banned_phrase_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        body = " ".join(["word"] * 850)
        judge._article_content = f'---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\nIn conclusion, this is a game-changer. {body}'
        result = judge.check_writing_quality()
        assert result.status == FAIL
        assert "banned phrase" in result.details.lower()

    def test_placeholder_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        body = " ".join(["word"] * 850)
        judge._article_content = f'---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\nSome stat [NEEDS SOURCE]. {body}'
        result = judge.check_writing_quality()
        assert result.status == FAIL

    def test_short_article_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = (
            '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\nToo short.'
        )
        result = judge.check_writing_quality()
        assert result.status == FAIL
        assert "Too short" in result.details


# ═══════════════════════════════════════════════════════════════════════════
# Structure checks
# ═══════════════════════════════════════════════════════════════════════════


class TestStructure:
    def test_valid_structure_passes(self, judge: EditorialJudge) -> None:
        result = judge.check_structure()
        assert result.status == PASS

    def test_missing_references_fails(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\n## Section 1\n\nContent\n\n## Section 2\n\nMore content'
        result = judge.check_structure()
        assert result.status == FAIL
        assert "References" in result.details

    def test_no_headings_warns(self) -> None:
        judge = EditorialJudge("o", "b", "test.md")
        judge._article_content = '---\nlayout: post\ntitle: "T"\ndate: 2026-04-04\n---\n\nJust paragraphs.\n\n## References\n\n1. Source'
        result = judge.check_structure()
        assert result.status == WARN


# ═══════════════════════════════════════════════════════════════════════════
# Report and verdict
# ═══════════════════════════════════════════════════════════════════════════


class TestReport:
    def test_all_pass_verdict(self) -> None:
        report = JudgeReport("Title", "file.md", "url")
        report.checks = [CheckResult("A", PASS, "ok"), CheckResult("B", PASS, "ok")]
        assert report.verdict == "PASS"

    def test_warn_verdict(self) -> None:
        report = JudgeReport("Title", "file.md", "url")
        report.checks = [CheckResult("A", PASS, "ok"), CheckResult("B", WARN, "hmm")]
        assert report.verdict == "NEEDS ATTENTION"

    def test_fail_verdict(self) -> None:
        report = JudgeReport("Title", "file.md", "url")
        report.checks = [CheckResult("A", FAIL, "bad"), CheckResult("B", PASS, "ok")]
        assert report.verdict == "FAIL"

    def test_format_report_contains_checks(self) -> None:
        report = JudgeReport("Test Title", "test.md", "https://example.com")
        report.checks = [
            CheckResult("Frontmatter", PASS, "All fields present"),
            CheckResult("Image", FAIL, "Image not found"),
        ]
        text = EditorialJudge.format_report(report)
        assert "Test Title" in text
        assert "FAIL" in text
        assert "Image not found" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
