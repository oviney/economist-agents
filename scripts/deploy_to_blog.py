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
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def find_latest_article():
    """Find the most recent generated article"""
    output_dir = Path("output")
    articles = list(output_dir.glob("*.md"))
    if not articles:
        print("❌ No articles found in output/ directory")
        print("💡 Run: python scripts/economist_agent.py")
        sys.exit(1)

    # Sort by modification time, get latest
    latest = sorted(articles, key=lambda p: p.stat().st_mtime)[-1]
    print(f"📄 Found latest article: {latest}")
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
        run_command(f"rm -rf {blog_dir}")

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
    posts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Copy article
    target_article = posts_dir / article.name
    print(f"📄 Copying article: {article} → {target_article}")

    # Read and potentially fix chart paths in article
    content = article.read_text()
    # Fix chart paths to match Jekyll assets structure
    content = content.replace("output/charts/", "/assets/charts/")
    content = content.replace("![", "![")  # Ensure proper markdown
    target_article.write_text(content)

    # Copy charts
    chart_file = charts_dir / f"{slug}.png"
    if chart_file.exists():
        target_chart = assets_dir / f"{slug}.png"
        print(f"📊 Copying chart: {chart_file} → {target_chart}")
        run_command(f"cp {chart_file} {target_chart}")

    # Commit changes
    print("💾 Committing changes...")
    run_command("git add .", cwd=blog_dir)

    commit_msg = f"content: Add generated article {article.name}"
    run_command(f'git commit -m "{commit_msg}"', cwd=blog_dir)

    # Push branch
    print(f"📤 Pushing branch {branch}...")
    run_command(f"git push origin {branch}", cwd=blog_dir)

    # Create PR
    print("🔄 Creating Pull Request...")
    pr_title = f"📝 New Article: {article.stem}"
    pr_body = f"""Automated article deployment from economist-agents.

**Article:** `{article.name}`
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Review Checklist
- [ ] Article content quality
- [ ] Chart rendering
- [ ] YAML frontmatter
- [ ] British spelling
- [ ] References section

**Charts:** {chart_file.name if chart_file.exists() else 'None'}

---
🤖 Generated by [economist-agents](https://github.com/oviney/economist-agents)
"""

    run_command(
        f'gh pr create --repo {args.blog_repo} --title "{pr_title}" --body "{pr_body}" --head {branch}'
    )

    print("✅ Pull Request created successfully!")
    print(f"🔗 View at: https://github.com/{args.blog_repo}/pulls")

    # Cleanup
    run_command(f"rm -rf {blog_dir}")
    print("🧹 Cleaned up temporary files")


if __name__ == "__main__":
    main()
