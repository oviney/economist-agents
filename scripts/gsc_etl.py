#!/usr/bin/env python3
"""Google Search Console ETL — Keyword & Search Performance (Issue #163).

Queries the GSC Search Analytics API for keyword and search performance data,
identifies content gaps, and stores results in SQLite.

Usage:
    python scripts/gsc_etl.py --days 30
"""

import argparse
import logging
import sqlite3
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import orjson
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "performance.db"
CONTENT_GAP_CTR_THRESHOLD = 0.03


# ═══════════════════════════════════════════════════════════════════════════
# Database
# ═══════════════════════════════════════════════════════════════════════════


def init_db(db_path: Path) -> sqlite3.Connection:
    """Create SQLite database and tables if they do not exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        An open sqlite3 connection.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_performance (
            page_url       TEXT,
            total_impressions INTEGER,
            total_clicks   INTEGER,
            avg_ctr        REAL,
            avg_position   REAL,
            fetched_at     TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS keyword_data (
            query          TEXT,
            page_url       TEXT,
            impressions    INTEGER,
            clicks         INTEGER,
            ctr            REAL,
            position       REAL,
            is_content_gap BOOLEAN,
            fetched_at     TEXT
        )
        """
    )
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# GSC Client
# ═══════════════════════════════════════════════════════════════════════════


def build_gsc_service(
    credentials_path: str,
) -> Any:
    """Authenticate and return a GSC service client.

    Args:
        credentials_path: Filesystem path to the service-account JSON key.

    Returns:
        A googleapiclient Resource for the Search Console API.
    """
    creds = Credentials.from_service_account_file(
        credentials_path,
        scopes=[GSC_SCOPE],
    )
    service = build("searchconsole", "v1", credentials=creds)
    return service


def fetch_search_analytics(
    service: Any,
    site_url: str,
    days: int,
) -> list[dict[str, Any]]:
    """Query GSC Search Analytics for query+page performance rows.

    Args:
        service: GSC API service resource.
        site_url: The verified property URL (e.g. ``https://www.viney.ca/``).
        days: Number of trailing days to query.

    Returns:
        A list of row dicts with keys, impressions, clicks, ctr, position.
        Returns an empty list when the property has no data yet.
    """
    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=days)

    request_body: dict[str, Any] = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["query", "page"],
        "rowLimit": 25000,
    }

    logger.info(
        "Querying GSC: site=%s, start=%s, end=%s",
        site_url,
        start_date.isoformat(),
        end_date.isoformat(),
    )

    response: dict[str, Any] = (
        service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
    )

    rows: list[dict[str, Any]] = response.get("rows", [])
    if not rows:
        logger.warning(
            "GSC returned no data for %s. "
            "New properties can take 24-48 hours to populate.",
            site_url,
        )
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Transform
# ═══════════════════════════════════════════════════════════════════════════


def parse_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalise raw GSC rows into flat dicts.

    Args:
        rows: Raw rows from the GSC response.

    Returns:
        List of dicts with query, page_url, impressions, clicks, ctr, position.
    """
    parsed: list[dict[str, Any]] = []
    for row in rows:
        keys = row.get("keys", [])
        parsed.append(
            {
                "query": keys[0] if len(keys) > 0 else "",
                "page_url": keys[1] if len(keys) > 1 else "",
                "impressions": int(row.get("impressions", 0)),
                "clicks": int(row.get("clicks", 0)),
                "ctr": float(row.get("ctr", 0.0)),
                "position": float(row.get("position", 0.0)),
            }
        )
    return parsed


def identify_content_gaps(
    keyword_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flag rows that represent content gaps.

    A content gap is a keyword/page combination where impressions exceed the
    median impression count AND CTR is below the threshold (0.03).

    Args:
        keyword_rows: Parsed keyword rows.

    Returns:
        The same rows with an added ``is_content_gap`` boolean field.
    """
    if not keyword_rows:
        return keyword_rows

    impression_values = [r["impressions"] for r in keyword_rows]
    median_impressions = statistics.median(impression_values)

    for row in keyword_rows:
        row["is_content_gap"] = (
            row["impressions"] > median_impressions
            and row["ctr"] < CONTENT_GAP_CTR_THRESHOLD
        )
    return keyword_rows


def aggregate_by_page(
    keyword_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Roll keyword-level data up to per-page aggregates.

    Args:
        keyword_rows: Parsed keyword rows.

    Returns:
        List of page-level aggregate dicts.
    """
    pages: dict[str, dict[str, Any]] = {}
    for row in keyword_rows:
        url = row["page_url"]
        if url not in pages:
            pages[url] = {
                "page_url": url,
                "total_impressions": 0,
                "total_clicks": 0,
                "ctr_sum": 0.0,
                "position_sum": 0.0,
                "count": 0,
            }
        agg = pages[url]
        agg["total_impressions"] += row["impressions"]
        agg["total_clicks"] += row["clicks"]
        agg["ctr_sum"] += row["ctr"]
        agg["position_sum"] += row["position"]
        agg["count"] += 1

    results: list[dict[str, Any]] = []
    for agg in pages.values():
        count = agg["count"]
        results.append(
            {
                "page_url": agg["page_url"],
                "total_impressions": agg["total_impressions"],
                "total_clicks": agg["total_clicks"],
                "avg_ctr": agg["ctr_sum"] / count if count else 0.0,
                "avg_position": agg["position_sum"] / count if count else 0.0,
            }
        )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# Load (SQLite)
# ═══════════════════════════════════════════════════════════════════════════


def store_results(
    conn: sqlite3.Connection,
    page_rows: list[dict[str, Any]],
    keyword_rows: list[dict[str, Any]],
    fetched_at: str,
) -> None:
    """Persist page and keyword data to SQLite.

    Args:
        conn: Open SQLite connection.
        page_rows: Per-page aggregated rows.
        keyword_rows: Per-keyword rows with content-gap flags.
        fetched_at: ISO-8601 timestamp string for this fetch.
    """
    conn.executemany(
        """
        INSERT INTO search_performance
            (page_url, total_impressions, total_clicks, avg_ctr, avg_position, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["page_url"],
                r["total_impressions"],
                r["total_clicks"],
                r["avg_ctr"],
                r["avg_position"],
                fetched_at,
            )
            for r in page_rows
        ],
    )
    conn.executemany(
        """
        INSERT INTO keyword_data
            (query, page_url, impressions, clicks, ctr, position, is_content_gap, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["query"],
                r["page_url"],
                r["impressions"],
                r["clicks"],
                r["ctr"],
                r["position"],
                r["is_content_gap"],
                fetched_at,
            )
            for r in keyword_rows
        ],
    )
    conn.commit()
    logger.info(
        "Stored %d page rows and %d keyword rows in %s",
        len(page_rows),
        len(keyword_rows),
        conn,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════════════════


def run_etl(
    credentials_path: str,
    site_url: str,
    days: int,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Execute the full ETL pipeline.

    Args:
        credentials_path: Path to the GCP service-account JSON key.
        site_url: GSC verified property URL.
        days: Trailing days to query.
        db_path: Path to the SQLite database.

    Returns:
        Summary dict with total_queries, total_pages, content_gaps counts.
    """
    service = build_gsc_service(credentials_path)
    raw_rows = fetch_search_analytics(service, site_url, days)

    if not raw_rows:
        logger.info("No data returned. Nothing to store.")
        return {"total_queries": 0, "total_pages": 0, "content_gaps": 0}

    keyword_rows = parse_rows(raw_rows)
    keyword_rows = identify_content_gaps(keyword_rows)
    page_rows = aggregate_by_page(keyword_rows)
    fetched_at = datetime.now(tz=UTC).isoformat()

    conn = init_db(db_path)
    try:
        store_results(conn, page_rows, keyword_rows, fetched_at)
    finally:
        conn.close()

    content_gaps = sum(1 for r in keyword_rows if r.get("is_content_gap"))
    summary: dict[str, Any] = {
        "total_queries": len(keyword_rows),
        "total_pages": len(page_rows),
        "content_gaps": content_gaps,
    }
    logger.info(
        "ETL complete — queries=%d, pages=%d, content_gaps=%d",
        summary["total_queries"],
        summary["total_pages"],
        summary["content_gaps"],
    )
    return summary


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Parsed namespace with ``days`` attribute.
    """
    parser = argparse.ArgumentParser(
        description="Google Search Console ETL — fetch keyword & page performance",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of trailing days to query (default: 30)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for CLI execution.

    Args:
        argv: Optional argument list for testing.
    """
    import os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = parse_args(argv)

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    site_url = os.environ.get("GSC_PROPERTY_URL", "")

    if not credentials_path:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS is not set.")
        raise SystemExit(1)
    if not site_url:
        logger.error("GSC_PROPERTY_URL is not set.")
        raise SystemExit(1)

    summary = run_etl(credentials_path, site_url, args.days)
    logger.info("Summary: %s", orjson.dumps(summary).decode())


if __name__ == "__main__":
    main()
