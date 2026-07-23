#!/usr/bin/env python3
"""Tests for B-013 promote: ``scripts.promote_review`` (``make publish``).

Promotes an approved unlisted draft (``_review/<slug>-<token>.md``) to a real
post (``_posts/YYYY-MM-DD-<slug>.md``): flips ``layout: review`` back to
``layout: post``, injects the publish date, runs the publication validator as a
blocking gate, removes the review draft, and pushes to the live branch (no PR —
the owner already reviewed the rendered draft).

Subprocess (``run_command``) and the validator are mocked.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.promote_review as pr

_REVIEW_DRAFT = (
    "---\n"
    "layout: review\n"
    'title: "Specific Descriptive Article Title"\n'
    "date: 2026-01-15\n"
    'author: "Ouray Viney"\n'
    'categories: ["Quality Engineering"]\n'
    "---\n\n"
    "Body text.\n\n"
    "![Chart](/assets/charts/my-draft.png)\n"
)


class TestPromote:
    @pytest.fixture(autouse=True)
    def _cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

    def _prepare_clone(self) -> None:
        blog = Path("temp_blog_repo")
        review = blog / "_review"
        review.mkdir(parents=True, exist_ok=True)
        (blog / "_posts").mkdir(parents=True, exist_ok=True)
        (review / "my-draft-deadbeef.md").write_text(_REVIEW_DRAFT)

    def test_promotes_draft_to_post_and_pushes_no_pr(self) -> None:
        commands: list[str] = []
        captured: dict[str, str] = {}

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_clone()
            if cmd.startswith("git add"):
                posts = list(Path("temp_blog_repo/_posts").glob("*my-draft.md"))
                assert posts, "post file not written before git add"
                captured["content"] = posts[0].read_text()
                captured["name"] = posts[0].name
            return ""

        with (
            patch.object(pr, "run_command", side_effect=fake_run_command),
            patch.object(pr, "validate_file", return_value=(True, "✅ ok")),
        ):
            result = pr.promote(
                slug="my-draft",
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
                live_branch="main",
                deploy_date="2026-07-23",
            )

        assert result.status == "published"
        assert result.pushed is True
        # Renamed to a dated post, layout flipped back, date injected.
        assert re.fullmatch(r"2026-07-23-my-draft\.md", captured["name"])
        assert "layout: post" in captured["content"]
        assert "layout: review" not in captured["content"]
        assert "date: 2026-07-23" in captured["content"]
        # The review draft is removed, pushed to live branch, and NO PR opened.
        assert any("git rm" in c and "my-draft-deadbeef.md" in c for c in commands), (
            "review draft not removed"
        )
        assert any(c == "git push origin main" for c in commands)
        assert not any("gh pr create" in c for c in commands)

    def test_missing_draft_raises(self) -> None:
        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                # Materialise an empty _review — no matching draft.
                (Path("temp_blog_repo") / "_review").mkdir(parents=True, exist_ok=True)
                (Path("temp_blog_repo") / "_posts").mkdir(parents=True, exist_ok=True)
            return ""

        with (
            patch.object(pr, "run_command", side_effect=fake_run_command),
            pytest.raises(pr.DeployError, match="No review draft"),
        ):
            pr.promote(
                slug="absent",
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
            )

    def test_validation_failure_blocks_publish(self) -> None:
        commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_clone()
            return ""

        with (
            patch.object(pr, "run_command", side_effect=fake_run_command),
            patch.object(
                pr, "validate_file", return_value=(False, "✗ bad frontmatter")
            ),
        ):
            result = pr.promote(
                slug="my-draft",
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
            )

        assert result.status == "validation_failed"
        assert result.pushed is False
        assert not any(c.startswith("git push") for c in commands), (
            "must not push when validation fails"
        )


def test_cli_main_promotes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    calls: dict[str, object] = {}

    def fake_promote(**kwargs):
        calls.update(kwargs)
        return pr.DeployResult(
            status="published",
            branch="main",
            article_name="2026-07-23-my-draft.md",
            validation_report="",
            pushed=True,
        )

    with patch.object(pr, "promote", side_effect=fake_promote):
        rc = pr.main(
            [
                "--slug",
                "my-draft",
                "--blog-owner",
                "test-owner",
                "--blog-repo",
                "test-blog",
                "--token",
                "t",
            ]
        )

    assert rc == 0
    assert calls["slug"] == "my-draft"
