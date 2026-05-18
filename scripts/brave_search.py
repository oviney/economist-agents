#!/usr/bin/env python3
"""Brave Search API integration.

Wraps `api.search.brave.com/res/v1/web/search`. Free tier is 2,000
queries/month; requires a ``BRAVE_API_KEY`` env var (sign up at
brave.com/search/api). When the key is absent the provider returns
``success=False`` so the multi-provider fallback can skip it cleanly.

Public surface
--------------
BraveSearcher                — class
search_brave_for_topic(topic, max_results=5) -> dict
    Returns::

        {
            "success": bool,
            "topic": str,
            "results_found": int,
            "results": list[dict],   # title, url, snippet, age
            "error": str | None,
        }
"""

from __future__ import annotations

import logging
import os
from typing import Any

import orjson
import requests

logger = logging.getLogger(__name__)

_API_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_TIMEOUT = 10


class BraveSearcher:
    """Thin wrapper around the Brave Search web endpoint."""

    def __init__(self, max_results: int = 5, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self.max_results = max_results
        self.timeout = timeout
        self._api_key = os.environ.get("BRAVE_API_KEY")

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        # X-Subscription-Token is the auth header per Brave's docs.
        # Accept: application/json keeps responses JSON-shaped even when
        # the upstream defaults change.
        return {
            "X-Subscription-Token": self._api_key or "",
            "Accept": "application/json",
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return up to ``max_results`` web results for ``query``.

        Raises ``RuntimeError`` when no key is configured (caller maps
        this to ``success=False`` rather than letting it propagate).
        Raises ``requests.HTTPError`` on transport-level failures.
        """
        if not self.has_credentials:
            raise RuntimeError("BRAVE_API_KEY is not set")
        params = {"q": query, "count": self.max_results}
        resp = requests.get(
            _API_URL,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = orjson.loads(resp.content)
        web = body.get("web") or {}
        return web.get("results", []) or []


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Brave web result into a uniform dict."""
    return {
        "title": raw.get("title", "Unknown"),
        "url": raw.get("url", ""),
        "snippet": raw.get("description", ""),
        # Brave returns `age` like "3 days ago" — preserve as-is; the
        # writer prompt can quote it directly for currency context.
        "age": raw.get("age", ""),
    }


def search_brave_for_topic(topic: str, max_results: int = 5) -> dict[str, Any]:
    """Run a Brave Search query and return a uniform research dict.

    Mirrors ``search_arxiv_for_topic`` / ``search_semantic_scholar_for_topic``
    so callers can iterate providers uniformly.

    Args:
        topic: Search query.
        max_results: Cap on returned results (default 5).

    Returns:
        ``{"success", "topic", "results_found", "results", "error"}``.

    """
    try:
        searcher = BraveSearcher(max_results=max_results)
        raw = searcher.search(topic)
        results = [_normalise(r) for r in raw]
        return {
            "success": True,
            "topic": topic,
            "results_found": len(results),
            "results": results,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Brave search failed for '%s': %s", topic, exc)
        return {
            "success": False,
            "topic": topic,
            "results_found": 0,
            "results": [],
            "error": str(exc),
        }


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)
    query = sys.argv[1] if len(sys.argv) > 1 else "AI testing tools"
    result = search_brave_for_topic(query, max_results=3)
    print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode())
