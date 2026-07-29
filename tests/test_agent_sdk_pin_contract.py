"""Pin contract for the Anthropic Agent SDK — regression guard for BUG-066.

BUG-066: ``requirements.txt`` declared ``claude-agent-sdk>=0.1.68,<1.0.0``. A
machine that resolved the *floor* installed 0.1.68, which bundles Claude Code
CLI 2.1.119. That binary hangs with no stderr, and ``claude_agent_sdk`` resolves
its CLI bundled-first — ``subprocess_cli._find_cli()`` returns
``_find_bundled_cli()`` before ever consulting ``shutil.which("claude")`` — so a
maintained system CLI sitting on ``PATH`` is never reached. Every ``query()``
call died with the SDK's opaque "Command failed with exit code 1 / Check stderr
output for details", which names neither the binary nor the version.

The failure surfaced as an article-generation run aborting in seconds instead of
the expected ~35 minutes, after the research and writer legs had already been
dispatched. Nothing in ``make ci-local`` could see it: the suite mocks the SDK,
so a broken bundled binary is invisible until a real run spends real money.

Two guards, covering the two ways this recurs:

1. The declared floor must exclude every SDK whose bundled CLI is known broken.
2. The *installed* SDK must satisfy that floor, so a stale virtualenv fails at
   gate time rather than 35 minutes into a paid run.
"""

from __future__ import annotations

import re
from importlib.metadata import version as installed_version
from pathlib import Path

import pytest

#: Lowest ``claude-agent-sdk`` release whose bundled Claude Code CLI is verified
#: functional (bundles CLI 2.1.220; probed to exit 0 on a stream-json call).
#: Raise this — never lower it — if a future release ships a broken binary.
MINIMUM_FUNCTIONAL_SDK = (0, 2, 128)

REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"

_FLOOR_PATTERN = re.compile(r"^claude-agent-sdk\s*>=\s*([0-9][0-9.]*)")


def _parse_version(raw: str) -> tuple[int, ...]:
    """Convert a dotted version string into a comparable tuple of ints."""
    return tuple(int(part) for part in raw.strip().split("."))


def _declared_floor() -> tuple[int, ...]:
    """Return the ``>=`` floor declared for claude-agent-sdk in requirements.txt."""
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        match = _FLOOR_PATTERN.match(line.strip())
        if match:
            return _parse_version(match.group(1))
    pytest.fail(f"no claude-agent-sdk '>=' floor found in {REQUIREMENTS}")


class TestAgentSdkPinContract:
    """The dependency pin must not permit an SDK with a broken bundled CLI."""

    def test_declared_floor_excludes_sdks_with_a_broken_bundled_cli(self) -> None:
        """The requirements floor must be at or above the known-good SDK.

        Fails against the BUG-066 pin (0.1.68), which permitted the broken 2.1.119
        bundled CLI to be installed by a plain ``pip install -r requirements.txt``.
        """
        floor = _declared_floor()

        assert floor >= MINIMUM_FUNCTIONAL_SDK, (
            f"requirements.txt allows claude-agent-sdk {'.'.join(map(str, floor))}, "
            f"below the {'.'.join(map(str, MINIMUM_FUNCTIONAL_SDK))} whose bundled "
            "Claude Code CLI is verified working. A fresh install resolving this "
            "floor gets a CLI that hangs with no stderr (BUG-066)."
        )

    def test_installed_sdk_satisfies_the_declared_floor(self) -> None:
        """A stale virtualenv must fail here, not mid-run.

        This is the guard that would have caught BUG-066 at gate time: the venv
        held 0.1.68 while the working machine ran something far newer, and nothing
        compared the two.
        """
        installed = _parse_version(installed_version("claude-agent-sdk"))
        floor = _declared_floor()

        assert installed >= floor, (
            f"installed claude-agent-sdk {'.'.join(map(str, installed))} is below "
            f"the declared floor {'.'.join(map(str, floor))} — this virtualenv is "
            "stale. Run: pip install --upgrade -r requirements.txt"
        )
