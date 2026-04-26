#!/usr/bin/env python3
"""Tests for Stage4Crew deterministic editorial post-processing."""

import pytest

from src.agent_sdk._shared import (
    _BANNED_CLOSINGS,
    _enforce_heading_limit,
)
from src.agent_sdk._shared import (
    apply_editorial_fixes as _apply_editorial_fixes,
)


class TestBritishSpelling:
    """British spelling replacements."""

    def test_organization_to_organisation(self) -> None:
        result = _apply_editorial_fixes("The organization grew.")
        assert "organisation" in result
        assert "organization" not in result

    def test_optimize_to_optimise(self) -> None:
        result = _apply_editorial_fixes("We optimize the process.")
        assert "optimise" in result

    def test_analyze_to_analyse(self) -> None:
        result = _apply_editorial_fixes("They analyze the data.")
        assert "analyse" in result

    def test_behavior_to_behaviour(self) -> None:
        result = _apply_editorial_fixes("User behavior changed.")
        assert "behaviour" in result


class TestBannedPhrases:
    """Banned phrase removal."""

    def test_game_changer_removed(self) -> None:
        result = _apply_editorial_fixes("This is a game-changer for testing.")
        assert "game-changer" not in result

    def test_paradigm_shift_removed(self) -> None:
        result = _apply_editorial_fixes("A paradigm shift in quality.")
        assert "paradigm shift" not in result

    def test_case_insensitive_removal(self) -> None:
        result = _apply_editorial_fixes("This is a GAME-CHANGER.")
        assert "game-changer" not in result.lower()


class TestExclamationPoints:
    """Exclamation point removal."""

    def test_exclamation_replaced_with_period(self) -> None:
        result = _apply_editorial_fixes("This is great!")
        assert "!" not in result
        assert "This is great." in result

    def test_exclamation_preserved_in_code_blocks(self) -> None:
        article = "Text here.\n\n```python\nprint('hello!')\n```\n\nMore text!"
        result = _apply_editorial_fixes(article)
        assert "hello!" in result  # preserved in code block
        assert result.endswith("More text.")  # fixed outside code block


class TestDateFix:
    """YAML frontmatter date correction."""

    def test_wrong_date_corrected(self) -> None:
        article = '---\nlayout: post\ntitle: "Test"\ndate: 2024-01-01\n---\n\nContent'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert "date: 2026-04-03" in result
        assert "date: 2024-01-01" not in result

    def test_correct_date_unchanged(self) -> None:
        article = '---\nlayout: post\ntitle: "Test"\ndate: 2026-04-03\n---\n\nContent'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert "date: 2026-04-03" in result

    def test_no_date_fix_when_not_provided(self) -> None:
        article = "---\nlayout: post\ndate: 2024-01-01\n---\n\nContent"
        result = _apply_editorial_fixes(article, current_date=None)
        assert "date: 2024-01-01" in result


class TestArticleIntegrity:
    """Verify fixes don't destroy article content."""

    def test_frontmatter_preserved(self) -> None:
        article = '---\nlayout: post\ntitle: "Quality Engineering"\ndate: 2026-04-03\n---\n\nContent here.'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert result.startswith("---\n")
        assert "layout: post" in result
        assert 'title: "Quality Engineering"' in result
        assert "Content here." in result

    def test_long_article_not_truncated(self) -> None:
        body = " ".join(["word"] * 1000)
        article = f'---\ntitle: "Test"\ndate: 2026-04-03\n---\n\n{body}'
        result = _apply_editorial_fixes(article, current_date="2026-04-03")
        assert len(result.split()) >= 1000

    def test_double_spaces_cleaned(self) -> None:
        result = _apply_editorial_fixes("This is a  game-changer  for testing.")
        assert "  " not in result


class TestHedgingPhrases:
    """Hedging phrase removal (SKILL.md Rule 4)."""

    def test_it_is_worth_noting_removed(self) -> None:
        result = _apply_editorial_fixes("It is worth noting that quality matters.")
        assert "it is worth noting" not in result.lower()

    def test_it_should_be_noted_removed(self) -> None:
        result = _apply_editorial_fixes("It should be noted that costs have risen.")
        assert "it should be noted" not in result.lower()

    def test_one_might_removed(self) -> None:
        result = _apply_editorial_fixes("One might expect the results to be clear.")
        assert "one might" not in result.lower()

    def test_it_would_be_misguided_removed(self) -> None:
        result = _apply_editorial_fixes(
            "It would be misguided to ignore these findings."
        )
        assert "it would be misguided" not in result.lower()

    def test_in_practical_terms_removed(self) -> None:
        result = _apply_editorial_fixes(
            "In practical terms, this means faster delivery."
        )
        assert "in practical terms" not in result.lower()


class TestVerbosePadding:
    """Verbose padding removal (SKILL.md Rule 6)."""

    def test_it_goes_without_saying_removed(self) -> None:
        result = _apply_editorial_fixes(
            "It goes without saying that testing is important."
        )
        assert "it goes without saying" not in result.lower()

    def test_needless_to_say_removed(self) -> None:
        result = _apply_editorial_fixes("Needless to say, quality is paramount.")
        assert "needless to say" not in result.lower()

    def test_as_mentioned_earlier_removed(self) -> None:
        result = _apply_editorial_fixes("As mentioned earlier, the team struggled.")
        assert "as mentioned earlier" not in result.lower()

    def test_content_retained_after_padding_removal(self) -> None:
        result = _apply_editorial_fixes("Needless to say, the framework works well.")
        assert "the framework works well" in result


class TestCategoryNormalization:
    """Category casing normalization to kebab-case."""

    def test_title_case_to_kebab(self) -> None:
        article = '---\ncategories: ["Quality Engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "quality-engineering" in result
        assert "Quality Engineering" not in result

    def test_mixed_case_to_kebab(self) -> None:
        article = '---\ncategories: ["software engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "software-engineering" in result

    def test_already_kebab_unchanged(self) -> None:
        article = '---\ncategories: ["quality-engineering"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "quality-engineering" in result

    def test_test_automation_normalized(self) -> None:
        article = '---\ncategories: ["Test Automation"]\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "test-automation" in result


class TestChartAutoEmbed:
    """Auto-insert chart embed when missing."""

    def test_chart_inserted_before_references(self) -> None:
        article = (
            "---\nimage: /assets/images/my-slug.png\n---\n"
            "Article body.\n\n## References\n\n1. Source"
        )
        result = _apply_editorial_fixes(article)
        assert "![Chart](/assets/charts/my-slug.png)" in result
        assert result.index("![Chart]") < result.index("## References")

    def test_chart_not_doubled_if_present(self) -> None:
        article = (
            "---\nimage: /assets/images/my-slug.png\n---\n"
            "Body.\n\n![Chart](/assets/charts/my-slug.png)\n\n## References\n"
        )
        result = _apply_editorial_fixes(article)
        assert result.count("![Chart]") == 1

    def test_no_chart_if_no_image_field(self) -> None:
        article = "---\ntitle: Test\n---\nBody.\n\n## References\n"
        result = _apply_editorial_fixes(article)
        assert "![Chart]" not in result

    def test_chart_appended_if_no_references_section(self) -> None:
        article = (
            "---\nimage: /assets/images/my-slug.png\n---\n"
            "Article body with no references."
        )
        result = _apply_editorial_fixes(article)
        assert "![Chart](/assets/charts/my-slug.png)" in result


class TestNewHedgingPhrases:
    """New hedging phrases added in Story 1."""

    def test_one_suspects_removed(self) -> None:
        """Article containing 'One suspects' has the phrase stripped."""
        result = _apply_editorial_fixes("One suspects the future is bleak.")
        assert "One suspects" not in result
        assert "the future is bleak" in result

    def test_it_is_clear_that_removed(self) -> None:
        """Article containing 'it is clear that' has the phrase stripped."""
        result = _apply_editorial_fixes("It is clear that progress has stalled.")
        assert "it is clear that" not in result.lower()
        assert "progress has stalled" in result

    def test_one_suspects_in_closing_banned(self) -> None:
        """'One suspects' appears in _BANNED_CLOSINGS."""
        assert "One suspects" in _BANNED_CLOSINGS


class TestHeadingLimitEnforcement:
    """Heading count enforcement (Story 3)."""

    def test_headings_under_limit_unchanged(self) -> None:
        """Article with 3 headings passes through unchanged."""
        article = (
            "---\ntitle: Test\n---\n\n"
            "## Introduction\n\nParagraph one.\n\n"
            "## Analysis\n\nParagraph two.\n\n"
            "## Conclusion\n\nParagraph three.\n"
        )
        result = _enforce_heading_limit(article)
        assert result.count("\n## ") == 3

    def test_headings_over_limit_merged(self) -> None:
        """Article with 6 headings is reduced to 4."""
        sections = []
        line = "Line.\n"
        for i in range(6):
            body = line * (i + 1)
            sections.append(f"## Section {i + 1}\n\n{body}")
        article = "---\ntitle: Test\n---\n\n" + "\n".join(sections)
        result = _enforce_heading_limit(article)
        heading_count = sum(
            1
            for line in result.split("\n")
            if line.startswith("## ") and line.strip() != "## References"
        )
        assert heading_count == 4

    def test_references_heading_not_counted(self) -> None:
        """Article with 4 body headings + ## References stays unchanged."""
        article = (
            "---\ntitle: Test\n---\n\n"
            "## Introduction\n\nText.\n\n"
            "## Analysis\n\nText.\n\n"
            "## Results\n\nText.\n\n"
            "## Outlook\n\nText.\n\n"
            "## References\n\n1. Source A\n"
        )
        result = _enforce_heading_limit(article)
        # All 4 body headings + References should remain
        all_headings = [line for line in result.split("\n") if line.startswith("## ")]
        assert len(all_headings) == 5
        body_headings = [h for h in all_headings if h.strip() != "## References"]
        assert len(body_headings) == 4


class TestDescriptionTruncation:
    """Description field truncation to 160 chars."""

    def test_long_description_truncated(self) -> None:
        desc = "A" * 200
        article = f'---\ndescription: "{desc}"\n---\nBody'
        result = _apply_editorial_fixes(article)
        # Extract description from result
        import re

        match = re.search(r'description:\s*"([^"]+)"', result)
        assert match is not None
        assert len(match.group(1)) <= 160
        assert match.group(1).endswith("...")

    def test_short_description_unchanged(self) -> None:
        article = '---\ndescription: "A short description."\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert "A short description." in result

    def test_exactly_160_unchanged(self) -> None:
        desc = "A" * 160
        article = f'---\ndescription: "{desc}"\n---\nBody'
        result = _apply_editorial_fixes(article)
        assert desc in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
