#!/usr/bin/env python3
"""Deploy generated articles to a blog repository.

This module exposes a callable :func:`deploy` function plus a thin
``main()`` CLI wrapper.  ``deploy()`` performs the same git-clone →
copy → commit → push workflow that previously lived inline in
``.github/workflows/content-pipeline.yml`` (lines 158-249) so the same
code path runs in CI, from ``flow.publish_article()``, and from local
shells.

Usage:
    # As a callable
    from scripts.deploy_to_blog import deploy
    result = deploy(
        article_path=Path("output/2026-05-15-foo.md"),
        blog_owner="oviney",
        blog_repo="viney-blog",
        token=os.environ["BLOG_REPO_TOKEN"],
    )

    # As a CLI
    python scripts/deploy_to_blog.py --blog-owner oviney --blog-repo viney-blog
    python -m scripts.deploy_to_blog --blog-owner oviney --blog-repo viney-blog
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Allow importing from scripts/ when run directly or via subprocess
sys.path.insert(0, str(Path(__file__).parent))
from scripts.publication_validator import validate_file  # noqa: E402

logger = logging.getLogger(__name__)


class DeployError(RuntimeError):
    """Raised when a deploy step fails (clone, push, validation, …)."""


#: Prefix of the reviewer-facing block ``_maybe_inject_hero_prompt`` adds when
#: Stage 3 drew no hero. Matching the prefix, not the whole block, keeps this
#: robust to the prompt text changing.
_HERO_PROMPT_MARKER = "<!-- HERO IMAGE"


def _reject_unrendered_hero_prompt(article_path: Path) -> None:
    """Refuse to publish an article still carrying the hero-prompt comment.

    BUG-065 (production escape): the block shipped into a published post and sat
    in the live page source. It is invisible in the render, but it is pipeline
    instructions on a public page.

    This cannot live in ``publication_validator``: the comment is injected AFTER
    ``run_stage4`` on purpose ("so validation is unchanged"), so the validator
    never sees it. Deploy is the real boundary — the last point before anything
    becomes public — so the gate belongs here.

    It **rejects** rather than strips. The comment is only ever present because
    no hero was drawn; silently deleting it would hide that, and the blog
    requires a resolvable ``image:`` anyway (B-019). A loud refusal naming the
    fix is the useful behaviour.
    """
    if _HERO_PROMPT_MARKER not in article_path.read_text():
        return
    raise DeployError(
        f"{article_path.name} still contains the hero-image prompt comment "
        f"({_HERO_PROMPT_MARKER}…). That block is a brief for a human reviewer "
        "and must never be published — it leaked into a live post once already "
        "(BUG-065). Draw or supply the hero, replace the whole comment with the "
        "image reference, then deploy again."
    )


@dataclass
class DeployResult:
    """Structured outcome of a deploy() / deploy_review() call."""

    status: str  # "published" | "up_to_date" | "validation_failed" | "dry_run"
    #             | "review_published"  (deploy_review)
    branch: str
    article_name: str
    validation_report: str
    pushed: bool
    url: str | None = None  # set by deploy_review() — the obscure review URL


# ---------------------------------------------------------------------------
# Shell helper
# ---------------------------------------------------------------------------


def run_command(cmd: str, cwd: Path | None = None) -> str:
    """Run *cmd* in a shell and return stdout (stripped).

    Raises :class:`DeployError` if the command exits non-zero.  When the
    module is invoked as a CLI, ``main()`` catches the error and exits 1
    so the legacy ``sys.exit(1)`` contract is preserved.
    """
    # nosec B602 - shell=True is intentional for git commands with quoted arguments
    result = subprocess.run(  # nosec B602
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0:
        logger.error("Command failed: %s", cmd)
        logger.error("stderr: %s", result.stderr)
        raise DeployError(
            f"Command failed (exit {result.returncode}): {cmd}\n{result.stderr}"
        )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Article-discovery helpers (used by CLI)
# ---------------------------------------------------------------------------


def _dated_post_name(source_name: str, deploy_date: str) -> str:
    """Return the ``_posts`` filename for ``source_name``, stamped with the date.

    Jekyll derives a post's date and URL from its filename — ``_config.yml`` sets
    ``permalink: /:year/:month/:day/:title/`` — so an undated file in ``_posts`` is
    not a publishable post.

    BUG-069: this used to be a bare ``re.sub`` of an existing ``YYYY-MM-DD-``
    prefix, which *replaced* a date but never *added* one. That held while the
    pipeline emitted dated filenames; B-006/B-008 moved generation to a canonical
    slug at ``output/posts/<slug>.md`` and the substitution quietly became a no-op.
    Strip-then-prefix handles both shapes, so the date cannot go missing again.
    """
    stripped = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", source_name)
    return f"{deploy_date}-{stripped}"


def find_latest_article() -> Path:
    """Find the most recent generated article.

    Prefers ``article_path.txt`` written by ``content-pipeline.yml`` (precise).
    Falls back to an mtime scan of canonical ``output/posts/*.md`` and
    legacy ``output/*.md`` locations with a warning (fragile).
    """
    article_path_file = Path("article_path.txt")
    if article_path_file.exists():
        candidate = Path(article_path_file.read_text().strip())
        if candidate.exists():
            logger.info("Using article from article_path.txt: %s", candidate)
            return candidate
        logger.warning(
            "article_path.txt points to missing file: %s — falling back to mtime scan",
            candidate,
        )

    output_dir = Path("output")
    articles = list(output_dir.glob("posts/*.md")) + list(output_dir.glob("*.md"))
    if not articles:
        raise DeployError(
            "No articles found in output/ directory. "
            "Run: python -m src.economist_agents.flow"
        )

    latest = sorted(articles, key=lambda p: p.stat().st_mtime)[-1]
    logger.warning(
        "article_path.txt not found — using most recently modified file: %s",
        latest,
    )
    return latest


# ---------------------------------------------------------------------------
# Core callable
# ---------------------------------------------------------------------------


def deploy(
    article_path: Path,
    blog_owner: str,
    blog_repo: str,
    token: str,
    *,
    dry_run: bool = False,
) -> DeployResult:
    """Deploy *article_path* to ``{blog_owner}/{blog_repo}``.

    Performs the full pipeline:

    1. Clone the blog repo into a temporary directory using *token*.
    2. Create a fresh ``content/<slug>-<timestamp>`` branch.
    3. Copy the article (with deploy-date injection and Jekyll-asset
       path rewriting) into ``_posts/``.
    4. Copy the matching chart PNG into ``assets/charts/`` and the
       featured PNG + generated WebP into ``assets/images/``.
    5. Run :func:`scripts.publication_validator.validate_file` as a
       blocking gate — return early with ``status="validation_failed"``
       if it fails.
    6. Commit (with the Double-Commit Protocol — BUG-025), push to
       ``origin``, and open a PR via ``gh pr create``.

    Args:
        article_path: Path to the source ``.md`` article in ``output/``.
        blog_owner:   GitHub owner of the blog repo (e.g. ``"oviney"``).
        blog_repo:    Repo name only (e.g. ``"viney-blog"``).
        token:        GitHub token with push access to the blog repo.
        dry_run:      When ``True``, prepare the working copy and run
                      validation but skip push/PR creation.  Returns
                      ``status="dry_run"`` on success.

    Returns:
        :class:`DeployResult` describing what happened.

    Raises:
        DeployError: On any unrecoverable failure (clone, push, missing
            article, validation aborting, …).
    """
    if not article_path.exists():
        raise DeployError(f"Article not found: {article_path}")
    # BUG-065: check the local file BEFORE any clone/push work, so a rejected
    # article costs nothing and the error is about the article, not about git.
    _reject_unrendered_hero_prompt(article_path)
    if not blog_owner or not blog_repo:
        raise DeployError("blog_owner and blog_repo are required")
    if not token:
        raise DeployError("GitHub token is required")

    full_repo = f"{blog_owner}/{blog_repo}"
    logger.info("Deploying %s to %s", article_path.name, full_repo)

    slug = article_path.stem
    charts_dir = Path("output/charts")

    # Setup git config (idempotent — safe to run inside CI or locally).
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

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"content/{slug}-{timestamp}"
    logger.info("Creating branch: %s", branch)
    run_command(f"git checkout -b {branch}", cwd=blog_dir)

    # Ensure the standard Jekyll layout exists in the working copy.
    posts_dir = blog_dir / "_posts"
    assets_dir = blog_dir / "assets" / "charts"
    images_dir = blog_dir / "assets" / "images"
    posts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Rename article file to today's deploy date and inject the same
    # date into the YAML front matter.
    deploy_date = datetime.now().strftime("%Y-%m-%d")
    article_name = _dated_post_name(article_path.name, deploy_date)
    target_article = posts_dir / article_name

    logger.info("Copying article: %s → %s", article_path, target_article)
    content = article_path.read_text()
    content = re.sub(
        r"(^date:\s*)\d{4}-\d{2}-\d{2}",
        rf"\g<1>{deploy_date}",
        content,
        flags=re.MULTILINE,
    )
    content = content.replace("output/charts/", "/assets/charts/")
    target_article.write_text(content)

    # Copy each referenced chart PNG. An embedded chart without a source
    # asset would ship a broken <img>, so fail before validation instead
    # of silently skipping the copy.
    chart_refs = sorted(set(re.findall(r"/assets/charts/([^)\s]+\.png)", content)))
    chart_files = [charts_dir / Path(ref).name for ref in chart_refs]
    if not chart_files:
        fallback_chart = charts_dir / f"{slug}.png"
        if fallback_chart.exists():
            chart_files.append(fallback_chart)

    for chart_file in chart_files:
        if not chart_file.exists():
            raise DeployError(f"Chart asset not found: {chart_file}")
        target_chart = assets_dir / chart_file.name
        logger.info("Copying chart: %s → %s", chart_file, target_chart)
        shutil.copy2(chart_file, target_chart)

    # Hero referenced by the frontmatter (B-016) — an SVG hero lives at a
    # ``<slug>-hero.svg`` name the slug-guess below never matches.
    _copy_hero_asset(target_article.read_text(), images_dir)

    # Copy featured PNG + generate WebP — the blog's responsive-image
    # include emits a <source srcset="…webp">, so the .webp must exist
    # or htmlproofer fails the deploy.
    featured_image_dir = Path("output") / "posts" / "images"
    featured_png = featured_image_dir / f"{slug}.png"
    if featured_png.exists():
        target_png = images_dir / f"{slug}.png"
        shutil.copy2(featured_png, target_png)
        logger.info("Copied featured image: %s → %s", featured_png, target_png)

        target_webp = images_dir / f"{slug}.webp"
        try:
            from PIL import Image  # type: ignore

            img = Image.open(target_png)
            img.save(str(target_webp), "WEBP", quality=85)
            logger.info("Generated webp: %s", target_webp)
        except ImportError:
            logger.warning(
                "Pillow not available — skipping webp generation (htmlproofer may fail)"
            )
    else:
        logger.info("No featured image at %s — skipping image copy", featured_png)

    # Pre-deploy validation gate.
    logger.info("Running pre-deploy validation…")
    is_valid, report = validate_file(str(target_article), expected_date=deploy_date)
    logger.info("%s", report)

    if not is_valid:
        logger.error("Pre-deploy validation failed — aborting PR creation")
        shutil.rmtree(blog_dir, ignore_errors=True)
        return DeployResult(
            status="validation_failed",
            branch=branch,
            article_name=article_name,
            validation_report=report,
            pushed=False,
        )

    logger.info("Pre-deploy validation passed")

    if dry_run:
        shutil.rmtree(blog_dir, ignore_errors=True)
        return DeployResult(
            status="dry_run",
            branch=branch,
            article_name=article_name,
            validation_report=report,
            pushed=False,
        )

    # Commit changes (Double Commit Protocol — BUG-025).
    # Pre-commit hooks (e.g. ruff-format) may reformat staged files,
    # leaving the working tree dirty after commit.  Re-stage and amend
    # so the loop terminates and the commit reflects formatted content.
    logger.info("Committing changes…")
    # Stage only the content paths this deploy writes. The blog gates every PR
    # with ``scripts/check-pr-scope.sh``: Rule 1 fails on protected files
    # (``_config.yml``, ``Gemfile``, ``.github/CODEOWNERS``, …), Rule 2 on >15
    # files, Rule 3 on ``.github/skills|instructions/``. An unscoped
    # ``git add .`` would stage whatever else happens to be dirty in the clone,
    # so "an article PR touches only _posts/ + assets/" must hold by
    # construction, not by luck (B-015). Mirrors ``deploy_review()``.
    run_command("git add _posts assets", cwd=blog_dir)

    commit_msg = f"content: Add generated article {article_name}"
    try:
        run_command(f'git commit -m "{commit_msg}"', cwd=blog_dir)
    except DeployError as exc:
        # `git commit` exits non-zero when there's nothing staged — that
        # means the blog is already up to date with this article.
        if "nothing to commit" in str(exc) or "no changes added" in str(exc):
            logger.info("No changes to commit — blog is already up to date")
            shutil.rmtree(blog_dir, ignore_errors=True)
            return DeployResult(
                status="up_to_date",
                branch=branch,
                article_name=article_name,
                validation_report=report,
                pushed=False,
            )
        raise

    dirty = run_command("git status --porcelain", cwd=blog_dir)
    if dirty:
        logger.info("pre-commit hooks modified files; amending commit")
        run_command("git add -u", cwd=blog_dir)
        run_command("git commit --amend --no-edit", cwd=blog_dir)

    # Push branch.
    logger.info("Pushing branch %s…", branch)
    run_command(f"git push origin {branch}", cwd=blog_dir)

    # Create PR.
    logger.info("Creating Pull Request…")
    pr_title = f"📝 New Article: {Path(article_name).stem}"
    pr_body = f"""Automated article deployment from economist-agents.

**Article:** `{article_name}`
**Deployed:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Review Checklist
- [ ] Article content quality
- [ ] Chart rendering
- [ ] YAML frontmatter
- [ ] British spelling
- [ ] References section

**Charts:** {", ".join(chart.name for chart in chart_files) or "None"}

## Automated Validation
```
{report}
```

---
🤖 Generated by [economist-agents](https://github.com/oviney/economist-agents)
"""
    run_command(
        f'gh pr create --repo {full_repo} --title "{pr_title}" '
        f'--body "{pr_body}" --head {branch}'
    )

    logger.info("Pull Request created successfully")
    logger.info("View at: https://github.com/%s/pulls", full_repo)

    shutil.rmtree(blog_dir, ignore_errors=True)
    logger.info("Cleaned up temporary files")

    return DeployResult(
        status="published",
        branch=branch,
        article_name=article_name,
        validation_report=report,
        pushed=True,
    )


# ---------------------------------------------------------------------------
# Review mode (B-013) — unlisted live draft, no PR
# ---------------------------------------------------------------------------


def _hero_asset_ref(content: str) -> str | None:
    """Filename of the hero the frontmatter ``image:`` points at, else ``None``.

    Frontmatter-driven rather than ``<slug>.png``-guessed, because the hero is a
    Claude-authored **SVG** named ``<slug>-hero.svg`` (B-016) and a slug guess
    silently skipped it, shipping a broken ``<img>``. An empty value is not a
    reference (BUG-055).
    """
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 2:
        return None
    match = re.search(
        r"^image:[ \t]*[\"']?([^\"'\s]+)[\"']?[ \t]*$", parts[1], re.MULTILINE
    )
    if not match:
        return None
    return Path(match.group(1)).name or None


def _copy_hero_asset(content: str, images_dir: Path) -> None:
    """Copy the frontmatter-referenced hero into the blog clone (B-016).

    A ``.png`` hero also gets a ``.webp`` sibling because the blog's
    ``responsive-image.html`` does ``replace: '.png', '.webp'`` and emits a
    ``<source srcset>`` html-proofer then requires. An ``.svg`` hero takes the
    plain ``<img>`` branch, so it needs no webp — which is why authoring the
    hero as SVG is both keyless and the lower-friction path.
    """
    name = _hero_asset_ref(content)
    if not name:
        return
    source = Path("output") / "posts" / "images" / name
    if not source.exists():
        raise DeployError(
            f"Hero asset not found: {source} (frontmatter image: references it)"
        )
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / name
    shutil.copy2(source, target)
    logger.info("Copied hero: %s → %s", source, target)

    if target.suffix.lower() != ".png":
        return
    try:
        from PIL import Image  # type: ignore

        Image.open(target).save(str(target.with_suffix(".webp")), "WEBP", quality=85)
        logger.info("Generated webp for PNG hero: %s", target.with_suffix(".webp"))
    except ImportError:
        logger.warning(
            "Pillow unavailable — no webp for PNG hero (htmlproofer may fail)"
        )


def _to_review_content(content: str) -> str:
    """Transform a generated post into an unlisted ``review`` draft.

    Swaps the ``layout: post`` front-matter for ``layout: review`` (the blog's
    ``review`` layout injects ``<meta name="robots" content="noindex,nofollow">``)
    and rewrites in-repo ``output/charts/`` asset paths to the deployed
    ``/assets/charts/`` location, mirroring :func:`deploy`.
    """
    content = re.sub(
        r"^layout:.*$", "layout: review", content, count=1, flags=re.MULTILINE
    )
    return content.replace("output/charts/", "/assets/charts/")


def deploy_review(
    article_path: Path,
    blog_owner: str,
    blog_repo: str,
    token: str,
    *,
    live_branch: str = "main",
    host: str = "www.viney.ca",
    dry_run: bool = False,
) -> DeployResult:
    """Deploy *article_path* as an **unlisted** live draft for owner review.

    Unlike :func:`deploy`, this writes to the blog's ``_review/`` collection at
    an obscure ``<slug>-<token>`` name, commits **directly to the live branch**,
    and opens **no PR**.  The owner reviews the fully-rendered post at the
    returned URL; the ``review`` collection is excluded from the site's nav,
    feed, and sitemap and carries ``noindex`` (B-013 leak-test gate). Promote an
    approved draft to ``_posts/`` with ``scripts.promote_review`` (``make
    publish``).

    This is a separate function from :func:`deploy` on purpose: the ``post``
    path serves the live keyless pipeline (B-010) and must stay byte-for-byte
    unchanged.
    """
    if not article_path.exists():
        raise DeployError(f"Article not found: {article_path}")
    # BUG-065: check the local file BEFORE any clone/push work, so a rejected
    # article costs nothing and the error is about the article, not about git.
    _reject_unrendered_hero_prompt(article_path)
    if not blog_owner or not blog_repo:
        raise DeployError("blog_owner and blog_repo are required")
    if not token:
        raise DeployError("GitHub token is required")

    full_repo = f"{blog_owner}/{blog_repo}"
    # Strip any leading deploy-date prefix so the review permalink is a clean
    # slug (the ``review`` collection permalink is /review/:name/).
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", article_path.stem)
    token_suffix = secrets.token_hex(4)  # 8 hex chars of obscurity
    review_name = f"{slug}-{token_suffix}.md"
    charts_dir = Path("output/charts")

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
    # Commit straight onto the live branch — no feature branch, no PR.
    run_command(f"git checkout {live_branch}", cwd=blog_dir)

    review_dir = blog_dir / "_review"
    assets_dir = blog_dir / "assets" / "charts"
    review_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    content = _to_review_content(article_path.read_text())
    (review_dir / review_name).write_text(content)
    logger.info("Wrote unlisted draft: _review/%s", review_name)

    # Copy referenced chart PNGs (fallback to <slug>.png) so the rendered draft
    # isn't a broken <img>.
    chart_refs = sorted(set(re.findall(r"/assets/charts/([^)\s]+\.png)", content)))
    chart_files = [charts_dir / Path(ref).name for ref in chart_refs]
    if not chart_files:
        fallback_chart = charts_dir / f"{slug}.png"
        if fallback_chart.exists():
            chart_files.append(fallback_chart)
    for chart_file in chart_files:
        if not chart_file.exists():
            raise DeployError(f"Chart asset not found: {chart_file}")
        shutil.copy2(chart_file, assets_dir / chart_file.name)

    # Ship the hero too (B-016) — a review draft is meant to be reviewed as the
    # finished post, so it must render the illustration, not a broken <img>.
    _copy_hero_asset(content, blog_dir / "assets" / "images")

    url = f"https://{host}/review/{slug}-{token_suffix}/"

    if dry_run:
        shutil.rmtree(blog_dir, ignore_errors=True)
        return DeployResult(
            status="dry_run",
            branch=live_branch,
            article_name=review_name,
            validation_report="",
            pushed=False,
            url=url,
        )

    run_command("git add _review assets/charts assets/images", cwd=blog_dir)
    commit_msg = f"review: unlisted draft {review_name}"
    run_command(f'git commit -m "{commit_msg}"', cwd=blog_dir)
    # Double-commit protocol (BUG-025): pre-commit hooks may reformat staged
    # files, leaving the tree dirty; re-stage and amend so the loop terminates.
    if run_command("git status --porcelain", cwd=blog_dir):
        run_command("git add -u", cwd=blog_dir)
        run_command("git commit --amend --no-edit", cwd=blog_dir)

    logger.info("Pushing unlisted draft to %s…", live_branch)
    run_command(f"git push origin {live_branch}", cwd=blog_dir)

    shutil.rmtree(blog_dir, ignore_errors=True)
    logger.info("Review draft live (unlisted, noindex): %s", url)

    return DeployResult(
        status="review_published",
        branch=live_branch,
        article_name=review_name,
        validation_report="",
        pushed=True,
        url=url,
    )


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    Split out from `_parse_args` so tests can assert on the *configuration* —
    specifically that `--mode` has no default (B-028 Task 1). Asserting only on
    behaviour would let a future change reintroduce a default alongside
    `required=True`, which argparse accepts silently.

    Returns:
        The configured parser.

    """
    parser = argparse.ArgumentParser(
        description="Deploy article to blog via Pull Request"
    )
    parser.add_argument(
        "--blog-owner",
        help="Blog repo owner (e.g. 'oviney'). Defaults to $BLOG_OWNER or "
        "the first half of $BLOG_REPO when in 'owner/repo' form.",
        default=os.getenv("BLOG_OWNER", ""),
    )
    parser.add_argument(
        "--blog-repo",
        help="Blog repo name. Accepts either 'repo' or 'owner/repo'. "
        "Defaults to $BLOG_REPO_NAME or $BLOG_REPO.",
        default=os.getenv("BLOG_REPO_NAME") or os.getenv("BLOG_REPO", ""),
    )
    parser.add_argument(
        "--article",
        help="Specific article to deploy (default: latest in output/)",
        type=Path,
    )
    parser.add_argument(
        "--token",
        help="GitHub token (default: from BLOG_REPO_TOKEN or GITHUB_TOKEN env var)",
        default=os.getenv("BLOG_REPO_TOKEN") or os.getenv("GITHUB_TOKEN", ""),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare and validate but skip push/PR creation",
    )
    # B-028: this carried `default="post"`, so the command as five docs
    # described it published without review, with no error and no warning —
    # exactly how article two skipped the B-013 review stage. Neither value is a
    # safe default: `post` skips review, and `review` would write to the blog's
    # live branch on a bare invocation, which is worse. Requiring the choice
    # removes the accident without picking a wrong default.
    parser.add_argument(
        "--mode",
        choices=("post", "review"),
        required=True,
        help="REQUIRED. 'review' (B-013, the sanctioned route): write an "
        "unlisted noindex draft to _review/ on the live branch, no PR — then "
        "`make publish SLUG=<slug>` after approval. 'post': open a PR straight "
        "into _posts/, skipping review.",
    )
    parser.add_argument(
        "--live-branch",
        default=os.getenv("BLOG_LIVE_BRANCH", "main"),
        help="Live branch to commit review drafts to (default: $BLOG_LIVE_BRANCH or 'main').",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("BLOG_HOST", "www.viney.ca"),
        help="Blog host for the printed review URL (default: $BLOG_HOST or 'www.viney.ca').",
    )
    return parser


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument vector; defaults to `sys.argv[1:]`.

    Returns:
        The parsed namespace.

    """
    return _build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)

    # Normalise blog_owner / blog_repo: `--blog-repo owner/repo` is
    # accepted for backwards compatibility with the legacy CLI flag.
    blog_owner = args.blog_owner
    blog_repo = args.blog_repo
    if "/" in blog_repo and not blog_owner:
        blog_owner, blog_repo = blog_repo.split("/", 1)

    if not blog_owner or not blog_repo:
        logger.error(
            "Blog owner + repo required. Set BLOG_OWNER + BLOG_REPO_NAME "
            "(or use --blog-owner / --blog-repo)."
        )
        return 1

    if not args.token:
        logger.error(
            "GitHub token required. Set BLOG_REPO_TOKEN/GITHUB_TOKEN or use --token."
        )
        return 1

    try:
        article = args.article or find_latest_article()
    except DeployError as exc:
        logger.error("%s", exc)
        return 1

    try:
        if args.mode == "review":
            result = deploy_review(
                article_path=article,
                blog_owner=blog_owner,
                blog_repo=blog_repo,
                token=args.token,
                live_branch=args.live_branch,
                host=args.host,
                dry_run=args.dry_run,
            )
        else:
            result = deploy(
                article_path=article,
                blog_owner=blog_owner,
                blog_repo=blog_repo,
                token=args.token,
                dry_run=args.dry_run,
            )
    except DeployError as exc:
        logger.error("Deploy failed: %s", exc)
        return 1

    if result.status == "validation_failed":
        return 1

    if result.url:
        logger.info("Review URL: %s", result.url)
    logger.info("Deploy finished: status=%s branch=%s", result.status, result.branch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
