"""Tests for the sensor-proof checker (B-043).

`docs/specs/sensor-proof-of-teeth.md` exists because 2026-08-01 produced four
independent proofs that nothing in this repo validates the sensors themselves —
B-039 found a *fifth* inert sensor after B-031 fixed four by name. B-031 fixed
four named sensors; it did not fix the class.

**The load-bearing test in this file is `TestItsOwnProofOfTeeth`.** It points the
checker at a fixture tree containing a sensor wired into a gate but absent from
the register, and asserts the checker fails. A checker that cannot fail is the
exact joke this item exists to prevent, so that test is the item's own proof of
teeth and every other test here is secondary to it.

Everything runs against throwaway fixture trees rather than the real repo, except
`TestTheRealRegister`, which asserts the shipped register is honest.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.check_sensor_proofs import (
    REGISTER_RELPATH,
    check_register,
    discover_gate_scripts,
    main,
)

REPO_ROOT = Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════════════════════
# Fixture-tree builders
# ═══════════════════════════════════════════════════════════════════════════

#: A Makefile whose gate step runs one in-repo sensor.
MAKEFILE = textwrap.dedent(
    """\
    VENV_BIN := $(CURDIR)/.venv/bin
    PY       := $(VENV_BIN)/python

    ci-local:
    \t@echo "── rogue guard ──" && $(PY) scripts/rogue_guard.py
    """
)

#: A pre-commit config whose only local hook runs one in-repo sensor.
PRECOMMIT = textwrap.dedent(
    """\
    repos:
      - repo: local
        hooks:
          - id: rogue-guard
            name: rogue guard
            entry: .venv/bin/python scripts/rogue_guard.py
            language: system
    """
)

#: A harness settings file wiring one Stop hook.
SETTINGS = textwrap.dedent(
    """\
    {
      "hooks": {
        "Stop": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "\\"${CLAUDE_PROJECT_DIR:-.}/scripts/hooks/run_hook.sh\\" rogue_hook"
              }
            ]
          }
        ]
      }
    }
    """
)

PROVEN_ENTRY = textwrap.dedent(
    """\
    sensors:
      - id: rogue_guard
        script: scripts/rogue_guard.py
        gates: ["make ci-local"]
        regulates: >-
          Something worth regulating, described well enough to re-adjudicate.
        proof: tests/test_rogue_guard.py::test_it_fires_on_a_real_defect
        mutation: >-
          Break the thing, run the guard, assert non-zero.
    """
)

PROOF_FILE = textwrap.dedent(
    """\
    def test_it_fires_on_a_real_defect() -> None:
        assert True
    """
)


def build_tree(
    root: Path,
    *,
    register: str = "sensors: []\n",
    gates: dict[str, str] | None = None,
    proof: str | None = None,
    scripts: tuple[str, ...] = ("scripts/rogue_guard.py",),
) -> Path:
    """Write a throwaway repo containing only what the checker reads.

    Args:
        root: Directory to build in.
        register: Contents of ``docs/sensors/register.yaml``.
        gates: Gate-site files as relpath → content. Defaults to a Makefile whose
            ci-local recipe runs ``scripts/rogue_guard.py``; pass ``{}`` for none.
        proof: Contents of ``tests/test_rogue_guard.py``, or None to omit it.
        scripts: Sensor scripts to create, relative to the tree root.

    Returns:
        The tree root, for chaining.

    """
    (root / "docs" / "sensors").mkdir(parents=True, exist_ok=True)
    (root / REGISTER_RELPATH).write_text(register)

    files = dict(gates if gates is not None else {"Makefile": MAKEFILE})
    if proof is not None:
        files["tests/test_rogue_guard.py"] = proof
    for relpath in scripts:
        files[relpath] = "def main() -> int:\n    return 1\n"

    for relpath, content in files.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    return root


def failures(root: Path) -> list[str]:
    """Return the checker's findings against a tree, as plain strings."""
    return [str(finding) for finding in check_register(root)]


# ═══════════════════════════════════════════════════════════════════════════
# The load-bearing test — this checker's own proof that it can fail
# ═══════════════════════════════════════════════════════════════════════════


class TestItsOwnProofOfTeeth:
    """B-043 ships a sensor, and a sensor that cannot fail is worse than none —
    it is the `|| true` on `validate_badges` that swallowed both the stale-badge
    failures it existed to catch *and* the proof it had no implementation.

    These tests mutate a fixture tree (add a sensor, do not register it) and
    assert the checker notices. Nothing else in this file substitutes for them.
    """

    def test_a_wired_sensor_absent_from_the_register_fails(
        self, tmp_path: Path
    ) -> None:
        build_tree(tmp_path, register="sensors: []\n")

        found = failures(tmp_path)

        assert found, (
            "a sensor wired into ci-local but unregistered must fail the check"
        )
        assert any("rogue_guard" in f for f in found)

    def test_that_same_tree_passes_once_the_sensor_is_registered(
        self, tmp_path: Path
    ) -> None:
        """The other half of the mutation: without this, the failure above could
        be an unconditional failure rather than a detection."""
        build_tree(tmp_path, register=PROVEN_ENTRY, proof=PROOF_FILE)

        assert failures(tmp_path) == []

    def test_it_exits_non_zero_at_the_command_line(self, tmp_path: Path) -> None:
        """`make ci-local` reads the exit code, not the findings list."""
        build_tree(tmp_path, register="sensors: []\n")

        assert main(["--root", str(tmp_path)]) != 0

    def test_it_exits_zero_when_the_register_is_honest(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register=PROVEN_ENTRY, proof=PROOF_FILE)

        assert main(["--root", str(tmp_path)]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Discovery — what the register's boundary actually is
# ═══════════════════════════════════════════════════════════════════════════


class TestDiscoveryFindsSensorsAtTheirGateSite:
    """A filename pattern (`*_guard.py`, `validate_*.py`) is gameable by renaming
    and blind to a sensor wired in under any other name. Discovery reads the
    wiring instead: a script is a sensor when a gate site invokes it.
    """

    def test_a_makefile_recipe_is_a_gate_site(self, tmp_path: Path) -> None:
        build_tree(tmp_path)

        assert "scripts/rogue_guard.py" in discover_gate_scripts(tmp_path)

    def test_a_pre_commit_entry_is_a_gate_site(self, tmp_path: Path) -> None:
        build_tree(tmp_path, gates={".pre-commit-config.yaml": PRECOMMIT})

        assert "scripts/rogue_guard.py" in discover_gate_scripts(tmp_path)

    def test_a_harness_hook_is_a_gate_site(self, tmp_path: Path) -> None:
        """B-030's hooks block a tool call and a turn; open question 2 in the spec
        answers yes — a hook is registered separately from what it invokes."""
        build_tree(
            tmp_path,
            gates={".claude/settings.json": SETTINGS},
            scripts=("scripts/hooks/rogue_hook.py",),
        )

        assert "scripts/hooks/rogue_hook.py" in discover_gate_scripts(tmp_path)

    def test_a_makefile_comment_is_not_a_gate_site(self, tmp_path: Path) -> None:
        """The real Makefile discusses scripts in its comments at length. Counting
        those would make the register a transcript of the commentary."""
        build_tree(
            tmp_path,
            gates={
                "Makefile": "# see scripts/rogue_guard.py for the reasoning\nall:\n\t@true\n"
            },
        )

        assert discover_gate_scripts(tmp_path) == {}

    def test_the_gate_site_is_recorded_not_just_the_script(
        self, tmp_path: Path
    ) -> None:
        """`--list` has to say where a sensor fires; "somewhere" is not auditable."""
        build_tree(tmp_path)

        assert discover_gate_scripts(tmp_path)["scripts/rogue_guard.py"] == ["Makefile"]

    def test_a_missing_gate_site_file_is_not_an_error(self, tmp_path: Path) -> None:
        """A tree with no pre-commit config discovers nothing from it and says
        nothing about it — degrade, do not crash."""
        build_tree(tmp_path, gates={})

        assert discover_gate_scripts(tmp_path) == {}


# ═══════════════════════════════════════════════════════════════════════════
# Proof resolution — the three rules from the spec
# ═══════════════════════════════════════════════════════════════════════════


class TestAProofMustExistAndBeAbleToRun:
    """Rule 2: an entry naming a proof that does not exist, is skipped, or is
    xfail has a register entry and no proof. That is worse than `proof: none`,
    which at least admits it."""

    def test_a_proof_naming_a_missing_file_fails(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register=PROVEN_ENTRY, proof=None)

        assert any("tests/test_rogue_guard.py" in f for f in failures(tmp_path))

    def test_a_proof_naming_a_missing_test_fails(self, tmp_path: Path) -> None:
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY,
            proof="def test_something_else() -> None:\n    assert True\n",
        )

        assert any("test_it_fires_on_a_real_defect" in f for f in failures(tmp_path))

    def test_a_skipped_proof_fails(self, tmp_path: Path) -> None:
        """Skipping is how a proof rots quietly: it stays green and stops running."""
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY,
            proof=(
                "import pytest\n\n\n"
                '@pytest.mark.skip(reason="flaky")\n'
                "def test_it_fires_on_a_real_defect() -> None:\n    assert True\n"
            ),
        )

        assert any("skip" in f.lower() for f in failures(tmp_path))

    def test_an_xfail_proof_fails(self, tmp_path: Path) -> None:
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY,
            proof=(
                "import pytest\n\n\n"
                "@pytest.mark.xfail\n"
                "def test_it_fires_on_a_real_defect() -> None:\n    assert True\n"
            ),
        )

        assert any("xfail" in f.lower() for f in failures(tmp_path))

    def test_a_proof_inside_a_class_resolves(self, tmp_path: Path) -> None:
        """Most proofs in this repo live in a class; `file::Class::test` must work."""
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY.replace(
                "tests/test_rogue_guard.py::test_it_fires_on_a_real_defect",
                "tests/test_rogue_guard.py::TestTeeth::test_it_fires_on_a_real_defect",
            ),
            proof=(
                "class TestTeeth:\n"
                "    def test_it_fires_on_a_real_defect(self) -> None:\n"
                "        assert True\n"
            ),
        )

        assert failures(tmp_path) == []

    def test_a_skipped_class_fails_its_proof(self, tmp_path: Path) -> None:
        """A class-level skip mutes every proof inside it, silently."""
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY.replace(
                "tests/test_rogue_guard.py::test_it_fires_on_a_real_defect",
                "tests/test_rogue_guard.py::TestTeeth::test_it_fires_on_a_real_defect",
            ),
            proof=(
                "import pytest\n\n\n"
                '@pytest.mark.skip(reason="later")\n'
                "class TestTeeth:\n"
                "    def test_it_fires_on_a_real_defect(self) -> None:\n"
                "        assert True\n"
            ),
        )

        assert any("skip" in f.lower() for f in failures(tmp_path))


class TestAnEntryMustCarryItsReasoning:
    """Rule 3: `regulates` and `mutation` exist so a reviewer can check the claim
    against the test in one glance. The checker cannot verify a proof is genuine
    — that limit is deliberate — so the reviewer needs the reasoning written down."""

    def test_a_missing_regulates_fails(self, tmp_path: Path) -> None:
        register = "\n".join(
            line
            for line in PROVEN_ENTRY.splitlines()
            if "regulates" not in line and "Something worth regulating" not in line
        )
        build_tree(tmp_path, register=register + "\n", proof=PROOF_FILE)

        assert any("regulates" in f for f in failures(tmp_path))

    def test_a_missing_mutation_fails(self, tmp_path: Path) -> None:
        register = "\n".join(
            line
            for line in PROVEN_ENTRY.splitlines()
            if "mutation" not in line and "Break the thing" not in line
        )
        build_tree(tmp_path, register=register + "\n", proof=PROOF_FILE)

        assert any("mutation" in f for f in failures(tmp_path))

    def test_an_entry_naming_a_script_that_does_not_exist_fails(
        self, tmp_path: Path
    ) -> None:
        """A register that outlives its sensor claims coverage it does not have."""
        build_tree(tmp_path, register=PROVEN_ENTRY, proof=PROOF_FILE, scripts=())

        assert any("scripts/rogue_guard.py" in f for f in failures(tmp_path))


class TestProofNoneIsAnHonestBaseline:
    """The spec ships the register green on a TRUE baseline rather than after a
    backfill sprint, and the count of `proof: none` is the burndown. An unproved
    sensor that says so is strictly better than one nobody has counted."""

    NONE_ENTRY = textwrap.dedent(
        """\
        sensors:
          - id: rogue_guard
            script: scripts/rogue_guard.py
            gates: ["make ci-local"]
            regulates: >-
              Something worth regulating.
            proof: none
            reason: >-
              Backfilled 2026-08-01 as a measured baseline; proof scheduled.
        """
    )

    def test_proof_none_with_a_reason_passes(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register=self.NONE_ENTRY)

        assert failures(tmp_path) == []

    def test_proof_none_without_a_reason_fails(self, tmp_path: Path) -> None:
        """Otherwise `proof: none` is a mute button rather than a recorded override."""
        register = "\n".join(
            line
            for line in self.NONE_ENTRY.splitlines()
            if "reason" not in line and "Backfilled" not in line
        )
        build_tree(tmp_path, register=register + "\n")

        assert any("reason" in f for f in failures(tmp_path))

    def test_proof_none_does_not_need_a_mutation(self, tmp_path: Path) -> None:
        """There is no mutation to describe when there is no proof."""
        build_tree(tmp_path, register=self.NONE_ENTRY)

        assert not any("mutation" in f for f in failures(tmp_path))


class TestNotEverythingWiredIntoAGateIsASensor:
    """`session_context` injects the constraints at SessionStart and
    `post_edit_sensor` returns `additionalContext`. Both are wired into
    `.claude/settings.json`, so discovery finds them; neither can deny a call or
    fail a gate, so there is no "can it fail?" to answer. `proof: n/a` records
    that, and keeps the `proof: none` burndown counting only what is owed.
    """

    NA_ENTRY = textwrap.dedent(
        """\
        sensors:
          - id: rogue_guard
            script: scripts/rogue_guard.py
            gates: ["make ci-local"]
            regulates: >-
              Nothing — it only reports.
            proof: n/a
            reason: >-
              Returns additionalContext; it cannot block a call or fail a gate.
        """
    )

    def test_proof_na_with_a_reason_passes(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register=self.NA_ENTRY)

        assert failures(tmp_path) == []

    def test_proof_na_without_a_reason_fails(self, tmp_path: Path) -> None:
        """Otherwise `n/a` is a way to exempt a real sensor in one word."""
        register = "\n".join(
            line
            for line in self.NA_ENTRY.splitlines()
            if "reason" not in line and "additionalContext" not in line
        )
        build_tree(tmp_path, register=register + "\n")

        assert any("reason" in f for f in failures(tmp_path))

    def test_it_does_not_count_towards_the_burndown(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`n/a` is not a debt; counting it as one makes the burndown never reach
        zero and so stop being read."""
        build_tree(tmp_path, register=self.NA_ENTRY)

        main(["--root", str(tmp_path), "--list"])

        assert "0 unproved" in capsys.readouterr().out


class TestTheRegisterFileItself:
    """Malformed input must fail the gate rather than silently pass it — the
    `(mypy || echo advisory)` failure mode, where 'never ran' looked like 'clean'."""

    def test_a_missing_register_fails(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text(MAKEFILE)

        assert failures(tmp_path)
        assert main(["--root", str(tmp_path)]) != 0

    def test_unparseable_yaml_fails(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register="sensors: [unclosed\n")

        assert failures(tmp_path)

    def test_a_register_that_is_not_a_mapping_fails(self, tmp_path: Path) -> None:
        build_tree(tmp_path, register="- just\n- a\n- list\n")

        assert failures(tmp_path)

    def test_a_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Two entries with one id means one of them is never read."""
        build_tree(
            tmp_path,
            register=PROVEN_ENTRY + PROVEN_ENTRY.split("\n", 1)[1],
            proof=PROOF_FILE,
        )

        assert any("duplicate" in f.lower() for f in failures(tmp_path))


class TestTheListView:
    """`--list` is where the `proof: none` burndown lives, rather than in
    someone's head."""

    def test_list_reports_each_sensor_and_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        build_tree(tmp_path, register=PROVEN_ENTRY, proof=PROOF_FILE)

        code = main(["--root", str(tmp_path), "--list"])

        assert code == 0
        assert "rogue_guard" in capsys.readouterr().out

    def test_list_counts_the_unproved(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        build_tree(tmp_path, register=TestProofNoneIsAnHonestBaseline.NONE_ENTRY)

        main(["--root", str(tmp_path), "--list"])

        assert "1" in capsys.readouterr().out


# ═══════════════════════════════════════════════════════════════════════════
# The real repo
# ═══════════════════════════════════════════════════════════════════════════


class TestTheRealRegister:
    """The gate has to be green on `main` from the first commit, and the register
    has to describe this repo rather than an aspiration."""

    def test_the_shipped_register_passes_its_own_check(self) -> None:
        found = failures(REPO_ROOT)

        assert found == [], "\n".join(found)

    def test_this_checker_is_in_its_own_register(self) -> None:
        """A sensor exempting itself is the failure this item is named after."""
        register = (REPO_ROOT / REGISTER_RELPATH).read_text()

        assert "scripts/check_sensor_proofs.py" in register
