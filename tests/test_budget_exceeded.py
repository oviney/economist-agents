"""Prove-it tests for #340: surface Agent SDK budget exhaustion as a typed error.

Verifies that:
1. ``BudgetExceededError`` is a ``RuntimeError`` subclass living alongside
   ``EmptyResearchBriefError`` in ``src/agent_sdk/_shared.py``.
2. ``_collect_text`` in ``stage3_runner.py`` raises ``BudgetExceededError``
   when the Agent SDK emits a ``ResultMessage`` with
   ``subtype="error_max_budget_usd"`` (and does NOT raise for normal
   ``subtype="success"`` results).
3. ``flow.generate_content`` catches ``BudgetExceededError`` and produces a
   terminal pipeline result with ``status: "budget_exceeded"`` — it does NOT
   route to revision (the budget is a hard cap, not a content problem).
4. ``flow.request_revision`` also short-circuits to ``status: "budget_exceeded"``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

# ── Unit: BudgetExceededError class ─────────────────────────────────────────


class TestBudgetExceededErrorClass:
    def test_is_runtime_error_subclass(self) -> None:
        from src.agent_sdk._shared import BudgetExceededError

        assert issubclass(BudgetExceededError, RuntimeError)

    def test_carries_budget_usd(self) -> None:
        from src.agent_sdk._shared import BudgetExceededError

        err = BudgetExceededError("cap hit", budget_usd=0.30)
        assert err.budget_usd == 0.30
        assert "cap hit" in str(err)

    def test_lives_next_to_empty_research_brief_error(self) -> None:
        """Both error types must export from the same module for symmetry."""
        from src.agent_sdk import _shared

        assert hasattr(_shared, "BudgetExceededError")
        assert hasattr(_shared, "EmptyResearchBriefError")


# ── Unit: _collect_text detects subtype="error_max_budget_usd" ──────────────


def _make_assistant_msg(text: str) -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model="claude-sonnet-4-6")


def _make_result_msg(
    subtype: str = "success",
    is_error: bool = False,
    total_cost_usd: float | None = 0.05,
) -> ResultMessage:
    return ResultMessage(
        subtype=subtype,
        duration_ms=1000,
        duration_api_ms=900,
        is_error=is_error,
        num_turns=1,
        session_id="test-session",
        total_cost_usd=total_cost_usd,
    )


async def _async_iter(items: list) -> AsyncIterator:
    for item in items:
        yield item


class TestCollectTextBudgetDetection:
    def test_raises_budget_exceeded_when_subtype_signals_budget(self) -> None:
        """The Agent SDK signals budget exhaustion via ResultMessage subtype,
        not by raising. _collect_text must inspect and re-raise as a typed error.
        """
        from src.agent_sdk._shared import BudgetExceededError
        from src.agent_sdk.stage3_runner import _collect_text

        messages = [
            _make_assistant_msg("partial output"),
            _make_result_msg(
                subtype="error_max_budget_usd",
                is_error=True,
                total_cost_usd=0.31,
            ),
        ]

        def _fake_query(prompt: str, options):  # noqa: ANN001 — mock signature
            return _async_iter(messages)

        with (
            patch("src.agent_sdk.stage3_runner.query", side_effect=_fake_query),
            pytest.raises(BudgetExceededError) as excinfo,
        ):
            asyncio.run(
                _collect_text(
                    prompt="hi",
                    system_prompt="sys",
                    max_budget_usd=0.30,
                )
            )

        # Message must include the cap and the cost we hit it at.
        assert excinfo.value.budget_usd == 0.30
        assert "0.30" in str(excinfo.value)
        assert "0.31" in str(excinfo.value)

    def test_does_not_raise_on_normal_success_subtype(self) -> None:
        """Belt-and-braces: a vanilla success ResultMessage must NOT trip the
        budget guard (the previous implementation didn't inspect subtype at all).
        """
        from src.agent_sdk.stage3_runner import _collect_text

        messages = [
            _make_assistant_msg("article body"),
            _make_result_msg(subtype="success", is_error=False, total_cost_usd=0.05),
        ]

        def _fake_query(prompt: str, options):  # noqa: ANN001 — mock signature
            return _async_iter(messages)

        with patch("src.agent_sdk.stage3_runner.query", side_effect=_fake_query):
            text, cost = asyncio.run(
                _collect_text(
                    prompt="hi",
                    system_prompt="sys",
                    max_budget_usd=0.30,
                )
            )

        assert "article body" in text
        assert cost == 0.05


# ── Integration: flow.py routes BudgetExceededError to clean abort ──────────


class TestFlowBudgetExceededRouting:
    def test_generate_content_returns_budget_exceeded_draft(self) -> None:
        from src.agent_sdk._shared import BudgetExceededError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=BudgetExceededError("cap $0.30 hit", budget_usd=0.30),
        ):
            draft = flow.generate_content({"topic": "AI Testing"})

        # Routes through the null-draft path (so quality_gate can see the failure).
        assert draft["publication_validator_passed"] is False
        assert draft["editorial_score"] == 0
        # Critically, flow.state records the abort so kickoff() short-circuits.
        assert flow.state.get("abort_reason") == "budget_exceeded"
        assert flow.state.get("budget_usd") == 0.30
        # The null-draft surfaces the typed reason in its issues.
        issues = draft["publication_validator_issues"]
        assert any(i.get("check") == "budget_exceeded" for i in issues)

    def test_kickoff_short_circuits_on_budget_exceeded(self) -> None:
        """When generate_content sets abort_reason, kickoff() must skip the
        quality_gate/revision dance and emit a budget_exceeded terminal result.
        """
        from src.agent_sdk._shared import BudgetExceededError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        # Stub the stages that run before generate_content.
        flow.discover_topics = MagicMock(  # type: ignore[method-assign]
            return_value={"topics": [{"topic": "AI Testing", "raw": {}}]}
        )
        flow.editorial_review = MagicMock(  # type: ignore[method-assign]
            return_value={"topic": "AI Testing"}
        )
        # Sentinels — they MUST NOT be called when budget exceeded.
        flow.quality_gate = MagicMock()  # type: ignore[method-assign]
        flow.request_revision = MagicMock()  # type: ignore[method-assign]
        flow.publish_article = MagicMock()  # type: ignore[method-assign]
        flow._write_pipeline_result = MagicMock()  # type: ignore[method-assign]

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=BudgetExceededError("cap hit", budget_usd=0.30),
        ):
            result = flow.kickoff()

        assert result["status"] == "budget_exceeded"
        assert result["budget_usd"] == 0.30
        assert result["editorial_score"] == 0
        assert result["gates_passed"] == 0
        # Revision/publish/quality_gate must NOT run — budget is a hard abort.
        flow.quality_gate.assert_not_called()
        flow.request_revision.assert_not_called()
        flow.publish_article.assert_not_called()

    def test_request_revision_returns_budget_exceeded_status(self) -> None:
        """Defense in depth: direct callers of request_revision get the same
        clean abort behaviour rather than thrashing through retries.
        """
        from src.agent_sdk._shared import BudgetExceededError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_feedback"] = ["fix something"]
        flow.state["article_draft"] = {"featured_image": ""}

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=BudgetExceededError("cap hit", budget_usd=0.30),
        ):
            result = flow.request_revision()

        assert result["status"] == "budget_exceeded"
        assert result["budget_usd"] == 0.30
        assert result["editorial_score"] == 0
