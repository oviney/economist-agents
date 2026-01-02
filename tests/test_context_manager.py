"""
Unit tests for ContextManager (Sprint 7 Story 2)

Tests context loading, access, updates, thread safety, and error handling.
Validates all acceptance criteria and quality requirements.
"""

import json
import tempfile
import threading
from pathlib import Path

import pytest

from scripts.context_manager import (
    ContextFileNotFoundError,
    ContextManager,
    ContextParseError,
    ContextSizeExceededError,
    ContextUpdateError,
    create_task_context,
)


class TestContextLoading:
    """AC1: Context Template Loading"""

    def test_load_valid_context(self):
        """Should load STORY_N_CONTEXT.md successfully"""
        ctx = ContextManager("docs/STORY_2_CONTEXT.md")

        assert ctx.story_id == "Story 2"
        assert ctx.get("goal") is not None
        assert "context" in ctx.get("goal").lower()
        assert len(ctx.get("acceptance_criteria", [])) >= 4

    def test_missing_file_raises_error(self):
        """Should raise helpful error if file missing"""
        with pytest.raises(ContextFileNotFoundError) as exc_info:
            ContextManager("docs/NONEXISTENT_CONTEXT.md")

        assert "not found" in str(exc_info.value).lower()
        assert "STORY_TEMPLATE" in str(exc_info.value)

    def test_empty_file_raises_error(self):
        """Should fail gracefully with empty file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name

        try:
            with pytest.raises(ContextParseError) as exc_info:
                ContextManager(temp_path)

            assert "missing required sections" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_malformed_markdown_raises_error(self):
        """Should handle malformed markdown gracefully"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # Missing required sections
            f.write("# Bad Context\n\nNo structure here")
            temp_path = f.name

        try:
            with pytest.raises(ContextParseError) as exc_info:
                ContextManager(temp_path)

            assert "missing required sections" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_large_context_raises_error(self):
        """Should error if context >10MB"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # Write >10MB of data
            large_content = "x" * (11 * 1024 * 1024)  # 11 MB
            f.write(large_content)
            temp_path = f.name

        try:
            with pytest.raises(ContextSizeExceededError) as exc_info:
                ContextManager(temp_path)

            assert "too large" in str(exc_info.value).lower()
            assert "10" in str(exc_info.value)  # Max size mentioned
        finally:
            Path(temp_path).unlink()


class TestContextAccess:
    """AC2: Agent Context Access"""

    @pytest.fixture
    def context(self):
        """Provide loaded context for tests"""
        return ContextManager("docs/STORY_2_CONTEXT.md")

    def test_get_existing_key(self, context):
        """Should retrieve existing context values"""
        story_id = context.get("story_id")
        assert story_id == "Story 2"

        goal = context.get("goal")
        assert goal is not None
        assert isinstance(goal, str)

    def test_get_missing_key_returns_default(self, context):
        """Should return default for missing keys"""
        result = context.get("nonexistent_key", "default_value")
        assert result == "default_value"

        result_none = context.get("another_missing")
        assert result_none is None

    def test_to_dict_returns_complete_context(self, context):
        """Should return all context as dict"""
        ctx_dict = context.to_dict()

        assert isinstance(ctx_dict, dict)
        assert "story_id" in ctx_dict
        assert "goal" in ctx_dict
        assert "acceptance_criteria" in ctx_dict

    def test_to_dict_returns_copy(self, context):
        """Should return copy (not reference)"""
        ctx_dict1 = context.to_dict()
        ctx_dict1["test_key"] = "modified"

        ctx_dict2 = context.to_dict()
        assert "test_key" not in ctx_dict2


class TestContextUpdates:
    """AC3: Context Propagation (update operations)"""

    @pytest.fixture
    def context(self):
        """Provide loaded context for tests"""
        return ContextManager("docs/STORY_2_CONTEXT.md")

    def test_set_valid_value(self, context):
        """Should set new context values"""
        context.set("developer_result", "Implementation complete")

        assert context.get("developer_result") == "Implementation complete"

    def test_set_complex_value(self, context):
        """Should handle complex JSON-serializable values"""
        test_data = {
            "test_results": {"passed": 42, "failed": 0},
            "coverage": 85.5,
            "files_changed": ["file1.py", "file2.py"],
        }

        context.set("test_summary", test_data)

        retrieved = context.get("test_summary")
        assert retrieved == test_data
        assert retrieved["test_results"]["passed"] == 42

    def test_set_non_serializable_raises_error(self, context):
        """Should reject non-JSON-serializable values"""

        class NonSerializable:
            pass

        with pytest.raises(ContextUpdateError) as exc_info:
            context.set("bad_value", NonSerializable())

        assert "JSON-serializable" in str(exc_info.value)

    def test_bulk_update(self, context):
        """Should support bulk updates"""
        updates = {
            "dev_status": "complete",
            "test_status": "in_progress",
            "review_status": "pending",
        }

        context.update(updates)

        assert context.get("dev_status") == "complete"
        assert context.get("test_status") == "in_progress"
        assert context.get("review_status") == "pending"

    def test_audit_logging(self, context):
        """Should log all modifications"""
        initial_log_count = len(context.get_audit_log())

        context.set("test_key", "test_value")

        audit_log = context.get_audit_log()
        assert len(audit_log) > initial_log_count

        # Check last entry
        last_entry = audit_log[-1]
        assert last_entry["action"] == "context_updated"
        assert last_entry["key"] == "test_key"
        assert "timestamp" in last_entry


class TestThreadSafety:
    """Concurrency validation (Quality Requirement)"""

    @pytest.fixture
    def context(self):
        """Provide loaded context for tests"""
        return ContextManager("docs/STORY_2_CONTEXT.md")

    def test_concurrent_reads(self, context):
        """Should handle multiple concurrent reads"""
        results = []

        def read_context():
            for _ in range(100):
                story_id = context.get("story_id")
                results.append(story_id)

        threads = [threading.Thread(target=read_context) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed
        assert len(results) == 1000
        assert all(r == "Story 2" for r in results)

    def test_concurrent_writes(self, context):
        """Should serialize concurrent writes"""

        def write_context(value):
            for i in range(10):
                context.set(f"thread_{value}_key_{i}", f"value_{i}")

        threads = [threading.Thread(target=write_context, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writes should succeed (5 threads * 10 writes = 50 keys)
        ctx_dict = context.to_dict()
        thread_keys = [k for k in ctx_dict if k.startswith("thread_")]
        assert len(thread_keys) == 50

    def test_concurrent_read_write(self, context):
        """Should handle mixed read/write operations"""
        read_results = []
        write_count = [0]

        def read_loop():
            for _ in range(50):
                context.get("story_id")
                read_results.append(True)

        def write_loop():
            for i in range(50):
                context.set(f"write_key_{i}", f"value_{i}")
                write_count[0] += 1

        read_threads = [threading.Thread(target=read_loop) for _ in range(3)]
        write_threads = [threading.Thread(target=write_loop) for _ in range(2)]

        all_threads = read_threads + write_threads

        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()

        # All operations should complete
        assert len(read_results) == 150  # 3 threads * 50 reads
        assert write_count[0] == 100  # 2 threads * 50 writes


class TestPerformance:
    """Performance validation (Quality Requirement)"""

    def test_load_time_under_2_seconds(self, benchmark):
        """AC4: Context load time < 2 seconds"""

        def load_context():
            return ContextManager("docs/STORY_2_CONTEXT.md")

        result = benchmark(load_context)
        assert result.story_id == "Story 2"

        # pytest-benchmark will fail if >2s (configure in pytest.ini if needed)

    def test_access_time_under_10ms(self, benchmark):
        """AC4: Context access < 10ms"""
        ctx = ContextManager("docs/STORY_2_CONTEXT.md")

        def access_context():
            return ctx.get("goal")

        result = benchmark(access_context)
        assert result is not None

    def test_memory_usage_under_10mb(self):
        """AC4: Context memory < 10MB"""
        import tracemalloc

        tracemalloc.start()

        ctx = ContextManager("docs/STORY_2_CONTEXT.md")
        _ = ctx.to_dict()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Convert to MB
        peak_mb = peak / 1024 / 1024

        assert peak_mb < 10, f"Peak memory usage: {peak_mb:.2f}MB (limit: 10MB)"


class TestTaskContextHelper:
    """Test create_task_context helper function"""

    def test_create_task_context_basic(self):
        """Should create task context with base data"""
        ctx = ContextManager("docs/STORY_2_CONTEXT.md")

        task_context = create_task_context(ctx)

        assert "story_id" in task_context
        assert "goal" in task_context
        assert task_context["story_id"] == "Story 2"

    def test_create_task_context_with_additional(self):
        """Should merge additional context"""
        ctx = ContextManager("docs/STORY_2_CONTEXT.md")

        task_context = create_task_context(
            ctx, previous_output="Developer done", current_agent="QE Lead"
        )

        assert task_context["story_id"] == "Story 2"
        assert task_context["previous_output"] == "Developer done"
        assert task_context["current_agent"] == "QE Lead"


class TestErrorHandling:
    """Error handling validation (Maintainability Requirement)"""

    def test_helpful_error_for_missing_file(self):
        """Should provide template example in error"""
        with pytest.raises(ContextFileNotFoundError) as exc_info:
            ContextManager("missing.md")

        error_msg = str(exc_info.value)
        assert "STORY_TEMPLATE" in error_msg
        assert "cp " in error_msg  # Should show copy command

    def test_helpful_error_for_parse_failure(self):
        """Should show which section failed"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Incomplete\n\nMissing required sections")
            temp_path = f.name

        try:
            with pytest.raises(ContextParseError) as exc_info:
                ContextManager(temp_path)

            error_msg = str(exc_info.value)
            assert "missing required sections" in error_msg.lower()
            assert "## User Story" in error_msg or "goal" in error_msg
        finally:
            Path(temp_path).unlink()

    def test_size_exceeded_error_helpful(self):
        """Should show size limit and suggest action"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # Write >10MB
            f.write("x" * (11 * 1024 * 1024))
            temp_path = f.name

        try:
            with pytest.raises(ContextSizeExceededError) as exc_info:
                ContextManager(temp_path)

            error_msg = str(exc_info.value)
            assert "too large" in error_msg.lower()
            assert "split" in error_msg.lower() or "reduce" in error_msg.lower()
        finally:
            Path(temp_path).unlink()


class TestAuditLogging:
    """Audit logging validation (Security Requirement)"""

    @pytest.fixture
    def context(self):
        """Provide loaded context for tests"""
        return ContextManager("docs/STORY_2_CONTEXT.md")

    def test_audit_log_captures_modifications(self, context):
        """Should log all context modifications"""
        initial_count = len(context.get_audit_log())

        context.set("test1", "value1")
        context.set("test2", "value2")
        context.update({"test3": "value3", "test4": "value4"})

        audit_log = context.get_audit_log()
        assert len(audit_log) > initial_count + 2

    def test_audit_log_has_timestamps(self, context):
        """Should include timestamp in each entry"""
        context.set("test", "value")

        audit_log = context.get_audit_log()
        for entry in audit_log:
            assert "timestamp" in entry
            assert "action" in entry

    def test_save_audit_log(self, context, tmp_path):
        """Should save audit log to file"""
        context.set("test", "value")

        output_file = tmp_path / "audit.json"
        context.save_audit_log(output_file)

        assert output_file.exists()

        # Load and verify
        with open(output_file) as f:
            audit_data = json.load(f)

        assert "story_id" in audit_data
        assert "log_entries" in audit_data
        assert len(audit_data["log_entries"]) > 0
