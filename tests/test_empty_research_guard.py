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
import inspect
from typing import Any
from unittest.mock import patch

import pytest


def _close_coros_then(action):
    """Build a stand-in for ``asyncio.run`` that closes any coroutine args
    before invoking *action*. Without the close, the mock receives an
    unawaited coroutine and Python emits ``RuntimeWarning: coroutine
    ... was never awaited``, polluting test output."""

    def _stub(*args: Any, **kwargs: Any) -> Any:
        for a in args:
            if inspect.iscoroutine(a):
                a.close()
        return action(*args, **kwargs)

    return _stub


# ── Unit: _shared.py ─────────────────────────────────────────────────────────


def _diag(
    arxiv: int = 0,
    semantic_scholar: int = 0,
    *,
    arxiv_failed: bool = False,
    semantic_scholar_failed: bool = False,
) -> dict[str, object]:
    """Build the diagnostics dict matching _run_web_searches' return shape.

    Free-providers-only after the paid-API removal: arXiv + Semantic Scholar.
    """
    return {
        "source_counts": {
            "arxiv": arxiv,
            "semantic_scholar": semantic_scholar,
        },
        "provider_failed": {
            "arxiv": arxiv_failed,
            "semantic_scholar": semantic_scholar_failed,
        },
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
                return_value=(
                    "",
                    _diag(arxiv_failed=True, semantic_scholar_failed=True),
                ),
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
            return_value=(
                "## Semantic Scholar\n- Some result",
                _diag(semantic_scholar=1),
            ),
        ):
            brief = build_research_brief("AI Testing")

        assert "Some result" in brief

    def test_free_providers_only_aggregate_sources_across_arxiv_and_semantic_scholar(
        self,
    ) -> None:
        """When arXiv fails but Semantic Scholar returns results, the brief
        must be built from Semantic Scholar alone and the gate must NOT fire.
        Proves the free-providers-only fan-out is resilient to a single
        provider outage (the paid Serper/Brave/Tavily providers were removed).
        """
        from src.agent_sdk._shared import _run_web_searches

        with (
            patch(
                "scripts.arxiv_search.search_arxiv_for_topic",
                return_value={"success": False, "insights": {}, "error": "rate-limit"},
            ),
            patch(
                "scripts.semantic_scholar_search.search_semantic_scholar_for_topic",
                return_value={
                    "success": True,
                    "papers": [
                        {
                            "title": "Paper",
                            "authors": "X",
                            "year": 2025,
                            "abstract": "abs",
                            "doi": "10.0/x",
                            "url": "https://semanticscholar.org/p/1",
                            "citation_count": 5,
                        }
                    ],
                },
            ),
        ):
            text, diag = _run_web_searches("AI Testing")

        # arXiv failed; Semantic Scholar carried the load.
        assert diag["provider_failed"]["arxiv"] is True
        assert diag["provider_failed"]["semantic_scholar"] is False
        # Exactly one source counted (from Semantic Scholar).
        assert sum(diag["source_counts"].values()) == 1
        assert diag["source_counts"]["semantic_scholar"] == 1
        # The Semantic Scholar paper surfaces in the brief for the writer.
        assert "Paper" in text

    def test_run_stage3_propagates_empty_research_error(self) -> None:
        """EmptyResearchBriefError (and subclasses) must not be swallowed by run_stage3."""
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.agent_sdk.stage3_runner import run_stage3

        with (
            patch(
                "src.agent_sdk._shared._run_web_searches",
                return_value=(
                    "",
                    _diag(arxiv_failed=True, semantic_scholar_failed=True),
                ),
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

        def _raise(*a, **k):
            raise EmptyResearchBriefError("No results")

        with patch(
            "src.economist_agents.flow.asyncio.run",
            new=_close_coros_then(_raise),
        ):
            result = flow.generate_content({"topic": "AI Testing"})

        assert result["publication_validator_passed"] is False
        assert result["editorial_score"] == 0
        assert "Research providers" in str(flow.state.get("revision_feedback", ""))

    def test_quality_gate_routes_to_revision_after_empty_research(self) -> None:
        from src.agent_sdk._shared import EmptyResearchBriefError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        def _raise(*a, **k):
            raise EmptyResearchBriefError("No results")

        with patch(
            "src.economist_agents.flow.asyncio.run",
            new=_close_coros_then(_raise),
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

        def _raise(*a, **k):
            raise EmptyResearchBriefError("No results")

        with patch(
            "src.economist_agents.flow.asyncio.run",
            new=_close_coros_then(_raise),
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

        def _raise_failed(*a, **k):
            raise SearchProvidersFailedError("simulated outage")

        monkeypatch.setattr(
            pl.asyncio,
            "run",
            _close_coros_then(_raise_failed),
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

        def _raise_empty(*a, **k):
            raise SearchProvidersEmptyError("zero results")

        monkeypatch.setattr(
            pl.asyncio,
            "run",
            _close_coros_then(_raise_empty),
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
        def _should_not_run(*a, **k):
            pytest.fail("asyncio.run called under --research-only")

        monkeypatch.setattr(
            pl.asyncio,
            "run",
            _close_coros_then(_should_not_run),
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

    def test_research_only_with_providers_empty_exits_3(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from src.agent_sdk import pipeline as pl
        from src.agent_sdk._shared import SearchProvidersEmptyError

        monkeypatch.setattr(
            "sys.argv", ["pipeline.py", "--research-only", "AI Testing"]
        )
        monkeypatch.setattr(
            "src.agent_sdk._shared.build_research_brief",
            lambda topic: (_ for _ in ()).throw(
                SearchProvidersEmptyError("zero results")
            ),
        )

        with pytest.raises(SystemExit) as exc_info:
            pl.main()

        assert exc_info.value.code == 3
        err = capsys.readouterr().err
        assert "zero sources" in err
        # --research-only's printer uses a shorter "Try broadening or
        # rephrasing" (no "it") vs the full-pipeline path's
        # "broadening it or rephrasing as a noun-phrase."
        assert "broadening or rephrasing" in err
        assert "Traceback" not in err
