#!/usr/bin/env python3
"""arXiv Search Integration Module

Provides real-time access to cutting-edge research papers from arXiv.org
to enhance article research with fresh, authoritative academic sources.

Business Value:
- Access to pre-publication research (6-12 months ahead of journals)
- Fresh 2026 sources instead of stale 2023-2024 training data
- Competitive advantage with cutting-edge insights
- Enhanced credibility through recent academic citations
"""

from __future__ import annotations

import contextlib
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

try:
    import arxiv
except ImportError:
    arxiv = None  # type: ignore[assignment]

with contextlib.suppress(ImportError):
    pass
if "json" not in locals():
    pass

logger = logging.getLogger(__name__)

# Retry policy for transient failures (HTTP 429 / connection errors).
# arXiv throttles bursts; a single 429 must not zero out the provider.
# Exponential backoff: 1.5s, 3.0s between three total attempts.
_MAX_ATTEMPTS = 3
_BASE_DELAY = 1.5


class ArxivSearchError(Exception):
    """Custom exception for arXiv search errors."""


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient errors worth retrying.

    Retryable: HTTP 429 (rate limit), arXiv's ``UnexpectedEmptyPageError``
    (a flaky empty page mid-stream), and connection-level errors whose type
    or message indicates a transient transport failure. Everything else —
    including clean empty results — is not retried.
    """
    if arxiv is not None:
        if isinstance(exc, arxiv.HTTPError):
            return getattr(exc, "status", None) == 429
        if isinstance(exc, arxiv.UnexpectedEmptyPageError):
            return True
    # Connection-level failures surface via requests under the hood or as
    # generic ConnectionError/TimeoutError. Match by type or message.
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    transient_markers = ("connection", "timed out", "timeout", "temporarily")
    return any(marker in str(exc).lower() for marker in transient_markers)


class ArxivSearcher:
    """Enhanced research capability with arXiv integration.

    Searches arXiv.org for recent academic papers to provide cutting-edge
    research insights instead of relying on stale LLM training data.

    Features:
    - Recent paper discovery (configurable date range)
    - Relevance scoring and ranking
    - Abstract analysis for key insights
    - Proper academic citation formatting
    - Business-relevant paper filtering

    Usage:
        searcher = ArxivSearcher()
        papers = searcher.search_recent_papers("artificial intelligence automation")
        insights = searcher.extract_business_insights(papers)
    """

    def __init__(self, max_results: int = 10, days_back: int = 30):
        """Initialize arXiv searcher with configuration.

        Args:
            max_results: Maximum papers to return per search
            days_back: How many days back to search for recent papers

        """
        if arxiv is None:
            raise ArxivSearchError(
                "arxiv package not installed. Run: pip install arxiv>=2.1.0",
            )

        self.max_results = max_results
        self.days_back = days_back
        self.cutoff_date = datetime.now() - timedelta(days=days_back)

        logger.info(
            f"ArxivSearcher initialized: max_results={max_results}, "
            f"searching papers from {self.cutoff_date.strftime('%Y-%m-%d')}",
        )

    def search_recent_papers(
        self,
        query: str,
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search arXiv for recent papers matching the query.

        Args:
            query: Search terms (e.g., "artificial intelligence automation")
            categories: Optional arXiv categories to filter by
                       (e.g., ["cs.AI", "econ.EM", "q-fin"])

        Returns:
            List of paper dictionaries with metadata and relevance scores

        Example:
            papers = searcher.search_recent_papers(
                "quality metrics automation",
                categories=["cs.SE", "cs.AI"]
            )

        """
        if not query.strip():
            raise ArxivSearchError("Search query cannot be empty")

        logger.info(f"Searching arXiv for: '{query}' (last {self.days_back} days)")

        try:
            # Build search query with date filter
            search_query = self._build_search_query(query, categories)

            # Execute arXiv search
            client = arxiv.Client()
            search = arxiv.Search(
                query=search_query,
                max_results=self.max_results * 2,  # Get extra for filtering
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            # Fetch with retry/backoff so a single 429 or transient connection
            # error doesn't zero out the provider. A clean empty result is not
            # an error and is not retried.
            results = self._fetch_results(client, search)

            papers = []
            for result in results:
                # Filter by date
                if result.published.replace(tzinfo=None) < self.cutoff_date:
                    continue

                # Convert to our format
                paper = self._format_paper_result(result, query)
                papers.append(paper)

                # Stop when we have enough recent papers
                if len(papers) >= self.max_results:
                    break

            logger.info(f"Found {len(papers)} recent papers")
            return papers

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            raise ArxivSearchError(f"Search failed: {e}") from e

    def _fetch_results(
        self,
        client: arxiv.Client,
        search: arxiv.Search,
    ) -> list[arxiv.Result]:
        """Materialise arXiv search results with retry + exponential backoff.

        Retries only on transient failures — HTTP 429 (rate limit), arXiv's
        ``UnexpectedEmptyPageError``, and connection-level errors. A clean,
        successfully-fetched (possibly empty) result list is returned without
        retrying. After ``_MAX_ATTEMPTS`` the last error is re-raised for the
        caller to convert into an ``ArxivSearchError``.
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                # Materialise the generator here so transient page-fetch
                # errors surface inside the retry loop, not downstream.
                return list(client.results(search))
            except Exception as exc:  # noqa: BLE001 - classified below
                if not _is_retryable(exc) or attempt == _MAX_ATTEMPTS:
                    raise
                last_exc = exc
                delay = _BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "arXiv transient error (%s); retry %d/%d after %.1fs",
                    exc,
                    attempt + 1,
                    _MAX_ATTEMPTS,
                    delay,
                )
                time.sleep(delay)
        # Unreachable: loop either returns or raises. Guard for type-checkers.
        if last_exc is not None:  # pragma: no cover
            raise last_exc
        return []  # pragma: no cover

    def extract_business_insights(self, papers: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract business-relevant insights from arXiv papers.

        Args:
            papers: List of paper dictionaries from search_recent_papers()

        Returns:
            Dictionary with business insights, statistics, and citations

        """
        if not papers:
            return {
                "insights": [],
                "recent_findings": [],
                "citations": [],
                "papers_analyzed": [],
                "source_freshness": "No recent papers found",
            }

        insights = []
        citations = []
        recent_findings = []
        papers_analyzed = []

        for paper in papers[:5]:  # Focus on top 5 most relevant
            # Extract key insight from abstract
            insight = self._extract_key_insight(paper)
            if insight:
                insights.append(insight)

            # Format academic citation
            citation = self._format_citation(paper)
            citations.append(citation)

            # Render-ready record for downstream consumers (the research brief
            # fan-out reads ``insights.papers_analyzed`` — title/url/authors/
            # published/key_insight). Authors are joined to a string here so the
            # brief doesn't render a raw Python list.
            authors = paper.get("authors", [])
            papers_analyzed.append(
                {
                    "title": paper.get("title", ""),
                    "url": paper.get("url", ""),
                    "authors": ", ".join(authors)
                    if isinstance(authors, list)
                    else str(authors),
                    "published": paper.get("published", ""),
                    "abstract": paper.get("abstract", ""),
                    "key_insight": insight,
                },
            )

            # Highlight recent finding
            if paper["days_old"] <= 7:  # Published this week
                recent_findings.append(
                    {
                        "finding": insight,
                        "source": citation,
                        "days_old": paper["days_old"],
                    },
                )

        # Calculate source freshness
        avg_age = sum(p["days_old"] for p in papers) / len(papers)
        freshness_desc = self._describe_freshness(avg_age)

        return {
            "insights": insights,
            "recent_findings": recent_findings,
            "citations": citations,
            "papers_analyzed": papers_analyzed,
            "source_freshness": freshness_desc,
            "paper_count": len(papers),
            "average_age_days": round(avg_age, 1),
        }

    def _build_search_query(
        self,
        query: str,
        categories: list[str] | None = None,
    ) -> str:
        """Build optimized arXiv search query."""
        # Clean and optimize search terms
        terms = self._optimize_search_terms(query)

        # Add category filters if specified
        if categories:
            category_filter = " OR ".join(f"cat:{cat}" for cat in categories)
            return f"({terms}) AND ({category_filter})"

        return terms

    def _optimize_search_terms(self, query: str) -> str:
        """Optimize search terms for better arXiv results."""
        # Map business terms to academic equivalents
        term_mapping = {
            "quality metrics": "quality measurement OR quality assessment",
            "automation": "automation OR automated OR automatic",
            "AI": "artificial intelligence OR machine learning",
            "business": "enterprise OR organizational OR commercial",
            "ROI": "return on investment OR cost benefit OR economic impact",
            "efficiency": "efficiency OR performance OR productivity",
        }

        optimized = query.lower()
        for business_term, academic_terms in term_mapping.items():
            # Word-boundary match so short keys don't fire inside other words —
            # e.g. "AI" must not expand inside "drain"/"training", "ROI" not
            # inside "heroism" (BUG-049). Replacement is passed as a function so
            # the expansion text is treated literally (no backref surprises).
            pattern = rf"\b{re.escape(business_term.lower())}\b"
            optimized = re.sub(pattern, lambda _m: academic_terms, optimized)

        return optimized

    def _format_paper_result(
        self,
        result: arxiv.Result,
        original_query: str,
    ) -> dict[str, Any]:
        """Format arXiv result into our standard paper format."""
        # Calculate relevance score
        relevance = self._calculate_relevance(result, original_query)

        # Calculate paper age
        days_old = (datetime.now() - result.published.replace(tzinfo=None)).days

        return {
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "abstract": result.summary,
            "published": result.published.strftime("%Y-%m-%d"),
            "arxiv_id": result.entry_id.split("/")[-1],
            "url": result.entry_id,
            "categories": result.categories,
            "relevance_score": relevance,
            "days_old": days_old,
            "journal_ref": getattr(result, "journal_ref", None),
            "doi": getattr(result, "doi", None),
        }

    def _calculate_relevance(self, result: arxiv.Result, query: str) -> float:
        """Calculate relevance score for paper based on query match."""
        score = 0.0
        query_terms = query.lower().split()

        title_lower = result.title.lower()
        abstract_lower = result.summary.lower()

        # Title matches (weighted heavily)
        for term in query_terms:
            if term in title_lower:
                score += 2.0

        # Abstract matches
        for term in query_terms:
            if term in abstract_lower:
                score += 1.0

        # Recent papers get bonus
        days_old = (datetime.now() - result.published.replace(tzinfo=None)).days
        if days_old <= 7:
            score += 1.5  # This week bonus
        elif days_old <= 30:
            score += 0.5  # This month bonus

        # High-impact categories get bonus
        high_impact_categories = ["cs.AI", "cs.LG", "econ.EM", "q-fin", "stat.ML"]
        if any(cat in result.categories for cat in high_impact_categories):
            score += 0.5

        return round(score, 2)

    def _extract_key_insight(self, paper: dict[str, Any]) -> str:
        """Extract the key business insight from paper abstract."""
        abstract = paper["abstract"]

        # Look for quantitative findings
        numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", abstract)

        # Extract first sentence with findings
        sentences = abstract.split(".")
        for sentence in sentences:
            # Look for sentences with results/findings indicators
            if any(
                keyword in sentence.lower()
                for keyword in [
                    "show",
                    "find",
                    "result",
                    "demonstrate",
                    "evidence",
                    "improve",
                ]
            ) and any(num in sentence for num in numbers):
                return sentence.strip() + "."

        # Fallback to first sentence if no quantitative finding
        return sentences[0].strip() + "." if sentences else abstract[:200] + "..."

    def _format_citation(self, paper: dict[str, Any]) -> str:
        """Format paper citation in academic style."""
        authors = paper["authors"]
        author_str = f"{authors[0]} et al." if len(authors) > 3 else ", ".join(authors)

        # Format: "Author et al. (2026). Title. arXiv:ID"
        return (
            f"{author_str} ({paper['published'][:4]}). "
            f"{paper['title']}. arXiv:{paper['arxiv_id']}"
        )

    def _describe_freshness(self, avg_age_days: float) -> str:
        """Describe how fresh the research sources are."""
        if avg_age_days <= 7:
            return "Cutting-edge (papers from this week)"
        if avg_age_days <= 14:
            return "Very recent (papers from last two weeks)"
        if avg_age_days <= 30:
            return "Recent (papers from this month)"
        return f"Moderately recent (average {int(avg_age_days)} days old)"


def search_arxiv_for_topic(topic: str, max_papers: int = 5) -> dict[str, Any]:
    """Convenience function for quick arXiv research integration.

    Args:
        topic: Research topic (e.g., "quality automation metrics")
        max_papers: Maximum number of papers to analyze

    Returns:
        Dictionary with research insights and citations

    Example:
        research = search_arxiv_for_topic("AI automation business")
        print(f"Found insights from {research['paper_count']} recent papers")

    """
    try:
        searcher = ArxivSearcher(max_results=max_papers, days_back=60)
        papers = searcher.search_recent_papers(topic)
        insights = searcher.extract_business_insights(papers)

        return {
            "success": True,
            "topic": topic,
            "papers_found": len(papers),
            "insights": insights,
            "error": None,
        }

    except Exception as e:
        logger.error(f"arXiv search failed for topic '{topic}': {e}")
        return {
            "success": False,
            "topic": topic,
            "papers_found": 0,
            "insights": {},
            "error": str(e),
        }


if __name__ == "__main__":
    # Demo usage
    print("🔬 arXiv Research Integration Demo")
    print("=" * 50)

    # Test search
    topic = "artificial intelligence automation quality"
    result = search_arxiv_for_topic(topic, max_papers=3)

    if result["success"]:
        insights = result["insights"]
        print(f"📊 Found {result['papers_found']} papers on: {topic}")
        print(f"📅 Source freshness: {insights.get('source_freshness', 'N/A')}")
        print("\n🔍 Key Insights:")
        for i, insight in enumerate(insights.get("insights", [])[:3], 1):
            print(f"  {i}. {insight}")

        print("\n📚 Recent Citations:")
        for citation in insights.get("citations", [])[:3]:
            print(f"  • {citation}")

        if insights.get("recent_findings"):
            print("\n🆕 This Week's Findings:")
            for finding in insights["recent_findings"]:
                print(f"  • {finding['finding']} ({finding['days_old']} days ago)")
    else:
        print(f"❌ Search failed: {result['error']}")
