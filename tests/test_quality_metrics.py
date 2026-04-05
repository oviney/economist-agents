#!/usr/bin/env python3
"""Tests for Observability Metrics Pipeline (Story 16.4).

Validates the quality_metrics.py pipeline that reads article_evals.json
and outputs a quality_dashboard.json with pass rates, failure modes,
score trends, and revision loop frequency.
"""

from pathlib import Path

import orjson
import pytest

from scripts.quality_metrics import QualityMetricsPipeline

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_EVALS = [
    {
        "article_filename": "2026-W14-article-a.md",
        "timestamp": "2026-04-07T10:00:00",
        "scores": {
            "opening_quality": 8,
            "evidence_sourcing": 9,
            "voice_consistency": 10,
            "structure": 9,
            "visual_engagement": 8,
        },
        "total_score": 44,
        "max_score": 50,
        "percentage": 88,
        "details": {
            "opening_quality": "Opening has 3 data tokens",
            "evidence_sourcing": "5 references cited, 0 placeholders",
            "voice_consistency": "Clean voice",
            "structure": "4 headings, 1200 words, references: yes",
            "visual_engagement": "image: yes, chart embedded: yes",
        },
    },
    {
        "article_filename": "2026-W14-article-b.md",
        "timestamp": "2026-04-08T10:00:00",
        "scores": {
            "opening_quality": 2,
            "evidence_sourcing": 3,
            "voice_consistency": 6,
            "structure": 4,
            "visual_engagement": 4,
        },
        "total_score": 19,
        "max_score": 50,
        "percentage": 38,
        "details": {
            "opening_quality": "Banned opening detected: 'in today's world'",
            "evidence_sourcing": "0 references cited, 2 placeholders",
            "voice_consistency": "banned: ['game-changer'], American spellings: ['behavior']",
            "structure": "0 headings, 400 words, missing: ['layout', 'image'], references: no",
            "visual_engagement": "image: no, chart embedded: no",
        },
    },
    {
        "article_filename": "2026-W15-article-c.md",
        "timestamp": "2026-04-14T10:00:00",
        "scores": {
            "opening_quality": 6,
            "evidence_sourcing": 7,
            "voice_consistency": 8,
            "structure": 7,
            "visual_engagement": 6,
        },
        "total_score": 34,
        "max_score": 50,
        "percentage": 68,
        "details": {
            "opening_quality": "Opening has 1 data tokens",
            "evidence_sourcing": "3 references cited, 0 placeholders",
            "voice_consistency": "American spellings: ['organize']",
            "structure": "2 headings, 900 words, references: yes",
            "visual_engagement": "image: no, chart embedded: yes",
        },
    },
]

SAMPLE_RUNS = [
    {
        "article_filename": "2026-W14-article-a.md",
        "timestamp": "2026-04-07T09:50:00",
        "status": "published",
        "retries": 0,
        "failure_reasons": [],
    },
    {
        "article_filename": "2026-W14-article-b.md",
        "timestamp": "2026-04-08T09:50:00",
        "status": "failed",
        "retries": 2,
        "failure_reasons": ["gate_failure", "banned_phrases"],
    },
    {
        "article_filename": "2026-W15-article-c.md",
        "timestamp": "2026-04-14T09:50:00",
        "status": "published",
        "retries": 1,
        "failure_reasons": ["validation_failure"],
    },
]

INVALID_EVAL = {"article_filename": "bad.md", "timestamp": "broken"}


@pytest.fixture
def tmp_pipeline(tmp_path: Path) -> QualityMetricsPipeline:
    """Pipeline with temp file paths."""
    return QualityMetricsPipeline(
        evals_path=tmp_path / "article_evals.json",
        runs_path=tmp_path / "pipeline_runs.json",
        dashboard_path=tmp_path / "quality_dashboard.json",
    )


@pytest.fixture
def pipeline_with_evals(tmp_path: Path) -> QualityMetricsPipeline:
    """Pipeline pre-loaded with sample eval data."""
    evals_path = tmp_path / "article_evals.json"
    evals_path.write_bytes(orjson.dumps(SAMPLE_EVALS))
    return QualityMetricsPipeline(
        evals_path=evals_path,
        runs_path=tmp_path / "pipeline_runs.json",
        dashboard_path=tmp_path / "quality_dashboard.json",
    )


@pytest.fixture
def pipeline_with_runs(tmp_path: Path) -> QualityMetricsPipeline:
    """Pipeline pre-loaded with evals and run data."""
    evals_path = tmp_path / "article_evals.json"
    runs_path = tmp_path / "pipeline_runs.json"
    evals_path.write_bytes(orjson.dumps(SAMPLE_EVALS))
    runs_path.write_bytes(orjson.dumps(SAMPLE_RUNS))
    return QualityMetricsPipeline(
        evals_path=evals_path,
        runs_path=runs_path,
        dashboard_path=tmp_path / "quality_dashboard.json",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Loading & edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestDataLoading:
    def test_load_evals_returns_empty_when_file_missing(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        assert tmp_pipeline._load_evals() == []

    def test_load_pipeline_runs_returns_empty_when_file_missing(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        assert tmp_pipeline._load_pipeline_runs() == []

    def test_load_evals_returns_empty_on_corrupt_json(self, tmp_path: Path) -> None:
        evals_path = tmp_path / "article_evals.json"
        evals_path.write_text("NOT VALID JSON")
        pipeline = QualityMetricsPipeline(evals_path=evals_path)
        assert pipeline._load_evals() == []

    def test_load_pipeline_runs_returns_empty_on_corrupt_json(
        self, tmp_path: Path
    ) -> None:
        runs_path = tmp_path / "pipeline_runs.json"
        runs_path.write_text("{broken")
        pipeline = QualityMetricsPipeline(runs_path=runs_path)
        assert pipeline._load_pipeline_runs() == []

    def test_invalid_eval_record_skipped(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        """Records without required fields are skipped without raising."""
        result = tmp_pipeline.categorize_failure_modes([INVALID_EVAL, SAMPLE_EVALS[0]])
        # Should only process the valid eval, not raise
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════
# Pass rates
# ═══════════════════════════════════════════════════════════════════════════


class TestPassRates:
    def test_empty_evals_returns_zeros(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.calculate_pass_rates([], [])
        assert result["total_articles"] == 0
        assert result["first_attempt_publish_rate"] == 0.0
        assert result["overall_publish_rate"] == 0.0

    def test_pass_rate_from_eval_scores_no_runs(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        """Without pipeline runs, pass = percentage >= 70."""
        evals = pipeline_with_evals._load_evals()
        result = pipeline_with_evals.calculate_pass_rates(evals, [])
        # article-a (88%) passes, article-b (38%) fails, article-c (68%) fails
        assert result["total_articles"] == 3
        assert result["first_attempt_publish_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_pass_rate_uses_pipeline_runs_when_available(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        evals = pipeline_with_runs._load_evals()
        runs = pipeline_with_runs._load_pipeline_runs()
        result = pipeline_with_runs.calculate_pass_rates(evals, runs)
        # article-a: published + 0 retries → first attempt
        # article-b: failed → not published
        # article-c: published + 1 retry → published but not first attempt
        assert result["total_articles"] == 3
        assert result["first_attempt_publish_rate"] == pytest.approx(1 / 3, abs=0.01)
        assert result["overall_publish_rate"] == pytest.approx(2 / 3, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# Failure modes
# ═══════════════════════════════════════════════════════════════════════════


class TestFailureModes:
    def test_empty_evals_returns_empty_dict(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        assert tmp_pipeline.categorize_failure_modes([]) == {}

    def test_detects_banned_opening(self, tmp_pipeline: QualityMetricsPipeline) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("banned_opening", 0) >= 1

    def test_detects_unverified_claims(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("unverified_claims", 0) >= 1

    def test_detects_missing_references(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("missing_references", 0) >= 1

    def test_detects_banned_phrases(self, tmp_pipeline: QualityMetricsPipeline) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("banned_phrases", 0) >= 1

    def test_detects_american_spellings(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("american_spellings", 0) >= 1

    def test_detects_missing_frontmatter_fields(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[1]])
        assert result.get("missing_frontmatter_fields", 0) >= 1

    def test_clean_article_has_no_failures(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes([SAMPLE_EVALS[0]])
        assert sum(result.values()) == 0

    def test_multiple_evals_aggregate_counts(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.categorize_failure_modes(SAMPLE_EVALS)
        # article-b and article-c both have american_spellings
        assert result.get("american_spellings", 0) >= 2


# ═══════════════════════════════════════════════════════════════════════════
# Quality score trends
# ═══════════════════════════════════════════════════════════════════════════


class TestScoreTrends:
    def test_empty_evals_returns_empty_trends(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        weekly, dims = tmp_pipeline.compute_score_trends([])
        assert weekly == []
        assert all(v == [] for v in dims.values())

    def test_weekly_trends_grouped_by_iso_week(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        evals = pipeline_with_evals._load_evals()
        weekly, _ = pipeline_with_evals.compute_score_trends(evals)
        weeks = [w["week"] for w in weekly]
        # articles-a/b in W14, article-c in W15
        assert "2026-W15" in weeks
        assert len(weeks) == 2

    def test_weekly_trend_contains_required_keys(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        evals = pipeline_with_evals._load_evals()
        weekly, _ = pipeline_with_evals.compute_score_trends(evals)
        for week in weekly:
            assert "week" in week
            assert "articles_generated" in week
            assert "published" in week
            assert "failed" in week
            assert "avg_score" in week
            assert "top_failure_modes" in week

    def test_dimension_trends_have_all_five_dims(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        evals = pipeline_with_evals._load_evals()
        _, dims = pipeline_with_evals.compute_score_trends(evals)
        expected = {
            "opening_quality",
            "evidence_sourcing",
            "voice_consistency",
            "structure",
            "visual_engagement",
        }
        assert set(dims.keys()) == expected

    def test_dimension_trends_values_are_floats(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        evals = pipeline_with_evals._load_evals()
        _, dims = pipeline_with_evals.compute_score_trends(evals)
        for scores in dims.values():
            assert all(isinstance(v, float) for v in scores)

    def test_invalid_eval_timestamp_is_skipped(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        bad_eval = {**SAMPLE_EVALS[0], "timestamp": "not-a-date"}
        weekly, _ = tmp_pipeline.compute_score_trends([bad_eval])
        assert weekly == []


# ═══════════════════════════════════════════════════════════════════════════
# Revision loop frequency
# ═══════════════════════════════════════════════════════════════════════════


class TestRevisionFrequency:
    def test_empty_runs_returns_zeros(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        result = tmp_pipeline.compute_revision_frequency([])
        assert result["avg_retries"] == 0.0
        assert result["zero_revision_pct"] == 0.0

    def test_avg_retries_calculated(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        runs = pipeline_with_runs._load_pipeline_runs()
        result = pipeline_with_runs.compute_revision_frequency(runs)
        # retries: [0, 2, 1] → avg = 1.0
        assert result["avg_retries"] == pytest.approx(1.0, abs=0.01)

    def test_zero_revision_pct(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        runs = pipeline_with_runs._load_pipeline_runs()
        result = pipeline_with_runs.compute_revision_frequency(runs)
        # 1 of 3 has 0 retries → 33.3%
        assert result["zero_revision_pct"] == pytest.approx(33.3, abs=0.1)

    def test_top_revision_triggers(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        runs = pipeline_with_runs._load_pipeline_runs()
        result = pipeline_with_runs.compute_revision_frequency(runs)
        assert isinstance(result["top_revision_triggers"], list)

    def test_two_plus_revision_pct(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        runs = pipeline_with_runs._load_pipeline_runs()
        result = pipeline_with_runs.compute_revision_frequency(runs)
        # 1 of 3 has 2 retries → 33.3%
        assert result["two_plus_revision_pct"] == pytest.approx(33.3, abs=0.1)


# ═══════════════════════════════════════════════════════════════════════════
# Alerts
# ═══════════════════════════════════════════════════════════════════════════


class TestAlerts:
    def test_no_alerts_for_healthy_metrics(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {
            "first_attempt_publish_rate": 0.90,
            "avg_eval_score": 42.0,
        }
        dim_trends = {d: [8.0, 8.0] for d in ["opening_quality", "evidence_sourcing"]}
        alerts = tmp_pipeline.generate_alerts(summary, dim_trends, {})
        assert alerts == []

    def test_warn_alert_for_low_pass_rate(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.65, "avg_eval_score": 40.0}
        alerts = tmp_pipeline.generate_alerts(summary, {}, {})
        severities = {a["severity"] for a in alerts}
        assert "warn" in severities

    def test_critical_alert_for_very_low_pass_rate(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.40, "avg_eval_score": 40.0}
        alerts = tmp_pipeline.generate_alerts(summary, {}, {})
        severities = {a["severity"] for a in alerts}
        assert "critical" in severities

    def test_warn_alert_for_low_avg_score(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.90, "avg_eval_score": 30.0}
        alerts = tmp_pipeline.generate_alerts(summary, {}, {})
        assert any(a["dimension"] == "avg_eval_score" for a in alerts)

    def test_warn_alert_for_low_dimension(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.90, "avg_eval_score": 40.0}
        dim_trends = {"visual_engagement": [5.0, 5.0, 5.0]}
        alerts = tmp_pipeline.generate_alerts(summary, dim_trends, {})
        assert any(a["dimension"] == "visual_engagement" for a in alerts)

    def test_warn_alert_for_repeated_failure_mode(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.90, "avg_eval_score": 40.0}
        failure_modes = {"banned_phrases": 3}
        alerts = tmp_pipeline.generate_alerts(summary, {}, failure_modes)
        assert any(a["type"] == "failure_mode" for a in alerts)

    def test_alert_has_required_fields(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        summary = {"first_attempt_publish_rate": 0.40, "avg_eval_score": 20.0}
        alerts = tmp_pipeline.generate_alerts(summary, {}, {})
        for alert in alerts:
            assert "type" in alert
            assert "dimension" in alert
            assert "message" in alert
            assert "severity" in alert


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard generation
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardGeneration:
    def test_empty_data_generates_valid_dashboard(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        dashboard = tmp_pipeline.generate_dashboard()
        assert "generated_at" in dashboard
        assert "summary" in dashboard
        assert "weekly_trends" in dashboard
        assert "dimension_trends" in dashboard
        assert "failure_mode_counts" in dashboard
        assert "revision_frequency" in dashboard
        assert "alerts" in dashboard

    def test_dashboard_summary_keys(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        dashboard = pipeline_with_evals.generate_dashboard()
        summary = dashboard["summary"]
        assert "total_articles" in summary
        assert "first_attempt_publish_rate" in summary
        assert "overall_publish_rate" in summary
        assert "avg_eval_score" in summary
        assert "avg_eval_percentage" in summary

    def test_dashboard_summary_total_articles(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        dashboard = pipeline_with_evals.generate_dashboard()
        assert dashboard["summary"]["total_articles"] == 3

    def test_run_writes_dashboard_json(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        pipeline_with_evals.run()
        assert pipeline_with_evals.dashboard_path.exists()

    def test_run_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "logs" / "quality_dashboard.json"
        pipeline = QualityMetricsPipeline(
            evals_path=tmp_path / "evals.json",
            dashboard_path=nested,
        )
        pipeline.run()
        assert nested.exists()

    def test_dashboard_json_is_valid(
        self, pipeline_with_evals: QualityMetricsPipeline
    ) -> None:
        pipeline_with_evals.run()
        raw = pipeline_with_evals.dashboard_path.read_bytes()
        data = orjson.loads(raw)
        assert isinstance(data, dict)

    def test_dashboard_json_schema_compliance(
        self, pipeline_with_runs: QualityMetricsPipeline
    ) -> None:
        """Dashboard JSON must comply with internal data interchange standards."""
        pipeline_with_runs.run()
        data = orjson.loads(pipeline_with_runs.dashboard_path.read_bytes())

        # Top-level keys
        assert set(data.keys()) >= {
            "generated_at",
            "summary",
            "weekly_trends",
            "dimension_trends",
            "failure_mode_counts",
            "revision_frequency",
            "alerts",
        }

        # Summary keys
        assert set(data["summary"].keys()) >= {
            "total_articles",
            "first_attempt_publish_rate",
            "overall_publish_rate",
            "avg_eval_score",
            "avg_eval_percentage",
        }

        # Dimension trends has 5 dimensions
        assert set(data["dimension_trends"].keys()) == {
            "opening_quality",
            "evidence_sourcing",
            "voice_consistency",
            "structure",
            "visual_engagement",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_article_with_invalid_metrics_is_skipped(self, tmp_path: Path) -> None:
        """Invalid metric records are skipped for scoring but counted in total."""
        mixed_evals = [INVALID_EVAL, SAMPLE_EVALS[0]]
        evals_path = tmp_path / "article_evals.json"
        evals_path.write_bytes(orjson.dumps(mixed_evals))
        pipeline = QualityMetricsPipeline(
            evals_path=evals_path,
            dashboard_path=tmp_path / "quality_dashboard.json",
        )
        dashboard = pipeline.generate_dashboard()
        # total_articles reflects all evals loaded (valid + invalid) for traceability
        assert dashboard["summary"]["total_articles"] == 2
        # Weekly trends skip the invalid record — only 1 valid article contributes
        assert all(w["articles_generated"] <= 1 for w in dashboard["weekly_trends"])

    def test_missing_image_failure_detected(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        eval_with_no_image = {
            **SAMPLE_EVALS[0],
            "details": {
                **SAMPLE_EVALS[0]["details"],
                "visual_engagement": "image: no, chart embedded: yes",
            },
        }
        result = tmp_pipeline.categorize_failure_modes([eval_with_no_image])
        assert result.get("missing_image", 0) >= 1

    def test_pipeline_runs_with_missing_article_filename(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        runs = [{"status": "published", "retries": 0}]  # no article_filename
        result = tmp_pipeline.calculate_pass_rates(SAMPLE_EVALS, runs)
        assert isinstance(result["total_articles"], int)

    def test_all_invalid_evals_produces_zero_summary(self, tmp_path: Path) -> None:
        evals_path = tmp_path / "article_evals.json"
        evals_path.write_bytes(orjson.dumps([INVALID_EVAL, INVALID_EVAL]))
        pipeline = QualityMetricsPipeline(
            evals_path=evals_path,
            dashboard_path=tmp_path / "quality_dashboard.json",
        )
        dashboard = pipeline.generate_dashboard()
        assert dashboard["summary"]["avg_eval_score"] == 0.0

    def test_is_valid_eval_rejects_missing_fields(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        assert tmp_pipeline._is_valid_eval({}) is False
        assert tmp_pipeline._is_valid_eval({"scores": {}, "total_score": 0}) is False

    def test_is_valid_eval_accepts_complete_record(
        self, tmp_pipeline: QualityMetricsPipeline
    ) -> None:
        assert tmp_pipeline._is_valid_eval(SAMPLE_EVALS[0]) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
