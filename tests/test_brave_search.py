"""Tests for scripts/brave_search.py (#388)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import orjson
import pytest

from scripts.brave_search import (
    BraveSearcher,
    _normalise,
    search_brave_for_topic,
)


def _mock_response(payload: dict) -> Mock:
    r = Mock()
    r.content = orjson.dumps(payload)
    r.raise_for_status = Mock()
    return r


def _result(title: str = "Result") -> dict:
    return {
        "title": title,
        "url": f"https://example.com/{title.lower()}",
        "description": f"A snippet about {title}.",
        "age": "3 days ago",
    }


class TestNormalise:
    def test_maps_description_to_snippet(self) -> None:
        out = _normalise(_result("X"))
        assert out["snippet"] == "A snippet about X."

    def test_preserves_age_string_verbatim(self) -> None:
        out = _normalise({"age": "yesterday"})
        assert out["age"] == "yesterday"

    def test_defaults_missing_fields_to_safe_sentinels(self) -> None:
        out = _normalise({})
        assert out["title"] == "Unknown"
        assert out["url"] == ""
        assert out["snippet"] == ""
        assert out["age"] == ""


class TestBraveSearcher:
    def test_has_credentials_true_when_key_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BRAVE_API_KEY", "tok")
        assert BraveSearcher().has_credentials is True

    def test_has_credentials_false_when_key_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        assert BraveSearcher().has_credentials is False

    def test_search_raises_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="BRAVE_API_KEY"):
            BraveSearcher().search("x")

    def test_sends_subscription_token_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BRAVE_API_KEY", "tok-123")
        with patch("scripts.brave_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"web": {"results": []}})
            BraveSearcher().search("AI testing")
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["X-Subscription-Token"] == "tok-123"
        assert headers["Accept"] == "application/json"

    def test_returns_results_from_web_results_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BRAVE_API_KEY", "tok")
        with patch("scripts.brave_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                {"web": {"results": [_result("A"), _result("B")]}}
            )
            results = BraveSearcher(max_results=3).search("q")
        assert len(results) == 2
        assert results[0]["title"] == "A"

    def test_handles_missing_web_key_gracefully(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Brave occasionally returns only spell-check / faq sections
        monkeypatch.setenv("BRAVE_API_KEY", "tok")
        with patch("scripts.brave_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"query": "x"})
            assert BraveSearcher().search("x") == []


class TestSearchBraveForTopic:
    def test_success_path_returns_normalised_results(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BRAVE_API_KEY", "tok")
        with patch("scripts.brave_search.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                {"web": {"results": [_result("First"), _result("Second")]}}
            )
            result = search_brave_for_topic("flaky tests", max_results=5)
        assert result["success"] is True
        assert result["results_found"] == 2
        assert result["results"][0]["snippet"].startswith("A snippet about")
        assert result["error"] is None

    def test_missing_key_returns_failure_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        result = search_brave_for_topic("anything")
        assert result["success"] is False
        assert "BRAVE_API_KEY" in result["error"]
        assert result["results_found"] == 0

    def test_http_error_returns_failure_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BRAVE_API_KEY", "tok")
        with patch(
            "scripts.brave_search.requests.get",
            side_effect=ConnectionError("network down"),
        ):
            result = search_brave_for_topic("x")
        assert result["success"] is False
        assert "network down" in result["error"]
