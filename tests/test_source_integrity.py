#!/usr/bin/env python3
"""B-020 · Reference integrity (BUG-058).

The published flaky-tests article printed two references that do not exist as
described: reference 1 credited to "Parry, J. et al." (actually Leinen et al.)
and reference 5 given an invented title. Both passed every gate, because the
existing evidence check *counts* references and has never *resolved* one.

Fixtures below are the real corpus case:
``data/review_corpus/2026-07-24-green-light-red-ledger/``.
"""

from __future__ import annotations

import pytest

from scripts.source_integrity import (
    Verdict,
    check_reference_integrity,
    parse_references,
)

# --- the article as published (references section only) ---------------------

_PUBLISHED_REFS = """
## References

1. Parry, J. et al. "Cost of Flaky Tests in CI: An Industrial Case Study." *ICST 2024 Industry Track*, April 2024. https://conf.researchr.org/details/icst-2024/x
2. Atlassian Engineering. "Taming Test Flakiness." *Atlassian Engineering Blog*. https://www.atlassian.com/blog/atlassian-engineering/taming-test-flakiness
3. Micco, J. "Flaky Tests at Google and How We Mitigate Them." *Google Testing Blog*, May 2016. https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html
5. arXiv (2025). "Empirical Study of Flaky Test Co-Failure Groups in 22 Java Projects." https://arxiv.org/html/2504.16777v1
"""

_ARTICLE = f"---\nlayout: post\ntitle: t\n---\n\nBody paragraph.\n{_PUBLISHED_REFS}"


def _page(title: str, authors: list[str]) -> str:
    """Minimal HTML carrying Highwire citation metadata."""
    meta = "\n".join(f'<meta name="citation_author" content="{a}">' for a in authors)
    return (
        f"<html><head><title>{title}</title>"
        f'<meta name="citation_title" content="{title}">'
        f"{meta}</head><body></body></html>"
    )


# The truth, as verified against the primary sources.
_TRUTH = {
    "https://conf.researchr.org/details/icst-2024/x": _page(
        "Cost of Flaky Tests in Continuous Integration: An Industrial Case Study",
        [
            "Leinen, Fabian",
            "Elsner, Daniel",
            "Pretschner, Alexander",
            "Stahlbauer, Andreas",
            "Sailer, Michael",
            "Juergens, Elmar",
        ],
    ),
    "https://arxiv.org/html/2504.16777v1": _page(
        "Systemic Flakiness: An Empirical Analysis of Co-Occurring Flaky Test Failures",
        ["Parry, Owain", "Kapfhammer, Gregory", "Hilton, Michael", "McMinn, Phil"],
    ),
    "https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html": (
        _page("Flaky Tests at Google and How We Mitigate Them", ["Micco, John"])
    ),
    "https://www.atlassian.com/blog/atlassian-engineering/taming-test-flakiness": (
        _page("Taming Test Flakiness", [])
    ),
}


def _fetch(mapping: dict[str, str]):
    def fetch(url: str) -> str | None:
        return mapping.get(url)

    return fetch


def _by_index(findings, idx):
    return [f for f in findings if f.reference_index == idx]


def _verdicts(findings, idx) -> set[Verdict]:
    return {f.verdict for f in _by_index(findings, idx)}


class TestParsing:
    def test_extracts_every_reference(self) -> None:
        refs = parse_references(_ARTICLE)
        assert [r.index for r in refs] == [1, 2, 3, 5]

    def test_splits_authors_title_and_url(self) -> None:
        ref = parse_references(_ARTICLE)[0]
        assert ref.index == 1
        assert "Parry" in ref.authors_raw
        assert ref.title == "Cost of Flaky Tests in CI: An Industrial Case Study"
        assert ref.url == "https://conf.researchr.org/details/icst-2024/x"

    def test_reference_without_named_authors_parses(self) -> None:
        ref = [r for r in parse_references(_ARTICLE) if r.index == 5][0]
        assert ref.url == "https://arxiv.org/html/2504.16777v1"
        assert "Co-Failure Groups" in ref.title

    def test_article_with_no_references_section_yields_nothing(self) -> None:
        assert parse_references("---\ntitle: t\n---\n\nBody only.\n") == []

    def test_body_urls_are_not_mistaken_for_references(self) -> None:
        article = (
            "---\ntitle: t\n---\n\nSee https://example.com/inline for more.\n"
            "\n## References\n\n1. A. \"T.\" https://example.com/real\n"
        )
        refs = parse_references(article)
        assert [r.url for r in refs] == ["https://example.com/real"]


class TestTitleIntegrity:
    def test_fabricated_title_fails(self) -> None:
        """Reference 5's title does not exist at that URL. This is BUG-058."""
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        titles = [f for f in _by_index(findings, 5) if f.check == "reference_title"]

        assert titles, "expected a title finding for reference 5"
        assert titles[0].verdict == "FAIL"
        assert "Systemic Flakiness" in titles[0].message

    def test_matching_title_passes(self) -> None:
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        titles = [f for f in _by_index(findings, 3) if f.check == "reference_title"]

        assert titles[0].verdict == "PASS"

    def test_subtitle_expansion_is_not_a_failure(self) -> None:
        """Ref 1 prints the short conference title; the paper uses the long one.

        "Cost of Flaky Tests in CI" vs "...in Continuous Integration" is an
        abbreviation, not a fabrication. Flagging it would train us to ignore
        the gate.
        """
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        titles = [f for f in _by_index(findings, 1) if f.check == "reference_title"]

        assert titles[0].verdict == "PASS"


class TestAuthorIntegrity:
    def test_wrong_author_fails(self) -> None:
        """Reference 1 is credited to Parry; the paper is by Leinen et al."""
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        authors = [f for f in _by_index(findings, 1) if f.check == "reference_author"]

        assert authors[0].verdict == "FAIL"
        assert "Parry" in authors[0].message

    def test_correct_author_passes(self) -> None:
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        authors = [f for f in _by_index(findings, 3) if f.check == "reference_author"]

        assert authors[0].verdict == "PASS"

    def test_reference_with_no_printed_author_is_not_flagged(self) -> None:
        """Ref 5 prints "arXiv (2025)" — no surname to check. Not a failure."""
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        authors = [f for f in _by_index(findings, 5) if f.check == "reference_author"]

        assert all(f.verdict != "FAIL" for f in authors)


class TestCrossReferenceContamination:
    def test_author_migrating_between_references_is_named(self) -> None:
        """The BUG-058 signature: Parry belongs to ref 5, printed on ref 1.

        A plain "author mismatch" is useful. Naming *where the name came from*
        is what turns the finding into a diagnosis of the pipeline bug.
        """
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        bleed = [f for f in findings if f.check == "reference_author_bleed"]

        assert bleed, "expected the contamination check to fire"
        assert bleed[0].verdict == "FAIL"
        assert bleed[0].reference_index == 1
        assert "Parry" in bleed[0].message
        assert "reference 5" in bleed[0].message

    def test_no_bleed_reported_when_authors_are_correct(self) -> None:
        clean = (
            "## References\n\n"
            '1. Micco, J. "Flaky Tests at Google and How We Mitigate Them." '
            "https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html\n"
        )
        findings = check_reference_integrity(clean, fetch_fn=_fetch(_TRUTH))

        assert not [f for f in findings if f.check == "reference_author_bleed"]


class TestFailClosed:
    """A check that could not run must never read as a check that passed.

    The existing citation_verifier does `if page_text is None: continue`,
    leaving `verified` untouched. Since arXiv already 403s us, a wired-in
    version would have passed the fabricated references by default. Fail-open
    verification is worse than none: it produces a green signal from a check
    that never ran.
    """

    def test_unreachable_source_is_unresolved_not_pass(self) -> None:
        findings = check_reference_integrity(_ARTICLE, fetch_fn=lambda url: None)

        assert findings
        assert all(f.verdict == "UNRESOLVED" for f in findings)
        assert not any(f.verdict == "PASS" for f in findings)

    def test_page_without_metadata_is_unresolved(self) -> None:
        bare = {r.url: "<html><body>no metadata</body></html>" for r in parse_references(_ARTICLE)}
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(bare))

        assert all(f.verdict != "PASS" for f in findings)

    @pytest.mark.parametrize("boom", [TimeoutError, ConnectionError, ValueError])
    def test_fetch_exceptions_become_unresolved(self, boom: type[Exception]) -> None:
        def fetch(url: str) -> str | None:
            raise boom("network went away")

        findings = check_reference_integrity(_ARTICLE, fetch_fn=fetch)

        assert findings
        assert all(f.verdict == "UNRESOLVED" for f in findings)


class TestCorpusAcceptance:
    """The gate must flag the defects that actually shipped."""

    def test_flags_both_fabrications_that_reached_production(self) -> None:
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))
        failed = {f.reference_index for f in findings if f.verdict == "FAIL"}

        assert 1 in failed, "reference 1's fabricated author was not caught"
        assert 5 in failed, "reference 5's fabricated title was not caught"

    def test_correct_references_are_not_flagged(self) -> None:
        findings = check_reference_integrity(_ARTICLE, fetch_fn=_fetch(_TRUTH))

        assert "FAIL" not in _verdicts(findings, 3)
