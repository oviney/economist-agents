"""Tests for the B-040 calibration spot-check sheet renderer.

The Phase 2 gate on B-040 is the owner's judgement on agent-drafted cases. The
cost of that judgement is that the cases are spread across 23 YAML files, so the
renderer's job is to collapse them into one ordered document. It is deterministic
and keyless: no judge runs here, nothing is scored.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.render_calibration_review_sheet import (
    load_cases,
    render_sheet,
)


@pytest.fixture
def cases_dir(tmp_path: Path) -> Path:
    """Two negatives and one positive, deliberately written out of order."""
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "g2-beta.yaml").write_text(
        "id: g2-beta\n"
        "gate: G2\n"
        "expected: pass\n"
        "source: article-two\n"
        "passage: >-\n  The beta passage.\n"
        "why: >-\n  Beta is a negative.\n",
    )
    (cases / "g1-alpha.yaml").write_text(
        "id: g1-alpha\n"
        "gate: G1\n"
        "expected: fail\n"
        "source: article-one\n"
        "passage: >-\n  The alpha passage.\n"
        "why: >-\n  Alpha is a positive.\n",
    )
    (cases / "g4-gamma.yaml").write_text(
        "id: g4-gamma\n"
        "gate: G4\n"
        "expected: pass\n"
        "source: article-one\n"
        "passage: >-\n  The gamma passage.\n"
        "why: >-\n  Gamma is a negative.\n",
    )
    return cases


class TestLoadCases:
    """Loading is deterministic and does not silently drop malformed cases."""

    def test_loads_every_case_file(self, cases_dir: Path) -> None:
        cases = load_cases(cases_dir)

        assert len(cases) == 3

    def test_orders_by_id_so_output_is_stable(self, cases_dir: Path) -> None:
        cases = load_cases(cases_dir)

        assert [c["id"] for c in cases] == ["g1-alpha", "g2-beta", "g4-gamma"]

    def test_rejects_a_case_missing_a_required_field(self, tmp_path: Path) -> None:
        cases = tmp_path / "cases"
        cases.mkdir()
        (cases / "broken.yaml").write_text("id: broken\ngate: G1\n")

        with pytest.raises(ValueError, match="missing required field"):
            load_cases(cases)

    def test_raises_when_the_directory_has_no_cases(self, tmp_path: Path) -> None:
        empty = tmp_path / "cases"
        empty.mkdir()

        with pytest.raises(ValueError, match="no case files"):
            load_cases(empty)


class TestRenderSheet:
    """The sheet must be reviewable top-to-bottom without opening the YAML."""

    def test_counts_in_the_header_are_measured_not_asserted(
        self,
        cases_dir: Path,
    ) -> None:
        sheet = render_sheet(load_cases(cases_dir))

        assert "3 cases" in sheet
        assert "2 negatives (67%)" in sheet
        assert "2 source articles" in sheet

    def test_negatives_come_first(self, cases_dir: Path) -> None:
        """Negatives are the agent-drafted half the spot-check exists to check."""
        sheet = render_sheet(load_cases(cases_dir))

        assert sheet.index("## Negatives") < sheet.index("## Positives")

    def test_every_case_carries_its_passage_and_reasoning(
        self,
        cases_dir: Path,
    ) -> None:
        sheet = render_sheet(load_cases(cases_dir))

        for fragment in (
            "The alpha passage.",
            "Alpha is a positive.",
            "The beta passage.",
            "Beta is a negative.",
            "The gamma passage.",
            "Gamma is a negative.",
        ):
            assert fragment in sheet

    def test_every_case_has_an_agree_disagree_control(self, cases_dir: Path) -> None:
        sheet = render_sheet(load_cases(cases_dir))

        assert sheet.count("- [ ] agree") == 3
        assert sheet.count("- [ ] disagree") == 3

    def test_case_ids_and_gates_are_shown(self, cases_dir: Path) -> None:
        sheet = render_sheet(load_cases(cases_dir))

        assert "g1-alpha" in sheet
        assert "G1" in sheet
        assert "article-one" in sheet

    def test_render_is_deterministic(self, cases_dir: Path) -> None:
        assert render_sheet(load_cases(cases_dir)) == render_sheet(
            load_cases(cases_dir),
        )


class TestAgainstTheRealCaseSet:
    """Guard the real set, so a malformed case fails here rather than silently."""

    def test_the_committed_case_set_renders(self) -> None:
        real = Path(__file__).resolve().parent.parent / "docs/evals/review-gate/cases"
        if not real.is_dir():  # pragma: no cover - set lands with B-040 Phase 1
            pytest.skip("calibration case set not present on this branch")

        sheet = render_sheet(load_cases(real))

        assert "# Review-gate calibration" in sheet
        assert "## Negatives" in sheet
