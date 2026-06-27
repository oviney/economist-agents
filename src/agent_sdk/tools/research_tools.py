"""Writer-callable research tools for the Stage 3 hybrid-research flow (#389).

The deterministic pre-research (``build_research_brief``) remains the primary,
pre-vetted seed. This module adds a ``search_for_source`` tool the writer can
call sparingly mid-draft to fetch additional sources for specific claims it
wants to support.

Design (see docs/specs/389-hybrid-research.md):
- Per-article ``SourceFetchSession`` enforces a hard call budget and dedupes
  identical queries within one run (no cross-article persistence).
- Backed by the existing provider stack (Brave-first for latency, Google web
  fallback) via ``scripts/*_search.py`` — no new providers.
- Fetched sources are accumulated so ``run_stage3`` can append them to the
  research brief *before* the stat audit, so writer-cited stats are not
  stripped as unsupported.
"""

from __future__ import annotations

import logging
from typing import Any

import orjson
from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

# Hard cap on writer search calls per article (resolved design question #1).
DEFAULT_SEARCH_CALL_BUDGET = 3

Source = dict[str, str]


def _run_provider_search(query: str, max_results: int) -> list[Source]:
    """Fetch sources for ``query`` via the free academic provider stack.

    arXiv first, Semantic Scholar as fallback when arXiv returns nothing. Both
    are keyless and no-cost — the pay-per-use providers (Brave, Google/Serper)
    were removed. Never raises — returns a possibly-empty list of
    ``{"title", "url", "snippet"}`` dicts.
    """
    try:
        from scripts.arxiv_search import search_arxiv_for_topic

        arxiv = search_arxiv_for_topic(query, max_papers=max_results)
        papers = arxiv.get("insights", {}).get("papers_analyzed", [])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("arXiv search failed for '%s': %s", query, exc)
        papers = []

    sources = [
        {
            "title": p.get("title", ""),
            "url": p.get("url", ""),
            "snippet": p.get("key_insight", ""),
        }
        for p in papers
    ]
    if sources:
        return sources[:max_results]

    # Fallback: Semantic Scholar (keyless). Returns a dict with a ``papers``
    # list, each carrying title / url / abstract.
    try:
        from scripts.semantic_scholar_search import search_semantic_scholar_for_topic

        ss = search_semantic_scholar_for_topic(query, max_papers=max_results)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Semantic Scholar fallback failed for '%s': %s", query, exc)
        return []

    return [
        {
            "title": p.get("title", ""),
            "url": p.get("url", ""),
            "snippet": p.get("abstract", ""),
        }
        for p in ss.get("papers", [])
        if isinstance(p, dict)
    ][:max_results]


class SourceFetchSession:
    """Per-article budget, dedupe cache, and accumulator for writer searches."""

    def __init__(self, max_calls: int = DEFAULT_SEARCH_CALL_BUDGET) -> None:
        self.max_calls = max_calls
        self.calls_made = 0
        self.fetched: list[Source] = []
        self._cache: dict[str, list[Source]] = {}

    def search(self, query: str, max_results: int = 3) -> list[Source]:
        """Return sources for ``query``, honouring the dedupe cache and budget.

        Returns an empty list (never raises) when the budget is exhausted or the
        provider fails, so the writer turn always survives.
        """
        key = query.strip().lower()
        if key in self._cache:
            return self._cache[key]

        if self.calls_made >= self.max_calls:
            logger.info(
                "search_for_source budget (%d) exhausted; refusing query %r",
                self.max_calls,
                query,
            )
            return []

        self.calls_made += 1
        try:
            results = _run_provider_search(query, max_results)
        except Exception as exc:  # provider must never break the writer
            logger.warning("search_for_source provider error for %r: %s", query, exc)
            results = []

        self._cache[key] = results
        for source in results:
            if source not in self.fetched:
                self.fetched.append(source)
        return results

    def brief_supplement(self) -> str:
        """Return a markdown block of fetched sources to append to the research
        brief before the stat audit, or ``""`` if nothing was fetched."""
        if not self.fetched:
            return ""
        lines = ["\n\n## Writer-fetched sources (supporting)\n"]
        for source in self.fetched:
            lines.append(f"- {source['title']}: {source['snippet']} ({source['url']})")
        return "\n".join(lines)


def build_search_tool(session: SourceFetchSession) -> Any:
    """Build the ``search_for_source`` SDK tool bound to ``session``.

    A fresh session (and therefore a fresh tool) is created per article so the
    budget and dedupe cache do not leak across runs.
    """

    @tool(
        "search_for_source",
        (
            "Find sources for a specific claim. Returns title/url/snippet for "
            "each result. Use this only when you are about to make a claim that "
            "is not supported by the research brief. Call sparingly (at most 3 "
            "per article) — prefer claims from the brief when possible."
        ),
        {"query": str, "max_results": int},
    )
    async def search_for_source(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"content": [{"type": "text", "text": "[]"}]}
        # The model may emit a non-numeric max_results (e.g. "three"); never let
        # a bad arg raise out of the tool handler and break the writer turn.
        try:
            max_results = int(args.get("max_results", 3) or 3)
        except (TypeError, ValueError):
            max_results = 3
        results = session.search(query, max_results)
        return {
            "content": [{"type": "text", "text": orjson.dumps(results).decode("utf-8")}]
        }

    return search_for_source
