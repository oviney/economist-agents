#!/usr/bin/env python3
"""GA4 ETL: Fetch article performance metrics and compute engagement scores.

Queries the GA4 Data API for page-level metrics, computes a composite
engagement score per ADR-002, and stores results in SQLite.

Usage:
    python scripts/ga4_etl.py --days 30

Environment variables (loaded from .env):
    GOOGLE_APPLICATION_CREDENTIALS — path to service account JSON
    GA4_PROPERTY_ID              — numeric GA4 property ID
"""

from __future__ import annotations

import argparse
import logging
import os
import pathlib
import sqlite3
from datetime import UTC, datetime
from typing import Any

import orjson
from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunReportResponse,
)
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "performance.db"

GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

COMPOSITE_WEIGHTS: dict[str, float] = {
    "pageviews": 0.25,
    "engagement_rate": 0.20,
    "avg_engagement_time": 0.15,
    "scroll_depth_rate": 0.10,
    "search_ctr": 0.15,  # placeholder until GSC wired
    "search_impressions": 0.15,  # placeholder until GSC wired
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_performance (
    page_path           TEXT,
    page_title          TEXT,
    pageviews           INTEGER,
    engagement_rate     REAL,
    avg_engagement_time REAL,
    scroll_depth_rate   REAL,
    composite_score     REAL,
    fetched_at          TEXT
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize(values: list[float]) -> list[float]:
    """Min-max normalize a list of floats to [0, 1].

    Returns a list of zeros when all values are identical or the list is empty.
    """
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    span = max_val - min_val
    if span == 0.0:
        return [0.0] * len(values)
    return [(v - min_val) / span for v in values]


def build_ga4_client(credentials_path: str | None = None) -> BetaAnalyticsDataClient:
    """Create an authenticated BetaAnalyticsDataClient.

    Args:
        credentials_path: Explicit path to the service-account JSON.
            Falls back to ``GOOGLE_APPLICATION_CREDENTIALS`` env var.

    Returns:
        An authenticated GA4 Data API client.
    """
    creds_file = credentials_path or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )
    if not creds_file:
        raise OSError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set and no credentials_path provided"
        )
    credentials = Credentials.from_service_account_file(creds_file, scopes=GA4_SCOPES)
    return BetaAnalyticsDataClient(credentials=credentials)


def fetch_ga4_report(
    client: BetaAnalyticsDataClient,
    property_id: str,
    days: int,
) -> RunReportResponse:
    """Run a GA4 report for article performance metrics.

    Args:
        client: Authenticated GA4 client.
        property_id: Numeric GA4 property ID.
        days: Number of days to look back.

    Returns:
        The raw ``RunReportResponse`` from the GA4 Data API.
    """
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[
            Dimension(name="pagePath"),
            Dimension(name="pageTitle"),
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="scrolledUsers"),
        ],
    )
    logger.info("Fetching GA4 report for property %s (last %d days)", property_id, days)
    return client.run_report(request)


def parse_rows(response: RunReportResponse) -> list[dict[str, Any]]:
    """Parse a GA4 RunReportResponse into a list of row dicts.

    Args:
        response: The GA4 API response.

    Returns:
        A list of dicts with keys: page_path, page_title, date,
        pageviews, engagement_rate, avg_engagement_time, scroll_depth_rate.
    """
    rows: list[dict[str, Any]] = []
    if not response.rows:
        logger.warning("GA4 returned no data rows")
        return rows

    for row in response.rows:
        dims = row.dimension_values
        mets = row.metric_values
        pageviews = int(mets[0].value)
        # scrolledUsers / screenPageViews as scroll-depth proxy
        scroll_depth_rate = float(mets[3].value) / pageviews if pageviews > 0 else 0.0
        rows.append(
            {
                "page_path": dims[0].value,
                "page_title": dims[1].value,
                "date": dims[2].value,
                "pageviews": pageviews,
                "engagement_rate": float(mets[1].value),
                "avg_engagement_time": float(mets[2].value),
                "scroll_depth_rate": scroll_depth_rate,
            }
        )
    logger.info("Parsed %d rows from GA4 response", len(rows))
    return rows


def compute_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute composite engagement scores for each row.

    The composite score is a weighted sum of min-max-normalised metrics
    per ADR-002.  GSC-based metrics (search_ctr, search_impressions)
    default to 0.0 until GSC integration is wired.

    Args:
        rows: Parsed GA4 rows.

    Returns:
        The same rows, each augmented with a ``composite_score`` key.
    """
    if not rows:
        return rows

    norm_pageviews = normalize([r["pageviews"] for r in rows])
    norm_engagement = normalize([r["engagement_rate"] for r in rows])
    norm_time = normalize([r["avg_engagement_time"] for r in rows])
    norm_scroll = normalize([r["scroll_depth_rate"] for r in rows])

    for i, row in enumerate(rows):
        score = (
            COMPOSITE_WEIGHTS["pageviews"] * norm_pageviews[i]
            + COMPOSITE_WEIGHTS["engagement_rate"] * norm_engagement[i]
            + COMPOSITE_WEIGHTS["avg_engagement_time"] * norm_time[i]
            + COMPOSITE_WEIGHTS["scroll_depth_rate"] * norm_scroll[i]
            + COMPOSITE_WEIGHTS["search_ctr"] * 0.0  # placeholder
            + COMPOSITE_WEIGHTS["search_impressions"] * 0.0  # placeholder
        )
        row["composite_score"] = round(score, 6)

    return rows


def store_results(
    rows: list[dict[str, Any]],
    db_path: pathlib.Path | str = DB_PATH,
) -> int:
    """Write scored rows into SQLite ``article_performance`` table.

    Args:
        rows: Scored row dicts from :func:`compute_scores`.
        db_path: Path to the SQLite database file.

    Returns:
        Number of rows inserted.
    """
    db_path = pathlib.Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(CREATE_TABLE_SQL)
        inserted = 0
        for row in rows:
            conn.execute(
                """
                INSERT INTO article_performance
                    (page_path, page_title, pageviews, engagement_rate,
                     avg_engagement_time, scroll_depth_rate, composite_score, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["page_path"],
                    row["page_title"],
                    row["pageviews"],
                    row["engagement_rate"],
                    row["avg_engagement_time"],
                    row["scroll_depth_rate"],
                    row["composite_score"],
                    fetched_at,
                ),
            )
            inserted += 1
        conn.commit()
        logger.info("Inserted %d rows into %s", inserted, db_path)
    finally:
        conn.close()

    return inserted


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Fetch GA4 article metrics and compute engagement scores.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help="SQLite database path (default: data/performance.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score but do not write to the database",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry-point for the GA4 ETL pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    property_id = os.environ.get("GA4_PROPERTY_ID", "")
    if not property_id:
        logger.error("GA4_PROPERTY_ID environment variable is not set")
        raise SystemExit(1)

    client = build_ga4_client()
    response = fetch_ga4_report(client, property_id, args.days)
    rows = parse_rows(response)

    if not rows:
        logger.warning("No data returned from GA4 — nothing to store")
        return

    scored = compute_scores(rows)

    if args.dry_run:
        logger.info("Dry-run mode — dumping scored rows to stdout")
        for row in scored:
            logger.info(orjson.dumps(row).decode())
        return

    count = store_results(scored, db_path=args.db)
    logger.info("ETL complete: %d rows written to %s", count, args.db)


if __name__ == "__main__":
    main()
