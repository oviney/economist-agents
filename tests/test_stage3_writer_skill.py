#!/usr/bin/env python3
"""
Tests for Stage3Crew Writer Agent economist-writing skill integration.

Validates that the writer backstory and task description in stage3_crew.py
satisfy Story 17.1 acceptance criteria:
- Backstory references skills/economist-writing/SKILL.md
- Prompt enforces: thesis in first 2 paragraphs, no lists, no hedging, name real companies
- Prompt requires: 3-4 headings max, provocative title, vivid ending
- Prompt bans: abstract openings, generic attribution, summary closings
"""

from pathlib import Path

import pytest

STAGE3_CREW_PATH = Path(__file__).parent.parent / "src" / "crews" / "stage3_crew.py"


@pytest.fixture(scope="module")
def stage3_source() -> str:
    """Read stage3_crew.py source once for all tests."""
    return STAGE3_CREW_PATH.read_text()


class TestWriterBackstorySkillReference:
    """Verify writer backstory references the economist-writing skill."""

    def test_backstory_references_skill_md(self, stage3_source: str) -> None:
        """Writer backstory must reference skills/economist-writing/SKILL.md."""
        assert "skills/economist-writing/SKILL.md" in stage3_source

    def test_backstory_references_10_rules(self, stage3_source: str) -> None:
        """Backstory must reference the 10 rules in SKILL.md."""
        assert "10 rules" in stage3_source


class TestWriterBackstoryThesisRequirement:
    """Verify backstory enforces thesis in first two paragraphs."""

    def test_backstory_requires_thesis(self, stage3_source: str) -> None:
        """Backstory must require a thesis argument."""
        assert "THESIS" in stage3_source

    def test_backstory_thesis_in_first_paragraphs(self, stage3_source: str) -> None:
        """Backstory must require thesis in first two paragraphs."""
        assert "first two paragraphs" in stage3_source

    def test_backstory_thesis_is_debatable(self, stage3_source: str) -> None:
        """Backstory must require a debatable argument, not a topic."""
        assert "debatable" in stage3_source


class TestWriterBackstoryNoLists:
    """Verify backstory bans numbered and bulleted lists."""

    def test_backstory_bans_numbered_lists(self, stage3_source: str) -> None:
        """Backstory must ban numbered lists."""
        assert "Numbered lists" in stage3_source or "numbered lists" in stage3_source

    def test_backstory_bans_bulleted_lists(self, stage3_source: str) -> None:
        """Backstory must ban bulleted lists."""
        assert "bulleted lists" in stage3_source or "Bulleted lists" in stage3_source

    def test_backstory_bans_lists_section(self, stage3_source: str) -> None:
        """Backstory must have a NO LISTS ban section."""
        assert "NO LISTS" in stage3_source


class TestWriterBackstoryNoHedging:
    """Verify backstory bans hedging phrases."""

    def test_backstory_bans_hedging_phrases(self, stage3_source: str) -> None:
        """Backstory must include BANNED HEDGING PHRASES section."""
        assert "BANNED HEDGING" in stage3_source or "hedging" in stage3_source.lower()

    def test_backstory_bans_one_might(self, stage3_source: str) -> None:
        """Backstory must ban 'one might' hedging phrase."""
        assert "one might" in stage3_source

    def test_backstory_bans_it_is_worth_noting(self, stage3_source: str) -> None:
        """Backstory must ban 'it is worth noting'."""
        assert "it is worth noting" in stage3_source

    def test_backstory_bans_it_would_be_misguided(self, stage3_source: str) -> None:
        """Backstory must ban 'it would be misguided'."""
        assert "it would be misguided" in stage3_source


class TestWriterBackstoryNameNames:
    """Verify backstory requires naming real companies and individuals."""

    def test_backstory_requires_named_companies(self, stage3_source: str) -> None:
        """Backstory must require at least 2 named companies or individuals."""
        assert (
            "named companies" in stage3_source or "named individuals" in stage3_source
        )

    def test_backstory_bans_generic_attribution(self, stage3_source: str) -> None:
        """Backstory must ban generic attribution like 'organisations', 'experts say'."""
        assert "BANNED GENERIC" in stage3_source

    def test_backstory_bans_experts_say(self, stage3_source: str) -> None:
        """Backstory must ban 'experts say'."""
        assert "experts say" in stage3_source

    def test_backstory_bans_studies_show(self, stage3_source: str) -> None:
        """Backstory must ban 'studies show'."""
        assert "studies show" in stage3_source


class TestWriterBackstoryHeadings:
    """Verify backstory requires 3-4 headings maximum."""

    def test_backstory_limits_headings(self, stage3_source: str) -> None:
        """Backstory must specify 3-4 headings maximum."""
        assert "3-4 headings" in stage3_source

    def test_backstory_headings_are_noun_phrases(self, stage3_source: str) -> None:
        """Backstory must require headings to be noun phrases."""
        assert "noun phrases" in stage3_source


class TestWriterBackstoryTitle:
    """Verify backstory requires provocative title."""

    def test_backstory_requires_provocative_title(self, stage3_source: str) -> None:
        """Backstory must require a provocative and memorable title."""
        assert "Provocative" in stage3_source or "provocative" in stage3_source

    def test_backstory_title_rules_present(self, stage3_source: str) -> None:
        """Backstory must include TITLE RULES."""
        assert "TITLE RULES" in stage3_source

    def test_backstory_bans_why_how_titles(self, stage3_source: str) -> None:
        """Backstory must ban titles starting with 'Why' or 'How'."""
        assert '"Why"' in stage3_source or '"How"' in stage3_source


class TestWriterBackstoryVividEnding:
    """Verify backstory requires vivid ending."""

    def test_backstory_requires_vivid_ending(self, stage3_source: str) -> None:
        """Backstory must require a vivid prediction/metaphor/provocation as ending."""
        assert "vivid" in stage3_source

    def test_backstory_bans_summary_closings(self, stage3_source: str) -> None:
        """Backstory must ban summary closings."""
        assert "BANNED CLOSINGS" in stage3_source

    def test_backstory_bans_in_conclusion(self, stage3_source: str) -> None:
        """Backstory must ban 'In conclusion'."""
        assert "In conclusion" in stage3_source

    def test_backstory_bans_only_time_will_tell(self, stage3_source: str) -> None:
        """Backstory must ban 'Only time will tell'."""
        assert "Only time will tell" in stage3_source


class TestWriterBackstoryAbstractOpenings:
    """Verify backstory bans abstract openings."""

    def test_backstory_bans_abstract_openings(self, stage3_source: str) -> None:
        """Backstory must ban abstract opening patterns."""
        assert "BANNED OPENINGS" in stage3_source

    def test_backstory_bans_in_todays_world(self, stage3_source: str) -> None:
        """Backstory must ban 'In today's world' opening."""
        assert "In today" in stage3_source

    def test_backstory_bans_its_no_secret(self, stage3_source: str) -> None:
        """Backstory must ban 'It's no secret' opening."""
        assert "It's no secret" in stage3_source


class TestWriterTaskDescription:
    """Verify the writer task description enforces all skill rules."""

    def test_task_references_skill_md(self, stage3_source: str) -> None:
        """Writer task must reference skills/economist-writing/SKILL.md."""
        assert "skills/economist-writing/SKILL.md" in stage3_source

    def test_task_requires_thesis(self, stage3_source: str) -> None:
        """Writer task description must require a thesis."""
        assert "THESIS" in stage3_source

    def test_task_specifies_headings_limit(self, stage3_source: str) -> None:
        """Writer task must specify 3-4 headings maximum."""
        assert "3-4 headings" in stage3_source

    def test_task_bans_lists(self, stage3_source: str) -> None:
        """Writer task must ban lists."""
        assert "LISTS" in stage3_source

    def test_task_bans_hedging(self, stage3_source: str) -> None:
        """Writer task must ban hedging phrases via the AUTHORITY section label."""
        assert "AUTHORITY" in stage3_source

    def test_task_requires_named_companies(self, stage3_source: str) -> None:
        """Writer task must require named companies/individuals."""
        assert "NAMES" in stage3_source

    def test_task_requires_vivid_ending(self, stage3_source: str) -> None:
        """Writer task must require a vivid ending."""
        assert "ENDING" in stage3_source

    def test_task_bans_in_conclusion_ending(self, stage3_source: str) -> None:
        """Writer task must ban 'In conclusion' type endings."""
        assert "In conclusion" in stage3_source

    def test_task_expected_output_mentions_thesis(self, stage3_source: str) -> None:
        """Writer task expected_output must mention thesis requirement."""
        assert "thesis in first two paragraphs" in stage3_source

    def test_task_expected_output_mentions_headings(self, stage3_source: str) -> None:
        """Writer task expected_output must mention headings limit."""
        assert "3-4 headings maximum" in stage3_source
