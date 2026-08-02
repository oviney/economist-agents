"""B-042: the packet is the hand-off, so it must be complete and honest.

A packet that omits the chart provenance, or that says "no chart needed" without
saying what was searched, sends the owner back to the terminal — which is the
failure this whole item is meant to remove.

Spec: docs/specs/mandatory-chart-setpoint.md — S4, S5, AC7, AC8.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.agent_sdk import review_packet
from src.agent_sdk.review_packet import build_packet, notify, write_packet


@dataclass
class _Result:
    """Stands in for PipelineResult — only the fields a packet reads."""

    topic: str = "testing shortcuts"
    slug: str = "testing-shortcuts"
    image_prompt: str = "An editorial illustration of a deadline."
    chart_proposal: dict[str, Any] | None = None
    chart_spec_path: Path | None = None
    editorial_score: int = 82
    gates_passed: int = 5
    publication_validator_passed: bool = True
    publication_validator_issues: list[dict[str, str]] = field(default_factory=list)
    total_cost_usd: float = 0.42
    article_chars: int = 7000


_PROPOSAL = {
    "title": "",
    "subtitle": "",
    "data": [
        {
            "metric": "",
            "value": 40,
            "unit": "%",
            "source": "brief: 'up to 40% of engineering capacity is consumed'",
        }
    ],
    "source": "",
}


class TestTheChartSectionIsHonestBothWays:
    def test_no_proposal_says_so_and_says_what_was_searched(self) -> None:
        """The absence must be a statement, not a blank.

        "No chart" used to be indistinguishable from "the chart step broke",
        which is why a CRITICAL gate felt safe. The packet has to close that
        gap in words the owner can act on.
        """
        packet = build_packet(_Result(), Path("output/posts/x.md"))
        assert "No chart proposed" in packet
        assert "no numeric claim" in packet
        # The scope limit is stated, so a missed unit-less count is visibly the
        # tool's known blind spot rather than a silent omission.
        assert "Bare counts and years are deliberately not" in packet

    def test_a_proposal_carries_provenance_for_every_row(self) -> None:
        result = _Result(chart_proposal=_PROPOSAL)
        packet = build_packet(result, Path("output/posts/x.md"))
        assert "40" in packet
        assert "up to 40% of engineering capacity is consumed" in packet
        assert "none was generated" in packet

    def test_a_proposal_says_what_the_owner_must_supply(self) -> None:
        packet = build_packet(_Result(chart_proposal=_PROPOSAL), Path("x.md"))
        assert "empty by design" in packet
        assert "make art SLUG=testing-shortcuts" in packet


class TestThePacketSaysWhatIsStillOutstanding:
    def test_the_hero_target_path_and_webp_rule_are_stated(self) -> None:
        packet = build_packet(_Result(), Path("x.md"))
        assert "output/posts/images/testing-shortcuts-hero.svg" in packet
        assert ".webp" in packet

    def test_the_hero_brief_is_inlined(self) -> None:
        packet = build_packet(_Result(), Path("x.md"))
        assert "An editorial illustration of a deadline." in packet

    def test_a_pass_is_not_claimed_to_mean_complete(self) -> None:
        """The trap this replaces: a green validator used to imply publishable."""
        packet = build_packet(_Result(), Path("x.md"))
        assert "not that the post is complete" in packet

    def test_the_permanent_slug_is_flagged(self) -> None:
        assert "permanent URL" in build_packet(_Result(), Path("x.md"))

    def test_outstanding_validator_issues_are_listed(self) -> None:
        result = _Result(
            publication_validator_passed=False,
            publication_validator_issues=[
                {"severity": "HIGH", "check": "ending_quality", "message": "weak"}
            ],
        )
        packet = build_packet(result, Path("x.md"))
        assert "ending_quality" in packet
        assert "FAILED" in packet

    def test_the_next_commands_are_in_order_and_end_at_review(self) -> None:
        packet = build_packet(_Result(), Path("x.md"))
        assert packet.index("make art") < packet.index("--mode review")
        assert packet.index("--mode review") < packet.index("make publish")


class TestWritePacket:
    def test_it_lands_beside_the_article(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(review_packet, "PACKETS_DIR", tmp_path / "posts")
        path = write_packet(_Result(), tmp_path / "posts" / "testing-shortcuts.md")
        assert path.name == "testing-shortcuts.review.md"
        assert "Review packet" in path.read_text()


class TestNotifyCannotFailAGoodRun:
    """AC8. The run has already succeeded by the time this is called."""

    def test_missing_osascript_is_not_an_error(self) -> None:
        with patch.object(review_packet.shutil, "which", return_value=None):
            assert notify("t", "m") is False

    def test_a_timeout_is_swallowed(self) -> None:
        with (
            patch.object(review_packet.shutil, "which", return_value="/usr/bin/osa"),
            patch.object(
                review_packet.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("osa", 5),
            ),
        ):
            assert notify("t", "m") is False

    def test_a_nonzero_exit_is_swallowed(self) -> None:
        with (
            patch.object(review_packet.shutil, "which", return_value="/usr/bin/osa"),
            patch.object(
                review_packet.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, "osa"),
            ),
        ):
            assert notify("t", "m") is False

    def test_quotes_in_the_topic_cannot_break_the_script(self) -> None:
        captured: dict[str, Any] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return None

        with (
            patch.object(review_packet.shutil, "which", return_value="/usr/bin/osa"),
            patch.object(review_packet.subprocess, "run", side_effect=fake_run),
        ):
            assert notify('say "hi"', 'and "bye"') is True

        script = captured["cmd"][2]
        # Exactly four quotes: the two AppleScript string delimiters per argument.
        assert script.count('"') == 4, script
