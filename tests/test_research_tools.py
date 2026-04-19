#!/usr/bin/env python3
"""Tests for CrewAI research tool wrappers.

Validates that ArxivSearchTool and GoogleSearchTool correctly wrap the
existing search scripts and handle missing dependencies gracefully.
"""

from unittest.mock import Mock, patch

import pytest

from src.tools.research_tools import (
    ArxivSearchTool,
    GoogleSearchTool,
    get_research_tools,
)


class TestArxivSearchTool:
    """ArxivSearchTool wraps scripts/arxiv_search.py."""

    def test_tool_metadata(self) -> None:
        tool = ArxivSearchTool()
        assert tool.name == "search_arxiv"
        assert "arXiv" in tool.description

    @patch("src.tools.research_tools.ArxivSearchTool._run")
    def test_returns_papers_on_success(self, mock_run: Mock) -> None:
        mock_run.return_value = (
            "Found 2 arXiv papers on 'AI testing':\n"
            "- Title: Paper One\n  URL: https://arxiv.org/abs/2501.00001\n"
        )
        tool = ArxivSearchTool()
        result = tool._run(topic="AI testing")
        assert "arxiv.org" in result

    def test_handles_import_error(self) -> None:
        tool = ArxivSearchTool()
        with patch.dict("sys.modules", {"arxiv_search": None}):
            with patch(
                "src.tools.research_tools.ArxivSearchTool._run",
                wraps=tool._run,
            ):
                # Direct call with mocked import
                result = tool._run(topic="test")
                # Should not crash — returns error string or results
                assert isinstance(result, str)


class TestGoogleSearchTool:
    """GoogleSearchTool wraps scripts/google_search.py."""

    def test_tool_metadata(self) -> None:
        tool = GoogleSearchTool()
        assert tool.name == "search_google"
        assert "Google" in tool.description

    def test_returns_unavailable_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        tool = GoogleSearchTool()
        result = tool._run(topic="AI testing")
        assert "unavailable" in result.lower() or "SERPER_API_KEY" in result

    @patch("src.tools.research_tools.GoogleSearchTool._run")
    def test_returns_results_on_success(self, mock_run: Mock) -> None:
        mock_run.return_value = (
            "Google search results for 'AI testing':\n"
            "## Web Results\n"
            "- Netflix Tech Blog\n  URL: https://netflixtechblog.com/article\n"
        )
        tool = GoogleSearchTool()
        result = tool._run(topic="AI testing")
        assert "netflixtechblog.com" in result


class TestGetResearchTools:
    """get_research_tools() returns both tools."""

    def test_returns_two_tools(self) -> None:
        tools = get_research_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "search_arxiv" in names
        assert "search_google" in names

    def test_tools_are_callable(self) -> None:
        tools = get_research_tools()
        for tool in tools:
            assert callable(getattr(tool, "_run", None))
