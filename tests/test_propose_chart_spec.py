"""B-042: the chart proposal is extracted, never generated.

The defect this replaces: ``missing_chart`` was CRITICAL, so a brief carrying
one number still required a chart, and the graphics LLM — which was handed the
article and never the brief — invented four percentages to comply.

``propose_chart_spec`` removes the generative step entirely. Every value it
emits came out of the brief by regex, so there is no fabrication path to audit.
Framing (title, metric labels) is left empty on purpose: a plausible
machine-written label is what made the fabricated chart unreadable as fiction.

Spec: docs/specs/mandatory-chart-setpoint.md — S3, AC3, AC4.
"""

from __future__ import annotations

import re

from src.agent_sdk._shared import propose_chart_spec

_BRIEF_WITH_NUMBERS = """
## Research brief — testing shortcuts

Teams that skip automated testing report that up to 40% of engineering capacity
is consumed by rework ([source](https://example.com/a)).

A 2025 survey of 1200 engineers found median remediation took 3.5 days.
The same survey put the figure at 40% again in its follow-up wave.
"""

_BRIEF_WITHOUT_NUMBERS = """
## Research brief — qualitative only

Practitioners describe migration deadlines as a forcing function. No study in
the set quantifies the effect; the evidence is interview-based throughout.
"""


class TestNoNumbersMeansNoChart:
    """AC1's upstream half: nothing to chart must be a first-class outcome."""

    def test_brief_without_numbers_proposes_nothing(self) -> None:
        assert propose_chart_spec(_BRIEF_WITHOUT_NUMBERS) is None

    def test_empty_brief_proposes_nothing(self) -> None:
        assert propose_chart_spec("") is None

    def test_bare_years_are_not_chartable(self) -> None:
        """A date is not a measurement. '2025' alone must not become a bar."""
        assert propose_chart_spec("The 2025 deadline follows the 2024 review.") is None


class TestEveryValueComesFromTheBrief:
    """AC3: the property that makes an audit unnecessary."""

    def test_all_proposed_values_appear_in_the_brief(self) -> None:
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        for row in spec["data"]:
            assert re.search(
                rf"\b{re.escape(str(row['value']))}\b", _BRIEF_WITH_NUMBERS
            ), f"value {row['value']!r} is not in the brief"

    def test_the_fabricated_values_cannot_be_proposed(self) -> None:
        """AC2 in miniature: g4's four invented percentages, against g4's brief.

        The real brief contained exactly one number. Any proposal drawn from it
        can only contain that number.
        """
        spec = propose_chart_spec(
            "Teams report up to 40% of engineering capacity is consumed by rework."
        )
        assert spec is not None
        values = {row["value"] for row in spec["data"]}
        assert values == {40}
        assert not values & {62, 46, 28, 12}

    def test_each_row_quotes_its_source_line(self) -> None:
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        for row in spec["data"]:
            assert row["source"].startswith("brief: "), row["source"]
            quoted = row["source"].removeprefix("brief: ").strip("'")
            normalised = re.sub(r"\s+", " ", _BRIEF_WITH_NUMBERS)
            assert quoted in normalised, f"provenance not found verbatim: {quoted!r}"


class TestFramingIsLeftToTheOwner:
    """AC4: the machine supplies numbers and provenance, never the story."""

    def test_title_and_subtitle_are_empty(self) -> None:
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        assert spec["title"] == ""
        assert spec["subtitle"] == ""

    def test_metric_labels_are_empty(self) -> None:
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        assert [row["metric"] for row in spec["data"]] == [""] * len(spec["data"])

    def test_units_are_carried_through(self) -> None:
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        assert "%" in {row["unit"] for row in spec["data"]}

    def test_repeated_figures_are_proposed_once(self) -> None:
        """40% appears twice in the brief; a chart with two identical bars is noise."""
        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        keys = [(row["value"], row["unit"]) for row in spec["data"]]
        assert len(keys) == len(set(keys))


class TestTheProposalIsNotSilentlyRenderable:
    """The renderer must reject a proposal until the owner has framed it.

    ``_validate_spec`` requires a non-empty title and a non-empty metric per
    row, so an untouched proposal cannot be rendered by accident — the owner
    has to make the editorial decisions before a PNG exists.
    """

    def test_untouched_proposal_is_rejected_by_the_renderer(self, tmp_path) -> None:
        import pytest

        from src.agent_sdk.chart_renderer import ChartRenderError, render_chart

        spec = propose_chart_spec(_BRIEF_WITH_NUMBERS)
        assert spec is not None
        with pytest.raises(ChartRenderError):
            render_chart(spec, tmp_path / "out.png")
