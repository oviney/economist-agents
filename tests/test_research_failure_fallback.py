"""Research-failure policy — B-024 / BUG-067.

BUG-067: ``build_claude_web_brief`` catches every failure and returns a
findings-free brief (guardrail header only) so Stage 3 "degrades softly".
``run_stage3`` logged the char count and dispatched the writer with no emptiness
check, so a failed research leg produced an *ungrounded* article rather than no
article.

The asymmetry was the defect: the deterministic provider path one line below
raises ``EmptyResearchBriefError``, and ``test_empty_research_guard.py`` asserts
``run_stage3`` propagates it. Two research paths, opposite failure policies, one
silent.

Approved policy (docs/specs/B-024-research-failure-policy.md, owner LGTM
2026-07-29): fall back to the keyless deterministic providers, with abort
underneath — if nothing anywhere yields findings, raise. The downgrade must be
loud, because a fallback article is sourced differently from what was
commissioned and must never be mistaken for a web-researched one.
"""

from __future__ import annotations

import asyncio

import pytest

from src.agent_sdk._shared import EmptyResearchBriefError
from src.agent_sdk.research.claude_web import _format_brief
from src.agent_sdk.stage3_runner import _acquire_research_brief

TOPIC = "code review queues"

#: Exactly what claude_web returns when its SDK call fails: header, no findings.
FINDINGS_FREE = _format_brief(TOPIC, "")

DETERMINISTIC_BRIEF = (
    "# Research Brief: code review queues\n\nGraphite, 2026: median PR takes 14 hours."
)


def _async_return(value: object):  # type: ignore[no-untyped-def]
    """Build an async stand-in returning ``value``."""

    async def _inner(*args: object, **kwargs: object) -> object:
        return value

    return _inner


class TestResearchFallback:
    """A failed claude_web leg must never reach the writer empty-handed."""

    def test_claude_web_failure_falls_back_to_deterministic_providers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The BUG-067 reproduction: a findings-free brief must not be used."""
        import src.agent_sdk.stage3_runner as s3

        monkeypatch.setattr(
            s3, "build_claude_web_brief", _async_return((FINDINGS_FREE, 0.12))
        )
        monkeypatch.setattr(
            s3, "build_research_brief", lambda topic: DETERMINISTIC_BRIEF
        )

        brief, cost, downgraded = asyncio.run(
            _acquire_research_brief(TOPIC, "claude_web", None)
        )

        assert brief == DETERMINISTIC_BRIEF
        assert downgraded is True
        # The failed leg still cost money; it must be reported, not discarded.
        assert cost == pytest.approx(0.12)

    def test_no_findings_anywhere_raises_rather_than_writing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Abort underneath the fallback — 'no research at all' is fatal."""
        import src.agent_sdk.stage3_runner as s3

        def _raise_empty(topic: str) -> str:
            raise EmptyResearchBriefError("no sources")

        monkeypatch.setattr(
            s3, "build_claude_web_brief", _async_return((FINDINGS_FREE, 0.0))
        )
        monkeypatch.setattr(s3, "build_research_brief", _raise_empty)

        with pytest.raises(EmptyResearchBriefError):
            asyncio.run(_acquire_research_brief(TOPIC, "claude_web", None))

    def test_successful_claude_web_research_is_used_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The happy path must not be disturbed — no fallback, no downgrade."""
        import src.agent_sdk.stage3_runner as s3

        researched = _format_brief(TOPIC, "LinearB, 2026: AI PRs wait 4.6x longer.")
        called: list[str] = []

        monkeypatch.setattr(
            s3, "build_claude_web_brief", _async_return((researched, 0.30))
        )
        monkeypatch.setattr(
            s3,
            "build_research_brief",
            lambda topic: called.append(topic) or DETERMINISTIC_BRIEF,
        )

        brief, cost, downgraded = asyncio.run(
            _acquire_research_brief(TOPIC, "claude_web", None)
        )

        assert brief == researched
        assert downgraded is False
        assert called == [], "deterministic providers must not run on the happy path"

    def test_supplied_brief_override_skips_research_entirely(self) -> None:
        """--brief is used verbatim at zero cost (B-012), never downgraded."""
        brief, cost, downgraded = asyncio.run(
            _acquire_research_brief(TOPIC, "claude_web", "# Supplied brief\n\nfacts")
        )

        assert brief == "# Supplied brief\n\nfacts"
        assert cost == 0.0
        assert downgraded is False
