"""Tests for scripts/arxiv_search.py rate-limit hardening.

Focus: the retry/backoff wrapper around the arXiv client must survive a
single transient 429 and recover, without retrying clean empty results.
All network and sleep are mocked — no real calls.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import arxiv
import pytest

from scripts.arxiv_search import ArxivSearcher


def _mock_result(title: str = "Paper", days_old: int = 1) -> Mock:
    """Build a minimal arxiv.Result-like mock recent enough to pass the date filter."""
    published = datetime.now()
    author = Mock()
    author.name = "A. One"
    result = Mock()
    result.title = title
    result.authors = [author]
    result.summary = "We show a 42% improvement in something measurable."
    result.published = published
    result.entry_id = "http://arxiv.org/abs/2406.00001v1"
    result.categories = ["cs.AI"]
    result.journal_ref = None
    result.doi = None
    return result


class TestArxivRetry:
    def test_retries_on_429_then_succeeds(self) -> None:
        """A 429 on the first attempt should retry and return papers, not zero out."""
        searcher = ArxivSearcher(max_results=3, days_back=60)

        attempts = {"n": 0}

        def flaky_results(_search):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise arxiv.HTTPError(url="http://arxiv.org", retry=0, status=429)
            return iter([_mock_result("Recovered")])

        with (
            patch("scripts.arxiv_search.arxiv.Client") as mock_client_cls,
            patch("scripts.arxiv_search.time.sleep") as mock_sleep,
        ):
            mock_client = Mock()
            mock_client.results.side_effect = flaky_results
            mock_client_cls.return_value = mock_client

            papers = searcher.search_recent_papers("ai automation")

        assert attempts["n"] == 2  # retried exactly once
        assert len(papers) == 1
        assert papers[0]["title"] == "Recovered"
        mock_sleep.assert_called()  # backoff slept between attempts

    def test_does_not_retry_clean_empty_results(self) -> None:
        """An empty (but successful) page is not an error and must not be retried."""
        searcher = ArxivSearcher(max_results=3, days_back=60)

        attempts = {"n": 0}

        def empty_results(_search):
            attempts["n"] += 1
            return iter([])

        with (
            patch("scripts.arxiv_search.arxiv.Client") as mock_client_cls,
            patch("scripts.arxiv_search.time.sleep"),
        ):
            mock_client = Mock()
            mock_client.results.side_effect = empty_results
            mock_client_cls.return_value = mock_client

            papers = searcher.search_recent_papers("nonexistent topic")

        assert papers == []
        assert attempts["n"] == 1  # no retry on clean empty result

    def test_gives_up_after_max_attempts_on_persistent_429(self) -> None:
        """Persistent 429 across all attempts raises, after backing off each time."""
        from scripts.arxiv_search import ArxivSearchError

        searcher = ArxivSearcher(max_results=3, days_back=60)

        attempts = {"n": 0}

        def always_429(_search):
            attempts["n"] += 1
            raise arxiv.HTTPError(url="http://arxiv.org", retry=0, status=429)

        with (
            patch("scripts.arxiv_search.arxiv.Client") as mock_client_cls,
            patch("scripts.arxiv_search.time.sleep") as mock_sleep,
        ):
            mock_client = Mock()
            mock_client.results.side_effect = always_429
            mock_client_cls.return_value = mock_client

            with pytest.raises(ArxivSearchError):
                searcher.search_recent_papers("ai automation")

        assert attempts["n"] == 3  # three attempts total
        assert mock_sleep.call_count == 2  # slept between attempts, not after the last
