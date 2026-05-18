#!/usr/bin/env python3
"""Tavily AI-native search integration.

Wraps `api.tavily.com/search`. Tavily returns ranked + pre-summarized
results (and optionally a generated answer) which saves writer-side
tokens compared with raw snippet lists. Free tier is 1,000 queries/month;
requires a ``TAVILY_API_KEY`` env var (sign up at tavily.com).

Public surface
--------------
TavilySearcher                — class
search_tavily_for_topic(topic, max_results=5) -> dict
    Returns::

        {
            "success": bool,
            "topic": str,
            "results_found": int,
            "results": list[dict],   # title, url, snippet, score
            "answer": str,           # Tavily's generated summary, may be ""
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

_API_URL = "https://api.tavily.com/search"
_DEFAULT_TIMEOUT = 15  # Tavily summarises server-side, runs a bit slower


class TavilySearcher:
    """Thin wrapper around the Tavily search endpoint."""

    def __init__(
        self,
        max_results: int = 5,
        timeout: int = _DEFAULT_TIMEOUT,
        include_answer: bool = True,
    ) -> None:
        self.max_results = max_results
        self.timeout = timeout
        self.include_answer = include_answer
        self._api_key = os.environ.get("TAVILY_API_KEY")

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str) -> dict[str, Any]:
        """Return the raw Tavily response body for ``query``.

        Returns the parsed JSON so the caller can pull both ``results``
        and the optional ``answer`` field. Raises ``RuntimeError`` when
        no key is configured; ``requests.HTTPError`` on transport failure.
        """
        if not self.has_credentials:
            raise RuntimeError("TAVILY_API_KEY is not set")
        # Tavily uses POST with the key in the JSON body (not a header).
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": self.max_results,
            "include_answer": self.include_answer,
            "search_depth": "basic",
        }
        resp = requests.post(_API_URL, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return orjson.loads(resp.content)


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Tavily result item into a uniform dict."""
    return {
        "title": raw.get("title", "Unknown"),
        "url": raw.get("url", ""),
        "snippet": raw.get("content", ""),
        # Tavily ranks results; the score helps the writer pick the
        # strongest source to cite when multiple cover the same point.
        "score": raw.get("score", 0.0),
    }


def search_tavily_for_topic(topic: str, max_results: int = 5) -> dict[str, Any]:
    """Run a Tavily query and return a uniform research dict.

    Args:
        topic: Search query.
        max_results: Cap on returned results (default 5).

    Returns:
        ``{"success", "topic", "results_found", "results", "answer", "error"}``.

    """
    try:
        searcher = TavilySearcher(max_results=max_results)
        body = searcher.search(topic)
        raw_results = body.get("results", []) or []
        results = [_normalise(r) for r in raw_results]
        return {
            "success": True,
            "topic": topic,
            "results_found": len(results),
            "results": results,
            "answer": body.get("answer", "") or "",
            "error": None,
        }
    except Exception as exc:
        logger.warning("Tavily search failed for '%s': %s", topic, exc)
        return {
            "success": False,
            "topic": topic,
            "results_found": 0,
            "results": [],
            "answer": "",
            "error": str(exc),
        }


if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO)
    query = sys.argv[1] if len(sys.argv) > 1 else "AI testing tools"
    result = search_tavily_for_topic(query, max_results=3)
    print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode())
