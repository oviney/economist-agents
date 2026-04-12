#!/usr/bin/env python3
"""Tests for scripts/topic_trend_grounding.py.

All HTTP calls and external API calls are mocked — no real network requests
are made during the test suite.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from topic_trend_grounding import (
    _DEFAULT_QUERIES,
    EvidenceItem,
    TrendEvidence,
    _fetch_hn_top_stories,
    _get_searcher,
    _run_query,
    build_grounded_trend_context,
    format_evidence_as_prompt,
    gather_trend_evidence,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


def _make_web_results(n: int = 3) -> list[dict[str, str]]:
    """Build fake GoogleSearcher.search_web() results."""
    return [
        {
            "title": f"Result {i}: QE Trend",
            "url": f"https://example.com/article-{i}",
            "snippet": f"Snippet about trend {i}",
            "date": f"Apr {datetime.now().year}",
            "source": "google_search",
        }
        for i in range(1, n + 1)
    ]


def _make_hn_api_response(n: int = 3) -> list[int]:
    """Build fake HN top-stories ID list."""
    return list(range(100, 100 + n))


def _make_hn_item(item_id: int) -> dict[str, Any]:
    """Build a single fake HN item payload."""
    return {
        "id": item_id,
        "title": f"HN Story {item_id}",
        "url": f"https://hn-example.com/{item_id}",
        "time": int(datetime.now().timestamp()),
        "type": "story",
    }


@pytest.fixture
def mock_searcher() -> MagicMock:
    """Return a mock GoogleSearcher whose search_web returns 3 results."""
    searcher = MagicMock()
    searcher.search_web.return_value = _make_web_results(3)
    return searcher


# ═══════════════════════════════════════════════════════════════════════════
# Tests: _get_searcher()
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSearcher:
    """Tests for the _get_searcher helper."""

    def test_returns_none_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns None when SERPER_API_KEY is not set."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        assert _get_searcher() is None

    def test_returns_searcher_with_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns a GoogleSearcher when SERPER_API_KEY is set."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")
        with patch.dict(
            "sys.modules",
            {"google_search": MagicMock()},
        ):
            result = _get_searcher()
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# Tests: _run_query()
# ═══════════════════════════════════════════════════════════════════════════


class TestRunQuery:
    """Tests for the _run_query helper."""

    def test_returns_evidence_items(self, mock_searcher: MagicMock) -> None:
        """Returns list of EvidenceItem dicts on success."""
        items = _run_query(mock_searcher, "test query", num_results=3)
        assert len(items) == 3
        assert items[0]["title"] == "Result 1: QE Trend"
        assert items[0]["url"] == "https://example.com/article-1"
        assert items[0]["source"] == "google_search"

    def test_skips_error_results(self, mock_searcher: MagicMock) -> None:
        """Filters out results that contain an error key."""
        mock_searcher.search_web.return_value = [
            {"error": "API quota exceeded"},
            {
                "title": "Valid",
                "url": "https://example.com/valid",
                "snippet": "ok",
                "date": "2026-04",
                "source": "google_search",
            },
        ]
        items = _run_query(mock_searcher, "test query")
        assert len(items) == 1
        assert items[0]["title"] == "Valid"

    def test_returns_empty_on_all_errors(self, mock_searcher: MagicMock) -> None:
        """Returns empty list when every result is an error."""
        mock_searcher.search_web.return_value = [{"error": "fail"}]
        items = _run_query(mock_searcher, "test query")
        assert items == []

    def test_handles_missing_fields_gracefully(
        self, mock_searcher: MagicMock
    ) -> None:
        """Missing optional fields default to empty strings."""
        mock_searcher.search_web.return_value = [
            {"title": "Only title"}
        ]
        items = _run_query(mock_searcher, "q")
        assert len(items) == 1
        assert items[0]["url"] == ""
        assert items[0]["snippet"] == ""
        assert items[0]["date"] == ""


# ═══════════════════════════════════════════════════════════════════════════
# Tests: _fetch_hn_top_stories()
# ═══════════════════════════════════════════════════════════════════════════


class TestFetchHnTopStories:
    """Tests for the Hacker News fetcher."""

    def test_returns_stories_on_success(self) -> None:
        """Returns list of EvidenceItem dicts with HN stories."""
        mock_top_resp = MagicMock()
        mock_top_resp.json.return_value = _make_hn_api_response(3)
        mock_top_resp.raise_for_status = MagicMock()

        items_map = {
            sid: MagicMock(
                json=MagicMock(return_value=_make_hn_item(sid)),
                raise_for_status=MagicMock(),
            )
            for sid in range(100, 103)
        }

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            for sid, mock_resp in items_map.items():
                if str(sid) in url:
                    return mock_resp
            return MagicMock()  # pragma: no cover

        with patch("topic_trend_grounding.requests.get", side_effect=get_side_effect):
            stories = _fetch_hn_top_stories(max_items=3)

        assert len(stories) == 3
        assert stories[0]["source"] == "hacker_news"
        assert stories[0]["title"] == "HN Story 100"
        assert stories[0]["url"] == "https://hn-example.com/100"

    def test_returns_empty_on_network_error(self) -> None:
        """Returns empty list when network request fails."""
        import requests

        with patch(
            "topic_trend_grounding.requests.get",
            side_effect=requests.RequestException("timeout"),
        ):
            stories = _fetch_hn_top_stories()
        assert stories == []

    def test_skips_null_items(self) -> None:
        """Skips HN items that return None/empty."""
        mock_top_resp = MagicMock()
        mock_top_resp.json.return_value = [100]
        mock_top_resp.raise_for_status = MagicMock()

        mock_item_resp = MagicMock()
        mock_item_resp.json.return_value = None
        mock_item_resp.raise_for_status = MagicMock()

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            return mock_item_resp

        with patch("topic_trend_grounding.requests.get", side_effect=get_side_effect):
            stories = _fetch_hn_top_stories()
        assert stories == []

    def test_respects_max_items(self) -> None:
        """Only fetches up to max_items stories."""
        mock_top_resp = MagicMock()
        mock_top_resp.json.return_value = list(range(200, 220))
        mock_top_resp.raise_for_status = MagicMock()

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            # Extract item ID from URL
            item_id = int(url.split("/")[-1].split(".")[0])
            mock_item = MagicMock()
            mock_item.json.return_value = _make_hn_item(item_id)
            mock_item.raise_for_status = MagicMock()
            return mock_item

        with patch("topic_trend_grounding.requests.get", side_effect=get_side_effect):
            stories = _fetch_hn_top_stories(max_items=2)
        assert len(stories) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Tests: gather_trend_evidence()
# ═══════════════════════════════════════════════════════════════════════════


class TestGatherTrendEvidence:
    """Tests for gather_trend_evidence()."""

    def test_returns_evidence_per_query(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns one TrendEvidence per query plus HN."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        mock_searcher = MagicMock()
        mock_searcher.search_web.return_value = _make_web_results(2)

        with (
            patch(
                "topic_trend_grounding._get_searcher", return_value=mock_searcher
            ),
            patch(
                "topic_trend_grounding._fetch_hn_top_stories", return_value=[]
            ),
        ):
            evidence = gather_trend_evidence(
                queries=["q1", "q2"], include_hn=True
            )

        assert len(evidence) == 2  # 2 queries, no HN results
        assert evidence[0]["query"] == "q1"
        assert evidence[1]["query"] == "q2"
        assert len(evidence[0]["results"]) == 2

    def test_includes_hn_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Appends HN evidence when include_hn=True and stories exist."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        hn_item = EvidenceItem(
            title="HN Story",
            url="https://hn.example.com",
            snippet="",
            date="2026-04-12",
            source="hacker_news",
        )

        with (
            patch(
                "topic_trend_grounding._get_searcher", return_value=MagicMock()
            ) as _,
            patch(
                "topic_trend_grounding._fetch_hn_top_stories",
                return_value=[hn_item],
            ),
        ):
            mock_searcher = MagicMock()
            mock_searcher.search_web.return_value = []
            with patch(
                "topic_trend_grounding._get_searcher",
                return_value=mock_searcher,
            ):
                evidence = gather_trend_evidence(
                    queries=["q1"], include_hn=True
                )

        # q1 + HN
        assert len(evidence) == 2
        assert evidence[-1]["query"] == "Hacker News front page"

    def test_skips_hn_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Does not include HN when include_hn=False."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        mock_searcher = MagicMock()
        mock_searcher.search_web.return_value = _make_web_results(1)

        with (
            patch(
                "topic_trend_grounding._get_searcher",
                return_value=mock_searcher,
            ),
            patch(
                "topic_trend_grounding._fetch_hn_top_stories"
            ) as mock_hn,
        ):
            evidence = gather_trend_evidence(
                queries=["q1"], include_hn=False
            )

        mock_hn.assert_not_called()
        assert len(evidence) == 1

    def test_uses_default_queries_when_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uses _DEFAULT_QUERIES when queries=None."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        mock_searcher = MagicMock()
        mock_searcher.search_web.return_value = []

        with (
            patch(
                "topic_trend_grounding._get_searcher",
                return_value=mock_searcher,
            ),
            patch(
                "topic_trend_grounding._fetch_hn_top_stories", return_value=[]
            ),
        ):
            evidence = gather_trend_evidence(queries=None, include_hn=False)

        assert len(evidence) == len(_DEFAULT_QUERIES)

    def test_degrades_without_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns only HN evidence when SERPER_API_KEY is missing."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        hn_item = EvidenceItem(
            title="HN Only",
            url="https://hn.example.com",
            snippet="",
            date="2026-04-12",
            source="hacker_news",
        )

        with patch(
            "topic_trend_grounding._fetch_hn_top_stories",
            return_value=[hn_item],
        ):
            evidence = gather_trend_evidence(
                queries=["q1"], include_hn=True
            )

        assert len(evidence) == 1
        assert evidence[0]["query"] == "Hacker News front page"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: format_evidence_as_prompt()
# ═══════════════════════════════════════════════════════════════════════════


class TestFormatEvidenceAsPrompt:
    """Tests for format_evidence_as_prompt()."""

    def test_formats_evidence_with_titles_and_urls(self) -> None:
        """Output includes titles, URLs, and snippets."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(
                query="AI testing 2026",
                results=[
                    EvidenceItem(
                        title="AI Tool Release",
                        url="https://example.com/ai",
                        snippet="A new AI testing tool was released.",
                        date="Apr 2026",
                        source="google_search",
                    )
                ],
            )
        ]
        output = format_evidence_as_prompt(evidence)

        assert "## Live Trend Evidence" in output
        assert "AI Tool Release" in output
        assert "https://example.com/ai" in output
        assert "A new AI testing tool was released." in output
        assert "Apr 2026" in output

    def test_returns_fallback_when_no_evidence(self) -> None:
        """Returns fallback text when evidence list is empty."""
        output = format_evidence_as_prompt([])
        assert "[UNVERIFIED]" in output
        assert "No live evidence" in output

    def test_returns_fallback_when_results_empty(self) -> None:
        """Returns fallback when evidence entries have zero results."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(query="q1", results=[])
        ]
        output = format_evidence_as_prompt(evidence)
        assert "[UNVERIFIED]" in output

    def test_skips_queries_with_no_results(self) -> None:
        """Queries with empty results are omitted from output."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(query="empty_query", results=[]),
            TrendEvidence(
                query="has_results",
                results=[
                    EvidenceItem(
                        title="Result",
                        url="https://example.com",
                        snippet="Good result",
                        date="2026-04",
                        source="google_search",
                    )
                ],
            ),
        ]
        output = format_evidence_as_prompt(evidence)
        assert "empty_query" not in output
        assert "has_results" in output

    def test_includes_collected_count(self) -> None:
        """Output includes the total number of collected items."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(
                query="q",
                results=[
                    EvidenceItem(
                        title=f"R{i}",
                        url=f"https://example.com/{i}",
                        snippet="",
                        date="",
                        source="google_search",
                    )
                    for i in range(5)
                ],
            )
        ]
        output = format_evidence_as_prompt(evidence)
        assert "5 items" in output

    def test_handles_missing_date_gracefully(self) -> None:
        """Items without date don't show empty parens."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(
                query="q",
                results=[
                    EvidenceItem(
                        title="No Date Item",
                        url="https://example.com",
                        snippet="Snippet",
                        date="",
                        source="google_search",
                    )
                ],
            )
        ]
        output = format_evidence_as_prompt(evidence)
        assert "No Date Item" in output
        assert "()" not in output

    def test_handles_missing_url(self) -> None:
        """Items without URL don't show 'URL:' line."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(
                query="q",
                results=[
                    EvidenceItem(
                        title="No URL",
                        url="",
                        snippet="Snippet",
                        date="2026-04",
                        source="google_search",
                    )
                ],
            )
        ]
        output = format_evidence_as_prompt(evidence)
        assert "No URL" in output
        assert "URL:" not in output


# ═══════════════════════════════════════════════════════════════════════════
# Tests: build_grounded_trend_context()
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildGroundedTrendContext:
    """Tests for build_grounded_trend_context()."""

    def test_returns_formatted_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns a non-empty formatted string."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        evidence = [
            TrendEvidence(
                query="test",
                results=[
                    EvidenceItem(
                        title="Article",
                        url="https://example.com",
                        snippet="Snippet",
                        date="Apr 2026",
                        source="google_search",
                    )
                ],
            )
        ]
        with patch(
            "topic_trend_grounding.gather_trend_evidence", return_value=evidence
        ):
            context = build_grounded_trend_context()

        assert isinstance(context, str)
        assert len(context) > 0
        assert "Article" in context

    def test_adds_focus_area_queries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Extra queries are added when focus_area is provided."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        captured_queries: list[list[str]] = []

        def mock_gather(
            queries: list[str] | None = None, **kwargs: Any
        ) -> list[TrendEvidence]:
            captured_queries.append(queries or [])
            return []

        with patch(
            "topic_trend_grounding.gather_trend_evidence",
            side_effect=mock_gather,
        ):
            build_grounded_trend_context(focus_area="test automation")

        assert len(captured_queries) == 1
        queries = captured_queries[0]
        focus_queries = [q for q in queries if "test automation" in q]
        assert len(focus_queries) >= 2

    def test_returns_fallback_without_evidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns fallback text when no evidence collected."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        with patch(
            "topic_trend_grounding.gather_trend_evidence", return_value=[]
        ):
            context = build_grounded_trend_context()

        assert "[UNVERIFIED]" in context

    def test_no_focus_area_uses_default_queries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without focus_area, only default queries are used."""
        monkeypatch.setenv("SERPER_API_KEY", "fake-key")

        captured_queries: list[list[str]] = []

        def mock_gather(
            queries: list[str] | None = None, **kwargs: Any
        ) -> list[TrendEvidence]:
            captured_queries.append(queries or [])
            return []

        with patch(
            "topic_trend_grounding.gather_trend_evidence",
            side_effect=mock_gather,
        ):
            build_grounded_trend_context(focus_area=None)

        assert len(captured_queries[0]) == len(_DEFAULT_QUERIES)
