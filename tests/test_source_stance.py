#!/usr/bin/env python3
"""B-022 · Source stance (BUG-060).

The most damaging finding in the external review, and the only one no
deterministic gate can reach. The article argued that auto-retry is "an
anaesthetic, not a cure" while citing a paper whose authors ran exactly that
comparison and concluded the opposite — they shifted effort *toward* automatic
reruns. Atlassian and Google, the other two cited organisations, did the same.

A reader following any citation would find it arguing against the paragraph
citing it. Detecting that means reading the source's conclusion, not matching
its numbers. This is the difference between an article that has read its
sources and one that has mined them.
"""

from __future__ import annotations

import orjson
import pytest

from scripts.source_stance import Citation, check_source_stance

_CITATION = Citation(
    index=1,
    title="Cost of Flaky Tests in Continuous Integration",
    url="https://example.org/icst2024",
    claim=(
        "The trouble is that auto-retry is an anaesthetic, not a cure; it masks "
        "the systemic rot while the cost accumulates elsewhere."
    ),
    source_text=(
        "Contrary to most other studies, we find the cost for rerunning tests "
        "to be negligible and inexpensive. The insights gained from our case "
        "study have led to the decision to shift effort from investigation and "
        "repair to automatically rerunning tests."
    ),
)


def _reply(stance: str, evidence: str = "quoted line") -> str:
    return orjson.dumps({"stance": stance, "evidence": evidence}).decode()


def _query(stance: str):
    def run(prompt: str) -> str:
        return _reply(stance)

    return run


class TestStanceVerdicts:
    def test_contradiction_fails(self) -> None:
        findings = check_source_stance([_CITATION], query_fn=_query("CONTRADICTS"))

        assert findings[0].verdict == "FAIL"
        assert findings[0].stance == "CONTRADICTS"
        assert "reference 1" in findings[0].message.lower()

    def test_support_passes(self) -> None:
        findings = check_source_stance([_CITATION], query_fn=_query("SUPPORTS"))

        assert findings[0].verdict == "PASS"

    def test_irrelevant_source_fails(self) -> None:
        """A citation that does not bear on its claim is not a citation."""
        findings = check_source_stance([_CITATION], query_fn=_query("DOES_NOT_BEAR_ON"))

        assert findings[0].verdict == "FAIL"

    def test_stance_is_case_insensitive(self) -> None:
        findings = check_source_stance([_CITATION], query_fn=_query("contradicts"))

        assert findings[0].verdict == "FAIL"


class TestPromptConstruction:
    def test_prompt_carries_both_the_claim_and_the_source(self) -> None:
        seen: list[str] = []

        def run(prompt: str) -> str:
            seen.append(prompt)
            return _reply("SUPPORTS")

        check_source_stance([_CITATION], query_fn=run)

        assert "anaesthetic, not a cure" in seen[0]
        assert "shift effort from investigation" in seen[0]

    def test_a_citation_without_source_text_is_unresolved(self) -> None:
        """Nothing to read means nothing to judge — and never a pass."""
        bare = Citation(
            index=2, title="t", url="https://example.org/x", claim="c", source_text=""
        )
        findings = check_source_stance([bare], query_fn=_query("SUPPORTS"))

        assert findings[0].verdict == "UNRESOLVED"


class TestFailClosed:
    def test_unparseable_reply_is_unresolved(self) -> None:
        findings = check_source_stance(
            [_CITATION], query_fn=lambda prompt: "I think it's fine, broadly."
        )

        assert findings[0].verdict == "UNRESOLVED"

    def test_unknown_stance_value_is_unresolved(self) -> None:
        findings = check_source_stance([_CITATION], query_fn=_query("MAYBE"))

        assert findings[0].verdict == "UNRESOLVED"

    @pytest.mark.parametrize("boom", [TimeoutError, RuntimeError, ValueError])
    def test_query_failure_is_unresolved_not_pass(self, boom: type[Exception]) -> None:
        def run(prompt: str) -> str:
            raise boom("model unavailable")

        findings = check_source_stance([_CITATION], query_fn=run)

        assert findings[0].verdict == "UNRESOLVED"
        assert findings[0].verdict != "PASS"

    def test_no_citations_yields_nothing(self) -> None:
        assert check_source_stance([], query_fn=_query("SUPPORTS")) == []


class TestCorpusAcceptance:
    def test_the_defect_that_shipped_is_caught(self) -> None:
        """The ICST paper concluded the opposite of the paragraph citing it."""
        findings = check_source_stance([_CITATION], query_fn=_query("CONTRADICTS"))
        failed = [f for f in findings if f.verdict == "FAIL"]

        assert failed
        assert "auto-retry" in failed[0].message or "anaesthetic" in failed[0].message
