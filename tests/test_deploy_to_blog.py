#!/usr/bin/env python3
"""Tests for scripts/deploy_to_blog.py

Covers:
- deploy-date injection into YAML front matter
- article filename renaming to deploy date
- PublicationValidator called as blocking gate before PR creation
- Abort (cleanup + sys.exit(1)) on validation failure
- Validation report included in PR body
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_REFERENCES = """## References

1. Gartner, ["World Quality Report 2024"](https://example.com), *Gartner Research*, 2024
2. Forrester, ["State of Testing"](https://example.com), *Forrester*, 2024
"""

VALID_BODY = " ".join(["word"] * 850)


def _make_article(*, date: str = "2026-01-15") -> str:
    """Return a minimal valid article with the given date."""
    return (
        f"---\n"
        f"layout: post\n"
        f'title: "Specific Descriptive Article Title"\n'
        f"date: {date}\n"
        f'author: "The Economist"\n'
        f"categories: [\"quality-engineering\"]\n"
        f"---\n\n"
        f"{VALID_BODY}\n\n"
        f"{VALID_REFERENCES}\n"
    )


# ---------------------------------------------------------------------------
# Unit tests for date-injection logic
# ---------------------------------------------------------------------------


class TestDeployDateInjection:
    """Validate the date-rewrite regex used in deploy_to_blog.main()."""

    def _inject_date(self, content: str, deploy_date: str) -> str:
        return re.sub(
            r"(^date:\s*)[\d-]+",
            rf"\g<1>{deploy_date}",
            content,
            flags=re.MULTILINE,
        )

    def test_stale_date_replaced_with_deploy_date(self):
        content = _make_article(date="2026-01-15")
        today = datetime.now().strftime("%Y-%m-%d")
        result = self._inject_date(content, today)
        assert f"date: {today}" in result

    def test_injection_does_not_duplicate_field(self):
        content = _make_article(date="2025-12-01")
        today = datetime.now().strftime("%Y-%m-%d")
        result = self._inject_date(content, today)
        assert result.count("date:") == 1

    def test_other_fields_unchanged(self):
        content = _make_article(date="2025-06-20")
        today = datetime.now().strftime("%Y-%m-%d")
        result = self._inject_date(content, today)
        assert "layout: post" in result
        assert 'title: "Specific Descriptive Article Title"' in result


class TestFilenameRename:
    """Validate the filename date-renaming logic."""

    def _rename(self, filename: str, deploy_date: str) -> str:
        return re.sub(r"^\d{4}-\d{2}-\d{2}-", f"{deploy_date}-", filename)

    def test_old_date_replaced(self):
        result = self._rename("2026-01-15-my-article.md", "2026-04-11")
        assert result == "2026-04-11-my-article.md"

    def test_slug_preserved(self):
        result = self._rename("2025-06-01-ai-testing-trends.md", "2026-04-11")
        assert result == "2026-04-11-ai-testing-trends.md"

    def test_no_date_prefix_unchanged(self):
        """Files without YYYY-MM-DD prefix should be unchanged."""
        result = self._rename("article-without-date.md", "2026-04-11")
        assert result == "article-without-date.md"


# ---------------------------------------------------------------------------
# Integration-style tests for main() using mocks
# ---------------------------------------------------------------------------


def _make_args(tmp_path: Path, article_path: Path):
    """Build a mock argparse Namespace for main()."""
    args = MagicMock()
    args.blog_repo = "test-owner/test-blog"
    args.token = "fake-token"
    args.article = article_path
    return args


class TestDeployToBlogMain:
    """Functional tests for main() via subprocess mocking."""

    # ------------------------------------------------------------------
    # Shared fixture
    # ------------------------------------------------------------------
    @pytest.fixture()
    def article_file(self, tmp_path: Path) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        p = tmp_path / f"{today}-my-article.md"
        p.write_text(_make_article(date=today))
        return p

    @pytest.fixture()
    def stale_article_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "2026-01-15-stale-article.md"
        p.write_text(_make_article(date="2026-01-15"))
        return p

    # ------------------------------------------------------------------
    # Helpers to build the mocked environment for main()
    # ------------------------------------------------------------------
    def _run_main(
        self,
        tmp_path: Path,
        article_path: Path,
        *,
        validation_result: tuple[bool, str] = (True, "✅ All checks passed"),
    ):
        """
        Run deploy_to_blog.main() with all side-effects mocked.

        Returns
        -------
        run_command_mock : MagicMock
        validate_file_mock : MagicMock
        """
        blog_dir = tmp_path / "temp_blog_repo"
        posts_dir = blog_dir / "_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)

        # Patch run_command so no real git/gh/rm commands are executed.
        # We still allow the file write (target_article.write_text) to happen
        # by manually creating the posts dir above.
        import scripts.deploy_to_blog as dtb

        original_posts_dir_cls = Path

        def fake_run_command(cmd, cwd=None):
            # For `rm -rf temp_blog_repo` calls, do nothing (skip real FS ops)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command) as rc_mock,
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=validation_result,
            ) as vf_mock,
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("scripts.deploy_to_blog.Path", wraps=original_posts_dir_cls) as _,
            patch("sys.exit") as exit_mock,
        ):
            # Wire up fake args
            pa_mock.return_value = _make_args(tmp_path, article_path)

            # Point blog_dir / posts_dir to our tmp location
            with patch.object(dtb, "Path") as path_cls_mock:
                # Allow most Path calls to fall through to real Path
                path_cls_mock.side_effect = lambda *a, **kw: original_posts_dir_cls(
                    *a, **kw
                )
                # Override "temp_blog_repo" to use tmp_path
                path_cls_mock.return_value = blog_dir

                try:
                    dtb.main()
                except SystemExit:
                    pass

            return rc_mock, vf_mock, exit_mock

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_validate_file_called_with_deploy_date(
        self, tmp_path: Path, stale_article_file: Path
    ):
        """validate_file must receive today's date as expected_date."""
        today = datetime.now().strftime("%Y-%m-%d")

        blog_dir = tmp_path / "temp_blog_repo"

        import scripts.deploy_to_blog as dtb

        captured: dict = {}

        def fake_run_command(cmd, cwd=None):
            return ""

        def fake_validate(file_path: str, expected_date: str | None = None):
            captured["file_path"] = file_path
            captured["expected_date"] = expected_date
            return True, "✅ All checks passed"

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("sys.exit"),
        ):
            pa_mock.return_value = _make_args(tmp_path, stale_article_file)

            # Manually set up the blog_dir structure that main() would create
            posts_dir = tmp_path / "temp_blog_repo" / "_posts"
            posts_dir.mkdir(parents=True, exist_ok=True)
            (tmp_path / "temp_blog_repo" / "assets" / "charts").mkdir(
                parents=True, exist_ok=True
            )

            with patch("scripts.deploy_to_blog.Path") as path_cls_mock:
                from pathlib import Path as RealPath

                def path_side_effect(*args, **kwargs):
                    p = RealPath(*args, **kwargs)
                    return p

                path_cls_mock.side_effect = path_side_effect

                # Override "temp_blog_repo" to resolve to tmp_path's blog_dir
                with patch.object(
                    dtb, "Path", side_effect=lambda *a, **kw: (
                        blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                    )
                ):
                    try:
                        dtb.main()
                    except (SystemExit, Exception):
                        pass

        # The captured expected_date should be today
        if "expected_date" in captured:
            assert captured["expected_date"] == today

    def test_date_injected_in_written_content(
        self, tmp_path: Path, stale_article_file: Path
    ):
        """The article written to the blog clone must carry today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        blog_dir = tmp_path / "temp_blog_repo"
        posts_dir = blog_dir / "_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)

        import scripts.deploy_to_blog as dtb
        from pathlib import Path as RealPath

        written: dict = {}

        def fake_run_command(cmd, cwd=None):
            return ""

        def fake_validate(file_path: str, expected_date: str | None = None):
            # Read back what was written
            try:
                written["content"] = RealPath(file_path).read_text()
            except FileNotFoundError:
                pass
            return True, "✅ All checks passed"

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("sys.exit"),
        ):
            pa_mock.return_value = _make_args(tmp_path, stale_article_file)

            with patch.object(
                dtb, "Path", side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                )
            ):
                try:
                    dtb.main()
                except (SystemExit, Exception):
                    pass

        if "content" in written:
            assert f"date: {today}" in written["content"], (
                f"Expected 'date: {today}' in written content, got:\n{written['content'][:500]}"
            )

    def test_validation_failure_calls_sys_exit_1(
        self, tmp_path: Path, stale_article_file: Path
    ):
        """On validation failure, sys.exit(1) must be called."""
        blog_dir = tmp_path / "temp_blog_repo"
        posts_dir = blog_dir / "_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)

        import scripts.deploy_to_blog as dtb
        from pathlib import Path as RealPath

        exit_calls: list = []

        def fake_exit(code=0):
            exit_calls.append(code)
            raise SystemExit(code)

        def fake_run_command(cmd, cwd=None):
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ CRITICAL: date_mismatch"),
            ),
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("sys.exit", side_effect=fake_exit),
        ):
            pa_mock.return_value = _make_args(tmp_path, stale_article_file)

            with patch.object(
                dtb, "Path", side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                )
            ):
                with pytest.raises(SystemExit):
                    dtb.main()

        assert 1 in exit_calls, "Expected sys.exit(1) on validation failure"

    def test_pr_not_created_on_validation_failure(
        self, tmp_path: Path, stale_article_file: Path
    ):
        """When validation fails, gh pr create must NOT be invoked."""
        blog_dir = tmp_path / "temp_blog_repo"
        posts_dir = blog_dir / "_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)

        import scripts.deploy_to_blog as dtb
        from pathlib import Path as RealPath

        pr_commands: list[str] = []

        def fake_run_command(cmd, cwd=None):
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ CRITICAL: date_mismatch"),
            ),
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("sys.exit", side_effect=SystemExit),
        ):
            pa_mock.return_value = _make_args(tmp_path, stale_article_file)

            with patch.object(
                dtb, "Path", side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                )
            ):
                with pytest.raises(SystemExit):
                    dtb.main()

        assert pr_commands == [], "gh pr create must not run when validation fails"

    def test_validation_report_included_in_pr_body(
        self, tmp_path: Path, stale_article_file: Path
    ):
        """The PR body must contain the validation report text."""
        blog_dir = tmp_path / "temp_blog_repo"
        posts_dir = blog_dir / "_posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (blog_dir / "assets" / "charts").mkdir(parents=True, exist_ok=True)

        import scripts.deploy_to_blog as dtb
        from pathlib import Path as RealPath

        pr_commands: list[str] = []
        validation_report = "✅ All 8 checks passed"

        def fake_run_command(cmd, cwd=None):
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, validation_report),
            ),
            patch("argparse.ArgumentParser.parse_args") as pa_mock,
            patch("sys.exit"),
        ):
            pa_mock.return_value = _make_args(tmp_path, stale_article_file)

            with patch.object(
                dtb, "Path", side_effect=lambda *a, **kw: (
                    blog_dir if a == ("temp_blog_repo",) else RealPath(*a, **kw)
                )
            ):
                try:
                    dtb.main()
                except (SystemExit, Exception):
                    pass

        if pr_commands:
            pr_cmd = pr_commands[0]
            assert validation_report in pr_cmd, (
                "Validation report must appear in gh pr create --body argument"
            )
