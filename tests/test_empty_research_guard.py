"""Prove-it tests for #324 + #384: empty research brief guard.

Verifies that:
1. build_research_brief raises EmptyResearchBriefError when both web
   searches return nothing, preventing any LLM call on zero sourcing.
2. The typed subclasses SearchProvidersFailedError /
   SearchProvidersEmptyError are raised per cause (#384 AC1).
3. run_stage3 propagates the error (does not swallow it).
4. EconomistContentFlow.generate_content and request_revision route it
   to revision rather than crashing or publishing fabricated content.
5. pipeline.main() CLI surfaces each typed error with distinct exit
   codes and prints traceback-free actionable messages (#384 AC2).
6. --research-only flag runs only Stage 0 and exits (#384 AC3).
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


# ── Integration: pipeline.main CLI (#384 AC2 + AC3) ──────────────────────────


class TestPipelineCliErrorSurfacing:
    """pipeline.main must surface typed errors with distinct exit codes
    and traceback-free messages, and the --research-only flag must short-
    circuit before any LLM call."""

    def test_providers_failed_exits_with_code_2_and_actionable_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from src.agent_sdk import pipeline as pl
        from src.agent_sdk._shared import SearchProvidersFailedError

        monkeypatch.setattr("sys.argv", ["pipeline.py", "AI Testing"])
        monkeypatch.setattr(
            pl.asyncio,
            "run",
            lambda *a, **k: (_ for _ in ()).throw(
                SearchProvidersFailedError("simulated outage")
            ),
        )

        with pytest.raises(SystemExit) as exc_info:
            pl.main()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "research providers failed" in err
        assert "rephrase the topic" in err
        assert "Traceback" not in err

    def test_providers_empty_exits_with_code_3_and_actionable_message(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from src.agent_sdk import pipeline as pl
        from src.agent_sdk._shared import SearchProvidersEmptyError

        monkeypatch.setattr("sys.argv", ["pipeline.py", "AI Testing"])
        monkeypatch.setattr(
            pl.asyncio,
            "run",
            lambda *a, **k: (_ for _ in ()).throw(
                SearchProvidersEmptyError("zero results")
            ),
        )

        with pytest.raises(SystemExit) as exc_info:
            pl.main()

        assert exc_info.value.code == 3
        err = capsys.readouterr().err
        assert "zero sources" in err
        assert "broadening it or rephrasing" in err
        assert "Traceback" not in err

    def test_research_only_flag_prints_brief_and_skips_pipeline(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from src.agent_sdk import pipeline as pl

        monkeypatch.setattr(
            "sys.argv", ["pipeline.py", "--research-only", "AI Testing"]
        )
        # asyncio.run must NOT be called when --research-only is set
        monkeypatch.setattr(
            pl.asyncio,
            "run",
            lambda *a, **k: pytest.fail("asyncio.run called under --research-only"),
        )
        monkeypatch.setattr(
            "src.agent_sdk._shared.build_research_brief",
            lambda topic: f"# Research Brief: {topic}\n\nfake source",
        )

        pl.main()

        out = capsys.readouterr().out
        assert "--- Research brief ---" in out
        assert "fake source" in out

    def test_research_only_with_providers_failed_exits_2(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from src.agent_sdk import pipeline as pl
        from src.agent_sdk._shared import SearchProvidersFailedError

        monkeypatch.setattr(
            "sys.argv", ["pipeline.py", "--research-only", "AI Testing"]
        )
        monkeypatch.setattr(
            "src.agent_sdk._shared.build_research_brief",
            lambda topic: (_ for _ in ()).throw(
                SearchProvidersFailedError("simulated")
            ),
        )

        with pytest.raises(SystemExit) as exc_info:
            pl.main()

        assert exc_info.value.code == 2
        assert "providers failed" in capsys.readouterr().err
