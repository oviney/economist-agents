#!/usr/bin/env python3
"""LLM variance check for Topic Scout.

Runs ``topic_scout.scout_topics()`` N times with the same performance
context and measures how stable the output is across runs.

Stability is measured via word-level Jaccard similarity between the
topic-title sets produced by each run.  A mean pairwise Jaccard above
:data:`REPRODUCIBILITY_VERDICT_THRESHOLD` is considered trustworthy.

Usage::

    .venv/bin/python scripts/topic_scout_reproducibility.py [--runs N]

Output: ``output/topic_scout_reproducibility_YYYYMMDD_HHMMSS.md``
        ``output/topic_scout_reproducibility_YYYYMMDD_HHMMSS.json``

Cost note: each run makes 2 LLM calls, so ``--runs 3`` ≈ 6 calls
(≈ $0.05–$0.15 on gpt-4o).
"""

from __future__ import annotations

import argparse
import logging
import re
import string
import sys
import time
from datetime import datetime
from itertools import chain
from pathlib import Path
from statistics import mean, stdev
from typing import Any
from unittest.mock import patch

import orjson

# Ensure scripts/ is on the import path when running directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_intelligence import get_performance_context
from topic_scout import create_client, scout_topics

logger = logging.getLogger(__name__)

#: Jaccard threshold above which output is considered reproducible.
REPRODUCIBILITY_VERDICT_THRESHOLD = 0.5

#: Maximum number of runs allowed via --runs.
MAX_RUNS = 10

# ──────────────────────────────────────────────────────────────────────────────
# Title normalisation helpers
# ──────────────────────────────────────────────────────────────────────────────

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "by",
        "for",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)


def _normalise_title(title: str) -> frozenset[str]:
    """Lower-case and tokenise a title into a frozen set of word tokens.

    Punctuation is replaced with spaces so that ``AI/ML`` splits into
    ``ai`` and ``ml`` rather than merging into ``aiml``.  Common
    stop-words are removed to reduce noise.

    Args:
        title: Raw topic title string.

    Returns:
        Frozen set of lowercase word tokens (stop-words excluded).
    """
    # Replace every punctuation character with a space so that
    # slash-separated terms (e.g. AI/ML) split correctly.
    text = title.lower().translate(
        str.maketrans(string.punctuation, " " * len(string.punctuation))
    )
    return frozenset(w for w in text.split() if w and w not in _STOP_WORDS)


# ──────────────────────────────────────────────────────────────────────────────
# Jaccard similarity
# ──────────────────────────────────────────────────────────────────────────────


def compute_title_jaccard(titles_a: list[str], titles_b: list[str]) -> float:
    """Compute word-level Jaccard similarity between two lists of topic titles.

    Each list of titles is treated as a bag of word-tokens after normalisation.
    Jaccard is then the intersection-over-union of those two bags.

    Args:
        titles_a: Topic titles from run A.
        titles_b: Topic titles from run B.

    Returns:
        Jaccard similarity in ``[0, 1]``.  Returns ``0.0`` if both sets
        are empty.
    """
    words_a: frozenset[str] = frozenset(
        chain.from_iterable(_normalise_title(t) for t in titles_a)
    )
    words_b: frozenset[str] = frozenset(
        chain.from_iterable(_normalise_title(t) for t in titles_b)
    )
    union = words_a | words_b
    if not union:
        return 0.0
    return len(words_a & words_b) / len(union)


def compute_jaccard_matrix(
    runs_topics: list[list[dict[str, Any]]],
) -> list[list[float]]:
    """Build an N×N pairwise Jaccard similarity matrix across runs.

    Args:
        runs_topics: List of topic lists, one per successful run.

    Returns:
        N×N list-of-lists with Jaccard scores; diagonal values are ``1.0``.
    """
    n = len(runs_topics)
    titles_per_run: list[list[str]] = [
        [t.get("topic", "") for t in run] for run in runs_topics
    ]
    matrix: list[list[float]] = []
    for i in range(n):
        row: list[float] = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            elif i > j:
                row.append(matrix[j][i])
            else:
                row.append(
                    compute_title_jaccard(titles_per_run[i], titles_per_run[j])
                )
        matrix.append(row)
    return matrix


def mean_pairwise_jaccard(matrix: list[list[float]]) -> float:
    """Return the mean of off-diagonal Jaccard scores.

    Args:
        matrix: N×N Jaccard matrix.

    Returns:
        Mean pairwise Jaccard; ``0.0`` when ``N < 2``.
    """
    n = len(matrix)
    if n < 2:
        return 0.0
    off_diag = [matrix[i][j] for i in range(n) for j in range(n) if i != j]
    return mean(off_diag)


# ──────────────────────────────────────────────────────────────────────────────
# Thematic stability
# ──────────────────────────────────────────────────────────────────────────────


def _extract_top_performer_keywords(
    perf_context: str,
    top_n: int = 3,
) -> list[str]:
    """Parse the performance-context Markdown to extract top-performer titles.

    Looks for table rows that follow the ``### Top performers`` heading.

    Args:
        perf_context: Markdown string from ``get_performance_context()``.
        top_n: Maximum number of top-performer titles to return.

    Returns:
        List of title strings (may be shorter than ``top_n``).
    """
    titles: list[str] = []
    in_top_section = False
    for line in perf_context.splitlines():
        if "Top performers" in line:
            in_top_section = True
            continue
        if not in_top_section:
            continue
        # Markdown table row: | score | pageviews | Title |
        match = re.match(r"\|\s*[\d.]+\s*\|\s*[\d,]+\s*\|\s*(.+?)\s*\|", line)
        if match:
            titles.append(match.group(1).strip())
            if len(titles) >= top_n:
                break
        elif line.startswith("### ") and titles:
            break  # Reached the next section header.
    return titles


def compute_thematic_stability(
    runs_topics: list[list[dict[str, Any]]],
    top_performer_titles: list[str],
) -> dict[str, float]:
    """Measure how often top-performer themes appear across runs.

    For each top-performer title, its keywords are matched against the
    topic titles and hooks produced by every run.  The result is the
    fraction of runs that mention at least one matching keyword.

    Args:
        runs_topics: List of topic lists, one per successful run.
        top_performer_titles: Top-performer titles from performance context.

    Returns:
        Dict mapping performer title → fraction of runs that match it
        (value in ``[0, 1]``).
    """
    n = len(runs_topics)
    if n == 0:
        return {}
    stability: dict[str, float] = {}
    for title in top_performer_titles:
        keywords = _normalise_title(title)
        if not keywords:
            stability[title] = 0.0
            continue
        hit_count = 0
        for run in runs_topics:
            run_words: set[str] = set()
            for topic in run:
                run_words.update(_normalise_title(topic.get("topic", "")))
                run_words.update(_normalise_title(topic.get("hook", "")))
            if keywords & run_words:
                hit_count += 1
        stability[title] = hit_count / n
    return stability


# ──────────────────────────────────────────────────────────────────────────────
# Score statistics and outlier detection
# ──────────────────────────────────────────────────────────────────────────────


def compute_score_stats(
    runs_topics: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    """Compute mean and std-dev of ``total_score`` values across all runs.

    Args:
        runs_topics: List of topic lists, one per successful run.

    Returns:
        Dict with keys:

        - ``all_scores``: flat list of every score
        - ``overall_mean``: mean across all runs and topics
        - ``overall_std``: std-dev across all runs and topics
        - ``per_run_mean``: list of per-run means
        - ``per_run_std``: list of per-run std-devs
    """
    all_scores: list[float] = []
    per_run_mean: list[float] = []
    per_run_std: list[float] = []
    for run in runs_topics:
        scores = [float(t.get("total_score", 0)) for t in run]
        all_scores.extend(scores)
        if scores:
            per_run_mean.append(mean(scores))
            per_run_std.append(stdev(scores) if len(scores) > 1 else 0.0)
        else:
            per_run_mean.append(0.0)
            per_run_std.append(0.0)
    return {
        "all_scores": all_scores,
        "overall_mean": mean(all_scores) if all_scores else 0.0,
        "overall_std": stdev(all_scores) if len(all_scores) > 1 else 0.0,
        "per_run_mean": per_run_mean,
        "per_run_std": per_run_std,
    }


def detect_outlier_runs(
    jaccard_matrix: list[list[float]],
) -> list[int]:
    """Identify run indices whose mean pairwise similarity is unusually low.

    A run is flagged as an outlier if its average Jaccard similarity to
    all other runs is more than one standard deviation below the grand
    mean.  Requires at least 3 runs; returns an empty list otherwise.

    Args:
        jaccard_matrix: N×N Jaccard matrix.

    Returns:
        List of 0-based run indices flagged as outliers.
    """
    n = len(jaccard_matrix)
    if n < 3:
        return []
    avg_per_run = [
        mean([jaccard_matrix[i][j] for j in range(n) if j != i])
        for i in range(n)
    ]
    grand_mean = mean(avg_per_run)
    grand_std = stdev(avg_per_run) if len(avg_per_run) > 1 else 0.0
    threshold = grand_mean - grand_std
    return [i for i, avg in enumerate(avg_per_run) if avg < threshold]


# ──────────────────────────────────────────────────────────────────────────────
# Report generation
# ──────────────────────────────────────────────────────────────────────────────


def format_jaccard_matrix(
    matrix: list[list[float]],
    run_labels: list[str],
) -> str:
    """Render the Jaccard matrix as a Markdown table.

    Args:
        matrix: N×N Jaccard scores.
        run_labels: Label for each run (e.g. ``["Run 1", "Run 2"]``).

    Returns:
        Markdown table string.
    """
    header = "| Run | " + " | ".join(run_labels) + " |"
    separator = "|-----|" + "|".join(["------" for _ in run_labels]) + "|"
    rows = []
    for i, label in enumerate(run_labels):
        cells = " | ".join(f"{matrix[i][j]:.3f}" for j in range(len(run_labels)))
        rows.append(f"| {label} | {cells} |")
    return "\n".join([header, separator] + rows)


def generate_report(
    *,
    n_requested: int,
    successful_runs: int,
    failed_runs: int,
    model: str,
    perf_context: str,
    top_performer_titles: list[str],
    runs_topics: list[list[dict[str, Any]]],
    run_timings: list[float],
    jaccard_matrix: list[list[float]],
    mean_jaccard: float,
    thematic_stability: dict[str, float],
    score_stats: dict[str, Any],
    outlier_run_indices: list[int],
    timestamp: str,
) -> str:
    """Assemble the full Markdown reproducibility report.

    Args:
        n_requested: Total runs requested.
        successful_runs: Number of runs that returned valid topics.
        failed_runs: Number of runs that failed (malformed JSON, etc.).
        model: LLM model name.
        perf_context: Raw performance context string injected into all runs.
        top_performer_titles: Extracted top-performer titles.
        runs_topics: List of topic lists per successful run.
        run_timings: Wall-clock seconds per successful run.
        jaccard_matrix: N×N Jaccard matrix (N = successful_runs).
        mean_jaccard: Mean pairwise Jaccard across all successful runs.
        thematic_stability: Fraction of runs matching each top performer.
        score_stats: Score distribution statistics dict.
        outlier_run_indices: 0-based indices of outlier runs.
        timestamp: ISO timestamp string for the report header.

    Returns:
        Markdown string ready to write to a file.
    """
    verdict = (
        "✅ **REPRODUCIBLE** — Output is stable enough to trust. "
        f"Mean Jaccard ({mean_jaccard:.3f}) exceeds the threshold "
        f"({REPRODUCIBILITY_VERDICT_THRESHOLD})."
        if mean_jaccard > REPRODUCIBILITY_VERDICT_THRESHOLD
        else "⚠️ **UNSTABLE** — Output varies too much across runs. "
        f"Mean Jaccard ({mean_jaccard:.3f}) is below the threshold "
        f"({REPRODUCIBILITY_VERDICT_THRESHOLD}). "
        "Single-run results should not be treated as reliable signal."
    )

    run_labels = [f"Run {i + 1}" for i in range(successful_runs)]
    lines: list[str] = []

    lines += [
        "# Topic Scout Reproducibility Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Model:** {model}",
        (
            f"**Runs requested:** {n_requested}"
            f" | **Successful:** {successful_runs}"
            f" | **Failed:** {failed_runs}"
        ),
        f"**Reproducibility threshold:** Jaccard > {REPRODUCIBILITY_VERDICT_THRESHOLD}",
        "",
        "---",
        "",
        "## Verdict",
        "",
        f"**Mean pairwise Jaccard similarity: {mean_jaccard:.3f}**",
        "",
        verdict,
        "",
        "---",
        "",
        "## Jaccard Similarity Matrix",
        "",
    ]

    if successful_runs >= 2:
        lines.append(format_jaccard_matrix(jaccard_matrix, run_labels))
    else:
        lines.append(
            "_Insufficient successful runs to compute a matrix (need ≥ 2)._"
        )

    lines += [
        "",
        "---",
        "",
        "## Thematic Stability (Top Performers)",
        "",
    ]

    if top_performer_titles and thematic_stability:
        lines += [
            "How often does a top-performer theme appear in scouted topics?",
            "",
            "| Top Performer | Runs Mentioning Theme | Stability |",
            "|---------------|----------------------|-----------|",
        ]
        for title, frac in thematic_stability.items():
            mentions = round(frac * successful_runs)
            lines.append(
                f"| {title[:60]} | {mentions}/{successful_runs} | {frac:.0%} |"
            )
    else:
        lines.append(
            "_No top-performer data available (database may be empty)._"
        )

    lines += [
        "",
        "---",
        "",
        "## Score Distribution",
        "",
    ]

    if score_stats["all_scores"]:
        lines += [
            (
                f"Overall — mean: **{score_stats['overall_mean']:.1f}**,"
                f" std-dev: **{score_stats['overall_std']:.1f}**"
            ),
            "",
            "| Run | Mean Score | Std Dev | Topics |",
            "|-----|-----------|---------|--------|",
        ]
        for i, (r_mean, r_std) in enumerate(
            zip(score_stats["per_run_mean"], score_stats["per_run_std"], strict=True)
        ):
            n_topics = len(runs_topics[i])
            lines.append(
                f"| {run_labels[i]} | {r_mean:.1f} | {r_std:.1f} | {n_topics} |"
            )
    else:
        lines.append("_No score data available._")

    lines += [
        "",
        "---",
        "",
        "## Outlier Detection",
        "",
    ]

    if outlier_run_indices:
        outlier_labels = ", ".join(run_labels[i] for i in outlier_run_indices)
        lines.append(
            f"The following runs produced topic sets that are outliers "
            f"(mean similarity > 1 std-dev below the grand mean): **{outlier_labels}**"
        )
        for i in outlier_run_indices:
            lines.append(f"\n**{run_labels[i]} topics:**")
            for topic in runs_topics[i]:
                lines.append(
                    f"- {topic.get('topic', '(unknown)')} "
                    f"(score: {topic.get('total_score', 'N/A')})"
                )
    elif successful_runs < 3:
        lines.append("_Need ≥ 3 successful runs to detect outliers._")
    else:
        lines.append("_No outlier runs detected._")

    lines += [
        "",
        "---",
        "",
        "## Topics per Run",
        "",
    ]

    for i, run in enumerate(runs_topics):
        timing_str = f" ({run_timings[i]:.1f}s)" if i < len(run_timings) else ""
        lines += [f"### {run_labels[i]}{timing_str}", ""]
        for topic in run:
            score = topic.get("total_score", "N/A")
            lines.append(
                f"- **{topic.get('topic', '(unknown)')}** (score: {score})"
            )
            hook = topic.get("hook", "")
            if hook:
                lines.append(f"  > {hook}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Performance Context (Identical Across All Runs)",
        "",
        perf_context,
    ]

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main orchestration
# ──────────────────────────────────────────────────────────────────────────────


def run_reproducibility_check(
    n_runs: int,
    output_dir: Path,
    client: Any | None = None,
) -> Path:
    """Execute the reproducibility check and write a Markdown report.

    Loads the performance context once, patches it into every call to
    ``scout_topics`` so all runs receive identical input, then computes
    similarity metrics and writes a report.

    Args:
        n_runs: Number of scout runs to execute.
        output_dir: Directory to write the Markdown report.
        client: LLM client instance; creates one via ``create_client()``
            if ``None``.

    Returns:
        Path to the generated Markdown report file.
    """
    if client is None:
        client = create_client()

    model: str = getattr(client, "model", "unknown")
    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # ── Step 1: Load performance context ONCE ────────────────────────────────
    print("📊 Loading performance context (once for all runs)...")
    perf_context = get_performance_context(top_limit=5, bottom_limit=5)
    top_performer_titles = _extract_top_performer_keywords(perf_context, top_n=3)
    print(f"   Top performers found: {len(top_performer_titles)}")

    # ── Step 2: Run scout N times ─────────────────────────────────────────────
    runs_topics: list[list[dict[str, Any]]] = []
    run_timings: list[float] = []
    failed_run_count = 0

    for i in range(n_runs):
        print(f"\n🔭 Run {i + 1}/{n_runs}...")
        t_start = time.monotonic()
        try:
            # Patch topic_scout.get_performance_context so every run sees
            # exactly the same performance context regardless of DB timing.
            with patch(
                "topic_scout.get_performance_context", return_value=perf_context
            ):
                topics = scout_topics(client)
        except Exception as exc:
            logger.warning("Run %d failed with error: %s", i + 1, exc)
            failed_run_count += 1
            continue

        elapsed = time.monotonic() - t_start

        if not topics:
            logger.warning(
                "Run %d returned no topics (likely a JSON parse failure).", i + 1
            )
            failed_run_count += 1
            continue

        runs_topics.append(topics)
        run_timings.append(elapsed)
        print(f"   ✅ {len(topics)} topics in {elapsed:.1f}s")

    successful_runs = len(runs_topics)
    print(
        f"\n📈 {successful_runs}/{n_runs} runs succeeded,"
        f" {failed_run_count} failed"
    )

    # ── Step 3: Compute metrics ───────────────────────────────────────────────
    jaccard_matrix = (
        compute_jaccard_matrix(runs_topics) if successful_runs >= 2 else []
    )
    mean_jaccard = mean_pairwise_jaccard(jaccard_matrix) if jaccard_matrix else 0.0
    thematic_stability = compute_thematic_stability(
        runs_topics, top_performer_titles
    )
    score_stats = compute_score_stats(runs_topics)
    outlier_indices = detect_outlier_runs(jaccard_matrix) if jaccard_matrix else []

    print(f"\n📊 Mean pairwise Jaccard similarity: {mean_jaccard:.3f}")
    verdict_word = (
        "REPRODUCIBLE"
        if mean_jaccard > REPRODUCIBILITY_VERDICT_THRESHOLD
        else "UNSTABLE"
    )
    print(f"   Verdict: {verdict_word} (threshold: {REPRODUCIBILITY_VERDICT_THRESHOLD})")

    # ── Step 4: Generate and save report ─────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"topic_scout_reproducibility_{ts_str}.md"

    report = generate_report(
        n_requested=n_runs,
        successful_runs=successful_runs,
        failed_runs=failed_run_count,
        model=model,
        perf_context=perf_context,
        top_performer_titles=top_performer_titles,
        runs_topics=runs_topics,
        run_timings=run_timings,
        jaccard_matrix=jaccard_matrix,
        mean_jaccard=mean_jaccard,
        thematic_stability=thematic_stability,
        score_stats=score_stats,
        outlier_run_indices=outlier_indices,
        timestamp=timestamp.isoformat(),
    )

    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 Report written to: {report_path}")

    # Save raw JSON data alongside the report for further analysis.
    json_path = report_path.with_suffix(".json")
    raw_data: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "model": model,
        "n_requested": n_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_run_count,
        "mean_pairwise_jaccard": mean_jaccard,
        "jaccard_matrix": jaccard_matrix,
        "thematic_stability": thematic_stability,
        "score_stats": {
            k: v for k, v in score_stats.items() if k != "all_scores"
        },
        "runs_topics": runs_topics,
    }
    json_path.write_bytes(orjson.dumps(raw_data, option=orjson.OPT_INDENT_2))
    print(f"📦 Raw data saved to: {json_path}")

    return report_path


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for the Topic Scout reproducibility check."""
    parser = argparse.ArgumentParser(
        description=(
            "Measure LLM variance in Topic Scout output by running it N times "
            "with the same performance context and computing Jaccard similarity."
        )
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        metavar="N",
        help=f"Number of scout runs (default: 3, max: {MAX_RUNS})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "output",
        help="Directory for the Markdown report (default: output/)",
    )
    args = parser.parse_args()

    if not 1 <= args.runs <= MAX_RUNS:
        parser.error(f"--runs must be between 1 and {MAX_RUNS}, got {args.runs}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    run_reproducibility_check(n_runs=args.runs, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
