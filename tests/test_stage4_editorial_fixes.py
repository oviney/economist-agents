#!/usr/bin/env python3
"""Tests for Stage4Crew deterministic editorial post-processing."""

import pytest

from src.crews.stage4_crew import _apply_editorial_fixes


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
