#!/usr/bin/env python3
"""Tests for the Agent Traceability Logger (Story 16.5).

Validates:
- Structured JSON logging of agent inputs/outputs/decisions
- Sensitive key redaction (security/privacy compliance)
- Trace summary retrieval
- GitHub comment formatting
- Error escalation on invalid operations
- Schema version presence (maintainability)
"""

import pytest

from scripts.agent_trace_logger import (
    TRACE_SCHEMA_VERSION,
    AgentTraceLogger,
    _sanitize,
)

# ═══════════════════════════════════════════════════════════════════════════
# Sanitization helper
# ═══════════════════════════════════════════════════════════════════════════


class TestSanitize:
    def test_non_sensitive_passthrough(self) -> None:
        obj = {"topic": "AI Testing", "score": 8.5}
        result = _sanitize(obj)
        assert result == obj

    def test_sensitive_key_redacted(self) -> None:
        obj = {"api_key": "sk-secret-123", "topic": "keep"}
        result = _sanitize(obj)
        assert result["api_key"] == "[REDACTED]"
        assert result["topic"] == "keep"

    def test_all_sensitive_keys_redacted(self) -> None:
        sensitive = {
            "api_key": "v1",
            "apikey": "v2",
            "token": "v3",
            "password": "v4",
            "secret": "v5",
            "authorization": "v6",
            "credential": "v7",
            "private_key": "v8",
        }
        result = _sanitize(sensitive)
        for k in sensitive:
            assert result[k] == "[REDACTED]", f"{k} was not redacted"

    def test_nested_dict_redaction(self) -> None:
        obj = {"outer": {"api_key": "secret", "safe": "value"}}
        result = _sanitize(obj)
        assert result["outer"]["api_key"] == "[REDACTED]"
        assert result["outer"]["safe"] == "value"

    def test_list_passthrough(self) -> None:
        obj = [{"topic": "A"}, {"topic": "B"}]
        result = _sanitize(obj)
        assert result == obj

    def test_list_with_sensitive_nested(self) -> None:
        obj = [{"password": "oops", "name": "keep"}]
        result = _sanitize(obj)
        assert result[0]["password"] == "[REDACTED]"
        assert result[0]["name"] == "keep"

    def test_non_dict_non_list_passthrough(self) -> None:
        assert _sanitize("hello") == "hello"
        assert _sanitize(42) == 42
        assert _sanitize(None) is None


# ═══════════════════════════════════════════════════════════════════════════
# AgentTraceLogger — log_agent_action
# ═══════════════════════════════════════════════════════════════════════════


class TestLogAgentAction:
    def test_returns_structured_entry(self) -> None:
        tracer = AgentTraceLogger()
        entry = tracer.log_agent_action(
            agent_name="TopicScout",
            stage="discover_topics",
            inputs={"focus_area": None},
            outputs={"topic_count": 3},
            decision="generated 3 topics",
        )
        assert entry["agent_name"] == "TopicScout"
        assert entry["stage"] == "discover_topics"
        assert entry["decision"] == "generated 3 topics"
        assert entry["status"] == "success"
        assert entry["inputs"] == {"focus_area": None}
        assert entry["outputs"] == {"topic_count": 3}
        assert "timestamp" in entry
        assert entry["schema_version"] == TRACE_SCHEMA_VERSION

    def test_custom_status_recorded(self) -> None:
        tracer = AgentTraceLogger()
        entry = tracer.log_agent_action(
            agent_name="Stage4Crew",
            stage="quality_gate",
            inputs={},
            outputs={},
            decision="revision needed",
            status="revision",
        )
        assert entry["status"] == "revision"

    def test_sensitive_inputs_redacted(self) -> None:
        tracer = AgentTraceLogger()
        entry = tracer.log_agent_action(
            agent_name="Adapter",
            stage="test",
            inputs={"api_key": "sk-secret", "topic": "AI"},
            outputs={},
        )
        assert entry["inputs"]["api_key"] == "[REDACTED]"
        assert entry["inputs"]["topic"] == "AI"

    def test_sensitive_outputs_redacted(self) -> None:
        tracer = AgentTraceLogger()
        entry = tracer.log_agent_action(
            agent_name="Adapter",
            stage="test",
            inputs={},
            outputs={"token": "tok-123", "result": "ok"},
        )
        assert entry["outputs"]["token"] == "[REDACTED]"
        assert entry["outputs"]["result"] == "ok"

    def test_empty_agent_name_raises(self) -> None:
        tracer = AgentTraceLogger()
        with pytest.raises(ValueError, match="agent_name"):
            tracer.log_agent_action(
                agent_name="",
                stage="discover_topics",
                inputs={},
                outputs={},
            )

    def test_empty_stage_raises(self) -> None:
        tracer = AgentTraceLogger()
        with pytest.raises(ValueError, match="stage"):
            tracer.log_agent_action(
                agent_name="TopicScout",
                stage="",
                inputs={},
                outputs={},
            )

    def test_multiple_entries_appended(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "stage1", {}, {})
        tracer.log_agent_action("B", "stage2", {}, {})
        tracer.log_agent_action("C", "stage3", {}, {})
        assert len(tracer._entries) == 3


# ═══════════════════════════════════════════════════════════════════════════
# AgentTraceLogger — get_trace_summary
# ═══════════════════════════════════════════════════════════════════════════


class TestGetTraceSummary:
    def test_empty_tracer_summary(self) -> None:
        tracer = AgentTraceLogger()
        summary = tracer.get_trace_summary()
        assert summary["schema_version"] == TRACE_SCHEMA_VERSION
        assert summary["entry_count"] == 0
        assert summary["entries"] == []

    def test_summary_contains_all_entries(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {}, {}, decision="d1")
        tracer.log_agent_action("B", "s2", {}, {}, decision="d2")

        summary = tracer.get_trace_summary()
        assert summary["entry_count"] == 2
        assert len(summary["entries"]) == 2
        assert summary["entries"][0]["agent_name"] == "A"
        assert summary["entries"][1]["agent_name"] == "B"

    def test_summary_does_not_mutate_internal_list(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {}, {})
        summary = tracer.get_trace_summary()
        summary["entries"].append({"bogus": True})
        # Internal list should not be affected
        assert len(tracer._entries) == 1

    def test_schema_version_present(self) -> None:
        tracer = AgentTraceLogger()
        summary = tracer.get_trace_summary()
        assert "schema_version" in summary
        assert summary["schema_version"] == "1.0"


# ═══════════════════════════════════════════════════════════════════════════
# AgentTraceLogger — format_as_github_comment
# ═══════════════════════════════════════════════════════════════════════════


class TestFormatAsGithubComment:
    def test_empty_tracer_produces_header(self) -> None:
        tracer = AgentTraceLogger()
        comment = tracer.format_as_github_comment()
        assert "Agent Traceability Log" in comment
        assert TRACE_SCHEMA_VERSION in comment

    def test_comment_contains_agent_names(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("TopicScout", "discover", {}, {}, decision="done")
        tracer.log_agent_action("EditorialBoard", "review", {}, {}, decision="voted")

        comment = tracer.format_as_github_comment()
        assert "TopicScout" in comment
        assert "EditorialBoard" in comment

    def test_comment_contains_decisions(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action(
            "Stage4Crew",
            "quality_gate",
            {},
            {},
            decision="revision — score below threshold",
            status="revision",
        )
        comment = tracer.format_as_github_comment()
        assert "revision — score below threshold" in comment

    def test_comment_contains_json_block(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {"key": "val"}, {"out": 1})
        comment = tracer.format_as_github_comment()
        assert "```json" in comment
        assert "key" in comment

    def test_success_status_icon(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {}, {}, status="success")
        comment = tracer.format_as_github_comment()
        assert "✅" in comment

    def test_revision_status_icon(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {}, {}, status="revision")
        comment = tracer.format_as_github_comment()
        assert "🔄" in comment

    def test_error_status_icon(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action("A", "s1", {}, {}, status="error")
        comment = tracer.format_as_github_comment()
        assert "❌" in comment

    def test_sensitive_data_not_in_comment(self) -> None:
        tracer = AgentTraceLogger()
        tracer.log_agent_action(
            "Adapter",
            "stage",
            inputs={"api_key": "super-secret-key"},
            outputs={},
        )
        comment = tracer.format_as_github_comment()
        assert "super-secret-key" not in comment
        assert "[REDACTED]" in comment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
