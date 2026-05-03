"""Integration tests for the rewritten EconomistContentFlow.

After ADR-0006 Phase 2 (epic #308) the flow no longer wraps CrewAI
crews; ``generate_content`` now calls ``src.agent_sdk.pipeline.run_pipeline``
directly. These tests mock the pipeline and the per-stage adapters so
each method can be exercised in isolation without spending API budget.

Replaces the now-skipped ``tests/test_economist_flow.py`` and the
``TestFlowOrchestration`` block in ``tests/test_production_integration.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.economist_agents.flow import (
    MAX_REVISIONS,
    PUBLISH_THRESHOLD,
    EconomistContentFlow,
)


@dataclass
class _FakePipelineResult:
    """Stand-in for the real PipelineResult used by run_pipeline."""

    article: str
    chart_data: dict
    editorial_score: int
    gates_passed: int
    publication_ready: bool
    publication_validator_passed: bool
    publication_validator_issues: list[dict[str, str]]
    total_cost_usd: float = 0.05
    writer_cost_usd: float = 0.04
    graphics_cost_usd: float = 0.01
    writer_model: str = "claude-sonnet-4-6"
    graphics_model: str = "claude-sonnet-4-6"
    stage3_seconds: float = 1.0
    stage4_seconds: float = 0.01
    article_chars: int = 500


_VALID_FRONTMATTER = (
    '---\nlayout: post\ntitle: "Specific Test Title"\n'
    'date: 2026-04-26\nauthor: "Test"\n'
    'description: "A concise SEO-friendly test article description here"\n'
    'categories: ["quality-engineering"]\n'
    "image: /assets/images/test.png\n---\n\nBody paragraph here.\n"
)


def _passing_pipeline_result() -> _FakePipelineResult:
    return _FakePipelineResult(
        article=_VALID_FRONTMATTER,
        chart_data={"title": "Chart"},
        editorial_score=88,
        gates_passed=5,
        publication_ready=True,
        publication_validator_passed=True,
        publication_validator_issues=[],
    )


# ─── stage 1 ────────────────────────────────────────────────────────────


class TestDiscoverTopics:
    @patch("src.economist_agents.flow.scout_topics")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_normalises_scout_scores(self, mock_client: Mock, mock_scout: Mock) -> None:
        mock_client.return_value = Mock()
        mock_scout.return_value = [
            {"topic": "Topic A", "total_score": 25},
            {"topic": "Topic B", "total_score": 15},
        ]
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        # Echo whatever topics get passed in so we can read the
        # post-normalisation scores back.
        flow._deduplicator.filter_topics.side_effect = lambda topics: (topics, [])

        result = flow.discover_topics()

        assert "topics" in result
        assert "timestamp" in result
        # 25/25 * 10 == 10.0; 15/25 * 10 == 6.0
        scores = [t["score"] for t in result["topics"]]
        assert scores == [10.0, 6.0]

    @patch("src.economist_agents.flow.scout_topics", return_value=[])
    @patch("src.economist_agents.flow.create_llm_client")
    def test_raises_when_scout_empty_after_retry(
        self,
        mock_client: Mock,
        mock_scout: Mock,
    ) -> None:
        mock_client.return_value = Mock()
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        flow._deduplicator.filter_topics.return_value = ([], [])
        with pytest.raises(ValueError, match="no topics"):
            flow.discover_topics()


# ─── stage 2 ────────────────────────────────────────────────────────────


class TestEditorialReview:
    @patch("src.economist_agents.flow.run_editorial_board")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_picks_board_top_pick(self, mock_client: Mock, mock_board: Mock) -> None:
        mock_client.return_value = Mock()
        mock_board.return_value = {
            "top_pick": {
                "topic": "Winner",
                "weighted_score": 8.5,
                "original_topic": {"hook": "h", "thesis": "t"},
            },
            "consensus": True,
            "dissenting_views": [],
        }
        flow = EconomistContentFlow()
        topics = {"topics": [{"topic": "Winner", "raw": {}, "score": 8.0}]}

        result = flow.editorial_review(topics)

        assert result["topic"] == "Winner"
        assert result["score"] == 8.5
        assert result["consensus"] is True

    @patch("src.economist_agents.flow.run_editorial_board")
    @patch("src.economist_agents.flow.create_llm_client")
    def test_falls_back_to_highest_scored(
        self,
        mock_client: Mock,
        mock_board: Mock,
    ) -> None:
        mock_client.return_value = Mock()
        mock_board.return_value = {"top_pick": None}
        flow = EconomistContentFlow()
        topics = {
            "topics": [
                {"topic": "Low", "score": 3.0},
                {"topic": "High", "score": 9.0},
            ],
        }

        result = flow.editorial_review(topics)

        assert result["topic"] == "High"

    def test_empty_topics_raises(self) -> None:
        flow = EconomistContentFlow()
        with pytest.raises(ValueError, match="No topics"):
            flow.editorial_review({"topics": []})


# ─── stage 3 ────────────────────────────────────────────────────────────


class TestGenerateContent:
    @patch("src.economist_agents.flow.generate_featured_image", return_value=False)
    @patch("src.economist_agents.flow.asyncio.run")
    def test_calls_pipeline_and_returns_article(
        self,
        mock_asyncio_run: Mock,
        mock_image: Mock,
    ) -> None:
        mock_asyncio_run.side_effect = [
            _passing_pipeline_result(),
            {"image_alt": "alt text", "image_caption": "caption text"},
        ]
        flow = EconomistContentFlow()

        result = flow.generate_content({"topic": "AI Testing"})

        # state preserved
        assert flow.state["selected_topic"]["topic"] == "AI Testing"
        # pipeline outputs propagated
        assert result["article"].startswith("---")
        assert result["chart_data"] == {"title": "Chart"}
        assert result["publication_validator_passed"] is True
        assert result["editorial_score"] == 88
        assert result["gates_passed"] == 5
        # image generation attempted; default returned
        assert result["featured_image"] == "/assets/images/blog-default.svg"

    @patch("src.economist_agents.flow.generate_featured_image", return_value=True)
    @patch("src.economist_agents.flow.asyncio.run")
    def test_uses_dalle_image_when_generated(
        self,
        mock_asyncio_run: Mock,
        mock_image: Mock,
    ) -> None:
        mock_asyncio_run.side_effect = [
            _passing_pipeline_result(),
            {"image_alt": "alt text", "image_caption": "caption text"},
        ]
        flow = EconomistContentFlow()

        result = flow.generate_content({"topic": "AI Coding Assistants"})

        assert result["featured_image"] == "/assets/images/ai-coding-assistants.png"

    @patch("src.economist_agents.flow.generate_featured_image", return_value=False)
    @patch("src.economist_agents.flow.asyncio.run")
    def test_refine_image_metadata_called_via_asyncio_run(
        self,
        mock_asyncio_run: Mock,
        mock_image: Mock,
    ) -> None:
        """asyncio.run must be called twice: once for run_pipeline, once for
        refine_image_metadata. The second call must receive a coroutine."""
        import asyncio as _asyncio

        mock_asyncio_run.side_effect = [
            _passing_pipeline_result(),
            {"image_alt": "editorial alt", "image_caption": "editorial caption"},
        ]
        flow = EconomistContentFlow()

        flow.generate_content({"topic": "AI Testing"})

        assert mock_asyncio_run.call_count == 2
        second_arg = mock_asyncio_run.call_args_list[1][0][0]
        assert _asyncio.iscoroutine(second_arg), (
            "Second asyncio.run() call should pass the refine_image_metadata coroutine, "
            f"got {type(second_arg)}"
        )
        second_arg.close()  # prevent ResourceWarning


# ─── stage 4 routing ────────────────────────────────────────────────────


class TestQualityGate:
    def _draft(self, **overrides: Any) -> dict[str, Any]:
        draft = {
            "article": _VALID_FRONTMATTER,
            "featured_image": "/assets/images/test.png",
            "editorial_score": 88,
            "gates_passed": 5,
            "publication_validator_passed": True,
            "publication_validator_issues": [],
        }
        draft.update(overrides)
        return draft

    def test_publish_when_score_and_validator_pass(self) -> None:
        flow = EconomistContentFlow()
        decision = flow.quality_gate(self._draft())
        assert decision == "publish"
        assert flow.state["decision"] == "publish"

    def test_revision_when_score_below_threshold(self) -> None:
        flow = EconomistContentFlow()
        decision = flow.quality_gate(self._draft(editorial_score=PUBLISH_THRESHOLD - 1))
        assert decision == "revision"
        assert "below" in flow.state["revision_reason"]

    def test_revision_when_validator_fails(self) -> None:
        flow = EconomistContentFlow()
        draft = self._draft(
            publication_validator_passed=False,
            publication_validator_issues=[
                {
                    "check": "word_count",
                    "severity": "CRITICAL",
                    "message": "too short",
                },
            ],
        )
        decision = flow.quality_gate(draft)
        assert decision == "revision"
        # Feedback contains the issue message; the check name is in the
        # log line but not in the feedback payload.
        assert any("too short" in m for m in flow.state["revision_feedback"])

    def test_frontmatter_schema_failure_routes_to_revision(self) -> None:
        flow = EconomistContentFlow()
        # Strip required frontmatter to trigger schema rejection
        bad = self._draft(article="No frontmatter here at all.\n")
        decision = flow.quality_gate(bad)
        assert decision == "revision"
        assert "schema" in flow.state["revision_reason"].lower()


# ─── publish + revise terminal paths ────────────────────────────────────


class TestPublishArticle:
    def test_publishes_and_indexes(self) -> None:
        flow = EconomistContentFlow()
        flow._deduplicator = Mock()
        flow.state["selected_topic"] = {"topic": "Indexed Topic"}
        flow.state["quality_result"] = {
            "article": _VALID_FRONTMATTER,
            "editorial_score": 90,
            "gates_passed": 5,
        }

        result = flow.publish_article()

        assert result["status"] == "published"
        flow._deduplicator.index_article.assert_called_once()
        kwargs = flow._deduplicator.index_article.call_args.kwargs
        assert kwargs["title"] == "Indexed Topic"


class TestRequestRevision:
    @patch("src.economist_agents.flow.asyncio.run")
    def test_succeeds_on_retry(self, mock_asyncio_run: Mock) -> None:
        mock_asyncio_run.return_value = _passing_pipeline_result()
        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "Retry Me"}
        flow.state["revision_feedback"] = ["fix the ending"]
        flow.state["article_draft"] = {"featured_image": "/assets/images/test.png"}

        result = flow.request_revision()

        assert result["status"] == "published"
        assert result["retry_count"] == 1

    @patch("src.economist_agents.flow.asyncio.run")
    def test_quarantines_when_retry_still_fails(
        self,
        mock_asyncio_run: Mock,
        tmp_path,
    ) -> None:
        failing = _passing_pipeline_result()
        failing.publication_validator_passed = False
        failing.publication_validator_issues = [
            {
                "check": "word_count",
                "severity": "CRITICAL",
                "message": "still too short",
            },
        ]
        failing.editorial_score = 40
        mock_asyncio_run.return_value = failing

        flow = EconomistContentFlow()
        flow.state["selected_topic"] = {"topic": "Stuck Topic"}
        flow.state["revision_feedback"] = ["fix"]
        flow.state["article_draft"] = {"featured_image": "/assets/images/test.png"}

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert "quarantine_path" in result

    def test_exhausted_retry_returns_needs_revision(self) -> None:
        flow = EconomistContentFlow()
        flow.state["retry_count"] = MAX_REVISIONS
        flow.state["quality_result"] = {"editorial_score": 50, "gates_passed": 2}
        flow.state["revision_reason"] = "out of retries"

        result = flow.request_revision()

        assert result["status"] == "needs_revision"
        assert result["retry_count"] == MAX_REVISIONS


# ─── helper ─────────────────────────────────────────────────────────────


class TestPatchFrontmatter:
    def test_overrides_image_path(self) -> None:
        article = "---\nlayout: post\ntitle: T\nimage: /old.png\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(
            article,
            "/assets/images/new.png",
        )
        assert "image: /assets/images/new.png" in patched
        assert "/old.png" not in patched

    def test_renames_summary_to_description(self) -> None:
        article = "---\nlayout: post\ntitle: T\nsummary: Hello\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(article, "")
        assert "description: Hello" in patched
        assert "summary:" not in patched

    def test_no_op_when_not_frontmatter(self) -> None:
        article = "Plain text without delimiters."
        assert EconomistContentFlow._patch_frontmatter(article, "/x.png") == article


# ─── BUG-037: image_alt + image_caption pipeline contract ────────────────
#
# RED tests — these must fail until implementation is complete.
# Do not implement the fix until all four tests are verified failing.


class TestWriterPromptImageMetadata:
    """Writer prompt must instruct the agent to emit image_alt and image_caption
    in the article frontmatter.  Fails until stage3_runner.py is updated."""

    def test_writer_prompt_requires_image_alt(self) -> None:
        import inspect

        import src.agent_sdk.stage3_runner as m

        source = inspect.getsource(m)
        assert "image_alt" in source, (
            "stage3_runner writer prompt must require image_alt in frontmatter"
        )

    def test_writer_prompt_requires_image_caption(self) -> None:
        import inspect

        import src.agent_sdk.stage3_runner as m

        source = inspect.getsource(m)
        assert "image_caption" in source, (
            "stage3_runner writer prompt must require image_caption in frontmatter"
        )


class TestVisionRefinement:
    """After image generation, a Claude vision call grounds image_alt and
    image_caption against the actual visual.  Fails until the refinement
    function is added to stage3_runner."""

    def test_refine_image_metadata_function_exists(self) -> None:
        import src.agent_sdk._shared as m

        assert hasattr(m, "refine_image_metadata"), (
            "_shared must expose a refine_image_metadata(image_path, "
            "draft_alt, draft_caption) async function"
        )

    def test_refine_image_metadata_returns_grounded_fields(
        self, tmp_path: Path
    ) -> None:
        """When Anthropic returns a vision response, refine_image_metadata
        parses and returns grounded image_alt and image_caption."""
        import asyncio
        import os
        from unittest.mock import AsyncMock, MagicMock, patch

        import src.agent_sdk._shared as m

        assert hasattr(m, "refine_image_metadata"), (
            "refine_image_metadata not yet implemented in _shared"
        )

        # Create a real file so the path.exists() guard passes
        img = tmp_path / "test.png"
        img.write_bytes(b"PNG")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"image_alt": "A grounded alt", "image_caption": "The caption"}'
            )
        ]
        mock_create = AsyncMock(return_value=mock_response)
        with (
            patch("anthropic.AsyncAnthropic") as mock_async_class,
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            mock_async_class.return_value.messages.create = mock_create
            result = asyncio.run(
                m.refine_image_metadata(
                    image_path=str(img),
                    draft_alt="draft alt",
                    draft_caption="draft caption",
                )
            )
        assert result["image_alt"] == "A grounded alt"
        assert result["image_caption"] == "The caption"

    def test_returns_drafts_when_no_api_key(self, tmp_path: Path) -> None:
        """Fallback branch 1: no ANTHROPIC_API_KEY → writer drafts returned."""
        import asyncio
        import os
        from unittest.mock import patch

        import src.agent_sdk._shared as m

        img = tmp_path / "test.png"
        img.write_bytes(b"PNG")

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = asyncio.run(
                m.refine_image_metadata(
                    image_path=str(img),
                    draft_alt="draft",
                    draft_caption="cap",
                )
            )
        assert result == {"image_alt": "draft", "image_caption": "cap"}

    def test_returns_drafts_when_image_missing(self) -> None:
        """Fallback branch 2: image file does not exist → writer drafts returned."""
        import asyncio
        import os
        from unittest.mock import patch

        import src.agent_sdk._shared as m

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = asyncio.run(
                m.refine_image_metadata(
                    image_path="/tmp/does_not_exist_xyz.png",
                    draft_alt="draft",
                    draft_caption="cap",
                )
            )
        assert result == {"image_alt": "draft", "image_caption": "cap"}

    def test_returns_drafts_when_vision_response_is_prose(self, tmp_path: Path) -> None:
        """Fallback branch 3: Claude returns prose instead of JSON →
        json.loads raises, except catches it, writer drafts returned."""
        import asyncio
        import os
        from unittest.mock import AsyncMock, MagicMock, patch

        import src.agent_sdk._shared as m

        img = tmp_path / "test.png"
        img.write_bytes(b"PNG")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Here is your alt text: great picture.")
        ]
        mock_create = AsyncMock(return_value=mock_response)
        with (
            patch("anthropic.AsyncAnthropic") as mock_async_class,
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            mock_async_class.return_value.messages.create = mock_create
            result = asyncio.run(
                m.refine_image_metadata(
                    image_path=str(img),
                    draft_alt="draft",
                    draft_caption="cap",
                )
            )
        assert result == {"image_alt": "draft", "image_caption": "cap"}

    def test_vision_model_comes_from_env_var(self, tmp_path: Path) -> None:
        """Model passed to messages.create must be VISION_MODEL env var, not hardcoded."""
        import asyncio
        import os
        from unittest.mock import AsyncMock, MagicMock, patch

        import src.agent_sdk._shared as m

        img = tmp_path / "test.png"
        img.write_bytes(b"PNG")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"image_alt": "alt", "image_caption": "cap"}')
        ]
        mock_create = AsyncMock(return_value=mock_response)

        with (
            patch("anthropic.AsyncAnthropic") as mock_async_class,
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "VISION_MODEL": "claude-haiku-4-5"}),
        ):
            mock_async_class.return_value.messages.create = mock_create
            asyncio.run(
                m.refine_image_metadata(
                    image_path=str(img),
                    draft_alt="draft alt",
                    draft_caption="draft caption",
                )
            )

        called_model = mock_create.call_args.kwargs.get("model") or mock_create.call_args.args[0] if mock_create.call_args.args else None
        if called_model is None:
            called_model = mock_create.call_args[1].get("model")
        assert called_model == "claude-haiku-4-5", (
            f"Expected VISION_MODEL env var 'claude-haiku-4-5', got '{called_model}'"
        )

    def test_vision_model_defaults_to_claude_sonnet_when_env_unset(self, tmp_path: Path) -> None:
        """When VISION_MODEL is not set, model must default to claude-sonnet-4-6."""
        import asyncio
        import os
        from unittest.mock import AsyncMock, MagicMock, patch

        import src.agent_sdk._shared as m

        img = tmp_path / "test.png"
        img.write_bytes(b"PNG")

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"image_alt": "alt", "image_caption": "cap"}')
        ]
        mock_create = AsyncMock(return_value=mock_response)

        env = {k: v for k, v in os.environ.items() if k != "VISION_MODEL"}
        env["ANTHROPIC_API_KEY"] = "test-key"

        with (
            patch("anthropic.AsyncAnthropic") as mock_async_class,
            patch.dict(os.environ, env, clear=True),
        ):
            mock_async_class.return_value.messages.create = mock_create
            asyncio.run(
                m.refine_image_metadata(
                    image_path=str(img),
                    draft_alt="draft alt",
                    draft_caption="draft caption",
                )
            )

        called_model = mock_create.call_args.kwargs.get("model") or mock_create.call_args[1].get("model")
        assert called_model == "claude-sonnet-4-6", (
            f"Expected default 'claude-sonnet-4-6', got '{called_model}'"
        )


class TestPatchFrontmatterImageMetadata:
    """_patch_frontmatter must inject image_alt and image_caption when provided.
    Fails until the method signature and body are extended."""

    def test_injects_image_alt(self) -> None:
        article = "---\nlayout: post\ntitle: T\nimage: /x.png\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(
            article,
            "/x.png",
            image_alt="An editorial illustration of a pipeline",
        )
        assert "image_alt:" in patched
        assert "editorial illustration" in patched

    def test_injects_image_caption(self) -> None:
        article = "---\nlayout: post\ntitle: T\nimage: /x.png\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(
            article,
            "/x.png",
            image_caption="The gap between promise and delivery",
        )
        assert "image_caption:" in patched
        assert "gap between promise" in patched

    def test_no_injection_when_fields_absent(self) -> None:
        """Calling without the new kwargs must not break existing behaviour."""
        article = "---\nlayout: post\ntitle: T\nimage: /x.png\n---\n\nBody"
        patched = EconomistContentFlow._patch_frontmatter(article, "/x.png")
        assert "image_alt" not in patched
        assert "image_caption" not in patched

    def test_replaces_existing_image_alt_not_duplicates(self) -> None:
        """If the writer already emitted image_alt, the grounded value must win
        and there must be exactly one image_alt key — no duplicate YAML keys."""
        article = (
            "---\nlayout: post\ntitle: T\nimage: /x.png\n"
            'image_alt: "writer draft version"\n---\n\nBody'
        )
        patched = EconomistContentFlow._patch_frontmatter(
            article,
            "/x.png",
            image_alt="Grounded by Claude vision",
        )
        assert "Grounded by Claude vision" in patched
        assert "writer draft version" not in patched
        assert patched.count("image_alt:") == 1, (
            "duplicate image_alt key in frontmatter"
        )

    def test_replaces_existing_image_caption_not_duplicates(self) -> None:
        """Same collision guard for image_caption."""
        article = (
            "---\nlayout: post\ntitle: T\nimage: /x.png\n"
            'image_caption: "writer draft caption"\n---\n\nBody'
        )
        patched = EconomistContentFlow._patch_frontmatter(
            article,
            "/x.png",
            image_caption="Grounded caption",
        )
        assert "Grounded caption" in patched
        assert "writer draft caption" not in patched
        assert patched.count("image_caption:") == 1, "duplicate image_caption key"


class TestQualityGateImageMetadataGates:
    """End-to-end: an article carrying image_alt and image_caption must pass
    the publication validator's CRITICAL image metadata gates and route to
    'publish', not 'revision'.  Fails until the full pipeline change lands."""

    _ALT = "An Economist-style editorial illustration of a quality pipeline"
    _CAPTION = "The gap between coverage metrics and shipping confidence"

    def _draft_with_image_metadata(self) -> dict[str, Any]:
        article = (
            "---\n"
            "layout: post\n"
            'title: "AI Testing: The 80-Percent Problem"\n'
            "date: 2026-04-30\n"
            'author: "Ouray Viney"\n'
            'categories: ["Quality Engineering"]\n'
            "image: /assets/images/ai-testing.png\n"
            f'image_alt: "{self._ALT}"\n'
            f'image_caption: "{self._CAPTION}"\n'
            'description: "Why AI test generators optimise for coverage not quality"\n'
            "---\n\n"
            + " ".join(["word"] * 850)
            + "\n\nAs the chart shows, the data is clear.\n\n"
            "![Chart](/assets/charts/ai-testing.png)\n\n"
            "## References\n\n"
            '1. Gartner, ["Report"](https://gartner.com), *Gartner*, 2024\n'
            '2. Forrester, ["Study"](https://forrester.com), *Forrester*, 2024\n'
            '3. IEEE, ["Standards"](https://ieee.org), *IEEE*, 2024\n'
        )
        return {
            "article": article,
            "featured_image": "/assets/images/ai-testing.png",
            "image_alt": self._ALT,
            "image_caption": self._CAPTION,
            "editorial_score": 88,
            "gates_passed": 5,
            "publication_validator_passed": True,
            "publication_validator_issues": [],
        }

    def test_image_metadata_present_routes_to_publish(self) -> None:
        flow = EconomistContentFlow()
        draft = self._draft_with_image_metadata()
        decision = flow.quality_gate(draft)
        assert decision == "publish", (
            f"Expected 'publish' but got '{decision}'. "
            f"Revision reason: {flow.state.get('revision_reason')}"
        )

    def test_validator_passes_image_metadata_gates(self) -> None:
        from scripts.publication_validator import PublicationValidator

        draft = self._draft_with_image_metadata()
        validator = PublicationValidator(expected_date="2026-04-30")
        is_valid, issues = validator.validate(draft["article"])
        image_critical = [
            i
            for i in issues
            if i["check"]
            in (
                "missing_image",
                "default_image_fallback",
                "missing_image_alt",
                "missing_image_caption",
            )
            and i["severity"] == "CRITICAL"
        ]
        assert image_critical == [], (
            f"Image metadata CRITICAL gates fired: {image_critical}"
        )
