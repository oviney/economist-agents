#!/usr/bin/env python3
"""Source stance — does the source support the sentence citing it? (B-022, BUG-060)

The most damaging finding in the external review of the first published article,
and the only one no deterministic gate can reach. The article argued that
auto-retry is "an anaesthetic, not a cure" while citing a paper whose authors
ran exactly that comparison and concluded the opposite: they shifted effort
*toward* automatic reruns. Atlassian and Google, the other cited organisations,
did the same. A reader following any citation would have found it arguing
against the paragraph citing it.

No amount of number-matching finds this. Every figure in that paragraph was
correctly transcribed. Detecting it means reading what the source *concluded*,
which is why this gate — alone among B-020..B-023 — uses the model.

Keyless: runs through ``query()`` on the Claude subscription (CLAUDE.md
constraint #3). ``query_fn`` is injectable so tests never reach the network,
and the default path honours ``ECON_AGENTS_OFFLINE``.

Fail closed, as everywhere in this family: an unparseable reply, an unknown
stance, a failed call or a citation with nothing to read all yield
``UNRESOLVED``. Never ``PASS``.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import orjson

logger = logging.getLogger(__name__)

Verdict = Literal["PASS", "FAIL", "UNRESOLVED"]
Stance = Literal["SUPPORTS", "CONTRADICTS", "DOES_NOT_BEAR_ON", "UNKNOWN"]

QueryFn = Callable[[str], str]

OFFLINE_ENV_VAR = "ECON_AGENTS_OFFLINE"

STANCE_MODEL = "claude-sonnet-4-6"

_VALID_STANCES: dict[str, Stance] = {
    "SUPPORTS": "SUPPORTS",
    "CONTRADICTS": "CONTRADICTS",
    "DOES_NOT_BEAR_ON": "DOES_NOT_BEAR_ON",
}

_PROMPT = """\
You are checking whether a cited source actually supports the claim citing it.

THE CLAIM, as written in the article:
{claim}

THE SOURCE ({title}, {url}), in its own words:
{source_text}

Decide which of these the source's own position is, with respect to the claim:

- SUPPORTS          the source's findings and conclusion back the claim
- CONTRADICTS       the source concludes the opposite, or its authors made the
                    opposite recommendation from the same evidence
- DOES_NOT_BEAR_ON  the source does not address the claim either way

Judge the source's CONCLUSION, not whether its numbers appear in the claim. A
source can supply a correct figure and still argue against the point it is
being used to make — that is the specific failure this check exists to catch.

Reply with JSON only: {{"stance": "...", "evidence": "<short quote from the
source that settles it>"}}
"""


@dataclass(frozen=True)
class Citation:
    """A claim in the article and the source it rests on."""

    index: int
    title: str
    url: str
    claim: str
    source_text: str


@dataclass(frozen=True)
class Finding:
    """One stance verdict for one citation."""

    check: str
    verdict: Verdict
    stance: Stance
    reference_index: int
    message: str
    evidence: str = ""


def _default_query(prompt: str) -> str:
    """Ask Claude on the subscription. Raises on any failure — caller catches."""
    if os.environ.get(OFFLINE_ENV_VAR):
        raise RuntimeError("offline mode — stance check not run")

    import asyncio

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        query,
    )

    async def _run() -> str:
        options = ClaudeAgentOptions(model=STANCE_MODEL, max_turns=1)
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        return "".join(chunks)

    return asyncio.run(_run())


def _parse(reply: str) -> tuple[Stance, str]:
    """Pull a stance out of the model's reply, tolerating fenced JSON."""
    text = reply.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        payload = orjson.loads(text)
    except Exception:
        logger.warning("Stance reply was not JSON: %r", reply[:120])
        return "UNKNOWN", ""

    if not isinstance(payload, dict):
        return "UNKNOWN", ""

    raw = str(payload.get("stance", "")).strip().upper()
    evidence = str(payload.get("evidence", ""))
    return _VALID_STANCES.get(raw, "UNKNOWN"), evidence


def check_source_stance(
    citations: list[Citation],
    *,
    query_fn: QueryFn | None = None,
) -> list[Finding]:
    """Classify each citation's source as supporting or contradicting its claim."""
    ask = query_fn or _default_query
    findings: list[Finding] = []

    for citation in citations:
        if not citation.source_text.strip():
            findings.append(
                Finding(
                    check="source_stance",
                    verdict="UNRESOLVED",
                    stance="UNKNOWN",
                    reference_index=citation.index,
                    message=(
                        f"Reference {citation.index} could not be read, so its "
                        f"stance is unknown. Not verified — not a pass."
                    ),
                )
            )
            continue

        prompt = _PROMPT.format(
            claim=citation.claim.strip(),
            title=citation.title,
            url=citation.url,
            source_text=citation.source_text.strip(),
        )

        try:
            reply = ask(prompt)
        except Exception as exc:  # noqa: BLE001 - any failure is UNRESOLVED
            logger.warning(
                "Stance check failed for reference %d: %s", citation.index, exc
            )
            findings.append(
                Finding(
                    check="source_stance",
                    verdict="UNRESOLVED",
                    stance="UNKNOWN",
                    reference_index=citation.index,
                    message=(
                        f"Stance check for reference {citation.index} did not "
                        f"run ({exc}). Not verified — not a pass."
                    ),
                )
            )
            continue

        stance, evidence = _parse(reply)
        findings.append(_finding_for(citation, stance, evidence))

    return findings


def _finding_for(citation: Citation, stance: Stance, evidence: str) -> Finding:
    if stance == "SUPPORTS":
        return Finding(
            check="source_stance",
            verdict="PASS",
            stance=stance,
            reference_index=citation.index,
            message=f"Reference {citation.index} supports the claim citing it.",
            evidence=evidence,
        )

    if stance == "UNKNOWN":
        return Finding(
            check="source_stance",
            verdict="UNRESOLVED",
            stance=stance,
            reference_index=citation.index,
            message=(
                f"Stance for reference {citation.index} could not be determined. "
                f"Not verified — not a pass."
            ),
            evidence=evidence,
        )

    reason = (
        "concludes the opposite"
        if stance == "CONTRADICTS"
        else "does not address the claim either way"
    )
    return Finding(
        check="source_stance",
        verdict="FAIL",
        stance=stance,
        reference_index=citation.index,
        message=(
            f"Reference {citation.index} {reason}. The article claims: "
            f"{citation.claim.strip()[:120]!r}. Source evidence: {evidence!r}. "
            f"A source cited in support of the position it refutes is not a "
            f"citation."
        ),
        evidence=evidence,
    )


def summarise(findings: list[Finding]) -> dict[str, int]:
    """Counts by verdict, keeping UNRESOLVED distinct from PASS."""
    return {
        "pass": sum(1 for f in findings if f.verdict == "PASS"),
        "fail": sum(1 for f in findings if f.verdict == "FAIL"),
        "unresolved": sum(1 for f in findings if f.verdict == "UNRESOLVED"),
    }
