"""Tests for scripts/citation_verifier.py — citation verification against source URLs."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from citation_verifier import (
    _normalize,
    _stat_appears_in_text,
    verify_citations,
)

# ═══════════════════════════════════════════════════════════════════════════
# Tests: _normalize()
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalize:
    """Tests for text normalization helper."""

    def test_lowercases(self) -> None:
        assert _normalize("ABC") == "abc"

    def test_collapses_whitespace(self) -> None:
        assert _normalize("a   b  c") == "a b c"

    def test_strips_punctuation(self) -> None:
        assert "50%" in _normalize("50% of companies")

    def test_empty_string(self) -> None:
        assert _normalize("") == ""


# ═══════════════════════════════════════════════════════════════════════════
# Tests: _stat_appears_in_text()
# ═══════════════════════════════════════════════════════════════════════════


class TestStatAppearsInText:
    """Tests for fuzzy stat-matching logic."""

    def test_exact_match(self) -> None:
        page = "A study found a 50% reduction in maintenance costs."
        assert _stat_appears_in_text("50% reduction in maintenance costs", page)

    def test_number_with_context_match(self) -> None:
        page = "The survey showed that 72% of teams reported reduced cognitive load."
        assert _stat_appears_in_text(
            "72% of teams reported reduced cognitive load", page
        )

    def test_number_present_but_wrong_context(self) -> None:
        page = "The year 2025 saw 72% growth in cloud spending."
        assert not _stat_appears_in_text(
            "72% of teams reported reduced cognitive load", page
        )

    def test_number_absent(self) -> None:
        page = "The survey found significant improvements."
        assert not _stat_appears_in_text("50% improvement", page)

    def test_no_numbers_in_stat(self) -> None:
        page = "Teams experienced improved velocity."
        assert not _stat_appears_in_text("improved velocity", page)

    def test_case_insensitive(self) -> None:
        page = "Gartner reports a 30% RISE in TCO."
        assert _stat_appears_in_text("30% rise in TCO", page)

    def test_empty_page(self) -> None:
        assert not _stat_appears_in_text("50% reduction", "")

    def test_empty_stat(self) -> None:
        assert not _stat_appears_in_text("", "some page content")


# ═══════════════════════════════════════════════════════════════════════════
# Tests: verify_citations()
# ═══════════════════════════════════════════════════════════════════════════


def _mock_fetch(url_to_content: dict[str, str | None]):
    """Build a mock fetch function that returns content by URL."""

    def fetch(url: str) -> str | None:
        return url_to_content.get(url)

    return fetch


class TestVerifyCitations:
    """Tests for the main verify_citations() function."""

    def test_verified_stat_stays_verified(self) -> None:
        """A stat that appears in its source URL stays verified=True."""
        research: dict[str, Any] = {
            "data_points": [
                {
                    "stat": "50% reduction in maintenance",
                    "source": "TestGuild 2024",
                    "url": "https://example.com/report",
                    "verified": True,
                }
            ],
            "unverified_claims": [],
        }
        fetch = _mock_fetch(
            {
                "https://example.com/report": "The report found a 50% reduction in maintenance costs across 200 teams."
            }
        )
        result = verify_citations(research, fetch_fn=fetch)
        assert result["data_points"][0]["verified"] is True
        assert result["citation_verification"]["verified"] == 1
        assert result["citation_verification"]["failed"] == 0

    def test_fabricated_stat_marked_unverified(self) -> None:
        """A stat NOT found in its source URL is marked verified=False."""
        research: dict[str, Any] = {
            "data_points": [
                {
                    "stat": "80% of companies adopted platform engineering",
                    "source": "Gartner 2026",
                    "url": "https://example.com/gartner",
                    "verified": True,
                }
            ],
            "unverified_claims": [],
        }
        fetch = _mock_fetch(
            {
                "https://example.com/gartner": "This paper discusses cloud infrastructure trends and cost optimization."
            }
        )
        result = verify_citations(research, fetch_fn=fetch)
        assert result["data_points"][0]["verified"] is False
        assert result["citation_verification"]["failed"] == 1
        assert any("80%" in c for c in result["unverified_claims"])

    def test_no_url_marks_unverified(self) -> None:
        """Data points without a URL are marked unverified."""
        research: dict[str, Any] = {
            "data_points": [
                {
                    "stat": "60% of teams struggle",
                    "source": "Unknown",
                    "url": "",
                    "verified": True,
                }
            ],
            "unverified_claims": [],
        }
        result = verify_citations(research, fetch_fn=_mock_fetch({}))
        assert result["data_points"][0]["verified"] is False
        assert len(result["unverified_claims"]) == 1

    def test_fetch_failure_preserves_verified_flag(self) -> None:
        """Network failures don't change the verified flag (benefit of doubt)."""
        research: dict[str, Any] = {
            "data_points": [
                {
                    "stat": "50% reduction",
                    "source": "Report",
                    "url": "https://down.example.com",
                    "verified": True,
                }
            ],
            "unverified_claims": [],
        }
        fetch = _mock_fetch({"https://down.example.com": None})
        result = verify_citations(research, fetch_fn=fetch)
        # Verified flag unchanged (couldn't fetch, not a definitive failure)
        assert result["data_points"][0]["verified"] is True

    def test_headline_stat_verified(self) -> None:
        """Headline stat with URL is also checked."""
        research: dict[str, Any] = {
            "headline_stat": {
                "value": "62% of enterprises report painful headaches",
                "source": "Gartner",
                "url": "https://example.com/headline",
                "verified": True,
            },
            "data_points": [],
            "unverified_claims": [],
        }
        fetch = _mock_fetch(
            {
                "https://example.com/headline": "This page discusses vendor management strategies."
            }
        )
        result = verify_citations(research, fetch_fn=fetch)
        assert result["headline_stat"]["verified"] is False
        assert any("HEADLINE" in c for c in result["unverified_claims"])

    def test_empty_data_points(self) -> None:
        """No data points → no verification needed."""
        research: dict[str, Any] = {"data_points": [], "unverified_claims": []}
        result = verify_citations(research, fetch_fn=_mock_fetch({}))
        assert result["citation_verification"]["total_checked"] == 0

    def test_mixed_batch(self) -> None:
        """Mix of verified, fabricated, and URL-less data points."""
        research: dict[str, Any] = {
            "data_points": [
                {
                    "stat": "50% reduction",
                    "url": "https://example.com/real",
                    "verified": True,
                },
                {
                    "stat": "99% adoption",
                    "url": "https://example.com/fake",
                    "verified": True,
                },
                {"stat": "Unknown stat", "url": "", "verified": True},
            ],
            "unverified_claims": [],
        }
        fetch = _mock_fetch(
            {
                "https://example.com/real": "The study found a 50% reduction in costs.",
                "https://example.com/fake": "This page is about gardening tips.",
            }
        )
        result = verify_citations(research, fetch_fn=fetch)
        assert result["data_points"][0]["verified"] is True
        assert result["data_points"][1]["verified"] is False
        assert result["data_points"][2]["verified"] is False
        assert result["citation_verification"]["verified"] == 1
        assert result["citation_verification"]["failed"] == 2

    def test_preserves_existing_unverified_claims(self) -> None:
        """Existing unverified_claims are preserved, not overwritten."""
        research: dict[str, Any] = {
            "data_points": [
                {"stat": "fake stat", "url": "https://example.com/x", "verified": True}
            ],
            "unverified_claims": ["Pre-existing claim"],
        }
        fetch = _mock_fetch({"https://example.com/x": "Unrelated content."})
        result = verify_citations(research, fetch_fn=fetch)
        assert "Pre-existing claim" in result["unverified_claims"]
        assert len(result["unverified_claims"]) == 2
