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


@pytest.fixture(autouse=True)
def _sandbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point B-045's deployable root at the test's own `output/` directory.

    The root is deliberately *not* a tool argument — an agent must not be able to
    widen its own sandbox — so tests move it via the environment instead.
    """
    monkeypatch.setenv("BLOG_DEPLOY_OUTPUT_ROOT", str(tmp_path / "output"))


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
        "Article body.\n",
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
        self,
        sample_article: Path,
        tmp_path: Path,
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

    def test_returns_articles_from_canonical_output_posts_dir(
        self, tmp_path: Path
    ) -> None:
        from mcp_servers.blog_deployer_server import list_deployable_articles

        posts_dir = tmp_path / "output" / "posts"
        posts_dir.mkdir(parents=True)
        (posts_dir / "canonical-article.md").write_text("---\n---\n")

        result = list_deployable_articles(str(tmp_path / "output"))

        assert result == [str(posts_dir / "canonical-article.md")]


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

    def test_article_not_found(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        # Inside the deployable root (B-045) but absent, so this still exercises
        # the missing-file branch rather than the sandbox refusal.
        missing = tmp_path / "output" / "article.md"
        result = deploy_article(str(missing), "oviney/blog")
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
        charts_dir = output_dir / "charts"
        charts_dir.mkdir()
        (charts_dir / "my-chart.png").write_bytes(b"png")
        article = output_dir / "2026-04-05-chart-article.md"
        article.write_text(
            "---\nlayout: post\ntitle: Charts\ndate: 2026-04-05\n---\n\n"
            "![Chart](output/charts/my-chart.png)\n",
        )

        result = deploy_article(str(article), "oviney/blog")
        assert result["success"] is True

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_missing_referenced_chart_blocks_canonical_deploy(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mock_run.return_value = "https://github.com/oviney/blog/pull/1"

        posts_dir = tmp_path / "output" / "posts"
        posts_dir.mkdir(parents=True)
        article = posts_dir / "chart-article.md"
        article.write_text(
            "---\nlayout: post\ntitle: Charts\ndate: 2026-04-05\n---\n\n"
            "![Chart](/assets/charts/chart-article.png)\n",
        )

        result = deploy_article(str(article), "oviney/blog")

        assert result["success"] is False
        assert "Chart asset not found" in result["error"]

    @patch("mcp_servers.blog_deployer_server.shutil.copy2")
    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_copies_referenced_chart_from_canonical_output_layout(
        self,
        mock_run: MagicMock,
        mock_copy: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        mock_run.return_value = "https://github.com/oviney/blog/pull/1"

        posts_dir = tmp_path / "output" / "posts"
        posts_dir.mkdir(parents=True)
        charts_dir = tmp_path / "output" / "charts"
        charts_dir.mkdir()
        chart = charts_dir / "chart-article.png"
        chart.write_bytes(b"png")
        article = posts_dir / "chart-article.md"
        article.write_text(
            "---\nlayout: post\ntitle: Charts\ndate: 2026-04-05\n---\n\n"
            "![Chart](/assets/charts/chart-article.png)\n",
        )

        result = deploy_article(str(article), "oviney/blog")

        assert result["success"] is True
        assert any(call.args[0] == chart for call in mock_copy.call_args_list)


class TestDeployArticlePathSandbox:
    """B-045: `article_path` is agent-supplied, so it must not escape `output/`.

    `deploy_article` copies the named file into a **public** blog PR using
    `GITHUB_TOKEN`. An agent steered by injected text in fetched research could
    otherwise name any readable file and have it published.
    """

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_rejects_article_outside_the_output_root(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        secret = tmp_path / "secrets.md"
        secret.write_text("ANTHROPIC_API_KEY=sk-should-never-be-published\n")

        result = deploy_article(str(secret), "oviney/blog")

        assert result["success"] is False
        assert "outside" in result["error"].lower()
        # The refusal must happen before anything clones or pushes.
        mock_run.assert_not_called()

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_rejects_traversal_out_of_the_output_root(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        secret = tmp_path / "secrets.md"
        secret.write_text("token\n")
        traversal = tmp_path / "output" / ".." / "secrets.md"

        result = deploy_article(str(traversal), "oviney/blog")

        assert result["success"] is False
        assert "outside" in result["error"].lower()
        mock_run.assert_not_called()

    @patch("mcp_servers.blog_deployer_server._run_command")
    def test_rejects_symlink_pointing_out_of_the_output_root(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from mcp_servers.blog_deployer_server import deploy_article

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        secret = tmp_path / "secrets.md"
        secret.write_text("token\n")
        link = tmp_path / "output" / "innocent.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(secret)

        result = deploy_article(str(link), "oviney/blog")

        assert result["success"] is False
        assert "outside" in result["error"].lower()
        mock_run.assert_not_called()

    def test_accepts_an_article_inside_the_output_root(
        self,
        sample_article: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The guard must not reject the legitimate path (no false positive)."""
        from mcp_servers.blog_deployer_server import _resolve_article_path

        resolved, error = _resolve_article_path(str(sample_article))

        assert error is None
        assert resolved == sample_article.resolve()


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
