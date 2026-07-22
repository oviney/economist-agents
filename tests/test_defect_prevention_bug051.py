"""Regression for BUG-051 (surfaced by B-010 deploy dry-run).

The BUG-016 chart-reference rule matched a hardcoded phrase list
("chart illustrates", "as the chart shows", ...). A natural reference like
"As the chart below illustrates" (an intervening word) was not matched, so a
correctly-referenced chart was flagged "Chart embedded but never referenced"
and the deploy pre-validation REJECTED a publish-valid article.
"""

from __future__ import annotations

from scripts.defect_prevention_rules import DefectPrevention

_EMBED = "![Chart](/assets/charts/x.png)"


def _check(body: str) -> str:
    content = (
        f"---\nlayout: post\ntitle: x\ndate: 2026-07-22\n---\n\n{body}\n\n{_EMBED}\n"
    )
    return DefectPrevention()._check_chart_embedding(content, {"chart_data": True})


def test_reference_with_intervening_word_is_accepted() -> None:
    # The exact live failure: "chart below illustrates".
    assert _check("As the chart below illustrates, red builds mislead.") == ""


def test_existing_phrasings_still_accepted() -> None:
    for phrase in (
        "As the chart shows, testing pays off.",
        "The chart reveals a stark gap.",
        "This is shown in the chart above.",
        "The chart illustrates the trend.",
        "As the chart above demonstrates, costs compound.",
    ):
        assert _check(phrase) == "", phrase


def test_genuinely_unreferenced_chart_is_still_flagged() -> None:
    msg = _check("A body with no mention of the visual at all.")
    assert "never referenced" in msg
