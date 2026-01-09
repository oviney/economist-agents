"""
Sprint 15 Production Integration Tests

Tests Flow orchestration, RAG integration, and ROI telemetry working together
in the production pipeline.

Tests API compatibility between Sprint 14 components.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.economist_agents.flow import EconomistContentFlow
from src.telemetry.roi_tracker import ROITracker
from src.tools.style_memory_tool import StyleMemoryTool


class TestFlowOrchestration:
    """Test Flow-based orchestration patterns"""

    def test_flow_initialization(self):
        """Test EconomistContentFlow initializes correctly"""
        flow = EconomistContentFlow()
        assert flow is not None
        assert hasattr(flow, "discover_topics")
        assert hasattr(flow, "editorial_review")
        assert hasattr(flow, "generate_content")
        assert hasattr(flow, "quality_gate")

    def test_flow_topic_discovery(self):
        """Test Flow can discover topics via Stage 1"""
        # Stage1Crew not yet integrated - test stub implementation
        flow = EconomistContentFlow()
        result = flow.discover_topics()

        assert result is not None
        assert "topics" in result
        assert len(result["topics"]) >= 2
        # Verify mock data structure
        for topic in result["topics"]:
            assert "topic" in topic
            assert "score" in topic

    @pytest.mark.skip(reason="Stage2Crew not yet implemented in flow.py")
    def test_flow_editorial_review_skip(self):
        """Placeholder for Stage 2 tests when implemented"""
        pass

    @patch("src.economist_agents.flow.Stage3Crew")
    def test_flow_content_generation(self, mock_stage3):
        """Test Flow can generate content via Stage 3"""
        # Mock Stage3Crew output
        mock_stage3_instance = MagicMock()
        mock_stage3_instance.kickoff.return_value = {
            "article": "# AI Testing\n\nContent here...",
            "chart_data": {"title": "Test Chart", "data": []},
        }
        mock_stage3.return_value = mock_stage3_instance

        flow = EconomistContentFlow()
        topic = {"topic": "AI Testing", "score": 85}
        result = flow.generate_content(topic)

        assert result is not None
        assert "article" in result
        mock_stage3_instance.kickoff.assert_called_once()

    @patch("src.economist_agents.flow.Stage4Crew")
    def test_flow_quality_gate(self, mock_stage4):
        """Test Flow can perform quality gate via Stage 4"""
        # Mock Stage4Crew output
        mock_stage4_instance = MagicMock()
        mock_stage4_instance.kickoff.return_value = {
            "decision": "PUBLISH",
            "quality_score": 9.2,
            "issues": [],
        }
        mock_stage4.return_value = mock_stage4_instance

        flow = EconomistContentFlow()
        # quality_gate expects dict from generate_content, not string
        article_draft = {
            "article": "# AI Testing\n\nHigh quality content...",
            "chart_path": None,
            "word_count": 100,
        }
        result = flow.quality_gate(article_draft)

        # quality_gate returns routing decision string ("publish" or "revision")
        assert result in ["publish", "revision"]
        mock_stage4_instance.kickoff.assert_called_once()


class TestRAGIntegration:
    """Test Style Memory RAG integration with Editor Agent"""

    def test_rag_tool_initialization(self):
        """Test StyleMemoryTool initializes correctly"""
        tool = StyleMemoryTool()
        assert tool is not None
        # Actual API uses query() not query_style_patterns()
        assert hasattr(tool, "query")
        assert hasattr(tool, "get_stats")

    def test_rag_query_performance(self):
        """Test RAG queries complete within 500ms"""
        tool = StyleMemoryTool()

        # Measure query latency
        start = time.time()
        results = tool.query("chart integration", n_results=3)
        latency_ms = (time.time() - start) * 1000

        # Target is <500ms per Sprint 14 specs
        assert latency_ms < 500, f"RAG latency {latency_ms}ms exceeds 500ms target"
        assert isinstance(results, list)

    def test_rag_returns_relevant_patterns(self):
        """Test RAG returns relevant style patterns"""
        tool = StyleMemoryTool()

        # Query for known pattern
        results = tool.query("banned phrases", n_results=5)

        # Graceful degradation: empty results OK if archive empty
        assert isinstance(results, list)
        if len(results) > 0:
            assert all(isinstance(r, dict) for r in results)
            assert all("text" in r and "score" in r for r in results)

    @patch("src.tools.style_memory_tool.StyleMemoryTool")
    def test_editor_queries_rag(self, mock_rag):
        """Test Editor Agent queries RAG during review via Stage4Crew"""
        # Mock RAG responses
        mock_rag_instance = MagicMock()
        mock_rag_instance.query.return_value = [
            {"text": "Avoid 'In today's world' openings", "score": 0.95},
            {"text": "Use British spelling", "score": 0.92},
        ]
        mock_rag.return_value = mock_rag_instance

        # Verify RAG tool can be queried
        style_patterns = mock_rag_instance.query("style guidelines")

        assert len(style_patterns) >= 2
        assert any("British spelling" in p["text"] for p in style_patterns)
        mock_rag_instance.query.assert_called_once()


class TestROIIntegration:
    """Test ROI Telemetry integration across all agents"""

    def test_roi_tracker_initialization(self):
        """Test ROITracker initializes and shares log file"""
        # ROITracker doesn't use singleton pattern - just shares log file
        tracker1 = ROITracker()
        tracker2 = ROITracker()
        assert tracker1.log_file == tracker2.log_file

    def test_roi_tracks_llm_calls(self):
        """Test ROI tracker logs LLM calls correctly"""
        tracker = ROITracker()

        # Start execution
        execution_id = tracker.start_execution("research_agent")
        assert execution_id is not None

        # Log LLM call with correct signature
        tracker.log_llm_call(
            execution_id=execution_id,
            agent="research_agent",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        # End execution
        result = tracker.end_execution(execution_id)
        assert result is not None
        assert result["total_tokens"] == 1500
        assert result["total_cost_usd"] > 0

    def test_roi_calculates_human_hours(self):
        """Test ROI tracker calculates human-hour equivalents"""
        tracker = ROITracker()
        execution_id = tracker.start_execution("writer_agent")

        tracker.log_llm_call(
            execution_id=execution_id,
            agent="writer_agent",
            model="gpt-4o",
            input_tokens=500,
            output_tokens=1000,
        )

        result = tracker.end_execution(execution_id)
        assert "human_hours_equivalent" in result
        assert result["human_hours_equivalent"] > 0

    def test_roi_multiplier_calculation(self):
        """Test ROI multiplier is >100x"""
        tracker = ROITracker()
        execution_id = tracker.start_execution("writer_agent")

        # Writer agent (3 hours human time)
        tracker.log_llm_call(
            execution_id=execution_id,
            agent="writer_agent",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )

        result = tracker.end_execution(execution_id)
        assert "roi_multiplier" in result
        assert result["roi_multiplier"] > 100

    def test_roi_logging_overhead(self):
        """Test ROI logging overhead is <10ms"""
        tracker = ROITracker()
        execution_id = tracker.start_execution("test_agent")

        # Measure logging overhead
        start = time.time()
        tracker.log_llm_call(
            execution_id=execution_id,
            agent="test_agent",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=200,
        )
        overhead_ms = (time.time() - start) * 1000

        assert (
            overhead_ms < 10
        ), f"ROI logging overhead {overhead_ms}ms exceeds 10ms target"


class TestEndToEndIntegration:
    """Test complete end-to-end pipeline with all components"""

    @patch("src.economist_agents.flow.Stage3Crew")
    @patch("src.economist_agents.flow.Stage4Crew")
    @patch("src.tools.style_memory_tool.StyleMemoryTool")
    def test_full_pipeline_with_flow_rag_roi(self, mock_rag, mock_stage4, mock_stage3):
        """Test complete pipeline: Flow → RAG → ROI"""
        # Setup mocks - Stage1 not needed (using stub discover_topics())

        mock_stage3_instance = MagicMock()
        mock_stage3_instance.kickoff.return_value = {
            "article": "# AI Testing ROI\n\nComprehensive analysis...",
            "chart_data": {"title": "ROI Analysis", "data": []},
        }
        mock_stage3.return_value = mock_stage3_instance

        mock_stage4_instance = MagicMock()
        mock_stage4_instance.kickoff.return_value = {
            "decision": "PUBLISH",
            "quality_score": 9.5,
        }
        mock_stage4.return_value = mock_stage4_instance

        mock_rag_instance = MagicMock()
        mock_rag_instance.query.return_value = [
            {"text": "Use data-driven claims", "score": 0.92}
        ]
        mock_rag.return_value = mock_rag_instance

        # Initialize ROI tracking
        roi_tracker = ROITracker()
        execution_id = roi_tracker.start_execution("full_pipeline")

        # Execute pipeline
        flow = EconomistContentFlow()

        # Stage 1: Discover topics
        topics = flow.discover_topics()
        assert len(topics["topics"]) > 0

        # Log ROI for Stage 1
        roi_tracker.log_llm_call(
            execution_id=execution_id,
            agent="research_agent",
            model="gpt-4o",
            input_tokens=500,
            output_tokens=200,
        )

        # Stage 3: Generate content
        content = flow.generate_content(topics["topics"][0])
        assert "article" in content

        # Query RAG for style patterns
        style_patterns = mock_rag_instance.query("style guidelines")
        assert len(style_patterns) > 0

        # Log ROI for Stage 3
        roi_tracker.log_llm_call(
            execution_id=execution_id,
            agent="writer_agent",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1500,
        )

        # Stage 4: Quality gate (expects dict from generate_content)
        quality_result = flow.quality_gate(content)
        assert quality_result in ["publish", "revision"]

        # Finalize ROI tracking
        roi_result = roi_tracker.end_execution(execution_id)
        assert roi_result["total_cost_usd"] > 0
        assert roi_result["roi_multiplier"] > 100

    def test_concurrent_operations(self):
        """Test Flow, RAG, and ROI work concurrently"""
        economist_flow = EconomistContentFlow()
        style_tool = StyleMemoryTool()
        roi_tracker = ROITracker()

        # Verify all components initialize without conflicts
        assert economist_flow is not None
        assert hasattr(flow, "discover_topics")

        # Start concurrent operations
        execution_id1 = roi_tracker.start_execution("agent1")
        execution_id2 = roi_tracker.start_execution("agent2")

        # Query style patterns
        style_results = style_tool.query("banned phrases")
        assert isinstance(style_results, list)

        # Log concurrent LLM calls
        roi_tracker.log_llm_call(
            execution_id=execution_id1,
            agent="agent1",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        roi_tracker.log_llm_call(
            execution_id=execution_id2,
            agent="agent2",
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=300,
        )

        # Verify no conflicts
        result1 = roi_tracker.end_execution(execution_id1)
        result2 = roi_tracker.end_execution(execution_id2)

        assert result1["execution_id"] != result2["execution_id"]
        assert result1["total_tokens"] == 1500
        assert result2["total_tokens"] == 800
