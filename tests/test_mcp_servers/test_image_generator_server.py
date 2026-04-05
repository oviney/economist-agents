#!/usr/bin/env python3
"""
Tests for the Image Generator MCP Server

Validates mcp_servers/image_generator_server.py without making real API calls.
All OpenAI interactions are mocked.
"""

import base64
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_servers.image_generator_server import (
    _build_dalle_prompt,
    generate_editorial_image,
    mcp,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_png_bytes() -> bytes:
    """Minimal PNG-like bytes for testing file writes."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture()
def mock_openai_image_response(fake_png_bytes: bytes) -> Mock:
    """Build a mock OpenAI images.generate() response with b64_json."""
    image_data = Mock()
    image_data.b64_json = base64.b64encode(fake_png_bytes).decode()
    image_data.url = None
    image_data.revised_prompt = None

    response = Mock()
    response.data = [image_data]
    return response


@pytest.fixture()
def mock_openai_url_response(fake_png_bytes: bytes) -> Mock:
    """Build a mock OpenAI images.generate() response with a URL."""
    image_data = Mock()
    image_data.b64_json = None
    image_data.url = "https://example.com/image.png"
    image_data.revised_prompt = None

    response = Mock()
    response.data = [image_data]
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildDallePrompt:
    """Unit tests for _build_dalle_prompt()."""

    @pytest.mark.unit
    def test_includes_title(self) -> None:
        """Prompt should embed the article title."""
        prompt = _build_dalle_prompt("The Cost of Flaky Tests", "summary text")
        assert "The Cost of Flaky Tests" in prompt

    @pytest.mark.unit
    def test_includes_summary(self) -> None:
        """Prompt should embed the article summary."""
        prompt = _build_dalle_prompt("Title", "QA teams spend 30% of time debugging.")
        assert "QA teams spend 30% of time debugging." in prompt

    @pytest.mark.unit
    def test_no_text_rule_present(self) -> None:
        """Prompt must contain the 'NO TEXT' instruction (editorial requirement)."""
        prompt = _build_dalle_prompt("T", "S")
        assert "NO TEXT" in prompt or "ZERO text" in prompt

    @pytest.mark.unit
    def test_human_element_rule_present(self) -> None:
        """Prompt must mandate a human figure."""
        prompt = _build_dalle_prompt("T", "S")
        assert "human" in prompt.lower() or "HUMAN" in prompt

    @pytest.mark.unit
    def test_painterly_style_present(self) -> None:
        """Prompt must reference the painterly / oil-painting style."""
        prompt = _build_dalle_prompt("T", "S")
        assert "painterly" in prompt.lower() or "oil painting" in prompt.lower()

    @pytest.mark.unit
    def test_colour_palette_present(self) -> None:
        """Prompt must include muted colour palette codes from the skill."""
        prompt = _build_dalle_prompt("T", "S")
        assert "#3b6d8f" in prompt or "#a34054" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# generate_editorial_image — success paths
# ─────────────────────────────────────────────────────────────────────────────


class TestGenerateEditorialImageSuccess:
    """Happy-path tests with mocked OpenAI."""

    @pytest.mark.unit
    def test_returns_path_and_size_b64(
        self,
        tmp_path: Path,
        fake_png_bytes: bytes,
        mock_openai_image_response: Mock,
    ) -> None:
        """Given a b64_json response, the tool saves the file and returns metadata."""
        output_path = str(tmp_path / "test_image.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = mock_openai_image_response

            result = generate_editorial_image(
                article_title="The Economics of Flaky Tests",
                article_summary="QA teams spend 30% of time on unreliable tests.",
                output_path=output_path,
            )

        assert result["path"] == output_path
        assert result["size_bytes"] == len(fake_png_bytes)
        assert Path(output_path).exists()
        assert Path(output_path).read_bytes() == fake_png_bytes

    @pytest.mark.unit
    def test_returns_path_and_size_url(
        self,
        tmp_path: Path,
        fake_png_bytes: bytes,
        mock_openai_url_response: Mock,
    ) -> None:
        """Given a URL response, the tool downloads + saves the file."""
        output_path = str(tmp_path / "url_image.png")

        mock_http_response = Mock()
        mock_http_response.content = fake_png_bytes
        mock_http_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
            patch(
                "mcp_servers.image_generator_server.requests.get",
                return_value=mock_http_response,
            ),
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = mock_openai_url_response

            result = generate_editorial_image(
                article_title="Self-Healing Tests",
                article_summary="Vendors promise 80% reduction; reality is 15%.",
                output_path=output_path,
            )

        assert result["path"] == output_path
        assert result["size_bytes"] == len(fake_png_bytes)
        assert Path(output_path).exists()

    @pytest.mark.unit
    def test_creates_parent_directories(
        self,
        tmp_path: Path,
        fake_png_bytes: bytes,
        mock_openai_image_response: Mock,
    ) -> None:
        """Output parent directories are created automatically."""
        output_path = str(tmp_path / "deep" / "nested" / "dir" / "image.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = mock_openai_image_response

            result = generate_editorial_image(
                article_title="Title",
                article_summary="Summary",
                output_path=output_path,
            )

        assert result["path"] == output_path
        assert Path(output_path).exists()

    @pytest.mark.unit
    def test_dalle_called_with_correct_model_and_size(
        self,
        tmp_path: Path,
        mock_openai_image_response: Mock,
    ) -> None:
        """DALL-E must be called with dall-e-3, 1792x1024, quality=hd."""
        output_path = str(tmp_path / "img.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = mock_openai_image_response

            generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

            call_kwargs = mock_client.images.generate.call_args.kwargs
            assert call_kwargs["model"] == "dall-e-3"
            assert call_kwargs["size"] == "1792x1024"
            assert call_kwargs["quality"] == "hd"
            assert call_kwargs["n"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# generate_editorial_image — error paths
# ─────────────────────────────────────────────────────────────────────────────


class TestGenerateEditorialImageErrors:
    """Error-handling tests."""

    @pytest.mark.unit
    def test_missing_api_key_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Given no OPENAI_API_KEY, the tool returns an error dict without raising."""
        output_path = str(tmp_path / "img.png")

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            # Remove the key entirely so os.environ.get returns None
            os.environ.pop("OPENAI_API_KEY", None)
            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert result["path"] is None
        assert result["size_bytes"] == 0
        assert "OPENAI_API_KEY" in result["error"]

    @pytest.mark.unit
    def test_invalid_api_key_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Given an invalid API key, AuthenticationError is caught and returned."""
        import openai

        output_path = str(tmp_path / "img.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-invalid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.side_effect = openai.AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401, headers={}),
                body={"error": {"message": "Invalid API key"}},
            )

            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert result["path"] is None
        assert result["size_bytes"] == 0

    @pytest.mark.unit
    def test_empty_response_data_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """If DALL-E returns empty data list, the tool returns a structured error."""
        output_path = str(tmp_path / "img.png")

        empty_response = Mock()
        empty_response.data = []

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = empty_response

            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert result["path"] is None
        assert result["size_bytes"] == 0

    @pytest.mark.unit
    def test_no_image_url_or_b64_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """If the response has neither b64_json nor url, return a structured error."""
        output_path = str(tmp_path / "img.png")

        image_data = Mock()
        image_data.b64_json = None
        image_data.url = None

        bad_response = Mock()
        bad_response.data = [image_data]

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = bad_response

            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert result["path"] is None
        assert result["size_bytes"] == 0

    @pytest.mark.unit
    def test_generic_exception_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """A requests.RequestException is caught and returned as a structured error."""
        import requests

        output_path = str(tmp_path / "img.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.side_effect = requests.RequestException(
                "Network timeout"
            )

            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert "Network timeout" in result["error"]
        assert result["path"] is None
        assert result["size_bytes"] == 0

    @pytest.mark.unit
    def test_invalid_timeout_env_var_falls_back_to_default(
        self,
        tmp_path: Path,
        fake_png_bytes: bytes,
        mock_openai_image_response: Mock,
    ) -> None:
        """Non-numeric IMAGE_DOWNLOAD_TIMEOUT_SECONDS falls back to 15 s default."""
        output_path = str(tmp_path / "img.png")

        with (
            patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": "sk-test-valid",
                    "IMAGE_DOWNLOAD_TIMEOUT_SECONDS": "not-a-number",
                },
            ),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value = mock_openai_image_response

            # Should succeed despite invalid timeout value (falls back to 15)
            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert result["path"] == output_path
        assert result["size_bytes"] > 0

    @pytest.mark.unit
    def test_openai_api_error_returns_structured_error(
        self,
        tmp_path: Path,
    ) -> None:
        """An openai.OpenAIError is caught and returned as a structured error."""
        import openai

        output_path = str(tmp_path / "img.png")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-valid"}),
            patch("openai.OpenAI") as mock_client_cls,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.side_effect = openai.APIStatusError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429, headers={}),
                body={"error": {"message": "Rate limit exceeded"}},
            )

            result = generate_editorial_image(
                article_title="T",
                article_summary="S",
                output_path=output_path,
            )

        assert "error" in result
        assert result["path"] is None
        assert result["size_bytes"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# MCP server registration
# ─────────────────────────────────────────────────────────────────────────────


class TestMcpServerRegistration:
    """Verify that the FastMCP server is properly configured."""

    @pytest.mark.unit
    def test_server_name(self) -> None:
        """Server must be named 'image-generator'."""
        assert mcp.name == "image-generator"

    @pytest.mark.unit
    def test_tool_registered(self) -> None:
        """generate_editorial_image must be registered as an MCP tool."""
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "generate_editorial_image" in tool_names

    @pytest.mark.unit
    def test_tool_has_required_parameters(self) -> None:
        """Tool schema must expose article_title, article_summary, output_path."""
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        tool = next(t for t in tools if t.name == "generate_editorial_image")
        schema_props = tool.parameters.get("properties", {})
        assert "article_title" in schema_props
        assert "article_summary" in schema_props
        assert "output_path" in schema_props
