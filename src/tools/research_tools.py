#!/usr/bin/env python3
"""CrewAI tool wrappers for web search — arXiv and Google Scholar.

Wraps existing scripts/arxiv_search.py and scripts/google_search.py as
CrewAI BaseTool instances so the Research Agent can search the web for
real, citable sources instead of hallucinating from training data.

Usage:
    from src.tools.research_tools import get_research_tools

    agent = Agent(
        role="Research Analyst",
        tools=get_research_tools(),
        ...
    )
"""

import logging
import os
import sys
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Allow imports from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

logger = logging.getLogger(__name__)


class ArxivSearchInput(BaseModel):
    """Input schema for arXiv search tool."""

    topic: str = Field(description="Research topic to search for on arXiv")
    max_papers: int = Field(
        default=5, description="Maximum number of papers to return"
    )


class ArxivSearchTool(BaseTool):
    """Search arXiv for recent academic papers on a topic.

    Returns paper titles, authors, abstracts, URLs, and publication dates.
    Papers are filtered to the last 60 days for freshness.
    """

    name: str = "search_arxiv"
    description: str = (
        "Search arXiv for recent academic papers. Returns titles, authors, "
        "abstracts, and URLs. Use this to find real, citable academic sources. "
        "ALWAYS use this tool before citing any academic paper."
    )
    args_schema: type[BaseModel] = ArxivSearchInput

    def _run(self, topic: str, max_papers: int = 5) -> str:
        """Execute arXiv search."""
        try:
            from arxiv_search import search_arxiv_for_topic

            result = search_arxiv_for_topic(topic, max_papers=max_papers)
            if not result.get("success"):
                return f"arXiv search failed: {result.get('error', 'unknown')}"

            insights = result.get("insights", {})
            papers = insights.get("papers_analyzed", [])
            if not papers:
                return f"No arXiv papers found for '{topic}'"

            output = [f"Found {len(papers)} arXiv papers on '{topic}':\n"]
            for p in papers[:max_papers]:
                output.append(
                    f"- Title: {p.get('title', 'Unknown')}\n"
                    f"  Authors: {p.get('authors', 'Unknown')}\n"
                    f"  URL: {p.get('url', 'N/A')}\n"
                    f"  Published: {p.get('published', 'N/A')}\n"
                    f"  Key finding: {p.get('key_insight', 'N/A')}\n"
                )
            return "\n".join(output)

        except ImportError:
            return "arXiv search unavailable (arxiv package not installed)"
        except Exception as e:
            logger.exception("arXiv search failed")
            return f"arXiv search error: {e}"


class GoogleSearchInput(BaseModel):
    """Input schema for Google search tool."""

    topic: str = Field(
        description="Research topic to search for on Google and Google Scholar"
    )
    max_results: int = Field(
        default=5, description="Maximum number of results per source"
    )


class GoogleSearchTool(BaseTool):
    """Search Google Web and Google Scholar for recent sources.

    Returns web results and academic papers with titles, URLs, snippets,
    and publication dates. Queries are automatically scoped to current
    and previous year for freshness.
    """

    name: str = "search_google"
    description: str = (
        "Search Google Web and Google Scholar for recent sources on a topic. "
        "Returns titles, URLs, snippets, and dates. Requires SERPER_API_KEY. "
        "ALWAYS use this tool before citing any industry report, company blog, "
        "or practitioner content."
    )
    args_schema: type[BaseModel] = GoogleSearchInput

    def _run(self, topic: str, max_results: int = 5) -> str:
        """Execute Google search."""
        if not os.environ.get("SERPER_API_KEY"):
            return (
                "Google search unavailable (SERPER_API_KEY not set). "
                "Use search_arxiv for academic sources instead."
            )

        try:
            from google_search import search_google_for_topic

            result = search_google_for_topic(
                topic, max_results=max_results, include_scholar=True
            )
            if not result.get("success"):
                return f"Google search failed: {result.get('error', 'unknown')}"

            output = [f"Google search results for '{topic}':\n"]

            web = result.get("web_results", [])
            if web:
                output.append("## Web Results")
                for r in web[:max_results]:
                    output.append(
                        f"- {r.get('title', 'Unknown')}\n"
                        f"  URL: {r.get('link', 'N/A')}\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}\n"
                        f"  Date: {r.get('date', 'N/A')}\n"
                    )

            scholar = result.get("scholar_results", [])
            if scholar:
                output.append("\n## Scholar Results")
                for r in scholar[:max_results]:
                    output.append(
                        f"- {r.get('title', 'Unknown')}\n"
                        f"  URL: {r.get('link', 'N/A')}\n"
                        f"  Snippet: {r.get('snippet', 'N/A')}\n"
                        f"  Year: {r.get('year', 'N/A')}\n"
                        f"  Cited by: {r.get('cited_by', 'N/A')}\n"
                    )

            return "\n".join(output)

        except ImportError:
            return "Google search unavailable (google_search module not found)"
        except Exception as e:
            logger.exception("Google search failed")
            return f"Google search error: {e}"


def get_research_tools() -> list[BaseTool]:
    """Return list of research tools for the Research Agent.

    Returns:
        List containing ArxivSearchTool and GoogleSearchTool instances.
    """
    return [ArxivSearchTool(), GoogleSearchTool()]
