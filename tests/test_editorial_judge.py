#!/usr/bin/env python3
"""Tests for the Editorial Judge — post-deployment shift-right quality gate."""

from unittest.mock import Mock, patch

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


# ═══════════════════════════════════════════════════════════════════════════
# GitHub issue creation with agent logs
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateGithubIssue:
    """Tests for create_github_issue() with agent traceability log support."""

    def _failing_report(self) -> JudgeReport:
        report = JudgeReport("Bad Article", "bad.md", "https://example.com/bad")
        report.checks = [CheckResult("Image", FAIL, "Image not found")]
        return report

    def _passing_report(self) -> JudgeReport:
        report = JudgeReport("Good Article", "good.md", "https://example.com/good")
        report.checks = [CheckResult("All", PASS, "All checks passed")]
        return report

    def test_no_issue_when_no_failures(self) -> None:
        judge = EditorialJudge("o", "b", "good.md")
        result = judge.create_github_issue(self._passing_report())
        assert result is None

    def test_issue_created_on_failure(self) -> None:
        judge = EditorialJudge("o", "b", "bad.md")
        report = self._failing_report()

        with patch("scripts.editorial_judge.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "https://github.com/o/r/issues/42\n"
            url = judge.create_github_issue(report)

        assert url == "https://github.com/o/r/issues/42"
        # Verify gh issue create was called
        create_call = mock_run.call_args_list[0]
        assert "issue" in create_call[0][0]
        assert "create" in create_call[0][0]

    def test_agent_logs_posted_as_comment_on_success(self) -> None:
        judge = EditorialJudge("o", "b", "bad.md")
        report = self._failing_report()
        agent_logs = "## 🔍 Agent Traceability Log\n\nSome trace data"

        create_result = Mock(
            returncode=0, stdout="https://github.com/o/r/issues/99\n", stderr=""
        )
        comment_result = Mock(returncode=0, stdout="", stderr="")

        with patch("scripts.editorial_judge.subprocess.run") as mock_run:
            mock_run.side_effect = [create_result, comment_result]
            url = judge.create_github_issue(report, agent_logs=agent_logs)

        assert url == "https://github.com/o/r/issues/99"
        assert mock_run.call_count == 2
        comment_call_args = mock_run.call_args_list[1][0][0]
        assert "issue" in comment_call_args
        assert "comment" in comment_call_args
        # The agent log body should be passed as --body argument
        body_index = comment_call_args.index("--body")
        assert comment_call_args[body_index + 1] == agent_logs

    def test_no_comment_when_agent_logs_none(self) -> None:
        judge = EditorialJudge("o", "b", "bad.md")
        report = self._failing_report()

        with patch("scripts.editorial_judge.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "https://github.com/o/r/issues/7\n"
            judge.create_github_issue(report, agent_logs=None)

        # Only 1 call: issue create (no comment call)
        assert mock_run.call_count == 1

    def test_returns_none_when_gh_fails(self) -> None:
        judge = EditorialJudge("o", "b", "bad.md")
        report = self._failing_report()

        with patch("scripts.editorial_judge.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "gh: command not found"
            url = judge.create_github_issue(report)

        assert url is None

    def test_comment_failure_does_not_raise(self) -> None:
        """A comment posting failure should log a warning, not propagate."""
        judge = EditorialJudge("o", "b", "bad.md")
        report = self._failing_report()
        agent_logs = "## Trace"

        create_result = Mock(
            returncode=0, stdout="https://github.com/o/r/issues/5\n", stderr=""
        )
        comment_result = Mock(returncode=1, stdout="", stderr="error")

        with patch("scripts.editorial_judge.subprocess.run") as mock_run:
            mock_run.side_effect = [create_result, comment_result]
            # Should not raise
            url = judge.create_github_issue(report, agent_logs=agent_logs)

        assert url == "https://github.com/o/r/issues/5"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
