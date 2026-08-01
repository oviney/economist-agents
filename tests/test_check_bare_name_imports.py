"""Proof of teeth for the bare-name import guard (B-043).

`scripts/check_bare_name_imports.py` runs in `make ci-local` and had **zero
tests** until this file — one of the two largest gaps the B-043 baseline
measured. It guards ADR-0010: a bare `from llm_client import call_llm` resolves
through `sys.path`, so any module of that name anywhere on the path silently
takes precedence. That is the CVE-377-adjacent module-spoofing class.

The tests here are efficacy tests, not unit tests. Each one **plants the defect
the guard exists to catch** in a throwaway tree and asserts the guard exits
non-zero, then plants the correct form and asserts it exits zero. Both halves
matter: a guard that always fails is as useless as one that never does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_bare_name_imports as guard


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo with one module in scripts/ and an empty src/.

    The guard resolves everything from module-level constants, so pointing it at
    a fixture tree means repointing those.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "llm_client.py").write_text(
        "def call_llm() -> None:\n    pass\n"
    )
    (tmp_path / "src").mkdir()

    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(guard, "SCRIPTS_DIR", tmp_path / "scripts")
    monkeypatch.setattr(guard, "SCAN_ROOTS", ["src", "scripts"])
    return tmp_path


class TestItFiresOnTheDefectItExistsFor:
    """Plant a bare-name import; the guard must notice."""

    def test_a_bare_from_import_is_caught(self, tree: Path) -> None:
        (tree / "src" / "consumer.py").write_text("from llm_client import call_llm\n")

        assert guard.main() == 1

    def test_a_bare_plain_import_is_caught(self, tree: Path) -> None:
        """`import llm_client` spoofs just as well as the `from` form."""
        (tree / "src" / "consumer.py").write_text("import llm_client\n")

        assert guard.main() == 1

    def test_an_aliased_bare_import_is_caught(self, tree: Path) -> None:
        (tree / "src" / "consumer.py").write_text("import llm_client as llm\n")

        assert guard.main() == 1

    def test_the_violation_is_reported_with_its_location(
        self, tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A guard that fails without saying where costs more than it saves."""
        (tree / "src" / "consumer.py").write_text(
            "\n\nfrom llm_client import call_llm\n"
        )

        guard.main()

        assert "consumer.py:3" in capsys.readouterr().err


class TestItDoesNotFireOnCorrectCode:
    """The other half of the mutation. Without these, every test above would
    pass against a guard hardcoded to return 1."""

    def test_the_fully_qualified_form_passes(self, tree: Path) -> None:
        (tree / "src" / "consumer.py").write_text(
            "from scripts.llm_client import call_llm\n"
        )

        assert guard.main() == 0

    def test_a_relative_import_inside_scripts_passes(self, tree: Path) -> None:
        """ADR-0010 forbids bare *absolute* imports; siblings may use `from .X`."""
        (tree / "scripts" / "sibling.py").write_text(
            "from .llm_client import call_llm\n"
        )

        assert guard.main() == 0

    def test_an_unrelated_module_name_passes(self, tree: Path) -> None:
        (tree / "src" / "consumer.py").write_text("import json\n")

        assert guard.main() == 0

    def test_a_docstring_example_is_not_a_violation(self, tree: Path) -> None:
        """AST parsing is the reason this guard can be documented in its own
        docstring without flagging itself."""
        (tree / "src" / "consumer.py").write_text(
            '"""Never write `import llm_client`; use scripts.llm_client."""\n'
        )

        assert guard.main() == 0


class TestItDegradesHonestly:
    """A guard that cannot run must say so rather than pass quietly — the
    `(mypy || echo advisory)` failure mode B-039 found."""

    def test_no_scripts_modules_is_an_error_not_a_pass(self, tree: Path) -> None:
        (tree / "scripts" / "llm_client.py").unlink()

        assert guard.main() == 1

    def test_an_unparseable_file_does_not_crash_the_guard(self, tree: Path) -> None:
        (tree / "src" / "broken.py").write_text("def (((\n")

        assert guard.main() == 0
