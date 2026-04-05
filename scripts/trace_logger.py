#!/usr/bin/env python3
"""
Agent Traceability Logging (Story #120)

Provides structured per-stage trace logging for every agent in the
Economist content pipeline.  Records inputs, outputs, and decisions
in a JSON schema, then flushes to ``logs/pipeline_traces.json`` in a
single buffered write at the end of the pipeline run.

Privacy rules (AC4):
- Keys whose names contain "token", "secret", "password", or "api_key"
  are replaced with "<REDACTED>" before storage.
- Values whose content exceeds ARTICLE_MAX_CHARS are truncated to a
  summary (word_count + first 100 chars).  This prevents full article
  text from polluting trace files.

Performance budget (AC3):
- All in-memory; only ``flush()`` performs file I/O.
- Target overhead: <50ms per stage.

Usage::

    from scripts.trace_logger import TraceLogger

    logger = TraceLogger(run_id="uuid")

    with logger.trace("topic_discovery", agent="topic_scout") as t:
        t.log_input("focus_area", None)
        topics = scout_topics(client)
        t.log_output("topic_count", len(topics))
        t.log_output("top_topic", topics[0]["topic"])

    logger.flush()  # write to logs/pipeline_traces.json
"""

import logging
import re
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import orjson

logger = logging.getLogger(__name__)

# Schema version — bump when the trace record structure changes.
SCHEMA_VERSION = "1.0"

# Sensitive key pattern (case-insensitive, word-boundary match).
_SENSITIVE_PATTERN = re.compile(r"(token|secret|password|api_key)", re.IGNORECASE)

# Article text that exceeds this char count is stored as a summary only.
ARTICLE_MAX_CHARS = 500


def _redact(key: str, value: Any) -> Any:
    """Return redacted value for sensitive keys, otherwise return value unchanged.

    Args:
        key:   Field name to check.
        value: Original value.

    Returns:
        ``"<REDACTED>"`` if the key matches a sensitive pattern, else
        the original value — but with long article text summarised.
    """
    if _SENSITIVE_PATTERN.search(key):
        return "<REDACTED>"
    if isinstance(value, str) and len(value) > ARTICLE_MAX_CHARS:
        word_count = len(value.split())
        return {
            "word_count": word_count,
            "preview": value[:100],
            "_truncated": True,
        }
    return value


class _TraceContext:
    """Mutable trace context passed inside the ``logger.trace()`` block.

    Users call ``log_input``, ``log_output``, and ``log_decision`` to
    populate the record incrementally.
    """

    def __init__(self, stage: str, agent: str, run_id: str) -> None:
        """Initialise a new trace context for a single stage.

        Args:
            stage:  Pipeline stage name (e.g. ``"topic_discovery"``).
            agent:  Agent identifier (e.g. ``"topic_scout"``).
            run_id: Parent pipeline run UUID.
        """
        self.stage = stage
        self.agent = agent
        self.run_id = run_id
        self.inputs: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}
        self.decisions: dict[str, Any] = {}
        self.status: str = "success"
        self.error: str | None = None

    def log_input(self, key: str, value: Any) -> None:
        """Record an input field for this stage.

        Args:
            key:   Input field name.
            value: Input value (redacted/truncated as needed).
        """
        self.inputs[key] = _redact(key, value)

    def log_output(self, key: str, value: Any) -> None:
        """Record an output field for this stage.

        Args:
            key:   Output field name.
            value: Output value (redacted/truncated as needed).
        """
        self.outputs[key] = _redact(key, value)

    def log_decision(self, key: str, value: Any) -> None:
        """Record a decision made during this stage.

        Args:
            key:   Decision field name.
            value: Decision value.
        """
        self.decisions[key] = _redact(key, value)


class TraceLogger:
    """Buffered, append-only logger for agent pipeline traces.

    One ``TraceLogger`` instance lives for the duration of a single
    pipeline run.  All trace records are kept in memory; call
    ``flush()`` once to write them to disk.

    Args:
        run_id:  Unique identifier for this pipeline run.  Defaults to
                 a freshly generated UUID4 if not provided.
        log_dir: Directory for ``pipeline_traces.json``.  Defaults to
                 ``logs/`` relative to the project root.
    """

    def __init__(
        self,
        run_id: str | None = None,
        log_dir: Path | str | None = None,
    ) -> None:
        """Initialise the logger for a new pipeline run."""
        self._run_id: str = run_id or str(uuid.uuid4())
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / "logs"
        self._log_dir = Path(log_dir)
        self._records: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Context manager interface
    # ------------------------------------------------------------------

    @contextmanager
    def trace(self, stage: str, *, agent: str) -> Generator[_TraceContext, None, None]:
        """Context manager that wraps a single pipeline stage.

        Starts timing on entry, records the trace on exit (even if the
        block raises).

        Args:
            stage: Pipeline stage name.  Must be non-empty.
            agent: Agent identifier.  Must be non-empty.

        Yields:
            A :class:`_TraceContext` the caller uses to log fields.

        Raises:
            ValueError: If ``stage`` or ``agent`` is blank.
            Exception:  Any exception raised inside the block is
                        recorded and re-raised unchanged.
        """
        if not stage:
            raise ValueError("stage name must not be empty")
        if not agent:
            raise ValueError("agent name must not be empty")

        ctx = _TraceContext(stage=stage, agent=agent, run_id=self._run_id)
        start_ts = datetime.now(UTC)
        start_ns = __import__("time").perf_counter_ns()

        try:
            yield ctx
        except Exception as exc:
            ctx.status = "failed"
            ctx.error = str(exc)
            raise
        finally:
            elapsed_ms = (__import__("time").perf_counter_ns() - start_ns) // 1_000_000
            record: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "trace_id": str(uuid.uuid4()),
                "pipeline_run_id": self._run_id,
                "stage": ctx.stage,
                "agent": ctx.agent,
                "timestamp": start_ts.isoformat(),
                "inputs": ctx.inputs,
                "outputs": ctx.outputs,
                "decisions": ctx.decisions,
                "duration_ms": elapsed_ms,
                "status": ctx.status,
            }
            if ctx.error is not None:
                record["error"] = ctx.error
            self._records.append(record)
            logger.debug(
                "trace stage=%s agent=%s status=%s duration_ms=%d",
                stage,
                agent,
                ctx.status,
                elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_records(self) -> list[dict[str, Any]]:
        """Return all in-memory trace records for this run.

        Returns:
            List of trace record dicts (mutable reference).
        """
        return self._records

    def get_summary(self) -> dict[str, Any]:
        """Return a compact summary dict suitable for GitHub issue bodies.

        Returns:
            Dict with ``pipeline_run_id``, ``stages_completed``, and
            ``trace_records`` (list of all records).
        """
        return {
            "pipeline_run_id": self._run_id,
            "stages_completed": len(self._records),
            "trace_records": self._records,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def flush(self) -> None:
        """Append all buffered records to ``pipeline_traces.json``.

        Creates the log directory and file if they do not exist.
        Existing records from previous runs are preserved (append-only).
        Uses ``orjson`` for fast, correct serialisation.
        """
        self._log_dir.mkdir(parents=True, exist_ok=True)
        trace_file = self._log_dir / "pipeline_traces.json"

        existing: list[dict[str, Any]] = []
        if trace_file.exists():
            try:
                existing = orjson.loads(trace_file.read_bytes())
            except Exception:
                existing = []

        combined = existing + self._records
        trace_file.write_bytes(orjson.dumps(combined, option=orjson.OPT_INDENT_2))
        logger.info(
            "flushed %d trace records to %s (total=%d)",
            len(self._records),
            trace_file,
            len(combined),
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_as_markdown(self) -> str:
        """Format trace records as a Markdown table for GitHub issue comments.

        Returns:
            Markdown string with a ``## Pipeline Trace`` section and a
            table row per stage.
        """
        lines: list[str] = [
            "## Pipeline Trace",
            "",
            "| Stage | Agent | Duration | Status | Key Output |",
            "|-------|-------|----------|--------|------------|",
        ]
        for rec in self._records:
            duration = f"{rec['duration_ms'] / 1000:.1f}s"
            key_output = _first_output_summary(rec["outputs"])
            lines.append(
                f"| {rec['stage']} | {rec['agent']} "
                f"| {duration} | {rec['status']} | {key_output} |"
            )
        return "\n".join(lines)


def _first_output_summary(outputs: dict[str, Any]) -> str:
    """Return a short human-readable summary of the first output field.

    Args:
        outputs: Outputs dict from a trace record.

    Returns:
        Short string, or ``"—"`` if outputs is empty.
    """
    if not outputs:
        return "—"
    key, val = next(iter(outputs.items()))
    if isinstance(val, dict) and val.get("_truncated"):
        return f"{val['word_count']} words"
    return f"{key}={val}"
