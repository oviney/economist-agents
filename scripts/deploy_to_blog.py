#!/usr/bin/env python3
"""
Deploy generated articles to blog repository via Pull Request

Usage:
    python scripts/deploy_to_blog.py
    python scripts/deploy_to_blog.py --blog-repo username/blog-repo
    python scripts/deploy_to_blog.py --article output/2026-01-18-article.md
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Allow importing from scripts/ when run directly or via subprocess
sys.path.insert(0, str(Path(__file__).parent))
from publication_validator import validate_file  # noqa: E402


def run_command(cmd, cwd=None):
    """Run shell command and return output"""
    # nosec B602 - shell=True is intentional for git commands with quoted arguments
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)  # nosec B602
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def find_latest_article():
    """Find the most recent generated article.

    Prefers article_path.txt written by content-pipeline.yml (precise).
    Falls back to mtime scan of output/*.md with a warning (fragile).
    """
    article_path_file = Path("article_path.txt")
    if article_path_file.exists():
        candidate = Path(article_path_file.read_text().strip())
        if candidate.exists():
            print(f"📄 Using article from article_path.txt: {candidate}")
            return candidate
        print(
            f"⚠️  article_path.txt points to missing file: {candidate} — falling back to mtime scan"
        )

    output_dir = Path("output")
    articles = list(output_dir.glob("*.md"))
    if not articles:
        print("❌ No articles found in output/ directory")
        print("💡 Run: python scripts/economist_agent.py")
        sys.exit(1)

    latest = sorted(articles, key=lambda p: p.stat().st_mtime)[-1]
    print(
        f"⚠️  article_path.txt not found — using most recently modified file: {latest}"
    )
    return latest


def main():
    parser = argparse.ArgumentParser(description="Deploy article to blog via PR")
    parser.add_argument(
        "--blog-repo",
        help="Blog repository (format: username/repo-name)",
        default=os.getenv("BLOG_REPO", ""),
    )
    parser.add_argument(
        "--article",
        help="Specific article to deploy (default: latest in output/)",
        type=Path,
    )
    parser.add_argument(
        "--token",
        help="GitHub token (default: from GITHUB_TOKEN env var)",
        default=os.getenv("GITHUB_TOKEN", ""),
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.blog_repo:
        print("❌ Blog repository required")
        print("💡 Set BLOG_REPO env var or use --blog-repo username/repo-name")
        sys.exit(1)

    if not args.token:
        print("❌ GitHub token required")
        print("💡 Set GITHUB_TOKEN env var or use --token")
        sys.exit(1)

    # Find article to deploy
    article = args.article or find_latest_article()
    if not article.exists():
        print(f"❌ Article not found: {article}")
        sys.exit(1)

    print(f"🚀 Deploying {article.name} to {args.blog_repo}")

    # Extract article slug from filename
    slug = article.stem
    charts_dir = Path("output/charts")

    # Setup git config
    run_command('git config --global user.name "Economist Agent Bot"')
    run_command(
        'git config --global user.email "github-actions[bot]@users.noreply.github.com"'
    )

    # Clone blog repository
    blog_dir = Path("temp_blog_repo")
    if blog_dir.exists():
        shutil.rmtree(blog_dir)

    print(f"📥 Cloning {args.blog_repo}...")
    run_command(
        f"git clone https://x-access-token:{args.token}@github.com/{args.blog_repo}.git {blog_dir}"
    )

    # Create new branch
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"content/{slug}-{timestamp}"

    print(f"🌿 Creating branch: {branch}")
    run_command(f"git checkout -b {branch}", cwd=blog_dir)

    # Setup blog directories
    posts_dir = blog_dir / "_posts"
    assets_dir = blog_dir / "assets" / "charts"
    images_dir = blog_dir / "assets" / "images"
    posts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Determine the deploy date and rename article file accordingly
    deploy_date = datetime.now().strftime("%Y-%m-%d")
    article_name = re.sub(r"^\d{4}-\d{2}-\d{2}-", f"{deploy_date}-", article.name)
    target_article = posts_dir / article_name

    print(f"📄 Copying article: {article} → {target_article}")

    # Read article and apply deploy-time transformations
    content = article.read_text()

    # 1. Inject deploy date into YAML front matter
    content = re.sub(
        r"(^date:\s*)\d{4}-\d{2}-\d{2}",
        rf"\g<1>{deploy_date}",
        content,
        flags=re.MULTILINE,
    )

    # 2. Fix chart paths to match Jekyll assets structure
    content = content.replace("output/charts/", "/assets/charts/")
    target_article.write_text(content)

    # Copy charts
    chart_file = charts_dir / f"{slug}.png"
    if chart_file.exists():
        target_chart = assets_dir / f"{slug}.png"
        print(f"📊 Copying chart: {chart_file} → {target_chart}")
        run_command(f"cp {chart_file} {target_chart}")

    # Copy featured image (PNG + WebP) — required by responsive-image.html include
    # The blog's _includes/responsive-image.html always emits a <picture><source srcset="...webp">
    # for every .png, so htmlproofer will fail if the .webp is absent.
    featured_image_dir = Path("output") / "posts" / "images"
    featured_png = featured_image_dir / f"{slug}.png"
    if featured_png.exists():
        target_png = images_dir / f"{slug}.png"
        shutil.copy2(featured_png, target_png)
        print(f"🖼️  Copied featured image: {featured_png} → {target_png}")

        # Generate WebP alongside PNG
        target_webp = images_dir / f"{slug}.webp"
        try:
            from PIL import Image  # type: ignore

            img = Image.open(target_png)
            img.save(str(target_webp), "WEBP", quality=85)
            print(f"🖼️  Generated webp: {target_webp}")
        except ImportError:
            print(
                "⚠️  Pillow not available — skipping webp generation (htmlproofer may fail)"
            )
    else:
        print(f"   ℹ No featured image at {featured_png} — skipping image copy")

    # -----------------------------------------------------------------------
    # Pre-deploy validation gate
    # -----------------------------------------------------------------------
    print("🔍 Running pre-deploy validation...")
    is_valid, report = validate_file(str(target_article), expected_date=deploy_date)
    print(report)

    if not is_valid:
        print("❌ Pre-deploy validation failed — aborting PR creation")
        shutil.rmtree(blog_dir, ignore_errors=True)
        sys.exit(1)

    print("✅ Pre-deploy validation passed — creating PR")

    # Commit changes (Double Commit Protocol — BUG-025)
    # Pre-commit hooks (e.g. ruff-format) may reformat staged files, leaving
    # the working tree dirty after the commit succeeds. Re-stage and amend so
    # the loop terminates and the commit reflects the formatted content.
    print("💾 Committing changes...")
    run_command("git add .", cwd=blog_dir)

    commit_msg = f"content: Add generated article {article_name}"
    run_command(f'git commit -m "{commit_msg}"', cwd=blog_dir)
    dirty = run_command("git status --porcelain", cwd=blog_dir)
    if dirty:
        print("🔁 pre-commit hooks modified files; amending commit")
        run_command("git add -u", cwd=blog_dir)
        run_command("git commit --amend --no-edit", cwd=blog_dir)

    # Push branch
    print(f"📤 Pushing branch {branch}...")
    run_command(f"git push origin {branch}", cwd=blog_dir)

    # Create PR
    print("🔄 Creating Pull Request...")
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

**Charts:** {chart_file.name if chart_file.exists() else "None"}

## Automated Validation
```
{report}
```

---
🤖 Generated by [economist-agents](https://github.com/oviney/economist-agents)
"""

    run_command(
        f'gh pr create --repo {args.blog_repo} --title "{pr_title}" --body "{pr_body}" --head {branch}'
    )

    print("✅ Pull Request created successfully!")
    print(f"🔗 View at: https://github.com/{args.blog_repo}/pulls")

    # Cleanup
    shutil.rmtree(blog_dir, ignore_errors=True)
    print("🧹 Cleaned up temporary files")


if __name__ == "__main__":
    main()
