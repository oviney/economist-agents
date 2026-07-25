#!/usr/bin/env python3
"""Source-integrity gates — verify that references are real (B-020, BUG-058).

The first pipeline-generated article passed every deterministic gate while
citing two references that do not exist as printed: an author lifted from a
different reference, and a title that appears nowhere at the cited URL. The
existing evidence check *counts* references; it has never *resolved* one.
Counting is not verification.

This module resolves each reference in the finished article's ``## References``
section and compares the printed metadata against the document actually living
at that URL.

Design notes, both learned from the incident:

1. **Fail closed.** ``UNRESOLVED`` is a first-class verdict, distinct from
   ``PASS``. ``scripts/citation_verifier`` does ``if page_text is None:
   continue``, leaving the prior verdict untouched — and arXiv already 403s
   datacentre fetches, so a wired-in version would have passed the fabricated
   references by default. A green signal from a check that never ran is worse
   than no check.
2. **Name where the error came from.** A bare "author mismatch" is a finding.
   "This surname belongs to reference 5" is a diagnosis of the pipeline bug —
   citation metadata is not bound to its source at extraction, so a name
   harvested from one reference can be attached to another.

Usage::

    from scripts.source_integrity import check_reference_integrity

    findings = check_reference_integrity(article)
    blocking = [f for f in findings if f.verdict == "FAIL"]
"""

from __future__ import annotations

import html
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

Verdict = Literal["PASS", "FAIL", "UNRESOLVED"]

FetchFn = Callable[[str], str | None]

_FETCH_TIMEOUT = 10
_MAX_CONTENT_LENGTH = 200_000

# Title tokens shorter than this carry no signal for matching.
_MIN_TOKEN_LEN = 4
# Share of the printed title's significant tokens that must appear in the
# resolved title. Below this we call it a fabrication rather than a variant.
_TITLE_MATCH_RATIO = 0.6

_REFERENCE_LINE = re.compile(r"^\s*(\d+)\.\s+(.*)$", re.MULTILINE)
_URL = re.compile(r"https?://\S+")
_QUOTED = re.compile(r"[\"“](.+?)[\"”]")

_META_TITLE = re.compile(
    r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_META_AUTHOR = re.compile(
    r'<meta[^>]+name=["\']citation_author["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# "Smith, J.", "Smith et al.", "Smith and Jones" — the surname is what we can
# compare. Initials are exactly what a fabricating pipeline guesses.
_SURNAME = re.compile(r"\b([A-Z][a-z]{2,})\b")

_AUTHORLESS_TOKENS = {
    "arxiv",
    "blog",
    "engineering",
    "the",
    "and",
    "google",
    "microsoft",
    "atlassian",
    "cloudbees",
    "testing",
}


@dataclass(frozen=True)
class Reference:
    """One entry parsed out of the article's ``## References`` section."""

    index: int
    authors_raw: str
    title: str
    url: str
    raw: str


@dataclass(frozen=True)
class ResolvedDoc:
    """Metadata extracted from the document living at a reference's URL."""

    title: str
    authors: list[str] = field(default_factory=list)

    @property
    def has_metadata(self) -> bool:
        return bool(self.title or self.authors)


@dataclass(frozen=True)
class Finding:
    """One verdict about one reference."""

    check: str
    verdict: Verdict
    reference_index: int
    message: str
    url: str = ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_references(article: str) -> list[Reference]:
    """Parse the ``## References`` section into structured entries.

    Only the references section is scanned, so inline body URLs are never
    mistaken for citations.
    """
    match = re.search(r"^##\s+References\s*$", article, re.MULTILINE)
    if not match:
        return []
    section = article[match.end() :]
    # Stop at the next H2 so a trailing section (e.g. a Correction block) is
    # not swallowed into the reference list.
    next_heading = re.search(r"^##\s+", section, re.MULTILINE)
    if next_heading:
        section = section[: next_heading.start()]

    references: list[Reference] = []
    for entry in _REFERENCE_LINE.finditer(section):
        index = int(entry.group(1))
        body = entry.group(2).strip()

        url_match = _URL.search(body)
        if not url_match:
            continue
        url = url_match.group(0).rstrip(".,;")

        quoted = _QUOTED.search(body)
        title = quoted.group(1).strip().rstrip(".,") if quoted else ""
        authors_raw = body[: quoted.start()].strip() if quoted else ""

        references.append(
            Reference(
                index=index,
                authors_raw=authors_raw,
                title=title,
                url=url,
                raw=body,
            )
        )
    return references


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


OFFLINE_ENV_VAR = "ECON_AGENTS_OFFLINE"


def _default_fetch(url: str) -> str | None:
    """Fetch a URL and return its text, or None on any failure.

    Honours ``ECON_AGENTS_OFFLINE`` so local verification stays hermetic
    (B-011 / ADR-0015). Offline yields ``UNRESOLVED``, never ``PASS`` — the
    whole point of the gate is that an unperformed check is not a passed one.
    """
    if os.environ.get(OFFLINE_ENV_VAR):
        logger.info("Offline mode — not resolving %s", url)
        return None
    try:
        import requests

        resp = requests.get(
            url,
            timeout=_FETCH_TIMEOUT,
            headers={"User-Agent": "EconomistAgents/1.0 source-integrity"},
        )
        resp.raise_for_status()
        if "text" not in resp.headers.get("content-type", ""):
            return None
        return resp.text[:_MAX_CONTENT_LENGTH]
    except Exception as exc:  # noqa: BLE001 - any failure is UNRESOLVED
        logger.warning("Could not fetch %s: %s", url, exc)
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def resolve_document(page: str) -> ResolvedDoc:
    """Extract title and author list from a fetched page."""
    title = ""
    if meta := _META_TITLE.search(page):
        title = _clean(meta.group(1))
    elif tag := _HTML_TITLE.search(page):
        title = _clean(tag.group(1))

    authors = [_clean(a) for a in _META_AUTHOR.findall(page)]
    return ResolvedDoc(title=title, authors=[a for a in authors if a])


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _tokens(title: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z]+", title.lower())
        if len(w) >= _MIN_TOKEN_LEN
    }


def _titles_match(printed: str, resolved: str) -> bool:
    """True when the printed title is plausibly the resolved document.

    Containment in either direction counts: conference sites routinely print an
    abbreviated title ("Cost of Flaky Tests in CI") for a paper published as
    "...in Continuous Integration". Flagging that as a fabrication would train
    us to ignore the gate.
    """
    printed_tokens = _tokens(printed)
    resolved_tokens = _tokens(resolved)
    if not printed_tokens or not resolved_tokens:
        return False
    overlap = len(printed_tokens & resolved_tokens)
    smaller = min(len(printed_tokens), len(resolved_tokens))
    return overlap / smaller >= _TITLE_MATCH_RATIO


def _surnames(text: str) -> set[str]:
    """Candidate surnames in a printed author string."""
    return {
        s for s in _SURNAME.findall(text) if s.lower() not in _AUTHORLESS_TOKENS
    }


def _resolved_surnames(authors: list[str]) -> set[str]:
    out: set[str] = set()
    for author in authors:
        out |= _surnames(author)
    return out


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def fetch_references(
    references: list[Reference],
    *,
    fetch_fn: FetchFn | None = None,
) -> dict[int, str]:
    """Fetch each reference's page, keyed by reference index.

    Exposed so the stance check (B-022) can read what a source actually says
    without fetching it a second time. A reference that could not be fetched is
    simply absent from the mapping — callers must treat absence as UNRESOLVED,
    never as a pass.
    """
    fetch = fetch_fn or _default_fetch
    pages: dict[int, str] = {}
    for ref in references:
        try:
            page = fetch(ref.url)
        except Exception as exc:  # noqa: BLE001 - any failure is UNRESOLVED
            logger.warning("Fetch raised for %s: %s", ref.url, exc)
            page = None
        if page is not None:
            pages[ref.index] = page
    return pages


def check_reference_integrity(
    article: str,
    *,
    fetch_fn: FetchFn | None = None,
) -> list[Finding]:
    """Resolve every reference and compare its metadata against the source.

    Returns one or more :class:`Finding` per reference. A reference whose URL
    could not be fetched, or whose page carries no usable metadata, yields
    ``UNRESOLVED`` — never ``PASS``.
    """
    references = parse_references(article)
    if not references:
        return []

    pages = fetch_references(references, fetch_fn=fetch_fn)
    resolved: dict[int, ResolvedDoc] = {}
    findings: list[Finding] = []

    for ref in references:
        page = pages.get(ref.index)

        if page is None:
            findings.append(
                Finding(
                    check="reference_resolution",
                    verdict="UNRESOLVED",
                    reference_index=ref.index,
                    message=(
                        f"Reference {ref.index} could not be fetched "
                        f"({ref.url}). Not verified — not a pass."
                    ),
                    url=ref.url,
                )
            )
            continue

        doc = resolve_document(page)
        if not doc.has_metadata:
            findings.append(
                Finding(
                    check="reference_resolution",
                    verdict="UNRESOLVED",
                    reference_index=ref.index,
                    message=(
                        f"Reference {ref.index} resolved but the page carries no "
                        f"title or author metadata ({ref.url})."
                    ),
                    url=ref.url,
                )
            )
            continue

        resolved[ref.index] = doc
        findings.extend(_check_title(ref, doc))
        findings.extend(_check_authors(ref, doc))

    findings.extend(_check_author_bleed(references, resolved))
    return findings


def _check_title(ref: Reference, doc: ResolvedDoc) -> list[Finding]:
    if not ref.title or not doc.title:
        return []
    if _titles_match(ref.title, doc.title):
        return [
            Finding(
                check="reference_title",
                verdict="PASS",
                reference_index=ref.index,
                message=f"Reference {ref.index} title matches the source.",
                url=ref.url,
            )
        ]
    return [
        Finding(
            check="reference_title",
            verdict="FAIL",
            reference_index=ref.index,
            message=(
                f"Reference {ref.index} title does not match the document at "
                f"{ref.url}. Printed: {ref.title!r}. Actual: {doc.title!r}."
            ),
            url=ref.url,
        )
    ]


def _check_authors(ref: Reference, doc: ResolvedDoc) -> list[Finding]:
    printed = _surnames(ref.authors_raw)
    actual = _resolved_surnames(doc.authors)
    if not printed or not actual:
        # Nothing to compare: an organisational byline ("arXiv (2025)") or a
        # page that lists no authors. Absence of a claim is not a false claim.
        return []

    if printed & actual:
        return [
            Finding(
                check="reference_author",
                verdict="PASS",
                reference_index=ref.index,
                message=f"Reference {ref.index} author matches the source.",
                url=ref.url,
            )
        ]
    return [
        Finding(
            check="reference_author",
            verdict="FAIL",
            reference_index=ref.index,
            message=(
                f"Reference {ref.index} credits {sorted(printed)} but the source "
                f"is by {sorted(actual)} ({ref.url})."
            ),
            url=ref.url,
        )
    ]


def _check_author_bleed(
    references: list[Reference],
    resolved: dict[int, ResolvedDoc],
) -> list[Finding]:
    """Detect a surname that belongs to a *different* reference in the list.

    This is the BUG-058 signature. "Parry" was printed on reference 1 and
    belongs to reference 5 — the pipeline harvested an author from one source
    and attached it to another. A generic author mismatch tells you something
    is wrong; this tells you what the pipeline did.
    """
    findings: list[Finding] = []
    for ref in references:
        doc = resolved.get(ref.index)
        if doc is None:
            continue
        printed = _surnames(ref.authors_raw)
        own = _resolved_surnames(doc.authors)
        stray = printed - own
        if not stray:
            continue

        for other in references:
            if other.index == ref.index:
                continue
            other_doc = resolved.get(other.index)
            if other_doc is None:
                continue
            migrated = stray & _resolved_surnames(other_doc.authors)
            if migrated:
                findings.append(
                    Finding(
                        check="reference_author_bleed",
                        verdict="FAIL",
                        reference_index=ref.index,
                        message=(
                            f"Reference {ref.index} is credited to "
                            f"{sorted(migrated)}, who authored reference "
                            f"{other.index}, not this source. Citation metadata "
                            f"is being re-associated across sources."
                        ),
                        url=ref.url,
                    )
                )
                break
    return findings


def summarise(findings: list[Finding]) -> dict[str, int]:
    """Counts by verdict. ``UNRESOLVED`` is reported separately from ``PASS``."""
    return {
        "pass": sum(1 for f in findings if f.verdict == "PASS"),
        "fail": sum(1 for f in findings if f.verdict == "FAIL"),
        "unresolved": sum(1 for f in findings if f.verdict == "UNRESOLVED"),
    }


def main() -> int:
    """Run the reference-integrity gate over an article file.

    Usage::

        python -m scripts.source_integrity output/posts/<slug>.md

    Exit codes: 0 = no failures, 1 = at least one reference does not match its
    source, 2 = nothing could be resolved (citations UNVERIFIED, not verified).
    """
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", help="path to the article markdown file")
    args = parser.parse_args()

    findings = check_reference_integrity(Path(args.article).read_text())
    if not findings:
        print("No references found — nothing to verify.")
        return 0

    counts = summarise(findings)
    for finding in findings:
        marker = {"PASS": "  ok", "FAIL": "FAIL", "UNRESOLVED": "  ??"}[finding.verdict]
        print(f"{marker}  [{finding.check}] {finding.message}")

    print(
        f"\n{counts['pass']} pass, {counts['fail']} FAIL, "
        f"{counts['unresolved']} unresolved"
    )
    if counts["fail"]:
        print("\nAt least one reference does not match its source. Do not publish.")
        return 1
    if counts["unresolved"] and not counts["pass"]:
        print("\nNothing resolved — citations are UNVERIFIED, not verified.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
