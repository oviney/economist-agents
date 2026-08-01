"""`create_llm_client` must run keyless on the Claude subscription (BUG-046).

Operating Constraint #3: "The only LLM auth is the Claude subscription via the
Agent SDK." `create_llm_client` did not honour that — it required
`ANTHROPIC_API_KEY` or `OPENAI_API_KEY` and raised `ValueError` when neither was
set. That is BUG-046, and it is why `EconomistContentFlow` Stage 1 (topic
discovery) and Stage 2 (editorial review) could not run on the keyless stack. The
documented workaround was to skip the flow entirely and drive
`src.agent_sdk.pipeline` with a manual topic.

The fix makes the keyless Agent SDK provider the **default**, so the constraint
holds by construction rather than by discipline. The key-based providers survive
only as an explicit opt-out via `LLM_PROVIDER`, because they are legacy paths
that pre-date the constraint — not because anything should reach for them.

This also dissolves B-023: there is nothing to authenticate, so whether an
`ANTHROPIC_AUTH_TOKEN` counts as a "new key" (#1) or as the subscription (#3) is
moot.
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts import llm_client as lc


@pytest.fixture(autouse=True)
def no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """The keyless case is the default case, so it is the default fixture."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


class TestKeylessIsTheDefault:
    """Constraint #3, enforced computationally rather than by convention."""

    def test_no_keys_yields_an_agent_sdk_client(self) -> None:
        """BUG-046: this used to raise ValueError."""
        client = lc.create_llm_client()

        assert client.provider == "agent_sdk"

    def test_agent_sdk_wins_even_when_an_api_key_is_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stray key in the environment must not silently start billing."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-leftover")

        assert lc.create_llm_client().provider == "agent_sdk"

    def test_keyless_client_needs_no_credential(self) -> None:
        client = lc.create_llm_client()

        assert client.client is None
        assert client.model


class TestLegacyProvidersAreOptOut:
    """The paid paths still exist, but you have to ask for them by name."""

    def test_explicit_anthropic_still_works(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(lc, "_create_anthropic_client", lambda: "ANTHROPIC")

        assert lc.create_llm_client() == "ANTHROPIC"

    def test_explicit_anthropic_without_a_key_is_a_clear_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asking for a paid path without its key must say so, not fall back."""
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            lc.create_llm_client()

    def test_unknown_provider_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        with pytest.raises(ValueError, match="gemini"):
            lc.create_llm_client()

    def test_agent_sdk_can_be_named_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "agent_sdk")

        assert lc.create_llm_client().provider == "agent_sdk"


class TestCallLlmRoutesKeyless:
    """`call_llm` is the whole consumer-facing surface; it must dispatch."""

    def test_agent_sdk_client_routes_to_the_sdk(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake(system: str, user: str, max_tokens: int, temperature: float) -> str:
            seen.update(
                system=system, user=user, max_tokens=max_tokens, temp=temperature
            )
            return "keyless response"

        monkeypatch.setattr(lc, "_call_agent_sdk", fake)
        client = lc.create_llm_client()

        result = lc.call_llm(client, "SYS", "USER", max_tokens=1234, temperature=0.5)

        assert result == "keyless response"
        assert seen["system"] == "SYS"
        assert seen["user"] == "USER"
        assert seen["max_tokens"] == 1234

    def test_the_flow_can_build_a_client_without_any_key(self) -> None:
        """The BUG-046 reproduction, stated as the thing that was broken.

        `EconomistContentFlow.discover_topics` calls `create_llm_client()` with
        no arguments. That is the call that raised.
        """
        assert lc.create_llm_client().provider == "agent_sdk"
