"""Tests for src/agent_sdk/image_gate.py + pipeline wire-up (#403 slice 4)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

from src.agent_sdk import pipeline as pl
from src.agent_sdk.image_gate import (
    EXPECTED_HEIGHT,
    EXPECTED_WIDTH,
    MIN_BYTES,
    ImageGateError,
    check_hero_image,
)
from src.agent_sdk.pipeline import EXIT_IMAGE_GATE_FAILED, _persist_stage3_artefacts
from src.agent_sdk.stage3_runner import Stage3Result


def _fake_png(path: Path, *, width: int, height: int, body_size: int = 0) -> Path:
    """Write a synthetic PNG with the given header dimensions.

    Only the 24-byte signature + IHDR header is well-formed — body is
    arbitrary padding bytes (the gate only inspects header + size).
    Real matplotlib output is bigger; we pad to body_size when given.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        b"\x89PNG\r\n\x1a\n"  # signature
        + b"\x00\x00\x00\x0dIHDR"  # IHDR chunk length + type
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"  # bit depth, color, etc.
    )
    body = b"\x00" * max(0, body_size - len(header))
    path.write_bytes(header + body)
    return path


# ── _read + check_hero_image unit tests ──────────────────────────────


class TestCheckHeroImage:
    def test_passes_on_exactly_expected_dimensions_and_size(
        self, tmp_path: Path
    ) -> None:
        path = _fake_png(
            tmp_path / "hero.png",
            width=EXPECTED_WIDTH,
            height=EXPECTED_HEIGHT,
            body_size=MIN_BYTES,
        )
        check_hero_image(path)  # must not raise

    def test_passes_within_5_percent_dimension_tolerance(self, tmp_path: Path) -> None:
        # 1700×1080 is within ±5% of 1792×1024 (well, 1080 is 5.5% over —
        # use 1075 which is ~5%). Pick safer mid-tolerance values.
        path = _fake_png(
            tmp_path / "hero.png",
            width=int(EXPECTED_WIDTH * 0.97),
            height=int(EXPECTED_HEIGHT * 1.03),
            body_size=MIN_BYTES,
        )
        check_hero_image(path)

    def test_raises_when_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(ImageGateError, match="not found"):
            check_hero_image(tmp_path / "absent.png")

    def test_raises_when_file_too_small(self, tmp_path: Path) -> None:
        path = _fake_png(
            tmp_path / "hero.png",
            width=EXPECTED_WIDTH,
            height=EXPECTED_HEIGHT,
            body_size=0,  # only the 24-byte header
        )
        with pytest.raises(ImageGateError, match="byte minimum"):
            check_hero_image(path)

    def test_raises_when_magic_bytes_wrong(self, tmp_path: Path) -> None:
        path = tmp_path / "hero.png"
        path.write_bytes(b"\x00" * 100_000)  # not a PNG
        with pytest.raises(ImageGateError, match="not a valid PNG"):
            check_hero_image(path)

    def test_raises_when_width_outside_tolerance(self, tmp_path: Path) -> None:
        path = _fake_png(
            tmp_path / "hero.png",
            width=900,  # way too narrow
            height=EXPECTED_HEIGHT,
            body_size=MIN_BYTES,
        )
        with pytest.raises(ImageGateError, match="dimensions"):
            check_hero_image(path)

    def test_raises_when_height_outside_tolerance(self, tmp_path: Path) -> None:
        path = _fake_png(
            tmp_path / "hero.png",
            width=EXPECTED_WIDTH,
            height=2000,  # way too tall
            body_size=MIN_BYTES,
        )
        with pytest.raises(ImageGateError, match="dimensions"):
            check_hero_image(path)


# ── pipeline wire-up: --resume exits 11 when gate fails ──────────────


def _seed_state(tmp_path: Path) -> None:
    """Helper: put a Stage 3 state file in place for --resume tests."""
    s3 = Stage3Result(
        topic="test",
        article="---\nlayout: post\ntitle: T\nimage: /assets/images/g.png\n"
        "image_alt: alt\nimage_caption: cap\n---\n\nBody.\n",
        chart_data={"title": "T", "data": [{"metric": "A", "value": 1}]},
        total_cost_usd=0.1,
        writer_cost_usd=0.08,
        graphics_cost_usd=0.02,
        writer_model="claude-sonnet-4-6",
        graphics_model="claude-sonnet-4-6",
        wall_seconds=1.0,
        research_brief_chars=100,
        article_chars=80,
        stat_audit_removed=0,
        chart_path=None,
        prompt_path=None,
        slug="g",
        image_prompt="prompt",
    )
    _persist_stage3_artefacts(s3)


class TestResumeGateWireUp:
    def test_resume_without_image_exits_11(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _seed_state(tmp_path)
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "--resume", "g"])

        with pytest.raises(SystemExit) as exc_info:
            pl.main()
        assert exc_info.value.code == EXIT_IMAGE_GATE_FAILED
        err = capsys.readouterr().err
        assert "Image gate failed" in err
        assert "not found" in err

    def test_resume_with_valid_image_passes_gate_and_runs_stage4(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _seed_state(tmp_path)
        _fake_png(
            tmp_path / "output" / "posts" / "images" / "g.png",
            width=EXPECTED_WIDTH,
            height=EXPECTED_HEIGHT,
            body_size=MIN_BYTES,
        )
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "--resume", "g"])

        from unittest.mock import MagicMock

        fake_s4 = MagicMock(
            article="polished",
            editorial_score=90,
            gates_passed=5,
            publication_ready=True,
            publication_validator_passed=True,
            publication_validator_issues=[],
        )
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.run_stage4",
            lambda article, chart: fake_s4,
        )
        pl.main()  # must not raise SystemExit

    def test_no_image_mode_skips_gate_even_without_png(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--no-image is the explicit opt-out: gate is bypassed entirely."""
        monkeypatch.chdir(tmp_path)
        _seed_state(tmp_path)
        # Deliberately do NOT create output/posts/images/g.png

        monkeypatch.setattr(sys, "argv", ["pipeline.py", "--resume", "g", "--no-image"])
        from unittest.mock import MagicMock

        fake_s4 = MagicMock(
            article="polished",
            editorial_score=90,
            gates_passed=5,
            publication_ready=True,
            publication_validator_passed=True,
            publication_validator_issues=[],
        )
        monkeypatch.setattr(
            "src.agent_sdk.pipeline.run_stage4",
            lambda article, chart: fake_s4,
        )
        pl.main()  # must not raise SystemExit — gate was skipped

    def test_resume_with_wrong_dims_exits_11_with_dim_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _seed_state(tmp_path)
        _fake_png(
            tmp_path / "output" / "posts" / "images" / "g.png",
            width=512,
            height=512,
            body_size=MIN_BYTES,
        )
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "--resume", "g"])

        with pytest.raises(SystemExit) as exc_info:
            pl.main()
        assert exc_info.value.code == EXIT_IMAGE_GATE_FAILED
        assert "dimensions 512x512" in capsys.readouterr().err
