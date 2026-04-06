#!/usr/bin/env python3
"""Unit tests for scripts/google_search.py.

All HTTP calls are mocked — no real network requests are made.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

import scripts.google_search as google_search_module
from scripts.google_search import GoogleSearcher, search_google_for_topic


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def searcher(monkeypatch: pytest.MonkeyPatch) -> GoogleSearcher:
    """Return a GoogleSearcher with a fake API key and fixed year."""
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    return GoogleSearcher(current_year=2026)


def _make_web_response(n: int = 2) -> dict[str, Any]:
    """Build a minimal Serper web-search response with *n* organic results."""
    return {
        "organic": [
            {
                "title": f"Web Result {i}",
                "link": f"https://example.com/{i}",
                "snippet": f"Snippet {i}",
                "date": "Apr 2026",
            }
            for i in range(1, n + 1)
        ]
    }


def _make_scholar_response(n: int = 2) -> dict[str, Any]:
    """Build a minimal Serper Scholar response with *n* organic results."""
    return {
        "organic": [
            {
                "title": f"Scholar Paper {i}",
                "link": f"https://scholar.example.com/{i}",
                "snippet": f"Abstract {i}",
                "year": 2026,
                "authors": f"Author {i} et al.",
                "citedBy": i * 10,
            }
            for i in range(1, n + 1)
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════
# GoogleSearcher.search_web
# ═══════════════════════════════════════════════════════════════════════════


class TestGoogleSearcherSearchWeb:
    """Tests for GoogleSearcher.search_web()."""

    def test_returns_results_on_success(self, searcher: GoogleSearcher) -> None:
        """Returns list of dicts with expected keys on successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = _make_web_response(2)
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_web("AI testing", num_results=2)

        assert len(results) == 2
        assert results[0]["title"] == "Web Result 1"
        assert results[0]["url"] == "https://example.com/1"
        assert results[0]["snippet"] == "Snippet 1"
        assert results[0]["source"] == "google_search"
        assert "date" in results[0]

    def test_respects_num_results_limit(self, searcher: GoogleSearcher) -> None:
        """Returns at most num_results items even if API returns more."""
        mock_response = MagicMock()
        mock_response.json.return_value = _make_web_response(10)
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_web("topic", num_results=3)

        assert len(results) == 3

    def test_missing_api_key_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When SERPER_API_KEY is absent, returns error without HTTP call."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        s = GoogleSearcher()

        with patch("scripts.google_search.requests.post") as mock_post:
            results = s.search_web("test")

        mock_post.assert_not_called()
        assert len(results) == 1
        assert "error" in results[0]
        assert "SERPER_API_KEY" in results[0]["error"]

    def test_http_error_returns_structured_error(
        self, searcher: GoogleSearcher
    ) -> None:
        """HTTP error from Serper returns structured error dict."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_web("query")

        assert len(results) == 1
        assert "error" in results[0]
        assert "HTTP error" in results[0]["error"]

    def test_network_error_returns_structured_error(
        self, searcher: GoogleSearcher
    ) -> None:
        """Network failure returns structured error dict."""
        with patch(
            "scripts.google_search.requests.post",
            side_effect=requests.ConnectionError("unreachable"),
        ):
            results = searcher.search_web("query")

        assert len(results) == 1
        assert "error" in results[0]

    def test_empty_organic_returns_empty_list(self, searcher: GoogleSearcher) -> None:
        """Empty organic list from API returns empty result list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_web("obscure query")

        assert results == []

    def test_year_appended_to_query_when_year_start_provided(
        self, searcher: GoogleSearcher
    ) -> None:
        """year_start causes an 'after:' clause to be added to the query."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "scripts.google_search.requests.post", return_value=mock_response
        ) as mock_post:
            searcher.search_web("test topic", year_start=2025)

        call_kwargs = mock_post.call_args[1]["json"]
        assert "after:2024" in call_kwargs["q"]

    def test_single_year_appended_when_start_equals_end(
        self, searcher: GoogleSearcher
    ) -> None:
        """When year_start == year_end, just the year is appended."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "scripts.google_search.requests.post", return_value=mock_response
        ) as mock_post:
            searcher.search_web("test topic", year_start=2026, year_end=2026)

        call_kwargs = mock_post.call_args[1]["json"]
        assert "2026" in call_kwargs["q"]


# ═══════════════════════════════════════════════════════════════════════════
# GoogleSearcher.search_scholar
# ═══════════════════════════════════════════════════════════════════════════


class TestGoogleSearcherSearchScholar:
    """Tests for GoogleSearcher.search_scholar()."""

    def test_returns_scholar_results_on_success(
        self, searcher: GoogleSearcher
    ) -> None:
        """Returns list of dicts with expected keys on successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = _make_scholar_response(2)
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_scholar("machine learning testing")

        assert len(results) == 2
        assert results[0]["title"] == "Scholar Paper 1"
        assert results[0]["source"] == "google_scholar"
        assert results[0]["year"] == "2026"
        assert "authors" in results[0]
        assert "cited_by" in results[0]

    def test_year_start_and_end_sent_in_payload(
        self, searcher: GoogleSearcher
    ) -> None:
        """year_start and year_end are forwarded as yearLow/yearHigh to Serper."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "scripts.google_search.requests.post", return_value=mock_response
        ) as mock_post:
            searcher.search_scholar("topic", year_start=2025, year_end=2026)

        payload = mock_post.call_args[1]["json"]
        assert payload["yearLow"] == 2025
        assert payload["yearHigh"] == 2026

    def test_no_year_params_not_sent_when_none(
        self, searcher: GoogleSearcher
    ) -> None:
        """yearLow/yearHigh are absent from payload when year args are None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "scripts.google_search.requests.post", return_value=mock_response
        ) as mock_post:
            searcher.search_scholar("topic")

        payload = mock_post.call_args[1]["json"]
        assert "yearLow" not in payload
        assert "yearHigh" not in payload

    def test_missing_api_key_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When SERPER_API_KEY is absent, returns error without HTTP call."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        s = GoogleSearcher()

        with patch("scripts.google_search.requests.post") as mock_post:
            results = s.search_scholar("topic")

        mock_post.assert_not_called()
        assert "error" in results[0]

    def test_http_error_returns_structured_error(
        self, searcher: GoogleSearcher
    ) -> None:
        """HTTP error returns structured error dict."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401")

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_scholar("topic")

        assert "error" in results[0]
        assert "HTTP error" in results[0]["error"]

    def test_uses_scholar_endpoint(self, searcher: GoogleSearcher) -> None:
        """Requests are sent to the /scholar Serper endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = MagicMock()

        with patch(
            "scripts.google_search.requests.post", return_value=mock_response
        ) as mock_post:
            searcher.search_scholar("topic")

        called_url = mock_post.call_args[0][0]
        assert "/scholar" in called_url

    def test_respects_num_results_limit(self, searcher: GoogleSearcher) -> None:
        """Returns at most num_results scholar results."""
        mock_response = MagicMock()
        mock_response.json.return_value = _make_scholar_response(10)
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            results = searcher.search_scholar("topic", num_results=3)

        assert len(results) == 3


# ═══════════════════════════════════════════════════════════════════════════
# search_google_for_topic (convenience function)
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchGoogleForTopic:
    """Tests for the search_google_for_topic() convenience function."""

    def _patch_searcher(
        self,
        web_results: list[dict],
        scholar_results: list[dict],
    ) -> MagicMock:
        """Return a mock GoogleSearcher instance with preset return values."""
        mock_instance = MagicMock()
        mock_instance.search_web.return_value = web_results
        mock_instance.search_scholar.return_value = scholar_results
        return mock_instance

    def test_success_returns_combined_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns dict with success=True and both web and scholar results."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")
        mock_response = MagicMock()
        mock_response.json.side_effect = [
            {"organic": [{"title": "W1", "link": "https://w1.com", "snippet": "", "date": ""}]},
            {"organic": [{"title": "S1", "link": "https://s1.com", "snippet": "", "year": 2026, "authors": "A", "citedBy": 5}]},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("scripts.google_search.requests.post", return_value=mock_response):
            result = search_google_for_topic("AI testing")

        assert result["success"] is True
        assert result["topic"] == "AI testing"
        assert len(result["web_results"]) == 1
        assert result["web_results"][0]["title"] == "W1"
        assert result["web_results"][0]["source"] == "google_search"
        assert len(result["scholar_results"]) == 1
        assert result["scholar_results"][0]["title"] == "S1"
        assert result["scholar_results"][0]["source"] == "google_scholar"
        assert result["error"] is None

    def test_year_range_set_to_current_and_previous(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """current_year and year_start span current and previous year."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")
        current_year = datetime.now().year

        mock_instance = self._patch_searcher([], [])
        with patch.object(google_search_module, "GoogleSearcher", return_value=mock_instance):
            result = search_google_for_topic("topic")

        assert result["current_year"] == current_year
        assert result["year_start"] == current_year - 1

    def test_scholar_skipped_when_include_scholar_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When include_scholar=False, search_scholar is not called."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")
        mock_instance = self._patch_searcher([], [])

        with patch.object(google_search_module, "GoogleSearcher", return_value=mock_instance):
            result = search_google_for_topic("topic", include_scholar=False)

        mock_instance.search_scholar.assert_not_called()
        assert result["scholar_results"] == []

    def test_exception_returns_failure_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unexpected error returns success=False with error message."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        with patch.object(
            google_search_module,
            "GoogleSearcher",
            side_effect=RuntimeError("boom"),
        ):
            result = search_google_for_topic("topic")

        assert result["success"] is False
        assert "boom" in result["error"]
        assert result["web_results"] == []
        assert result["scholar_results"] == []

    def test_web_query_includes_year_range(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Web search query contains 'current_year OR previous_year' for freshness."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")
        current_year = datetime.now().year
        mock_instance = self._patch_searcher([], [])

        with patch.object(google_search_module, "GoogleSearcher", return_value=mock_instance):
            search_google_for_topic("AI testing")

        call_args = mock_instance.search_web.call_args
        query_used = call_args[1]["query"] if "query" in call_args[1] else call_args[0][0]
        assert str(current_year) in query_used
        assert str(current_year - 1) in query_used
