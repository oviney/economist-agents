#!/usr/bin/env python3
"""Tests for editorial judge feedback loops (Story #118).

Validates that judge failures are logged as patterns and injected
as prevention rules for future articles.
"""

import json
from pathlib import Path

import pytest

from scripts.feedback_loop import FeedbackLoop

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def feedback(tmp_path: Path) -> FeedbackLoop:
    """FeedbackLoop with temp storage."""
    return FeedbackLoop(patterns_file=str(tmp_path / "patterns.json"))


@pytest.fixture
def sample_failure() -> dict:
    """A sample editorial judge failure."""
    return {
        "check_name": "image_exists",
        "status": "fail",
        "message": "Image not found: /assets/images/test.png",
        "article_filename": "2026-04-04-test-article.md",
    }


# ═══════════════════════════════════════════════════════════════════════════
# AC1: Log failure patterns
# ═══════════════════════════════════════════════════════════════════════════


class TestPatternLogging:
    """Given a check failure, When detected, Then log the pattern."""

    def test_failure_logged(self, feedback: FeedbackLoop, sample_failure: dict) -> None:
        feedback.log_failure(sample_failure)
        patterns = feedback.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].check_name == "image_exists"

    def test_multiple_failures_logged(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        feedback.log_failure(sample_failure)
        feedback.log_failure({**sample_failure, "check_name": "frontmatter"})
        patterns = feedback.get_patterns()
        assert len(patterns) == 2

    def test_pattern_persisted_to_file(
        self, feedback: FeedbackLoop, sample_failure: dict, tmp_path: Path
    ) -> None:
        feedback.log_failure(sample_failure)
        data = json.loads((tmp_path / "patterns.json").read_text())
        assert len(data["patterns"]) == 1

    def test_pattern_has_timestamp(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        feedback.log_failure(sample_failure)
        pattern = feedback.get_patterns()[0]
        assert pattern.timestamp is not None


# ═══════════════════════════════════════════════════════════════════════════
# AC2: Inject prevention rule
# ═══════════════════════════════════════════════════════════════════════════


class TestRuleInjection:
    """Given a logged pattern, When polish runs, Then prevention rule applied."""

    def test_generates_prevention_rule(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        feedback.log_failure(sample_failure)
        rules = feedback.generate_prevention_rules()
        assert len(rules) >= 1
        assert any("image" in r["description"].lower() for r in rules)

    def test_rule_has_required_fields(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        feedback.log_failure(sample_failure)
        rules = feedback.generate_prevention_rules()
        rule = rules[0]
        assert "id" in rule
        assert "description" in rule
        assert "check_name" in rule
        assert "occurrence_count" in rule


# ═══════════════════════════════════════════════════════════════════════════
# AC3: Apply prevention to new articles
# ═══════════════════════════════════════════════════════════════════════════


class TestPrevention:
    """Given previous failure patterns, When new article processed, Then apply rules."""

    def test_known_pattern_detected_in_new_article(
        self, feedback: FeedbackLoop
    ) -> None:
        # Log a "missing layout" pattern
        feedback.log_failure(
            {
                "check_name": "frontmatter",
                "status": "fail",
                "message": "Missing critical field: layout",
                "article_filename": "old-article.md",
            }
        )
        # Check a new article missing layout
        article = '---\ntitle: "New"\ndate: 2026-04-04\n---\n\nBody'
        warnings = feedback.check_article(article)
        assert len(warnings) >= 1
        assert any("layout" in w.lower() for w in warnings)


# ═══════════════════════════════════════════════════════════════════════════
# AC4: Performance
# ═══════════════════════════════════════════════════════════════════════════


class TestPerformance:
    """Feedback loop completes within 2 minutes."""

    def test_logging_under_100ms(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        import time

        start = time.perf_counter()
        for _ in range(100):
            feedback.log_failure(sample_failure)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0


# ═══════════════════════════════════════════════════════════════════════════
# AC6: Ambiguous patterns escalated
# ═══════════════════════════════════════════════════════════════════════════


class TestEscalation:
    """Given an ambiguous failure, When detected, Then escalate."""

    def test_single_occurrence_not_escalated(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        feedback.log_failure(sample_failure)
        escalations = feedback.get_escalations()
        assert len(escalations) == 0

    def test_repeated_pattern_escalated(
        self, feedback: FeedbackLoop, sample_failure: dict
    ) -> None:
        for _ in range(3):
            feedback.log_failure(sample_failure)
        escalations = feedback.get_escalations()
        assert len(escalations) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
