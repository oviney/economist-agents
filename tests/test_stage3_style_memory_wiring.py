#!/usr/bin/env python3
"""Tests for issue #339 — StyleMemoryTool wiring into ``run_stage3``.

Validates that the writer prompt built inside
``src.agent_sdk.stage3_runner.run_stage3`` includes a ``## Style Memory``
section populated from ``StyleMemoryTool.get_style_context(topic)`` when
ChromaDB returns results, and omits the section entirely when it does
not.

We exercise ``run_stage3`` end-to-end with two patches:

1. ``build_research_brief`` is stubbed to a deterministic string so the
   research path does not hit the network.
2. ``_collect_text`` is stubbed to capture the writer/graphics prompts
   instead of calling the Anthropic API. The captured writer prompt is
   the unit under test.

``_fetch_style_context`` is patched directly to model the two states the
tool can be in (results vs. empty) without depending on a populated
ChromaDB collection at test time.
"""

from __future__ import annotations

import asyncio
import re
from unittest.mock import AsyncMock, patch

import pytest

import src.agent_sdk.stage3_runner as stage3_runner
from src.agent_sdk.stage3_runner import run_stage3


VALID_ARTICLE = (
    "---\n"
    "layout: post\n"
    "title: Test\n"
    "date: 2026-01-01\n"
    "author: Test\n"
    "categories: Software Engineering\n"
    "image: /assets/images/test.png\n"
    "description: Test description.\n"
    "image_alt: Test alt.\n"
    "image_caption: Test caption.\n"
    "---\n"
    "\n"
    "A debatable thesis paragraph that opens the article.\n"
    "\n"
    "## References\n"
    "\n"
    "1. https://example.com\n"
)


@pytest.fixture
def captured_prompts() -> dict[str, str]:
    """Container the patched ``_collect_text`` writes into."""
    return {}


@pytest.fixture
def stub_pipeline(captured_prompts):
    """Stub research + Agent SDK calls so ``run_stage3`` runs offline.

    The first call to ``_collect_text`` (the writer) records its prompt
    under ``captured_prompts["writer"]`` and returns a minimally valid
    article. The second call (graphics) returns a trivial JSON chart.
    """

    async def fake_collect_text(prompt, system_prompt, **kwargs):
        if "writer" not in captured_prompts:
            captured_prompts["writer"] = prompt
            return VALID_ARTICLE, 0.0
        captured_prompts["graphics"] = prompt
        return '{"title": "t", "data": []}', 0.0

    with (
        patch.object(
            stage3_runner,
            "build_research_brief",
            return_value="STUB RESEARCH BRIEF",
        ),
        patch.object(
            stage3_runner,
            "_collect_text",
            AsyncMock(side_effect=fake_collect_text),
        ),
    ):
        yield


class TestStyleMemoryWiring:
    """``run_stage3`` injects style-memory exemplars when available."""

    def test_style_section_present_when_chromadb_returns_results(
        self, stub_pipeline, captured_prompts
    ) -> None:
        """AC2 — the ``## Style Memory`` section appears after the brief."""
        exemplars = (
            "Reference these voice exemplars from Gold Standard articles.\n"
            "\n"
            "1. (source: foo.md, score: 0.91)\n"
            "   > Sample exemplar paragraph.\n"
        )
        with patch.object(
            stage3_runner, "_fetch_style_context", return_value=exemplars
        ):
            asyncio.run(run_stage3("a topic"))

        prompt = captured_prompts["writer"]
        assert "## Style Memory" in prompt, "Style Memory heading missing from prompt"
        assert "Sample exemplar paragraph." in prompt

        # AC2 — heading must appear after the research brief, not before.
        brief_idx = prompt.index("RESEARCH BRIEF")
        style_idx = prompt.index("## Style Memory")
        assert style_idx > brief_idx, (
            "## Style Memory must appear after RESEARCH BRIEF"
        )

    def test_style_section_omitted_when_chromadb_empty(
        self, stub_pipeline, captured_prompts
    ) -> None:
        """AC3 — empty/cold ChromaDB results omit the section entirely."""
        with patch.object(stage3_runner, "_fetch_style_context", return_value=""):
            asyncio.run(run_stage3("a topic"))

        prompt = captured_prompts["writer"]
        assert "## Style Memory" not in prompt, (
            "Empty style context must not emit an empty heading"
        )
        # No trailing whitespace explosion at the join site.
        assert not re.search(r"STUB RESEARCH BRIEF\s{3,}$", prompt)

    def test_run_stage3_invokes_fetch_style_context_with_topic(
        self, stub_pipeline, captured_prompts
    ) -> None:
        """AC1 — ``run_stage3`` calls the style fetcher with the topic."""
        with patch.object(
            stage3_runner, "_fetch_style_context", return_value=""
        ) as mock_fetch:
            asyncio.run(run_stage3("how AI agents change software testing"))
        mock_fetch.assert_called_once_with("how AI agents change software testing")


class TestGetStyleContextMethod:
    """``StyleMemoryTool.get_style_context`` formats exemplars correctly."""

    def test_returns_empty_when_query_returns_no_results(self) -> None:
        from src.tools.style_memory_tool import StyleMemoryTool

        tool = StyleMemoryTool.__new__(StyleMemoryTool)
        tool.collection = object()  # truthy — passes the early-return gate
        with patch.object(
            StyleMemoryTool, "query", return_value=[]
        ):
            assert tool.get_style_context("anything") == ""

    def test_returns_empty_for_empty_topic(self) -> None:
        from src.tools.style_memory_tool import StyleMemoryTool

        tool = StyleMemoryTool.__new__(StyleMemoryTool)
        tool.collection = object()
        assert tool.get_style_context("") == ""
        assert tool.get_style_context("   ") == ""

    def test_formats_results_as_markdown_block(self) -> None:
        from src.tools.style_memory_tool import StyleMemoryTool

        tool = StyleMemoryTool.__new__(StyleMemoryTool)
        tool.collection = object()
        fake_results = [
            {
                "text": "Companies are racing to ship AI agents.",
                "score": 0.88,
                "source": "ai-agents.md",
                "paragraph": 0,
            },
            {
                "text": "The chart makes clear how fast adoption grew.",
                "score": 0.81,
                "source": "adoption.md",
                "paragraph": 4,
            },
        ]
        with patch.object(StyleMemoryTool, "query", return_value=fake_results):
            out = tool.get_style_context("ai agents")

        assert "Companies are racing" in out
        assert "The chart makes clear" in out
        assert "ai-agents.md" in out
        assert "adoption.md" in out
        # Format checks: numbered, scores rendered, no empty trailing heading.
        assert "1. (source: ai-agents.md" in out
        assert "2. (source: adoption.md" in out


class TestFetchStyleContextHelper:
    """``_fetch_style_context`` swallows failures and returns ``''``."""

    def test_returns_empty_when_tool_raises(self) -> None:
        with patch(
            "src.tools.style_memory_tool.StyleMemoryTool",
            side_effect=RuntimeError("chromadb down"),
        ):
            assert stage3_runner._fetch_style_context("any topic") == ""

    def test_returns_tool_output_on_success(self) -> None:
        class _FakeTool:
            def get_style_context(self, topic):
                return f"exemplars for {topic}"

        with patch(
            "src.tools.style_memory_tool.StyleMemoryTool",
            return_value=_FakeTool(),
        ):
            assert (
                stage3_runner._fetch_style_context("a topic")
                == "exemplars for a topic"
            )
