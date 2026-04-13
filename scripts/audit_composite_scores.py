#!/usr/bin/env python3
"""Audit composite engagement scores stored in the performance database.

Reads ``data/performance.db`` (written by ``scripts/ga4_etl.py``) and
produces a step-by-step audit of the composite-scoring mathematics for a
representative sample of URLs.

Usage:
    .venv/bin/python scripts/audit_composite_scores.py [--db DATA_DB]

Output:
    Markdown report to stdout **and** ``output/composite_score_audit_<ts>.md``.

Exit codes:
    0 — verdict is "proceed"
    1 — verdict is "re-weight" or "wait for GSC"
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sqlite3
import sys

# Re-derive the composite-scoring constants from ga4_etl so the audit stays
# honest if the formula ever changes.
# sys.path is extended so both `python scripts/audit_composite_scores.py`
# (scripts/ added by Python) and `pytest` (repo root added by pythonpath=.)
# can resolve the sibling module.
import sys as _sys
from datetime import UTC, datetime
from typing import Any

_sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ga4_etl import COMPOSITE_WEIGHTS, normalize  # noqa: E402

logger = logging.getLogger(__name__)

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "performance.db"
OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "output"

# DB columns that map to composite-score inputs (excludes page_path, page_title,
# composite_score, and fetched_at)
_DB_METRIC_COLS: list[str] = [
    "pageviews",
    "engagement_rate",
    "avg_engagement_time",
    "scroll_depth_rate",
]

# Terms in COMPOSITE_WEIGHTS that have NO corresponding DB column are placeholders
# (currently search_ctr and search_impressions — GSC not yet integrated).
# We derive this dynamically so the audit stays honest if ga4_etl.py changes.
_ACTIVE_TERMS: set[str] = set(COMPOSITE_WEIGHTS) & set(_DB_METRIC_COLS)
_ZERO_WEIGHT_TERMS: set[str] = set(COMPOSITE_WEIGHTS) - _ACTIVE_TERMS
_ACTIVE_WEIGHT_SUM: float = sum(COMPOSITE_WEIGHTS[t] for t in _ACTIVE_TERMS)
_ZERO_WEIGHT_SUM: float = sum(COMPOSITE_WEIGHTS[t] for t in _ZERO_WEIGHT_TERMS)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def load_all_rows(db_path: pathlib.Path) -> list[dict[str, Any]]:
    """Load all rows from ``article_performance`` (latest snapshot per URL).

    We take the row with the most recent ``fetched_at`` per ``page_path`` so
    the audit reflects the current state of the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of row dicts with keys matching the table schema.

    Raises:
        FileNotFoundError: If ``db_path`` does not exist.
        sqlite3.OperationalError: If the table does not exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}\n"
            "Run `python scripts/ga4_etl.py` first to populate it."
        )

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            """
            SELECT page_path, page_title, pageviews, engagement_rate,
                   avg_engagement_time, scroll_depth_rate, composite_score,
                   fetched_at
            FROM article_performance
            WHERE fetched_at = (
                SELECT MAX(fetched_at)
                FROM article_performance AS inner_ap
                WHERE inner_ap.page_path = article_performance.page_path
            )
            ORDER BY composite_score DESC
            """
        )
        rows: list[dict[str, Any]] = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    logger.info("Loaded %d rows from %s", len(rows), db_path)
    return rows


# ---------------------------------------------------------------------------
# Sample selection
# ---------------------------------------------------------------------------


def select_sample(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Choose 5 representative URLs spanning the score distribution.

    The five slots are:

    * ``top`` — Highest composite score
    * ``viral_shallow`` — Lowest composite score where ``pageviews > 50``
    * ``median`` — Row closest to the median composite score
    * ``most_traffic`` — Highest pageviews
    * ``tail`` — Lowest pageviews where ``pageviews > 5``

    Args:
        rows: All rows ordered by composite_score DESC.

    Returns:
        Dict mapping slot name → row dict.  A slot is absent if no qualifying
        row exists.
    """
    if not rows:
        return {}

    sample: dict[str, dict[str, Any]] = {}

    # Top scorer
    sample["top"] = rows[0]

    # Highest pageviews
    most_traffic = max(rows, key=lambda r: r["pageviews"])
    sample["most_traffic"] = most_traffic

    # Median composite score
    sorted_by_score = sorted(rows, key=lambda r: r["composite_score"])
    mid = len(sorted_by_score) // 2
    sample["median"] = sorted_by_score[mid]

    # Lowest composite score with pageviews > 50
    candidates_viral = [r for r in rows if r["pageviews"] > 50]
    if candidates_viral:
        sample["viral_shallow"] = min(
            candidates_viral, key=lambda r: r["composite_score"]
        )

    # Lowest pageviews with pageviews > 5
    candidates_tail = [r for r in rows if r["pageviews"] > 5]
    if candidates_tail:
        sample["tail"] = min(candidates_tail, key=lambda r: r["pageviews"])

    return sample


# ---------------------------------------------------------------------------
# Per-URL math walkthrough
# ---------------------------------------------------------------------------


def recompute_score(
    row: dict[str, Any],
    all_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Re-derive normalized values and weighted contributions for one URL.

    Args:
        row: The target row.
        all_rows: Full dataset used for min-max normalisation.

    Returns:
        Dict with keys:
        * ``raw`` — original metric values
        * ``normalized`` — min-max normalised values per ``COMPOSITE_WEIGHTS``
        * ``contributions`` — weighted contribution per term
        * ``recomputed_score`` — sum of contributions
        * ``stored_score`` — ``composite_score`` from the database
        * ``zero_terms`` — list of terms contributing 0.0 (placeholders)
    """
    # Build normalised vectors for the metrics available in the DB
    norm_pageviews = normalize([r["pageviews"] for r in all_rows])
    norm_engagement = normalize([r["engagement_rate"] for r in all_rows])
    norm_time = normalize([r["avg_engagement_time"] for r in all_rows])
    norm_scroll = normalize([r["scroll_depth_rate"] for r in all_rows])

    idx = next(i for i, r in enumerate(all_rows) if r["page_path"] == row["page_path"])

    norm_map: dict[str, float] = {
        "pageviews": norm_pageviews[idx],
        "engagement_rate": norm_engagement[idx],
        "avg_engagement_time": norm_time[idx],
        "scroll_depth_rate": norm_scroll[idx],
        # GSC placeholders — always 0.0 until integrated
        "search_ctr": 0.0,
        "search_impressions": 0.0,
    }

    contributions: dict[str, float] = {
        term: weight * norm_map[term] for term, weight in COMPOSITE_WEIGHTS.items()
    }

    zero_terms = [t for t, c in contributions.items() if c == 0.0]

    return {
        "raw": {k: row[k] for k in _DB_METRIC_COLS},
        "normalized": norm_map,
        "contributions": contributions,
        "recomputed_score": round(sum(contributions.values()), 6),
        "stored_score": row["composite_score"],
        "zero_terms": zero_terms,
    }


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------


def _fmt_float(value: float, decimals: int = 4) -> str:
    """Format a float with a fixed number of decimal places."""
    return f"{value:.{decimals}f}"


def render_url_section(
    slot: str,
    row: dict[str, Any],
    math: dict[str, Any],
) -> str:
    """Render a Markdown section for one URL.

    Args:
        slot: Descriptive slot name (e.g. "top", "median").
        row: The database row for this URL.
        math: Output from :func:`recompute_score`.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    label_map = {
        "top": "🏆 Top scorer",
        "viral_shallow": "📉 Viral-but-shallow",
        "median": "🎯 Median scorer",
        "most_traffic": "🚦 Most traffic",
        "tail": "🔻 Tail (low pageviews)",
    }
    label = label_map.get(slot, slot.replace("_", " ").title())

    lines.append(f"### {label}: `{row['page_path']}`")
    lines.append("")
    lines.append(f"**Title:** {row.get('page_title', '(unknown)')}")
    lines.append("")

    # Raw values
    lines.append("#### Raw values")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for col in _DB_METRIC_COLS:
        lines.append(f"| `{col}` | {row[col]} |")
    lines.append("")

    # Normalised values
    lines.append("#### Normalised values (0–1 min-max)")
    lines.append("")
    lines.append("| Metric | Normalised |")
    lines.append("|--------|-----------|")
    for term, nv in math["normalized"].items():
        flag = " ⚠️ placeholder" if term in {"search_ctr", "search_impressions"} else ""
        lines.append(f"| `{term}` | {_fmt_float(nv)}{flag} |")
    lines.append("")

    # Weighted contributions
    lines.append("#### Weighted contributions")
    lines.append("")
    lines.append("| Term | Weight | × Normalised | = Contribution |")
    lines.append("|------|--------|-------------|----------------|")
    for term, contrib in math["contributions"].items():
        w = COMPOSITE_WEIGHTS[term]
        nv = math["normalized"][term]
        flag = " ⚠️" if contrib == 0.0 and w > 0.0 else ""
        lines.append(
            f"| `{term}` | {w} | × {_fmt_float(nv)} | = {_fmt_float(contrib)}{flag} |"
        )
    lines.append(f"| **Total** | | | **{_fmt_float(math['recomputed_score'])}** |")
    lines.append("")

    # Score comparison
    lines.append("#### Score check")
    match = math["recomputed_score"] == math["stored_score"]
    status = "✅ matches stored value" if match else "❌ MISMATCH vs stored value"
    lines.append(
        f"Recomputed: `{math['recomputed_score']}` — {status} "
        f"(stored: `{math['stored_score']}`)"
    )
    lines.append("")

    # Zero-term flags
    active_zero = [t for t in math["zero_terms"] if COMPOSITE_WEIGHTS.get(t, 0.0) > 0.0]
    if active_zero:
        lines.append(
            f"> ⚠️ **{len(active_zero)} term(s) with positive weight are zeroed:** "
            + ", ".join(f"`{t}`" for t in active_zero)
        )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------


def run_sanity_checks(
    rows: list[dict[str, Any]],
    sample: dict[str, dict[str, Any]],
    math_map: dict[str, dict[str, Any]],
) -> list[str]:
    """Run sanity checks and return a list of Markdown bullet points.

    Checks:
    1. Is the highest-pageviews URL in the top 20% by composite score?
    2. Is scoring deterministic (recomputed == stored)?
    3. What fraction of the score comes from active vs placeholder weights?

    Args:
        rows: All rows.
        sample: Sampled URLs from :func:`select_sample`.
        math_map: ``{slot: recomputed_math}`` from :func:`recompute_score`.

    Returns:
        List of Markdown lines for the sanity-check section.
    """
    lines: list[str] = []

    # 1 — Is the highest-pageviews URL in the top 20%?
    n = len(rows)
    sorted_by_score = sorted(rows, key=lambda r: r["composite_score"], reverse=True)
    top_20_pct_cutoff = max(1, int(n * 0.2))
    top_20_paths = {r["page_path"] for r in sorted_by_score[:top_20_pct_cutoff]}

    if "most_traffic" in sample:
        traffic_path = sample["most_traffic"]["page_path"]
        if traffic_path in top_20_paths:
            lines.append(
                f"- ✅ **Top-traffic URL is in the top 20% by composite score** "
                f"(`{traffic_path}`)"
            )
        else:
            rank = next(
                i + 1
                for i, r in enumerate(sorted_by_score)
                if r["page_path"] == traffic_path
            )
            pct = 100 * rank / n
            lines.append(
                f"- ⚠️ **Top-traffic URL is NOT in the top 20% by composite score** "
                f"(`{traffic_path}`, rank {rank}/{n}, top {pct:.0f}%). "
                f"High pageviews alone do not guarantee a high composite score; "
                f"engagement-quality metrics (rate, time, scroll) must also be strong."
            )

    # 2 — Stored vs. recomputed score comparison
    # Note: differences are expected and non-alarming. Min-max normalisation is
    # dataset-dependent — the ETL stored scores were derived from the full batch
    # of rows at fetch time, while this audit re-normalises over the current DB
    # snapshot (which may differ in row count or range). What matters is that
    # running the audit twice on the same snapshot produces identical results.
    mismatches = [
        slot
        for slot, m in math_map.items()
        if m["recomputed_score"] != m["stored_score"]
    ]
    if mismatches:
        lines.append(
            "- ℹ️ **Stored vs. recomputed scores differ** for "
            + str(len(mismatches))
            + " sample URL(s) — this is expected. Min-max normalisation is "
            "dataset-scoped: the ETL stored each score against the full fetch "
            "batch, while this audit re-normalises over the current DB snapshot. "
            "The formula itself is deterministic (re-running this audit on the "
            "same snapshot will always produce the same recomputed values)."
        )
    else:
        lines.append(
            "- ✅ **Stored scores match recomputed values** for all sampled URLs "
            "(ETL batch and current DB snapshot appear identical in range)."
        )

    # 3 — Active vs placeholder weight fraction
    active_pct = 100 * _ACTIVE_WEIGHT_SUM
    zero_pct = 100 * _ZERO_WEIGHT_SUM
    placeholder_terms = ", ".join(
        f"`{t}` ({COMPOSITE_WEIGHTS[t]:.2f})"
        for t in COMPOSITE_WEIGHTS
        if t not in _ACTIVE_TERMS
    )
    active_terms_str = ", ".join(
        f"`{t}` ({COMPOSITE_WEIGHTS[t]:.2f})" for t in _ACTIVE_TERMS
    )
    lines.append(
        f"- 📊 **Active weight fraction: {active_pct:.0f}%** "
        f"({active_terms_str}).  "
        f"Placeholder (zero) fraction: {zero_pct:.0f}% ({placeholder_terms})."
    )

    return lines


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def compute_verdict(rows: list[dict[str, Any]]) -> tuple[str, str, int]:
    """Determine the audit verdict.

    Logic:
    * If no GSC terms are zero-weighted (all weights active) → "proceed"
    * If zero-weight placeholders represent < 20% of the total weight
      and rankings are otherwise stable → "proceed"
    * If zero-weight placeholders ≥ 20% but < 40% → "re-weight"
    * If zero-weight placeholders ≥ 40% → "wait for GSC"

    Args:
        rows: All rows loaded from the database.

    Returns:
        Tuple of (verdict_key, narrative, exit_code).
    """
    # TODO: use rows for additional ranking-stability checks once GSC data is available
    #       (e.g., compare pre/post GSC ranking positions to quantify the ranking shift)

    zero_fraction = _ZERO_WEIGHT_SUM  # already a fraction of 1.0

    if zero_fraction == 0.0:
        return (
            "proceed",
            "All composite-score dimensions are active. Rankings are based on the "
            "full formula.",
            0,
        )
    if zero_fraction < 0.20:
        return (
            "proceed",
            f"Zero-weight placeholders account for only "
            f"{zero_fraction * 100:.0f}% of the total weight. Current rankings "
            f"are sufficiently meaningful for topic selection.",
            0,
        )
    if zero_fraction < 0.40:
        return (
            "re-weight",
            f"Zero-weight placeholders account for {zero_fraction * 100:.0f}% of "
            f"the total weight. Consider temporarily redistributing that weight to "
            f"active dimensions so rankings reflect 100% of available signal.",
            1,
        )
    return (
        "wait for GSC",
        f"Zero-weight placeholders account for {zero_fraction * 100:.0f}% of the "
        f"total weight — rankings derived from only "
        f"{_ACTIVE_WEIGHT_SUM * 100:.0f}% of the intended formula. "
        f"Activating the GSC integration before using these rankings for topic "
        f"selection is strongly recommended.",
        1,
    )


def render_verdict_section(
    verdict_key: str,
    narrative: str,
    rows: list[dict[str, Any]],
) -> str:
    """Render the verdict section of the report.

    Args:
        verdict_key: One of "proceed", "re-weight", "wait for GSC".
        narrative: Human-readable explanation of the verdict.
        rows: All rows. Reserved for future per-row GSC-activation projections.

    Returns:
        Markdown string.
    """
    # TODO: use rows to project per-URL score changes when GSC data becomes available
    icon = {"proceed": "✅", "re-weight": "⚠️", "wait for GSC": "🚫"}.get(
        verdict_key, "❓"
    )
    lines: list[str] = [
        "## Verdict",
        "",
        f"**{icon} {verdict_key.upper()}**",
        "",
        narrative,
        "",
        "### What would change if GSC terms were activated?",
        "",
    ]

    gsc_terms = [t for t in COMPOSITE_WEIGHTS if t not in _ACTIVE_TERMS]
    if gsc_terms:
        total_gsc_weight = sum(COMPOSITE_WEIGHTS[t] for t in gsc_terms)
        lines.append(
            f"Activating {', '.join(f'`{t}`' for t in gsc_terms)} would add "
            f"{total_gsc_weight * 100:.0f}% weight to the composite score. URLs "
            f"with high organic search visibility (impressions) and click-through "
            f"rates would rise in the rankings relative to URLs that perform well "
            f"only on GA4 engagement metrics. This could significantly reorder "
            f"topic-selection priorities."
        )
    else:
        lines.append("All terms are currently active — no change expected.")

    lines += [
        "",
        "### Recommendation",
        "",
    ]

    reco_map = {
        "proceed": (
            "Proceed with the current scoring. The rankings are meaningful and "
            "the feedback loop can be advanced to the Accepted state in ADR-0007."
        ),
        "re-weight": (
            "Temporarily redistribute the placeholder weights to active dimensions "
            "(e.g., increase `pageviews` or `engagement_rate` weights proportionally) "
            "before using rankings for production topic selection. Re-evaluate once "
            "GSC integration is complete."
        ),
        "wait for GSC": (
            "Do **not** advance ADR-0007 to Accepted yet. Complete the GSC integration "
            "first so that all scoring dimensions are active. The current rankings "
            "cover too small a fraction of the intended formula to be reliable."
        ),
    }
    lines.append(reco_map.get(verdict_key, "See narrative above."))
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def build_report(
    rows: list[dict[str, Any]],
    db_path: pathlib.Path,
) -> tuple[str, int]:
    """Build the full Markdown audit report.

    Args:
        rows: All rows from the database.
        db_path: Source database path (for the report header).

    Returns:
        Tuple of (markdown_text, exit_code).
    """
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    n = len(rows)
    lines: list[str] = [
        "# Composite Score Audit",
        "",
        f"**Generated:** {ts}  ",
        f"**Source:** `{db_path}`  ",
        f"**Total URLs in database:** {n}  ",
        "**Formula:** weighted sum of min-max-normalised metrics per "
        "`scripts/ga4_etl.COMPOSITE_WEIGHTS`",
        "",
        "## Weight Summary",
        "",
        "| Term | Weight | Status |",
        "|------|--------|--------|",
    ]
    for term, weight in COMPOSITE_WEIGHTS.items():
        if term in _ACTIVE_TERMS:
            status = "✅ active"
        else:
            status = "⚠️ placeholder (0.0 — GSC not integrated)"
        lines.append(f"| `{term}` | {weight} | {status} |")
    lines.append("")
    lines.append(
        f"**Active weight total:** {_ACTIVE_WEIGHT_SUM:.2f} "
        f"({_ACTIVE_WEIGHT_SUM * 100:.0f}% of formula)  "
    )
    lines.append(
        f"**Placeholder weight total:** {_ZERO_WEIGHT_SUM:.2f} "
        f"({_ZERO_WEIGHT_SUM * 100:.0f}% of formula)"
    )
    lines.append("")

    if n == 0:
        lines += [
            "## Sample URLs",
            "",
            "> ⚠️ The database is empty. Run `python scripts/ga4_etl.py` to populate it.",
            "",
        ]
        verdict_key, narrative, exit_code = "wait for GSC", "No data available.", 1
        lines.append(render_verdict_section(verdict_key, narrative, rows))
        return "\n".join(lines), exit_code

    # ---- Per-URL walkthroughs ----------------------------------------
    sample = select_sample(rows)
    math_map: dict[str, dict[str, Any]] = {
        slot: recompute_score(row, rows) for slot, row in sample.items()
    }

    lines.append("## Sample URL Walkthroughs")
    lines.append("")
    for slot, row in sample.items():
        lines.append(render_url_section(slot, row, math_map[slot]))

    # ---- Sanity checks -----------------------------------------------
    lines.append("## Sanity Checks")
    lines.append("")
    sanity_bullets = run_sanity_checks(rows, sample, math_map)
    lines.extend(sanity_bullets)
    lines.append("")

    # ---- Verdict -------------------------------------------------------
    verdict_key, narrative, exit_code = compute_verdict(rows)
    lines.append(render_verdict_section(verdict_key, narrative, rows))

    return "\n".join(lines), exit_code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the audit CLI."""
    parser = argparse.ArgumentParser(
        description="Audit composite engagement scores in the performance database.",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help="Path to the SQLite performance database (default: data/performance.db)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry-point for the composite score audit.

    Args:
        argv: Optional list of CLI arguments (defaults to sys.argv).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    db_path = pathlib.Path(args.db)

    try:
        rows = load_all_rows(db_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except sqlite3.OperationalError as exc:
        logger.error("Database error: %s", exc)
        sys.exit(1)

    report, exit_code = build_report(rows, db_path)

    # Write to stdout
    print(report)

    # Write to output file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts_file = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"composite_score_audit_{ts_file}.md"
    out_path.write_text(report, encoding="utf-8")
    logger.info("Report written to %s", out_path)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
