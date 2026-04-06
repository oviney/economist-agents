#!/usr/bin/env python3
"""A/B verification of the Topic Scout feedback loop (ADR-0007).

Runs Topic Scout twice — once *with* the GA4 performance context (Run A)
and once *without* it (Run B) — and compares the two result sets to
determine whether the feedback loop is causally real.

Metrics:
    - Jaccard similarity of topic titles (0.0 = completely different,
      1.0 = identical)
    - Per-dimension score delta (avg and max across the five criteria)
    - Qualitative notes: which Run A topics reference a top/bottom
      performer from the DB

Verdict criteria (both must hold for the loop to be "causally real"):
    1. Jaccard similarity < 0.6
    2. At least one Run A topic explicitly references a top performer
       from the database in its hook, thesis, or contrarian_angle field.

Usage:
    .venv/bin/python scripts/ab_topic_scout_comparison.py [--runs N]

Output:
    - Markdown report printed to stdout
    - Report saved to output/ab_topic_scout_comparison_YYYYMMDD_HHMMSS.md
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import orjson

# ---------------------------------------------------------------------------
# Path setup — allow running from the repo root or the scripts/ directory
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import content_intelligence  # noqa: E402
import topic_scout  # noqa: E402
from llm_client import create_llm_client  # noqa: E402

logger = logging.getLogger(__name__)

# Fallback string returned by the monkey-patched Run B
_EMPTY_CONTEXT = (
    "## Performance Context\n\n"
    "_No performance data available yet. Run `scripts/ga4_etl.py` "
    "to populate `data/performance.db`._\n"
)

SCORE_DIMENSIONS: tuple[str, ...] = (
    "timeliness",
    "data_availability",
    "contrarian_potential",
    "audience_fit",
    "economist_fit",
)


# ---------------------------------------------------------------------------
# Core comparison helpers
# ---------------------------------------------------------------------------


def _topic_title_set(topics: list[dict[str, Any]]) -> set[str]:
    """Extract a normalised set of topic titles.

    Args:
        topics: List of topic dicts as returned by ``scout_topics``.

    Returns:
        Set of lower-cased, stripped title strings.
    """
    return {t.get("topic", "").strip().lower() for t in topics if t.get("topic")}


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets of strings.

    Returns ``intersection / union``.  When both sets are empty the
    result is 0.0 (vacuously no overlap rather than vacuously identical)
    so that an A/B run with zero topics does not falsely appear as a
    perfect match.

    Args:
        set_a: First set of strings.
        set_b: Second set of strings.

    Returns:
        Float in [0.0, 1.0].
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def score_deltas(
    topics_a: list[dict[str, Any]],
    topics_b: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Compute per-dimension score statistics between two topic lists.

    For each SCORE_DIMENSION, compute the average and maximum absolute
    delta, using the mean score of each run as its representative value
    for that dimension.

    Args:
        topics_a: Run A topic list.
        topics_b: Run B topic list.

    Returns:
        Dict mapping dimension name to ``{"avg_delta": ..., "max_delta": ...}``.
    """

    def _mean_dim(topics: list[dict[str, Any]], dim: str) -> float:
        vals = [
            float(t.get("scores", {}).get(dim, 0)) for t in topics if t.get("scores")
        ]
        return sum(vals) / len(vals) if vals else 0.0

    result: dict[str, dict[str, float]] = {}
    for dim in SCORE_DIMENSIONS:
        avg_a = _mean_dim(topics_a, dim)
        avg_b = _mean_dim(topics_b, dim)
        delta = abs(avg_a - avg_b)
        # Individual per-topic max delta
        per_topic_deltas: list[float] = []
        for t in topics_a:
            score_a = float(t.get("scores", {}).get(dim, 0))
        # Compare to the nearest-named topic in B or fall back to avg_b.
            # NOTE: when there is no matching topic by title the fallback
            # uses avg_b (the run-level mean), which makes the comparison
            # asymmetric.  This is intentional: Run A topics that have no
            # Run B counterpart still contribute to max_delta so the caller
            # is made aware of the strongest single divergence point.
            matched = next(
                (
                    b
                    for b in topics_b
                    if b.get("topic", "").strip().lower()
                    == t.get("topic", "").strip().lower()
                ),
                None,
            )
            score_b = float(matched.get("scores", {}).get(dim, 0)) if matched else avg_b
            per_topic_deltas.append(abs(score_a - score_b))
        max_delta = max(per_topic_deltas) if per_topic_deltas else delta
        result[dim] = {"avg_delta": round(delta, 3), "max_delta": round(max_delta, 3)}
    return result


def qualitative_notes(
    topics_a: list[dict[str, Any]],
    top_performers: list[content_intelligence.ArticlePerformance],
    bottom_performers: list[content_intelligence.ArticlePerformance],
) -> list[str]:
    """Identify Run A topics that explicitly reference top/bottom performers.

    Searches each Run A topic's ``hook``, ``thesis``, ``contrarian_angle``,
    and ``timeliness_trigger`` fields for keywords drawn from the article
    titles in the performance database.

    Args:
        topics_a: Run A topic list.
        top_performers: Top-performing articles from the DB.
        bottom_performers: Bottom-performing articles from the DB.

    Returns:
        List of human-readable note strings.
    """
    notes: list[str] = []

    def _keywords(title: str) -> list[str]:
        """Extract single-word keywords from an article title.

        Strips punctuation, filters short words (≤3 chars) and common
        English stop-words so that only meaningful content words remain.
        """
        stop = {"the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "are"}
        words = [w.lower().strip(".,:-") for w in title.split() if len(w) > 3]
        return [w for w in words if w not in stop]

    def _searchable(topic: dict[str, Any]) -> set[str]:
        """Return a set of whole lower-cased words from key topic fields."""
        raw = " ".join(
            str(topic.get(field, "")).lower()
            for field in ("hook", "thesis", "contrarian_angle", "timeliness_trigger", "topic")
        )
        return set(re.findall(r"\b\w+\b", raw))

    for topic in topics_a:
        words = _searchable(topic)
        title = topic.get("topic", "")

        for art in top_performers:
            kws = _keywords(art.page_title or art.page_path)
            matched_kws = [kw for kw in kws if kw in words]
            if matched_kws:
                notes.append(
                    f'✅ Run A topic **"{title}"** references top-performer '
                    f'**"{art.page_title}"** (keywords: {", ".join(matched_kws)})'
                )
                break

        for art in bottom_performers:
            kws = _keywords(art.page_title or art.page_path)
            matched_kws = [kw for kw in kws if kw in words]
            if matched_kws:
                notes.append(
                    f'⚠️  Run A topic **"{title}"** resembles underperformer '
                    f'**"{art.page_title}"** (keywords: {", ".join(matched_kws)})'
                )
                break

    if not notes:
        notes.append(
            "ℹ️  No Run A topic explicitly matched keywords from the top/bottom performers."
        )
    return notes


def verdict(
    jac: float,
    notes: list[str],
) -> tuple[bool, str]:
    """Determine if the feedback loop is causally real.

    Criteria (both required):
        1. Jaccard similarity < 0.6
        2. At least one Run A topic explicitly references a top performer
           from the DB.

    Args:
        jac: Jaccard similarity score.
        notes: Qualitative notes from ``qualitative_notes()``.

    Returns:
        Tuple of (is_real: bool, explanation: str).
    """
    has_top_ref = any("✅" in note for note in notes)
    criteria_1 = jac < 0.6
    criteria_2 = has_top_ref
    is_real = criteria_1 and criteria_2

    reasons: list[str] = []
    reasons.append(
        f"Jaccard similarity = {jac:.3f} "
        + ("✅ < 0.6 (runs diverge)" if criteria_1 else "❌ ≥ 0.6 (runs too similar)")
    )
    reasons.append(
        "Run A references a top performer: "
        + ("✅ YES" if criteria_2 else "❌ NO")
    )

    conclusion = (
        "**✅ VERDICT: Feedback loop is causally real.**"
        if is_real
        else "**❌ VERDICT: Feedback loop is NOT confirmed.**"
    )
    explanation = "\n".join(reasons) + "\n\n" + conclusion
    return is_real, explanation


# ---------------------------------------------------------------------------
# Single A/B pair runner
# ---------------------------------------------------------------------------


def run_ab_pair(
    client: Any,
    pair_index: int = 1,
) -> dict[str, Any]:
    """Execute one A/B scout pair and return the comparison data.

    Run A calls ``topic_scout.scout_topics()`` normally (with GA4 context).
    Run B monkey-patches ``topic_scout.get_performance_context`` to return
    an empty-fallback string, then calls ``scout_topics()`` again.

    Args:
        client: LLM client instance (from ``create_llm_client``).
        pair_index: 1-based index for log messages.

    Returns:
        Dict with keys: ``topics_a``, ``topics_b``, ``jaccard``,
        ``deltas``, ``notes``, ``verdict_is_real``, ``verdict_text``,
        ``top_performers``, ``bottom_performers``.
    """
    logger.info("Pair %d — Run A (with performance context)…", pair_index)
    topics_a = topic_scout.scout_topics(client)

    logger.info("Pair %d — Run B (without performance context)…", pair_index)
    with patch.object(
        topic_scout,
        "get_performance_context",
        return_value=_EMPTY_CONTEXT,
    ):
        topics_b = topic_scout.scout_topics(client)

    top_perf = content_intelligence.get_top_performers()
    bottom_perf = content_intelligence.get_bottom_performers()

    set_a = _topic_title_set(topics_a)
    set_b = _topic_title_set(topics_b)
    jac = jaccard_similarity(set_a, set_b)
    deltas = score_deltas(topics_a, topics_b)
    notes = qualitative_notes(topics_a, top_perf, bottom_perf)
    verdict_is_real, verdict_text = verdict(jac, notes)

    return {
        "topics_a": topics_a,
        "topics_b": topics_b,
        "jaccard": jac,
        "deltas": deltas,
        "notes": notes,
        "verdict_is_real": verdict_is_real,
        "verdict_text": verdict_text,
        "top_performers": top_perf,
        "bottom_performers": bottom_perf,
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _escape_md_table(text: str) -> str:
    """Escape pipe characters so they do not break Markdown table cells.

    Args:
        text: Raw cell text.

    Returns:
        Text with ``|`` replaced by ``\\|``.
    """
    return text.replace("|", "\\|")


def _topic_table(topics: list[dict[str, Any]], label: str) -> list[str]:
    """Render a Markdown table for one run's topics.

    Args:
        topics: List of topic dicts.
        label: Column header label (e.g. "Run A — with context").

    Returns:
        List of Markdown lines.
    """
    lines: list[str] = [f"### {label}", ""]
    if not topics:
        lines.append("_No topics returned._")
        lines.append("")
        return lines

    lines.append("| # | Score | Topic | Hook |")
    lines.append("|---|-------|-------|------|")
    for i, t in enumerate(topics, 1):
        score = t.get("total_score", "—")
        title = _escape_md_table(t.get("topic", "—"))
        hook = _escape_md_table((t.get("hook", "—") or "—")[:80])
        lines.append(f"| {i} | {score} | {title} | {hook}… |")
    lines.append("")
    return lines


def render_report(
    pairs: list[dict[str, Any]],
    timestamp: str,
) -> str:
    """Build the full Markdown report from one or more A/B pair results.

    Args:
        pairs: List of dicts as returned by ``run_ab_pair``.
        timestamp: ISO-ish timestamp string for the report header.

    Returns:
        Complete Markdown report as a single string.
    """
    lines: list[str] = [
        "# A/B Topic Scout Comparison Report",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Runs:** {len(pairs)}  ",
        "",
        "---",
        "",
    ]

    for idx, pair in enumerate(pairs, 1):
        if len(pairs) > 1:
            lines += [f"## Pair {idx}", ""]

        jac = pair["jaccard"]
        deltas = pair["deltas"]

        # Summary stats
        lines += [
            "## Summary Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Jaccard similarity | {jac:.3f} |",
        ]
        overall_avg = (
            sum(d["avg_delta"] for d in deltas.values()) / len(deltas)
            if deltas
            else 0.0
        )
        lines.append(f"| Avg score delta (across all dimensions) | {overall_avg:.3f} |")
        lines.append("")

        # Per-dimension deltas
        lines += [
            "## Per-Dimension Score Deltas",
            "",
            "| Dimension | Avg Δ | Max Δ |",
            "|-----------|-------|-------|",
        ]
        for dim, stats in deltas.items():
            lines.append(
                f"| {dim.replace('_', ' ').title()} "
                f"| {stats['avg_delta']:.3f} "
                f"| {stats['max_delta']:.3f} |"
            )
        lines.append("")

        # Side-by-side topic tables
        lines += ["## Topic Comparison", ""]
        lines += _topic_table(pair["topics_a"], "Run A — with GA4 performance context")
        lines += _topic_table(pair["topics_b"], "Run B — without performance context")

        # Qualitative notes
        lines += ["## Qualitative Notes", ""]
        for note in pair["notes"]:
            lines.append(f"- {note}")
        lines.append("")

        # Verdict
        lines += [
            "## Verdict",
            "",
            pair["verdict_text"],
            "",
        ]

        if len(pairs) > 1 and idx < len(pairs):
            lines += ["---", ""]

    # Aggregate verdict when running multiple pairs
    if len(pairs) > 1:
        real_count = sum(1 for p in pairs if p["verdict_is_real"])
        avg_jac = sum(p["jaccard"] for p in pairs) / len(pairs)
        lines += [
            "---",
            "",
            "## Aggregate Verdict (all pairs)",
            "",
            f"- Pairs run: {len(pairs)}",
            f"- Pairs where loop confirmed real: {real_count} / {len(pairs)}",
            f"- Average Jaccard similarity: {avg_jac:.3f}",
            "",
            (
                "**✅ AGGREGATE: Feedback loop CONFIRMED** "
                if real_count > len(pairs) / 2
                else "**❌ AGGREGATE: Feedback loop NOT confirmed**"
            ),
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def save_report(report: str, output_dir: Path) -> Path:
    """Save the Markdown report to *output_dir* with a timestamped filename.

    Args:
        report: Markdown report string.
        output_dir: Directory to write the file into (created if absent).

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"ab_topic_scout_comparison_{ts}.md"
    out_path.write_text(report, encoding="utf-8")
    return out_path


def save_raw_json(pairs: list[dict[str, Any]], output_dir: Path) -> Path:
    """Persist raw comparison data as JSON for downstream analysis.

    Args:
        pairs: List of A/B pair result dicts.
        output_dir: Directory to write the file into.

    Returns:
        Path to the written JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"ab_topic_scout_comparison_{ts}.json"

    # Serialise only JSON-safe data (ArticlePerformance dataclasses → dicts)
    def _serialisable(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return dataclasses.asdict(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")

    raw: list[dict[str, Any]] = []
    for pair in pairs:
        raw.append(
            {
                "topics_a": pair["topics_a"],
                "topics_b": pair["topics_b"],
                "jaccard": pair["jaccard"],
                "deltas": pair["deltas"],
                "notes": pair["notes"],
                "verdict_is_real": pair["verdict_is_real"],
                "top_performers": [
                    _serialisable(p) for p in pair["top_performers"]
                ],
                "bottom_performers": [
                    _serialisable(p) for p in pair["bottom_performers"]
                ],
            }
        )
    out_path.write_bytes(orjson.dumps(raw, option=orjson.OPT_INDENT_2))
    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the A/B Topic Scout comparison tool."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Number of A/B pairs to run (default: 1). Higher values increase "
        "statistical robustness.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("OUTPUT_DIR", "output")),
        help="Directory to save the Markdown report (default: output/).",
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    logger.info("Creating LLM client…")
    client = create_llm_client()

    pairs: list[dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        logger.info("Starting A/B pair %d of %d…", i, args.runs)
        pair = run_ab_pair(client, pair_index=i)
        pairs.append(pair)
        logger.info(
            "Pair %d complete — Jaccard=%.3f, verdict=%s",
            i,
            pair["jaccard"],
            "REAL" if pair["verdict_is_real"] else "NOT CONFIRMED",
        )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = render_report(pairs, timestamp)

    # Print to stdout
    print(report)

    # Save files
    report_path = save_report(report, args.output_dir)
    json_path = save_raw_json(pairs, args.output_dir)
    logger.info("Report saved to %s", report_path)
    logger.info("Raw JSON saved to %s", json_path)


if __name__ == "__main__":
    main()
