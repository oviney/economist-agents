"""Prove-it tests for #323: malformed writer output guard.

Verifies that:
1. run_stage3 raises MalformedArticleError when the LLM returns prose
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
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(
                    side_effect=[
                        (valid, 0.01),
                        ('{"title":"Chart","data":[{"metric":"A","value":1}]}', 0.005),
                    ]
                ),
            ),
            patch(
                "src.agent_sdk.stage3_runner.render_chart",
                return_value=Path("output/charts/test.png"),
            ),
        ):
            result = asyncio.run(run_stage3("AI Testing"))
            assert result.article.startswith("---")

    def test_run_stage3_strips_code_fence_wrapped_article(self) -> None:
        """A valid article wrapped in a ```yaml fence must be unwrapped, not
        rejected. Prove-It for the writer emitting fenced output."""
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
        fenced = "```yaml\n" + valid + "\n```"

        with (
            patch(
                "src.agent_sdk.stage3_runner.build_research_brief", return_value="brief"
            ),
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(
                    side_effect=[
                        (fenced, 0.01),
                        ('{"title":"Chart","data":[{"metric":"A","value":1}]}', 0.005),
                    ]
                ),
            ),
            patch(
                "src.agent_sdk.stage3_runner.render_chart",
                return_value=Path("output/charts/test.png"),
            ),
        ):
            result = asyncio.run(run_stage3("AI Testing"))
            assert result.article.startswith("---")
            assert "```" not in result.article.split("\n", 1)[0]


class TestStripCodeFence:
    """Unit tests for the code-fence stripper."""

    def test_strips_yaml_fence_wrapper(self) -> None:
        from src.agent_sdk.stage3_runner import _strip_code_fence

        out = _strip_code_fence("```yaml\n---\ntitle: x\n---\nbody\n```")
        assert out.startswith("---")
        assert out.rstrip().endswith("body")

    def test_leaves_unfenced_text_untouched(self) -> None:
        from src.agent_sdk.stage3_runner import _strip_code_fence

        text = "---\ntitle: x\n---\nbody\n"
        assert _strip_code_fence(text) == text

    def test_preserves_inner_code_blocks(self) -> None:
        from src.agent_sdk.stage3_runner import _strip_code_fence

        out = _strip_code_fence(
            "```\n---\nt: x\n---\nsee `code`:\n```py\nx=1\n```\n```"
        )
        assert out.startswith("---")
        assert "```py" in out  # inner fence preserved

    def test_opening_fence_without_close_is_untouched(self) -> None:
        from src.agent_sdk.stage3_runner import _strip_code_fence

        text = "```yaml\n---\ntitle: x\n---\nbody without trailing fence"
        assert _strip_code_fence(text) == text


class TestExtractArticle:
    """Unit tests for the noisy-writer-output extractor."""

    def test_strips_conversational_preamble_and_fence(self) -> None:
        from src.agent_sdk.stage3_runner import _extract_article

        raw = (
            "Topic is fresh — no duplicate. I'll write directly.\n\n"
            "---\n\n"  # stray markdown rule in the preamble
            "```yaml\n"
            '---\nlayout: post\ntitle: "X"\n---\n\nThe body.\n\n## References\n\n1. Y\n'
            "```"
        )
        out = _extract_article(raw)
        assert out.startswith("---\nlayout: post")
        assert "The body." in out
        assert not out.rstrip().endswith("```")

    def test_leaves_clean_article_unchanged(self) -> None:
        from src.agent_sdk.stage3_runner import _extract_article

        clean = "---\ntitle: X\n---\n\nBody here.\n"
        assert _extract_article(clean).strip() == clean.strip()

    def test_prose_without_frontmatter_is_unchanged(self) -> None:
        from src.agent_sdk.stage3_runner import _extract_article

        prose = "I cannot write that article."
        assert _extract_article(prose).strip() == prose

    def test_run_stage3_recovers_preamble_wrapped_article(self) -> None:
        """run_stage3 must recover an article buried under preamble + a fence."""
        from src.agent_sdk.stage3_runner import run_stage3

        valid = (
            '---\nlayout: post\ntitle: "Test"\ndate: 2026-01-01\n'
            'author: "Ouray Viney"\ncategories: ["Quality Engineering"]\n'
            'description: "A test."\nimage: /assets/images/test.png\n'
            'image_alt: "alt"\nimage_caption: "cap"\n---\n\n'
            + " ".join(["word"] * 900)
            + '\n\n## References\n\n1. Gartner, ["R"](https://example.com), 2024\n'
            '2. Forrester, ["R"](https://example.com), 2024\n'
            '3. IEEE, ["R"](https://example.com), 2024\n'
        )
        noisy = "Topic is fresh. I'll write now.\n\n---\n\n```yaml\n" + valid + "\n```"

        with (
            patch(
                "src.agent_sdk.stage3_runner.build_research_brief", return_value="brief"
            ),
            patch(
                "src.agent_sdk.stage3_runner._collect_text",
                new=AsyncMock(
                    side_effect=[
                        (noisy, 0.01),
                        ('{"title":"Chart","data":[{"metric":"A","value":1}]}', 0.005),
                    ]
                ),
            ),
            patch(
                "src.agent_sdk.stage3_runner.render_chart",
                return_value=Path("output/charts/test.png"),
            ),
        ):
            result = asyncio.run(run_stage3("AI Testing"))
            assert result.article.startswith("---")


# ── Integration: generate_content routes to revision ─────────────────────────


class TestGenerateContentMalformedRouting:
    """generate_content must not crash on MalformedArticleError."""

    def test_generate_content_returns_revision_dict_on_malformed_output(self) -> None:
        """When run_pipeline raises MalformedArticleError, generate_content
        returns a dict with editorial_score=0 and publication_validator_passed=False
        so quality_gate routes to revision."""
        from src.agent_sdk.stage3_runner import MalformedArticleError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=MalformedArticleError("Writer returned prose"),
        ):
            result = flow.generate_content({"topic": "AI Testing"})

        assert result["publication_validator_passed"] is False
        assert result["editorial_score"] == 0

    def test_quality_gate_routes_to_revision_after_malformed(self) -> None:
        """The dict returned on MalformedArticleError must cause quality_gate
        to return 'revision'."""
        from src.agent_sdk.stage3_runner import MalformedArticleError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=MalformedArticleError("Writer returned prose"),
        ):
            draft = flow.generate_content({"topic": "AI Testing"})

        decision = flow.quality_gate(draft)
        assert decision == "revision"

    def test_request_revision_returns_needs_revision_on_malformed_output(self) -> None:
        """MalformedArticleError in the retry path must also be handled gracefully."""
        from src.agent_sdk.stage3_runner import MalformedArticleError
        from src.economist_agents.flow import EconomistContentFlow

        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "AI Testing"}
        flow.state["revision_feedback"] = ["fix the frontmatter"]
        flow.state["article_draft"] = {"featured_image": ""}

        with patch(
            "src.economist_agents.flow.asyncio.run",
            side_effect=MalformedArticleError("Prose output on retry"),
        ):
            result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert result["editorial_score"] == 0
