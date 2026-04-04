#!/usr/bin/env python3
"""Editorial Judge — Post-Deployment Shift-Right Quality Gate.

Fetches a deployed article from the blog repository via the GitHub API
and validates 6 quality dimensions.  Designed to catch defects that
escape pre-deployment gates (missing layout, broken images, duplicate
topics, etc.).

Usage:
    python scripts/editorial_judge.py \\
        --blog-owner oviney --blog-repo blog \\
        --article 2026-04-04-article-slug.md \\
        --create-issue-on-failure
"""

import argparse
import base64
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════

PASS = "pass"
WARN = "warn"
FAIL = "fail"


@dataclass
class CheckResult:
    """Result of a single quality check."""

    name: str
    status: str  # "pass", "warn", "fail"
    message: str
    details: str = ""


@dataclass
class JudgeReport:
    """Full editorial judge report."""

    article_title: str
    article_filename: str
    article_url: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == WARN]

    @property
    def verdict(self) -> str:
        if self.failures:
            return "FAIL"
        if self.warnings:
            return "NEEDS ATTENTION"
        return "PASS"


# ═══════════════════════════════════════════════════════════════════════════
# Editorial Judge
# ═══════════════════════════════════════════════════════════════════════════

# Required frontmatter fields
_REQUIRED_FIELDS = ["layout", "title", "date", "categories"]

# Banned phrases (subset — full list in publication_validator.py)
_BANNED_PHRASES = [
    "game-changer",
    "paradigm shift",
    "in conclusion",
    "in today's world",
    "it's no secret",
    "remains to be seen",
    "only time will tell",
]


class EditorialJudge:
    """Post-deployment quality validator for blog articles."""

    def __init__(
        self,
        blog_owner: str,
        blog_repo: str,
        article_filename: str,
    ) -> None:
        self.blog_owner = blog_owner
        self.blog_repo = blog_repo
        self.article_filename = article_filename
        self._article_content: str | None = None
        self._frontmatter: dict[str, Any] | None = None

    # --- GitHub API layer ---

    def _gh_api(self, endpoint: str) -> dict[str, Any]:
        """Call GitHub REST API via gh CLI."""
        result = subprocess.run(
            ["gh", "api", f"repos/{self.blog_owner}/{self.blog_repo}/{endpoint}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
        return json.loads(result.stdout)

    def _fetch_file_content(self, path: str) -> str:
        """Fetch and decode a file from the blog repo."""
        data = self._gh_api(f"contents/{path}")
        return base64.b64decode(data["content"]).decode("utf-8")

    def _file_exists(self, path: str) -> bool:
        """Check whether a file exists in the blog repo."""
        try:
            self._gh_api(f"contents/{path}")
            return True
        except RuntimeError:
            return False

    def _list_posts(self) -> list[dict[str, str]]:
        """List all files in _posts/."""
        data = self._gh_api("contents/_posts")
        if isinstance(data, list):
            return [{"name": f["name"], "path": f["path"]} for f in data]
        return []

    def _get_article(self) -> str:
        """Fetch the article under test (cached)."""
        if self._article_content is None:
            self._article_content = self._fetch_file_content(
                f"_posts/{self.article_filename}"
            )
        return self._article_content

    def _get_frontmatter(self) -> dict[str, Any]:
        """Parse YAML frontmatter from the article (cached)."""
        if self._frontmatter is None:
            content = self._get_article()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    self._frontmatter = yaml.safe_load(parts[1]) or {}
                else:
                    self._frontmatter = {}
            else:
                self._frontmatter = {}
        return self._frontmatter

    def _get_body(self) -> str:
        """Extract body text after frontmatter."""
        content = self._get_article()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

    # --- Check functions ---

    def check_frontmatter(self) -> CheckResult:
        """Check that all required frontmatter fields are present."""
        fm = self._get_frontmatter()
        missing = [f for f in _REQUIRED_FIELDS if f not in fm]

        if not fm:
            return CheckResult("Frontmatter", FAIL, "No YAML frontmatter found")

        if "layout" in missing:
            return CheckResult(
                "Frontmatter",
                FAIL,
                f"Missing critical field: layout (page renders unstyled). Missing: {missing}",
            )

        if missing:
            return CheckResult(
                "Frontmatter", FAIL, f"Missing required fields: {missing}"
            )

        # Check layout value
        if fm.get("layout") != "post":
            return CheckResult(
                "Frontmatter",
                WARN,
                f"layout is '{fm.get('layout')}', expected 'post'",
            )

        return CheckResult(
            "Frontmatter",
            PASS,
            f"All required fields present: {_REQUIRED_FIELDS}",
        )

    def check_image_exists(self) -> CheckResult:
        """Check that the featured image file exists in the blog repo."""
        fm = self._get_frontmatter()
        image_path = fm.get("image", "")

        if not image_path:
            return CheckResult(
                "Image", WARN, "No image field in frontmatter (no featured image)"
            )

        # Strip leading / for API path
        api_path = image_path.lstrip("/")

        if self._file_exists(api_path):
            return CheckResult("Image", PASS, f"Image exists: {image_path}")

        return CheckResult(
            "Image",
            FAIL,
            f"Image not found in blog repo: {image_path}",
            details=f"File {api_path} does not exist. Upload the image or use /assets/images/blog-default.svg",
        )

    def check_categories(self) -> CheckResult:
        """Check that categories/tags are present and non-empty."""
        fm = self._get_frontmatter()
        categories = fm.get("categories", fm.get("category"))

        if categories is None:
            return CheckResult(
                "Categories", FAIL, "No categories or category field in frontmatter"
            )

        if isinstance(categories, list) and len(categories) == 0:
            return CheckResult("Categories", FAIL, "Categories list is empty")

        if isinstance(categories, str) and not categories.strip():
            return CheckResult("Categories", FAIL, "Category field is empty")

        cat_list = categories if isinstance(categories, list) else [categories]
        return CheckResult("Categories", PASS, f"Categories: {cat_list}")

    def check_duplication(self) -> CheckResult:
        """Check for content duplication against past posts."""
        new_body_words = self._get_body().split()
        if not new_body_words:
            return CheckResult("Duplication", WARN, "Article body is empty")

        posts = self._list_posts()
        # Exclude the article under test
        other_posts = [p for p in posts if p["name"] != self.article_filename]

        if not other_posts:
            return CheckResult("Duplication", PASS, "No past posts to compare against")

        highest_ratio = 0.0
        most_similar = ""

        for post in other_posts:
            try:
                content = self._fetch_file_content(post["path"])
                # Extract body after frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    past_body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    past_body = content

                past_words = past_body.split()
                if not past_words:
                    continue

                ratio = SequenceMatcher(None, new_body_words, past_words).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    most_similar = post["name"]
            except Exception:
                continue

        highest_pct = round(highest_ratio * 100)

        if highest_ratio >= 0.80:
            return CheckResult(
                "Duplication",
                FAIL,
                f"{highest_pct}% similarity with '{most_similar}' — likely duplicate",
            )

        if highest_ratio >= 0.60:
            return CheckResult(
                "Duplication",
                WARN,
                f"{highest_pct}% similarity with '{most_similar}' — substantial overlap",
            )

        return CheckResult(
            "Duplication",
            PASS,
            f"Max {highest_pct}% similarity (most similar: '{most_similar}')",
        )

    def check_writing_quality(self) -> CheckResult:
        """Check writing quality using deterministic validators."""
        content = self._get_article()
        body_lower = content.lower()

        issues: list[str] = []

        # Banned phrases
        for phrase in _BANNED_PHRASES:
            if phrase.lower() in body_lower:
                issues.append(f"Contains banned phrase: '{phrase}'")

        # Placeholder flags
        if "[NEEDS SOURCE]" in content or "[UNVERIFIED]" in content:
            issues.append("Contains verification placeholder tags")

        # Word count
        body = self._get_body()
        word_count = len(body.split())
        if word_count < 800:
            issues.append(f"Too short: {word_count} words (minimum 800)")

        if issues:
            return CheckResult(
                "Writing Quality",
                FAIL,
                f"{len(issues)} issue(s) found",
                details="\n".join(f"  - {i}" for i in issues),
            )

        return CheckResult(
            "Writing Quality",
            PASS,
            f"No banned phrases or placeholders ({word_count} words)",
        )

    def check_structure(self) -> CheckResult:
        """Check article structural elements."""
        body = self._get_body()
        issues: list[str] = []

        # Heading count
        headings = re.findall(r"^#{2,3}\s", body, re.MULTILINE)
        if len(headings) < 2:
            issues.append(f"Only {len(headings)} headings (need ≥2 for structure)")

        # References section
        if "## References" not in body and "## references" not in body.lower():
            issues.append("Missing ## References section")

        if issues:
            status = FAIL if "References" in str(issues) else WARN
            return CheckResult(
                "Structure",
                status,
                f"{len(issues)} structural issue(s)",
                details="\n".join(f"  - {i}" for i in issues),
            )

        return CheckResult(
            "Structure",
            PASS,
            f"{len(headings)} headings, references section present",
        )

    # --- Orchestration ---

    def run_all_checks(self) -> JudgeReport:
        """Run all 6 quality checks and produce a report."""
        fm = self._get_frontmatter()
        title = fm.get("title", self.article_filename)
        url = f"https://github.com/{self.blog_owner}/{self.blog_repo}/blob/main/_posts/{self.article_filename}"

        report = JudgeReport(
            article_title=title,
            article_filename=self.article_filename,
            article_url=url,
        )

        checks = [
            self.check_frontmatter,
            self.check_image_exists,
            self.check_categories,
            self.check_duplication,
            self.check_writing_quality,
            self.check_structure,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
                report.checks.append(result)
            except Exception as e:
                report.checks.append(
                    CheckResult(check_fn.__name__, FAIL, f"Check crashed: {e}")
                )

        return report

    @staticmethod
    def format_report(report: JudgeReport) -> str:
        """Format the judge report as readable text."""
        icon_map = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}
        lines = [
            "EDITORIAL JUDGE REPORT",
            "=" * 50,
            f'Article: "{report.article_title}"',
            f"File: {report.article_filename}",
            f"URL: {report.article_url}",
            "",
            "CHECKS:",
        ]

        for check in report.checks:
            icon = icon_map.get(check.status, "?")
            lines.append(f"  {icon} {check.name}: {check.message}")
            if check.details:
                for detail_line in check.details.split("\n"):
                    lines.append(f"     {detail_line}")

        lines.append("")
        lines.append(
            f"VERDICT: {report.verdict} "
            f"({len(report.failures)} critical, {len(report.warnings)} warning)"
        )

        return "\n".join(lines)

    def create_github_issue(self, report: JudgeReport) -> str | None:
        """Create a GitHub issue on economist-agents if failures found."""
        if not report.failures:
            return None

        title = (
            f"Editorial Judge: {len(report.failures)} issue(s) in "
            f'"{report.article_title}"'
        )
        body = f"```\n{self.format_report(report)}\n```"

        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                f"{self.blog_owner}/economist-agents",
                "--title",
                title,
                "--body",
                body,
                "--label",
                "bug,quality",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            print(f"Created issue: {issue_url}")
            return issue_url

        logger.warning("Failed to create issue: %s", result.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Editorial Judge — Post-Deployment QA")
    parser.add_argument("--blog-owner", required=True, help="Blog repo owner")
    parser.add_argument("--blog-repo", required=True, help="Blog repo name")
    parser.add_argument("--article", required=True, help="Article filename in _posts/")
    parser.add_argument(
        "--create-issue-on-failure",
        action="store_true",
        help="Create GitHub issue on economist-agents if checks fail",
    )
    args = parser.parse_args()

    judge = EditorialJudge(args.blog_owner, args.blog_repo, args.article)
    report = judge.run_all_checks()

    print(EditorialJudge.format_report(report))

    if args.create_issue_on_failure and report.failures:
        judge.create_github_issue(report)

    sys.exit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
