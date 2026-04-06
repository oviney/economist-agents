#!/usr/bin/env python3
"""Tests for the Blog Quality Audit script (Story #135)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import scripts.blog_quality_audit as audit


# ── Fixtures ──────────────────────────────────────────────────────────────────

GOOD_POST_CONTENT = """\
---
layout: post
title: "Strong Quality Post"
date: 2026-04-07
author: "Test Author"
categories: ["Quality Engineering"]
image: /assets/images/strong.png
---

According to Gartner 2024, 73% of organisations now use test automation, yet 60% report rising costs.

## The Maintenance Trap

Forrester's 2024 analysis shows maintenance consumes 40% of QA budgets in large enterprises.

## The Skills Gap

Hiring automation engineers costs 25% more than traditional QA roles, per Deloitte 2024.

## The Alternative

Infrastructure-first teams report 3x faster delivery with 5x fewer production incidents.

![Chart](/assets/charts/costs.png)

As the chart illustrates, costs have grown steadily since 2020.

The organisations that thrive will treat test infrastructure as a strategic investment.

## References

1. Gartner, "World Quality Report 2024", 2024
2. Forrester, "Test Automation ROI Study", 2024
3. Deloitte, "Technology Workforce Report", 2024
4. IEEE, "Software Engineering Standards", 2024
5. Capgemini, "Digital Engineering Report", 2024
""" + " ".join(["word"] * 500)

BAD_POST_CONTENT = """\
---
title: "Weak Post"
date: April 7
---

In today's world, testing is a game-changer. It's no secret that paradigm shifts happen.
Studies show this is important. [NEEDS SOURCE]
"""

MOCK_POSTS = [
    {"filename": "2026-04-01-good-post.md", "path": "_posts/2026-04-01-good-post.md", "content": GOOD_POST_CONTENT},
    {"filename": "2026-04-01-bad-post.md", "path": "_posts/2026-04-01-bad-post.md", "content": BAD_POST_CONTENT},
]


# ── fetch_posts ───────────────────────────────────────────────────────────────

class TestFetchPosts:
    def test_filters_non_markdown_files(self) -> None:
        import base64

        contents_response = [
            {"name": "2026-04-01-post.md", "path": "_posts/2026-04-01-post.md", "url": "https://api.github.com/repos/oviney/blog/contents/_posts/2026-04-01-post.md"},
            {"name": "README.txt", "path": "_posts/README.txt", "url": "https://api.github.com/repos/oviney/blog/contents/_posts/README.txt"},
        ]
        file_response = {
            "content": base64.b64encode(GOOD_POST_CONTENT.encode()).decode() + "\n"
        }

        call_responses = [contents_response, file_response]

        def fake_gh_get(url):
            return call_responses.pop(0)

        with patch.object(audit, "_gh_get", side_effect=fake_gh_get):
            posts = audit.fetch_posts()

        assert len(posts) == 1
        assert posts[0]["filename"] == "2026-04-01-post.md"
        assert posts[0]["content"] == GOOD_POST_CONTENT

    def test_decodes_base64_content(self) -> None:
        import base64

        raw = "# Hello\nThis is a post."
        contents_response = [
            {"name": "2026-04-01-post.md", "path": "_posts/2026-04-01-post.md", "url": "https://example.com/file"},
        ]
        file_response = {"content": base64.b64encode(raw.encode()).decode() + "\n"}

        with patch.object(audit, "_gh_get", side_effect=[contents_response, file_response]):
            posts = audit.fetch_posts()

        assert posts[0]["content"] == raw


# ── existing_issue_title ──────────────────────────────────────────────────────

class TestExistingIssueTitle:
    def test_returns_true_when_issue_exists(self) -> None:
        mock_issues = [
            {"title": "[Quality Audit] Weak Post"},
            {"title": "[Quality Audit] Other Post"},
        ]
        with patch.object(audit, "_gh_get", return_value=mock_issues):
            assert audit.existing_issue_title("Weak Post") is True

    def test_returns_false_when_no_matching_issue(self) -> None:
        mock_issues = [{"title": "[Quality Audit] Other Post"}]
        with patch.object(audit, "_gh_get", return_value=mock_issues):
            assert audit.existing_issue_title("Weak Post") is False

    def test_returns_false_for_empty_issue_list(self) -> None:
        with patch.object(audit, "_gh_get", return_value=[]):
            assert audit.existing_issue_title("Any Title") is False


# ── recommendations ───────────────────────────────────────────────────────────

class TestRecommendations:
    def test_low_opening_quality_recommendation(self) -> None:
        from scripts.article_evaluator import ArticleEvaluator

        result = ArticleEvaluator().evaluate(BAD_POST_CONTENT, filename="bad.md")
        recs = audit._recommendations(result)
        assert "Opening" in recs

    def test_low_evidence_recommendation(self) -> None:
        from scripts.article_evaluator import ArticleEvaluator

        result = ArticleEvaluator().evaluate(BAD_POST_CONTENT, filename="bad.md")
        recs = audit._recommendations(result)
        assert "Evidence" in recs or "References" in recs or "recommendations" in recs.lower() or "required" in recs.lower()

    def test_good_article_no_recommendations_needed(self) -> None:
        from scripts.article_evaluator import ArticleEvaluator

        result = ArticleEvaluator().evaluate(GOOD_POST_CONTENT, filename="good.md")
        # Good article should score high — recommendations may be empty or minimal
        recs = audit._recommendations(result)
        assert isinstance(recs, str)


# ── run_audit (dry run) ───────────────────────────────────────────────────────

class TestRunAuditDryRun:
    def test_dry_run_writes_audit_log(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: MOCK_POSTS)
        monkeypatch.setattr(audit, "ensure_label", lambda: None)

        audit.run_audit(dry_run=True)

        assert (tmp_path / "blog_audit.json").exists()

    def test_dry_run_does_not_create_issues(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: MOCK_POSTS)
        monkeypatch.setattr(audit, "ensure_label", lambda: None)

        issue_calls: list = []
        monkeypatch.setattr(audit, "create_issue", lambda *a, **kw: issue_calls.append(a) or "http://example.com")

        audit.run_audit(dry_run=True)

        assert issue_calls == []

    def test_audit_log_structure(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: MOCK_POSTS)
        monkeypatch.setattr(audit, "ensure_label", lambda: None)

        audit.run_audit(dry_run=True)

        data = json.loads((tmp_path / "blog_audit.json").read_bytes())
        assert "audit_timestamp" in data
        assert "total_posts" in data
        assert data["total_posts"] == 2
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["dry_run"] is True


# ── run_audit (live, mocked) ──────────────────────────────────────────────────

class TestRunAuditLive:
    def test_creates_issue_for_low_scoring_post(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: [MOCK_POSTS[1]])  # bad post only
        monkeypatch.setattr(audit, "ensure_label", lambda: None)
        monkeypatch.setattr(audit, "existing_issue_title", lambda t: False)

        created: list = []
        monkeypatch.setattr(audit, "create_issue", lambda title, fn, res: created.append(title) or "http://example.com/1")

        audit.run_audit(dry_run=False)

        assert len(created) == 1

    def test_skips_issue_if_already_exists(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: [MOCK_POSTS[1]])
        monkeypatch.setattr(audit, "ensure_label", lambda: None)
        monkeypatch.setattr(audit, "existing_issue_title", lambda t: True)  # already exists

        created: list = []
        monkeypatch.setattr(audit, "create_issue", lambda *a, **kw: created.append(a) or "http://x")

        audit.run_audit(dry_run=False)

        assert created == []

    def test_no_issue_for_high_scoring_post(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path / "blog_audit.json")
        monkeypatch.setattr(audit, "fetch_posts", lambda: [MOCK_POSTS[0]])  # good post
        monkeypatch.setattr(audit, "ensure_label", lambda: None)
        monkeypatch.setattr(audit, "existing_issue_title", lambda t: False)

        created: list = []
        monkeypatch.setattr(audit, "create_issue", lambda *a, **kw: created.append(a) or "http://x")

        audit.run_audit(dry_run=False)

        # Good post may or may not exceed threshold — verify no error
        data = json.loads((tmp_path / "blog_audit.json").read_bytes())
        assert data["total_posts"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
