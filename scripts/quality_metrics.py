#!/usr/bin/env python3
"""Observability Metrics Pipeline — Article Quality Dashboard (Story 16.4).

Reads article evaluation logs and optional pipeline run metadata to produce
a quality dashboard JSON with:

- Article pass rates (first-attempt and overall)
- Common failure modes categorised from evaluation details
- Quality score trends (weekly averages, per-dimension)
- Revision loop frequency

Output is written to ``logs/quality_dashboard.json``.

Usage::

    from scripts.quality_metrics import QualityMetricsPipeline

    pipeline = QualityMetricsPipeline()
    dashboard = pipeline.run()
    # logs/quality_dashboard.json is now up-to-date
"""

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────

_PASS_THRESHOLD_PCT: int = 70  # Articles >= this percentage are "passing"

_WARN_PASS_RATE: float = 0.70
_CRITICAL_PASS_RATE: float = 0.50
_WARN_AVG_SCORE: float = 35.0
_CRITICAL_AVG_SCORE: float = 25.0
_WARN_DIMENSION_AVG: float = 6.0
_CRITICAL_DIMENSION_AVG: float = 4.0
_WARN_FAILURE_STREAK: int = 3
_CRITICAL_FAILURE_STREAK: int = 5

_DIMENSIONS: list[str] = [
    "opening_quality",
    "evidence_sourcing",
    "voice_consistency",
    "structure",
    "visual_engagement",
]


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────


class QualityMetricsPipeline:
    """Reads article evals and pipeline runs to build an observability dashboard.

    All metrics are deterministic — derived from evaluation logs, not LLMs.
    The pipeline fails gracefully when log files are absent or corrupt.
    """

    def __init__(
        self,
        evals_path: str | Path = "logs/article_evals.json",
        runs_path: str | Path = "logs/pipeline_runs.json",
        dashboard_path: str | Path = "logs/quality_dashboard.json",
    ) -> None:
        """Initialise the pipeline with configurable file paths.

        Args:
            evals_path: Path to article evaluations JSON (from ArticleEvaluator).
            runs_path: Path to pipeline run metadata JSON (optional).
            dashboard_path: Path to write the output dashboard JSON.
        """
        self.evals_path = Path(evals_path)
        self.runs_path = Path(runs_path)
        self.dashboard_path = Path(dashboard_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────────────────

    def _load_evals(self) -> list[dict[str, Any]]:
        """Load article evaluations from JSON log.

        Returns:
            List of eval records, or empty list if file absent or corrupt.
        """
        if not self.evals_path.exists():
            logger.info("Evals file not found: %s", self.evals_path)
            return []
        try:
            return orjson.loads(self.evals_path.read_bytes())
        except Exception as exc:
            logger.error("Failed to load evals from %s: %s", self.evals_path, exc)
            return []

    def _load_pipeline_runs(self) -> list[dict[str, Any]]:
        """Load pipeline run metadata from JSON log.

        Returns:
            List of run records, or empty list if file absent or corrupt.
        """
        if not self.runs_path.exists():
            logger.info("Pipeline runs file not found: %s", self.runs_path)
            return []
        try:
            return orjson.loads(self.runs_path.read_bytes())
        except Exception as exc:
            logger.error(
                "Failed to load pipeline runs from %s: %s", self.runs_path, exc
            )
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Metric computation
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_pass_rates(
        self,
        evals: list[dict[str, Any]],
        runs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate article pass rates.

        When ``pipeline_runs.json`` is available uses the ``status`` field.
        Falls back to ``percentage >= _PASS_THRESHOLD_PCT`` when runs are absent.

        Args:
            evals: List of article evaluation records.
            runs: List of pipeline run records (may be empty).

        Returns:
            Dict with ``total_articles``, ``first_attempt_publish_rate``, and
            ``overall_publish_rate``.
        """
        total = len(evals)
        if total == 0:
            return {
                "total_articles": 0,
                "first_attempt_publish_rate": 0.0,
                "overall_publish_rate": 0.0,
            }

        if runs:
            runs_by_file: dict[str, dict[str, Any]] = {
                r["article_filename"]: r for r in runs if "article_filename" in r
            }
            first_attempt = 0
            published = 0
            for e in evals:
                run = runs_by_file.get(e.get("article_filename", ""), {})
                if run.get("status") == "published":
                    published += 1
                    if run.get("retries", 0) == 0:
                        first_attempt += 1
        else:
            passing = [
                e
                for e in evals
                if self._is_valid_eval(e)
                and e.get("percentage", 0) >= _PASS_THRESHOLD_PCT
            ]
            first_attempt = len(passing)
            published = len(passing)

        return {
            "total_articles": total,
            "first_attempt_publish_rate": round(first_attempt / total, 4),
            "overall_publish_rate": round(published / total, 4),
        }

    def categorize_failure_modes(self, evals: list[dict[str, Any]]) -> dict[str, int]:
        """Categorise and count failure modes from evaluation details.

        Skips records that do not pass ``_is_valid_eval`` and logs a warning.

        Args:
            evals: List of article evaluation records.

        Returns:
            Dict mapping failure mode name to occurrence count.
        """
        counts: dict[str, int] = defaultdict(int)

        for eval_record in evals:
            if not self._is_valid_eval(eval_record):
                logger.warning(
                    "Skipping invalid eval record: %s",
                    eval_record.get("article_filename", "<unknown>"),
                )
                continue

            details = eval_record.get("details", {})
            scores = eval_record.get("scores", {})

            # Opening failures
            opening_detail = details.get("opening_quality", "")
            if "Banned opening" in opening_detail:
                counts["banned_opening"] += 1

            # Evidence failures
            evidence_detail = details.get("evidence_sourcing", "")
            m = re.search(r"(\d+) placeholders", evidence_detail)
            if m and int(m.group(1)) > 0:
                counts["unverified_claims"] += 1
            if "0 references" in evidence_detail:
                counts["missing_references"] += 1
            if scores.get("evidence_sourcing", 10) <= 4:
                counts["poor_evidence"] += 1

            # Voice failures
            voice_detail = details.get("voice_consistency", "")
            if "banned:" in voice_detail:
                counts["banned_phrases"] += 1
            if "American spellings" in voice_detail:
                counts["american_spellings"] += 1

            # Structure failures
            structure_detail = details.get("structure", "")
            if "missing:" in structure_detail:
                counts["missing_frontmatter_fields"] += 1
            if "references: no" in structure_detail:
                counts["missing_references"] += 1
            m = re.search(r"(\d+) words", structure_detail)
            if m and int(m.group(1)) < 800:
                counts["insufficient_word_count"] += 1

            # Visual failures
            visual_detail = details.get("visual_engagement", "")
            if "image: no" in visual_detail:
                counts["missing_image"] += 1
            if "chart embedded: no" in visual_detail:
                counts["missing_chart"] += 1

        return dict(counts)

    def compute_score_trends(
        self,
        evals: list[dict[str, Any]],
        runs: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
        """Compute weekly score trends and per-dimension trend arrays.

        Invalid or unparseable records are skipped with a warning.

        Args:
            evals: List of article evaluation records.
            runs: Optional list of pipeline run records for retry metrics.

        Returns:
            Tuple of (``weekly_trends`` list, ``dimension_trends`` dict).
            ``dimension_trends`` always contains all five dimension keys even
            when the lists are empty.
        """
        by_week: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for eval_record in evals:
            if not self._is_valid_eval(eval_record):
                logger.warning(
                    "Skipping invalid eval in score trends: %s",
                    eval_record.get("article_filename", "<unknown>"),
                )
                continue
            try:
                ts = datetime.fromisoformat(eval_record["timestamp"])
                week_key = ts.strftime("%G-W%V")
                by_week[week_key].append(eval_record)
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping eval with invalid timestamp: %s", exc)

        # Index runs by filename for per-week retry lookup
        runs_by_file: dict[str, dict[str, Any]] = (
            {r["article_filename"]: r for r in runs if "article_filename" in r}
            if runs
            else {}
        )

        dimension_weekly: dict[str, list[float]] = {d: [] for d in _DIMENSIONS}
        weekly_trends: list[dict[str, Any]] = []

        for week in sorted(by_week.keys()):
            week_evals = by_week[week]
            count = len(week_evals)
            if count == 0:
                continue

            avg_score = sum(e["total_score"] for e in week_evals) / count
            published = sum(
                1 for e in week_evals if e.get("percentage", 0) >= _PASS_THRESHOLD_PCT
            )
            failed = count - published
            top_failures = self._top_failures_for_evals(week_evals)

            week_retries = [
                runs_by_file.get(e.get("article_filename", ""), {}).get("retries", 0)
                for e in week_evals
            ]
            avg_retries = round(sum(week_retries) / len(week_retries), 2)

            weekly_trends.append(
                {
                    "week": week,
                    "articles_generated": count,
                    "published": published,
                    "failed": failed,
                    "avg_score": round(avg_score, 2),
                    "avg_retries": avg_retries,
                    "top_failure_modes": top_failures,
                }
            )

            for dim in _DIMENSIONS:
                dim_scores = [
                    e["scores"][dim] for e in week_evals if dim in e.get("scores", {})
                ]
                if dim_scores:
                    dimension_weekly[dim].append(
                        round(sum(dim_scores) / len(dim_scores), 2)
                    )

        return weekly_trends, dimension_weekly

    def compute_revision_frequency(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute revision loop frequency statistics from pipeline runs.

        Args:
            runs: List of pipeline run records.

        Returns:
            Dict with ``avg_retries``, ``zero_revision_pct``,
            ``one_revision_pct``, ``two_plus_revision_pct``, and
            ``top_revision_triggers``.
        """
        if not runs:
            return {
                "avg_retries": 0.0,
                "zero_revision_pct": 0.0,
                "one_revision_pct": 0.0,
                "two_plus_revision_pct": 0.0,
                "top_revision_triggers": [],
            }

        retries = [r.get("retries", 0) for r in runs]
        total = len(retries)
        avg = sum(retries) / total if total > 0 else 0.0
        zero = sum(1 for r in retries if r == 0)
        one = sum(1 for r in retries if r == 1)
        two_plus = sum(1 for r in retries if r >= 2)

        trigger_counts: dict[str, int] = defaultdict(int)
        for run in runs:
            for reason in run.get("failure_reasons", []):
                trigger_counts[reason] += 1

        top_triggers = sorted(
            trigger_counts, key=lambda k: trigger_counts[k], reverse=True
        )[:3]

        return {
            "avg_retries": round(avg, 2),
            "zero_revision_pct": round(zero / total * 100, 1) if total > 0 else 0.0,
            "one_revision_pct": round(one / total * 100, 1) if total > 0 else 0.0,
            "two_plus_revision_pct": (
                round(two_plus / total * 100, 1) if total > 0 else 0.0
            ),
            "top_revision_triggers": top_triggers,
        }

    def generate_alerts(
        self,
        summary: dict[str, Any],
        dimension_trends: dict[str, list[float]],
        failure_modes: dict[str, int],
    ) -> list[dict[str, str]]:
        """Generate alerts based on configured metric thresholds.

        Args:
            summary: Dashboard summary section.
            dimension_trends: Per-dimension weekly score arrays.
            failure_modes: Failure mode occurrence counts.

        Returns:
            List of alert dicts with ``type``, ``dimension``, ``message``,
            and ``severity`` keys.
        """
        alerts: list[dict[str, str]] = []

        # Pass rate alerts
        first_attempt_rate = summary.get("first_attempt_publish_rate", 1.0)
        if first_attempt_rate < _CRITICAL_PASS_RATE:
            alerts.append(
                {
                    "type": "pass_rate",
                    "dimension": "first_attempt_publish_rate",
                    "message": (
                        f"First-attempt publish rate critically low: "
                        f"{first_attempt_rate:.0%}"
                    ),
                    "severity": "critical",
                }
            )
        elif first_attempt_rate < _WARN_PASS_RATE:
            alerts.append(
                {
                    "type": "pass_rate",
                    "dimension": "first_attempt_publish_rate",
                    "message": (
                        f"First-attempt publish rate below target: "
                        f"{first_attempt_rate:.0%}"
                    ),
                    "severity": "warn",
                }
            )

        # Average score alerts
        avg_score = summary.get("avg_eval_score", 50.0)
        if avg_score < _CRITICAL_AVG_SCORE:
            alerts.append(
                {
                    "type": "quality_score",
                    "dimension": "avg_eval_score",
                    "message": f"Average eval score critically low: {avg_score:.1f}/50",
                    "severity": "critical",
                }
            )
        elif avg_score < _WARN_AVG_SCORE:
            alerts.append(
                {
                    "type": "quality_score",
                    "dimension": "avg_eval_score",
                    "message": (
                        f"Average eval score below threshold: {avg_score:.1f}/50"
                    ),
                    "severity": "warn",
                }
            )

        # Dimension-level alerts
        for dim, scores in dimension_trends.items():
            if not scores:
                continue
            avg_dim = sum(scores) / len(scores)
            if avg_dim < _CRITICAL_DIMENSION_AVG:
                alerts.append(
                    {
                        "type": "degradation",
                        "dimension": dim,
                        "message": (
                            f"{dim} scores critically low: avg {avg_dim:.1f}/10"
                        ),
                        "severity": "critical",
                    }
                )
            elif avg_dim < _WARN_DIMENSION_AVG:
                alerts.append(
                    {
                        "type": "degradation",
                        "dimension": dim,
                        "message": (
                            f"{dim} scores below threshold: avg {avg_dim:.1f}/10"
                        ),
                        "severity": "warn",
                    }
                )

        # Failure mode streak alerts
        for mode, count in failure_modes.items():
            if count >= _CRITICAL_FAILURE_STREAK:
                alerts.append(
                    {
                        "type": "failure_mode",
                        "dimension": mode,
                        "message": f"Failure mode '{mode}' occurred {count} times",
                        "severity": "critical",
                    }
                )
            elif count >= _WARN_FAILURE_STREAK:
                alerts.append(
                    {
                        "type": "failure_mode",
                        "dimension": mode,
                        "message": f"Failure mode '{mode}' occurred {count} times",
                        "severity": "warn",
                    }
                )

        return alerts

    # ─────────────────────────────────────────────────────────────────────────
    # Dashboard generation & persistence
    # ─────────────────────────────────────────────────────────────────────────

    def generate_dashboard(self) -> dict[str, Any]:
        """Build the complete dashboard dict without writing to disk.

        Returns:
            Dashboard dict matching the schema in
            ``skills/observability/SKILL.md``.
        """
        evals = self._load_evals()
        runs = self._load_pipeline_runs()

        pass_rates = self.calculate_pass_rates(evals, runs)
        failure_modes = self.categorize_failure_modes(evals)
        weekly_trends, dimension_trends = self.compute_score_trends(evals, runs)
        revision_freq = self.compute_revision_frequency(runs)

        valid_evals = [e for e in evals if self._is_valid_eval(e)]
        avg_score = (
            sum(e["total_score"] for e in valid_evals) / len(valid_evals)
            if valid_evals
            else 0.0
        )
        avg_pct = (
            sum(e["percentage"] for e in valid_evals) / len(valid_evals)
            if valid_evals
            else 0.0
        )

        summary: dict[str, Any] = {
            **pass_rates,
            "avg_eval_score": round(avg_score, 2),
            "avg_eval_percentage": round(avg_pct, 1),
        }

        alerts = self.generate_alerts(summary, dimension_trends, failure_modes)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
            "weekly_trends": weekly_trends,
            "dimension_trends": dimension_trends,
            "failure_mode_counts": failure_modes,
            "revision_frequency": revision_freq,
            "alerts": alerts,
        }

    def run(self) -> dict[str, Any]:
        """Run the pipeline: generate dashboard and persist to JSON.

        Returns:
            The dashboard dict (also written to ``dashboard_path``).
        """
        dashboard = self.generate_dashboard()
        self.dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        self.dashboard_path.write_bytes(
            orjson.dumps(dashboard, option=orjson.OPT_INDENT_2)
        )
        logger.info("Dashboard written to %s", self.dashboard_path)
        return dashboard

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_eval(record: dict[str, Any]) -> bool:
        """Return True if *record* contains the minimum required fields.

        Args:
            record: Candidate eval record.

        Returns:
            True when all required keys are present, False otherwise.
        """
        required = {"scores", "total_score", "percentage", "timestamp"}
        return isinstance(record, dict) and required.issubset(record.keys())

    def _top_failures_for_evals(self, evals: list[dict[str, Any]]) -> list[str]:
        """Return the top-3 failure mode names for a collection of evals.

        Args:
            evals: List of eval records.

        Returns:
            List of up to three failure mode names, sorted by frequency.
        """
        modes = self.categorize_failure_modes(evals)
        return sorted(modes, key=lambda k: modes[k], reverse=True)[:3]


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pipeline = QualityMetricsPipeline()
    result = pipeline.run()
    summary = result["summary"]
    print(
        f"Dashboard generated: {result['generated_at']}\n"
        f"  Total articles : {summary['total_articles']}\n"
        f"  Pass rate (1st): {summary['first_attempt_publish_rate']:.0%}\n"
        f"  Avg eval score : {summary['avg_eval_score']:.1f}/50\n"
        f"  Alerts         : {len(result['alerts'])}"
    )
    sys.exit(0)
