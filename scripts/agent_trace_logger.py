#!/usr/bin/env python3
"""Agent Traceability Logger — Structured JSON logging for agent auditing.

Records each agent stage's inputs, outputs, and decisions in a versioned,
structured JSON format for transparency, accountability, and post-incident
analysis.

Acceptance Criteria Addressed:
- AC1: Log inputs, outputs, and decisions in structured JSON format
- AC2: Surface logs as GitHub issue comments when article fails
- AC4: Sanitize sensitive keys (privacy/security compliance)
- AC7: Schema version field for maintainable, version-controlled format

Usage:
    from scripts.agent_trace_logger import AgentTraceLogger

    tracer = AgentTraceLogger()
    tracer.log_agent_action(
        agent_name="TopicScout",
        stage="discover_topics",
        inputs={"focus_area": None},
        outputs={"topics": ["AI Testing"]},
        decision="generated 3 topic candidates",
    )
    comment_body = tracer.format_as_github_comment()
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Trace log schema version — increment this on any breaking format change.
# Documented change history must be kept in docs/conventions/ per AC7.
TRACE_SCHEMA_VERSION = "1.0"

# Keys whose values are automatically redacted for security/privacy compliance.
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "apikey",
        "token",
        "password",
        "secret",
        "authorization",
        "credential",
        "private_key",
    }
)


def _sanitize(obj: Any) -> Any:
    """Recursively redact sensitive keys from a nested dict/list.

    Args:
        obj: Any Python value to sanitize.

    Returns:
        A copy of *obj* with sensitive dict values replaced by "[REDACTED]".
    """
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _sanitize(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    return obj


class AgentTraceLogger:
    """Structured JSON trace logger for agent pipeline actions.

    Records inputs, outputs, and decisions for each agent stage
    in a versioned JSON format.  Designed to be embedded in the
    EconomistContentFlow (and other orchestrators) so that every
    stage's behaviour is auditable without post-hoc reconstruction.

    Thread-safety note: This class is NOT thread-safe.  Create one
    instance per flow execution.

    Example:
        tracer = AgentTraceLogger()
        tracer.log_agent_action(
            agent_name="TopicScout",
            stage="discover_topics",
            inputs={"focus_area": None},
            outputs={"topic_count": 3},
            decision="generated 3 topic candidates",
        )
        summary = tracer.get_trace_summary()
    """

    def __init__(self) -> None:
        """Initialize with an empty trace entry list."""
        self._entries: list[dict[str, Any]] = []

    # ── Core logging ────────────────────────────────────────────────────────

    def log_agent_action(
        self,
        agent_name: str,
        stage: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        decision: str = "",
        status: str = "success",
    ) -> dict[str, Any]:
        """Log a single agent action with structured metadata.

        Args:
            agent_name: Human-readable agent identifier (e.g. "TopicScout").
            stage: Pipeline stage name (e.g. "discover_topics").
            inputs: Agent input data — sensitive keys are auto-redacted.
            outputs: Agent output data — sensitive keys are auto-redacted.
            decision: Human-readable routing decision or outcome summary.
            status: One of "success", "revision", or "error".

        Returns:
            The structured log entry dict that was appended.

        Raises:
            ValueError: If *agent_name* or *stage* is empty.
        """
        if not agent_name:
            raise ValueError("agent_name must not be empty")
        if not stage:
            raise ValueError("stage must not be empty")

        entry: dict[str, Any] = {
            "schema_version": TRACE_SCHEMA_VERSION,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "agent_name": agent_name,
            "stage": stage,
            "status": status,
            "decision": decision,
            "inputs": _sanitize(inputs),
            "outputs": _sanitize(outputs),
        }
        self._entries.append(entry)
        logger.debug(
            "Agent trace: %s.%s → %s [%s]", agent_name, stage, decision, status
        )
        return entry

    # ── Retrieval ────────────────────────────────────────────────────────────

    def get_trace_summary(self) -> dict[str, Any]:
        """Return all trace entries with top-level metadata.

        Returns:
            dict containing:
                schema_version (str): Current log format version.
                entry_count (int): Number of logged actions.
                entries (list[dict]): Ordered list of action entries.
        """
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "entry_count": len(self._entries),
            "entries": list(self._entries),
        }

    # ── GitHub comment formatting ─────────────────────────────────────────

    def format_as_github_comment(self) -> str:
        """Format trace log as a GitHub issue comment body.

        Produces Markdown that renders cleanly in GitHub Issues, with
        collapsible <details> sections for large input/output payloads.

        Returns:
            Markdown-formatted string suitable for use as a GitHub comment body.
        """
        summary = self.get_trace_summary()
        _status_icon: dict[str, str] = {
            "success": "✅",
            "revision": "🔄",
            "error": "❌",
        }

        lines: list[str] = [
            "## 🔍 Agent Traceability Log",
            f"Schema version: `{summary['schema_version']}` · "
            f"Entries: `{summary['entry_count']}`",
            "",
        ]

        for entry in summary["entries"]:
            icon = _status_icon.get(entry.get("status", ""), "ℹ️")
            lines.append(f"### {icon} `{entry['agent_name']}` — {entry['stage']}")
            lines.append(f"- **Timestamp**: {entry['timestamp']}")
            lines.append(f"- **Decision**: {entry.get('decision', 'N/A')}")
            lines.append(f"- **Status**: `{entry.get('status', 'unknown')}`")
            lines.append("")
            lines.append("<details><summary>Inputs / Outputs</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(
                json.dumps(
                    {
                        "inputs": entry.get("inputs"),
                        "outputs": entry.get("outputs"),
                    },
                    indent=2,
                    default=str,
                )
            )
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        return "\n".join(lines)
