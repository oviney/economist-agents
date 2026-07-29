#!/usr/bin/env python3
"""Regression for BUG-065: the hero-prompt comment must never reach the blog.

The ``<!-- HERO IMAGE — generate an image from the prompt below, then replace
this whole comment with it -->`` block shipped into the published flaky-tests
post and sat in the live page source. It is invisible in the render, but it is
pipeline instructions on a public page.

The publication validator cannot catch it: ``_maybe_inject_hero_prompt`` runs
*after* ``run_stage4`` by design ("so validation is unchanged"), so the comment
does not exist yet when the validator looks. The gate therefore belongs at the
**deploy boundary** — the last point before anything becomes public — and it
guards BOTH entry points, because a review deploy is a live URL too.

The guard REJECTS rather than strips: silently deleting the comment would hide
that no hero was drawn, and a heroless article fails the blog's required
``image:`` anyway (B-019).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.deploy_to_blog import DeployError, deploy, deploy_review

_MARKER = (
    "<!-- HERO IMAGE — generate an image from the prompt below, then replace "
    "this whole comment with it (see output/posts/<slug>.image_prompt.md):\n\n"
    "Draw something editorial.\n-->\n\n"
)
_FRONTMATTER = "---\nlayout: post\ntitle: t\nimage: /assets/images/t-hero.svg\n---\n\n"
_BODY = "Body paragraph. As the chart shows, things happen.\n"


def _write(tmp_path: Path, content: str) -> Path:
    article = tmp_path / "2026-07-28-a-post.md"
    article.write_text(content)
    return article


def test_deploy_refuses_an_article_carrying_the_hero_prompt_comment(
    tmp_path: Path,
) -> None:
    article = _write(tmp_path, _FRONTMATTER + _MARKER + _BODY)

    with pytest.raises(DeployError) as excinfo:
        deploy(
            article_path=article,
            blog_owner="oviney",
            blog_repo="blog",
            token="fake-token",
        )

    message = str(excinfo.value)
    assert article.name in message, "the operator needs to know WHICH file"
    assert "prompt comment" in message.lower()


def test_deploy_review_refuses_it_too(tmp_path: Path) -> None:
    """A review deploy is an unlisted LIVE url — same exposure, same gate."""
    article = _write(tmp_path, _FRONTMATTER + _MARKER + _BODY)

    with pytest.raises(DeployError) as excinfo:
        deploy_review(
            article_path=article,
            blog_owner="oviney",
            blog_repo="blog",
            token="fake-token",
        )

    assert "prompt comment" in str(excinfo.value).lower()


def test_the_guard_fires_before_anything_is_cloned_or_pushed(tmp_path: Path) -> None:
    """It must abort on the local file, not after network work has begun —
    the fake token would otherwise fail with a git error instead."""
    article = _write(tmp_path, _FRONTMATTER + _MARKER + _BODY)

    with pytest.raises(DeployError) as excinfo:
        deploy(
            article_path=article,
            blog_owner="oviney",
            blog_repo="blog",
            token="fake-token",
        )

    message = str(excinfo.value).lower()
    assert "prompt comment" in message
    assert "clone" not in message and "git" not in message


def test_a_clean_article_is_not_blocked_by_this_guard(tmp_path: Path) -> None:
    """The guard must be specific. A normal article gets past it and fails (or
    succeeds) on its own merits — never on this check."""
    article = _write(tmp_path, _FRONTMATTER + _BODY)

    with pytest.raises(DeployError) as excinfo:
        deploy(
            article_path=article,
            blog_owner="oviney",
            blog_repo="blog",
            token="fake-token",
        )

    # It gets further than the guard — whatever stops it, it is not this. (The
    # pre-existing hero-ASSET check also mentions "hero", so match this guard's
    # own wording, not the word.)
    assert "prompt comment" not in str(excinfo.value).lower()
