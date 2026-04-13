#!/usr/bin/env python3
"""Tests for scripts/deploy_to_blog.py

Covers:
- deploy-date injection into YAML front matter
- article filename renaming to deploy date
- PublicationValidator called as blocking gate before PR creation
- Abort (cleanup + sys.exit(1)) on validation failure
- Validation report included in PR body
"""

import contextlib
import re
from datetime import datetime
from pathlib import Path
from pathlib import Path as RealPath
from unittest.mock import MagicMock, patch

import pytest

import scripts.deploy_to_blog as dtb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_REFERENCES = """## References

1. Gartner, ["World Quality Report 2024"](https://example.com), *Gartner Research*, 2024
2. Forrester, ["State of Testing"](https://example.com), *Forrester*, 2024
"""

VALID_BODY = " ".join(["word"] * 850)

# Regex patterns mirrored from deploy_to_blog.py
_DATE_INJECT_RE = re.compile(r"(^date:\s*)\d{4}-\d{2}-\d{2}", re.MULTILINE)
_FILENAME_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _make_article(*, date: str = "2026-01-15") -> str:
    """Return a minimal valid article with the given date."""
    return (
        f"---\n"
        f"layout: post\n"
        f'title: "Specific Descriptive Article Title"\n'
        f"date: {date}\n"
        f'author: "The Economist"\n'
        f'categories: ["quality-engineering"]\n'
        f"---\n\n"
        f"{VALID_BODY}\n\n"
        f"{VALID_REFERENCES}\n"
    )


def _fake_args(tmp_path: Path, article_path: Path) -> MagicMock:
    """Build a mock argparse Namespace for main()."""
    args = MagicMock()
    args.blog_repo = "test-owner/test-blog"
    args.token = "fake-token"
    args.article = article_path
    return args


def _setup_blog_dir(tmp_path: Path) -> Path:
    """Create the directory structure that main() would clone into."""
    blog_dir = tmp_path / "temp_blog_repo"
    (blog_dir / "_posts").mkdir(parents=True, exist_ok=True)
    (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)
    return blog_dir


# ---------------------------------------------------------------------------
# Unit tests for date-injection logic
# ---------------------------------------------------------------------------


class TestDeployDateInjection:
    """Validate the date-rewrite regex used in deploy_to_blog.main()."""

    def test_stale_date_replaced_with_deploy_date(self) -> None:
        content = _make_article(date="2026-01-15")
        today = datetime.now().strftime("%Y-%m-%d")
        result = _DATE_INJECT_RE.sub(rf"\g<1>{today}", content)
        assert f"date: {today}" in result

    def test_injection_does_not_duplicate_field(self) -> None:
        content = _make_article(date="2025-12-01")
        today = datetime.now().strftime("%Y-%m-%d")
        result = _DATE_INJECT_RE.sub(rf"\g<1>{today}", content)
        assert result.count("date:") == 1

    def test_other_fields_unchanged(self) -> None:
        content = _make_article(date="2025-06-20")
        today = datetime.now().strftime("%Y-%m-%d")
        result = _DATE_INJECT_RE.sub(rf"\g<1>{today}", content)
        assert "layout: post" in result
        assert 'title: "Specific Descriptive Article Title"' in result

    def test_precise_regex_rejects_invalid_date_format(self) -> None:
        """The YYYY-MM-DD regex must NOT match malformed date strings."""
        content = "---\ndate: 1-2-3\n---\n\nBody\n"
        today = datetime.now().strftime("%Y-%m-%d")
        result = _DATE_INJECT_RE.sub(rf"\g<1>{today}", content)
        # Malformed date should NOT be replaced
        assert "date: 1-2-3" in result


class TestFilenameRename:
    """Validate the filename date-renaming logic."""

    def test_old_date_replaced(self) -> None:
        result = _FILENAME_DATE_RE.sub("2026-04-11-", "2026-01-15-my-article.md")
        assert result == "2026-04-11-my-article.md"

    def test_slug_preserved(self) -> None:
        result = _FILENAME_DATE_RE.sub("2026-04-11-", "2025-06-01-ai-testing-trends.md")
        assert result == "2026-04-11-ai-testing-trends.md"

    def test_no_date_prefix_unchanged(self) -> None:
        """Files without YYYY-MM-DD prefix should be unchanged."""
        result = _FILENAME_DATE_RE.sub("2026-04-11-", "article-without-date.md")
        assert result == "article-without-date.md"


# ---------------------------------------------------------------------------
# Integration-style tests for main() using mocks
# ---------------------------------------------------------------------------


class TestDeployToBlogMain:
    """Functional tests for main() with all external side-effects mocked."""

    @pytest.fixture()
    def stale_article_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "2026-01-15-stale-article.md"
        p.write_text(_make_article(date="2026-01-15"))
        return p

    def test_validate_file_called_with_deploy_date(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """validate_file must be called with today's date as expected_date."""

        today = datetime.now().strftime("%Y-%m-%d")
        blog_dir = _setup_blog_dir(tmp_path)
        captured: dict = {}

        def fake_validate(
            file_path: str, expected_date: str | None = None
        ) -> tuple[bool, str]:
            captured["expected_date"] = expected_date
            return True, "✅ All checks passed"

        with (
            patch.object(dtb, "run_command", return_value=""),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=_fake_args(tmp_path, stale_article_file),
            ),
            patch("sys.exit"),
            patch.object(
                dtb,
                "Path",
                side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                ),
            ),contextlib.suppress(SystemExit, Exception)
        ):
            dtb.main()

        assert "expected_date" in captured, "validate_file was never called"
        assert captured["expected_date"] == today

    def test_date_injected_in_written_content(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """The article written to the blog clone must carry today's date."""

        today = datetime.now().strftime("%Y-%m-%d")
        blog_dir = _setup_blog_dir(tmp_path)
        captured: dict = {}

        def fake_validate(
            file_path: str, expected_date: str | None = None
        ) -> tuple[bool, str]:
            with contextlib.suppress(FileNotFoundError):
                captured["content"] = RealPath(file_path).read_text()
            return True, "✅ All checks passed"

        with (
            patch.object(dtb, "run_command", return_value=""),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=_fake_args(tmp_path, stale_article_file),
            ),
            patch("sys.exit"),
            patch.object(
                dtb,
                "Path",
                side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                ),
            ),contextlib.suppress(SystemExit, Exception)
        ):
            dtb.main()

        assert "content" in captured, "validate_file was not given a readable file"
        assert f"date: {today}" in captured["content"], (
            f"Expected 'date: {today}' in written content"
        )

    def test_validation_failure_calls_sys_exit_1(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """On validation failure, sys.exit(1) must be called."""

        blog_dir = _setup_blog_dir(tmp_path)
        exit_codes: list[int] = []

        def fake_exit(code: int = 0) -> None:
            exit_codes.append(code)
            raise SystemExit(code)

        with (
            patch.object(dtb, "run_command", return_value=""),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ date_mismatch"),
            ),
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=_fake_args(tmp_path, stale_article_file),
            ),
            patch("sys.exit", side_effect=fake_exit),
            patch.object(
                dtb,
                "Path",
                side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                ),
            ),pytest.raises(SystemExit)
        ):
            dtb.main()

        assert 1 in exit_codes, "Expected sys.exit(1) on validation failure"

    def test_pr_not_created_on_validation_failure(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """When validation fails, gh pr create must NOT be invoked."""

        blog_dir = _setup_blog_dir(tmp_path)
        pr_commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ date_mismatch"),
            ),
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=_fake_args(tmp_path, stale_article_file),
            ),
            patch("sys.exit", side_effect=SystemExit),
            patch.object(
                dtb,
                "Path",
                side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                ),
            ),pytest.raises(SystemExit)
        ):
            dtb.main()

        assert pr_commands == [], "gh pr create must not run when validation fails"

    def test_validation_report_included_in_pr_body(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """The PR body must contain the validation report text."""

        blog_dir = _setup_blog_dir(tmp_path)
        pr_commands: list[str] = []
        validation_report = "✅ All 8 checks passed"

        def fake_run_command(cmd: str, cwd=None) -> str:
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, validation_report),
            ),
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=_fake_args(tmp_path, stale_article_file),
            ),
            patch("sys.exit"),
            patch.object(
                dtb,
                "Path",
                side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                ),
            ),contextlib.suppress(SystemExit, Exception)
        ):
            dtb.main()

        assert pr_commands, "gh pr create was not called on successful validation"
        assert validation_report in pr_commands[0], (
            "Validation report must appear in gh pr create --body argument"
        )
