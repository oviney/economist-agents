#!/usr/bin/env python3
"""B-005 word-count contract: single source of truth + structured prompt.

Deterministic, no-API. The behavioural target (real drafts clear the word count)
is a live-run acceptance criterion the human executes — see
``docs/specs/B-005-writer-word-count-contract.md`` §Success Criteria 6.
"""

import pytest

from scripts.publication_validator import (
    WORD_COUNT_MAX,
    WORD_COUNT_MIN,
    WORD_COUNT_TARGET,
    PublicationValidator,
    word_count_shortfall,
)

_TODAY = "2026-07-14"


def _article(word_count: int) -> str:
    """A minimally-valid article whose body has exactly ``word_count`` words."""
    body = " ".join(["quality"] * word_count)
    return (
        f'---\nlayout: post\ntitle: "T"\ndate: {_TODAY}\nauthor: "x"\n'
        f'categories: ["Quality Engineering"]\nimage: "/x.svg"\n'
        f'description: "d"\n---\n\n{body}'
    )


class TestConstantsAreConsistent:
    """The contract holds together: floor < target <= max."""

    def test_target_above_floor_for_margin(self) -> None:
        assert WORD_COUNT_TARGET > WORD_COUNT_MIN

    def test_max_at_or_above_target(self) -> None:
        assert WORD_COUNT_MAX >= WORD_COUNT_TARGET


class TestValidatorUsesTheConstant:
    """No more 'docstring says 800, code enforces 700' drift."""

    def test_exactly_min_passes(self) -> None:
        v = PublicationValidator(expected_date=_TODAY)
        v.validate(_article(WORD_COUNT_MIN))
        assert not any(i["check"] == "word_count" for i in v.issues)

    def test_one_under_min_is_critical(self) -> None:
        v = PublicationValidator(expected_date=_TODAY)
        v.validate(_article(WORD_COUNT_MIN - 1))
        wc = [i for i in v.issues if i["check"] == "word_count"]
        assert wc and wc[0]["severity"] == "CRITICAL"

    def test_message_quotes_the_constant(self) -> None:
        v = PublicationValidator(expected_date=_TODAY)
        v.validate(_article(WORD_COUNT_MIN - 50))
        wc = [i for i in v.issues if i["check"] == "word_count"][0]
        assert str(WORD_COUNT_MIN) in wc["message"]


class TestWordCountShortfallHelper:
    """Pure helper drives specific expansion feedback."""

    def test_none_when_at_or_above_floor(self) -> None:
        assert word_count_shortfall(_article(WORD_COUNT_MIN)) is None
        assert word_count_shortfall(_article(WORD_COUNT_MIN + 200)) is None

    def test_feedback_names_actual_count_when_short(self) -> None:
        short = WORD_COUNT_MIN - 62
        msg = word_count_shortfall(_article(short))
        assert msg is not None
        assert str(short) in msg
        assert str(WORD_COUNT_TARGET) in msg

    def test_handles_body_without_frontmatter(self) -> None:
        assert word_count_shortfall("just three words") is not None


class TestPromptEmbedsTheContract:
    """The single source of truth reaches the writer prompt — no drift possible.

    Guarded: importing stage3_runner pulls the Anthropic Agent SDK, which is not
    installed in an API-key-less session. Skip cleanly there; the constant-level
    guarantees above still run.
    """

    def test_prompt_contains_target_and_floor(self) -> None:
        pytest.importorskip("claude_agent_sdk")
        from src.agent_sdk.stage3_runner import _build_writer_prompt

        prompt = _build_writer_prompt("Test Topic", "BRIEF", "")
        assert str(WORD_COUNT_TARGET) in prompt
        assert str(WORD_COUNT_MIN) in prompt
        # structured budget, not just a bare number
        assert "section" in prompt.lower()
