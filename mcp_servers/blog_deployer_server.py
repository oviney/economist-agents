#!/usr/bin/env python3
"""Blog Deployer MCP Server (Story 18.3).

Exposes blog deployment as MCP tools so any agent (Claude Code,
CrewAI, or future framework) can deploy articles without shell
scripting.

Tools:
    deploy_article: Deploy an article to the blog repo via PR.
    list_deployable_articles: List articles in output/ ready for deployment.

Usage:
    python -m mcp_servers.blog_deployer_server
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("blog-deployer")


def _run_command(cmd: str, cwd: str | None = None) -> str:
    """Run a shell command and return stdout.

    Args:
        cmd: Shell command to execute.
        cwd: Working directory for the command.

    Returns:
        Stripped stdout output.

    Raises:
        subprocess.CalledProcessError: If command exits non-zero.

    """
    result = subprocess.run(  # noqa: S602
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=120,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr,
        )
    return result.stdout.strip()


@mcp.tool()
def list_deployable_articles(output_dir: str = "output") -> list[str]:
    """List markdown articles in the output directory ready for deployment.

    Args:
        output_dir: Path to the output directory containing articles.

    Returns:
        List of article file paths sorted by modification time (newest first).

    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return []

    articles = sorted(
        [*output_path.glob("posts/*.md"), *output_path.glob("*.md")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [str(a) for a in articles]


_OUTPUT_ROOT_ENV = "BLOG_DEPLOY_OUTPUT_ROOT"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _deployable_root() -> Path:
    """The only directory `deploy_article` may read an article from.

    Deliberately **not** a tool argument. `article_path` is chosen by an agent,
    and an agent that can widen its own sandbox does not have one.

    Returns:
        Absolute, symlink-resolved path to the deployable root.

    """
    override = os.environ.get(_OUTPUT_ROOT_ENV)
    root = Path(override) if override else _REPO_ROOT / "output"
    return root.resolve()


def _resolve_article_path(article_path: str) -> tuple[Path | None, str | None]:
    """Resolve an agent-supplied article path, refusing anything outside `output/`.

    `deploy_article` copies the named file into a **public** blog PR using
    `GITHUB_TOKEN`, so an unconstrained path is an exfiltration route: text
    injected into fetched research could name any readable file. `resolve()`
    collapses `..` and follows symlinks before the check, so neither traversal
    nor a symlink planted inside `output/` escapes.

    Args:
        article_path: Caller-supplied path to the article markdown file.

    Returns:
        `(resolved_path, None)` when the path is inside the deployable root and
        exists, otherwise `(None, error_message)`. The sandbox check runs first
        so an out-of-root path cannot be used to probe which files exist.

    """
    root = _deployable_root()
    try:
        candidate = Path(article_path).resolve()
    except OSError as exc:  # pragma: no cover - platform-dependent
        return None, f"Article path could not be resolved: {exc}"

    if not candidate.is_relative_to(root):
        return None, (
            f"Article path is outside the deployable root {root}: {article_path}"
        )
    if not candidate.exists():
        return None, f"Article not found: {article_path}"
    return candidate, None


@mcp.tool()
def deploy_article(
    article_path: str,
    blog_repo: str,
) -> dict[str, Any]:
    """Deploy an article to the blog repository via pull request.

    Clones the blog repo, copies the article and associated images,
    rewrites chart paths for Jekyll, creates a feature branch, commits,
    pushes, and opens a PR.

    Args:
        article_path: Path to the article markdown file.
        blog_repo: GitHub repository in 'owner/repo' format.

    Returns:
        Dict with success status, PR URL, and article filename.

    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return {
            "success": False,
            "error": "GITHUB_TOKEN environment variable not set",
            "pr_url": None,
            "article": None,
        }

    article, path_error = _resolve_article_path(article_path)
    if article is None:
        return {
            "success": False,
            "error": path_error,
            "pr_url": None,
            "article": None,
        }

    slug = article.stem
    blog_dir = None

    try:
        blog_dir = Path(tempfile.mkdtemp(prefix="blog_deploy_"))

        logger.info("Cloning %s", blog_repo)
        _run_command(
            f"git clone --depth 1 "
            f"https://x-access-token:{token}@github.com/{blog_repo}.git "
            f"{blog_dir}",
        )

        # Configure git in temp repo
        _run_command('git config user.name "Economist Agent Bot"', cwd=str(blog_dir))
        _run_command(
            'git config user.email "github-actions[bot]@users.noreply.github.com"',
            cwd=str(blog_dir),
        )

        # Create feature branch
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch = f"content/{slug}-{timestamp}"
        _run_command(f"git checkout -b {branch}", cwd=str(blog_dir))

        # Ensure directories exist
        posts_dir = blog_dir / "_posts"
        assets_charts = blog_dir / "assets" / "charts"
        assets_images = blog_dir / "assets" / "images"
        posts_dir.mkdir(parents=True, exist_ok=True)
        assets_charts.mkdir(parents=True, exist_ok=True)
        assets_images.mkdir(parents=True, exist_ok=True)

        # Copy article with chart path rewriting
        content = article.read_text()
        content = content.replace("output/charts/", "/assets/charts/")
        (posts_dir / article.name).write_text(content)

        # Canonical handshake articles live under output/posts/, while
        # legacy articles live directly under output/.
        output_dir = (
            article.parent.parent if article.parent.name == "posts" else article.parent
        )

        # Copy associated charts. A referenced chart without a source PNG
        # would publish a broken <img>, so block the deploy explicitly.
        charts_dir = output_dir / "charts"
        chart_refs = sorted(set(re.findall(r"/assets/charts/([^)\s]+\.png)", content)))
        chart_files = [charts_dir / Path(ref).name for ref in chart_refs]
        if not chart_files:
            fallback_chart = charts_dir / f"{slug}.png"
            if fallback_chart.exists():
                chart_files.append(fallback_chart)
        for chart_file in chart_files:
            if not chart_file.exists():
                raise FileNotFoundError(f"Chart asset not found: {chart_file}")
            shutil.copy2(chart_file, assets_charts / chart_file.name)

        # Copy associated images
        images_dir = article.parent / "images"
        for ext in ("png", "webp"):
            image_file = images_dir / f"{slug}.{ext}"
            if image_file.exists():
                shutil.copy2(image_file, assets_images / f"{slug}.{ext}")

        # Commit (Double Commit Protocol — BUG-025)
        # If pre-commit hooks reformat files post-commit, the working directory
        # is left dirty. Re-stage and amend so the commit captures the fixed
        # content and we don't loop on the next iteration.
        _run_command("git add .", cwd=str(blog_dir))
        commit_msg = f"content: Add article {article.name}"
        _run_command(f'git commit -m "{commit_msg}"', cwd=str(blog_dir))
        dirty = _run_command("git status --porcelain", cwd=str(blog_dir))
        if dirty:
            logger.info("pre-commit hooks modified files; amending commit")
            _run_command("git add -u", cwd=str(blog_dir))
            _run_command("git commit --amend --no-edit", cwd=str(blog_dir))

        # Push
        _run_command(f"git push origin {branch}", cwd=str(blog_dir))

        # Create PR
        pr_title = f"New Article: {slug}"
        pr_url = _run_command(
            f"gh pr create --repo {blog_repo} "
            f'--title "{pr_title}" '
            f'--body "Automated deployment from economist-agents MCP server." '
            f"--head {branch}",
            cwd=str(blog_dir),
        )

        logger.info("PR created: %s", pr_url)
        return {
            "success": True,
            "pr_url": pr_url,
            "article": article.name,
            "branch": branch,
        }

    except subprocess.CalledProcessError as e:
        logger.exception("Deployment failed: %s", e.cmd)
        return {
            "success": False,
            "error": f"Command failed: {e.cmd} — {e.stderr or e.stdout or str(e)}",
            "pr_url": None,
            "article": article.name,
        }
    except Exception as e:
        logger.exception("Unexpected error during deployment")
        return {
            "success": False,
            "error": str(e),
            "pr_url": None,
            "article": article.name if article else None,
        }
    finally:
        if blog_dir and blog_dir.exists():
            shutil.rmtree(blog_dir, ignore_errors=True)


if __name__ == "__main__":
    mcp.run(transport="stdio")
