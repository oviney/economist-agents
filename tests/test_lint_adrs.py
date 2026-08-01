"""Proof of teeth for the ADR governance lint (B-043).

`scripts/lint_adrs.py` is the `adr-lint` pre-commit hook and had **zero tests**
until this file — the other of the two largest gaps the B-043 baseline measured.
It enforces `skills/adr-governance/SKILL.md`: one canonical location, one number
per ADR, a status from a closed set, an mkdocs entry, and supersession links that
point both ways.

Every test here plants **one** governance defect in a throwaway ADR tree and
asserts the lint reports it, with a clean tree as the control. A lint with seven
rules and no proof that any of them fires is seven rules on paper.

Two of these have bitten this repo for real: ADR-0018 was renumbered from 0016
after `main` landed a different ADR-0016 while the draft sat on disk (a duplicate
number), and `adr-lint` fails while an ADR is untracked because the hook
framework stashes the `mkdocs.yml` nav line but not the file (the mkdocs rule).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.lint_adrs import lint, main

ADR = textwrap.dedent(
    """\
    # ADR-0001: A Decision

    **Status:** Accepted
    **Date:** 2026-08-01

    ## Context

    Something needed deciding.
    """
)


def write_adr(root: Path, name: str, body: str = ADR, *, in_nav: bool = True) -> Path:
    """Add an ADR to a fixture tree, optionally wiring it into mkdocs.yml."""
    path = root / "docs" / "adr" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    if in_nav:
        nav = root / "mkdocs.yml"
        nav.write_text(nav.read_text() + f"      - adr/{name}\n")
    return path


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal repo with one valid ADR — the control for every mutation."""
    (tmp_path / "mkdocs.yml").write_text("nav:\n  - ADRs:\n")
    write_adr(tmp_path, "0001-a-decision.md")
    return tmp_path


class TestTheCleanTreeIsClean:
    """Without this, every failing assertion below could be an always-red lint."""

    def test_a_valid_adr_tree_passes(self, tree: Path) -> None:
        assert lint(tree) == []

    def test_it_exits_zero(self, tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["lint_adrs.py", "--repo-root", str(tree)])

        assert main() == 0


class TestItFiresOnEachGovernanceDefect:
    """One mutation per rule. Each asserts the *specific* rule fired, not merely
    that something did — a lint that reports the wrong reason sends the next
    reader to the wrong place."""

    def test_a_status_outside_the_allowed_set_is_caught(self, tree: Path) -> None:
        write_adr(
            tree,
            "0002-approved.md",
            ADR.replace("**Status:** Accepted", "**Status:** Approved"),
        )

        assert any("not in allowed set" in e for e in lint(tree))

    def test_a_missing_status_header_is_caught(self, tree: Path) -> None:
        write_adr(tree, "0002-no-status.md", "# ADR-0002: No Status\n\n## Context\n")

        assert any("missing '**Status:**' header" in e for e in lint(tree))

    def test_a_filename_off_the_pattern_is_caught(self, tree: Path) -> None:
        write_adr(tree, "0002_snake_case.md")

        assert any("does not match NNNN-kebab-case" in e for e in lint(tree))

    def test_a_duplicate_number_is_caught(self, tree: Path) -> None:
        """This one happened: ADR-0018 was renumbered from 0016 because `main`
        landed a different 0016 while the draft sat uncommitted on disk."""
        write_adr(tree, "0001-a-different-decision.md")

        assert any("duplicate ADR number" in e for e in lint(tree))

    def test_an_adr_missing_from_mkdocs_is_caught(self, tree: Path) -> None:
        write_adr(tree, "0002-unlisted.md", in_nav=False)

        assert any("not referenced in mkdocs.yml" in e for e in lint(tree))

    def test_an_adr_outside_the_canonical_directory_is_caught(self, tree: Path) -> None:
        (tree / "docs" / "ADR-0002-stray.md").write_text(ADR)

        assert any("outside canonical location" in e for e in lint(tree))

    def test_a_superseded_adr_with_no_link_is_caught(self, tree: Path) -> None:
        write_adr(
            tree,
            "0002-superseded.md",
            ADR.replace("**Status:** Accepted", "**Status:** Superseded"),
        )

        assert any("no 'Superseded by ADR-NNNN' link" in e for e in lint(tree))

    def test_one_way_supersession_is_caught(self, tree: Path) -> None:
        """A link that points one way is how an ADR tree starts lying about
        which decision is current."""
        write_adr(
            tree,
            "0002-the-superseder.md",
            ADR.replace("**Date:**", "**Supersedes:** ADR-0001\n**Date:**"),
        )

        assert any("does not have 'Superseded by ADR-0002'" in e for e in lint(tree))

    def test_a_dangling_supersession_target_is_caught(self, tree: Path) -> None:
        write_adr(
            tree,
            "0002-points-at-nothing.md",
            ADR.replace("**Date:**", "**Supersedes:** ADR-0099\n**Date:**"),
        )

        assert any("which does not exist" in e for e in lint(tree))

    def test_a_bidirectional_pair_passes(self, tree: Path) -> None:
        """The negative control for the two supersession tests above."""
        (tree / "docs" / "adr" / "0001-a-decision.md").write_text(
            ADR.replace(
                "**Status:** Accepted",
                "**Status:** Superseded\n**Superseded by** ADR-0002",
            )
        )
        write_adr(
            tree,
            "0002-the-superseder.md",
            ADR.replace("**Date:**", "**Supersedes:** ADR-0001\n**Date:**"),
        )

        assert lint(tree) == []


class TestItCannotPassByFailingToRun:
    """B-039's failure mode: a sensor that never ran reporting the same thing as
    a sensor that ran and found nothing."""

    def test_an_empty_adr_directory_is_an_error_not_a_pass(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "mkdocs.yml").write_text("nav:\n")
        (tmp_path / "docs" / "adr").mkdir(parents=True)

        assert any("no ADRs found" in e for e in lint(tmp_path))

    def test_a_missing_mkdocs_is_an_error_not_a_pass(self, tmp_path: Path) -> None:
        (tmp_path / "mkdocs.yml").write_text("nav:\n")
        write_adr(tmp_path, "0001-a-decision.md")
        (tmp_path / "mkdocs.yml").unlink()

        assert any("not found" in e for e in lint(tmp_path))

    def test_violations_exit_non_zero(
        self, tree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exit code is what the pre-commit hook reads."""
        write_adr(tree, "0001-a-different-decision.md")
        monkeypatch.setattr("sys.argv", ["lint_adrs.py", "--repo-root", str(tree)])

        assert main() == 1


class TestTheRealAdrTree:
    """The repo's own ADRs must pass, or the hook is red on `main`."""

    def test_this_repos_adrs_lint_clean(self) -> None:
        errors = lint(Path(__file__).parent.parent)

        assert errors == [], "\n".join(errors)
