#!/usr/bin/env python3
"""Semantic Scholar Academic Search integration.

Wraps the public Semantic Scholar Graph API (`api.semanticscholar.org/graph/v1`).
No API key required for low-volume use; an optional ``SEMANTIC_SCHOLAR_API_KEY``
env var unlocks higher rate limits. Mirrors the contract of
``scripts/arxiv_search.search_arxiv_for_topic`` so it slots into
``src/agent_sdk/_shared._run_web_searches`` with the same shape.

Public surface
--------------
SemanticScholarSearcher       — class, configurable rate-limit/timeout
search_semantic_scholar_for_topic(topic, max_papers=5) -> dict
    Convenience function returning::

        {
            "success": bool,
            "topic": str,
            "papers_found": int,
            "papers": list[dict],   # title, authors, year, abstract, doi, url, citation_count
            "error": str | None,
        }
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import orjson
import requests

logger = logging.getLogger(__name__)

_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_DEFAULT_FIELDS = "title,authors,year,abstract,externalIds,url,citationCount,venue"
_DEFAULT_TIMEOUT = 10

# Retry policy for transient failures (HTTP 429 / connection errors).
# Free providers throttle aggressively; a single 429 must not zero out the
# provider. Exponential backoff: 1.5s, 3.0s between three total attempts.
_MAX_ATTEMPTS = 3
_BASE_DELAY = 1.5
# Connection-level errors worth retrying (DNS hiccups, resets, timeouts).
_RETRYABLE_EXC = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class SemanticScholarSearcher:
    """Thin wrapper around the Semantic Scholar paper search endpoint."""

    def __init__(self, max_results: int = 5, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self.max_results = max_results
        self.timeout = timeout
        # Optional key — Semantic Scholar accepts unauthenticated requests
        # under a shared lower-tier rate limit. The key boosts to
        # ~1 req/sec when present.
        self._api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"x-api-key": self._api_key}
        return {}

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return up to ``max_results`` papers for ``query``.

        Wraps the outbound request in retry + exponential backoff so a single
        HTTP 429 or transient connection error does not zero out the provider.
        Retries are limited to rate-limit/connection failures; a clean empty
        result set is returned immediately without retrying.

        Raises ``requests.HTTPError`` (or the last transient error) once retries
        are exhausted, so the caller's try/except can mark the provider failed.
        """
        params = {
            "query": query,
            "limit": self.max_results,
            "fields": _DEFAULT_FIELDS,
        }

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                resp = requests.get(
                    _API_URL,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
            except _RETRYABLE_EXC as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    self._backoff(attempt, f"connection error: {exc}")
                    continue
                raise

            if resp.status_code == 429 and attempt < _MAX_ATTEMPTS:
                self._backoff(attempt, "HTTP 429 (rate limited)")
                continue

            resp.raise_for_status()
            body = orjson.loads(resp.content)
            return body.get("data", []) or []

        # Exhausted retries on a persistent 429: surface a real HTTPError.
        if last_exc is not None:
            raise last_exc
        resp.raise_for_status()
        return []

    @staticmethod
    def _backoff(attempt: int, reason: str) -> None:
        """Sleep with exponential backoff before the next attempt."""
        delay = _BASE_DELAY * (2 ** (attempt - 1))
        logger.warning(
            "Semantic Scholar %s; retry %d/%d after %.1fs",
            reason,
            attempt + 1,
            _MAX_ATTEMPTS,
            delay,
        )
        time.sleep(delay)


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Semantic Scholar paper record into a uniform dict.

    Semantic Scholar nests authors as ``[{"authorId": ..., "name": ...}]``
    and DOIs under ``externalIds``. Flatten for prompt-friendliness.
    """
    authors_raw = raw.get("authors") or []
    authors = ", ".join(a.get("name", "") for a in authors_raw if a.get("name"))
    external = raw.get("externalIds") or {}
    doi = external.get("DOI", "")
    return {
        "title": raw.get("title", "Unknown"),
        "authors": authors or "Unknown",
        "year": raw.get("year") or "N/A",
        "abstract": (raw.get("abstract") or "")[:500],
        "doi": doi,
        "url": raw.get("url", ""),
        "citation_count": raw.get("citationCount", 0),
        "venue": raw.get("venue", ""),
    }


def search_semantic_scholar_for_topic(
    topic: str,
    max_papers: int = 5,
) -> dict[str, Any]:
    """Run a Semantic Scholar query and return a uniform research dict.

    Mirrors the shape of ``search_arxiv_for_topic`` and
    ``search_google_for_topic`` so callers can iterate providers uniformly.

    Args:
        topic: Search query, typically a noun-phrase.
        max_papers: Cap on returned papers (default 5).

    Returns:
        ``{"success", "topic", "papers_found", "papers", "error"}``.

    """
    try:
        searcher = SemanticScholarSearcher(max_results=max_papers)
        raw_papers = searcher.search(topic)
        papers = [_normalise(p) for p in raw_papers]
        return {
            "success": True,
            "topic": topic,
            "papers_found": len(papers),
            "papers": papers,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Semantic Scholar search failed for '%s': %s", topic, exc)
        return {
            "success": False,
            "topic": topic,
            "papers_found": 0,
            "papers": [],
            "error": str(exc),
        }


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)
    query = sys.argv[1] if len(sys.argv) > 1 else "AI testing tools"
    result = search_semantic_scholar_for_topic(query, max_papers=3)
    print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode())
