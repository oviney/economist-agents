#!/usr/bin/env python3
"""Blog Quality Audit — Weekly post scoring + GitHub issue creation (Story #135).

Fetches all _posts/ markdown files from oviney/blog via the GitHub API,
evaluates each with ArticleEvaluator, and creates a GitHub issue in
oviney/blog for any post scoring below 90%.

Outputs a dashboard summary to logs/blog_audit.json.

Usage:
    python scripts/blog_quality_audit.py

Environment variables:
    GH_TOKEN        GitHub token with access to oviney/blog (BLOG_REPO_TOKEN)
    OPENAI_API_KEY  OpenAI key (passed through to ArticleEvaluator if needed)
    DRY_RUN         Set to 'true' to score posts without creating issues
"""

import base64
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import orjson
import requests

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.article_evaluator import ArticleEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

BLOG_REPO = "oviney/blog"
QUALITY_THRESHOLD = 90  # percent
AUDIT_LOG = Path("logs/blog_audit.json")
QUALITY_LABEL = "quality-audit"

# ── GitHub helpers ───────────────────────────────────────────────────────────


def _gh_headers() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _gh_get(url: str) -> dict | list:
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_posts() -> list[dict]:
    """Return list of {filename, path, content} dicts for all _posts/ files."""
    url = f"https://api.github.com/repos/{BLOG_REPO}/contents/_posts"
    items = _gh_get(url)
    posts = []
    for item in items:
        if not item["name"].endswith(".md"):
            continue
        logger.info("Fetching %s …", item["name"])
        file_data = _gh_get(item["url"])
        raw = base64.b64decode(file_data["content"]).decode("utf-8")
        posts.append({"filename": item["name"], "path": item["path"], "content": raw})
    return posts


# ── Label helpers ────────────────────────────────────────────────────────────


def ensure_label() -> None:
    """Create the quality-audit label in oviney/blog if it doesn't exist."""
    url = f"https://api.github.com/repos/{BLOG_REPO}/labels/{QUALITY_LABEL}"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    if resp.status_code == 200:
        return

    payload = {"name": QUALITY_LABEL, "color": "e11d48", "description": "Post flagged by weekly quality audit"}
    create_resp = requests.post(
        f"https://api.github.com/repos/{BLOG_REPO}/labels",
        headers=_gh_headers(),
        json=payload,
        timeout=30,
    )
    if create_resp.status_code in (201, 422):  # 422 = already exists (race)
        logger.info("Label '%s' ready.", QUALITY_LABEL)
    else:
        create_resp.raise_for_status()


# ── Issue helpers ─────────────────────────────────────────────────────────────


def existing_issue_title(post_title: str) -> bool:
    """Return True if an open quality-audit issue for this post already exists."""
    url = (
        f"https://api.github.com/repos/{BLOG_REPO}/issues"
        f"?labels={QUALITY_LABEL}&state=open&per_page=100"
    )
    issues = _gh_get(url)
    needle = f"[Quality Audit] {post_title}"
    return any(i["title"] == needle for i in issues)


def create_issue(post_title: str, filename: str, result) -> str:
    """Create a GitHub issue in oviney/blog; return the HTML URL."""
    dimensions = "\n".join(
        f"- **{dim.replace('_', ' ').title()}**: {score}/10 — {result.details.get(dim, '')}"
        for dim, score in result.scores.items()
    )
    body = (
        f"## Quality Audit Report\n\n"
        f"**Post**: `{filename}`  \n"
        f"**Score**: {result.percentage}% ({result.total_score}/{result.max_score})  \n"
        f"**Threshold**: {QUALITY_THRESHOLD}%  \n"
        f"**Audited**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"### Dimension Scores\n\n{dimensions}\n\n"
        f"### Recommendations\n\n"
        + _recommendations(result)
    )

    payload = {
        "title": f"[Quality Audit] {post_title}",
        "body": body,
        "labels": [QUALITY_LABEL],
    }
    resp = requests.post(
        f"https://api.github.com/repos/{BLOG_REPO}/issues",
        headers=_gh_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


def _recommendations(result) -> str:
    recs = []
    if result.scores.get("opening_quality", 10) < 7:
        recs.append("- **Opening**: Lead with a specific data point (e.g. '73% of organisations…'). Avoid banned openings like 'In today's world'.")
    if result.scores.get("evidence_sourcing", 10) < 7:
        recs.append("- **Evidence**: Add a `## References` section with ≥5 numbered citations. Remove `[NEEDS SOURCE]` placeholders.")
    if result.scores.get("voice_consistency", 10) < 7:
        recs.append("- **Voice**: Replace American spellings with British equivalents (organisation, behaviour). Remove clichés like 'game-changer' and 'paradigm shift'.")
    if result.scores.get("structure", 10) < 7:
        recs.append("- **Structure**: Ensure front matter includes `layout`, `title`, `date`, `categories`, and `image`. Keep 2–5 `##` headings; aim for 600–1500 words.")
    if result.scores.get("visual_engagement", 10) < 7:
        recs.append("- **Visuals**: Add a featured `image:` in front matter. Embed at least one chart with a reference ('As the chart shows…').")
    return "\n".join(recs) if recs else "- General improvement required across multiple dimensions."


# ── Audit logic ───────────────────────────────────────────────────────────────


def run_audit(dry_run: bool = False) -> None:
    evaluator = ArticleEvaluator()
    posts = fetch_posts()
    logger.info("Fetched %d posts from %s.", len(posts), BLOG_REPO)

    if not dry_run:
        ensure_label()

    results = []
    issues_created = 0

    for post in posts:
        eval_result = evaluator.evaluate(post["content"], filename=post["filename"])
        logger.info(
            "%s → %d%% (%d/%d)",
            post["filename"],
            eval_result.percentage,
            eval_result.total_score,
            eval_result.max_score,
        )

        entry: dict = {
            "filename": post["filename"],
            "path": post["path"],
            **eval_result.to_dict(),
            "issue_created": False,
            "issue_url": None,
        }

        if eval_result.percentage < QUALITY_THRESHOLD:
            fm = ArticleEvaluator._parse_frontmatter(post["content"])
            post_title = fm.get("title", post["filename"])

            if dry_run:
                logger.info("[DRY RUN] Would create issue for '%s' (%d%%)", post_title, eval_result.percentage)
            elif existing_issue_title(post_title):
                logger.info("Issue already exists for '%s' — skipping.", post_title)
            else:
                url = create_issue(post_title, post["filename"], eval_result)
                logger.info("Created issue: %s", url)
                entry["issue_created"] = True
                entry["issue_url"] = url
                issues_created += 1

        results.append(entry)

    summary = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "blog_repo": BLOG_REPO,
        "threshold_percent": QUALITY_THRESHOLD,
        "dry_run": dry_run,
        "total_posts": len(posts),
        "posts_below_threshold": sum(1 for r in results if r["percentage"] < QUALITY_THRESHOLD),
        "issues_created": issues_created,
        "results": results,
    }

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG.write_bytes(orjson.dumps(summary, option=orjson.OPT_INDENT_2))
    logger.info("Audit complete. Summary written to %s.", AUDIT_LOG)
    logger.info(
        "%d/%d posts below %d%%. %d new issue(s) created.",
        summary["posts_below_threshold"],
        len(posts),
        QUALITY_THRESHOLD,
        issues_created,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    run_audit(dry_run=dry_run)
