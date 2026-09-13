"""The owner's brief is the input (B-048 D1): parsing, the one hard requirement, and
what the writer and the researcher are handed."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_sdk.brief import OwnerBriefError, load_owner_brief

FULL = """# Coverage mandates are a board-level comfort blanket

## My take

Coverage targets measure visitation, not judgement. Boards adopt them because the
number is legible, and the number is legible because it means nothing.

## What I've seen

At a bank in 2019 an 80% mandate arrived by memo. Within a quarter the suite had
doubled and the escaped-defect rate had not moved.

## Where I disagree

With the vendor line that coverage is "a floor". A floor you can raise by deleting
duplicate code is not a floor.

## What would change my mind

A codebase where high line coverage coincides with a high mutation kill rate at scale.

## Sources I trust on this

https://arxiv.org/abs/2309.02395

## Verdict

"""


def _write(
    tmp_path: Path, text: str, name: str = "coverage-comfort-blanket.md"
) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestParsing:
    def test_reads_every_template_section(self, tmp_path: Path) -> None:
        brief = load_owner_brief(_write(tmp_path, FULL))

        assert brief.title == "Coverage mandates are a board-level comfort blanket"
        assert brief.take.startswith("Coverage targets measure visitation")
        assert "bank in 2019" in brief.seen
        assert "vendor line" in brief.disagree
        assert "mutation kill rate" in brief.change_mind
        assert "arxiv.org" in brief.sources
        assert brief.verdict == ""
        assert brief.missing == []

    def test_slug_is_the_file_stem(self, tmp_path: Path) -> None:
        assert (
            load_owner_brief(_write(tmp_path, FULL)).slug == "coverage-comfort-blanket"
        )

    def test_headings_match_by_keyword_and_case(self, tmp_path: Path) -> None:
        text = "# T\n\n## The Take\n\nX.\n\n## Things I have SEEN\n\nY.\n"
        brief = load_owner_brief(_write(tmp_path, text))

        assert brief.take == "X."
        assert brief.seen == "Y."

    def test_title_falls_back_to_the_stem(self, tmp_path: Path) -> None:
        brief = load_owner_brief(
            _write(tmp_path, "## My take\n\nX.\n", "flaky-tests.md")
        )

        assert brief.title == "flaky tests"


class TestTheOneHardRequirement:
    def test_a_brief_without_a_take_cannot_run(self, tmp_path: Path) -> None:
        with pytest.raises(OwnerBriefError, match="My take"):
            load_owner_brief(_write(tmp_path, "# T\n\n## What I've seen\n\nY.\n"))

    def test_an_empty_take_is_no_take(self, tmp_path: Path) -> None:
        with pytest.raises(OwnerBriefError):
            load_owner_brief(
                _write(tmp_path, "# T\n\n## My take\n\n## What I've seen\n\nY.\n")
            )

    def test_a_missing_file_says_so(self, tmp_path: Path) -> None:
        with pytest.raises(OwnerBriefError, match="No brief"):
            load_owner_brief(tmp_path / "nope.md")

    def test_optional_sections_are_reported_not_required(self, tmp_path: Path) -> None:
        brief = load_owner_brief(_write(tmp_path, "# T\n\n## My take\n\nX.\n"))

        assert brief.missing == ["seen", "disagree", "change_mind"]


class TestWhatTheMachinesAreHanded:
    def test_writer_block_makes_the_take_the_spine(self, tmp_path: Path) -> None:
        block = load_owner_brief(_write(tmp_path, FULL)).writer_block()

        assert "AUTHOR'S BRIEF" in block
        assert "THESIS" in block and "Coverage targets measure visitation" in block
        assert "first person" in block and "bank in 2019" in block
        assert "never invent additional experiences" in block
        assert "counterpoint" in block and "mutation kill rate" in block

    def test_writer_block_omits_sections_the_owner_left_empty(
        self, tmp_path: Path
    ) -> None:
        block = load_owner_brief(
            _write(tmp_path, "# T\n\n## My take\n\nX.\n")
        ).writer_block()

        assert "WHAT THE AUTHOR HAS SEEN" not in block
        assert "COUNTERPOINT" not in block.upper() or "WHAT WOULD CHANGE" not in block

    def test_research_focus_asks_for_evidence_both_ways(self, tmp_path: Path) -> None:
        focus = load_owner_brief(_write(tmp_path, FULL)).research_focus()

        assert "thesis" in focus.lower()
        assert "counter-evidence" in focus
        assert "arxiv.org" in focus
