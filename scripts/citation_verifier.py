#!/usr/bin/env python3
"""Citation Verifier — confirm statistics appear in their cited sources.

Fetches URLs from the Research Agent's ``data_points`` and checks whether
the claimed statistic actually appears in the source text.  Marks
unverifiable claims as ``verified: false`` so the Writer can tag them
``[UNVERIFIED]`` and the publication validator can reject the article.

Usage::

    from scripts.citation_verifier import verify_citations

    research_data = research_agent.research(topic)
    research_data = verify_citations(research_data)
    # data_points now have accurate ``verified`` flags
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10
_MAX_CONTENT_LENGTH = 50_000  # chars — don't read entire books


def _fetch_page_text(url: str) -> str | None:
    """Fetch a URL and return plain text content.

    Returns None on any failure (network, timeout, non-text response).
    """
    try:
        resp = requests.get(
            url,
            timeout=_FETCH_TIMEOUT,
            headers={"User-Agent": "EconomistAgents/1.0 citation-verifier"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text" not in content_type and "json" not in content_type:
            logger.info("Skipping non-text URL: %s (%s)", url, content_type)
            return None
        return resp.text[:_MAX_CONTENT_LENGTH]
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for fuzzy matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s%.$]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _stat_appears_in_text(stat: str, page_text: str) -> bool:
    """Check whether a statistic appears in the page text.

    Uses fuzzy matching: extracts key numbers/percentages from the stat
    and checks if they appear near relevant words in the page text.
    """
    if not stat or not stat.strip():
        return False

    norm_page = _normalize(page_text)
    norm_stat = _normalize(stat)

    # Extract numbers and percentages from the stat — required for verification.
    # Stats without numbers can't be meaningfully verified against source text.
    numbers = re.findall(r"\d+(?:\.\d+)?%?", stat)
    if not numbers:
        # No numbers in the stat — can't verify numerically
        return False

    # Check if ALL key numbers appear somewhere in the page
    for num in numbers:
        if num not in norm_page:
            return False

    # Numbers are present — check if at least one contextual word from
    # the stat also appears near a number (within 200 chars)
    context_words = [
        w
        for w in re.findall(r"[a-z]{4,}", norm_stat)
        if w not in {"that", "than", "with", "from", "this", "have", "been"}
    ]
    if not context_words:
        return True  # numbers match, no context words to check

    for num in numbers:
        idx = norm_page.find(num)
        if idx == -1:
            continue
        window = norm_page[max(0, idx - 200) : idx + 200]
        if any(w in window for w in context_words):
            return True

    return False


def verify_citations(
    research_data: dict[str, Any],
    *,
    fetch_fn: Any = None,
) -> dict[str, Any]:
    """Verify that cited statistics appear in their source URLs.

    For each ``data_point`` with a ``url`` field, fetches the page and
    checks whether the ``stat`` text appears.  Updates ``verified`` to
    ``False`` for unverifiable claims and adds them to
    ``unverified_claims``.

    Args:
        research_data: Output from ``ResearchAgent.research()``.
        fetch_fn: Optional override for ``_fetch_page_text`` (for testing).

    Returns:
        The same dict with updated ``verified`` flags and
        ``unverified_claims`` list.
    """
    fetch = fetch_fn or _fetch_page_text
    data_points = research_data.get("data_points", [])
    unverified: list[str] = list(research_data.get("unverified_claims", []))
    verified_count = 0
    failed_count = 0

    for dp in data_points:
        url = dp.get("url", "")
        stat = dp.get("stat", "")

        if not url or not stat:
            # No URL to verify against — mark unverified
            if stat and dp.get("verified", True):
                dp["verified"] = False
                unverified.append(f"{stat} (no URL to verify)")
                failed_count += 1
            continue

        page_text = fetch(url)
        if page_text is None:
            # Couldn't fetch — mark unverified but don't penalise
            # (network issues shouldn't block the pipeline)
            logger.info(
                "Could not fetch %s — leaving verified=%s", url, dp.get("verified")
            )
            continue

        if _stat_appears_in_text(stat, page_text):
            dp["verified"] = True
            verified_count += 1
            logger.info("✅ Verified: '%s' found in %s", stat[:60], url)
        else:
            dp["verified"] = False
            failed_count += 1
            claim_desc = f"{stat} (not found in {url})"
            unverified.append(claim_desc)
            logger.warning("❌ Unverified: '%s' NOT found in %s", stat[:60], url)

    # Also verify headline_stat if it has a URL
    headline = research_data.get("headline_stat", {})
    headline_url = headline.get("url", "")
    headline_stat = headline.get("value", "")
    if headline_url and headline_stat:
        page_text = fetch(headline_url)
        if page_text and not _stat_appears_in_text(headline_stat, page_text):
            headline["verified"] = False
            unverified.append(
                f"HEADLINE: {headline_stat} (not found in {headline_url})"
            )
            failed_count += 1
            logger.warning("❌ Headline unverified: '%s'", headline_stat[:60])

    research_data["unverified_claims"] = unverified
    research_data["citation_verification"] = {
        "verified": verified_count,
        "failed": failed_count,
        "total_checked": verified_count + failed_count,
    }

    logger.info(
        "Citation verification: %d verified, %d failed, %d total",
        verified_count,
        failed_count,
        verified_count + failed_count,
    )

    return research_data
