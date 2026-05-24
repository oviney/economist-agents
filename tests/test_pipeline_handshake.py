"""Tests for #403 slice 3: pipeline.py --resume / --no-image / exit 10.

Covers the three-mode CLI:
  - default: Stage 3 only, writes artefacts, prints handshake, exits 10
  - --resume <slug>: Stage 4 only, requires the dropped image
  - --resume <slug> --no-image: strips image fields, Stage 4 ships chart-only
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.agent_sdk import pipeline as pl
from src.agent_sdk.pipeline import (
    EXIT_HANDSHAKE_PENDING,
    _load_state,
    _persist_stage3_artefacts,
    _strip_image_frontmatter,
)
from src.agent_sdk.stage3_runner import Stage3Result


def _fake_stage3(
    slug: str = "test-slug", *, chart_path: Path | None = None
) -> Stage3Result:
    return Stage3Result(
        topic="test topic",
        article=(
            "---\nlayout: post\ntitle: T\n"
            "image: /assets/images/test-slug.png\n"
            "image_alt: alt\nimage_caption: cap\n---\n\nBody.\n"
        ),
        chart_data={"title": "T", "data": [{"metric": "A", "value": 1}]},
        total_cost_usd=0.1,
        writer_cost_usd=0.08,
        graphics_cost_usd=0.02,
        writer_model="claude-sonnet-4-6",
        graphics_model="claude-sonnet-4-6",
        wall_seconds=10.0,
        research_brief_chars=500,
        article_chars=200,
        stat_audit_removed=0,
        chart_path=chart_path,
        prompt_path=None,
        slug=slug,
        image_prompt="paste this into ChatGPT",
    )


# ── _strip_image_frontmatter ─────────────────────────────────────────


class TestStripImageFrontmatter:
    def test_removes_all_three_image_fields(self) -> None:
        article = (
            "---\nlayout: post\ntitle: x\n"
            "image: /assets/images/x.png\n"
            'image_alt: "alt text"\n'
            "image_caption: caption text\n"
            "---\n\nBody.\n"
        )
        out = _strip_image_frontmatter(article)
        assert "image:" not in out.split("---")[1]
        assert "image_alt:" not in out.split("---")[1]
        assert "image_caption:" not in out.split("---")[1]

    def test_preserves_other_frontmatter_fields(self) -> None:
        article = (
            "---\nlayout: post\ntitle: Keep Me\n"
            "image: /assets/images/x.png\n"
            "author: Ouray Viney\n"
            "---\n\nBody.\n"
        )
        out = _strip_image_frontmatter(article)
        assert "title: Keep Me" in out
        assert "author: Ouray Viney" in out
        assert "image:" not in out.split("---")[1]

    def test_preserves_body_chart_embed(self) -> None:
        # The body's ![Chart](/assets/charts/x.png) reference must NOT be
        # touched — it's chart-only mode, the chart still ships.
        article = (
            "---\nlayout: post\ntitle: x\nimage: /assets/images/x.png\n---\n\n"
            "Body.\n\n![Chart](/assets/charts/x.png)\n"
        )
        out = _strip_image_frontmatter(article)
        assert "![Chart](/assets/charts/x.png)" in out

    def test_noop_when_no_image_fields_present(self) -> None:
        article = "---\nlayout: post\ntitle: x\n---\n\nBody.\n"
        assert _strip_image_frontmatter(article) == article

    def test_noop_when_no_frontmatter(self) -> None:
        article = "Just a body, no frontmatter.\n"
        assert _strip_image_frontmatter(article) == article


# ── state persistence ────────────────────────────────────────────────


class TestStatePersistence:
    def test_persist_writes_article_and_state_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        s3 = _fake_stage3()
        artefacts = _persist_stage3_artefacts(s3)

        assert artefacts.article_path == Path("output/posts/test-slug.md")
        assert artefacts.article_path.exists()
        assert artefacts.article_path.read_text() == s3.article
        assert artefacts.state_path == Path("output/state/test-slug.json")
        assert artefacts.state_path.exists()

    def test_state_round_trips_chart_data_for_stage4(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        s3 = _fake_stage3()
        _persist_stage3_artefacts(s3)
        state = _load_state("test-slug")
        # chart_data must survive JSON round-trip so Stage 4 can consume it
        # without re-reading the chart spec file.
        assert state["chart_data"] == s3.chart_data
        assert state["topic"] == s3.topic
        assert state["metrics"]["writer_cost_usd"] == s3.writer_cost_usd

    def test_load_state_missing_slug_raises_with_actionable_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="No Stage 3 state"):
            _load_state("never-generated")


# ── CLI mode dispatch ────────────────────────────────────────────────


class TestPipelineMain:
    def test_default_mode_exits_with_handshake_code_after_stage3(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bare ``pipeline 'topic'`` runs Stage 3 only, writes artefacts,
        prints handshake message, exits 10 (does NOT run Stage 4)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "test topic"])

        fake_s3 = _fake_stage3()

        async def fake_run_stage3(*args, **kwargs):
            return fake_s3

        # If Stage 4 runs in default mode we have a bug — assert it doesn't.
        run_stage4_mock = MagicMock()
        monkeypatch.setattr("src.agent_sdk.pipeline.run_stage4", run_stage4_mock)
        monkeypatch.setattr("src.agent_sdk.pipeline.run_stage3", fake_run_stage3)

        with pytest.raises(SystemExit) as exc_info:
            pl.main()
        assert exc_info.value.code == EXIT_HANDSHAKE_PENDING
        run_stage4_mock.assert_not_called()
        # Artefacts landed at slug-keyed paths
        assert Path("output/posts/test-slug.md").exists()
        assert Path("output/state/test-slug.json").exists()

    def test_resume_no_image_runs_stage4_without_image_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        # Pre-seed state (as Stage 3 would have)
        _persist_stage3_artefacts(_fake_stage3())

        monkeypatch.setattr(
            sys, "argv", ["pipeline.py", "--resume", "test-slug", "--no-image"]
        )

        captured_article = []
        fake_stage4 = MagicMock()
        fake_stage4.return_value = MagicMock(
            article="polished",
            editorial_score=90,
            gates_passed=5,
            publication_ready=True,
            publication_validator_passed=True,
            publication_validator_issues=[],
        )

        def _capture(article, chart_data):
            captured_article.append(article)
            return fake_stage4.return_value

        monkeypatch.setattr("src.agent_sdk.pipeline.run_stage4", _capture)
        pl.main()
        assert captured_article, "Stage 4 was not called"
        polished_input = captured_article[0]
        # image: / image_alt: / image_caption: must have been stripped
        # before Stage 4 saw the article
        assert "image:" not in polished_input.split("---")[1]
        assert "image_alt:" not in polished_input.split("---")[1]
        assert "image_caption:" not in polished_input.split("---")[1]

    def test_resume_with_unknown_slug_exits_1_with_clear_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "--resume", "never-was"])
        with pytest.raises(SystemExit) as exc_info:
            pl.main()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "No Stage 3 state" in err
        assert "never-was" in err

    def test_handshake_message_includes_prompt_drop_path_and_resume_command(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "test topic"])

        async def fake_run_stage3(*args, **kwargs):
            return _fake_stage3()

        monkeypatch.setattr("src.agent_sdk.pipeline.run_stage3", fake_run_stage3)
        monkeypatch.setattr("src.agent_sdk.pipeline.run_stage4", MagicMock())
        with pytest.raises(SystemExit):
            pl.main()
        out = capsys.readouterr().out
        # Verbose handoff per spec Q2: paste-ready prompt + drop path + resume cmd
        assert "paste this into ChatGPT" in out
        assert "output/posts/images/test-slug.png" in out
        assert "--resume test-slug" in out
        assert "--no-image" in out  # alternate path also shown
