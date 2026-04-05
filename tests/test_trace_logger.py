#!/usr/bin/env python3
"""
Tests for Agent Traceability Logging (Issue #120)

Covers acceptance criteria:
1. Log inputs, outputs, and decisions in structured JSON format
2. Agent logs included in GitHub issue comments on article failure
3. Logging must not degrade performance by more than 5% (<50ms/stage)
4. Logged data must comply with privacy/security standards
5. Invalid logging operations raise structured error reports
6. Log format includes schema version for maintainability
"""

import time
from pathlib import Path

import orjson
import pytest

# --- AC1: structured JSON trace records ---


class TestTraceRecord:
    """TraceLogger produces valid structured JSON records."""

    def test_trace_record_has_required_fields(self, tmp_path: Path) -> None:
        """Given an agent action, trace record contains all required fields."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="test-run-001", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_input("focus_area", None)
            t.log_output("topic_count", 5)
            t.log_output("top_topic", "AI Testing Paradox")

        records = logger.get_records()
        assert len(records) == 1
        rec = records[0]

        assert "trace_id" in rec
        assert "pipeline_run_id" in rec
        assert "stage" in rec
        assert "agent" in rec
        assert "timestamp" in rec
        assert "inputs" in rec
        assert "outputs" in rec
        assert "decisions" in rec
        assert "duration_ms" in rec
        assert "status" in rec

    def test_trace_record_values_correct(self, tmp_path: Path) -> None:
        """Trace record captures correct stage, agent, inputs, outputs."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="run-abc", log_dir=tmp_path)

        with logger.trace("editorial_review", agent="editorial_board") as t:
            t.log_input("topic_count", 5)
            t.log_output("top_topic", "AI Ethics")
            t.log_decision("consensus", True)

        rec = logger.get_records()[0]
        assert rec["stage"] == "editorial_review"
        assert rec["agent"] == "editorial_board"
        assert rec["pipeline_run_id"] == "run-abc"
        assert rec["inputs"]["topic_count"] == 5
        assert rec["outputs"]["top_topic"] == "AI Ethics"
        assert rec["decisions"]["consensus"] is True
        assert rec["status"] == "success"

    def test_trace_record_captures_duration(self, tmp_path: Path) -> None:
        """Trace record includes realistic duration_ms."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="run-dur", log_dir=tmp_path)

        with logger.trace("content_generation", agent="stage3_crew") as t:
            t.log_output("word_count", 1200)
            time.sleep(0.01)  # 10ms artificial delay

        rec = logger.get_records()[0]
        assert rec["duration_ms"] >= 10

    def test_multiple_stages_produce_multiple_records(self, tmp_path: Path) -> None:
        """Each stage call produces a separate trace record."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="multi-run", log_dir=tmp_path)

        stages = [
            ("topic_discovery", "topic_scout"),
            ("editorial_review", "editorial_board"),
            ("content_generation", "stage3_crew"),
            ("quality_gate", "stage4_reviewer"),
        ]
        for stage, agent in stages:
            with logger.trace(stage, agent=agent) as t:
                t.log_output("status", "ok")

        records = logger.get_records()
        assert len(records) == 4
        stage_names = [r["stage"] for r in records]
        assert "topic_discovery" in stage_names
        assert "quality_gate" in stage_names


# --- AC2: flush to file (for GitHub issue inclusion) ---


class TestTraceFlushToFile:
    """TraceLogger writes records to logs/pipeline_traces.json."""

    def test_flush_writes_json_file(self, tmp_path: Path) -> None:
        """flush() writes trace records to pipeline_traces.json as JSON array."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="flush-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 3)

        logger.flush()

        trace_file = tmp_path / "pipeline_traces.json"
        assert trace_file.exists()
        data = orjson.loads(trace_file.read_bytes())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["stage"] == "topic_discovery"

    def test_flush_appends_on_subsequent_runs(self, tmp_path: Path) -> None:
        """flush() appends new run records without overwriting existing ones."""
        from scripts.trace_logger import TraceLogger

        # First run
        logger1 = TraceLogger(run_id="run-1", log_dir=tmp_path)
        with logger1.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)
        logger1.flush()

        # Second run
        logger2 = TraceLogger(run_id="run-2", log_dir=tmp_path)
        with logger2.trace("quality_gate", agent="stage4_reviewer") as t:
            t.log_output("score", 92)
        logger2.flush()

        trace_file = tmp_path / "pipeline_traces.json"
        data = orjson.loads(trace_file.read_bytes())
        assert len(data) == 2
        run_ids = {r["pipeline_run_id"] for r in data}
        assert "run-1" in run_ids
        assert "run-2" in run_ids

    def test_format_pipeline_trace_markdown(self, tmp_path: Path) -> None:
        """format_as_markdown() returns a formatted table for GitHub issue comments."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="md-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)
            t.log_output("top_topic", "AI Testing")

        with logger.trace("quality_gate", agent="stage4_reviewer") as t:
            t.log_output("score", 45)
        logger.get_records()[-1]["status"] = "fail"  # simulate failure

        md = logger.format_as_markdown()

        assert "## Pipeline Trace" in md
        assert "topic_discovery" in md
        assert "topic_scout" in md
        assert "quality_gate" in md
        assert "stage4_reviewer" in md
        # Table format
        assert "|" in md


# --- AC3: performance budget ---


class TestTracePerformance:
    """Logging must not add more than 50ms per stage."""

    def test_single_trace_overhead_under_50ms(self, tmp_path: Path) -> None:
        """A single trace context manager adds <50ms overhead."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="perf-run", log_dir=tmp_path)

        start = time.perf_counter()
        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_input("focus_area", None)
            t.log_output("topic_count", 5)
            t.log_output("top_topic", "AI Testing")
            t.log_decision("selected", True)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"Trace overhead was {elapsed_ms:.1f}ms, expected <50ms"

    def test_flush_is_buffered_not_per_stage(self, tmp_path: Path) -> None:
        """No file I/O occurs during trace stages; only flush() writes disk."""
        from scripts.trace_logger import TraceLogger

        trace_file = tmp_path / "pipeline_traces.json"
        logger = TraceLogger(run_id="buf-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)

        # File should NOT exist until flush() is called
        assert not trace_file.exists(), "File written before flush() - not buffered"

        logger.flush()
        assert trace_file.exists()


# --- AC4: privacy and security ---


class TestTracePrivacy:
    """Logged data must comply with security and privacy standards."""

    def test_does_not_log_api_keys(self, tmp_path: Path) -> None:
        """Trace records must not contain API key values."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="priv-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            # Attempt to log something that looks like an API key
            t.log_input("api_key", "sk-secret-12345")
            t.log_output("topic_count", 5)

        logger.flush()
        content = (tmp_path / "pipeline_traces.json").read_text()
        assert "sk-secret-12345" not in content

    def test_does_not_log_full_article_text(self, tmp_path: Path) -> None:
        """Article full text is not stored in trace records."""
        from scripts.trace_logger import TraceLogger

        long_article = "This is the article body. " * 200  # ~5000 chars

        logger = TraceLogger(run_id="art-run", log_dir=tmp_path)

        with logger.trace("quality_gate", agent="stage4_reviewer") as t:
            t.log_input("article", long_article)
            t.log_output("score", 85)

        logger.flush()
        content = (tmp_path / "pipeline_traces.json").read_text()
        # Full article must not be stored verbatim
        assert long_article not in content
        # But word count summary should be there
        assert "word_count" in content or "article" in content

    def test_sensitive_key_names_are_redacted(self, tmp_path: Path) -> None:
        """Keys matching sensitive patterns (token, secret, password) are redacted."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="redact-run", log_dir=tmp_path)

        with logger.trace("publish", agent="publisher") as t:
            t.log_input("github_token", "ghp_supersecrettoken")
            t.log_input("normal_field", "safe_value")

        logger.flush()
        content = (tmp_path / "pipeline_traces.json").read_text()
        assert "ghp_supersecrettoken" not in content
        assert "safe_value" in content


# --- AC5: error escalation ---


class TestTraceErrorHandling:
    """Invalid logging operations raise structured error reports."""

    def test_exception_in_stage_sets_status_failed(self, tmp_path: Path) -> None:
        """When a stage raises an exception, trace record status is 'failed'."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="err-run", log_dir=tmp_path)

        with (
            pytest.raises(ValueError, match="stage failed"),
            logger.trace("content_generation", agent="stage3_crew") as t,
        ):
            t.log_input("topic", "AI Testing")
            raise ValueError("stage failed")

        records = logger.get_records()
        assert len(records) == 1
        assert records[0]["status"] == "failed"
        assert "error" in records[0]
        assert "stage failed" in records[0]["error"]

    def test_invalid_stage_name_raises_value_error(self, tmp_path: Path) -> None:
        """Blank stage name raises ValueError immediately."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="inv-run", log_dir=tmp_path)

        with (
            pytest.raises(ValueError, match="stage"),
            logger.trace("", agent="topic_scout"),
        ):
            pass

    def test_invalid_agent_name_raises_value_error(self, tmp_path: Path) -> None:
        """Blank agent name raises ValueError immediately."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="inv-run2", log_dir=tmp_path)

        with (
            pytest.raises(ValueError, match="agent"),
            logger.trace("topic_discovery", agent=""),
        ):
            pass


# --- AC6/AC7: schema version for maintainability ---


class TestTraceSchemaVersion:
    """Trace records include schema_version for format change tracking."""

    def test_records_include_schema_version(self, tmp_path: Path) -> None:
        """Each trace record includes schema_version field."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="schema-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)

        rec = logger.get_records()[0]
        assert "schema_version" in rec
        assert rec["schema_version"] == "1.0"

    def test_flushed_records_retain_schema_version(self, tmp_path: Path) -> None:
        """Schema version survives serialisation to JSON file."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="sv-flush", log_dir=tmp_path)
        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)
        logger.flush()

        data = orjson.loads((tmp_path / "pipeline_traces.json").read_bytes())
        assert data[0]["schema_version"] == "1.0"


# --- Integration: TraceLogger used in flow context ---


class TestTraceLoggerIntegration:
    """TraceLogger can be wired into the flow pipeline."""

    def test_get_summary_for_github_issue(self, tmp_path: Path) -> None:
        """get_summary() returns a dict suitable for inclusion in a GitHub issue."""
        from scripts.trace_logger import TraceLogger

        logger = TraceLogger(run_id="gh-run", log_dir=tmp_path)

        with logger.trace("topic_discovery", agent="topic_scout") as t:
            t.log_output("topic_count", 5)
            t.log_output("top_topic", "AI Testing")

        with logger.trace("quality_gate", agent="stage4_reviewer") as t:
            t.log_output("score", 40)
            t.log_decision("decision", "revision")

        summary = logger.get_summary()

        assert "pipeline_run_id" in summary
        assert "stages_completed" in summary
        assert summary["stages_completed"] == 2
        assert "trace_records" in summary
        assert len(summary["trace_records"]) == 2
