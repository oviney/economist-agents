#!/usr/bin/env python3
"""B-016b slices 3+4: Claude authors the hero SVG, then critiques its own render.

Spec: ``docs/specs/B-016b-automatic-hero-svg.md``.

The critique exists because the structural gate is blind to composition — every
real defect in the first hand-authored hero passed all nine rules and was only
visible in a render.

These tests pin the *control flow* (retry, cap, degradation, exit semantics). They
cannot pin drawing quality; that is verified by generating real heroes and looking
at them, per Operating Constraint #4.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent_sdk import hero_author

_GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
    "<title>A green build drains the budget</title>"
    "<desc>An engineer presses a green button while coins pour into a drain.</desc>"
    + '<rect width="40" height="40" fill="#0f3a5f"/>' * 14
    + "</svg>"
)

_BAD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 900"><title>x</title><desc>y</desc></svg>'

_BRIEF = "Subject: an engineer pressing a green tick while money drains away."


class _Recorder:
    """Records prompts and returns queued replies — stands in for the Agent SDK."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def __call__(
        self, prompt: str, *args: object, **kwargs: object
    ) -> tuple[str, float]:
        self.prompts.append(prompt)
        return (self.replies.pop(0) if self.replies else ""), 0.0


@pytest.fixture
def _no_render(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: rendering unavailable, so the critique is skipped."""
    monkeypatch.setattr(hero_author, "render_to_png", lambda svg, png: None)


class TestAuthoring:
    def test_writes_the_svg_and_returns_its_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        monkeypatch.setattr(hero_author, "_collect_text", _Recorder([_GOOD_SVG]))
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="my-slug", images_dir=tmp_path
        )
        assert result.path == tmp_path / "my-slug-hero.svg"
        assert result.path.read_text() == _GOOD_SVG
        assert result.critique == ""

    def test_strips_a_markdown_fence_and_preamble(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        # The model routinely wraps output in prose and fences; the gate rejects
        # that as malformed XML, so extraction has to happen first.
        wrapped = f"Here is the hero:\n\n```svg\n{_GOOD_SVG}\n```\nHope that helps."
        monkeypatch.setattr(hero_author, "_collect_text", _Recorder([wrapped]))
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None
        assert result.path.read_text().startswith("<svg")

    def test_retries_when_the_structural_gate_rejects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        recorder = _Recorder([_BAD_SVG, _GOOD_SVG])
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None
        assert len(recorder.prompts) == 2
        # The retry must tell the model what was wrong, or it will repeat itself.
        assert "aspect ratio" in recorder.prompts[1]

    def test_gives_up_after_the_attempt_cap_and_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        recorder = _Recorder([_BAD_SVG] * 6)
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is None
        assert list(tmp_path.iterdir()) == []
        assert len(recorder.prompts) == hero_author._MAX_STRUCTURAL_ATTEMPTS
        assert "aspect ratio" in result.error

    def test_an_sdk_failure_degrades_to_no_hero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        async def boom(*a: object, **k: object) -> tuple[str, float]:
            raise RuntimeError("SDK exploded")

        monkeypatch.setattr(hero_author, "_collect_text", boom)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is None
        assert "SDK exploded" in result.error


class TestCritiqueLoop:
    """A vision *verdict* may fail the run; a vision *malfunction* may not."""

    def _with_render(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def fake_render(svg: Path, png: Path) -> Path:
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
            return png

        monkeypatch.setattr(hero_author, "render_to_png", fake_render)

    def test_a_clean_verdict_ends_the_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._with_render(monkeypatch, tmp_path)
        recorder = _Recorder([_GOOD_SVG, '{"ok": true, "defects": []}'])
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.critique == ""
        assert result.path is not None

    def test_a_reported_defect_triggers_a_redraw(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._with_render(monkeypatch, tmp_path)
        recorder = _Recorder(
            [
                _GOOD_SVG,
                '{"ok": false, "defects": ["the drain is painted over the coins"]}',
                _GOOD_SVG,
                '{"ok": true, "defects": []}',
            ]
        )
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.critique == ""
        # The redraw prompt must carry the critique forward.
        assert "painted over the coins" in recorder.prompts[2]

    def test_an_unresolved_defect_keeps_the_hero_and_reports_the_critique(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Spec failure policy row 3: write and link the hero, surface the
        # critique, and let the CLI exit non-zero. Never silently ship.
        self._with_render(monkeypatch, tmp_path)
        recorder = _Recorder(
            [_GOOD_SVG, '{"ok": false, "defects": ["large empty region upper right"]}']
            * 4
        )
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None and result.path.is_file()
        assert "large empty region" in result.critique

    def test_the_retry_cap_is_two(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._with_render(monkeypatch, tmp_path)
        recorder = _Recorder(
            [_GOOD_SVG, '{"ok": false, "defects": ["dead space"]}'] * 8
        )
        monkeypatch.setattr(hero_author, "_collect_text", recorder)
        hero_author.author_hero_svg(brief=_BRIEF, slug="s", images_dir=tmp_path)
        draws = [p for p in recorder.prompts if "Draw" in p or "redraw" in p.lower()]
        assert len(draws) == 1 + hero_author._MAX_CRITIQUE_RETRIES


class TestVisionMalfunctionDegrades:
    """None of these may lose the hero or produce a critique."""

    def test_no_renderer_skips_the_critique(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        monkeypatch.setattr(hero_author, "_collect_text", _Recorder([_GOOD_SVG]))
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None
        assert result.critique == ""

    def test_non_json_verdict_is_treated_as_no_critique(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_render(svg: Path, png: Path) -> Path:
            png.write_bytes(b"\x89PNG")
            return png

        monkeypatch.setattr(hero_author, "render_to_png", fake_render)
        monkeypatch.setattr(
            hero_author,
            "_collect_text",
            _Recorder([_GOOD_SVG, "I think it looks nice!"]),
        )
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None
        assert result.critique == ""

    def test_a_vision_exception_is_treated_as_no_critique(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_render(svg: Path, png: Path) -> Path:
            png.write_bytes(b"\x89PNG")
            return png

        monkeypatch.setattr(hero_author, "render_to_png", fake_render)
        calls = {"n": 0}

        async def draw_then_explode(
            prompt: str, *a: object, **k: object
        ) -> tuple[str, float]:
            calls["n"] += 1
            if calls["n"] == 1:
                return _GOOD_SVG, 0.0
            raise RuntimeError("vision exploded")

        monkeypatch.setattr(hero_author, "_collect_text", draw_then_explode)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None and result.path.is_file()
        assert result.critique == ""


class TestCliExitPolicy:
    """Spec success criterion 4: the three failure outcomes are distinguishable.

    A vision MALFUNCTION must not change the exit code; a vision VERDICT must.
    """

    @staticmethod
    def _result(**overrides: object):  # type: ignore[no-untyped-def]
        from src.agent_sdk.pipeline import PipelineResult

        base: dict[str, object] = {
            "topic": "t",
            "article": '---\nlayout: post\ntitle: "T"\n---\n\nBody.\n',
            "chart_data": {},
            "editorial_score": 1.0,
            "gates_passed": True,
            "publication_ready": True,
            "publication_validator_passed": True,
            "publication_validator_issues": [],
            "total_cost_usd": 0.1,
            "writer_cost_usd": 0.0,
            "graphics_cost_usd": 0.0,
            "research_cost_usd": 0.0,
            "writer_model": "w",
            "graphics_model": "g",
            "stage3_seconds": 0.1,
            "stage4_seconds": 0.1,
            "article_chars": 10,
        }
        base.update(overrides)
        return PipelineResult(**base)  # type: ignore[arg-type]

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result) -> int:
        import src.agent_sdk.pipeline as pipe

        monkeypatch.chdir(tmp_path)

        async def fake_run_pipeline(topic, **kwargs):  # type: ignore[no-untyped-def]
            return result

        monkeypatch.setattr(pipe, "run_pipeline", fake_run_pipeline)
        monkeypatch.setattr(pipe, "POSTS_DIR", tmp_path / "output" / "posts")
        with pytest.raises(SystemExit) as exc:
            pipe._run_end_to_end(
                "topic",
                writer_budget=None,
                graphics_budget=None,
                writer_model="w",
                graphics_model="g",
                research_mode="claude_web",
            )
        return int(exc.value.code or 0)

    def test_a_clean_run_exits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert self._run(tmp_path, monkeypatch, self._result()) == 0

    def test_a_vision_malfunction_does_not_change_the_exit_code(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No renderer / SDK error / non-JSON all surface as: hero present, no
        # critique, no error. That must stay exit 0 (spec failure policy row 2).
        result = self._result(hero_critique="", hero_error="")
        assert self._run(tmp_path, monkeypatch, result) == 0

    def test_an_unresolved_critique_exits_non_zero(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = self._result(hero_critique="- large empty region upper right")
        assert self._run(tmp_path, monkeypatch, result) == 1
        assert "large empty region" in capsys.readouterr().err

    def test_a_missing_hero_exits_non_zero_and_says_why(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = self._result(hero_error="aspect ratio is 1.000")
        assert self._run(tmp_path, monkeypatch, result) == 1
        err = capsys.readouterr().err
        # The diagnosis must name the real fault, not the blog's downstream
        # "hero image not set".
        assert "aspect ratio" in err
        assert "requires a resolvable image:" in err

    def test_the_article_is_still_written_when_the_hero_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Nothing is lost: the operator can look, redraw, or publish anyway.
        result = self._result(hero_critique="- dead space")
        self._run(tmp_path, monkeypatch, result)
        assert list((tmp_path / "output" / "posts").glob("*.md"))


class TestDrawTimeoutIsBounded:
    """BUG-059: _collect_text has no timeout, so an unbounded hero call hung the
    pipeline for 15 minutes with no output. A stalled draw must be a retryable
    attempt, never a hang."""

    def test_a_timeout_is_retried_with_a_simpler_instruction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        calls = {"n": 0}
        prompts: list[str] = []

        async def stall_then_draw(
            prompt: str, *a: object, **k: object
        ) -> tuple[str, float]:
            prompts.append(prompt)
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError
            return _GOOD_SVG, 0.0

        monkeypatch.setattr(hero_author, "_collect_text", stall_then_draw)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is not None, "a timeout must not lose the hero entirely"
        # The retry has to ask for something cheaper, or it just stalls again.
        assert "simpler" in prompts[1]

    def test_repeated_timeouts_give_up_with_a_diagnostic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        async def always_stall(*a: object, **k: object) -> tuple[str, float]:
            raise TimeoutError

        monkeypatch.setattr(hero_author, "_collect_text", always_stall)
        result = hero_author.author_hero_svg(
            brief=_BRIEF, slug="s", images_dir=tmp_path
        )
        assert result.path is None
        # Names the real fault so the operator is not left guessing.
        assert "exceeded" in result.error and "s" in result.error

    def test_the_draw_call_is_actually_wrapped_in_a_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _no_render: None
    ) -> None:
        # Guards the fix itself: if the wait_for is ever removed, a stalled SDK
        # call would hang the pipeline again and this test would hang with it.
        seen: dict[str, object] = {}

        async def capture(coro, timeout=None):  # type: ignore[no-untyped-def]
            seen["timeout"] = timeout
            coro.close()
            return _GOOD_SVG, 0.0

        monkeypatch.setattr(hero_author.asyncio, "wait_for", capture)
        monkeypatch.setattr(hero_author, "_collect_text", _Recorder([_GOOD_SVG]))
        hero_author.author_hero_svg(brief=_BRIEF, slug="s", images_dir=tmp_path)
        assert seen["timeout"] == hero_author._DRAW_TIMEOUT_S
