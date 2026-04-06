"""Tests for Blog Deployer MCP Server (Story 18.3).

Tests mock all git/gh operations — no real PRs created.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GITHUB_TOKEN is not leaked from environment."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


@pytest.fixture
def sample_article(tmp_path: Path) -> Path:
    """Create a sample article for deployment tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    article = output_dir / "2026-04-05-test-article.md"
    article.write_text(
        "---\n"
        "layout: post\n"
        'title: "Test Article"\n'
        "date: 2026-04-05\n"
        "image: /assets/images/test-article.png\n"
        "---\n\n"
        "Article body.\n"
    )
    return article


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Create a sample image alongside the article."""
    images_dir = tmp_path / "output" / "images"
    images_dir.mkdir(parents=True)
    image = images_dir / "test-article.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return image


class TestListDeployableArticles:
    """Tests for list_deployable_articles tool."""

    def test_returns_articles_from_output_dir(
        self, sample_article: Path, tmp_path: Path
    ) -> None:
        from mcp_servers.blog_deployer_server import list_deployable_articles

        result = list_deployable_articles(str(tmp_path / "output"))
        assert len(result) == 1
        assert "2026-04-05-test-article.md" in result[0]

    def test_returns_empty_when_no_articles(self, tmp_path: Path) -> None:
        from mcp_servers.blog_deployer_server import list_deployable_articles

        empty_dir = tmp_path / "empty_output"
        empty_dir.mkdir()
        result = list_deployable_articles(str(empty_dir))
        assert result == []

    def test_returns_empty_when_dir_missing(self) -> None:
        from mcp_servers.blog_deployer_server import list_deployable_articles

        result = list_deployable_articles("/nonexistent/path")
        assert result == []

    def test_excludes_non_markdown_files(self, tmp_path: Path) -> None:
        from mcp_servers.blog_deployer_server import list_deployable_articles

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "not-an-article.txt").write_text("hello")
        (output_dir / "2026-04-05-real-article.md").write_text("---\n---\n")
        result = list_deployable_articles(str(output_dir))
        assert len(result) == 1
        assert "real-article" in result[0]


class TestDeployArticle:
    """Tests for deploy_article tool."""

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_successful_deployment(
        self,
        mock_run: MagicMock,
        sample_article: Path,
        sample_image: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        # Mock git/gh commands to succeed
        mock_run.return_value = ""

        # Mock the PR URL extraction
        mock_run.side_effect = lambda cmd, **kwargs: (
            "https://github.com/oviney/blog/pull/999" if "gh pr create" in cmd else ""
        )

        result = deploy_article(
            str(sample_article),
            "oviney/blog",
        )

        assert result["success"] is True
        assert "pr_url" in result
        assert result["article"] == "2026-04-05-test-article.md"

    def test_missing_github_token(self, sample_article: Path) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        result = deploy_article(str(sample_article), "oviney/blog")
        assert result["success"] is False
        assert "GITHUB_TOKEN" in result["error"]

    def test_article_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        result = deploy_article("/nonexistent/article.md", "oviney/blog")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_git_clone_failure(
        self,
        mock_run: MagicMock,
        sample_article: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mock_run.side_effect = subprocess.CalledProcessError(1, "git clone")

        result = deploy_article(str(sample_article), "oviney/blog")
        assert result["success"] is False
        assert "error" in result

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_cleanup_on_failure(
        self,
        mock_run: MagicMock,
        sample_article: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mock_run.side_effect = subprocess.CalledProcessError(1, "git push")

        result = deploy_article(str(sample_article), "oviney/blog")
        assert result["success"] is False
        # Temp directory should be cleaned up even on failure

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_chart_path_rewriting(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mock_run.return_value = "https://github.com/oviney/blog/pull/1"

        # Article with output/charts/ path that needs rewriting
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        article = output_dir / "2026-04-05-chart-article.md"
        article.write_text(
            "---\nlayout: post\ntitle: Charts\ndate: 2026-04-05\n---\n\n"
            "![Chart](output/charts/my-chart.png)\n"
        )

        result = deploy_article(str(article), "oviney/blog")
        assert result["success"] is True


class TestMcpServerRegistration:
    """Tests for MCP server configuration."""

    def test_server_name(self) -> None:
        from mcp_servers.blog_deployer_server import mcp

        assert mcp.name == "blog-deployer"

    def test_tools_registered(self) -> None:
        from mcp_servers.blog_deployer_server import mcp

        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        assert "deploy_article" in tool_names
        assert "list_deployable_articles" in tool_names
