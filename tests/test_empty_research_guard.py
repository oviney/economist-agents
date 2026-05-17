"""Prove-it tests for #324: empty research brief guard.

Verifies that:
1. build_research_brief raises EmptyResearchBriefError when both web
   searches return nothing, preventing any LLM call on zero sourcing.
2. run_stage3 propagates the error (does not swallow it).
3. EconomistContentFlow.generate_content and request_revision route it
   to revision rather than crashing or publishing fabricated content.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

# ── Unit: _shared.py ─────────────────────────────────────────────────────────


def _diag(
    arxiv: int = 0,
    google_web: int = 0,
    google_scholar: int = 0,
    *,
    arxiv_failed: bool = False,
    google_failed: bool = False,
) -> dict[str, object]:
    """Build the diagnostics dict matching _run_web_searches' new return shape."""
    return {
        "source_counts": {
            "arxiv": arxiv,
            "google_web": google_web,
            "google_scholar": google_scholar,
        },
        "provider_failed": {"arxiv": arxiv_failed, "google": google_failed},
    }


class TestEmptyResearchBriefError:
    """EmptyResearchBriefError and its typed subclasses gate build_research_brief."""

    def test_error_class_is_runtime_error_subclass(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError

        assert issubclass(EmptyResearchBriefError, RuntimeError)

    def test_typed_subclasses_inherit_from_empty_research_brief_error(self) -> None:
        from src.agent_sdk._shared import (
            EmptyResearchBriefError,
            SearchProvidersEmptyError,
            SearchProvidersFailedError,
        )

        assert issubclass(SearchProvidersFailedError, EmptyResearchBriefError)
        assert issubclass(SearchProvidersEmptyError, EmptyResearchBriefError)

    def test_raises_search_providers_failed_when_any_provider_errored(self) -> None:
        """If a provider raised/returned success=False and total sources is 0,
        the failure-class error is raised (transient/environmental).
        """
        from src.agent_sdk._shared import (
            SearchProvidersFailedError,
            build_research_brief,
        )

        with (
            patch(
                "src.agent_sdk._shared._run_web_searches",
                return_value=("", _diag(arxiv_failed=True, google_failed=True)),
            ),
            pytest.raises(SearchProvidersFailedError, match="provider_failed"),
        ):
            build_research_brief("AI Testing")

    def test_raises_search_providers_empty_when_providers_succeeded_but_found_nothing(
        self,
    ) -> None:
        """If providers ran cleanly but returned 0 sources, the empty-class
        error is raised (topic likely too narrow / search-hostile phrasing).
        """
        from src.agent_sdk._shared import (
            SearchProvidersEmptyError,
            build_research_brief,
        )

        with (
            patch(
                "src.agent_sdk._shared._run_web_searches",
                return_value=("", _diag()),
            ),
            pytest.raises(SearchProvidersEmptyError, match="source_counts"),
        ):
            build_research_brief("AI Testing")

    def test_does_not_raise_when_at_least_one_source_returned(self) -> None:
        from src.agent_sdk._shared import build_research_brief

        with patch(
            "src.agent_sdk._shared._run_web_searches",
            return_value=("## Web Sources\n- Some result", _diag(google_web=1)),
        ):
            brief = build_research_brief("AI Testing")

        assert "Some result" in brief

    def test_run_stage3_propagates_empty_research_error(self) -> None:
        """EmptyResearchBriefError (and subclasses) must not be swallowed by run_stage3."""
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.agent_sdk.stage3_runner import run_stage3

        with (
            patch(
                "src.agent_sdk._shared._run_web_searches",
                return_value=("", _diag(arxiv_failed=True, google_failed=True)),
            ),
            pytest.raises(EmptyResearchBriefError),
        ):
            asyncio.run(run_stage3("AI Testing"))


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
