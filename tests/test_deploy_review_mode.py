#!/usr/bin/env python3
"""Tests for B-013 review mode: ``deploy_review()`` + ``--mode review``.

Review mode writes an *unlisted* draft to the blog's ``_review/`` collection at
an obscure ``<slug>-<token>`` name, commits it directly to the live branch, and
opens **no PR** — the owner reviews the rendered post at the printed URL. The
default ``--mode post`` path is untouched (a separate function guarantees it).

Subprocess (``run_command``) is mocked so no git/network happens.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.deploy_to_blog as dtb

VALID_REFERENCES = """## References

1. Gartner, ["World Quality Report 2024"](https://example.com), *Gartner*, 2024
"""
VALID_BODY = " ".join(["word"] * 850)


def _make_article(*, date: str = "2026-01-15") -> str:
    return (
        "---\n"
        "layout: post\n"
        'title: "Specific Descriptive Article Title"\n'
        f"date: {date}\n"
        'author: "Ouray Viney"\n'
        'categories: ["Quality Engineering"]\n'
        "---\n\n"
        f"{VALID_BODY}\n\n"
        "![Chart](output/charts/my-draft.png)\n\n"
        f"{VALID_REFERENCES}\n"
    )


# ── pure content transform ───────────────────────────────────────────


def test_to_review_content_rewrites_layout_and_chart_paths() -> None:
    src = "---\nlayout: post\ntitle: X\n---\n\nBody ![c](output/charts/x.png)\n"
    out = dtb._to_review_content(src)
    assert "layout: review" in out
    assert "layout: post" not in out
    assert "/assets/charts/x.png" in out
    assert "output/charts/" not in out


# ── deploy_review() orchestration ────────────────────────────────────


class TestDeployReview:
    @pytest.fixture
    def article_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.chdir(tmp_path)
        article = tmp_path / "2026-01-15-my-draft.md"
        article.write_text(_make_article())
        charts = tmp_path / "output" / "charts"
        charts.mkdir(parents=True)
        (charts / "my-draft.png").write_bytes(b"PNG")
        return article

    def _prepare_clone(self) -> None:
        blog = Path("temp_blog_repo")
        (blog / "_review").mkdir(parents=True, exist_ok=True)
        (blog / "assets" / "charts").mkdir(parents=True, exist_ok=True)

    def test_writes_unlisted_draft_to_live_branch_with_no_pr(
        self, article_file: Path
    ) -> None:
        commands: list[str] = []
        captured: dict[str, str] = {}

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_clone()
            if cmd.startswith("git add"):
                # Capture the draft content *before* deploy_review cleans up.
                written = list(Path("temp_blog_repo/_review").glob("my-draft-*.md"))
                assert written, "review draft not written before git add"
                captured["content"] = written[0].read_text()
                captured["name"] = written[0].name
            return ""

        with patch.object(dtb, "run_command", side_effect=fake_run_command):
            result = dtb.deploy_review(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
                live_branch="main",
                host="viney.ca",
            )

        # Outcome
        assert result.status == "review_published"
        assert result.pushed is True
        assert result.url is not None
        assert re.fullmatch(
            r"https://viney\.ca/review/my-draft-[0-9a-f]{8}/", result.url
        ), result.url

        # Draft written with the review layout + rewritten chart path.
        assert re.fullmatch(r"my-draft-[0-9a-f]{8}\.md", captured["name"])
        assert "layout: review" in captured["content"]
        assert "/assets/charts/my-draft.png" in captured["content"]

        # Committed + pushed to the LIVE branch, no feature branch, NO PR.
        assert any(c == "git checkout main" for c in commands), (
            "did not use live branch"
        )
        assert any(c == "git push origin main" for c in commands), (
            "did not push to main"
        )
        assert not any(c.startswith("git checkout -b") for c in commands), (
            "review mode must not create a content branch"
        )
        assert not any("gh pr create" in c for c in commands), (
            "review mode must not open a PR"
        )

    def test_default_host_is_canonical_www(self, article_file: Path) -> None:
        # BUG-052: the blog's canonical URL is www.viney.ca; deploy_review must
        # default there so the printed review URL doesn't 404/redirect on the apex.
        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._prepare_clone()
            return ""

        with patch.object(dtb, "run_command", side_effect=fake_run_command):
            result = dtb.deploy_review(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
            )  # no host= → exercises the default
        assert result.url is not None
        assert result.url.startswith("https://www.viney.ca/review/"), result.url

    def test_missing_chart_asset_raises(self, article_file: Path) -> None:
        # Remove the fallback chart so the referenced asset is absent.
        (Path("output/charts/my-draft.png")).unlink()

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._prepare_clone()
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            pytest.raises(dtb.DeployError, match="Chart asset not found"),
        ):
            dtb.deploy_review(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="t",
            )


# ── CLI dispatch: --mode review calls deploy_review ──────────────────


def test_cli_mode_review_dispatches_to_deploy_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    article = tmp_path / "2026-01-15-my-draft.md"
    article.write_text(_make_article())

    calls: dict[str, object] = {}

    def fake_deploy_review(**kwargs):
        calls.update(kwargs)
        return dtb.DeployResult(
            status="review_published",
            branch="main",
            article_name="my-draft-deadbeef.md",
            validation_report="",
            pushed=True,
            url="https://viney.ca/review/my-draft-deadbeef/",
        )

    with (
        patch.object(dtb, "deploy_review", side_effect=fake_deploy_review),
        patch.object(dtb, "deploy") as post_deploy,
    ):
        rc = dtb.main(
            [
                "--mode",
                "review",
                "--article",
                str(article),
                "--blog-owner",
                "test-owner",
                "--blog-repo",
                "test-blog",
                "--token",
                "t",
            ]
        )

    assert rc == 0
    assert calls["blog_owner"] == "test-owner"
    post_deploy.assert_not_called()  # post path untouched in review mode
