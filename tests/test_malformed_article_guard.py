"""Prove-it tests for #323: malformed writer output guard.

Verifies that:
run_stage3 raises MalformedArticleError when the LLM returns prose
   instead of a well-formed article (unit level).
2. EconomistContentFlow.generate_content catches MalformedArticleError and
   returns a dict that quality_gate routes to revision (integration level).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ── Unit: stage3_runner ───────────────────────────────────────────────────────


class TestMalformedArticleError:
    """MalformedArticleError must exist and be a ValueError subclass."""

    @pytest.fixture(autouse=True)
    def _cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """BUG-082: the code under test writes cwd-relative paths; keep them in tmp_path."""
        monkeypatch.chdir(tmp_path)

    def test_error_class_exists(self) -> None:
        from src.agent_sdk.stage3_runner import MalformedArticleError

        assert issubclass(MalformedArticleError, ValueError)

    def test_run_stage3_raises_on_prose_output(self) -> None:
        """When the writer returns plain prose (no ---), raise MalformedArticleError."""
        from src.agent_sdk.stage3_runner import MalformedArticleError, run_stage3

        prose = "I apologise, but I cannot write that article at this time."

        with (
            patch(
                "src.agent_sdk.stage3_runner.build_research_brief", return_value="brief"
            ),
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(return_value=(prose, 0.01)),
            ),
            pytest.raises(MalformedArticleError),
        ):
            asyncio.run(run_stage3("AI Testing"))

    def test_run_stage3_raises_on_empty_body(self) -> None:
        """Frontmatter with no body is also malformed."""
        from src.agent_sdk.stage3_runner import MalformedArticleError, run_stage3

        no_body = "---\nlayout: post\ntitle: Test\n---\n"

        with (
            patch(
                "src.agent_sdk.stage3_runner.build_research_brief", return_value="brief"
            ),
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(return_value=(no_body, 0.01)),
            ),
            pytest.raises(MalformedArticleError),
        ):
            asyncio.run(run_stage3("AI Testing"))

    def test_run_stage3_does_not_raise_on_valid_article(self) -> None:
        """Well-formed frontmatter + body must not raise."""
        from src.agent_sdk.stage3_runner import run_stage3

        valid = (
            '---\nlayout: post\ntitle: "Test"\ndate: 2026-01-01\n'
            'author: "Ouray Viney"\ncategories: ["Quality Engineering"]\n'
            'description: "A test."\nimage: /assets/images/test.png\n'
            'image_alt: "alt"\nimage_caption: "cap"\n---\n\n'
            + " ".join(["word"] * 900)
            + '\n\n## References\n\n1. Gartner, ["Report"](https://example.com), 2024\n'
            '2. Forrester, ["Report"](https://example.com), 2024\n'
            '3. IEEE, ["Report"](https://example.com), 2024\n'
        )

        with (
            patch(
                "src.agent_sdk.stage3_runner.build_research_brief", return_value="brief"
            ),
            # B-042: one model call, not two. The second was the graphics agent
            # producing chart JSON; there is no graphics agent.
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(side_effect=[(valid, 0.01)]),
            ),
        ):
            result = asyncio.run(run_stage3("AI Testing"))
            assert result.article.startswith("---")
