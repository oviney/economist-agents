#!/usr/bin/env python3
"""
Tests for featured_image_agent.py

Covers:
- ECONOMIST_IMAGE_STYLE constant — editorial quality requirements
- create_image_prompt() — SCENE/MOOD sections, contrarian angle, mood parameter
- generate_featured_image() — API key guard, DALL-E call, file save, error handling
- CLI argument handling (--mood flag)

All DALL-E / OpenAI calls are mocked; no real API keys required.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from featured_image_agent import (
    ECONOMIST_IMAGE_STYLE,
    create_image_prompt,
    generate_featured_image,
    test_generate_sample_images,
)

# ===========================================================================
# ECONOMIST_IMAGE_STYLE constant
# ===========================================================================


class TestEconomistImageStyle:
    """Validate the style specification constant against SKILL.md requirements."""

    def test_bold_graphic_style_required(self) -> None:
        """Style must demand bold graphic editorial illustration, not painterly."""
        assert "bold" in ECONOMIST_IMAGE_STYLE.lower()
        assert "graphic" in ECONOMIST_IMAGE_STYLE.lower()
        assert "editorial illustration" in ECONOMIST_IMAGE_STYLE.lower()
        assert "NOT watercolour" in ECONOMIST_IMAGE_STYLE
        assert "NOT oil painting" in ECONOMIST_IMAGE_STYLE
        assert "NOT photorealism" in ECONOMIST_IMAGE_STYLE

    def test_human_element_mandatory(self) -> None:
        """Human figures must be explicitly required."""
        assert "MANDATORY" in ECONOMIST_IMAGE_STYLE
        assert "human figure" in ECONOMIST_IMAGE_STYLE

    def test_expanded_colour_palette(self) -> None:
        """Colour palette must include Economist red, blues, and accent colours."""
        assert "#E3120B" in ECONOMIST_IMAGE_STYLE  # Economist red
        assert "#3b6d8f" in ECONOMIST_IMAGE_STYLE
        assert "#a34054" in ECONOMIST_IMAGE_STYLE  # dusty red
        assert "#c4953a" in ECONOMIST_IMAGE_STYLE  # ochre

    def test_no_text_instruction(self) -> None:
        """Style must explicitly forbid text/labels in the image."""
        assert (
            "NO TEXT" in ECONOMIST_IMAGE_STYLE
            or "ABSOLUTELY NO TEXT" in ECONOMIST_IMAGE_STYLE
        )

    def test_avoids_cliches(self) -> None:
        """Style must explicitly avoid technology clichés."""
        assert (
            "lightbulbs" in ECONOMIST_IMAGE_STYLE
            or "cliché" in ECONOMIST_IMAGE_STYLE.lower()
        )

    def test_composition_includes_scale_exaggeration(self) -> None:
        """Composition rules must include scale exaggeration guidance."""
        assert (
            "scale exaggeration" in ECONOMIST_IMAGE_STYLE
            or "exaggeration" in ECONOMIST_IMAGE_STYLE
        )


# ===========================================================================
# create_image_prompt()
# ===========================================================================


class TestCreateImagePrompt:
    """Unit tests for prompt construction."""

    TOPIC = "The Economics of Flaky Tests"
    SUMMARY = (
        "QA teams spend 30% of time on unreliable tests, costing $50k per engineer."
    )
    CONTRARIAN = "Flaky tests are a culture problem, not a technical one."

    def test_prompt_contains_economist_style(self) -> None:
        """Prompt must embed the ECONOMIST_IMAGE_STYLE constant."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert "Bold" in prompt or "bold" in prompt
        assert "graphic" in prompt.lower()

    def test_prompt_contains_scene_section(self) -> None:
        """Prompt must contain a SCENE section as required by SKILL.md template."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert "SCENE:" in prompt

    def test_scene_contains_topic(self) -> None:
        """SCENE section must reference the article topic."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert self.TOPIC in prompt

    def test_scene_contains_summary(self) -> None:
        """SCENE section must incorporate the article summary."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert self.SUMMARY in prompt

    def test_prompt_contains_mood_section(self) -> None:
        """Prompt must contain a MOOD section as required by SKILL.md template."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY, mood="satirical")
        assert "MOOD:" in prompt

    def test_mood_is_capitalised_in_prompt(self) -> None:
        """Mood value should be capitalised in the prompt output."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY, mood="satirical")
        assert "Satirical" in prompt

    def test_default_mood_is_contemplative(self) -> None:
        """Default mood should be 'contemplative'."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert "Contemplative" in prompt

    def test_contrarian_angle_included_when_provided(self) -> None:
        """Contrarian angle must appear in prompt when supplied."""
        prompt = create_image_prompt(
            self.TOPIC, self.SUMMARY, contrarian_angle=self.CONTRARIAN
        )
        assert self.CONTRARIAN in prompt

    def test_contrarian_angle_omitted_when_empty(self) -> None:
        """No contrarian placeholder text when angle is empty."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY, contrarian_angle="")
        assert "counterintuitive angle:" not in prompt

    def test_prompt_requires_human_figure_in_scene(self) -> None:
        """SCENE section must include human figure instruction."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert "human figure" in prompt

    def test_prompt_has_no_text_critical_instruction(self) -> None:
        """Prompt must end with CRITICAL no-text instruction."""
        prompt = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert "ZERO text" in prompt or "NO TEXT" in prompt or "CRITICAL" in prompt

    def test_returns_string(self) -> None:
        """create_image_prompt must return a string."""
        result = create_image_prompt(self.TOPIC, self.SUMMARY)
        assert isinstance(result, str)
        assert len(result) > 100  # should be a substantial prompt

    def test_prompt_truncated_to_dalle_max_length(self) -> None:
        """Prompt must never exceed DALLE_MAX_PROMPT_LENGTH (3900 chars)."""
        from featured_image_agent import DALLE_MAX_PROMPT_LENGTH

        # Use an extremely long summary to trigger truncation
        long_summary = "A" * 5000
        prompt = create_image_prompt(self.TOPIC, long_summary)
        assert len(prompt) <= DALLE_MAX_PROMPT_LENGTH, (
            f"Prompt length {len(prompt)} exceeds DALLE_MAX_PROMPT_LENGTH {DALLE_MAX_PROMPT_LENGTH}"
        )


# ===========================================================================
# generate_featured_image()
# ===========================================================================


def _make_openai_mock(mock_client: Mock) -> MagicMock:
    """Return a mock openai module whose OpenAI() constructor yields mock_client."""
    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    return mock_openai


class TestGenerateFeaturedImage:
    """Integration-style tests for generate_featured_image (DALL-E mocked)."""

    TOPIC = "Self-Healing Tests: Myth vs Reality"
    SUMMARY = "AI promises 80% reduction in test maintenance; reality is closer to 15%."

    def test_returns_none_without_api_key(self) -> None:
        """Must return None and not crash when OPENAI_API_KEY is absent."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path="/tmp/test_image.png",
            )
        assert result is None

    def test_saves_image_and_returns_path_with_b64(self, tmp_path: Path) -> None:
        """Must save image bytes and return output path when b64_json is returned."""
        import base64

        output_file = str(tmp_path / "image.png")
        fake_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        b64_data = base64.b64encode(fake_bytes).decode()

        mock_image = Mock()
        mock_image.b64_json = b64_data
        mock_image.url = None
        mock_image.revised_prompt = None

        mock_response = Mock()
        mock_response.data = [mock_image]

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        assert result == output_file
        assert Path(output_file).exists()
        assert Path(output_file).read_bytes() == fake_bytes

    def test_saves_image_and_returns_path_with_url(self, tmp_path: Path) -> None:
        """Must download image from URL and save when url is returned."""
        output_file = str(tmp_path / "image.png")
        fake_bytes = b"\x89PNG\r\n" + b"\x00" * 50

        mock_image = Mock()
        mock_image.b64_json = None
        mock_image.url = "https://example.com/fake.png"
        mock_image.revised_prompt = "A revised prompt"

        mock_response = Mock()
        mock_response.data = [mock_image]

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        mock_requests_response = Mock()
        mock_requests_response.content = fake_bytes
        mock_requests_response.raise_for_status = Mock()

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
            patch("requests.get", return_value=mock_requests_response),
        ):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        assert result == output_file
        assert Path(output_file).read_bytes() == fake_bytes

    def test_returns_none_when_no_image_data(self, tmp_path: Path) -> None:
        """Must return None when DALL-E returns empty data list."""
        output_file = str(tmp_path / "image.png")

        mock_response = Mock()
        mock_response.data = []

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        assert result is None

    def test_returns_none_on_api_exception(self, tmp_path: Path) -> None:
        """Must return None (not raise) when DALL-E call raises an exception."""
        output_file = str(tmp_path / "image.png")

        mock_client = Mock()
        mock_client.images.generate.side_effect = RuntimeError("API error")

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        assert result is None

    def test_uses_landscape_hd_defaults(self, tmp_path: Path) -> None:
        """Default size must be 1792x1024 and quality hd (SKILL.md requirement)."""
        import base64

        output_file = str(tmp_path / "image.png")
        fake_bytes = b"\x89PNG" + b"\x00" * 20

        mock_image = Mock()
        mock_image.b64_json = base64.b64encode(fake_bytes).decode()
        mock_image.url = None
        mock_image.revised_prompt = None

        mock_response = Mock()
        mock_response.data = [mock_image]

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        call_kwargs = mock_client.images.generate.call_args
        assert call_kwargs.kwargs["size"] == "1792x1024"
        assert call_kwargs.kwargs["quality"] == "hd"

    def test_mood_parameter_passed_to_prompt(self, tmp_path: Path) -> None:
        """Mood parameter must appear in the prompt sent to DALL-E."""
        import base64

        output_file = str(tmp_path / "image.png")
        fake_bytes = b"\x89PNG" + b"\x00" * 20

        mock_image = Mock()
        mock_image.b64_json = base64.b64encode(fake_bytes).decode()
        mock_image.url = None
        mock_image.revised_prompt = None

        mock_response = Mock()
        mock_response.data = [mock_image]

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
                mood="urgent",
            )

        call_kwargs = mock_client.images.generate.call_args
        assert "Urgent" in call_kwargs.kwargs["prompt"]

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        """Output directory must be created automatically if it does not exist."""
        import base64

        output_file = str(tmp_path / "nested" / "deep" / "image.png")
        fake_bytes = b"\x89PNG" + b"\x00" * 20

        mock_image = Mock()
        mock_image.b64_json = base64.b64encode(fake_bytes).decode()
        mock_image.url = None
        mock_image.revised_prompt = None

        mock_response = Mock()
        mock_response.data = [mock_image]

        mock_client = Mock()
        mock_client.images.generate.return_value = mock_response

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict(sys.modules, {"openai": _make_openai_mock(mock_client)}),
        ):
            result = generate_featured_image(
                topic=self.TOPIC,
                article_summary=self.SUMMARY,
                output_path=output_file,
            )

        assert result == output_file
        assert Path(output_file).exists()


# ===========================================================================
# test_generate_sample_images()
# ===========================================================================


class TestGenerateSampleImages:
    """Tests for the bundled sample-image test harness."""

    def test_runs_without_api_key(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Must complete without error when OPENAI_API_KEY is absent."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.mkdir"),
        ):
            test_generate_sample_images()

        captured = capsys.readouterr()
        # Should print the skipping message three times (one per topic)
        assert captured.out.count("OPENAI_API_KEY not set") == 3

    def test_generates_three_topics(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Must attempt to generate images for exactly 3 topics."""
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.mkdir"),
        ):
            test_generate_sample_images()

        captured = capsys.readouterr()
        assert "Test 1/3" in captured.out
        assert "Test 2/3" in captured.out
        assert "Test 3/3" in captured.out
