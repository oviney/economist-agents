"""One Python version, declared once and agreed everywhere (B-037).

ADR-0015 says Python is "pinned to one version via `.python-version`". That was
not true. Four different versions were declared across the repo, and nothing
detected the disagreement:

| Source | Claimed |
|---|---|
| `.python-version` | 3.12 |
| `CONTRIBUTING.md` | 3.12 |
| `ruff.toml` `target-version` | py311 |
| `mypy.ini` `python_version` | 3.11 |
| `README.md`, `GEMINI.md`, ADR-0004 | 3.13 |
| the interpreter actually running the suite | 3.13.14 |

A pin nothing verifies is a comment. `.python-version` is the single source of
truth here; every other declaration is checked against it, including the
interpreter that runs this test — because a pin the tests themselves violate is
the least useful kind.

Found while fixing B-036: correcting the README's Python badge required deciding
which version was authoritative, and the answer was not knowable from the repo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_FILE = REPO_ROOT / ".python-version"


@pytest.fixture(scope="module")
def pin() -> str:
    """The declared version, e.g. ``"3.13"``. This is the source of truth."""
    return PIN_FILE.read_text(encoding="utf-8").strip()


class TestThePinIsReal:
    """`.python-version` must exist and be a bare major.minor."""

    def test_pin_file_exists(self) -> None:
        assert PIN_FILE.is_file()

    def test_pin_is_major_minor(self, pin: str) -> None:
        assert re.fullmatch(r"\d+\.\d+", pin), (
            f".python-version should be bare major.minor, got {pin!r}"
        )


class TestEverythingAgreesWithThePin:
    """Each declaration is checked against the pin, never against a literal.

    Written this way so the next bump is a one-line change to
    `.python-version` and these tests keep working — a test that hardcodes 3.13
    would just relocate the drift.
    """

    def test_running_interpreter_matches(self, pin: str) -> None:
        """The pin must describe the interpreter that actually runs the suite."""
        running = f"{sys.version_info.major}.{sys.version_info.minor}"

        assert running == pin, (
            f"tests are running on Python {running} but .python-version pins "
            f"{pin}. Rebuild .venv on {pin}, or bump the pin deliberately."
        )

    def test_ruff_target_version_matches(self, pin: str) -> None:
        text = (REPO_ROOT / "ruff.toml").read_text(encoding="utf-8")
        match = re.search(r'target-version\s*=\s*"py(\d)(\d+)"', text)

        assert match, "ruff.toml has no target-version"
        assert f"{match.group(1)}.{match.group(2)}" == pin

    def test_mypy_python_version_matches(self, pin: str) -> None:
        text = (REPO_ROOT / "mypy.ini").read_text(encoding="utf-8")
        match = re.search(r"python_version\s*=\s*(\d+\.\d+)", text)

        assert match, "mypy.ini has no python_version"
        assert match.group(1) == pin

    def test_contributing_states_the_pin(self, pin: str) -> None:
        text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        assert f"Python {pin}" in text, f"CONTRIBUTING.md does not state Python {pin}"

    def test_readme_badge_matches(self, pin: str) -> None:
        """Overlaps validate_badges.py on purpose — it is cheap and it is load-bearing."""
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        found = re.findall(r"img\.shields\.io/badge/Python-([0-9.]+)-", text)

        assert found, "README has no Python badge"
        assert all(v == pin for v in found), f"badge says {found}, pin says {pin}"
