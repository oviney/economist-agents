#!/usr/bin/env python3
"""Tests for scripts/topic_trend_grounding.py (free, HN-only trend grounding).

The pay-per-use Google/Serper search path was removed; Hacker News (keyless) is
the only trend signal. All HTTP calls are mocked — no real network requests are
made during the test suite.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from scripts.topic_trend_grounding import (
    EvidenceItem,
    TrendEvidence,
    _fetch_hn_top_stories,
    build_grounded_trend_context,
    format_evidence_as_prompt,
    gather_trend_evidence,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════
# Tests: _fetch_hn_top_stories()
# ═══════════════════════════════════════════════════════════════════════════


class TestFetchHnTopStories:
    """Tests for the Hacker News fetcher."""

    def test_returns_stories_on_success(self) -> None:
        """Returns list of EvidenceItem dicts with HN stories."""
        import orjson

        mock_top_resp = MagicMock()
        mock_top_resp.content = orjson.dumps(_make_hn_api_response(3))
        mock_top_resp.raise_for_status = MagicMock()

        items_map = {
            sid: MagicMock(
                content=orjson.dumps(_make_hn_item(sid)),
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

        with patch(
            "scripts.topic_trend_grounding.requests.get", side_effect=get_side_effect
        ):
            stories = _fetch_hn_top_stories(max_items=3)

        assert len(stories) == 3
        assert stories[0]["source"] == "hacker_news"
        assert stories[0]["title"] == "HN Story 100"
        assert stories[0]["url"] == "https://hn-example.com/100"

    def test_returns_empty_on_network_error(self) -> None:
        """Returns empty list when network request fails."""
        import requests

        with patch(
            "scripts.topic_trend_grounding.requests.get",
            side_effect=requests.RequestException("timeout"),
        ):
            stories = _fetch_hn_top_stories()
        assert stories == []

    def test_skips_null_items(self) -> None:
        """Skips HN items that return None/empty."""
        import orjson

        mock_top_resp = MagicMock()
        mock_top_resp.content = orjson.dumps([100])
        mock_top_resp.raise_for_status = MagicMock()

        mock_item_resp = MagicMock()
        mock_item_resp.content = orjson.dumps(None)
        mock_item_resp.raise_for_status = MagicMock()

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            return mock_item_resp

        with patch(
            "scripts.topic_trend_grounding.requests.get", side_effect=get_side_effect
        ):
            stories = _fetch_hn_top_stories()
        assert stories == []

    def test_skips_items_with_zero_timestamp(self) -> None:
        """Skips HN items with missing/zero timestamps (would be 1970-01-01)."""
        import orjson

        mock_top_resp = MagicMock()
        mock_top_resp.content = orjson.dumps([100])
        mock_top_resp.raise_for_status = MagicMock()

        item_no_time = {
            "id": 100,
            "title": "No Time",
            "url": "https://x.com",
            "time": 0,
        }
        mock_item_resp = MagicMock()
        mock_item_resp.content = orjson.dumps(item_no_time)
        mock_item_resp.raise_for_status = MagicMock()

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            return mock_item_resp

        with patch(
            "scripts.topic_trend_grounding.requests.get", side_effect=get_side_effect
        ):
            stories = _fetch_hn_top_stories()
        assert stories == []

    def test_respects_max_items(self) -> None:
        """Only fetches up to max_items stories."""
        import orjson

        mock_top_resp = MagicMock()
        mock_top_resp.content = orjson.dumps(list(range(200, 220)))
        mock_top_resp.raise_for_status = MagicMock()

        def get_side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "topstories" in url:
                return mock_top_resp
            item_id = int(url.rsplit("/", maxsplit=1)[-1].split(".", maxsplit=1)[0])
            mock_item = MagicMock()
            mock_item.content = orjson.dumps(_make_hn_item(item_id))
            mock_item.raise_for_status = MagicMock()
            return mock_item

        with patch(
            "scripts.topic_trend_grounding.requests.get", side_effect=get_side_effect
        ):
            stories = _fetch_hn_top_stories(max_items=2)
        assert len(stories) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Tests: gather_trend_evidence()  (HN-only)
# ═══════════════════════════════════════════════════════════════════════════


class TestGatherTrendEvidence:
    """Tests for gather_trend_evidence() — Hacker News is the only source."""

    def test_includes_hn_when_enabled(self) -> None:
        """Appends HN evidence when include_hn=True and stories exist."""
        hn_item = EvidenceItem(
            title="HN Story",
            url="https://hn.example.com",
            snippet="",
            date="2026-06-27",
            source="hacker_news",
        )
        with patch(
            "scripts.topic_trend_grounding._fetch_hn_top_stories",
            return_value=[hn_item],
        ):
            evidence = gather_trend_evidence(include_hn=True)

        assert len(evidence) == 1
        assert evidence[0]["query"] == "Hacker News front page"
        assert evidence[0]["results"] == [hn_item]

    def test_skips_hn_when_disabled(self) -> None:
        """Does not fetch HN when include_hn=False."""
        with patch("scripts.topic_trend_grounding._fetch_hn_top_stories") as mock_hn:
            evidence = gather_trend_evidence(include_hn=False)

        mock_hn.assert_not_called()
        assert evidence == []

    def test_returns_empty_when_hn_yields_nothing(self) -> None:
        """No evidence entry is appended when HN returns no stories."""
        with patch(
            "scripts.topic_trend_grounding._fetch_hn_top_stories", return_value=[]
        ):
            evidence = gather_trend_evidence(include_hn=True)

        assert evidence == []


# ═══════════════════════════════════════════════════════════════════════════
# Tests: format_evidence_as_prompt()
# ═══════════════════════════════════════════════════════════════════════════


class TestFormatEvidenceAsPrompt:
    """Tests for format_evidence_as_prompt()."""

    def test_formats_evidence_with_titles_and_urls(self) -> None:
        """Output includes titles, URLs, and snippets."""
        evidence: list[TrendEvidence] = [
            TrendEvidence(
                query="Hacker News front page",
                results=[
                    EvidenceItem(
                        title="AI Tool Release",
                        url="https://example.com/ai",
                        snippet="A new AI testing tool was released.",
                        date="2026-06-27",
                        source="hacker_news",
                    ),
                ],
            ),
        ]
        output = format_evidence_as_prompt(evidence)

        assert "## Live Trend Evidence" in output
        assert "AI Tool Release" in output
        assert "https://example.com/ai" in output
        assert "A new AI testing tool was released." in output
        assert "2026-06-27" in output

    def test_returns_fallback_when_no_evidence(self) -> None:
        """Returns fallback text when evidence list is empty."""
        output = format_evidence_as_prompt([])
        assert "[UNVERIFIED]" in output
        assert "No live evidence" in output

    def test_returns_fallback_when_results_empty(self) -> None:
        """Returns fallback when evidence entries have zero results."""
        evidence: list[TrendEvidence] = [TrendEvidence(query="q1", results=[])]
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
                        source="hacker_news",
                    ),
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
                        source="hacker_news",
                    )
                    for i in range(5)
                ],
            ),
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
                        source="hacker_news",
                    ),
                ],
            ),
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
                        source="hacker_news",
                    ),
                ],
            ),
        ]
        output = format_evidence_as_prompt(evidence)
        assert "No URL" in output
        assert "URL:" not in output


# ═══════════════════════════════════════════════════════════════════════════
# Tests: build_grounded_trend_context()
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildGroundedTrendContext:
    """Tests for build_grounded_trend_context()."""

    def test_returns_formatted_string(self) -> None:
        """Returns a non-empty formatted string built from gathered evidence."""
        evidence = [
            TrendEvidence(
                query="Hacker News front page",
                results=[
                    EvidenceItem(
                        title="Article",
                        url="https://example.com",
                        snippet="Snippet",
                        date="2026-06-27",
                        source="hacker_news",
                    ),
                ],
            ),
        ]
        with patch(
            "scripts.topic_trend_grounding.gather_trend_evidence",
            return_value=evidence,
        ):
            context = build_grounded_trend_context()

        assert isinstance(context, str)
        assert "Article" in context

    def test_focus_area_is_accepted_and_does_not_break(self) -> None:
        """focus_area is retained for API compatibility (no longer query-driving)."""
        with patch(
            "scripts.topic_trend_grounding.gather_trend_evidence",
            return_value=[],
        ) as mock_gather:
            context = build_grounded_trend_context(focus_area="test automation")

        mock_gather.assert_called_once_with(include_hn=True)
        assert "[UNVERIFIED]" in context

    def test_returns_fallback_without_evidence(self) -> None:
        """Returns fallback text when no evidence collected."""
        with patch(
            "scripts.topic_trend_grounding.gather_trend_evidence", return_value=[]
        ):
            context = build_grounded_trend_context()

        assert "[UNVERIFIED]" in context
