"""The owner's brief is the input (B-048 D1): parsing, the one hard requirement, and
what the writer and the researcher are handed."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_sdk.brief import OwnerBriefError, load_owner_brief, recent_verdicts

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


class TestParsingIsFenceAndLevelAware:
    def test_a_hash_inside_a_code_block_does_not_end_the_take(
        self, tmp_path: Path
    ) -> None:
        text = (
            "# T\n\n## My take\n\nBefore.\n\n```yaml\n# not a heading\nkey: v\n```\n\n"
            "After.\n\n## What I've seen\n\nY.\n"
        )
        brief = load_owner_brief(_write(tmp_path, text))

        assert brief.take.startswith("Before.") and brief.take.endswith("After.")
        assert "# not a heading" in brief.take
        assert brief.seen == "Y."

    def test_a_subsection_stays_inside_its_section(self, tmp_path: Path) -> None:
        text = (
            "# T\n\n## My take\n\nPart one.\n\n### Background\n\nPart two.\n\n"
            "## What I've seen\n\nY.\n"
        )
        brief = load_owner_brief(_write(tmp_path, text))

        assert "Part one." in brief.take and "Part two." in brief.take
        assert brief.seen == "Y."

    def test_crlf_line_endings_parse(self, tmp_path: Path) -> None:
        brief = load_owner_brief(_write(tmp_path, FULL.replace("\n", "\r\n")))

        assert brief.take.startswith("Coverage targets measure visitation")
        assert "bank in 2019" in brief.seen

    def test_a_verbatim_template_copy_has_no_take(self, tmp_path: Path) -> None:
        template = Path("briefs/TEMPLATE.md").read_text(encoding="utf-8")

        with pytest.raises(OwnerBriefError, match="My take"):
            load_owner_brief(_write(tmp_path, template, "my-post.md"))

    def test_placeholder_sections_count_as_missing(self, tmp_path: Path) -> None:
        text = "# T\n\n## My take\n\nX.\n\n## What I've seen\n\n<Two or three experiences.>\n"
        brief = load_owner_brief(_write(tmp_path, text))

        assert brief.seen == ""
        assert "seen" in brief.missing


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
        assert "Never invent" in block
        assert "counterpoint" in block and "mutation kill rate" in block

    def test_writer_block_omits_sections_the_owner_left_empty(
        self, tmp_path: Path
    ) -> None:
        block = load_owner_brief(
            _write(tmp_path, "# T\n\n## My take\n\nX.\n")
        ).writer_block()

        assert "WHAT THE AUTHOR HAS SEEN" not in block
        assert "WHAT WOULD CHANGE" not in block
        # The prohibition is unconditional: it matters most when there is nothing to quote.
        assert "Never invent" in block

    def test_research_focus_asks_for_evidence_both_ways(self, tmp_path: Path) -> None:
        focus = load_owner_brief(_write(tmp_path, FULL)).research_focus()

        assert "thesis" in focus.lower()
        assert "counter-evidence" in focus
        assert "arxiv.org" in focus


class TestVerdictsCloseTheLoop:
    """B-048 D5: the owner's post-publish verdicts steer the next draft."""

    def test_no_briefs_dir_means_no_context(self, tmp_path: Path) -> None:
        assert recent_verdicts(tmp_path / "nowhere") == ""

    def test_briefs_without_verdicts_mean_no_context(self, tmp_path: Path) -> None:
        _write(tmp_path, FULL)
        _write(tmp_path, "# T\n\n## My take\n\nX.\n", "TEMPLATE.md")

        assert recent_verdicts(tmp_path) == ""

    def test_the_template_is_never_a_verdict(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "# T\n\n## My take\n\nX.\n\n## Verdict\n\n<Leave empty>\n",
            "TEMPLATE.md",
        )

        assert recent_verdicts(tmp_path) == ""

    def test_newest_five_verdicts_newest_first(self, tmp_path: Path) -> None:
        import os

        for n in range(7):
            p = _write(
                tmp_path,
                f"# T{n}\n\n## My take\n\nX.\n\n## Verdict\n\n{n}/5 — note {n}\n",
                f"post-{n}.md",
            )
            os.utime(p, (1_700_000_000 + n, 1_700_000_000 + n))

        block = recent_verdicts(tmp_path, limit=5)

        assert block.splitlines()[0] == "- post-6: 6/5 — note 6"
        assert len(block.splitlines()) == 5
        assert "post-0" not in block and "post-1" not in block

    def test_author_context_is_the_verdict_block(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from src.agent_sdk import stage3_runner

        _write(
            tmp_path,
            "# T\n\n## My take\n\nX.\n\n## Verdict\n\n4/5 — cut the opening anecdote\n",
            "post.md",
        )
        monkeypatch.setattr(
            stage3_runner, "recent_verdicts", lambda: recent_verdicts(tmp_path)
        )

        assert "cut the opening anecdote" in stage3_runner._fetch_author_context("x")

    def test_a_copied_template_is_not_a_verdict(self, tmp_path: Path) -> None:
        template = Path("briefs/TEMPLATE.md").read_text(encoding="utf-8")
        _write(tmp_path, template, "my-post.md")

        assert recent_verdicts(tmp_path) == ""
