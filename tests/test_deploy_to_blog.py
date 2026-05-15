#!/usr/bin/env python3
"""Tests for scripts/deploy_to_blog.py

Covers:
- deploy-date injection into YAML front matter
- article filename renaming to deploy date
- PublicationValidator called as blocking gate before PR creation
- Validation failure short-circuits before push/PR
- Validation report included in PR body
- The callable deploy() contract added by #336
"""

import contextlib
import re
from datetime import datetime
from pathlib import Path
from pathlib import Path as RealPath
from unittest.mock import patch

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
        f'author: "Ouray Viney"\n'
        f'categories: ["Quality Engineering"]\n'
        f"---\n\n"
        f"{VALID_BODY}\n\n"
        f"{VALID_REFERENCES}\n"
    )


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
    """Tests for the deploy()-via-CLI integration concerns.

    These were originally written against the old inline ``main()``
    that called ``sys.exit(1)`` on validation failure. After #336 the
    callable ``deploy()`` returns a typed :class:`DeployResult` and
    ``main()`` translates that into an exit code, so they have been
    rewritten to assert the new contract.
    """

    @pytest.fixture
    def stale_article_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> Path:
        monkeypatch.chdir(tmp_path)
        p = tmp_path / "2026-01-15-stale-article.md"
        p.write_text(_make_article(date="2026-01-15"))
        return p

    def _setup_clone(self, _cwd) -> None:
        blog = Path("temp_blog_repo")
        blog.mkdir(exist_ok=True)
        (blog / "_posts").mkdir(exist_ok=True)
        (blog / "assets" / "charts").mkdir(parents=True, exist_ok=True)
        (blog / "assets" / "images").mkdir(parents=True, exist_ok=True)

    def test_validate_file_called_with_deploy_date(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """validate_file must be called with today's date as expected_date."""
        today = datetime.now().strftime("%Y-%m-%d")
        captured: dict = {}

        def fake_validate(
            file_path: str, expected_date: str | None = None
        ) -> tuple[bool, str]:
            captured["expected_date"] = expected_date
            return True, "✅ All checks passed"

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._setup_clone(cwd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
        ):
            dtb.deploy(
                article_path=stale_article_file,
                blog_owner="o",
                blog_repo="r",
                token="t",
            )

        assert captured.get("expected_date") == today

    def test_date_injected_in_written_content(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """The article written to the blog clone must carry today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        captured: dict = {}

        def fake_validate(
            file_path: str, expected_date: str | None = None
        ) -> tuple[bool, str]:
            with contextlib.suppress(FileNotFoundError):
                captured["content"] = RealPath(file_path).read_text()
            return True, "✅ All checks passed"

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._setup_clone(cwd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch("scripts.deploy_to_blog.validate_file", side_effect=fake_validate),
        ):
            dtb.deploy(
                article_path=stale_article_file,
                blog_owner="o",
                blog_repo="r",
                token="t",
            )

        assert "content" in captured, "validate_file was not given a readable file"
        assert f"date: {today}" in captured["content"]

    def test_main_returns_exit_code_1_on_validation_failure(
        self, tmp_path: Path, stale_article_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() must return exit code 1 when validation fails."""

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._setup_clone(cwd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ date_mismatch"),
            ),
        ):
            exit_code = dtb.main(
                [
                    "--blog-owner",
                    "test-owner",
                    "--blog-repo",
                    "test-blog",
                    "--token",
                    "fake-token",
                    "--article",
                    str(stale_article_file),
                ]
            )

        assert exit_code == 1, "main() must return 1 on validation failure"

    def test_pr_not_created_on_validation_failure(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """When validation fails, gh pr create must NOT be invoked."""
        pr_commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._setup_clone(cwd)
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ date_mismatch"),
            ),
        ):
            result = dtb.deploy(
                article_path=stale_article_file,
                blog_owner="o",
                blog_repo="r",
                token="t",
            )

        assert result.status == "validation_failed"
        assert pr_commands == [], "gh pr create must not run when validation fails"

    def test_validation_report_included_in_pr_body(
        self, tmp_path: Path, stale_article_file: Path
    ) -> None:
        """The PR body must contain the validation report text."""
        pr_commands: list[str] = []
        validation_report = "✅ All 8 checks passed"

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                self._setup_clone(cwd)
            if "gh pr create" in cmd:
                pr_commands.append(cmd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, validation_report),
            ),
        ):
            dtb.deploy(
                article_path=stale_article_file,
                blog_owner="o",
                blog_repo="r",
                token="t",
            )

        assert pr_commands, "gh pr create was not called on successful validation"
        assert validation_report in pr_commands[0], (
            "Validation report must appear in gh pr create --body argument"
        )


# ---------------------------------------------------------------------------
# Integration tests for the callable deploy() function (#336)
# ---------------------------------------------------------------------------


class TestDeployCallable:
    """Integration tests for the callable deploy() function.

    Subprocess (``run_command``) and the publication validator are mocked
    so the tests don't shell out to git or hit GitHub.
    """

    @pytest.fixture
    def article_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        # Work inside tmp_path so the blog clone dir ('temp_blog_repo')
        # is created in an isolated location.
        monkeypatch.chdir(tmp_path)
        article = tmp_path / "2026-01-15-callable-deploy.md"
        article.write_text(_make_article(date="2026-01-15"))
        return article

    def _prepare_blog_clone(self, cwd: Path | None) -> None:
        """Side-effect helper: mimic `git clone` by materialising temp_blog_repo."""
        # Only the `git clone` invocation has cwd=None and contains "git clone".
        # We don't inspect the command — the dispatch happens in the
        # fake_run_command closure below.
        blog = Path("temp_blog_repo")
        blog.mkdir(exist_ok=True)
        (blog / "_posts").mkdir(exist_ok=True)
        (blog / "assets" / "charts").mkdir(parents=True, exist_ok=True)
        (blog / "assets" / "images").mkdir(parents=True, exist_ok=True)

    def test_happy_path_pushes_and_opens_pr(
        self, article_file: Path, tmp_path: Path
    ) -> None:
        """Happy path: clone → branch → copy → validate → commit → push → PR."""
        commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                # Materialise the clone directory so subsequent steps
                # (mkdir / file copies) work against a real filesystem.
                self._prepare_blog_clone(cwd)
            # Empty `git status --porcelain` → no double-commit amend.
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, "✅ All checks passed"),
            ),
        ):
            result = dtb.deploy(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="fake-token",
            )

        assert result.status == "published"
        assert result.pushed is True
        assert result.article_name.endswith("-callable-deploy.md")
        # Token must appear in the clone URL (used to push as well).
        assert any(
            "git clone https://x-access-token:fake-token@github.com/test-owner/test-blog.git"
            in c
            for c in commands
        ), "clone command missing or token not interpolated"
        # PR creation must run against the full owner/repo.
        assert any("gh pr create --repo test-owner/test-blog" in c for c in commands), (
            "PR was not created"
        )
        # Push must target the new branch.
        assert any(c.startswith("git push origin content/") for c in commands), (
            "branch push not invoked"
        )

    def test_auth_failure_raises_deploy_error(
        self, article_file: Path, tmp_path: Path
    ) -> None:
        """A failing `git clone` (e.g. bad token) must raise DeployError."""

        def fake_run_command(cmd: str, cwd=None) -> str:
            if cmd.startswith("git clone"):
                raise dtb.DeployError(
                    "Command failed (exit 128): git clone …\n"
                    "remote: Invalid username or password.\n"
                    "fatal: Authentication failed"
                )
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, "✅ All checks passed"),
            ),
            pytest.raises(dtb.DeployError, match="Authentication failed"),
        ):
            dtb.deploy(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="bad-token",
            )

    def test_already_up_to_date_returns_status(
        self, article_file: Path, tmp_path: Path
    ) -> None:
        """When `git commit` reports nothing to commit, return status='up_to_date'."""
        commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_blog_clone(cwd)
                return ""
            if cmd.startswith("git commit -m"):
                raise dtb.DeployError(
                    'Command failed (exit 1): git commit -m "…"\n'
                    "nothing to commit, working tree clean"
                )
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, "✅ All checks passed"),
            ),
        ):
            result = dtb.deploy(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="fake-token",
            )

        assert result.status == "up_to_date"
        assert result.pushed is False
        # No push or PR should have run on the no-op path.
        assert not any(c.startswith("git push") for c in commands)
        assert not any("gh pr create" in c for c in commands)

    def test_validation_failure_short_circuits(
        self, article_file: Path, tmp_path: Path
    ) -> None:
        """When validate_file returns False, abort before commit/push/PR."""
        commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_blog_clone(cwd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(False, "❌ date_mismatch"),
            ),
        ):
            result = dtb.deploy(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="fake-token",
            )

        assert result.status == "validation_failed"
        assert result.pushed is False
        assert "date_mismatch" in result.validation_report
        assert not any(c.startswith("git push") for c in commands)
        assert not any("gh pr create" in c for c in commands)
        assert not any(c.startswith("git commit -m") for c in commands)

    def test_missing_article_raises(self, tmp_path: Path) -> None:
        """deploy() must reject a non-existent article path up front."""
        with pytest.raises(dtb.DeployError, match="Article not found"):
            dtb.deploy(
                article_path=tmp_path / "does-not-exist.md",
                blog_owner="owner",
                blog_repo="repo",
                token="t",
            )

    def test_dry_run_skips_push_and_pr(
        self, article_file: Path, tmp_path: Path
    ) -> None:
        """dry_run=True must validate but never push or open a PR."""
        commands: list[str] = []

        def fake_run_command(cmd: str, cwd=None) -> str:
            commands.append(cmd)
            if cmd.startswith("git clone"):
                self._prepare_blog_clone(cwd)
            return ""

        with (
            patch.object(dtb, "run_command", side_effect=fake_run_command),
            patch(
                "scripts.deploy_to_blog.validate_file",
                return_value=(True, "✅ All checks passed"),
            ),
        ):
            result = dtb.deploy(
                article_path=article_file,
                blog_owner="test-owner",
                blog_repo="test-blog",
                token="fake-token",
                dry_run=True,
            )

        assert result.status == "dry_run"
        assert result.pushed is False
        assert not any(c.startswith("git push") for c in commands)
        assert not any("gh pr create" in c for c in commands)
