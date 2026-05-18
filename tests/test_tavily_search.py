"""Tests for scripts/tavily_search.py (#388)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import orjson
import pytest

from scripts.tavily_search import (
    TavilySearcher,
    _normalise,
    search_tavily_for_topic,
)


def _mock_response(payload: dict) -> Mock:
    r = Mock()
    r.content = orjson.dumps(payload)
    r.raise_for_status = Mock()
    return r


def _result(title: str = "Result", score: float = 0.9) -> dict:
    return {
        "title": title,
        "url": f"https://example.com/{title.lower()}",
        "content": f"Pre-summarised content about {title}.",
        "score": score,
    }


class TestNormalise:
    def test_maps_content_to_snippet(self) -> None:
        out = _normalise(_result("X"))
        assert out["snippet"] == "Pre-summarised content about X."

    def test_preserves_score(self) -> None:
        out = _normalise(_result(score=0.42))
        assert out["score"] == 0.42

    def test_defaults_missing_fields(self) -> None:
        out = _normalise({})
        assert out["title"] == "Unknown"
        assert out["url"] == ""
        assert out["snippet"] == ""
        assert out["score"] == 0.0


class TestTavilySearcher:
    def test_has_credentials_follows_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        assert TavilySearcher().has_credentials is False
        monkeypatch.setenv("TAVILY_API_KEY", "tok")
        assert TavilySearcher().has_credentials is True

    def test_search_raises_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
            TavilySearcher().search("x")

    def test_posts_with_api_key_in_body_not_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Tavily authenticates via JSON body field, not Authorization header.
        # Asserting this prevents an easy migration mistake.
        monkeypatch.setenv("TAVILY_API_KEY", "tok-99")
        with patch("scripts.tavily_search.requests.post") as mock_post:
            mock_post.return_value = _mock_response({"results": []})
            TavilySearcher(max_results=4).search("AI testing")
        body = mock_post.call_args.kwargs["json"]
        assert body["api_key"] == "tok-99"
        assert body["query"] == "AI testing"
        assert body["max_results"] == 4
        assert body["include_answer"] is True

    def test_returns_parsed_response_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "tok")
        with patch("scripts.tavily_search.requests.post") as mock_post:
            mock_post.return_value = _mock_response(
                {"results": [_result("A")], "answer": "Summary text."}
            )
            body = TavilySearcher().search("q")
        assert body["answer"] == "Summary text."
        assert len(body["results"]) == 1


class TestSearchTavilyForTopic:
    def test_success_path_includes_results_and_answer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "tok")
        with patch("scripts.tavily_search.requests.post") as mock_post:
            mock_post.return_value = _mock_response(
                {
                    "results": [_result("First", 0.95), _result("Second", 0.8)],
                    "answer": "Both papers agree on X.",
                }
            )
            result = search_tavily_for_topic("flaky tests", max_results=5)
        assert result["success"] is True
        assert result["results_found"] == 2
        assert result["answer"] == "Both papers agree on X."
        # Scores preserved for the writer to rank by
        assert result["results"][0]["score"] == 0.95
        assert result["error"] is None

    def test_answer_defaults_to_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "tok")
        with patch("scripts.tavily_search.requests.post") as mock_post:
            mock_post.return_value = _mock_response({"results": []})
            result = search_tavily_for_topic("x")
        assert result["answer"] == ""

    def test_missing_key_returns_failure_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        result = search_tavily_for_topic("anything")
        assert result["success"] is False
        assert "TAVILY_API_KEY" in result["error"]
        assert result["results_found"] == 0
        assert result["answer"] == ""

    def test_http_error_returns_failure_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "tok")
        with patch(
            "scripts.tavily_search.requests.post",
            side_effect=ConnectionError("network down"),
        ):
            result = search_tavily_for_topic("x")
        assert result["success"] is False
        assert "network down" in result["error"]
