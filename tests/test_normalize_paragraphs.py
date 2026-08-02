"""BUG-071: a heading needs a blank line above it, or kramdown eats it.

The blog renders with kramdown, which will not start a block element on the
line directly after a paragraph. ``...deadline.\\n## References`` therefore
renders as the literal text ``## References`` inside the paragraph — verified
by running kramdown itself on 2026-08-02, not inferred from the spec.

The damage is manufactured by the stat audit, and it is manufactured on every
article: ``audit_article_stats`` splits on ``(?<=[.!?])\\s+``, which swallows
the newline before ``## References``, and rejoins with a single space. What
changed is that B-042 deleted Stage 4's unconditional chart embed — the
``![Chart](…)`` line had been sitting in the gap and supplying the blank line
by accident. Both articles generated before B-042 show the same
``. \\n![Chart]…\\n\\n## References`` shape on disk. The first article
generated without a chart is the first one where the heading actually breaks.

``_normalize_paragraphs`` already lifted *inline* headings onto their own line.
It did not put a blank line above a heading that was already on one.
"""

from __future__ import annotations

from src.agent_sdk.stage3_runner import _normalize_paragraphs


class TestAHeadingAlwaysGetsABlankLineAboveIt:
    def test_the_measured_case_a_stat_audited_references_heading(self) -> None:
        """Exactly what the stat audit emits: trailing space, single newline."""
        audited = "The next transformation will also have a fixed deadline. \n## References\n\n1. A\n"

        result = _normalize_paragraphs(audited)

        assert "deadline.\n\n## References" in result

    def test_a_heading_on_its_own_line_after_a_paragraph(self) -> None:
        result = _normalize_paragraphs("Paragraph text.\n## The Next Section\n\nMore.")
        assert "text.\n\n## The Next Section" in result

    def test_an_inline_heading_is_still_lifted(self) -> None:
        """The behaviour that already worked must keep working."""
        result = _normalize_paragraphs("...the easy part. ## The Perception Gap\n\nX.")
        assert "part.\n\n## The Perception Gap" in result

    def test_a_correctly_spaced_heading_is_left_alone(self) -> None:
        already_fine = "Paragraph text.\n\n## A Heading\n\nMore text.\n"
        assert _normalize_paragraphs(already_fine) == already_fine

    def test_the_first_line_of_the_body_may_be_a_heading(self) -> None:
        """No paragraph above it means nothing to separate it from."""
        result = _normalize_paragraphs("## Opening Heading\n\nBody text.\n")
        assert result.startswith("## Opening Heading")
