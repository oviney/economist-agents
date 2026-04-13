#!/usr/bin/env python3
"""Content Intelligence query module.

Reads performance data from data/performance.db (written by ga4_etl.py
and gsc_etl.py) and produces structured summaries that the Topic Scout
agent uses to select future topics.

This module closes the feedback loop described in ADR-0007: published
article performance metrics flow back into topic selection, so the
pipeline learns from what's working.

The SQLite schema has one row per (page_path, page_title, date) from
the ETL. Callers almost always want aggregates per URL, so every
query in this module aggregates by page_path using SUM(pageviews)
and AVG(scores).

Example:
    from content_intelligence import get_performance_context
    context = get_performance_context(days=30)
    print(context)  # Markdown block ready to inject into an LLM prompt
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "performance.db"

# URLs that aren't real articles — excluded from performer rankings.
# These are index pages, archives, and category listings that always
# dominate pageview counts but aren't editorial content.
NON_ARTICLE_PATHS: frozenset[str] = frozenset(
    [
        "/",
        "/about/",
        "/blog/",
        "/software-engineering/",
        "/quality-engineering/",
        "/contact/",
        "/tags/",
        "/categories/",
    ]
)


@dataclass(frozen=True)
class ArticlePerformance:
    """Aggregated performance for a single article URL."""

    page_path: str
    page_title: str
    total_pageviews: int
    avg_engagement_rate: float
    avg_engagement_time: float
    avg_scroll_depth: float
    avg_composite_score: float


@dataclass(frozen=True)
class TrafficSummary:
    """High-level traffic summary for a time window."""

    article_count: int
    total_pageviews: int
    avg_pageviews_per_article: float
    avg_composite_score: float


def _connect(db_path: Path) -> sqlite3.Connection | None:
    """Open the performance database, returning None if it does not exist."""
    if not db_path.exists():
        logger.warning(
            "Performance database not found at %s. "
            "Run scripts/ga4_etl.py to populate it.",
            db_path,
        )
        return None
    return sqlite3.connect(db_path)


def _is_article(page_path: str) -> bool:
    """Return True if the path looks like an editorial article, not an index."""
    if page_path in NON_ARTICLE_PATHS:
        return False
    # Real articles have dated slugs like /YYYY/MM/DD/slug/
    return any(ch.isdigit() for ch in page_path)


def get_top_performers(
    limit: int = 5,
    min_pageviews: int = 5,
    db_path: Path | None = None,
) -> list[ArticlePerformance]:
    """Return the best-scoring articles by composite engagement score.

    Aggregates by page_path so the same URL doesn't appear multiple
    times (the ETL stores one row per date).

    Args:
        limit: Maximum number of articles to return.
        min_pageviews: Exclude articles with fewer total pageviews than
            this threshold to avoid statistical noise.
        db_path: Override the default database path.

    Returns:
        List of ArticlePerformance, sorted descending by composite score.
        Empty list if the database does not exist.
    """
    conn = _connect(db_path or DEFAULT_DB_PATH)
    if conn is None:
        return []

    try:
        cursor = conn.execute(
            """
            SELECT
                page_path,
                MAX(page_title) AS page_title,
                SUM(pageviews) AS total_pageviews,
                AVG(engagement_rate) AS avg_engagement_rate,
                AVG(avg_engagement_time) AS avg_engagement_time,
                AVG(scroll_depth_rate) AS avg_scroll_depth,
                AVG(composite_score) AS avg_composite_score
            FROM article_performance
            GROUP BY page_path
            HAVING total_pageviews >= ?
            ORDER BY avg_composite_score DESC
            """,
            (min_pageviews,),
        )
        rows = [
            ArticlePerformance(
                page_path=row[0],
                page_title=row[1] or "",
                total_pageviews=int(row[2]),
                avg_engagement_rate=float(row[3]),
                avg_engagement_time=float(row[4]),
                avg_scroll_depth=float(row[5]),
                avg_composite_score=float(row[6]),
            )
            for row in cursor
            if _is_article(row[0])
        ]
    finally:
        conn.close()

    return rows[:limit]


def get_bottom_performers(
    limit: int = 5,
    min_pageviews: int = 20,
    db_path: Path | None = None,
) -> list[ArticlePerformance]:
    """Return underperforming articles worth learning from.

    Requires higher minimum pageviews than get_top_performers because
    low-pageview articles are usually noise, not signal. We want
    articles that got real traffic but failed to engage readers.

    Args:
        limit: Maximum number of articles to return.
        min_pageviews: Minimum pageviews to qualify as "real traffic
            that didn't convert".
        db_path: Override the default database path.

    Returns:
        List of ArticlePerformance, sorted ascending by composite score.
    """
    conn = _connect(db_path or DEFAULT_DB_PATH)
    if conn is None:
        return []

    try:
        cursor = conn.execute(
            """
            SELECT
                page_path,
                MAX(page_title) AS page_title,
                SUM(pageviews) AS total_pageviews,
                AVG(engagement_rate) AS avg_engagement_rate,
                AVG(avg_engagement_time) AS avg_engagement_time,
                AVG(scroll_depth_rate) AS avg_scroll_depth,
                AVG(composite_score) AS avg_composite_score
            FROM article_performance
            GROUP BY page_path
            HAVING total_pageviews >= ?
            ORDER BY avg_composite_score ASC
            """,
            (min_pageviews,),
        )
        rows = [
            ArticlePerformance(
                page_path=row[0],
                page_title=row[1] or "",
                total_pageviews=int(row[2]),
                avg_engagement_rate=float(row[3]),
                avg_engagement_time=float(row[4]),
                avg_scroll_depth=float(row[5]),
                avg_composite_score=float(row[6]),
            )
            for row in cursor
            if _is_article(row[0])
        ]
    finally:
        conn.close()

    return rows[:limit]


def get_traffic_summary(db_path: Path | None = None) -> TrafficSummary | None:
    """Return a high-level summary of recent traffic.

    Returns None if the database does not exist or has no rows.
    """
    conn = _connect(db_path or DEFAULT_DB_PATH)
    if conn is None:
        return None

    try:
        cursor = conn.execute(
            """
            SELECT
                COUNT(DISTINCT page_path) AS article_count,
                SUM(pageviews) AS total_pageviews,
                AVG(composite_score) AS avg_composite_score
            FROM article_performance
            """
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None or row[0] == 0:
        return None

    article_count = int(row[0])
    total_pageviews = int(row[1] or 0)
    avg_composite_score = float(row[2] or 0.0)
    avg_pageviews_per_article = (
        total_pageviews / article_count if article_count > 0 else 0.0
    )

    return TrafficSummary(
        article_count=article_count,
        total_pageviews=total_pageviews,
        avg_pageviews_per_article=avg_pageviews_per_article,
        avg_composite_score=avg_composite_score,
    )


def get_performance_context(
    top_limit: int = 5,
    bottom_limit: int = 5,
    db_path: Path | None = None,
) -> str:
    """Build a Markdown block describing recent article performance.

    This is the primary integration point for Topic Scout: the returned
    string is ready to paste into an LLM prompt as a "Performance
    Context" section. If no performance data is available, returns a
    short notice so the caller can proceed without the context.

    Args:
        top_limit: Number of top performers to include.
        bottom_limit: Number of bottom performers to include.
        db_path: Override the default database path.

    Returns:
        A Markdown string ready for prompt injection.
    """
    summary = get_traffic_summary(db_path=db_path)
    if summary is None:
        logger.info("No performance data available — returning empty context.")
        return (
            "## Performance Context\n\n"
            "_No performance data available yet. Run `scripts/ga4_etl.py` "
            "to populate `data/performance.db`._\n"
        )

    top = get_top_performers(limit=top_limit, db_path=db_path)
    bottom = get_bottom_performers(limit=bottom_limit, db_path=db_path)

    lines: list[str] = ["## Performance Context", ""]
    lines.append(
        f"Over the last 30 days, the blog served **{summary.total_pageviews:,} "
        f"pageviews** across {summary.article_count} URLs "
        f"(avg composite score {summary.avg_composite_score:.3f}).",
    )
    lines.append("")

    if top:
        lines.append("### Top performers (build on what's working)")
        lines.append("")
        lines.append("| Score | Pageviews | Title |")
        lines.append("|-------|-----------|-------|")
        for a in top:
            title = (a.page_title or a.page_path)[:70]
            lines.append(
                f"| {a.avg_composite_score:.3f} | {a.total_pageviews:,} | {title} |"
            )
        lines.append("")

    if bottom:
        lines.append(
            "### Underperformers (traffic arrived but engagement was weak — topics to avoid or reframe)"
        )
        lines.append("")
        lines.append("| Score | Pageviews | Title |")
        lines.append("|-------|-----------|-------|")
        for a in bottom:
            title = (a.page_title or a.page_path)[:70]
            lines.append(
                f"| {a.avg_composite_score:.3f} | {a.total_pageviews:,} | {title} |"
            )
        lines.append("")

    lines.append(
        "**Use this to inform topic selection:** favour themes similar "
        "to the top performers, and avoid or reframe angles that resemble "
        "the underperformers."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point: print the performance context to stdout."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the performance database",
    )
    parser.add_argument("--top", type=int, default=5, help="Number of top performers")
    parser.add_argument(
        "--bottom", type=int, default=5, help="Number of bottom performers"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(
        get_performance_context(
            top_limit=args.top,
            bottom_limit=args.bottom,
            db_path=args.db,
        )
    )


if __name__ == "__main__":
    main()
