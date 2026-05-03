"""Prove-it tests for #324: empty research brief guard.

Verifies that:
1. build_research_brief raises EmptyResearchBriefError when both web
   searches return nothing, preventing any LLM call on zero sourcing.
2. run_stage3_spike propagates the error (does not swallow it).
3. EconomistContentFlow.generate_content and request_revision route it
   to revision rather than crashing or publishing fabricated content.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


# ── Unit: _shared.py ─────────────────────────────────────────────────────────


class TestEmptyResearchBriefError:
    """EmptyResearchBriefError must exist and gate build_research_brief."""

    def test_error_class_is_runtime_error_subclass(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError

        assert issubclass(EmptyResearchBriefError, RuntimeError)

    def test_build_research_brief_raises_when_searches_empty(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError, build_research_brief

        with patch("src.agent_sdk._shared._run_web_searches", return_value=""):
            with pytest.raises(EmptyResearchBriefError, match="SERPER_API_KEY"):
                build_research_brief("AI Testing")

    def test_build_research_brief_does_not_raise_when_searches_return_content(
        self,
    ) -> None:
        from src.agent_sdk._shared import build_research_brief

        with patch(
            "src.agent_sdk._shared._run_web_searches",
            return_value="## Web Sources\n- Some result",
        ):
            brief = build_research_brief("AI Testing")

        assert "Some result" in brief

    def test_run_stage3_spike_propagates_empty_research_error(self) -> None:
        """EmptyResearchBriefError must not be swallowed by run_stage3_spike."""
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.agent_sdk.stage3_runner import run_stage3_spike

        with patch("src.agent_sdk._shared._run_web_searches", return_value=""):
            with pytest.raises(EmptyResearchBriefError):
                asyncio.run(run_stage3_spike("AI Testing"))


# ── Integration: flow.py routing ─────────────────────────────────────────────


class TestEmptyResearchFlowRouting:
    """generate_content and request_revision must route EmptyResearchBriefError
    to revision rather than crashing."""

    def test_generate_content_returns_revision_dict_on_empty_research(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=EmptyResearchBriefError("No results"),
        ):
            result = flow.generate_content({"topic": "AI Testing"})

        assert result["publication_validator_passed"] is False
        assert result["editorial_score"] == 0
        assert "SERPER_API_KEY" in str(flow.state.get("revision_feedback", ""))

    def test_quality_gate_routes_to_revision_after_empty_research(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=EmptyResearchBriefError("No results"),
        ):
            draft = flow.generate_content({"topic": "AI Testing"})

        assert flow.quality_gate(draft) == "revision"

    def test_request_revision_returns_needs_revision_on_empty_research(
        self,
    ) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_feedback"] = ["fix it"]
        flow.state["article_draft"] = {"featured_image": ""}

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=EmptyResearchBriefError("No results"),
        ):
            result = flow.request_revision()

        assert result["status"] == "needs_revision"
