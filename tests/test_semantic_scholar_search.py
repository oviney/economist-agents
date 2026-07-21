"""Tests for scripts/semantic_scholar_search.py (#388)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import orjson
import pytest
import requests

from scripts.semantic_scholar_search import (
    SemanticScholarSearcher,
    _normalise,
    search_semantic_scholar_for_topic,
)


def _mock_response(payload: dict, status: int = 200) -> Mock:
    r = Mock()
    r.status_code = status
    r.content = orjson.dumps(payload)
    if status >= 400:
        r.raise_for_status = Mock(
            side_effect=requests.exceptions.HTTPError(f"HTTP {status}")
        )
    else:
        r.raise_for_status = Mock()
    return r


def _paper(title: str = "Paper", year: int = 2025, doi: str = "10.0/x") -> dict:
    return {
        "title": title,
        "authors": [{"name": "A. One"}, {"name": "B. Two"}],
        "year": year,
        "abstract": "An abstract about something." * 30,
        "externalIds": {"DOI": doi},
        "url": f"https://semanticscholar.org/paper/{doi}",
        "citationCount": 42,
        "venue": "ICSE",
    }


class TestNormalise:
    def test_collapses_authors_to_csv_string(self) -> None:
        out = _normalise(_paper())
        assert out["authors"] == "A. One, B. Two"

    def test_truncates_abstract_to_500_chars(self) -> None:
        out = _normalise(_paper())
        assert len(out["abstract"]) == 500

    def test_extracts_doi_from_external_ids(self) -> None:
        out = _normalise(_paper(doi="10.1145/test"))
        assert out["doi"] == "10.1145/test"

    def test_missing_fields_default_to_sentinels(self) -> None:
        out = _normalise({})
        assert out["title"] == "Unknown"
        assert out["authors"] == "Unknown"
        assert out["year"] == "N/A"
        assert out["doi"] == ""
        assert out["citation_count"] == 0

    def test_handles_none_authors_list(self) -> None:
        # Semantic Scholar can return authors: None for some papers
        out = _normalise({"title": "x", "authors": None})
        assert out["authors"] == "Unknown"


class TestSemanticScholarSearcher:
    def test_sends_api_key_header_when_env_var_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "secret-token")
        searcher = SemanticScholarSearcher()
        with patch("scripts.semantic_scholar_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"data": []})
            searcher.search("AI testing")
        kwargs = mock_get.call_args.kwargs
        assert kwargs["headers"] == {"x-api-key": "secret-token"}

    def test_omits_header_when_env_var_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
        searcher = SemanticScholarSearcher()
        with patch("scripts.semantic_scholar_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"data": []})
            searcher.search("AI testing")
        assert mock_get.call_args.kwargs["headers"] == {}

    def test_returns_papers_from_data_field(self) -> None:
        searcher = SemanticScholarSearcher(max_results=3)
        with patch("scripts.semantic_scholar_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                {"data": [_paper("First"), _paper("Second")]}
            )
            result = searcher.search("flaky tests")
        assert len(result) == 2
        assert result[0]["title"] == "First"

    def test_raises_on_http_error(self) -> None:
        searcher = SemanticScholarSearcher()
        with (
            patch("scripts.semantic_scholar_search.requests.get") as mock_get,
            patch("scripts.semantic_scholar_search.time.sleep"),
        ):
            err_resp = Mock()
            err_resp.status_code = 500
            err_resp.raise_for_status.side_effect = Exception("HTTP 500")
            mock_get.return_value = err_resp
            with pytest.raises(Exception, match="HTTP 500"):
                searcher.search("x")


class TestSemanticScholarRetry:
    def test_retries_on_429_then_succeeds(self) -> None:
        """A 429 first response retries and recovers, not zeroing the provider."""
        searcher = SemanticScholarSearcher(max_results=3)
        rate_limited = _mock_response({}, status=429)
        ok = _mock_response({"data": [_paper("Recovered")]})

        with (
            patch("scripts.semantic_scholar_search.requests.get") as mock_get,
            patch("scripts.semantic_scholar_search.time.sleep") as mock_sleep,
        ):
            mock_get.side_effect = [rate_limited, ok]
            result = searcher.search("flaky tests")

        assert mock_get.call_count == 2  # retried exactly once
        assert len(result) == 1
        assert result[0]["title"] == "Recovered"
        mock_sleep.assert_called()  # backoff slept between attempts

    def test_retries_on_connection_error_then_succeeds(self) -> None:
        """A transient ConnectionError retries and recovers."""
        searcher = SemanticScholarSearcher(max_results=3)
        ok = _mock_response({"data": [_paper("Recovered")]})

        with (
            patch("scripts.semantic_scholar_search.requests.get") as mock_get,
            patch("scripts.semantic_scholar_search.time.sleep"),
        ):
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("reset"),
                ok,
            ]
            result = searcher.search("flaky tests")

        assert mock_get.call_count == 2
        assert result[0]["title"] == "Recovered"

    def test_does_not_retry_clean_empty_results(self) -> None:
        """An empty 200 response is a clean result, not retried."""
        searcher = SemanticScholarSearcher(max_results=3)
        with (
            patch("scripts.semantic_scholar_search.requests.get") as mock_get,
            patch("scripts.semantic_scholar_search.time.sleep"),
        ):
            mock_get.return_value = _mock_response({"data": []})
            result = searcher.search("nothing here")

        assert result == []
        assert mock_get.call_count == 1  # no retry on clean empty result

    def test_gives_up_after_max_attempts_on_persistent_429(self) -> None:
        """Persistent 429 raises after exhausting retries, backing off each time."""
        searcher = SemanticScholarSearcher(max_results=3)
        with (
            patch("scripts.semantic_scholar_search.requests.get") as mock_get,
            patch("scripts.semantic_scholar_search.time.sleep") as mock_sleep,
        ):
            mock_get.return_value = _mock_response({}, status=429)
            with pytest.raises(requests.exceptions.HTTPError):
                searcher.search("flaky tests")

        assert mock_get.call_count == 3  # three attempts total
        assert mock_sleep.call_count == 2  # slept between attempts, not after last


class TestSearchSemanticScholarForTopic:
    def test_returns_success_dict_with_normalised_papers(self) -> None:
        with patch("scripts.semantic_scholar_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                {"data": [_paper("First"), _paper("Second")]}
            )
            result = search_semantic_scholar_for_topic("AI testing", max_papers=5)

        assert result["success"] is True
        assert result["topic"] == "AI testing"
        assert result["papers_found"] == 2
        assert result["error"] is None
        # Normalised shape
        assert result["papers"][0]["authors"] == "A. One, B. Two"
        assert result["papers"][0]["doi"] == "10.0/x"

    def test_returns_failure_dict_on_exception(self) -> None:
        with patch(
            "scripts.semantic_scholar_search.requests.get",
            side_effect=ConnectionError("no internet"),
        ):
            result = search_semantic_scholar_for_topic("anything")
        assert result["success"] is False
        assert result["papers_found"] == 0
        assert result["papers"] == []
        assert "no internet" in result["error"]

    def test_zero_results_is_success_with_empty_list(self) -> None:
        # Provider ran cleanly; topic too narrow. Caller distinguishes via
        # papers_found, not success.
        with patch("scripts.semantic_scholar_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"data": []})
            result = search_semantic_scholar_for_topic("xxxnonexistentyyy")
        assert result["success"] is True
        assert result["papers_found"] == 0
        assert result["papers"] == []
