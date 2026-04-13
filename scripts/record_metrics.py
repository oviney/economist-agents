#!/usr/bin/env python3
"""
Record Metrics — CLI tool to append a pipeline run row to data/metrics.db.

Usage:
    python3 scripts/record_metrics.py \\
        --agent researcher \\
        --topic "AI in Finance" \\
        --editorial-score 82 \\
        --gates-passed 4 \\
        --token-count 12000 \\
        --cost-usd 0.036 \\
        --duration-s 47.2 \\
        --status published

    # Or pass all fields via JSON:
    python3 scripts/record_metrics.py --json '{"agent_name": "researcher", ...}'

DB schema:
    run_id          TEXT PRIMARY KEY   (UUID v4)
    timestamp       TEXT               (ISO-8601)
    agent_name      TEXT
    topic           TEXT
    editorial_score REAL
    gates_passed    INTEGER
    token_count     INTEGER
    cost_usd        REAL
    duration_s      REAL
    status          TEXT               (published | revision | failed)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default DB path (overridable via DB_PATH env-var or function argument)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
DEFAULT_DB_PATH = _REPO_ROOT / "data" / "metrics.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    agent_name      TEXT NOT NULL,
    topic           TEXT NOT NULL,
    editorial_score REAL NOT NULL DEFAULT 0,
    gates_passed    INTEGER NOT NULL DEFAULT 0,
    token_count     INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0.0,
    duration_s      REAL NOT NULL DEFAULT 0.0,
    status          TEXT NOT NULL DEFAULT 'unknown'
);
"""

_VALID_STATUSES = {"published", "revision", "failed", "unknown"}


# ---------------------------------------------------------------------------
# Public API (imported by metrics_dashboard.py and tests)
# ---------------------------------------------------------------------------


def get_db_path() -> Path:
    """Return the default database path, creating parent dir if needed.

    Returns:
        Path to the SQLite database file.
    """
    import os

    env_override = os.environ.get("METRICS_DB_PATH")
    if env_override:
        return Path(env_override)
    return DEFAULT_DB_PATH


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure schema exists.

    Args:
        db_path: Path to the database file. Defaults to ``data/metrics.db``.

    Returns:
        An open :class:`sqlite3.Connection` with row_factory set to
        ``sqlite3.Row``.
    """
    if db_path is None:
        db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    logger.debug("DB initialised at %s", db_path)
    return conn


def record_run(
    agent_name: str,
    topic: str,
    editorial_score: float = 0.0,
    gates_passed: int = 0,
    token_count: int = 0,
    cost_usd: float = 0.0,
    duration_s: float = 0.0,
    status: str = "unknown",
    run_id: str | None = None,
    timestamp: str | None = None,
    db_path: Path | None = None,
) -> str:
    """Insert one pipeline-run row into the database.

    Args:
        agent_name: Name of the primary agent (e.g. ``"researcher"``).
        topic: Article topic string.
        editorial_score: Editorial quality score (0–100).
        gates_passed: Number of editorial gates passed (0–5).
        token_count: Total tokens consumed during the run.
        cost_usd: Estimated API cost in USD.
        duration_s: Wall-clock duration in seconds.
        status: One of ``published``, ``revision``, ``failed``, ``unknown``.
        run_id: UUID string; auto-generated when omitted.
        timestamp: ISO-8601 string; defaults to UTC now.
        db_path: Override the default DB path.

    Returns:
        The ``run_id`` of the inserted row.

    Raises:
        ValueError: If *status* is not a recognised value.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Invalid status {status!r}. Must be one of {sorted(_VALID_STATUSES)}"
        )
    if run_id is None:
        run_id = str(uuid.uuid4())
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    conn = init_db(db_path)
    try:
        conn.execute(
            """
            INSERT INTO pipeline_runs
                (run_id, timestamp, agent_name, topic,
                 editorial_score, gates_passed, token_count,
                 cost_usd, duration_s, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                timestamp,
                agent_name,
                topic,
                editorial_score,
                gates_passed,
                token_count,
                cost_usd,
                duration_s,
                status,
            ),
        )
        conn.commit()
        logger.info("Recorded run %s (%s / %s)", run_id, agent_name, status)
    finally:
        conn.close()

    return run_id


def fetch_all_runs(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return all rows from *pipeline_runs*, newest-first.

    Args:
        db_path: Override the default DB path.

    Returns:
        A list of dicts, each representing one pipeline run.
    """
    conn = init_db(db_path)
    try:
        cursor = conn.execute("SELECT * FROM pipeline_runs ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def compute_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics from a list of run dicts.

    Args:
        runs: List of run dicts as returned by :func:`fetch_all_runs`.

    Returns:
        Dictionary with keys:

        - ``total_runs`` (int)
        - ``published_count`` (int)
        - ``revision_count`` (int)
        - ``failed_count`` (int)
        - ``avg_editorial_score`` (float)
        - ``avg_cost_usd`` (float)
        - ``avg_duration_s`` (float)
        - ``total_cost_usd`` (float)
        - ``success_rate_pct`` (float)  — published / total × 100
    """
    if not runs:
        return {
            "total_runs": 0,
            "published_count": 0,
            "revision_count": 0,
            "failed_count": 0,
            "avg_editorial_score": 0.0,
            "avg_cost_usd": 0.0,
            "avg_duration_s": 0.0,
            "total_cost_usd": 0.0,
            "success_rate_pct": 0.0,
        }

    total = len(runs)
    published = sum(1 for r in runs if r["status"] == "published")
    revision = sum(1 for r in runs if r["status"] == "revision")
    failed = sum(1 for r in runs if r["status"] == "failed")

    avg_score = sum(r["editorial_score"] for r in runs) / total
    total_cost = sum(r["cost_usd"] for r in runs)
    avg_cost = total_cost / total
    avg_dur = sum(r["duration_s"] for r in runs) / total
    success_rate = (published / total) * 100 if total > 0 else 0.0

    return {
        "total_runs": total,
        "published_count": published,
        "revision_count": revision,
        "failed_count": failed,
        "avg_editorial_score": round(avg_score, 2),
        "avg_cost_usd": round(avg_cost, 4),
        "avg_duration_s": round(avg_dur, 2),
        "total_cost_usd": round(total_cost, 4),
        "success_rate_pct": round(success_rate, 1),
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a pipeline-run row to data/metrics.db",
    )
    parser.add_argument(
        "--agent",
        dest="agent_name",
        default="unknown",
        help="Agent name (default: unknown)",
    )
    parser.add_argument("--topic", default="", help="Article topic")
    parser.add_argument(
        "--editorial-score",
        type=float,
        default=0.0,
        metavar="SCORE",
        help="Editorial score 0-100 (default: 0)",
    )
    parser.add_argument(
        "--gates-passed",
        type=int,
        default=0,
        metavar="N",
        help="Number of gates passed (default: 0)",
    )
    parser.add_argument(
        "--token-count",
        type=int,
        default=0,
        metavar="N",
        help="Total tokens consumed (default: 0)",
    )
    parser.add_argument(
        "--cost-usd",
        type=float,
        default=0.0,
        metavar="COST",
        help="Cost in USD (default: 0)",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=0.0,
        metavar="SECS",
        help="Duration in seconds (default: 0)",
    )
    parser.add_argument(
        "--status",
        default="unknown",
        choices=sorted(_VALID_STATUSES),
        help="Run status (default: unknown)",
    )
    parser.add_argument(
        "--db-path", default=None, help="Override DB path (default: data/metrics.db)"
    )
    return parser


def main() -> None:
    """CLI entry-point: parse arguments and call :func:`record_run`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else None
    run_id = record_run(
        agent_name=args.agent_name,
        topic=args.topic,
        editorial_score=args.editorial_score,
        gates_passed=args.gates_passed,
        token_count=args.token_count,
        cost_usd=args.cost_usd,
        duration_s=args.duration_s,
        status=args.status,
        db_path=db_path,
    )
    print(f"✅ Recorded run {run_id}")


if __name__ == "__main__":
    main()
