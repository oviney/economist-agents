#!/usr/bin/env python3
"""Promote an approved B-013 review draft to a published post.

The B-013 workflow reviews generated drafts as unlisted, ``noindex`` live posts
under the blog's ``_review/`` collection (see ``scripts.deploy_to_blog
--mode review``). Once the owner approves a draft at its obscure URL, this
module promotes it to a real post:

    _review/<slug>-<token>.md   ->   _posts/YYYY-MM-DD-<slug>.md

flipping ``layout: review`` back to ``layout: post``, injecting the publish
date, running the publication validator as a **blocking** gate, deleting the
review draft, and pushing to the live branch. No PR is opened — the owner has
already reviewed the rendered draft (that *is* the review gate).

Usage:
    make publish SLUG=<slug>
    python -m scripts.promote_review --slug <slug>
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Reuse the proven git/shell helpers + result type from the deploy module.
sys.path.insert(0, str(Path(__file__).parent))
from scripts.deploy_to_blog import (  # noqa: E402
    DeployError,
    DeployResult,
    run_command,
)
from scripts.publication_validator import validate_file  # noqa: E402

logger = logging.getLogger(__name__)


def promote(
    slug: str,
    blog_owner: str,
    blog_repo: str,
    token: str,
    *,
    live_branch: str = "main",
    deploy_date: str | None = None,
    delete_after: bool = True,
) -> DeployResult:
    """Promote the unlisted ``_review/<slug>-<token>.md`` draft to a post.

    Returns a :class:`DeployResult` (``status="published"`` on success,
    ``"validation_failed"`` if the publication validator rejects the post — in
    which case nothing is pushed).

    Raises:
        DeployError: on bad inputs, clone failure, or when no (or more than one)
            review draft matches *slug*.
    """
    if not slug:
        raise DeployError("slug is required")
    if not blog_owner or not blog_repo:
        raise DeployError("blog_owner and blog_repo are required")
    if not token:
        raise DeployError("GitHub token is required")

    full_repo = f"{blog_owner}/{blog_repo}"
    deploy_date = deploy_date or datetime.now().strftime("%Y-%m-%d")

    run_command('git config --global user.name "Economist Agent Bot"')
    run_command(
        'git config --global user.email "github-actions[bot]@users.noreply.github.com"'
    )

    blog_dir = Path("temp_blog_repo")
    if blog_dir.exists():
        shutil.rmtree(blog_dir)

    logger.info("Cloning %s …", full_repo)
    run_command(
        f"git clone https://x-access-token:{token}@github.com/{full_repo}.git {blog_dir}"
    )
    run_command(f"git checkout {live_branch}", cwd=blog_dir)

    review_dir = blog_dir / "_review"
    matches = sorted(review_dir.glob(f"{slug}-*.md")) if review_dir.exists() else []
    if not matches:
        shutil.rmtree(blog_dir, ignore_errors=True)
        raise DeployError(f"No review draft found for slug '{slug}' in _review/")
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        shutil.rmtree(blog_dir, ignore_errors=True)
        raise DeployError(
            f"Multiple review drafts match slug '{slug}': {names}. "
            "Remove the stale one(s) first."
        )
    review_file = matches[0]

    # Transform draft -> post: flip the layout back and inject the publish date.
    content = review_file.read_text()
    content = re.sub(
        r"^layout:.*$", "layout: post", content, count=1, flags=re.MULTILINE
    )
    content = re.sub(
        r"(^date:\s*)\d{4}-\d{2}-\d{2}",
        rf"\g<1>{deploy_date}",
        content,
        flags=re.MULTILINE,
    )

    posts_dir = blog_dir / "_posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    post_name = f"{deploy_date}-{slug}.md"
    target_post = posts_dir / post_name
    target_post.write_text(content)
    logger.info("Promoting _review/%s → _posts/%s", review_file.name, post_name)

    # Blocking publication gate.
    is_valid, report = validate_file(str(target_post), expected_date=deploy_date)
    logger.info("%s", report)
    if not is_valid:
        logger.error("Publication validation failed — not publishing")
        shutil.rmtree(blog_dir, ignore_errors=True)
        return DeployResult(
            status="validation_failed",
            branch=live_branch,
            article_name=post_name,
            validation_report=report,
            pushed=False,
        )

    if delete_after:
        run_command(f"git rm {review_file.relative_to(blog_dir)}", cwd=blog_dir)

    run_command("git add _posts", cwd=blog_dir)
    commit_msg = f"content: publish {post_name} (was review draft {review_file.name})"
    run_command(f'git commit -m "{commit_msg}"', cwd=blog_dir)
    # Double-commit protocol (BUG-025).
    if run_command("git status --porcelain", cwd=blog_dir):
        run_command("git add -u", cwd=blog_dir)
        run_command("git commit --amend --no-edit", cwd=blog_dir)

    logger.info("Publishing to %s…", live_branch)
    run_command(f"git push origin {live_branch}", cwd=blog_dir)

    shutil.rmtree(blog_dir, ignore_errors=True)
    logger.info("Published %s", post_name)

    return DeployResult(
        status="published",
        branch=live_branch,
        article_name=post_name,
        validation_report=report,
        pushed=True,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote an approved B-013 review draft to a published post."
    )
    parser.add_argument("--slug", required=True, help="Slug of the draft to promote.")
    parser.add_argument(
        "--blog-owner",
        default=os.getenv("BLOG_OWNER", ""),
        help="Blog repo owner (default: $BLOG_OWNER).",
    )
    parser.add_argument(
        "--blog-repo",
        default=os.getenv("BLOG_REPO_NAME") or os.getenv("BLOG_REPO", ""),
        help="Blog repo name (default: $BLOG_REPO_NAME/$BLOG_REPO).",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("BLOG_REPO_TOKEN") or os.getenv("GITHUB_TOKEN", ""),
        help="GitHub token (default: $BLOG_REPO_TOKEN/$GITHUB_TOKEN).",
    )
    parser.add_argument(
        "--live-branch",
        default=os.getenv("BLOG_LIVE_BRANCH", "main"),
        help="Live branch to publish to (default: $BLOG_LIVE_BRANCH or 'main').",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)

    blog_owner, blog_repo = args.blog_owner, args.blog_repo
    if "/" in blog_repo and not blog_owner:
        blog_owner, blog_repo = blog_repo.split("/", 1)
    if not blog_owner or not blog_repo:
        logger.error("Blog owner + repo required (set BLOG_OWNER + BLOG_REPO_NAME).")
        return 1
    if not args.token:
        logger.error("GitHub token required (set BLOG_REPO_TOKEN/GITHUB_TOKEN).")
        return 1

    try:
        result = promote(
            slug=args.slug,
            blog_owner=blog_owner,
            blog_repo=blog_repo,
            token=args.token,
            live_branch=args.live_branch,
        )
    except DeployError as exc:
        logger.error("Promote failed: %s", exc)
        return 1

    if result.status == "validation_failed":
        return 1
    logger.info(
        "Promote finished: status=%s post=%s", result.status, result.article_name
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
