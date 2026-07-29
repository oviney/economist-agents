"""Chrome discovery for the hero render — regression guard for BUG-068.

BUG-068: ``render_to_png`` resolved Chrome with ``shutil.which()`` against
``("google-chrome", "chromium", "chromium-browser")``. On macOS — the owner's
platform — Chrome ships as an app bundle at
``/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`` and is never on
``PATH`` under any of those names, so ``which()`` always returned ``None``.

The consequence was not a failed render but a *silent* one: no raster meant no
vision critique, the pipeline logged a single WARNING and carried on to a PASSED
validator. Operating Constraint #4 ("always look at the rendered result before
shipping") became unenforceable on the platform the owner actually runs. It bit
for real on the article-two hero, whose clipped top card went unreported —
exactly the defect class the critique caught on B-020.

Discovery order is PATH first, then known app-bundle locations: an explicitly
installed binary on PATH is the operator's choice and should win over a
system-default bundle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_sdk import hero_svg
from src.agent_sdk.hero_svg import _find_chrome


class TestChromeDiscovery:
    """Chrome must be found wherever the platform actually puts it."""

    def test_finds_a_binary_on_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A Chrome on PATH is used as-is."""
        monkeypatch.setattr(
            hero_svg.shutil, "which", lambda name: "/usr/bin/google-chrome"
        )

        assert _find_chrome() == "/usr/bin/google-chrome"

    def test_falls_back_to_the_macos_app_bundle_when_nothing_is_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The BUG-068 reproduction: nothing on PATH, but Chrome is installed.

        Fails before the fix, where ``which()`` returning ``None`` ended the
        search and the hero was never rendered.
        """
        bundle = tmp_path / "Google Chrome.app/Contents/MacOS/Google Chrome"
        bundle.parent.mkdir(parents=True)
        bundle.write_text("#!/bin/sh\n")
        monkeypatch.setattr(hero_svg.shutil, "which", lambda name: None)
        monkeypatch.setattr(hero_svg, "_CHROME_APP_PATHS", (bundle,))

        assert _find_chrome() == str(bundle)

    def test_path_wins_over_the_app_bundle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An operator-installed binary outranks the system default."""
        bundle = tmp_path / "Google Chrome"
        bundle.write_text("#!/bin/sh\n")
        monkeypatch.setattr(hero_svg.shutil, "which", lambda name: "/usr/bin/chromium")
        monkeypatch.setattr(hero_svg, "_CHROME_APP_PATHS", (bundle,))

        assert _find_chrome() == "/usr/bin/chromium"

    def test_returns_none_when_chrome_is_genuinely_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No Chrome anywhere still degrades to None, never raises.

        A vision *malfunction* must not affect the article (B-016b failure
        policy, row 2).
        """
        monkeypatch.setattr(hero_svg.shutil, "which", lambda name: None)
        monkeypatch.setattr(
            hero_svg, "_CHROME_APP_PATHS", (tmp_path / "does-not-exist",)
        )

        assert _find_chrome() is None
