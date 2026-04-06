#!/usr/bin/env python3
"""Tests for mcp_servers/web_researcher_server.py.

All HTTP calls and external library calls are mocked — no real network
requests are made during the test suite.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

import mcp_servers.web_researcher_server as web_researcher_module
from mcp_servers.web_researcher_server import (
    fetch_page,
    search_arxiv,
    search_google_scholar,
    search_web,
)

# ═══════════════════════════════════════════════════════════════════════════
# search_web
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchWeb:
    """Tests for the search_web MCP tool."""

    def test_returns_results_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given a valid query and API key, returns list of {title,url,snippet}."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Result One",
                    "link": "https://example.com/1",
                    "snippet": "Snippet one",
                },
                {
                    "title": "Result Two",
                    "link": "https://example.com/2",
                    "snippet": "Snippet two",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            return_value=mock_response,
        ) as mock_post:
            results = search_web("test query", num_results=2)

        mock_post.assert_called_once()
        assert len(results) == 2
        assert results[0]["title"] == "Result One"
        assert results[0]["url"] == "https://example.com/1"
        assert results[0]["snippet"] == "Snippet one"
        assert results[1]["title"] == "Result Two"

    def test_respects_num_results_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns at most num_results items even when API returns more."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        organic = [
            {"title": f"R{i}", "link": f"https://example.com/{i}", "snippet": f"S{i}"}
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": organic}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            return_value=mock_response,
        ):
            results = search_web("query", num_results=3)

        assert len(results) == 3

    def test_missing_api_key_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Given no SERPER_API_KEY, returns structured error without HTTP call."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        with patch("mcp_servers.web_researcher_server.requests.post") as mock_post:
            results = search_web("test query")

        mock_post.assert_not_called()
        assert len(results) == 1
        assert "error" in results[0]
        assert "SERPER_API_KEY" in results[0]["error"]

    def test_http_error_returns_structured_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Given an HTTP error from Serper, returns structured error dict."""
        monkeypatch.setenv("SERPER_API_KEY", "bad-key")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            return_value=mock_response,
        ):
            results = search_web("query")

        assert len(results) == 1
        assert "error" in results[0]
        assert "HTTP error" in results[0]["error"]

    def test_network_error_returns_structured_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Given a network failure, returns structured error dict."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            side_effect=requests.ConnectionError("Network unreachable"),
        ):
            results = search_web("query")

        assert len(results) == 1
        assert "error" in results[0]

    def test_empty_organic_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When API returns empty organic list, returns empty list."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            return_value=mock_response,
        ):
            results = search_web("obscure query")

        assert results == []

    def test_default_num_results_is_five(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default num_results is 5."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        organic = [
            {"title": f"R{i}", "link": f"https://x.com/{i}", "snippet": ""}
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": organic}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.post",
            return_value=mock_response,
        ):
            results = search_web("query")

        assert len(results) == 5


# ═══════════════════════════════════════════════════════════════════════════
# search_arxiv
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchArxiv:
    """Tests for the search_arxiv MCP tool."""

    def _make_paper(self, idx: int) -> dict[str, Any]:
        return {
            "title": f"Paper {idx}",
            "authors": [f"Author {idx}"],
            "abstract": f"Abstract text for paper {idx}.",
            "url": f"https://arxiv.org/abs/2401.{idx:05d}",
            "published": f"2026-01-{idx:02d}",
            "arxiv_id": f"2401.{idx:05d}",
            "relevance_score": 3.0,
            "days_old": idx,
        }

    def test_returns_paper_list_on_success(self) -> None:
        """Given a valid query, returns list of paper dicts."""
        papers = [self._make_paper(i) for i in range(1, 4)]

        with (
            patch.object(web_researcher_module, "search_arxiv_for_topic") as mock_topic,
            patch.object(web_researcher_module, "ArxivSearcher") as MockSearcher,
        ):
            mock_topic.return_value = {"success": True, "insights": {}, "error": None}
            instance = MockSearcher.return_value
            instance.search_recent_papers.return_value = papers

            results = search_arxiv("machine learning", max_results=3)

        assert len(results) == 3
        assert results[0]["title"] == "Paper 1"
        assert "authors" in results[0]
        assert "abstract" in results[0]
        assert "url" in results[0]
        assert "published" in results[0]

    def test_arxiv_search_failure_returns_error(self) -> None:
        """When search_arxiv_for_topic raises, returns structured error."""
        with patch.object(
            web_researcher_module,
            "search_arxiv_for_topic",
            side_effect=RuntimeError("arxiv down"),
        ):
            results = search_arxiv("query")

        assert len(results) == 1
        assert "error" in results[0]
        assert "arxiv" in results[0]["error"].lower()

    def test_unsuccessful_search_returns_error(self) -> None:
        """When search_arxiv_for_topic returns success=False, returns error."""
        with patch.object(
            web_researcher_module,
            "search_arxiv_for_topic",
            return_value={
                "success": False,
                "error": "Package not installed",
                "insights": {},
            },
        ):
            results = search_arxiv("query")

        assert len(results) == 1
        assert "error" in results[0]

    def test_arxiv_searcher_fallback_on_exception(self) -> None:
        """When ArxivSearcher raises, falls back to citation strings."""
        citations = ["Author (2026). Title. arXiv:123"]

        with (
            patch.object(
                web_researcher_module,
                "search_arxiv_for_topic",
                return_value={
                    "success": True,
                    "insights": {"citations": citations},
                    "error": None,
                },
            ),
            patch.object(
                web_researcher_module,
                "ArxivSearcher",
                side_effect=RuntimeError("no arxiv package"),
            ),
        ):
            results = search_arxiv("query")

        # Should fall back to citation-based minimal records
        assert len(results) == 1
        assert results[0]["title"] == citations[0]

    def test_empty_results_when_no_papers(self) -> None:
        """Returns empty list when no papers found and no citations."""
        with (
            patch.object(
                web_researcher_module,
                "search_arxiv_for_topic",
                return_value={"success": True, "insights": {}, "error": None},
            ),
            patch.object(web_researcher_module, "ArxivSearcher") as MockSearcher,
        ):
            instance = MockSearcher.return_value
            instance.search_recent_papers.return_value = []

            results = search_arxiv("very obscure topic")

        assert results == []

    def test_respects_max_results(self) -> None:
        """Returns at most max_results papers."""
        papers = [self._make_paper(i) for i in range(1, 11)]

        with (
            patch.object(
                web_researcher_module,
                "search_arxiv_for_topic",
                return_value={"success": True, "insights": {}, "error": None},
            ),
            patch.object(web_researcher_module, "ArxivSearcher") as MockSearcher,
        ):
            instance = MockSearcher.return_value
            instance.search_recent_papers.return_value = papers

            results = search_arxiv("topic", max_results=3)

        assert len(results) == 3


# ═══════════════════════════════════════════════════════════════════════════
# fetch_page
# ═══════════════════════════════════════════════════════════════════════════


class TestFetchPage:
    """Tests for the fetch_page MCP tool."""

    def test_returns_plain_text_from_html(self) -> None:
        """Strips HTML tags and returns plain text."""
        html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.get", return_value=mock_response
        ):
            result = fetch_page("https://example.com")

        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_strips_script_and_style_blocks(self) -> None:
        """Removes <script> and <style> block contents."""
        html = (
            "<html><head><style>body{color:red}</style></head>"
            "<body><script>alert('x')</script><p>Content</p></body></html>"
        )
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.get", return_value=mock_response
        ):
            result = fetch_page("https://example.com")

        assert "Content" in result
        assert "alert" not in result
        assert "color:red" not in result

    def test_http_error_returns_error_string(self) -> None:
        """Given an HTTP error, returns error message string."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch(
            "mcp_servers.web_researcher_server.requests.get", return_value=mock_response
        ):
            result = fetch_page("https://example.com/missing")

        assert result.startswith("Error:")
        assert "HTTP error" in result

    def test_network_error_returns_error_string(self) -> None:
        """Given a network failure, returns error message string."""
        with patch(
            "mcp_servers.web_researcher_server.requests.get",
            side_effect=requests.ConnectionError("Timeout"),
        ):
            result = fetch_page("https://unreachable.example.com")

        assert result.startswith("Error:")

    def test_unexpected_error_returns_error_string(self) -> None:
        """Given an unexpected exception, returns error message string."""
        with patch(
            "mcp_servers.web_researcher_server.requests.get",
            side_effect=ValueError("unexpected"),
        ):
            result = fetch_page("https://example.com")

        assert result.startswith("Error:")
        assert "Unexpected" in result

    def test_collapses_whitespace(self) -> None:
        """Collapses multiple whitespace characters into single spaces."""
        html = "<p>Hello     World</p>"
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch(
            "mcp_servers.web_researcher_server.requests.get", return_value=mock_response
        ):
            result = fetch_page("https://example.com")

        assert "  " not in result
        assert "Hello" in result
        assert "World" in result


# ═══════════════════════════════════════════════════════════════════════════
# search_google_scholar
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchGoogleScholar:
    """Tests for the search_google_scholar MCP tool."""

    def _make_scholar_result(self, idx: int) -> dict[str, Any]:
        return {
            "title": f"Scholar Paper {idx}",
            "url": f"https://scholar.example.com/{idx}",
            "snippet": f"Abstract {idx}",
            "year": "2026",
            "authors": f"Author {idx}",
            "cited_by": idx * 5,
            "source": "google_scholar",
        }

    def test_returns_scholar_results_on_success(self) -> None:
        """Returns list of scholar paper dicts on success."""
        papers = [self._make_scholar_result(i) for i in range(1, 4)]
        mock_searcher = MagicMock()
        mock_searcher.search_scholar.return_value = papers

        with patch.object(
            web_researcher_module, "_GoogleSearcher", return_value=mock_searcher
        ):
            results = search_google_scholar("software testing AI", max_results=3)

        assert len(results) == 3
        assert results[0]["title"] == "Scholar Paper 1"
        assert results[0]["source"] == "google_scholar"

    def test_missing_google_search_module_returns_error(self) -> None:
        """When _GoogleSearcher is None (module not available), returns error."""
        original = web_researcher_module._GoogleSearcher
        web_researcher_module._GoogleSearcher = None  # type: ignore[assignment]
        try:
            results = search_google_scholar("topic")
        finally:
            web_researcher_module._GoogleSearcher = original  # type: ignore[assignment]

        assert len(results) == 1
        assert "error" in results[0]

    def test_defaults_to_current_and_previous_year(self) -> None:
        """When year args are None, defaults year range to current and previous year."""
        from datetime import datetime as _dt

        current_year = _dt.now().year
        mock_searcher = MagicMock()
        mock_searcher.search_scholar.return_value = []

        with patch.object(
            web_researcher_module, "_GoogleSearcher", return_value=mock_searcher
        ):
            search_google_scholar("topic")

        call_kwargs = mock_searcher.search_scholar.call_args[1]
        assert call_kwargs["year_start"] == current_year - 1
        assert call_kwargs["year_end"] == current_year

    def test_explicit_year_params_forwarded(self) -> None:
        """Explicit year_start and year_end are forwarded to the searcher."""
        mock_searcher = MagicMock()
        mock_searcher.search_scholar.return_value = []

        with patch.object(
            web_researcher_module, "_GoogleSearcher", return_value=mock_searcher
        ):
            search_google_scholar("topic", year_start=2024, year_end=2025)

        call_kwargs = mock_searcher.search_scholar.call_args[1]
        assert call_kwargs["year_start"] == 2024
        assert call_kwargs["year_end"] == 2025

    def test_exception_returns_structured_error(self) -> None:
        """Unexpected exception from searcher returns structured error dict."""
        mock_searcher = MagicMock()
        mock_searcher.search_scholar.side_effect = RuntimeError("API down")

        with patch.object(
            web_researcher_module, "_GoogleSearcher", return_value=mock_searcher
        ):
            results = search_google_scholar("topic")

        assert len(results) == 1
        assert "error" in results[0]
        assert "Google Scholar" in results[0]["error"]
